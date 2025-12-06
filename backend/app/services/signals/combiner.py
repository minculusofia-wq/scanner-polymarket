"""
Signal Combiner Service.

Combines signals from whale detection, volume analysis, and news to generate
trading opportunity signals.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings
from app.services.whale.detector import whale_detector
from app.services.volume.analyzer import volume_analyzer
from app.services.news.aggregator import news_aggregator


class SignalLevel(Enum):
    """Signal strength levels."""
    WATCH = "watch"               # 40-60
    INTERESTING = "interesting"   # 60-75
    STRONG = "strong"             # 75-90
    OPPORTUNITY = "opportunity"   # 90+


@dataclass
class Signal:
    """A trading signal combining multiple data sources."""
    id: str
    market_id: str
    market_question: str
    score: int              # 0-100
    level: SignalLevel
    direction: str          # YES or NO
    whale_score: int
    volume_score: int
    news_score: int
    price_movement: float
    reasons: List[str]
    created_at: datetime


class SignalCombiner:
    """
    Service for combining signals from multiple sources.
    
    Weights (configurable):
    - Whale activity: 30%
    - Volume analysis: 30%
    - News sentiment: 20%
    - Price movement: 20%
    """
    
    def __init__(self):
        self.weight_whale = settings.signal_weight_whale
        self.weight_volume = settings.signal_weight_volume
        self.weight_news = settings.signal_weight_news
        self.weight_price = settings.signal_weight_price
        self.alert_threshold = settings.signal_alert_threshold
        
        # Generated signals
        self._signals: List[Signal] = []
    
    async def generate_signals(self) -> List[Signal]:
        """
        Generate signals for all active markets.
        
        Returns:
            List of signals sorted by score
        """
        from app.services.polymarket.client import polymarket_client
        
        markets = await polymarket_client.get_markets(limit=100, active=True)
        signals = []
        
        for market in markets:
            try:
                signal = await self._analyze_market(market)
                if signal and signal.score >= 4:  # Minimum threshold for WATCH
                    signals.append(signal)
                    self._signals.append(signal)
            except Exception as e:
                print(f"Error analyzing market for signals: {e}")
        
        # Keep only last 500 signals
        if len(self._signals) > 500:
            self._signals = self._signals[-500:]
        
        # Sort by score
        signals.sort(key=lambda x: x.score, reverse=True)
        
        return signals
    
    async def _analyze_market(self, market: Dict[str, Any]) -> Optional[Signal]:
        """
        Analyze a single market and generate a signal.
        
        Args:
            market: Market data
            
        Returns:
            Signal if significant, None otherwise
        """
        market_id = market.get("id", "")
        question = market.get("question", "Unknown")
        
        # Get whale score
        whale_trades = whale_detector.get_recent_trades(hours=24)
        market_whale_trades = [t for t in whale_trades if t.market_id == market_id]
        whale_score = self._calculate_whale_score(market_whale_trades)
        
        # Get volume score
        volume_score = volume_analyzer.get_market_volume_score(market_id)
        
        # Get news score
        news_score = news_aggregator.get_news_score(question)
        
        # Calculate price movement score
        price_score, price_movement = await self._calculate_price_score(market)
        
        # Combine scores with weights
        total_score = (
            whale_score * (self.weight_whale / 100) +
            volume_score * (self.weight_volume / 100) +
            news_score * (self.weight_news / 100) +
            price_score * (self.weight_price / 100)
        )
        
        total_score = int(min(total_score, 100))
        final_score = round(total_score / 10)
        
        # Determine level
        level = self._get_level(final_score)
        
        # Determine direction
        direction = self._determine_direction(
            market_whale_trades,
            market,
            news_score
        )
        
        # Generate reasons
        reasons = self._generate_reasons(
            whale_score, volume_score, news_score, price_movement
        )
        
        return Signal(
            id=f"{market_id}_{datetime.now(timezone.utc).timestamp()}",
            market_id=market_id,
            market_question=question,
            score=final_score,
            level=level,
            direction=direction,
            whale_score=whale_score,
            volume_score=volume_score,
            news_score=news_score,
            price_movement=price_movement,
            reasons=reasons,
            created_at=datetime.now(timezone.utc)
        )
    
    def _calculate_whale_score(self, trades: List) -> int:
        """Calculate whale score from trades."""
        if not trades:
            return 0
        
        total_volume = sum(t.size_usd for t in trades)
        
        if total_volume >= 500000:
            return 100
        elif total_volume >= 200000:
            return 80
        elif total_volume >= 100000:
            return 60
        elif total_volume >= 50000:
            return 40
        elif total_volume >= 10000:
            return 20
        else:
            return 10
    
    async def _calculate_price_score(
        self,
        market: Dict[str, Any]
    ) -> tuple[int, float]:
        """Calculate price movement score."""
        try:
            price_change = float(market.get("price24HourChange", 0))
        except (ValueError, TypeError):
            price_change = 0
        
        abs_change = abs(price_change)
        
        if abs_change >= 20:
            score = 100
        elif abs_change >= 15:
            score = 80
        elif abs_change >= 10:
            score = 60
        elif abs_change >= 5:
            score = 40
        else:
            score = 20
        
        return score, price_change
    
    def _get_level(self, score: int) -> SignalLevel:
        """Determine signal level from score."""
        if score >= 9:
            return SignalLevel.OPPORTUNITY
        elif score >= 7:
            return SignalLevel.STRONG
        elif score >= 6:
            return SignalLevel.INTERESTING
        else:
            return SignalLevel.WATCH
    
    def _determine_direction(
        self,
        whale_trades: List,
        market: Dict[str, Any],
        news_score: int
    ) -> str:
        """Determine the likely direction (YES or NO)."""
        yes_votes = 0
        no_votes = 0
        
        # Whale direction
        for trade in whale_trades:
            if trade.side == "YES":
                yes_votes += trade.size_usd
            else:
                no_votes += trade.size_usd
        
        # Price direction
        try:
            yes_price = float(market.get("outcomePrices", [0.5, 0.5])[0])
            if yes_price > 0.5:
                yes_votes += 10000
            else:
                no_votes += 10000
        except Exception:
            pass
        
        # News direction
        if news_score > 60:
            yes_votes += 5000
        elif news_score < 40:
            no_votes += 5000
        
        return "YES" if yes_votes >= no_votes else "NO"
    
    def _generate_reasons(
        self,
        whale_score: int,
        volume_score: int,
        news_score: int,
        price_movement: float
    ) -> List[str]:
        """Generate human-readable reasons for the signal."""
        reasons = []
        
        if whale_score >= 60:
            reasons.append(f"🐋 High whale activity (score: {whale_score})")
        elif whale_score >= 40:
            reasons.append(f"🐋 Moderate whale activity (score: {whale_score})")
        
        if volume_score >= 60:
            reasons.append(f"📈 Volume spike detected (score: {volume_score})")
        
        if news_score > 60:
            reasons.append(f"📰 Positive news sentiment (score: {news_score})")
        elif news_score < 40:
            reasons.append(f"📰 Negative news sentiment (score: {news_score})")
        
        if abs(price_movement) >= 10:
            direction = "up" if price_movement > 0 else "down"
            reasons.append(f"💹 Price {direction} {abs(price_movement):.1f}% 24h")
        
        return reasons
    
    def get_signals(
        self,
        min_score: int = 4,
        level: Optional[SignalLevel] = None,
        limit: int = 20
    ) -> List[Signal]:
        """Get filtered signals."""
        filtered = [s for s in self._signals if s.score >= min_score]
        
        if level:
            filtered = [s for s in filtered if s.level == level]
        
        # Sort by score and return most recent
        filtered.sort(key=lambda x: (x.score, x.created_at), reverse=True)
        
        return filtered[:limit]
    
    def get_top_signals(self, limit: int = 5) -> List[Signal]:
        """Get top signals by score."""
        return self.get_signals(min_score=7, limit=limit)


# Singleton instance
signal_combiner = SignalCombiner()
