"""
Data validators for external API responses.
Provides safe parsing and validation of market data.
"""
from typing import Optional, List, Any, Tuple
from pydantic import BaseModel, validator
import json


class MarketValidator(BaseModel):
    """Validates Polymarket market data."""
    id: Optional[str] = None
    question: Optional[str] = None
    conditionId: Optional[str] = None
    slug: Optional[str] = None
    outcomePrices: Optional[str] = None
    volume24hr: Optional[float] = 0
    liquidityNum: Optional[float] = 0
    endDateIso: Optional[str] = None
    closed: Optional[bool] = False
    active: Optional[bool] = True

    class Config:
        extra = "ignore"  # Ignore unknown fields

    @validator('volume24hr', 'liquidityNum', pre=True, always=True)
    def coerce_to_float(cls, v):
        """Safely coerce values to float."""
        if v is None:
            return 0.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    @validator('closed', 'active', pre=True, always=True)
    def coerce_to_bool(cls, v):
        """Safely coerce values to bool."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return bool(v) if v else False


def safe_parse_prices(outcome_prices: str) -> Tuple[float, float]:
    """
    Safely parse outcome prices from JSON string.
    
    Returns:
        Tuple of (yes_price, no_price), defaults to (0.5, 0.5)
    """
    try:
        if not outcome_prices:
            return (0.5, 0.5)
        prices = json.loads(outcome_prices)
        if len(prices) >= 2:
            return (float(prices[0]), float(prices[1]))
        elif len(prices) == 1:
            return (float(prices[0]), 1.0 - float(prices[0]))
    except (json.JSONDecodeError, ValueError, TypeError, IndexError):
        pass
    return (0.5, 0.5)


def validate_markets(markets: List[Any]) -> List[dict]:
    """
    Validate and sanitize a list of markets.
    
    Args:
        markets: Raw market data from API
        
    Returns:
        List of validated market dicts
    """
    validated = []
    for market in markets:
        try:
            if not isinstance(market, dict):
                continue
            # Use Pydantic to validate and coerce
            validated_market = MarketValidator(**market)
            validated.append(validated_market.dict())
        except Exception:
            continue  # Skip invalid markets
    return validated


def safe_get_float(data: dict, key: str, default: float = 0.0) -> float:
    """Safely extract float from dict."""
    try:
        val = data.get(key)
        if val is None:
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_get_int(data: dict, key: str, default: int = 0) -> int:
    """Safely extract int from dict."""
    try:
        val = data.get(key)
        if val is None:
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default
