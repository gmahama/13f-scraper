"""
13F XML/TXT parser to extract holdings data into a normalized DataFrame.
"""

import pandas as pd
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import logging
from bs4 import BeautifulSoup
import re

from utils import safe_int, safe_float, normalize_cik

logger = logging.getLogger(__name__)


class ThirteenFParser:
    """Parser for 13F-HR information tables (XML and TXT formats)."""
    
    def __init__(self):
        """Initialize the parser."""
        self.xml_namespaces = {
            'ns1': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'
        }
    
    def parse_information_table(self, content: str, file_type: str = 'auto') -> pd.DataFrame:
        """
        Parse 13F information table content.
        
        Args:
            content: Raw content of the information table
            file_type: File type ('xml', 'txt', or 'auto' for detection)
            
        Returns:
            DataFrame with normalized holdings data
        """
        # First, try to extract the information table section if this is a full filing document
        extracted_content = self._extract_information_table_section(content)
        
        if file_type == 'auto':
            file_type = self._detect_file_type(extracted_content)
        
        if file_type == 'xml':
            return self._parse_xml(extracted_content)
        elif file_type == 'txt':
            return self._parse_txt(extracted_content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    def _extract_information_table_section(self, content: str) -> str:
        """
        Extract the information table section from a full filing document.
        
        Args:
            content: Full filing document content
            
        Returns:
            Extracted information table section
        """
        try:
            # Look for the information table section
            # Pattern 1: Look for <ns1:informationTable> tags
            start_tag = '<ns1:informationTable'
            end_tag = '</ns1:informationTable>'
            
            start_idx = content.find(start_tag)
            if start_idx != -1:
                # Find the last occurrence of the end tag to get the complete section
                end_idx = content.rfind(end_tag)
                if end_idx != -1:
                    # Include the end tag
                    extracted = content[start_idx:end_idx + len(end_tag)]
                    logger.info("Extracted information table using ns1:informationTable tags")
                    return extracted
            
            # Pattern 2: Look for <informationTable> tags (without namespace)
            start_tag2 = '<informationTable'
            end_tag2 = '</informationTable>'
            
            start_idx = content.find(start_tag2)
            if start_idx != -1:
                end_idx = content.find(end_tag2, start_idx)
                if end_idx != -1:
                    # Include the end tag
                    extracted = content[start_idx:end_idx + len(end_tag2)]
                    logger.info("Extracted information table using informationTable tags")
                    return extracted
            
            # Pattern 3: Look for <ns1:infoTable> tags
            start_tag3 = '<ns1:infoTable'
            end_tag3 = '</ns1:infoTable>'
            
            start_idx = content.find(start_tag3)
            if start_idx != -1:
                end_idx = content.find(end_tag3, start_idx)
                if end_idx != -1:
                    # Include the end tag
                    extracted = content[start_idx:end_idx + len(end_tag3)]
                    logger.info("Extracted information table using ns1:infoTable tags")
                    return extracted
            
            # If no specific tags found, return the original content
            logger.info("No information table tags found, using original content")
            return content
            
        except Exception as e:
            logger.warning(f"Error extracting information table section: {e}")
            return content
    
    def _detect_file_type(self, content: str) -> str:
        """Detect file type based on content."""
        content_start = content.strip()[:100].lower()
        
        if content_start.startswith('<?xml') or '<informationtable' in content_start:
            return 'xml'
        elif 'nameofissuer' in content_start or 'cusip' in content_start:
            return 'txt'
        else:
            # Default to XML for better parsing
            return 'xml'
    
    def _parse_xml(self, content: str) -> pd.DataFrame:
        """
        Parse XML format information table.
        
        Args:
            content: XML content
            
        Returns:
            DataFrame with holdings data
        """
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Find all infoTable elements
            info_tables = root.findall('.//ns1:infoTable', self.xml_namespaces)
            if not info_tables:
                # Try without namespace
                info_tables = root.findall('.//infoTable')
            
            holdings = []
            
            for info_table in info_tables:
                holding = self._extract_holding_from_xml(info_table)
                if holding:
                    holdings.append(holding)
            
            if not holdings:
                logger.warning("No holdings found in XML content")
                return pd.DataFrame()
            
            return pd.DataFrame(holdings)
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            # Fallback to text parsing
            return self._parse_txt(content)
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return pd.DataFrame()
    
    def _extract_holding_from_xml(self, info_table: ET.Element) -> Optional[Dict[str, Any]]:
        """
        Extract holding data from XML infoTable element.
        
        Args:
            info_table: XML element containing holding information
            
        Returns:
            Dictionary with holding data or None if invalid
        """
        try:
            # Helper function to safely extract text
            def get_text(element, tag, default=''):
                # Try to find the tag with the full namespace
                namespace = '{http://www.sec.gov/edgar/document/thirteenf/informationtable}'
                found = element.find(f'.//{namespace}{tag}')
                if found is None or found.text is None:
                    return default
                return found.text.strip()
            
            # Helper function to safely extract integer
            def get_int(element, tag, default=0):
                text = get_text(element, tag)
                return safe_int(text, default)
            
            # Helper function to safely extract float
            def get_float(element, tag, default=0.0):
                text = get_text(element, tag)
                return safe_float(text, default)
            
            holding = {
                'cusip': get_text(info_table, 'cusip'),
                'issuer_name': get_text(info_table, 'nameOfIssuer'),
                'class_title': get_text(info_table, 'titleOfClass'),
                'value_usd': get_float(info_table, 'value'),
                'ssh_prnamt': get_int(info_table, 'shrsOrPrnAmt'),
                'ssh_prnamt_type': get_text(info_table, 'shrsOrPrnAmt'),
                'put_call': get_text(info_table, 'putCall'),
                'investment_discretion': get_text(info_table, 'investmentDiscretion'),
                'other_managers': get_text(info_table, 'otherManager'),
                'voting_authority_sole': get_int(info_table, 'votingAuthority', 'sole'),
                'voting_authority_shared': get_int(info_table, 'votingAuthority', 'shared'),
                'voting_authority_none': get_int(info_table, 'votingAuthority', 'none')
            }
            
            # Validate required fields
            if not holding['cusip'] or not holding['issuer_name']:
                return None
            
            return holding
            
        except Exception as e:
            logger.warning(f"Failed to extract holding from XML: {e}")
            return None
    
    def _parse_txt(self, content: str) -> pd.DataFrame:
        """
        Parse TXT format information table.
        
        Args:
            content: TXT content
            
        Returns:
            DataFrame with holdings data
        """
        try:
            # Use BeautifulSoup to handle HTML-like formatting
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find table or structured content
            table = soup.find('table')
            if table:
                return self._parse_html_table(table)
            else:
                return self._parse_structured_text(content)
                
        except Exception as e:
            logger.error(f"Error parsing TXT: {e}")
            return pd.DataFrame()
    
    def _parse_html_table(self, table) -> pd.DataFrame:
        """Parse HTML table format."""
        try:
            # Extract headers
            headers = []
            header_row = table.find('tr')
            if header_row:
                for th in header_row.find_all(['th', 'td']):
                    headers.append(th.get_text(strip=True).lower())
            
            # Extract data rows
            rows = []
            for tr in table.find_all('tr')[1:]:  # Skip header
                row_data = []
                for td in tr.find_all('td'):
                    row_data.append(td.get_text(strip=True))
                
                if len(row_data) >= len(headers):
                    rows.append(dict(zip(headers, row_data)))
            
            if not rows:
                return pd.DataFrame()
            
            # Convert to DataFrame and normalize
            df = pd.DataFrame(rows)
            return self._normalize_dataframe(df)
            
        except Exception as e:
            logger.error(f"Failed to parse HTML table: {e}")
            return pd.DataFrame()
    
    def _parse_structured_text(self, content: str) -> pd.DataFrame:
        """Parse structured text format."""
        try:
            # Split into lines and look for structured data
            lines = content.split('\n')
            holdings = []
            
            # Look for patterns like "CUSIP: XXXX" or structured sections
            current_holding = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for key-value pairs
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    # Map common keys to our schema
                    if 'cusip' in key:
                        if current_holding and 'cusip' in current_holding:
                            # Save previous holding and start new one
                            if self._is_valid_holding(current_holding):
                                holdings.append(current_holding.copy())
                            current_holding = {}
                        current_holding['cusip'] = value
                    elif 'issuer' in key or 'name' in key:
                        current_holding['issuer_name'] = value
                    elif 'class' in key or 'title' in key:
                        current_holding['class_title'] = value
                    elif 'value' in key:
                        current_holding['value_usd'] = safe_float(value)
                    elif 'shares' in key or 'amount' in key:
                        current_holding['ssh_prnamt'] = safe_int(value)
                    elif 'put' in key or 'call' in key:
                        current_holding['put_call'] = value
                    elif 'discretion' in key:
                        current_holding['investment_discretion'] = value
                    elif 'voting' in key:
                        # Parse voting authority
                        if 'sole' in value.lower():
                            current_holding['voting_authority_sole'] = 1
                        elif 'shared' in value.lower():
                            current_holding['voting_authority_shared'] = 1
                        elif 'none' in value.lower():
                            current_holding['voting_authority_none'] = 1
            
            # Add the last holding
            if current_holding and self._is_valid_holding(current_holding):
                holdings.append(current_holding)
            
            if not holdings:
                return pd.DataFrame()
            
            # Convert to DataFrame and normalize
            df = pd.DataFrame(holdings)
            return self._normalize_dataframe(df)
            
        except Exception as e:
            logger.error(f"Failed to parse structured text: {e}")
            return pd.DataFrame()
    
    def _is_valid_holding(self, holding: Dict[str, Any]) -> bool:
        """Check if holding has required fields."""
        required_fields = ['cusip', 'issuer_name']
        return all(field in holding and holding[field] for field in required_fields)
    
    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame to standard schema.
        
        Args:
            df: Raw DataFrame from parsing
            
        Returns:
            Normalized DataFrame
        """
        # Define expected columns
        expected_columns = [
            'cusip', 'issuer_name', 'class_title', 'value_usd', 'ssh_prnamt',
            'ssh_prnamt_type', 'put_call', 'investment_discretion', 'other_managers',
            'voting_authority_sole', 'voting_authority_shared', 'voting_authority_none'
        ]
        
        # Initialize normalized DataFrame
        normalized_df = pd.DataFrame(columns=expected_columns)
        
        # Map existing columns to expected columns
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            
            # Map common variations
            if 'cusip' in col_lower:
                column_mapping[col] = 'cusip'
            elif any(x in col_lower for x in ['issuer', 'name', 'company']):
                column_mapping[col] = 'issuer_name'
            elif any(x in col_lower for x in ['class', 'title', 'security']):
                column_mapping[col] = 'class_title'
            elif 'value' in col_lower:
                column_mapping[col] = 'value_usd'
            elif any(x in col_lower for x in ['shares', 'amount', 'quantity']):
                column_mapping[col] = 'ssh_prnamt'
            elif 'type' in col_lower:
                column_mapping[col] = 'ssh_prnamt_type'
            elif any(x in col_lower for x in ['put', 'call']):
                column_mapping[col] = 'put_call'
            elif 'discretion' in col_lower:
                column_mapping[col] = 'investment_discretion'
            elif 'manager' in col_lower:
                column_mapping[col] = 'other_managers'
            elif 'voting' in col_lower and 'sole' in col_lower:
                column_mapping[col] = 'voting_authority_sole'
            elif 'voting' in col_lower and 'shared' in col_lower:
                column_mapping[col] = 'voting_authority_shared'
            elif 'voting' in col_lower and 'none' in col_lower:
                column_mapping[col] = 'voting_authority_none'
        
        # Copy data using mapping
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                normalized_df[new_col] = df[old_col]
        
        # Fill missing columns with defaults
        for col in expected_columns:
            if col not in normalized_df.columns:
                if 'voting_authority' in col:
                    normalized_df[col] = 0
                elif col in ['value_usd', 'ssh_prnamt']:
                    normalized_df[col] = 0.0
                else:
                    normalized_df[col] = ''
        
        # Clean and validate data
        normalized_df = self._clean_dataframe(normalized_df)
        
        return normalized_df
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate DataFrame data.
        
        Args:
            df: DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        # Remove rows with missing required fields
        df = df.dropna(subset=['cusip', 'issuer_name'])
        
        # Clean CUSIP (remove non-alphanumeric characters)
        df['cusip'] = df['cusip'].astype(str).str.replace(r'[^A-Za-z0-9]', '', regex=True)
        
        # Clean issuer names
        df['issuer_name'] = df['issuer_name'].astype(str).str.strip()
        
        # Convert numeric fields
        df['value_usd'] = pd.to_numeric(df['value_usd'], errors='coerce').fillna(0.0)
        df['ssh_prnamt'] = pd.to_numeric(df['ssh_prnamt'], errors='coerce').fillna(0)
        
        # Ensure voting authority columns are integers
        voting_cols = ['voting_authority_sole', 'voting_authority_shared', 'voting_authority_none']
        for col in voting_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # Remove duplicate CUSIPs (keep first occurrence)
        df = df.drop_duplicates(subset=['cusip'], keep='first')
        
        return df.reset_index(drop=True)
    
    def get_holdings_count(self, df: pd.DataFrame) -> int:
        """
        Get the number of distinct holdings.
        
        Args:
            df: Holdings DataFrame
            
        Returns:
            Number of distinct holdings
        """
        if df.empty:
            return 0
        
        # Count distinct CUSIPs
        return df['cusip'].nunique()
    
    def get_total_value(self, df: pd.DataFrame) -> float:
        """
        Get total portfolio value.
        
        Args:
            df: Holdings DataFrame
            
        Returns:
            Total portfolio value
        """
        if df.empty:
            return 0.0
        
        return df['value_usd'].sum()
