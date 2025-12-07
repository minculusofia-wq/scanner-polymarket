"""
Monte Carlo Calculator for Polymarket opportunities.

Calculates edge between Monte Carlo probabilities and Polymarket prices.
"""
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from app.services.monte_carlo.binance_data import get_binance_ohlcv
from app.services.monte_carlo.yahoo_data import get_yahoo_ohlcv
from app.services.monte_carlo.sentiment import get_crypto_fear_and_greed
from app.services.monte_carlo.tradfi_sentiment import get_tradfi_sentiment
from app.services.monte_carlo.macro import check_high_impact_events
from app.services.monte_carlo.bootstrap_model import BootstrapOptionModel
from app.core.cache import cache


# Cache key for OHLCV data
CACHE_KEY_OHLCV = "binance_ohlcv_{symbol}_{interval}"
CACHE_TTL = 3600  # 1 hour


import asyncio
from concurrent.futures import ProcessPoolExecutor

# Helper function for serialization (must be top-level)
def run_simulation_task(model, end_date, noise_multiplier):
    return model.simulate(end_date, noise_multiplier=noise_multiplier)


@dataclass
class EdgeOpportunity:
    """Represents an edge opportunity on Polymarket."""
    market_id: str
    market_question: str
    slug: str
    
    # Prices
    polymarket_yes_price: float
    polymarket_no_price: float
    
    # Monte Carlo results
    mc_probability: float
    mc_confidence_low: float
    mc_confidence_high: float
    
    # Edge calculation
    edge: float  # mc_probability - polymarket_yes_price
    edge_percent: float
    
    # Recommendation
    recommendation: str  # BUY_YES, BUY_NO, HOLD
    confidence: str  # HIGH, MEDIUM, LOW
    
    # Metadata
    asset: str
    target_price: float
    end_date: str
    current_price: float
    
    # Sentiment
    sentiment_score: Optional[float] = None  # 0-100
    sentiment_label: Optional[str] = None    # "Extreme Fear", etc.

    def to_dict(self) -> dict:
        return {
            "market_id": self.market_id,
            "market_question": self.market_question,
            "slug": self.slug,
            "polymarket_yes_price": self.polymarket_yes_price,
            "polymarket_no_price": self.polymarket_no_price,
            "mc_probability": self.mc_probability,
            "mc_confidence_low": self.mc_confidence_low,
            "mc_confidence_high": self.mc_confidence_high,
            "edge": self.edge,
            "edge_percent": self.edge_percent,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "asset": self.asset,
            "target_price": self.target_price,
            "end_date": self.end_date,
            "current_price": self.current_price,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
        }


