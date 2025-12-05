"""
Celery configuration for background tasks.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "polymarket_scanner",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.services.whale.tasks",
        "app.services.volume.tasks",
        "app.services.news.tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Scan whales every 30 seconds
        "scan-whales": {
            "task": "app.services.whale.tasks.scan_whale_activity",
            "schedule": settings.scan_interval_seconds,
        },
        # Analyze volume every minute
        "analyze-volume": {
            "task": "app.services.volume.tasks.analyze_volume",
            "schedule": 60.0,
        },
        # Fetch news every 5 minutes
        "fetch-news": {
            "task": "app.services.news.tasks.fetch_news",
            "schedule": 300.0,
        },
    },
)
