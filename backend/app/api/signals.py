"""
Signals API endpoints - Real Polymarket data with caching.
"""
from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
import httpx
import asyncio
import json

from app.core.cache import cache
from app.core.logger import get_logger
from app.services.strategies.fade import analyze_fade_opportunity
from app.utils.market import get_yes_no_prices

logger = get_logger(__name__)

router = APIRouter()

# Cache keys
CACHE_KEY_MARKETS = "polymarket_markets"
CACHE_TTL_SECONDS = 60  # Fresh data every 60 seconds


class Signal(BaseModel):
    """Signal model."""
    id: str
    market_id: str
    condition_id: str
    slug: str
    market_question: str
    score: int
    level: str
    direction: str
    whale_score: int
    volume_score: int
    news_score: int
    whale_count: int
    unique_whale_count: int
    volume_24h: float
    news_count: int
    yes_price: float
    no_price: float
    price_movement: float
    liquidity: float
    spread: float
    hours_remaining: float
    end_date: str
    polymarket_url: str
    created_at: datetime


class SignalResponse(BaseModel):
    """Response model for signals."""
    signals: List[Signal]
    total: int
    cached: bool = False
    cache_age: Optional[int] = None
    error: Optional[str] = None


async def fetch_markets_from_api(max_retries: int = 3):
    """Fetch ALL markets from Polymarket API using pagination with retry logic."""
    
    async def fetch_with_retry(client, url, attempt=1):
        """Fetch URL with exponential backoff retry."""
        try:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json(), None
            elif response.status_code == 429:  # Rate limited
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 2, 4, 8 seconds
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    return await fetch_with_retry(client, url, attempt + 1)
            elif response.status_code >= 500:  # Server error
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    return await fetch_with_retry(client, url, attempt + 1)
            return None, f"API Error {response.status_code}"
        except httpx.TimeoutException:
            if attempt < max_retries:
                logger.warning(f"Timeout, retry {attempt + 1}/{max_retries}")
                return await fetch_with_retry(client, url, attempt + 1)
            return None, "Timeout après plusieurs tentatives"
        except Exception as e:
            return None, str(e)
    
    # Reduced timeout: 10s instead of 30s
    async with httpx.AsyncClient(timeout=10.0) as client:
        all_markets = []
        offset = 0
        limit = 1000
        base_url = "https://gamma-api.polymarket.com/markets"
        
        try:
            while True:
                url = f"{base_url}?limit={limit}&offset={offset}&active=true&closed=false"
                
                data, error = await fetch_with_retry(client, url)
                
                if error:
                    logger.warning(f"API Error: {error}")
                    break
                
                if not isinstance(data, list) or len(data) == 0:
                    break
                    
                all_markets.extend(data)
                logger.debug(f"Fetched {len(data)} markets (Offset: {offset})")
                
                if len(data) < limit:
                    break
                    
                offset += limit
                
                # Safety break
                if offset > 10000:
                    break
            
            if len(all_markets) > 0:
                logger.info(f"Total markets fetched: {len(all_markets)}")
                return all_markets, None
                
            return None, "Aucun marché trouvé (API error?)"
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return None, str(e)



async def fetch_markets():
    """
    Fetch markets with caching strategy:
    1. Try fresh API data
    2. If API fails, use cached data (any age)
    3. Cache successful responses
    """
    # Try to get fresh data from API
    markets, api_error = await fetch_markets_from_api()
    
    if markets:
        # Success! Cache the data
        cache.set(CACHE_KEY_MARKETS, markets)
        return markets, None, False, None
    
    # API failed - try cache fallback
    cached_markets = cache.get_fallback(CACHE_KEY_MARKETS)
    cache_age = cache.get_age(CACHE_KEY_MARKETS)
    
    if cached_markets:
        # Return cached data with warning
        age_str = f"{cache_age // 60}min" if cache_age and cache_age >= 60 else f"{cache_age}s"
        return cached_markets, f"⚠️ Données en cache ({age_str}). {api_error}", True, cache_age
    
    # No cache available
    return [], api_error, False, None


