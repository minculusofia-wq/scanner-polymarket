"""
TradFi Asset Sentiment Service (Alpha Vantage).
"""
import aiohttp
import os
import time
from typing import Dict, Any, Optional

# Cache
_SENTIMENT_CACHE = {}
CACHE_TTL = 3600  # 1 hour

async def get_tradfi_sentiment(ticker: str) -> Dict[str, Any]:
    """
    Fetch news sentiment for a ticker from Alpha Vantage.
    """
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        return {"score": None, "label": None}
        
    cache_key = f"sentiment_{ticker}"
    now = time.time()
    
    if cache_key in _SENTIMENT_CACHE:
        cached = _SENTIMENT_CACHE[cache_key]
        if now - cached["timestamp"] < CACHE_TTL:
            return cached["data"]

    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={api_key}&limit=50"
    
    # SSL Bypass
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
                    
                    # Compute average sentiment
                    feed = data.get("feed", [])
                    if not feed:
                        return {"score": 50, "label": "Neutral"}
                        
                    total_score = 0
                    count = 0
                    
                    for item in feed:
                        score = float(item.get("overall_sentiment_score", 0))
                        total_score += score
                        count += 1
                        
                    if count > 0:
                        avg_score = total_score / count
                        # Remap -1.0 to 1.0 -> 0 to 100
                        # -1 -> 0, 0 -> 50, 1 -> 100
                        final_score = (avg_score + 1) * 50
                        
                        label = "Neutral"
                        if final_score > 60: label = "Greed"
                        if final_score > 80: label = "Extreme Greed"
                        if final_score < 40: label = "Fear"
                        if final_score < 20: label = "Extreme Fear"
                        
                        result = {"score": int(final_score), "label": label}
                        
                        _SENTIMENT_CACHE[cache_key] = {
                            "data": result,
                            "timestamp": now
                        }
                        return result
                        
    except Exception as e:
        print(f"Error fetching TradFi sentiment: {e}")
        
    return {"score": None, "label": None}
