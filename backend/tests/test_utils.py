"""
Tests for utility functions.
"""
import pytest
from app.utils.market import (
    parse_outcome_prices,
    get_yes_no_prices,
    calculate_spread,
    is_valid_market
)


class TestParseOutcomePrices:
    """Tests for parse_outcome_prices function."""

    def test_valid_string_json(self):
        """Test with valid JSON string."""
        market = {"outcomePrices": '["0.65", "0.35"]'}
        result = parse_outcome_prices(market)
        assert result == [0.65, 0.35]

    def test_valid_list(self):
        """Test with list format."""
        market = {"outcomePrices": [0.7, 0.3]}
        result = parse_outcome_prices(market)
        assert result == [0.7, 0.3]

    def test_missing_key(self):
        """Test with missing outcomePrices key."""
        market = {}
        result = parse_outcome_prices(market)
        assert result == [0.5, 0.5]

    def test_invalid_json(self):
        """Test with invalid JSON string."""
        market = {"outcomePrices": "invalid"}
        result = parse_outcome_prices(market)
        assert result == [0.5, 0.5]

    def test_empty_list(self):
        """Test with empty list."""
        market = {"outcomePrices": []}
        result = parse_outcome_prices(market)
        assert result == [0.5, 0.5]

    def test_single_value_list(self):
        """Test with single value list."""
        market = {"outcomePrices": [0.5]}
        result = parse_outcome_prices(market)
        assert result == [0.5, 0.5]


class TestGetYesNoPrices:
    """Tests for get_yes_no_prices function."""

    def test_returns_tuple(self):
        """Test that function returns a tuple."""
        market = {"outcomePrices": '["0.6", "0.4"]'}
        yes, no = get_yes_no_prices(market)
        assert yes == 0.6
        assert no == 0.4

    def test_default_on_error(self):
        """Test default values on parse error."""
        market = {}
        yes, no = get_yes_no_prices(market)
        assert yes == 0.5
        assert no == 0.5


class TestCalculateSpread:
    """Tests for calculate_spread function."""

    def test_normal_spread(self):
        """Test with normal prices."""
        spread = calculate_spread(0.6, 0.35)
        assert spread == pytest.approx(0.05, rel=0.01)

    def test_zero_spread(self):
        """Test with prices summing to 1."""
        spread = calculate_spread(0.6, 0.4)
        assert spread == pytest.approx(0.0, abs=0.001)

    def test_negative_spread(self):
        """Test with prices summing to more than 1."""
        spread = calculate_spread(0.6, 0.5)
        assert spread == pytest.approx(0.1, abs=0.001)


class TestIsValidMarket:
    """Tests for is_valid_market function."""

    def test_valid_market(self):
        """Test with valid market."""
        market = {"id": "123", "question": "Will it rain?"}
        assert is_valid_market(market) is True

    def test_missing_id(self):
        """Test with missing id."""
        market = {"question": "Will it rain?"}
        assert is_valid_market(market) is False

    def test_missing_question(self):
        """Test with missing question."""
        market = {"id": "123"}
        assert is_valid_market(market) is False

    def test_closed_market(self):
        """Test with closed market."""
        market = {"id": "123", "question": "Will it rain?", "closed": True}
        assert is_valid_market(market) is False

    def test_empty_market(self):
        """Test with empty dict."""
        assert is_valid_market({}) is False

    def test_none_market(self):
        """Test with None."""
        assert is_valid_market(None) is False
