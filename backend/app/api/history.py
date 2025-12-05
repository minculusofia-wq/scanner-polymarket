"""
History API endpoints - Signal history and trends.
"""
from fastapi import APIRouter, Query
from typing import Optional

from app.core.database import db

router = APIRouter()


@router.get("/signals/{market_id}")
async def get_signal_history(
    market_id: str,
    hours: int = Query(default=24, le=168)
):
    """
    Get signal history for a specific market.
    
    - **market_id**: Market identifier
    - **hours**: Hours of history (max 168 = 1 week)
    """
    history = db.get_signal_history(market_id, hours)
    return {
        "market_id": market_id,
        "history": history,
        "count": len(history)
    }


@router.get("/prices/{market_id}")
async def get_price_history(
    market_id: str,
    hours: int = Query(default=24, le=168)
):
    """
    Get price history for a specific market.
    """
    history = db.get_price_history(market_id, hours)
    return {
        "market_id": market_id,
        "prices": history,
        "count": len(history)
    }


@router.get("/trending")
async def get_trending_markets(
    hours: int = Query(default=24, le=168),
    limit: int = Query(default=10, le=50)
):
    """
    Get markets with biggest score changes.
    """
    trending = db.get_trending_markets(hours, limit)
    return {
        "trending": trending,
        "period_hours": hours
    }


@router.get("/stats")
async def get_database_stats():
    """
    Get database statistics.
    """
    return db.get_stats()


@router.post("/cleanup")
async def cleanup_old_data(
    days: int = Query(default=30, ge=7, le=365)
):
    """
    Remove data older than specified days.
    """
    db.cleanup_old_data(days)
    return {"message": f"Cleaned up data older than {days} days"}
