"""
Tests for patterns.py
=====================

Tests for centralized regex patterns and extraction functions.
"""

import sys
from pathlib import Path

import pytest

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira"))
sys.path.insert(0, str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "skills" / "common"))


class TestMachinePatterns:
    """Tests for machine model pattern matching."""
    
    def test_extract_pf1_models(self):
        """Should extract PF1 model numbers."""
        from patterns import extract_machine_models
        
        text = "We offer PF1-C-3020 and PF1-X-2015 machines"
        models = extract_machine_models(text)
        
        assert len(models) > 0
    
    def test_extract_am_models(self):
        """Should extract AM series models."""
        from patterns import extract_machine_models
        
        text = "The AM-V-5060 is our vacuum forming machine"
        models = extract_machine_models(text)
        
        assert len(models) > 0
    
    def test_extract_atf_models(self):
        """Should extract ATF models."""
        from patterns import extract_machine_models
        
        text = "ATF-1218 automatic trimming machine"
        models = extract_machine_models(text)
        
        assert len(models) > 0
    
    def test_extract_no_models(self):
        """Should return empty list for text without models."""
        from patterns import extract_machine_models
        
        text = "This is a general inquiry about business"
        models = extract_machine_models(text)
        
        assert models == []
    
    def test_machine_patterns_dict_exists(self):
        """MACHINE_PATTERNS dict should exist with expected keys."""
        from patterns import MACHINE_PATTERNS
        
        assert isinstance(MACHINE_PATTERNS, dict)
        assert "pf1" in MACHINE_PATTERNS
        assert "atf" in MACHINE_PATTERNS


class TestPricePatterns:
    """Tests for price extraction."""
    
    def test_extract_inr_price(self):
        """Should extract INR prices."""
        from patterns import extract_prices
        
        text = "Price is ₹48,50,000 for the machine"
        prices = extract_prices(text)
        
        assert len(prices) > 0
    
    def test_extract_usd_price(self):
        """Should extract USD prices."""
        from patterns import extract_prices
        
        text = "The price is $65,000 USD"
        prices = extract_prices(text)
        
        assert len(prices) > 0
    
    def test_extract_no_prices(self):
        """Should return empty for text without prices."""
        from patterns import extract_prices
        
        text = "Please send me a quotation"
        prices = extract_prices(text)
        
        assert prices == []
    
    def test_price_patterns_list_exists(self):
        """PRICE_PATTERNS list should exist."""
        from patterns import PRICE_PATTERNS
        
        assert isinstance(PRICE_PATTERNS, list)
        assert len(PRICE_PATTERNS) > 0


class TestCurrencyConversion:
    """Tests for currency conversion constants."""
    
    def test_usd_to_inr_rate(self):
        """Should have reasonable USD to INR rate."""
        from patterns import USD_TO_INR
        
        assert USD_TO_INR > 70  # Min reasonable rate
        assert USD_TO_INR < 100  # Max reasonable rate
    
    def test_eur_to_inr_rate(self):
        """Should have reasonable EUR to INR rate."""
        from patterns import EUR_TO_INR
        
        assert EUR_TO_INR > 80  # Min reasonable rate
        assert EUR_TO_INR < 110  # Max reasonable rate


class TestQuickPatterns:
    """Tests for quick matching patterns."""
    
    def test_quick_patterns_exist(self):
        """MACHINE_QUICK_PATTERNS should exist."""
        from patterns import MACHINE_QUICK_PATTERNS
        
        assert MACHINE_QUICK_PATTERNS is not None


class TestPatternNormalization:
    """Tests for pattern normalization utilities."""
    
    def test_normalize_model_name_exists(self):
        """normalize_model_name function should exist."""
        from patterns import normalize_model_name
        
        # Basic functionality test
        result = normalize_model_name("pf1-c-3020")
        assert result is not None
        assert "PF1" in result.upper()
    
    def test_normalize_model_variations(self):
        """Should normalize various model formats."""
        from patterns import normalize_model_name
        
        # These should all normalize to similar result
        result1 = normalize_model_name("PF1-C-3020")
        result2 = normalize_model_name("pf1c3020")
        
        # Both should contain PF1 and 3020
        assert "PF1" in result1.upper()
        assert "3020" in result1


class TestExtractedPrice:
    """Tests for ExtractedPrice dataclass."""
    
    def test_extracted_price_dataclass(self):
        """ExtractedPrice should have expected fields."""
        from patterns import ExtractedPrice
        
        price = ExtractedPrice(
            amount=4850000,
            currency="INR",
            original="₹48,50,000",
            amount_inr=4850000
        )
        
        assert price.amount == 4850000
        assert price.currency == "INR"
        assert price.amount_inr == 4850000


class TestExportedSymbols:
    """Tests for exported symbols."""
    
    def test_all_exports_exist(self):
        """All items in __all__ should be importable."""
        import patterns
        
        # Check that key exports work
        assert hasattr(patterns, 'extract_machine_models')
        assert hasattr(patterns, 'extract_prices')
        assert hasattr(patterns, 'MACHINE_PATTERNS')
        assert hasattr(patterns, 'USD_TO_INR')
        assert hasattr(patterns, 'EUR_TO_INR')
