"""
Unit tests for 13F parser functionality.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch

from parser import ThirteenFParser


class TestThirteenFParser:
    """Test 13F parser functionality."""
    
    def setup_method(self):
        """Set up parser instance."""
        self.parser = ThirteenFParser()
    
    def test_detect_file_type_xml(self):
        """Test XML file type detection."""
        xml_content = '<?xml version="1.0"?><informationTable>...</informationTable>'
        assert self.parser._detect_file_type(xml_content) == 'xml'
        
        xml_content2 = '<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">'
        assert self.parser._detect_file_type(xml_content2) == 'xml'
    
    def test_detect_file_type_txt(self):
        """Test TXT file type detection."""
        txt_content = 'Name of Issuer: Apple Inc.\nCUSIP: 037833100'
        assert self.parser._detect_file_type(txt_content) == 'txt'
        
        txt_content2 = 'CUSIP: 037833100\nIssuer: Apple Inc.'
        assert self.parser._detect_file_type(txt_content2) == 'txt'
    
    def test_parse_xml_valid(self):
        """Test parsing valid XML content."""
        xml_content = '''<?xml version="1.0"?>
        <informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
            <infoTable>
                <cusip>037833100</cusip>
                <nameOfIssuer>Apple Inc.</nameOfIssuer>
                <titleOfClass>Common Stock</titleOfClass>
                <value>1000000</value>
                <shrsOrPrnAmt>1000</shrsOrPrnAmt>
                <investmentDiscretion>SOLE</investmentDiscretion>
                <votingAuthority>
                    <sole>1000</sole>
                    <shared>0</shared>
                    <none>0</none>
                </votingAuthority>
            </infoTable>
            <infoTable>
                <cusip>88160R101</cusip>
                <nameOfIssuer>Tesla Inc.</nameOfIssuer>
                <titleOfClass>Common Stock</titleOfClass>
                <value>500000</value>
                <shrsOrPrnAmt>500</shrsOrPrnAmt>
                <investmentDiscretion>SOLE</investmentDiscretion>
                <votingAuthority>
                    <sole>500</sole>
                    <shared>0</shared>
                    <none>0</none>
                </votingAuthority>
            </infoTable>
        </informationTable>'''
        
        result = self.parser.parse_information_table(xml_content, 'xml')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'cusip' in result.columns
        assert 'issuer_name' in result.columns
        
        # Check first row
        first_row = result.iloc[0]
        assert first_row['cusip'] == '037833100'
        assert first_row['issuer_name'] == 'Apple Inc.'
        assert first_row['class_title'] == 'Common Stock'
        assert first_row['value_usd'] == 1000000.0
        assert first_row['ssh_prnamt'] == 1000
        assert first_row['investment_discretion'] == 'SOLE'
        assert first_row['voting_authority_sole'] == 1000
        assert first_row['voting_authority_shared'] == 0
        assert first_row['voting_authority_none'] == 0
    
    def test_parse_xml_invalid(self):
        """Test parsing invalid XML content."""
        invalid_xml = '<invalid>xml content'
        
        # Should fallback to text parsing
        result = self.parser.parse_information_table(invalid_xml, 'xml')
        assert isinstance(result, pd.DataFrame)
    
    def test_parse_xml_missing_required_fields(self):
        """Test parsing XML with missing required fields."""
        xml_content = '''<?xml version="1.0"?>
        <informationTable>
            <infoTable>
                <cusip>037833100</cusip>
                <!-- Missing issuer name -->
                <titleOfClass>Common Stock</titleOfClass>
                <value>1000000</value>
            </infoTable>
        </informationTable>'''
        
        result = self.parser.parse_information_table(xml_content, 'xml')
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0  # Should filter out invalid holdings
    
    def test_parse_txt_table(self):
        """Test parsing TXT content with HTML table."""
        txt_content = '''
        <table>
            <tr>
                <th>CUSIP</th>
                <th>Issuer Name</th>
                <th>Class Title</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>037833100</td>
                <td>Apple Inc.</td>
                <td>Common Stock</td>
                <td>1000000</td>
            </tr>
            <tr>
                <td>88160R101</td>
                <td>Tesla Inc.</td>
                <td>Common Stock</td>
                <td>500000</td>
            </tr>
        </table>
        '''
        
        result = self.parser.parse_information_table(txt_content, 'txt')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'cusip' in result.columns
        assert 'issuer_name' in result.columns
    
    def test_parse_txt_structured(self):
        """Test parsing structured TXT content."""
        txt_content = '''
        CUSIP: 037833100
        Issuer Name: Apple Inc.
        Class Title: Common Stock
        Value: 1000000
        Shares: 1000
        Investment Discretion: SOLE
        Voting Authority: SOLE
        
        CUSIP: 88160R101
        Issuer Name: Tesla Inc.
        Class Title: Common Stock
        Value: 500000
        Shares: 500
        Investment Discretion: SOLE
        Voting Authority: SOLE
        '''
        
        result = self.parser.parse_information_table(txt_content, 'txt')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'cusip' in result.columns
        assert 'issuer_name' in result.columns
    
    def test_normalize_dataframe(self):
        """Test DataFrame normalization."""
        # Create raw DataFrame with various column names
        raw_df = pd.DataFrame({
            'CUSIP': ['037833100', '88160R101'],
            'Issuer': ['Apple Inc.', 'Tesla Inc.'],
            'Security Class': ['Common Stock', 'Common Stock'],
            'Market Value': [1000000, 500000],
            'Shares Held': [1000, 500],
            'Investment Discretion': ['SOLE', 'SOLE']
        })
        
        normalized = self.parser._normalize_dataframe(raw_df)
        
        # Check expected columns exist
        expected_columns = [
            'cusip', 'issuer_name', 'class_title', 'value_usd', 'ssh_prnamt',
            'ssh_prnamt_type', 'put_call', 'investment_discretion', 'other_managers',
            'voting_authority_sole', 'voting_authority_shared', 'voting_authority_none'
        ]
        
        for col in expected_columns:
            assert col in normalized.columns
        
        # Check data was mapped correctly
        assert normalized.iloc[0]['cusip'] == '037833100'
        assert normalized.iloc[0]['issuer_name'] == 'Apple Inc.'
        assert normalized.iloc[0]['class_title'] == 'Common Stock'
        assert normalized.iloc[0]['value_usd'] == 1000000.0
        assert normalized.iloc[0]['ssh_prnamt'] == 1000
    
    def test_clean_dataframe(self):
        """Test DataFrame cleaning and validation."""
        # Create DataFrame with some invalid data
        raw_df = pd.DataFrame({
            'cusip': ['037833100', '88160R101', '', 'invalid_cusip'],
            'issuer_name': ['Apple Inc.', 'Tesla Inc.', '', 'Valid Company'],
            'class_title': ['Common Stock', 'Common Stock', 'Bond', 'Stock'],
            'value_usd': [1000000, 500000, 'invalid', 750000],
            'ssh_prnamt': [1000, 500, 'invalid', 750],
            'voting_authority_sole': [1000, 500, 0, 750],
            'voting_authority_shared': [0, 0, 0, 0],
            'voting_authority_none': [0, 0, 0, 0]
        })
        
        cleaned = self.parser._clean_dataframe(raw_df)
        
        # Should remove rows with missing required fields
        assert len(cleaned) == 2  # Only valid rows should remain
        
        # Check data types
        assert cleaned['value_usd'].dtype == 'float64'
        assert cleaned['ssh_prnamt'].dtype == 'int64'
        assert cleaned['voting_authority_sole'].dtype == 'int64'
        
        # Check CUSIP cleaning
        assert '037833100' in cleaned['cusip'].values
        assert '88160R101' in cleaned['cusip'].values
    
    def test_holdings_count(self):
        """Test holdings count calculation."""
        # Create test DataFrame
        df = pd.DataFrame({
            'cusip': ['037833100', '88160R101', '037833100'],  # Duplicate CUSIP
            'issuer_name': ['Apple Inc.', 'Tesla Inc.', 'Apple Inc.'],
            'value_usd': [1000000, 500000, 1000000]
        })
        
        count = self.parser.get_holdings_count(df)
        assert count == 2  # Should count distinct CUSIPs
    
    def test_total_value(self):
        """Test total portfolio value calculation."""
        # Create test DataFrame
        df = pd.DataFrame({
            'cusip': ['037833100', '88160R101'],
            'issuer_name': ['Apple Inc.', 'Tesla Inc.'],
            'value_usd': [1000000, 500000]
        })
        
        total = self.parser.get_total_value(df)
        assert total == 1500000.0
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrames."""
        empty_df = pd.DataFrame()
        
        assert self.parser.get_holdings_count(empty_df) == 0
        assert self.parser.get_total_value(empty_df) == 0.0
    
    def test_is_valid_holding(self):
        """Test holding validation."""
        # Valid holding
        valid_holding = {
            'cusip': '037833100',
            'issuer_name': 'Apple Inc.'
        }
        assert self.parser._is_valid_holding(valid_holding) is True
        
        # Invalid holding - missing CUSIP
        invalid_holding1 = {
            'issuer_name': 'Apple Inc.'
        }
        assert self.parser._is_valid_holding(invalid_holding1) is False
        
        # Invalid holding - missing issuer name
        invalid_holding2 = {
            'cusip': '037833100'
        }
        assert self.parser._is_valid_holding(invalid_holding2) is False
        
        # Invalid holding - empty values
        invalid_holding3 = {
            'cusip': '',
            'issuer_name': 'Apple Inc.'
        }
        assert self.parser._is_valid_holding(invalid_holding3) is False


if __name__ == "__main__":
    pytest.main([__file__])
