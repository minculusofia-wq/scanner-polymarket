"""
Whale Tracker Service - Detect and track large traders on Polymarket.
"""
import httpx
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

from app.core.cache import cache
from app.core.database import db


@dataclass
class WhaleTrade:
    """A large trade by a whale."""
    id: str
    trader: str
    market_id: str
    market_question: str
    slug: str
    side: str  # YES or NO
    size_usd: float
    price: float
    timestamp: datetime
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass 
class WhaleProfile:
    """Profile of a whale trader."""
    address: str
    total_volume: float
    trade_count: int
    avg_trade_size: float
    favorite_side: str  # YES or NO
    markets_traded: int
    last_seen: datetime
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['last_seen'] = self.last_seen.isoformat()
        return d


# Minimum trade size to be considered a whale (in USD)
WHALE_MIN_TRADE_USD = 10000

# Cache keys
CACHE_KEY_TRADES = "whale_trades"
CACHE_KEY_PROFILES = "whale_profiles"


class WhaleTracker:
    """
    Tracks whale activity on Polymarket.
    
    Features:
    - Detect large trades (>$10k)
    - Track whale addresses and their patterns
    - Store recent whale activity
    """
    
    def __init__(self):
        self._trades: List[WhaleTrade] = []
        self._profiles: Dict[str, WhaleProfile] = {}
        self._load_from_cache()
    
    def _load_from_cache(self):
        """Load saved data from cache."""
        cached_trades = cache.get_fallback(CACHE_KEY_TRADES)
        if cached_trades:
            self._trades = []
            for t in cached_trades:
                try:
                    t['timestamp'] = datetime.fromisoformat(t['timestamp'])
                    self._trades.append(WhaleTrade(**t))
                except:
                    pass
        
        cached_profiles = cache.get_fallback(CACHE_KEY_PROFILES)
        if cached_profiles:
            self._profiles = {}
            for addr, p in cached_profiles.items():
                try:
                    p['last_seen'] = datetime.fromisoformat(p['last_seen'])
                    self._profiles[addr] = WhaleProfile(**p)
                except:
                    pass
    
    def _save_to_cache(self):
        """Save data to cache."""
        cache.set(CACHE_KEY_TRADES, [t.to_dict() for t in self._trades[-100:]])  # Keep last 100
        cache.set(CACHE_KEY_PROFILES, {k: v.to_dict() for k, v in self._profiles.items()})
    
    async def fetch_recent_trades(self, market_id: str = None) -> List[Dict]:
        """
        Fetch recent trades from Polymarket CLOB API.
        
        Args:
            market_id: Optional specific market to query
        
        Returns:
            List of trade dictionaries
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Try to fetch trades
                url = "https://clob.polymarket.com/trades"
                params = {"limit": 100}
                
                if market_id:
                    params["market"] = market_id
                
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                
            except Exception as e:
                print(f"Error fetching trades: {e}")
        
        return []
    
    def process_trade(self, trade: Dict, market_info: Dict = None) -> Optional[WhaleTrade]:
        """
        Process a trade and check if it's a whale trade.
        
        Args:
            trade: Trade data from API
            market_info: Optional market metadata
        
        Returns:
            WhaleTrade if it's a whale trade, None otherwise
        """
        try:
            # Calculate trade size in USD
            size = float(trade.get("size", 0))
            price = float(trade.get("price", 0.5))
            size_usd = size * price
            
            # Check if it's a whale trade
            if size_usd < WHALE_MIN_TRADE_USD:
                return None
            
            # Create whale trade
            whale_trade = WhaleTrade(
                id=trade.get("id", str(datetime.utcnow().timestamp())),
                trader=trade.get("maker", trade.get("taker", "unknown"))[:10] + "...",
                market_id=trade.get("market", ""),
                market_question=market_info.get("question", "Unknown") if market_info else "Unknown",
                slug=market_info.get("slug", "") if market_info else "",
                side="YES" if trade.get("side") == "BUY" else "NO",
                size_usd=size_usd,
                price=price,
                timestamp=datetime.utcnow()
            )
            
            # Add to trades list
            self._trades.append(whale_trade)
            
            # Update whale profile
            self._update_profile(whale_trade)
            
            # Save to cache
            self._save_to_cache()
            
            # Save to database
            try:
                db.save_whale_trade(whale_trade.to_dict())
            except Exception as e:
                print(f"Error saving whale trade to DB: {e}")
            
            return whale_trade
            
        except Exception as e:
            print(f"Error processing trade: {e}")
            return None
    
    def _update_profile(self, trade: WhaleTrade):
        """Update whale profile with new trade."""
        addr = trade.trader
        
        if addr in self._profiles:
            profile = self._profiles[addr]
            profile.total_volume += trade.size_usd
            profile.trade_count += 1
            profile.avg_trade_size = profile.total_volume / profile.trade_count
            profile.last_seen = trade.timestamp
        else:
            self._profiles[addr] = WhaleProfile(
                address=addr,
                total_volume=trade.size_usd,
                trade_count=1,
                avg_trade_size=trade.size_usd,
                favorite_side=trade.side,
                markets_traded=1,
                last_seen=trade.timestamp
            )
    
    def get_recent_trades(self, limit: int = 20, min_usd: float = 0) -> List[WhaleTrade]:
        """Get recent whale trades."""
        trades = [t for t in self._trades if t.size_usd >= min_usd]
        trades.sort(key=lambda x: x.timestamp, reverse=True)
        return trades[:limit]
    
    def get_top_whales(self, limit: int = 10) -> List[WhaleProfile]:
        """Get top whales by volume."""
        profiles = list(self._profiles.values())
        profiles.sort(key=lambda x: x.total_volume, reverse=True)
        return profiles[:limit]
    
    def get_whale_activity_for_market(self, market_id: str) -> Dict:
        """Get whale activity summary for a specific market."""
        market_trades = [t for t in self._trades if t.market_id == market_id]
        
        if not market_trades:
            return {
                "whale_count": 0,
                "total_volume": 0,
                "yes_volume": 0,
                "no_volume": 0,
                "sentiment": "neutral"
            }
        
        yes_volume = sum(t.size_usd for t in market_trades if t.side == "YES")
        no_volume = sum(t.size_usd for t in market_trades if t.side == "NO")
        unique_whales = len(set(t.trader for t in market_trades))
        
        # Determine sentiment
        if yes_volume > no_volume * 1.5:
            sentiment = "bullish"
        elif no_volume > yes_volume * 1.5:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
        
        return {
            "whale_count": unique_whales,
            "total_volume": yes_volume + no_volume,
            "yes_volume": yes_volume,
            "no_volume": no_volume,
            "sentiment": sentiment,
            "recent_trades": [t.to_dict() for t in market_trades[:5]]
        }
    
    def get_stats(self) -> Dict:
        """Get whale tracking statistics."""
        return {
            "total_trades_tracked": len(self._trades),
            "unique_whales": len(self._profiles),
            "total_volume_tracked": sum(t.size_usd for t in self._trades),
            "top_trade": max((t.size_usd for t in self._trades), default=0),
            "last_trade": self._trades[-1].to_dict() if self._trades else None
        }
    
    def add_simulated_trade(self, market_question: str, slug: str, side: str, size_usd: float, price: float):
        """
        Add a simulated whale trade (for when API is unavailable).
        Used to demonstrate the tracking system.
        """
        trade = WhaleTrade(
            id=f"sim_{datetime.utcnow().timestamp()}",
            trader=f"0x{hash(market_question) % 0xFFFF:04x}...",
            market_id=slug,
            market_question=market_question,
            slug=slug,
            side=side,
            size_usd=size_usd,
            price=price,
            timestamp=datetime.utcnow()
        )
        
        self._trades.append(trade)
        self._update_profile(trade)
        self._save_to_cache()
        
        return trade


# Singleton instance
whale_tracker = WhaleTracker()