def calculate_score(market: dict) -> tuple[int, str]:
    """
    Smart Scoring 2.0:
    - Focus on Turnover (Activity relative to Size)
    - Penalize Wide Spreads (Untradeable)
    - Reward Volatility (Price Movement)
    """
    score = 0
    
    # 1. Liquidity (Max 30 pts)
    liquidity = float(market.get("liquidityNum") or 0)
    if liquidity > 1000000:
        score += 30
    elif liquidity > 500000:
        score += 25
    elif liquidity > 100000:
        score += 20
    elif liquidity > 50000:
        score += 15
    elif liquidity > 10000:
        score += 10
        
    # 2. Activity / Turnover (Max 40 pts) - Is it HEATING UP?
    vol_24h = float(market.get("volume24hr") or market.get("volume") or 0)
    
    # Whale Bonus (Absolute Volume)
    if vol_24h > 100000:
        score += 10
    
    # Turnover Ratio (Relative Volume)
    # If a 10k pool trades 5k (0.5 ratio), it's hotter than a 1M pool trading 10k (0.01 ratio).
    if liquidity > 0:
        turnover = vol_24h / liquidity
        if turnover > 0.5:
            score += 30
        elif turnover > 0.2:
            score += 20
        elif turnover > 0.1:
            score += 10
            
    # 3. Volatility / Opportunity (Max 30 pts)
    price_change = abs(float(market.get("oneDayPriceChange") or 0))
    if price_change > 10.0:
        score += 20
    elif price_change > 5.0:
        score += 15
    elif price_change > 2.0:
        score += 10
        
    # 4. Spread Analysis (Bonus or Penalty)
    try:
        best_bid = float(market.get("bestBid") or 0)
        best_ask = float(market.get("bestAsk") or 0)
        
        if best_bid > 0 and best_ask > 0:
            spread = best_ask - best_bid
            
            # Tight Spread Bonus (Easy to scalp/enter)
            if spread <= 0.01:
                score += 10
            # Wide Spread Penalty (Trap)
            elif spread > 0.05:
                score -= 30
            elif spread > 0.03:
                score -= 15
    except (ValueError, TypeError, KeyError):
        pass # Ignore spread if data missing
        
    # 5. Dead Market Penalty
    if vol_24h < 1000:
        score -= 50
        
    # Clamping (0-100) -> Normalize to 0-10
    raw_score = max(0, min(100, int(score)))
    final_score = round(raw_score / 10)
    
    # Level Determination (Adjusted for 0-10 scale)
    if final_score >= 8:
        level = "opportunity" # The cream of the crop
    elif final_score >= 6:
        level = "strong"
    elif final_score >= 4:
        level = "interesting"
    else:
        level = "watch"
    
    return final_score, level


def parse_prices(market: dict):
    """Parse prices safely."""
    return get_yes_no_prices(market)


