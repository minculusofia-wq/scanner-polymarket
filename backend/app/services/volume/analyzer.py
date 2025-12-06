"""
Volume Analysis Service.

Analyzes trading volume to detect spikes and unusual activity.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from collections import defaultdict
import statistics

from app.core.config import settings
from app.services.polymarket.client import polymarket_client


@dataclass
class VolumeData:
    """Volume analysis data for a market."""
    market_id: str
    market_question: str
    current_volume: float
    avg_volume: float
    volume_ratio: float
    is_spike: bool
    direction_bias: str     # YES, NO, or NEUTRAL
    direction_pct: float
    timestamp: datetime


@dataclass
class VolumeAlert:
    """Alert for unusual volume activity."""
    id: str
    market_id: str
    market_question: str
    alert_type: str         # spike, unusual, trending
    volume_change_pct: float
    direction: str
    created_at: datetime


class VolumeAnalyzer:
    """
    Service for analyzing trading volume.
    
    Detects:
    - Volume spikes (sudden increase)
    - Unusual volume (sustained high volume)
    - Direction bias (more buying vs selling)
    """
    
    def __init__(self):
        self.spike_threshold = settings.volume_spike_threshold
        self.avg_window_days = settings.volume_avg_window_days
        self.unusual_multiplier = settings.unusual_volume_multiplier
        
        # Volume history cache: market_id -> list of (timestamp, volume)
        self._volume_history: Dict[str, List[tuple]] = defaultdict(list)
        
        # Recent alerts
        self._alerts: List[VolumeAlert] = []
    
    async def analyze_all_markets(self) -> List[VolumeData]:
        """
        Analyze volume for all active markets.
        
        Returns:
            List of volume analysis data
        """
        markets = await polymarket_client.get_markets(limit=100, active=True)
        results = []
        
        for market in markets:
            try:
                analysis = await self.analyze_market(market)
                if analysis:
                    results.append(analysis)
            except Exception as e:
                print(f"Error analyzing market {market.get('id')}: {e}")
        
        # Sort by volume ratio (highest first)
        results.sort(key=lambda x: x.volume_ratio, reverse=True)
        
        return results
    
    async def analyze_market(self, market: Dict[str, Any]) -> Optional[VolumeData]:
        """
        Analyze volume for a specific market.
        
        Args:
            market: Market data from API
            
        Returns:
            VolumeData analysis or None
        """
        market_id = market.get("id", "")
        question = market.get("question", "Unknown")
        
        # Get current volume
        current_volume = float(market.get("volume", 0))
        if current_volume == 0:
            return None
        
        # Update history
        now = datetime.now(timezone.utc)
        self._volume_history[market_id].append((now, current_volume))
        
        # Keep only last 7 days of history
        cutoff = now - timedelta(days=self.avg_window_days)
        self._volume_history[market_id] = [
            (ts, vol) for ts, vol in self._volume_history[market_id]
            if ts >= cutoff
        ]
        
        # Calculate average volume
        history = self._volume_history[market_id]
        if len(history) < 2:
            avg_volume = current_volume
        else:
            volumes = [vol for _, vol in history[:-1]]  # Exclude current
            avg_volume = statistics.mean(volumes) if volumes else current_volume
        
        # Calculate volume ratio
        volume_ratio = (current_volume / avg_volume * 100) if avg_volume > 0 else 100
        
        # Detect spike
        is_spike = volume_ratio >= self.spike_threshold
        
        # Analyze direction bias (simplified - would need order book data)
        direction_bias, direction_pct = await self._analyze_direction(market)
        
        # Create alert if spike detected
        if is_spike:
            self._create_alert(
                market_id=market_id,
                question=question,
                alert_type="spike",
                change_pct=volume_ratio - 100,
                direction=direction_bias
            )
        
        return VolumeData(
            market_id=market_id,
            market_question=question,
            current_volume=current_volume,
            avg_volume=avg_volume,
            volume_ratio=volume_ratio,
            is_spike=is_spike,
            direction_bias=direction_bias,
            direction_pct=direction_pct,
            timestamp=now
        )
    
    async def _analyze_direction(
        self,
        market: Dict[str, Any]
    ) -> tuple[str, float]:
        """
        Analyze the direction bias of trading.
        
        Returns:
            Tuple of (direction, percentage)
        """
        # Get prices to infer direction
        yes_price = float(market.get("outcomePrices", [0.5, 0.5])[0])
        
        # Simple heuristic: if YES price > 0.55, bias is YES
        # In production, would analyze order flow
        if yes_price > 0.55:
            return "YES", yes_price * 100
        elif yes_price < 0.45:
            return "NO", (1 - yes_price) * 100
        else:
            return "NEUTRAL", 50.0
    
    def _create_alert(
        self,
        market_id: str,
        question: str,
        alert_type: str,
        change_pct: float,
        direction: str
    ):
        """Create a volume alert."""
        alert = VolumeAlert(
            id=f"{market_id}_{datetime.now(timezone.utc).timestamp()}",
            market_id=market_id,
            market_question=question,
            alert_type=alert_type,
            volume_change_pct=change_pct,
            direction=direction,
            created_at=datetime.now(timezone.utc)
        )
        self._alerts.append(alert)
        
        # Keep only last 100 alerts
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]
        
        print(f"📈 Volume Alert: {question[:50]}... | {alert_type} | +{change_pct:.0f}%")
    
    def get_volume_spikes(
        self,
        min_change: float = None
    ) -> List[VolumeData]:
        """
        Get markets with volume spikes.
        
        Args:
            min_change: Minimum percentage change
            
        Returns:
            List of volume data for spiking markets
        """
        min_change = min_change or self.spike_threshold
        
        # This would query the analyzed data
        # For now, return empty (would be populated by analyze_all_markets)
        return []
    
    def get_alerts(self, limit: int = 20) -> List[VolumeAlert]:
        """Get recent volume alerts."""
        return self._alerts[-limit:][::-1]
    
    def get_market_volume_score(self, market_id: str) -> int:
        """
        Calculate a volume score (0-100) for a market.
        
        Used for signal combination.
        """
        history = self._volume_history.get(market_id, [])
        
        if len(history) < 2:
            return 0
        
        current = history[-1][1]
        previous = [vol for _, vol in history[:-1]]
        avg = statistics.mean(previous) if previous else current
        
        ratio = current / avg if avg > 0 else 1
        
        # Score based on ratio
        if ratio >= 3.0:
            return 100
        elif ratio >= 2.5:
            return 85
        elif ratio >= 2.0:
            return 70
        elif ratio >= 1.5:
            return 50
        elif ratio >= 1.2:
            return 30
        else:
            return 10


# Singleton instance
volume_analyzer = VolumeAnalyzer()
