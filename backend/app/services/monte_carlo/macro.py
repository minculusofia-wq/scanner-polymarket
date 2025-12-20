"""
Macroeconomic Data Service (Finnhub).
"""
import aiohttp
import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Thread-safe cache with lock
_MACRO_CACHE = {
    "data": [],
    "timestamp": 0
}
_cache_lock = asyncio.Lock()
CACHE_TTL = 3600 * 4  # 4 hours

HIGH_IMPACT_KEYWORDS = ["fomc", "fed interest", "non-farm", "cpi", "gdp"]


def _get_ssl_context():
    """Get SSL context based on environment configuration."""
    import ssl
    if os.getenv("DISABLE_SSL_VERIFY", "").lower() == "true":
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    return None  # Use default SSL verification


def _analyze_events(events: List[Dict[str, Any]]) -> float:
    """Analyze events and return volatility multiplier."""
    vol_multiplier = 1.0

    print(f"[Macro] Analyzing {len(events)} events...")

    for event in events:
        # Finnhub event structure: {'event': '...', 'impact': '...', 'date': '...'}
        event_name = event.get("event", "").lower()
        impact = event.get("impact", "").lower()

        # Check for high impact
        if impact == "high" or any(k in event_name for k in HIGH_IMPACT_KEYWORDS):
            print(f"[Macro] High Impact Event Detected: {event_name} ({event.get('date')})")
            vol_multiplier = max(vol_multiplier, 1.5)  # Increase volatility by 50%

    return vol_multiplier


async def check_high_impact_events(days_ahead: int = 7) -> float:
    """
    Check for high impact economic events in the near future.
    Returns a volatility multiplier (e.g., 1.5 if Fed meeting).
    """
    global _MACRO_CACHE
    api_key = os.getenv("FINNHUB_KEY")
    if not api_key:
        print("Finnhub key missing.")
        return 1.0

    now = time.time()

    # Check cache with lock
    async with _cache_lock:
        if _MACRO_CACHE["data"] and (now - _MACRO_CACHE["timestamp"] < CACHE_TTL):
            events = _MACRO_CACHE["data"]
            return _analyze_events(events)

    # Fetch fresh data
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    url = f"https://finnhub.io/api/v1/calendar/economic?from={start_date}&to={end_date}&token={api_key}"
    ssl_context = _get_ssl_context()
    events = []

    try:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict) and 'economicCalendar' in data:
                        events = data['economicCalendar']
                    elif isinstance(data, list):
                        events = data
                    else:
                        events = []

                    # Update cache with lock
                    async with _cache_lock:
                        _MACRO_CACHE["data"] = events
                        _MACRO_CACHE["timestamp"] = now
                else:
                    print(f"Finnhub API Error: {response.status}")
                    return 1.0
    except Exception as e:
        print(f"Error fetching macro data: {e}")
        return 1.0

    return _analyze_events(events)
