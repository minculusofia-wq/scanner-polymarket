"""
Tests for Monte Carlo calculator.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestMonteCarloCalculator:
    """Tests for MonteCarloCalculator class."""
    
    def test_parse_bitcoin_question(self):
        """Test parsing Bitcoin price questions."""
        from app.services.monte_carlo.calculator import MonteCarloCalculator
        
        calc = MonteCarloCalculator(n_sims=100)
        
        # Test various Bitcoin patterns
        result = calc._parse_market_question("Will Bitcoin reach $150,000 by March 2025?")
        assert result is not None
        assert result[0] == "BTC"
        assert result[1] == 150000.0
        assert result[2] == "above"
        
        result = calc._parse_market_question("Will BTC hit $100k?")
        assert result is not None
        assert result[0] == "BTC"
        
        calc.shutdown()
        
    def test_parse_ethereum_question(self):
        """Test parsing Ethereum price questions."""
        from app.services.monte_carlo.calculator import MonteCarloCalculator
        
        calc = MonteCarloCalculator(n_sims=100)
        
        result = calc._parse_market_question("Will Ethereum reach $8,000 by end of 2025?")
        assert result is not None
        assert result[0] == "ETH"
        assert result[1] == 8000.0
        
        calc.shutdown()

    def test_parse_gold_question(self):
        """Test parsing Gold price questions."""
        from app.services.monte_carlo.calculator import MonteCarloCalculator
        
        calc = MonteCarloCalculator(n_sims=100)
        
        result = calc._parse_market_question("Will Gold close at $2,500 at the end of 2025?")
        assert result is not None
        assert result[0] == "GOLD"
        assert result[1] == 2500.0
        
        calc.shutdown()
        
    def test_parse_non_crypto_question(self):
        """Test that non-crypto questions return None."""
        from app.services.monte_carlo.calculator import MonteCarloCalculator
        
        calc = MonteCarloCalculator(n_sims=100)
        
        result = calc._parse_market_question("Will Trump win the 2024 election?")
        assert result is None
        
        calc.shutdown()

    def test_direction_detection(self):
        """Test direction detection (above vs below)."""
        from app.services.monte_carlo.calculator import MonteCarloCalculator
        
        calc = MonteCarloCalculator(n_sims=100)
        
        # "reach" and "hit" should be "above"
        result = calc._parse_market_question("Will Bitcoin reach $100,000?")
        assert result[2] == "above"
        
        # "dip" and "fall" should be "below"
        result = calc._parse_market_question("Will Bitcoin dip to $50,000?")
        assert result[2] == "below"
        
        calc.shutdown()


class TestEdgeOpportunity:
    """Tests for EdgeOpportunity dataclass."""
    
    def test_to_dict(self):
        """Test EdgeOpportunity serialization."""
        from app.services.monte_carlo.calculator import EdgeOpportunity
        
        opp = EdgeOpportunity(
            market_id="123",
            market_question="Test question",
            slug="test-slug",
            polymarket_yes_price=0.60,
            polymarket_no_price=0.40,
            mc_probability=0.75,
            mc_confidence_low=0.72,
            mc_confidence_high=0.78,
            edge=0.15,
            edge_percent=15.0,
            recommendation="BUY_YES",
            confidence="HIGH",
            asset="BTC",
            target_price=100000.0,
            end_date="2025-12-31",
            current_price=95000.0,
        )
        
        result = opp.to_dict()
        
        assert result["market_id"] == "123"
        assert result["edge"] == 0.15
        assert result["recommendation"] == "BUY_YES"
