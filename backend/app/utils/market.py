"""
Market utility functions for Polymarket Scanner Bot.
"""
import json
from typing import Tuple, List, Optional


def parse_outcome_prices(market: dict) -> List[float]:
    """
    Parse outcome prices from market data.

    Handles both string JSON and list formats from the Polymarket API.

    Args:
        market: Market dictionary from API

    Returns:
        List of float prices [yes_price, no_price]
    """
    outcome_prices = market.get("outcomePrices", "[0.5, 0.5]")

    if isinstance(outcome_prices, str):
        try:
            outcome_prices = json.loads(outcome_prices)
        except (json.JSONDecodeError, TypeError):
            return [0.5, 0.5]

    if not isinstance(outcome_prices, list) or len(outcome_prices) < 2:
        return [0.5, 0.5]

    try:
        return [float(outcome_prices[0]), float(outcome_prices[1])]
    except (ValueError, TypeError, IndexError):
        return [0.5, 0.5]


def get_yes_no_prices(market: dict, default: float = 0.5) -> Tuple[float, float]:
    """
    Get YES and NO prices from market data.

    Args:
        market: Market dictionary from API
        default: Default price if parsing fails

    Returns:
        Tuple of (yes_price, no_price)
    """
    prices = parse_outcome_prices(market)
    return prices[0], prices[1]


def calculate_spread(yes_price: float, no_price: float) -> float:
    """
    Calculate the bid-ask spread.

    Args:
        yes_price: YES price
        no_price: NO price

    Returns:
        Spread as a decimal (e.g., 0.05 for 5%)
    """
    return abs(1 - yes_price - no_price)


def is_valid_market(market: dict) -> bool:
    """
    Check if a market has valid required fields.

    Args:
        market: Market dictionary from API

    Returns:
        True if market is valid, False otherwise
    """
    if not market:
        return False

    required_fields = ["id", "question"]
    for field in required_fields:
        if not market.get(field):
            return False

    # Check if closed
    if market.get("closed"):
        return False

    return True
