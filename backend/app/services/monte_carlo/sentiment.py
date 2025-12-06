"""
Sentiment Analysis Service for Monte Carlo Simulations.
"""
import aiohttp
import asyncio
from typing import Dict, Any, Optional

# Cache for sentiment data
_SENTIMENT_CACHE = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 3600  # 1 hour

async def get_crypto_fear_and_greed() -> Dict[str, Any]:
    """
    Fetch Crypto Fear & Greed Index from alternative.me.
    
    Returns:
        Dict with keys: 'score' (0-100), 'value_classification' (e.g., 'Extreme Fear')
    """
    import time
    global _SENTIMENT_CACHE
    
    now = time.time()
    
    # Return cached data if valid
    if _SENTIMENT_CACHE["data"] and (now - _SENTIMENT_CACHE["timestamp"] < CACHE_TTL):
        return _SENTIMENT_CACHE["data"]
    
    url = "https://api.alternative.me/fng/"
    
    # Create SSL context that skips verification
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        item = data["data"][0]
                        result = {
                            "score": int(item.get("value", 50)),
                            "value_classification": item.get("value_classification", "Neutral"),
                            "timestamp": int(item.get("timestamp", 0))
                        }
                        
                        # Update cache
                        _SENTIMENT_CACHE["data"] = result
                        _SENTIMENT_CACHE["timestamp"] = now
                        
                        return result
                    else:
                        print("Fear & Greed API returned no data")
                else:
                    print(f"Fear & Greed API error: {response.status}")
    except Exception as e:
        print(f"Error fetching sentiment: {e}")
        
    # Fallback default
    return {
        "score": 50,
        "value_classification": "Neutral (Fallback)"
    }
