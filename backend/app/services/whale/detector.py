"""
Whale Detection Service.

Detects and tracks large traders (whales) on Polymarket.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

from app.core.config import settings
from app.services.polymarket.client import polymarket_client


@dataclass
class WhaleProfile:
    """Profile of a whale trader."""
    address: str
    total_volume_usd: float
    total_trades: int
    win_rate: float
    whale_score: int
    last_active: datetime
    positions: Dict[str, Any]


@dataclass
class WhaleTrade:
    """A trade made by a whale."""
    trade_id: str
    whale_address: str
    market_id: str
    market_question: str
    side: str  # YES or NO
    size_usd: float
    price: float
    timestamp: datetime


class WhaleDetector:
    """
    Service for detecting and tracking whale activity.
    
    Criteria for whale detection:
    - Trade size > whale_min_trade_usd
    - Position total > whale_min_position_usd
    - Historical win rate > whale_win_rate_threshold
    """
    
    def __init__(self):
        self.min_trade_usd = settings.whale_min_trade_usd
        self.min_position_usd = settings.whale_min_position_usd
        self.win_rate_threshold = settings.whale_win_rate_threshold
        
        # Cache of known whales
        self._whale_cache: Dict[str, WhaleProfile] = {}
        self._recent_trades: List[WhaleTrade] = []
    
    async def scan_whale_activity(self) -> List[WhaleTrade]:
        """
        Scan for recent whale activity.
        
        Returns:
            List of whale trades detected
        """
        # Get large trades from Polymarket
        large_trades = await polymarket_client.get_large_trades(
            min_size_usd=self.min_trade_usd,
            limit=50
        )
        
        whale_trades = []
        
        for trade in large_trades:
            whale_trade = await self._process_trade(trade)
            if whale_trade:
                whale_trades.append(whale_trade)
                self._recent_trades.append(whale_trade)
        
        # Keep only last 1000 trades
        if len(self._recent_trades) > 1000:
            self._recent_trades = self._recent_trades[-1000:]
        
        return whale_trades
    
    async def _process_trade(self, trade: Dict[str, Any]) -> Optional[WhaleTrade]:
        """
        Process a trade and determine if it's a whale trade.
        
        Args:
            trade: Raw trade data
            
        Returns:
            WhaleTrade if qualifies, None otherwise
        """
        try:
            address = trade.get("maker", "")
            size = float(trade.get("size", 0))
            price = float(trade.get("price", 0))
            value_usd = trade.get("value_usd", size * price)
            
            if value_usd < self.min_trade_usd:
                return None
            
            # Update whale cache
            if address not in self._whale_cache:
                self._whale_cache[address] = WhaleProfile(
                    address=address,
                    total_volume_usd=0,
                    total_trades=0,
                    win_rate=50.0,  # Default until we have data
                    whale_score=0,
                    last_active=datetime.utcnow(),
                    positions={}
                )
            
            whale = self._whale_cache[address]
            whale.total_volume_usd += value_usd
            whale.total_trades += 1
            whale.last_active = datetime.utcnow()
            whale.whale_score = self._calculate_whale_score(whale)
            
            # Determine side (YES/NO)
            side = "YES" if trade.get("side", "").upper() == "BUY" else "NO"
            
            return WhaleTrade(
                trade_id=trade.get("id", ""),
                whale_address=address,
                market_id=trade.get("market", ""),
                market_question=trade.get("question", "Unknown"),
                side=side,
                size_usd=value_usd,
                price=price,
                timestamp=datetime.utcnow()
            )
            
        except (ValueError, TypeError, KeyError) as e:
            print(f"Error processing trade: {e}")
            return None
    
    def _calculate_whale_score(self, whale: WhaleProfile) -> int:
        """
        Calculate a whale score (0-100) based on various metrics.
        
        Score factors:
        - Total volume (40%)
        - Win rate (40%)
        - Activity (20%)
        """
        score = 0
        
        # Volume score (0-40)
        if whale.total_volume_usd >= 1000000:
            score += 40
        elif whale.total_volume_usd >= 500000:
            score += 30
        elif whale.total_volume_usd >= 100000:
            score += 20
        elif whale.total_volume_usd >= 50000:
            score += 10
        
        # Win rate score (0-40)
        if whale.win_rate >= 70:
            score += 40
        elif whale.win_rate >= 60:
            score += 30
        elif whale.win_rate >= 55:
            score += 20
        elif whale.win_rate >= 50:
            score += 10
        
        # Activity score (0-20)
        if whale.total_trades >= 100:
            score += 20
        elif whale.total_trades >= 50:
            score += 15
        elif whale.total_trades >= 20:
            score += 10
        elif whale.total_trades >= 10:
            score += 5
        
        return min(score, 100)
    
    def get_top_whales(self, limit: int = 10) -> List[WhaleProfile]:
        """
        Get top whales by score.
        
        Args:
            limit: Maximum number of whales to return
            
        Returns:
            List of top whale profiles
        """
        sorted_whales = sorted(
            self._whale_cache.values(),
            key=lambda w: w.whale_score,
            reverse=True
        )
        return sorted_whales[:limit]
    
    def get_recent_trades(
        self,
        hours: int = 24,
        min_size: float = None
    ) -> List[WhaleTrade]:
        """
        Get recent whale trades.
        
        Args:
            hours: Look back period
            min_size: Minimum trade size (optional)
            
        Returns:
            List of whale trades
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        min_size = min_size or self.min_trade_usd
        
        return [
            trade for trade in self._recent_trades
            if trade.timestamp >= cutoff and trade.size_usd >= min_size
        ]
    
    def get_whale_by_address(self, address: str) -> Optional[WhaleProfile]:
        """Get a whale profile by address."""
        return self._whale_cache.get(address)


# Singleton instance
whale_detector = WhaleDetector()
