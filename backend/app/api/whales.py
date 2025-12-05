"""
Whales API endpoints - Real whale tracking.
"""
from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.services.whale_tracker import whale_tracker

router = APIRouter()


class WhaleTradeResponse(BaseModel):
    """Whale trade response."""
    id: str
    trader: str
    market_id: str
    market_question: str
    slug: str
    side: str
    size_usd: float
    price: float
    timestamp: str


class WhaleProfileResponse(BaseModel):
    """Whale profile response."""
    address: str
    total_volume: float
    trade_count: int
    avg_trade_size: float
    favorite_side: str
    markets_traded: int
    last_seen: str


@router.get("/trades")
async def get_whale_trades(
    limit: int = Query(default=20, le=100),
    min_usd: float = Query(default=10000, ge=0)
):
    """
    Get recent whale trades.
    
    - **limit**: Maximum trades to return
    - **min_usd**: Minimum trade size in USD
    """
    trades = whale_tracker.get_recent_trades(limit=limit, min_usd=min_usd)
    
    return {
        "trades": [t.to_dict() for t in trades],
        "total": len(trades)
    }


@router.get("/profiles")
async def get_whale_profiles(
    limit: int = Query(default=10, le=50)
):
    """Get top whale profiles by volume."""
    profiles = whale_tracker.get_top_whales(limit=limit)
    
    return {
        "profiles": [p.to_dict() for p in profiles],
        "total": len(profiles)
    }


@router.get("/market/{market_id}")
async def get_whale_activity(market_id: str):
    """Get whale activity for a specific market."""
    return whale_tracker.get_whale_activity_for_market(market_id)


@router.get("/stats")
async def get_whale_stats():
    """Get whale tracking statistics."""
    return whale_tracker.get_stats()