def market_to_signal(market: dict) -> Signal:
    """Convert Polymarket market to Signal."""
    score, level = calculate_score(market)
    yes_price, no_price = parse_prices(market)
    
    # Direction based on momentum
    price_change = market.get("oneDayPriceChange", 0) or 0
    direction = "YES" if price_change > 0 or yes_price > 0.5 else "NO"
    
    # Get slug - Prioritize EVENT slug because market slug often 404s on /event/ URL
    slug = ""
    if market.get("events") and len(market["events"]) > 0:
        slug = market["events"][0].get("slug", "")
    
    if not slug:
        slug = market.get("slug", "")
    
    # Generate URL
    if slug:
        polymarket_url = f"https://polymarket.com/event/{slug}"
    else:
        polymarket_url = "https://polymarket.com"

    vol_24h = market.get("volume24hr", 0) or 0
    liquidity = market.get("liquidityNum", 0) or 0
    
    # Calculate Spread
    spread = 0.0
    try:
        best_bid = float(market.get("bestBid") or 0)
        best_ask = float(market.get("bestAsk") or 0)
        if best_bid > 0 and best_ask > 0:
            spread = best_ask - best_bid
    except (ValueError, TypeError, KeyError):
        pass

    # Calculate Time Remaining
    hours_remaining = 0.0
    try:
        end_date_str = market.get("endDateIso")
        if end_date_str:
            clean_date_str = end_date_str.replace("Z", "+00:00")
            end_date = datetime.fromisoformat(clean_date_str)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            delta = end_date - datetime.now(timezone.utc)
            hours_remaining = max(0.0, delta.total_seconds() / 3600.0)
    except (ValueError, TypeError, KeyError):
        pass

    whale_count = max(1, int(vol_24h / 10000))
    # Heuristic: 40% of trades are unique whales, capped at least 1
    unique_whale_count = max(1, int(whale_count * 0.4))

    return Signal(
        id=str(market.get("id", "")),
        market_id=str(market.get("id", "")),
        condition_id=market.get("conditionId", ""),
        slug=slug,
        market_question=market.get("question", "Unknown"),
        score=score,
        level=level,
        direction=direction,
        whale_score=min(int(vol_24h / 1000), 100),
        volume_score=min(int(liquidity / 10000), 100),
        news_score=50,
        whale_count=whale_count,
        unique_whale_count=unique_whale_count,
        volume_24h=vol_24h,
        news_count=0,
        yes_price=yes_price,
        no_price=no_price,
        price_movement=price_change,
        liquidity=liquidity,
        spread=spread,
        hours_remaining=hours_remaining,
        end_date=market.get("endDateIso", ""),
        polymarket_url=polymarket_url,
        created_at=datetime.now(timezone.utc)
    )


@router.get("", response_model=SignalResponse)
async def get_signals(
    min_score: int = Query(default=0, ge=0, le=100),
    min_volume: float = Query(default=0, ge=0),
    min_liquidity: float = Query(default=0, ge=0),
    level: Optional[str] = Query(default=None),
    limit: int = Query(default=1000, le=5000)
):
    """
    Get signals from Polymarket with caching.
    
    When API is down, returns cached data with age indicator.
    """
    try:
        markets, error, is_cached, cache_age = await fetch_markets()
        
        if not markets and error:
            return SignalResponse(signals=[], total=0, cached=False, error=error)
        
        signals = []
        for market in markets:
            try:
                if market.get("closed") or not market.get("question"):
                    continue
                
                signal = market_to_signal(market)
                
                # Apply filters
                if signal.score < min_score:
                    continue
                if signal.volume_24h < min_volume:
                    continue
                if signal.liquidity < min_liquidity:
                    continue
                if level and signal.level != level:
                    continue
                
                signals.append(signal)
            except Exception:
                continue
        
        # Sort by score
        signals.sort(key=lambda x: x.score, reverse=True)
        
        return SignalResponse(
            signals=signals[:limit],
            total=len(signals),
            cached=is_cached,
            cache_age=cache_age,
            error=error
        )
    except Exception as e:
        return SignalResponse(signals=[], total=0, cached=False, error=f"CRASH: {str(e)}")


@router.get("/equilibrage", response_model=SignalResponse)
async def get_equilibrage_signals(
    limit: int = Query(default=1000, le=5000)
):
    """
    Get 'Equilibrage' signals:
    - YES price between 0.45 and 0.55
    - Sorted by volume
    """
    try:
        markets, error, is_cached, cache_age = await fetch_markets()
        
        if not markets and error:
            return SignalResponse(signals=[], total=0, cached=False, error=error)
        
        signals = []
        for market in markets:
            try:
                if market.get("closed") or not market.get("question"):
                    continue
                
                # Get basic signal to check prices
                signal = market_to_signal(market)
                
                # Filter for Equilibrage: 45% <= price <= 55%
                if not (0.45 <= signal.yes_price <= 0.55):
                    continue
                    
                signals.append(signal)
            except Exception:
                continue
        
        # Sort by volume (liquidity/action is more important here than score)
        signals.sort(key=lambda x: x.volume_24h, reverse=True)
        
        return SignalResponse(
            signals=signals[:limit],
            total=len(signals),
            cached=is_cached,
            cache_age=cache_age,
            error=error
        )
    except Exception as e:
        return SignalResponse(signals=[], total=0, cached=False, error=f"CRASH: {str(e)}")


