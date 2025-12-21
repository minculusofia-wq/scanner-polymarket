"""
Tests for signals API and scoring logic.
"""
import pytest
from datetime import datetime, timezone


class TestScoring:
    """Tests for market scoring logic."""
    
    def test_calculate_score_high_liquidity(self):
        """Test scoring for high liquidity markets."""
        from app.api.signals import calculate_score
        
        market = {
            "liquidityNum": 1500000,  # 1.5M
            "volume24hr": 50000,
            "oneDayPriceChange": 5.0,
            "bestBid": 0.50,
            "bestAsk": 0.51,
        }
        
        score, level = calculate_score(market)
        
        # High liquidity should give good score
        assert score >= 5
        assert level in ["opportunity", "strong", "interesting"]
        
    def test_calculate_score_dead_market(self):
        """Test scoring for dead markets."""
        from app.api.signals import calculate_score
        
        market = {
            "liquidityNum": 1000,
            "volume24hr": 100,  # Very low volume
            "oneDayPriceChange": 0,
        }
        
        score, level = calculate_score(market)
        
        # Dead markets should have low score
        assert score <= 3
        assert level == "watch"
        
    def test_calculate_score_wide_spread_penalty(self):
        """Test that wide spreads get penalized."""
        from app.api.signals import calculate_score
        
        # Normal market with good metrics
        good_market = {
            "liquidityNum": 100000,
            "volume24hr": 10000,
            "oneDayPriceChange": 2.0,
            "bestBid": 0.48,
            "bestAsk": 0.52,  # 4 cent spread
        }
        
        # Same market with tight spread
        tight_spread_market = {
            "liquidityNum": 100000,
            "volume24hr": 10000,
            "oneDayPriceChange": 2.0,
            "bestBid": 0.49,
            "bestAsk": 0.50,  # 1 cent spread
        }
        
        wide_score, _ = calculate_score(good_market)
        tight_score, _ = calculate_score(tight_spread_market)
        
        # Tight spread should score higher
        assert tight_score >= wide_score


class TestMarketToSignal:
    """Tests for market to signal conversion."""
    
    def test_market_to_signal_basic(self):
        """Test basic market to signal conversion."""
        from app.api.signals import market_to_signal
        
        market = {
            "id": "12345",
            "conditionId": "cond123",
            "slug": "test-market",
            "question": "Will this test pass?",
            "liquidityNum": 50000,
            "volume24hr": 5000,
            "oneDayPriceChange": 2.5,
            "outcomePrices": "[0.65, 0.35]",
            "endDateIso": "2025-12-31T00:00:00Z",
            "events": [{"slug": "test-event"}]
        }
        
        signal = market_to_signal(market)
        
        assert signal.id == "12345"
        assert signal.market_question == "Will this test pass?"
        assert signal.yes_price == 0.65
        assert signal.no_price == 0.35
        assert "polymarket.com" in signal.polymarket_url


class TestValidators:
    """Tests for data validators."""
    
    def test_safe_parse_prices_valid(self):
        """Test parsing valid price strings."""
        from app.utils.validators import safe_parse_prices
        
        yes, no = safe_parse_prices("[0.70, 0.30]")
        assert yes == 0.70
        assert no == 0.30
        
    def test_safe_parse_prices_invalid(self):
        """Test parsing invalid price strings returns defaults."""
        from app.utils.validators import safe_parse_prices
        
        yes, no = safe_parse_prices("invalid json")
        assert yes == 0.5
        assert no == 0.5
        
        yes, no = safe_parse_prices(None)
        assert yes == 0.5
        assert no == 0.5
        
    def test_safe_get_float(self):
        """Test safe float extraction."""
        from app.utils.validators import safe_get_float
        
        data = {"price": 0.65, "invalid": "not a number", "missing": None}
        
        assert safe_get_float(data, "price") == 0.65
        assert safe_get_float(data, "invalid") == 0.0
        assert safe_get_float(data, "missing", 0.5) == 0.5
        assert safe_get_float(data, "nonexistent", 0.3) == 0.3
