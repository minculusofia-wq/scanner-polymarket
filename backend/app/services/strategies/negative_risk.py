from typing import List, Dict, Optional
from dataclasses import dataclass
import json

@dataclass
class ArbitrageOpportunity:
    event_id: str
    event_slug: str
    event_title: str
    market_count: int
    sum_yes_price: float
    max_pay_out: float
    total_cost: float
    profit_pct: float
    markets: List[Dict]

def calculate_negative_risk(markets: List[Dict]) -> List[ArbitrageOpportunity]:
    """
    Identify Negative Risk (Arbitrage) opportunities in grouped markets.
    Logic: In a Mutually Exclusive winner-take-all market, Sum(YES) should be 1.0.
    If Sum(YES) > 1.0 (e.g. 1.20), it implies Sum(NO) < (N-1).
    Buying NO on ALL outcomes guarantees profit.
    """
    
    # 1. Group markets by Event ID
    events: Dict[str, List[Dict]] = {}
    
    for market in markets:
        # Skip closed or invalid markets
        if market.get("closed") or not market.get("active"):
            continue
            
        # We need to find a way to group them. 
        # Usually 'event_id' is the key? Or 'slug' logic.
        # Let's check distinct identifiers.
        # Primary: 'conditionId' is unique. 'parentConditionId' might group? (Not reliably)
        # Best bet: Iterate 'events' array in the market object.
        
        market_events = market.get("events", [])
        if not market_events:
            continue
            
        # Assume the first event is the main one
        event = market_events[0]
        event_id = event.get("id")
        
        if not event_id:
            continue
            
        if event_id not in events:
            events[event_id] = []
            
        events[event_id].append(market)

    opportunities = []

    # 2. Analyze each Group
    for event_id, group in events.items():
        if len(group) < 2:
            continue
            
        # Check if they are mutually exclusive?
        # Heuristic: Check grouped market questions. "Winner 2024", "Who will win X?".
        # Or checking tags. But for now, we assume markets in the same event
        # with high-level question similarity are exclusive.
        # RISK: Some events have multiple independent questions.
        # Strict Filter: Group must check 'question' keyword overlap or rely on external knowledge.
        # BETTER: For now, we only flag them. User must verify exclusivity.
        # We can analyze 'description' or 'groupItemTitle'.

        # Calculate Sum YES
        total_yes = 0.0
        details = []
        
        valid_group = True
        
        for m in group:
            try:
                outcome_prices = json.loads(m.get("outcomePrices", "[]"))
                if len(outcome_prices) < 2:
                    continue
                yes_price = float(outcome_prices[0])
                total_yes += yes_price
                
                details.append({
                    "id": m.get("id"),
                    "question": m.get("question"),
                    "yes_price": yes_price,
                    "liquidity": float(m.get("liquidityNum") or 0)
                })
            except:
                valid_group = False
                break
        
        if not valid_group:
            continue
            
        # Threshold: 1.02 (2% buffer for fees/slippage)
        # Note: Ideally we want strict exclusivity. 
        # If total_yes > 1.05 and liquidity is decent?
        
        if total_yes > 1.02:
            # Check liquidity - if any market is dead, arb is risky (can't sell/buy)
            min_liq = min([d["liquidity"] for d in details])
            if min_liq < 100: # Skip junk
                continue
                
            event_obj = group[0]["events"][0]
            
            # Simple Profit Calculation for "Buy All NOs"
            # Cost to buy 1 NO for each = (1 - Yes_i)
            # Total Cost = Sum(1 - Yes_i) = N - Sum(Yes_i)
            # Payoff = N - 1 (since 1 Yes wins, rest No wins)
            # Profit = Payoff - Cost = (N-1) - (N - Sum(Yes)) = Sum(Yes) - 1.
            
            profit_pct = (total_yes - 1.0) * 100
            
            opp = ArbitrageOpportunity(
                event_id=event_id,
                event_slug=event_obj.get("slug", ""),
                event_title=event_obj.get("title", "Unknown Event"),
                market_count=len(group),
                sum_yes_price=total_yes,
                max_pay_out=len(group) - 1, # Not strictly useful for display, but logic
                total_cost=len(group) - total_yes, # Algo logic
                profit_pct=profit_pct,
                markets=details
            )
            opportunities.append(opp)
            
    # Sort by profit
    opportunities.sort(key=lambda x: x.profit_pct, reverse=True)
    return opportunities
