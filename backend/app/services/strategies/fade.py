"""
Fade / Contrarian Strategy Logic.

Detects overhyped markets to bet "No" (Fade).
"""
from typing import Optional, Dict, Any, Tuple
from app.services.monte_carlo.sentiment import get_crypto_fear_and_greed

async def analyze_fade_opportunity(market: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], float]:
    """
    Analyze if a market is a good Candidate for Fading (We want to Sell Yes / Buy No).
    
    Returns:
        (opportunity_side, display_msg, sort_score)
        opportunity_side: "FADE" or None
    """
    try:
        # 1. Basic Filters
        question = market.get("question", "").lower()
        if market.get("closed"):
            return None, None, 0
            
        # Liquidity Check (> $10k to ensure we can exit)
        liquidity = float(market.get("liquidityNum") or 0)
        if liquidity < 10000:
            return None, None, 0

        # Parse Prices
        import json
        outcome_prices = json.loads(market.get("outcomePrices", "[]"))
        if len(outcome_prices) < 2:
            return None, None, 0
            
        yes_price = float(outcome_prices[0])
        
        # 2. Price Filter: We only fade High Probability "Yes" (> 60 cents)
        # If it's 99 cents, it might be resolved, so cap at 95.
        if not (0.60 <= yes_price <= 0.95):
            return None, None, 0

        # 3. Sentiment Check (Global Crypto)
        # We start with a simple heuristic: Global Fear & Greed
        sentiment_score = 50
        sentiment_label = "Neutral"
        
        # Check if Crypto Market
        is_crypto = any(x in question for x in ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "token", "crypto"])
        
        if is_crypto:
            sentiment_data = await get_crypto_fear_and_greed()
            sentiment_score = sentiment_data.get("score", 50)
            sentiment_label = sentiment_data.get("value_classification", "Neutral")
            
            # STRATEGY: FADE if Price is High AND Sentiment is GREED (> 60)
            if sentiment_score > 60:
                # Calculate "Hype Score"
                # Hype = (Price * 100) + (Sentiment - 50)
                # Ex: Price 0.70, Sentiment 80 -> 70 + 30 = 100
                hype_score = (yes_price * 100) + (sentiment_score - 50)
                
                # Dynamic Message
                msg = f"FADE HYPE: YES {yes_price:.2f} (Sent: {sentiment_label})"
                return "FADE", msg, hype_score
                
        # 4. (Future) TradFi / Event checks can go here
        
        # Fallback: Simple High Price without sentiment confirmation?
        # Maybe too risky to auto-fade everything. We stick to Crypto+Greed for now.
        
    except Exception as e:
        print(f"Error in fade strategy: {e}")
        pass
        
    return None, None, 0
