"""
Whale detection background tasks.
"""
from app.core.celery import celery_app
from app.services.whale.detector import whale_detector


@celery_app.task(name="app.services.whale.tasks.scan_whale_activity")
def scan_whale_activity():
    """
    Background task to scan for whale activity.
    Runs every 30 seconds.
    """
    import asyncio
    
    async def _scan():
        trades = await whale_detector.scan_whale_activity()
        
        if trades:
            print(f"🐋 Detected {len(trades)} whale trades")
            for trade in trades:
                print(f"  - {trade.whale_address[:10]}... | {trade.side} | ${trade.size_usd:,.0f}")
        
        return len(trades)
    
    # Run async function in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_scan())
        return {"trades_detected": result}
    finally:
        loop.close()