class MonteCarloCalculator:
    """
    Calculator for Monte Carlo probabilities on Polymarket markets.
    """
    
    # Patterns to detect crypto price markets
    # Match patterns like: "Bitcoin reach $150,000", "Ethereum hit $8,000", "BTC $100k"
    CRYPTO_PATTERNS = {
        "BTC": [
            r"bitcoin.*?\$\s*([\d,]+)",  # "Bitcoin reach $150,000"
            r"bitcoin.*?reach.*?([\d,]+)",
            r"bitcoin.*?hit.*?([\d,]+)",
            r"btc.*?\$\s*([\d,]+)",
        ],
        "ETH": [
            r"ethereum.*?\$\s*([\d,]+)",  # "Ethereum hit $8,000"
            r"ethereum.*?reach.*?([\d,]+)",
            r"ethereum.*?hit.*?([\d,]+)",
            r"eth.*?\$\s*([\d,]+)",
        ],
        "SOL": [
            r"solana.*?\$\s*([\d,]+)",
            r"solana.*?reach.*?([\d,]+)",
            r"solana.*?hit.*?([\d,]+)",
        ],
    }

    TRADFI_PATTERNS = {
        "SPX": [
            r"s\&p\s*500.*?\s*([\d,]+)",
            r"spx.*?\s*([\d,]+)",
            r"spy.*?\s*([\d,]+)",
        ],
        "NDX": [
            r"nasdaq.*?\s*([\d,]+)",
            r"ndx.*?\s*([\d,]+)",
            r"qqq.*?\s*([\d,]+)",
        ],
        "GOLD": [
            r"gold.*?\s*([\d,]+)",
            r"xau.*?\s*([\d,]+)",
        ],
        "OIL": [
            r"crude.*?\s*([\d,]+)",
            r"oil.*?\s*([\d,]+)",
            r"wti.*?\s*([\d,]+)",
            r"brent.*?\s*([\d,]+)",
        ],
    }
    
    ASSET_TO_SYMBOL = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "SOL": "SOLUSDT",
        "SPX": "^GSPC",
        "NDX": "^IXIC",
        "GOLD": "GC=F",
        "OIL": "CL=F",
    }
    
    
    def __init__(self, n_sims: int = 50_000):
        """
        Initialize calculator.
        
        Args:
            n_sims: Number of Monte Carlo simulations (lower = faster)
        """
        self.n_sims = n_sims
        self._models: Dict[str, BootstrapOptionModel] = {}
        # Max workers = None usually defaults to cpu_count()
        self.executor = ProcessPoolExecutor(max_workers=None)
    
    def shutdown(self):
        """Shutdown the process pool."""
        self.executor.shutdown(wait=True)

    def __del__(self):
        self.shutdown()

    def _parse_market_question(self, question: str) -> Optional[Tuple[str, float, str]]:
        """
        Parse a market question to extract asset, target price, and direction.
        
        Args:
            question: Market question (e.g., "Will Bitcoin hit $150k by March 2025?")
            
        Returns:
            Tuple of (asset, target_price, direction) or None if not parseable
        """
        question_lower = question.lower()
        # print(f"[MC] Parsing question: {question_lower[:80]}...")
        
        # Determine direction based on keywords
        if "dip" in question_lower or "fall" in question_lower or "drop" in question_lower:
            direction = "below"
        else:
            direction = "above"
        
        # Check for each asset
        for asset, patterns in self.CRYPTO_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, question_lower)
                if match:
                    # Extract price
                    price_str = match.group(1).replace(",", "")
                    # print(f"[MC] Found match for {asset}: {price_str} (direction: {direction})")
                    try:
                        price = float(price_str)
                        return (asset, price, direction)
                    except ValueError:
                        continue
        
        # Check for TradFi assets
        for asset, patterns in self.TRADFI_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, question_lower)
                if match:
                    price_str = match.group(1).replace(",", "")
                    # print(f"[MC] Found match for {asset}: {price_str} (direction: {direction})")
                    try:
                        price = float(price_str)
                        return (asset, price, direction)
                    except ValueError:
                        continue

        # print(f"[MC] No crypto or tradfi pattern matched")
        return None
    
    def _extract_end_date(self, question: str, end_date_iso: str) -> str:
        """Extract or format end date for simulation."""
        # Try to use the ISO date from market
        if end_date_iso:
            try:
                # Parse ISO format
                if "T" in end_date_iso:
                    dt = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
                else:
                    dt = datetime.strptime(end_date_iso, "%Y-%m-%d")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
        
        # Default: end of current year
        return f"{datetime.now().year}-12-31 23:59:59"
    
    async def get_or_create_model(self, symbol: str) -> BootstrapOptionModel:
        """Get cached model or create new one."""
        if symbol in self._models:
            return self._models[symbol]
        
        # Fetch OHLCV data
        cache_key = CACHE_KEY_OHLCV.format(symbol=symbol, interval="1h")
        cached_df = cache.get(cache_key, max_age_seconds=CACHE_TTL)
        
        if cached_df is not None:
            import pandas as pd
            df = pd.DataFrame(cached_df)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
        else:
            # Convert Binance symbols to Yahoo symbols
            # BTCUSDT -> BTC-USD, ETHUSDT -> ETH-USD, etc.
            yahoo_symbol = symbol
            if "USDT" in symbol:
                yahoo_symbol = symbol.replace("USDT", "-USD")
            
            print(f"Fetching {yahoo_symbol} from Yahoo Finance...")
            loop = asyncio.get_event_loop()
            try:
                df = await loop.run_in_executor(None, get_yahoo_ohlcv, yahoo_symbol, "1h", "2y")
            except Exception as e:
                print(f"Yahoo fetch failed for {yahoo_symbol}: {e}")
                # Try daily data as fallback
                try:
                    df = await loop.run_in_executor(None, get_yahoo_ohlcv, yahoo_symbol, "1d", "2y")
                except Exception as e2:
                    print(f"Yahoo daily fetch also failed: {e2}")
                    raise ValueError(f"Cannot fetch data for {symbol}")

            # Cache as dict for JSON serialization - convert timestamps to strings
            cache_data = df.reset_index().copy()
            cache_data['date'] = cache_data['date'].astype(str)
            cache.set(cache_key, cache_data.to_dict(orient="records"))
        
        # Create model
        model = BootstrapOptionModel(df, n_sims=self.n_sims)
        self._models[symbol] = model
        
        return model
    
    async def calculate_probability(
        self,
        asset: str,
        target_price: float,
        end_date: str,
        direction: str = "above",
    ) -> Dict[str, Any]:
        """
        Calculate Monte Carlo probability for a price target.
        
        Args:
            asset: Asset code (BTC, ETH, SOL)
            target_price: Target price level
            end_date: End date for simulation
            direction: "above" (hit/reach) or "below" (dip/fall)
            
        Returns:
            Dict with probability and metadata
        """
        symbol = self.ASSET_TO_SYMBOL.get(asset)
        if not symbol:
            raise ValueError(f"Unknown asset: {asset}")
        
        model = await self.get_or_create_model(symbol)
        
        # Check for High Impact Macro Events (Finnhub)
        # Boost noise_std if big events are coming
        macro_mult = 1.0
        try:
            macro_mult = await check_high_impact_events(days_ahead=7)
        except Exception:
            pass
            
        # Run simulation with macro adjustment using ProcessPoolExecutor
        loop = asyncio.get_event_loop()
        # Non-blocking simulation on separate process
        result = await loop.run_in_executor(
            self.executor, 
            run_simulation_task, 
            model, 
            end_date, 
            macro_mult
        )
        
        # Calculate probability based on direction
        if direction == "below":
            probability = result.probability_below(target_price)
        else:
            probability = result.probability_above(target_price)
        
        # Simplified confidence interval (±3% estimate)
        conf_low = max(0.0, probability - 0.03)
        conf_high = min(1.0, probability + 0.03)
        
        return {
            "asset": asset,
            "symbol": symbol,
            "current_price": model.S0,
            "target_price": target_price,
            "end_date": end_date,
            "probability": probability,
            "confidence_low": conf_low,
            "confidence_high": conf_high,
            "n_simulations": self.n_sims,
            "percentiles": result.get_percentiles(),
            "direction": direction,
        }
    
    async def calculate_edge(
        self,
        market: Dict[str, Any],
    ) -> Optional[EdgeOpportunity]:
        """
        Calculate edge for a Polymarket market.
        
        Args:
            market: Market dict with question, yes_price, end_date, etc.
            
        Returns:
            EdgeOpportunity or None if market is not a crypto price market
        """
        question = market.get("market_question") or market.get("question", "")
        
        # Parse market question
        parsed = self._parse_market_question(question)
        if not parsed:
            return None  # Not a crypto price market
        
        asset, target_price, direction = parsed
        
        # Get end date
        end_date = self._extract_end_date(
            question,
            market.get("end_date") or market.get("endDateIso", "")
        )
        
        try:
            # Calculate MC probability based on direction
            mc_result = await self.calculate_probability(asset, target_price, end_date, direction)
        except Exception as e:
            # print(f"Error calculating MC for {question}: {e}")
            return None
        
        mc_prob = mc_result["probability"]
        yes_price = market.get("yes_price", 0.5)
        no_price = market.get("no_price", 0.5)
        
        # Calculate edge
        edge = mc_prob - yes_price
        edge_percent = edge * 100
        
        # Determine recommendation
        if edge > 0.05:
            recommendation = "BUY_YES"
            confidence = "HIGH" if edge > 0.10 else "MEDIUM"
        elif edge < -0.05:
            recommendation = "BUY_NO"
            confidence = "HIGH" if edge < -0.10 else "MEDIUM"
        else:
            recommendation = "HOLD"
            confidence = "LOW"
            
        # Fetch sentiment
        sentiment_score = None
        sentiment_label = None
        
        # Crypto
        if asset in ["BTC", "ETH", "SOL"]:
            sentiment_data = await get_crypto_fear_and_greed()
            sentiment_score = sentiment_data.get("score")
            sentiment_label = sentiment_data.get("value_classification")
        # TradFi
        elif asset in ["SPX", "NDX", "GOLD", "OIL"]:
            sym = self.ASSET_TO_SYMBOL.get(asset, "")
            # Alpha Vantage expects tickers like SPY, GLD, USO not futures
            # Mapping for AV Sentiment
            av_ticker = sym
            if asset == "SPX": av_ticker = "SPY"
            if asset == "NDX": av_ticker = "QQQ"
            if asset == "GOLD": av_ticker = "GLD"
            if asset == "OIL": av_ticker = "USO"
            
            sentiment_data = await get_tradfi_sentiment(av_ticker)
            sentiment_score = sentiment_data.get("score")
            sentiment_label = sentiment_data.get("label")
        
        return EdgeOpportunity(
            market_id=market.get("id", market.get("market_id", "")),
            market_question=question,
            slug=market.get("slug", ""),
            polymarket_yes_price=yes_price,
            polymarket_no_price=no_price,
            mc_probability=mc_prob,
            mc_confidence_low=mc_result["confidence_low"],
            mc_confidence_high=mc_result["confidence_high"],
            edge=edge,
            edge_percent=edge_percent,
            recommendation=recommendation,
            confidence=confidence,
            asset=asset,
            target_price=target_price,
            end_date=end_date,
            current_price=mc_result["current_price"],
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
        )


# Singleton instance - reduced simulations for speed
mc_calculator = MonteCarloCalculator(n_sims=10_000)
