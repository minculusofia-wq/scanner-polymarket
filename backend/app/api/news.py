"""
News API endpoints - Multi-source news aggregation.
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict

from app.services.news.aggregator import news_aggregator

router = APIRouter()


@router.get("/")
async def get_news(
    limit: int = Query(default=20, le=100),
    source: Optional[str] = Query(default=None)
):
    """
    Get latest news from all sources.
    
    - **limit**: Max news items
    - **source**: Filter by source (google_news, newsapi, serpapi)
    """
    # Trigger fetch if cache is empty
    if not news_aggregator._news_cache:
        await news_aggregator.fetch_all()
    
    news = news_aggregator.get_all_cached_news(limit)
    
    if source:
        news = [n for n in news if n.source == source]
        
    return {
        "news": news,
        "count": len(news),
        "sources": news_aggregator.get_sources_status()
    }


@router.get("/market/{market_question}")
async def get_market_news(
    market_question: str,
    hours: int = Query(default=24, le=168)
):
    """Get news relevant to a specific market."""
    news = news_aggregator.get_news_for_market(market_question, hours)
    score = news_aggregator.get_news_score(market_question)
    
    return {
        "market_question": market_question,
        "news": news,
        "score": score,
        "sentiment": "positive" if score > 60 else "negative" if score < 40 else "neutral"
    }


@router.post("/refresh")
async def refresh_news():
    """Force refresh of news sources."""
    news = await news_aggregator.fetch_all()
    return {
        "message": "News refreshed",
        "count": len(news),
        "sources": news_aggregator.get_sources_status()
    }
