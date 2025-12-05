"""
Volume analysis background tasks.
"""
from app.core.celery import celery_app
from app.services.volume.analyzer import volume_analyzer


@celery_app.task(name="app.services.volume.tasks.analyze_volume")
def analyze_volume():
    """
    Background task to analyze volume across all markets.
    Runs every minute.
    """
    import asyncio
    
    async def _analyze():
        results = await volume_analyzer.analyze_all_markets()
        
        spikes = [r for r in results if r.is_spike]
        if spikes:
            print(f"📊 Volume analysis: {len(spikes)} spikes detected")
        
        return len(results)
    
    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_analyze())
        return {"markets_analyzed": result}
    finally:
        loop.close()
