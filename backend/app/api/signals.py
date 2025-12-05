"""
Signals API endpoints - Real Polymarket data with caching.
"""
from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import httpx
import json

from app.core.cache import cache

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
    volume_24h: float
    news_count: int
    yes_price: float
    no_price: float
    price_movement: float
    liquidity: float
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


async def fetch_markets_from_api():
    """Fetch ALL markets from Polymarket API using pagination."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        all_markets = []
        offset = 0
        limit = 1000
        base_url = "https://gamma-api.polymarket.com/markets"
        
        try:
            while True:
                # Fetch only active and non-closed markets
                url = f"{base_url}?limit={limit}&offset={offset}&active=true&closed=false"
                
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        
                        if not isinstance(data, list) or len(data) == 0:
                            break
                            
                        all_markets.extend(data)
                        print(f"Fetched {len(data)} markets (Offset: {offset})")
                        
                        if len(data) < limit:
                            break
                            
                        offset += limit
                        
                        # Safety break to avoid infinite loops if something goes wrong
                        if offset > 10000:
                            break
                    else:
                        print(f"API Error {response.status_code}: {response.text}")
                        break
                        
                except Exception as e:
                    print(f"Error checking url {url}: {e}")
                    break
            
            if len(all_markets) > 0:
                print(f"Total markets fetched: {len(all_markets)}")
                return all_markets, None
                
            return None, "Aucun marché trouvé (API error?)"
            
        except Exception as e:
            return None, f"Erreur globale: {str(e)}"


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
    """Calculate signal score (0-100) and level."""
    score = 0
    
    # Volume 24h (0-30 points)
    vol_24h = market.get("volume24hr", 0) or 0
    if vol_24h > 100000:
        score += 30
    elif vol_24h > 50000:
        score += 25
    elif vol_24h > 10000:
        score += 20
    elif vol_24h > 1000:
        score += 10
    
    # Liquidity (0-25 points)
    liquidity = market.get("liquidityNum", 0) or 0
    if liquidity > 500000:
        score += 25
    elif liquidity > 100000:
        score += 20
    elif liquidity > 50000:
        score += 15
    elif liquidity > 10000:
        score += 10
    
    # Price movement (0-25 points)
    price_change = abs(market.get("oneDayPriceChange", 0) or 0)
    if price_change > 20:
        score += 25
    elif price_change > 10:
        score += 20
    elif price_change > 5:
        score += 15
    elif price_change > 2:
        score += 10
    
    # Weekly activity (0-20 points)
    vol_1wk = market.get("volume1wk", 0) or 0
    if vol_1wk > 500000:
        score += 20
    elif vol_1wk > 100000:
        score += 15
    elif vol_1wk > 50000:
        score += 10
    
    # Level
    if score >= 75:
        level = "opportunity"
    elif score >= 60:
        level = "strong"
    elif score >= 40:
        level = "interesting"
    else:
        level = "watch"
    
    return score, level


def parse_prices(market: dict) -> tuple[float, float]:
    """Parse YES/NO prices."""
    try:
        prices_str = market.get("outcomePrices", '["0.5", "0.5"]')
        if isinstance(prices_str, str):
            prices = json.loads(prices_str)
        else:
            prices = prices_str
        return float(prices[0]), float(prices[1])
    except:
        return 0.5, 0.5


def market_to_signal(market: dict) -> Signal:
    """Convert Polymarket market to Signal."""
    score, level = calculate_score(market)
    yes_price, no_price = parse_prices(market)
    
    # Direction based on momentum
    price_change = market.get("oneDayPriceChange", 0) or 0
    direction = "YES" if price_change > 0 or yes_price > 0.5 else "NO"
    
    # Get slug
    slug = market.get("slug", "")
    if not slug and market.get("events"):
        slug = market["events"][0].get("slug", "")
    
    # Generate URL
    if slug:
        polymarket_url = f"https://polymarket.com/event/{slug}"
    else:
        polymarket_url = "https://polymarket.com"

    vol_24h = market.get("volume24hr", 0) or 0
    liquidity = market.get("liquidityNum", 0) or 0
    
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
        whale_count=max(1, int(vol_24h / 10000)),
        volume_24h=vol_24h,
        news_count=0,
        yes_price=yes_price,
        no_price=no_price,
        price_movement=price_change,
        liquidity=liquidity,
        end_date=market.get("endDateIso", ""),
        polymarket_url=polymarket_url,
        created_at=datetime.utcnow()
    )


@router.get("/", response_model=SignalResponse)
async def get_signals(
    min_score: int = Query(default=0, ge=0, le=100),
    min_volume: float = Query(default=0, ge=0),
    min_liquidity: float = Query(default=0, ge=0),
    level: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200)
):
    """
    Get signals from Polymarket with caching.
    
    When API is down, returns cached data with age indicator.
    """
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


@router.get("/equilibrage", response_model=SignalResponse)
async def get_equilibrage_signals(
    limit: int = Query(default=100, le=500)
):
    """
    Get 'Equilibrage' signals:
    - YES price between 0.45 and 0.55
    - Sorted by volume
    """
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
            # We strictly check both yes_price and no_price to be safe, 
            # though usually if yes is 0.45, no is 0.55.
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


@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    return cache.get_stats()


@router.post("/cache/clear")
async def clear_cache():
    """Clear all cache."""
    cache.clear()
    return {"message": "Cache cleared"}
