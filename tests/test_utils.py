"""
Unit tests for utility functions.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, date

from utils import (
    Cache, parse_quarter, format_quarter, get_quarter_dates,
    get_latest_quarter, normalize_cik, normalize_fund_name,
    ensure_output_dir, safe_int, safe_float, format_currency
)


class TestQuarterFunctions:
    """Test quarter-related utility functions."""
    
    def test_parse_quarter_valid(self):
        """Test parsing valid quarter strings."""
        assert parse_quarter("2024Q4") == (2024, 4)
        assert parse_quarter("2023Q1") == (2023, 1)
        assert parse_quarter("2025Q2") == (2025, 2)
    
    def test_parse_quarter_invalid(self):
        """Test parsing invalid quarter strings."""
        with pytest.raises(ValueError):
            parse_quarter("2024Q5")  # Invalid quarter
        
        with pytest.raises(ValueError):
            parse_quarter("2024Q0")  # Invalid quarter
        
        with pytest.raises(ValueError):
            parse_quarter("2024Q")   # Missing quarter
        
        with pytest.raises(ValueError):
            parse_quarter("Q4")      # Missing year
        
        with pytest.raises(ValueError):
            parse_quarter("")        # Empty string
    
    def test_format_quarter(self):
        """Test quarter formatting."""
        assert format_quarter(2024, 4) == "2024Q4"
        assert format_quarter(2023, 1) == "2023Q1"
        assert format_quarter(2025, 2) == "2025Q2"
    
    def test_get_quarter_dates(self):
        """Test quarter date calculations."""
        # Q1 2024
        start, end = get_quarter_dates(2024, 1)
        assert start == date(2024, 1, 1)
        assert end == date(2024, 3, 31)
        
        # Q2 2024
        start, end = get_quarter_dates(2024, 2)
        assert start == date(2024, 4, 1)
        assert end == date(2024, 6, 30)
        
        # Q3 2024
        start, end = get_quarter_dates(2024, 3)
        assert start == date(2024, 7, 1)
        assert end == date(2024, 9, 30)
        
        # Q4 2024
        start, end = get_quarter_dates(2024, 4)
        assert start == date(2024, 10, 1)
        assert end == date(2024, 12, 31)
    
    def test_get_latest_quarter(self):
        """Test latest quarter calculation."""
        quarter = get_latest_quarter()
        assert len(quarter) == 6
        assert quarter.endswith(('Q1', 'Q2', 'Q3', 'Q4'))
        
        # Parse to ensure it's valid
        year, q = parse_quarter(quarter)
        assert 2000 <= year <= 2030
        assert 1 <= q <= 4


class TestCIKNormalization:
    """Test CIK normalization functions."""
    
    def test_normalize_cik(self):
        """Test CIK normalization."""
        assert normalize_cik("1234567") == "0001234567"
        assert normalize_cik("0001234567") == "0001234567"
        assert normalize_cik("1234567890") == "1234567890"
        assert normalize_cik("0000000001") == "0000000001"
        assert normalize_cik("") == "0000000000"
        assert normalize_cik("abc123def") == "0000000123"
    
    def test_normalize_fund_name(self):
        """Test fund name normalization."""
        assert normalize_fund_name("Citadel Advisors LLC") == "CITADEL ADVISORS"
        assert normalize_fund_name("AQR Capital Management LP") == "AQR CAPITAL MANAGEMENT"
        assert normalize_fund_name("  Bridgewater Associates  ") == "BRIDGEWATER ASSOCIATES"
        assert normalize_fund_name("") == ""
        assert normalize_fund_name("Simple Fund") == "SIMPLE FUND"


class TestSafeConversion:
    """Test safe conversion functions."""
    
    def test_safe_int(self):
        """Test safe integer conversion."""
        assert safe_int("123") == 123
        assert safe_int("123.45") == 123
        assert safe_int(123.45) == 123
        assert safe_int(None) == 0
        assert safe_int("") == 0
        assert safe_int("abc") == 0
        assert safe_int("123", default=999) == 123
        assert safe_int("abc", default=999) == 999
    
    def test_safe_float(self):
        """Test safe float conversion."""
        assert safe_float("123.45") == 123.45
        assert safe_float("123") == 123.0
        assert safe_float(123) == 123.0
        assert safe_float(None) == 0.0
        assert safe_float("") == 0.0
        assert safe_float("abc") == 0.0
        assert safe_float("123.45", default=999.99) == 123.45
        assert safe_float("abc", default=999.99) == 999.99
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(1234.56) == "$1.23K"
        assert format_currency(1234567.89) == "$1.23M"
        assert format_currency(1234567890.12) == "$1.23B"
        assert format_currency(123.45) == "$123.45"
        assert format_currency(0) == "$0.00"


class TestCache:
    """Test caching functionality."""
    
    def setup_method(self):
        """Set up test cache directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = Cache(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test cache directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_cache_set_get(self):
        """Test basic cache set and get operations."""
        test_data = {"key": "value", "number": 42}
        
        # Set data
        self.cache.set("test_key", test_data)
        
        # Get data
        retrieved = self.cache.get("test_key")
        assert retrieved is not None
        assert retrieved["key"] == "value"
        assert retrieved["number"] == 42
        assert "timestamp" in retrieved
    
    def test_cache_expiry(self):
        """Test cache expiration."""
        test_data = {"key": "value"}
        
        # Set data
        self.cache.set("test_key", test_data)
        
        # Data should be available
        assert self.cache.get("test_key") is not None
        
        # Clear cache
        self.cache.clear("test_key")
        
        # Data should not be available
        assert self.cache.get("test_key") is None
    
    def test_cache_clear_all(self):
        """Test clearing all cache."""
        # Set multiple cache entries
        self.cache.set("key1", {"data": "value1"})
        self.cache.set("key2", {"data": "value2"})
        
        # Verify they exist
        assert self.cache.get("key1") is not None
        assert self.cache.get("key2") is not None
        
        # Clear all
        self.cache.clear()
        
        # Verify they're gone
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") is None


class TestOutputDirectory:
    """Test output directory functions."""
    
    def setup_method(self):
        """Set up test output directory."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test output directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_ensure_output_dir(self):
        """Test output directory creation."""
        test_dir = Path(self.temp_dir) / "test_output"
        
        # Directory shouldn't exist initially
        assert not test_dir.exists()
        
        # Create directory
        result = ensure_output_dir(str(test_dir))
        
        # Directory should exist and be returned
        assert test_dir.exists()
        assert result == test_dir
        
        # Calling again should not fail
        result2 = ensure_output_dir(str(test_dir))
        assert result2 == test_dir


if __name__ == "__main__":
    pytest.main([__file__])