@router.get("/hot", response_model=SignalResponse)
async def get_hot_signals(
    amount: float = Query(default=0, ge=0),
    target_profit: float = Query(default=0, ge=0),
    strategy: str = Query(default="whale"), # whale, yield, scalp
    limit: int = Query(default=1000, le=5000)
):
    """
    Get 'Pro Insights' Calls based on Insider Strategies.
    Strategies:
    - whale: Smart Money Tracking (Volume > 25k or High Activity). COPY TRADING.
    - yield: Safe Yield / Group Arb (Sum of Prices < 0.98). DELTA NEUTRAL.
    - scalp: Liquidity Pockets (Spread > 3cts). LIMIT ORDERS.
    - fade: Contrarian / Hype Fading (High Price + High Sentiment). BET NO.
    """
    try:
        markets, error, is_cached, cache_age = await fetch_markets()
        
        if not markets and error:
            return SignalResponse(signals=[], total=0, cached=False, error=error)
            
        signals = []
        
        # Pre-calc time
        now = datetime.now(timezone.utc)
        
        for market in markets:
            try:
                # Basic validation
                if market.get("closed") or not market.get("question"):
                    continue

                # Parse prices
                outcome_prices = json.loads(market.get("outcomePrices", "[]"))
                if len(outcome_prices) < 2:
                    continue
                    
                yes_price = float(outcome_prices[0])
                no_price = float(outcome_prices[1])
                liquidity = float(market.get("liquidityNum") or 0)
                volume = float(market.get("volume24hr") or market.get("volume") or 0)
                
                opportunity_side = None
                display_msg = ""
                sort_score = 0
                
                # --- STRATEGY LOGIC ---

                if strategy == "whale":
                    # Logic: Identify "Heavy Actions".
                    # Filter 1: High Volume (>25k).
                    # Filter 2: Volume/Liquidity Ratio indicates action?
                    # Simple: If Volume > 25,000, it's a Whale Call.
                    
                    if volume > 25000:
                        # Which side? The side with price momentum or just the market.
                        # We return the market as a "Whale Call".
                        # Heuristic: If YES > 0.60, Whale is Buying YES. If YES < 0.40, Whale is Buying NO.
                        # Default to trending side.
                        if yes_price > 0.55:
                            opportunity_side = "YES"
                            display_msg = f"WHALE BUY: YES ({yes_price:.2f})"
                        elif no_price > 0.55:
                            opportunity_side = "NO"
                            display_msg = f"WHALE BUY: NO ({no_price:.2f})"
                        else:
                            opportunity_side = "WATCH" # Accumulation
                            display_msg = "WHALE ACCUMULATION"
                        
                        sort_score = volume

                elif strategy == "yield":
                    # Logic: Sum of prices < 1.0 indicates arbitrage opportunity.
                    # Standard Polymarket is Binary (2 outcomes). Sum should be 1.0.
                    # Any gap represents potential yield.
                    
                    price_sum = sum([float(p) for p in outcome_prices])
                    
                    # Calculate potential yield from buying all outcomes
                    # If sum < 1.0, buying all = guaranteed profit
                    # If sum > 1.0 but close, still worth showing
                    
                    if price_sum < 1.0:
                        opportunity_side = "HEDGE"
                        yield_pct = (1.0 - price_sum) * 100
                        display_msg = f"SAFE YIELD: +{yield_pct:.1f}%"
                        sort_score = yield_pct
                    elif price_sum < 1.02 and liquidity > 500:
                        # Near-parity: Small edge but still opportunity
                        opportunity_side = "HEDGE"
                        yield_pct = (1.0 - price_sum) * 100  # Will be negative but small
                        display_msg = f"NEAR PARITY: {price_sum:.2f}"
                        sort_score = 1.0 - price_sum

                elif strategy == "scalp":
                    # Logic: Detect wide spreads between YES and NO prices.
                    # In a perfect market: YES + NO = 1.0
                    # If YES + NO > 1.0, there's a spread we can scalp.
                    
                    price_sum = yes_price + no_price
                    spread = price_sum - 1.0
                    
                    # Filter: Spread > 1 cent (0.01) and decent liquidity
                    if spread > 0.01 and liquidity > 1000:
                        opportunity_side = "SCALP"
                        spread_cents = spread * 100
                        display_msg = f"SCALP SPREAD: {spread_cents:.1f}c"
                        sort_score = spread
                    elif spread > 0.005 and liquidity > 5000:
                        # Smaller spread but high liquidity = still tradeable
                        opportunity_side = "SCALP"
                        spread_cents = spread * 100
                        display_msg = f"TIGHT SCALP: {spread_cents:.1f}c"
                        sort_score = spread

                elif strategy == "fade":
                    # Logic: Fade Strategy Service
                    opp_side, msg, score = await analyze_fade_opportunity(market)
                    
                    if opp_side:
                        opportunity_side = opp_side
                        display_msg = msg
                        sort_score = score

                
                if not opportunity_side:
                    continue
                
                # Construct Signal
                signal = market_to_signal(market)
                if not signal: 
                    continue

                # Override/Enrich for Display
                # We hijack 'direction' or 'level' to enable frontend to display the Call.
                signal.level = "opportunity"
                if display_msg:
                    # We can store the msg in 'direction' if we want, or rely on frontend?
                    # Better: Frontend generates text. But backend logic is cleaner here.
                    # There is no 'message' field. We'll reuse 'direction' for the specific "Call".
                    signal.direction = display_msg
                
                signals.append({
                    "data": signal,
                    "sort": sort_score
                })
                
            except Exception:
                continue

        # Sort
        signals.sort(key=lambda x: x["sort"], reverse=True)
        
        # Unwrap
        final_signals = [s["data"] for s in signals]
        
        return SignalResponse(
            signals=final_signals[:limit],
            total=len(final_signals),
            cached=is_cached,
            cache_age=cache_age,
            error=error
        )
    except Exception as e:
        # RETURN ERROR AS STRING instead of 500ing
        return SignalResponse(signals=[], total=0, cached=False, error=f"CRASH: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    return cache.get_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cache."""
    cache.clear()
    return {"message": "Cache cleared"}


# --- ADVANCED STRATEGY ENDPOINTS ---

from app.services.strategies.negative_risk import calculate_negative_risk

@router.get("/arbitrage", response_model=dict)
async def get_arbitrage_opportunities():
    """
    Get 'Negative Risk' Arbitrage Opportunities.
    Returns events where Sum(YES) > 1.02.
    """
    try:
        markets, error, is_cached, cache_age = await fetch_markets()
        
        if not markets:
            return {"opportunities": [], "error": error}
            
        opportunities = calculate_negative_risk(markets)
        
        # Convert dataclass to dict
        results = []
        for opp in opportunities:
            results.append({
                "event_id": opp.event_id,
                "event_slug": opp.event_slug,
                "event_title": opp.event_title,
                "market_count": opp.market_count,
                "sum_yes_price": opp.sum_yes_price,
                "profit_pct": opp.profit_pct,
                "markets": opp.markets
            })
            
        return {
            "opportunities": results,
            "count": len(results),
            "cached": is_cached,
            "error": None
        }
    except Exception as e:
        return {"opportunities": [], "error": f"CRASH: {str(e)}"}
