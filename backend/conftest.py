"""
Pytest configuration and fixtures.
"""
import pytest


@pytest.fixture
def sample_market():
    """Sample market data for testing."""
    return {
        "id": "test-market-123",
        "conditionId": "condition-456",
        "slug": "test-market",
        "question": "Will BTC reach $100k?",
        "outcomePrices": '["0.65", "0.35"]',
        "volume": 1000000,
        "volume24hr": 50000,
        "liquidity": 250000,
        "spread": 0.02,
        "closed": False,
        "endDate": "2025-12-31T00:00:00Z"
    }


@pytest.fixture
def sample_signal():
    """Sample signal data for testing."""
    return {
        "id": "signal-123",
        "market_id": "test-market-123",
        "condition_id": "condition-456",
        "slug": "test-market",
        "market_question": "Will BTC reach $100k?",
        "score": 75,
        "level": "strong",
        "direction": "YES",
        "whale_score": 20,
        "volume_score": 30,
        "news_score": 25,
        "whale_count": 5,
        "unique_whale_count": 3,
        "volume_24h": 50000,
        "news_count": 2,
        "yes_price": 0.65,
        "no_price": 0.35,
        "price_movement": 0.05,
        "liquidity": 250000,
        "spread": 0.02,
        "hours_remaining": 168,
        "end_date": "2025-12-31T00:00:00Z",
        "polymarket_url": "https://polymarket.com/event/test-market"
    }
