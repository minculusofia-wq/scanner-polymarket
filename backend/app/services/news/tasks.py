"""
News aggregation background tasks.
"""
from app.core.celery import celery_app
from app.services.news.aggregator import news_aggregator


@celery_app.task(name="app.services.news.tasks.fetch_news")
def fetch_news():
    """
    Background task to fetch news from all sources.
    Runs every 5 minutes.
    """
    import asyncio
    
    async def _fetch():
        news = await news_aggregator.fetch_all()
        
        if news:
            print(f"📰 Fetched {len(news)} news items")
            for item in news[:3]:
                print(f"  - [{item.source}] {item.title[:50]}...")
        
        return len(news)
    
    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_fetch())
        return {"news_fetched": result}
    finally:
        loop.close()
