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
            
        # Liquidity Check (lowered to $2k to capture more opportunities)
        liquidity = float(market.get("liquidityNum") or 0)
        if liquidity < 2000:
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
        sentiment_score = 50
        sentiment_label = "Neutral"
        
        # Check if Crypto Market
        is_crypto = any(x in question for x in ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "token", "crypto"])
        
        if is_crypto:
            try:
                sentiment_data = await get_crypto_fear_and_greed()
                sentiment_score = sentiment_data.get("score", 50)
                sentiment_label = sentiment_data.get("value_classification", "Neutral")
            except Exception:
                sentiment_score = 50
                sentiment_label = "Unknown"
            
            # STRATEGY: FADE if Price is High AND Sentiment is GREED (> 55)
            if sentiment_score > 55:
                hype_score = (yes_price * 100) + (sentiment_score - 50)
                msg = f"FADE HYPE: YES {yes_price:.2f} (Sent: {sentiment_label})"
                return "FADE", msg, hype_score
        
        # 4. Non-Crypto Fallback: Pure Price-Based Fade
        # If YES price is very high (> 75%), it's potentially overhyped regardless of sentiment
        if yes_price >= 0.75:
            hype_score = yes_price * 100
            msg = f"FADE HIGH: YES {yes_price:.2f} (Contrarian)"
            return "FADE", msg, hype_score
        
        # 5. Moderate Price: Show as "Watch" opportunity
        if yes_price >= 0.65:
            hype_score = yes_price * 50  # Lower priority
            msg = f"FADE WATCH: YES {yes_price:.2f}"
            return "FADE", msg, hype_score
        
    except Exception as e:
        print(f"Error in fade strategy: {e}")
        pass
        
    return None, None, 0

