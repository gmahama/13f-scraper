"""
Unit tests for core business logic.
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd

from logic import ThirteenFProcessor
from models import FilingSummary


class TestThirteenFProcessor:
    """Test core business logic functionality."""
    
    def setup_method(self):
        """Set up processor instance with mocked dependencies."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock SEC client
        self.mock_sec_client = Mock()
        
        # Create processor with mocked client
        with patch('logic.SECClient') as mock_sec_class:
            mock_sec_class.return_value = self.mock_sec_client
            self.processor = ThirteenFProcessor(cache_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_get_fund_list_ciks_only(self):
        """Test fund list creation with CIKs only."""
        ciks = ["0001167483", "0001056903"]
        
        result = self.processor._get_fund_list(funds=None, ciks=ciks)
        
        assert len(result) == 2
        assert result[0]['cik'] == "0001167483"
        assert result[1]['cik'] == "0001056903"
        assert result[0]['name'] == "0001167483"  # Uses CIK as name
        assert result[1]['name'] == "0001056903"
    
    def test_get_fund_list_funds_only(self):
        """Test fund list creation with fund names only."""
        funds = ["Citadel Advisors", "AQR Capital Management"]
        
        # Mock fund name resolution
        self.mock_sec_client.search_company_by_name.side_effect = [
            [{"cik": "0001167483", "name": "Citadel Advisors"}],
            [{"cik": "0001056903", "name": "AQR Capital Management"}]
        ]
        
        result = self.processor._get_fund_list(funds=funds, ciks=None)
        
        assert len(result) == 2
        assert result[0]['cik'] == "0001167483"
        assert result[1]['cik'] == "0001056903"
        assert result[0]['name'] == "Citadel Advisors"
        assert result[1]['name'] == "AQR Capital Management"
    
    def test_get_fund_list_mixed(self):
        """Test fund list creation with both funds and CIKs."""
        funds = ["Citadel Advisors"]
        ciks = ["0001056903"]
        
        # Mock fund name resolution
        self.mock_sec_client.search_company_by_name.return_value = [
            {"cik": "0001167483", "name": "Citadel Advisors"}
        ]
        
        result = self.processor._get_fund_list(funds=funds, ciks=ciks)
        
        assert len(result) == 2
        # Should have both funds
        ciks_in_result = [f['cik'] for f in result]
        assert "0001167483" in ciks_in_result
        assert "0001056903" in ciks_in_result
    
    def test_get_fund_list_duplicates(self):
        """Test fund list deduplication."""
        funds = ["Citadel Advisors"]
        ciks = ["0001167483"]  # Same CIK as resolved fund
        
        # Mock fund name resolution
        self.mock_sec_client.search_company_by_name.return_value = [
            {"cik": "0001167483", "name": "Citadel Advisors"}
        ]
        
        result = self.processor._get_fund_list(funds=funds, ciks=ciks)
        
        # Should only have one fund
        assert len(result) == 1
        assert result[0]['cik'] == "0001167483"
    
    def test_resolve_fund_name_to_cik_success(self):
        """Test successful fund name resolution."""
        fund_name = "Citadel Advisors"
        
        # Mock successful search
        self.mock_sec_client.search_company_by_name.return_value = [
            {"cik": "0001167483", "name": "Citadel Advisors"}
        ]
        
        result = self.processor._resolve_fund_name_to_cik(fund_name)
        
        assert result == "0001167483"
        # Should be cached
        assert fund_name.upper().strip() in self.processor.company_name_cache
    
    def test_resolve_fund_name_to_cik_failure(self):
        """Test failed fund name resolution."""
        fund_name = "Non Existent Fund"
        
        # Mock failed search
        self.mock_sec_client.search_company_by_name.return_value = []
        
        result = self.processor._resolve_fund_name_to_cik(fund_name)
        
        assert result is None
    
    def test_resolve_fund_name_to_cik_cached(self):
        """Test fund name resolution from cache."""
        fund_name = "Citadel Advisors"
        
        # Pre-populate cache
        self.processor.company_name_cache[fund_name.upper().strip()] = "0001167483"
        
        result = self.processor._resolve_fund_name_to_cik(fund_name)
        
        assert result == "0001167483"
        # Should not call SEC client
        self.mock_sec_client.search_company_by_name.assert_not_called()
    
    def test_find_target_filings(self):
        """Test finding target filings for a quarter."""
        # Mock submissions data
        submissions = {
            "filings": {
                "recent": [
                    {
                        "form": "13F-HR",
                        "filingDate": "2024-01-15",  # Q4 2023
                        "accessionNumber": "1234567890"
                    },
                    {
                        "form": "13F-HR/A",
                        "filingDate": "2024-02-15",  # Q4 2023
                        "accessionNumber": "1234567891"
                    },
                    {
                        "form": "13F-HR",
                        "filingDate": "2024-04-15",  # Q1 2024
                        "accessionNumber": "1234567892"
                    },
                    {
                        "form": "13F-NT",  # Should be ignored
                        "filingDate": "2024-01-10",
                        "accessionNumber": "1234567893"
                    }
                ]
            }
        }
        
        # Find Q4 2023 filings
        result = self.processor._find_target_filings(submissions, 2023, 4)
        
        assert len(result) == 2
        assert result[0]['form'] == "13F-HR"
        assert result[1]['form'] == "13F-HR/A"
    
    def test_get_latest_filing(self):
        """Test getting the latest filing from a list."""
        filings = [
            {"filingDate": "2024-01-15", "accessionNumber": "1234567890"},
            {"filingDate": "2024-02-15", "accessionNumber": "1234567891"},
            {"filingDate": "2024-01-10", "accessionNumber": "1234567892"}
        ]
        
        result = self.processor._get_latest_filing(filings)
        
        assert result['accessionNumber'] == "1234567891"  # Latest date
    
    def test_check_first_time_filer_true(self):
        """Test first-time filer detection when true."""
        # Mock submissions with no earlier 13F-HR filings
        submissions = {
            "filings": {
                "recent": [
                    {
                        "form": "13F-HR",
                        "filingDate": "2024-01-15",  # Q4 2023 (target quarter)
                        "accessionNumber": "1234567890"
                    }
                ]
            }
        }
        
        is_first_time, earliest_period = self.processor._check_first_time_filer(
            submissions, 2023, 4
        )
        
        assert is_first_time is True
        assert earliest_period is None
    
    def test_check_first_time_filer_false(self):
        """Test first-time filer detection when false."""
        # Mock submissions with earlier 13F-HR filings
        submissions = {
            "filings": {
                "recent": [
                    {
                        "form": "13F-HR",
                        "filingDate": "2023-01-15",  # Q4 2022 (earlier)
                        "accessionNumber": "1234567890"
                    },
                    {
                        "form": "13F-HR",
                        "filingDate": "2024-01-15",  # Q4 2023 (target quarter)
                        "accessionNumber": "1234567891"
                    }
                ]
            }
        }
        
        is_first_time, earliest_period = self.processor._check_first_time_filer(
            submissions, 2023, 4
        )
        
        assert is_first_time is False
        assert earliest_period == "2022Q4"
    
    def test_check_first_time_filer_ignores_13f_nt(self):
        """Test that 13F-NT filings are ignored for first-time detection."""
        # Mock submissions with 13F-NT but no 13F-HR
        submissions = {
            "filings": {
                "recent": [
                    {
                        "form": "13F-NT",
                        "filingDate": "2023-01-15",  # Q4 2022
                        "accessionNumber": "1234567890"
                    },
                    {
                        "form": "13F-HR",
                        "filingDate": "2024-01-15",  # Q4 2023 (target quarter)
                        "accessionNumber": "1234567891"
                    }
                ]
            }
        }
        
        is_first_time, earliest_period = self.processor._check_first_time_filer(
            submissions, 2023, 4
        )
        
        # Should still be first-time since 13F-NT doesn't count
        assert is_first_time is True
        assert earliest_period is None
    
    def test_passes_holdings_filters_min_only(self):
        """Test holdings filters with minimum only."""
        num_holdings = 50
        
        # Should pass with min_holdings = 20
        assert self.processor._passes_holdings_filters(
            num_holdings, min_holdings=20, max_holdings=None, between_holdings=None
        ) is True
        
        # Should fail with min_holdings = 100
        assert self.processor._passes_holdings_filters(
            num_holdings, min_holdings=100, max_holdings=None, between_holdings=None
        ) is False
    
    def test_passes_holdings_filters_max_only(self):
        """Test holdings filters with maximum only."""
        num_holdings = 50
        
        # Should pass with max_holdings = 100
        assert self.processor._passes_holdings_filters(
            num_holdings, min_holdings=None, max_holdings=100, between_holdings=None
        ) is True
        
        # Should fail with max_holdings = 25
        assert self.processor._passes_holdings_filters(
            num_holdings, min_holdings=None, max_holdings=25, between_holdings=None
        ) is False
    
    def test_passes_holdings_filters_between(self):
        """Test holdings filters with between range."""
        num_holdings = 50
        
        # Should pass with range 25-75
        assert self.processor._passes_holdings_filters(
            num_holdings, min_holdings=None, max_holdings=None, between_holdings=(25, 75)
        ) is True
        
        # Should fail with range 75-100
        assert self.processor._passes_holdings_filters(
            num_holdings, min_holdings=None, max_holdings=None, between_holdings=(75, 100)
        ) is False
    
    def test_passes_holdings_filters_between_shorthand(self):
        """Test that between_holdings overrides min/max."""
        num_holdings = 50
        
        # between_holdings should override min_holdings and max_holdings
        assert self.processor._passes_holdings_filters(
            num_holdings, min_holdings=100, max_holdings=10, between_holdings=(25, 75)
        ) is True
    
    def test_passes_holdings_filters_no_filters(self):
        """Test holdings filters with no filters applied."""
        num_holdings = 50
        
        # Should always pass when no filters are set
        assert self.processor._passes_holdings_filters(
            num_holdings, min_holdings=None, max_holdings=None, between_holdings=None
        ) is True
    
    def test_process_funds_basic(self):
        """Test basic fund processing."""
        # Mock dependencies
        with patch.object(self.processor, '_get_fund_list') as mock_get_funds:
            with patch.object(self.processor, '_process_single_fund') as mock_process:
                
                # Mock fund list
                mock_get_funds.return_value = [
                    {"cik": "0001167483", "name": "Citadel Advisors"}
                ]
                
                # Mock processing result
                mock_summary = FilingSummary(
                    fund_name="Citadel Advisors",
                    cik="0001167483",
                    period="2024Q4",
                    period_end="2024-12-31",
                    is_first_time_filer=False,
                    num_holdings=100,
                    filing_url="http://example.com/filing",
                    info_table_url="http://example.com/info"
                )
                mock_process.return_value = mock_summary
                
                # Process funds
                result = self.processor.process_funds(
                    ciks=["0001167483"],
                    quarter="2024Q4"
                )
                
                assert len(result) == 1
                assert result[0].fund_name == "Citadel Advisors"
                assert result[0].num_holdings == 100
    
    def test_process_funds_no_funds(self):
        """Test processing with no valid funds."""
        with patch.object(self.processor, '_get_fund_list') as mock_get_funds:
            mock_get_funds.return_value = []
            
            result = self.processor.process_funds(ciks=["invalid"])
            
            assert result == []
    
    def test_process_funds_invalid_quarter(self):
        """Test processing with invalid quarter format."""
        result = self.processor.process_funds(
            ciks=["0001167483"],
            quarter="invalid"
        )
        
        assert result == []
    
    def test_process_funds_default_quarter(self):
        """Test processing with default quarter."""
        with patch('logic.get_latest_quarter') as mock_latest:
            with patch.object(self.processor, '_get_fund_list') as mock_get_funds:
                with patch.object(self.processor, '_process_single_fund') as mock_process:
                    
                    mock_latest.return_value = "2024Q4"
                    mock_get_funds.return_value = [
                        {"cik": "0001167483", "name": "Test Fund"}
                    ]
                    mock_process.return_value = None  # No filing found
                    
                    result = self.processor.process_funds(ciks=["0001167483"])
                    
                    assert result == []
                    mock_latest.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
