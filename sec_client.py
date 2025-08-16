"""
SEC EDGAR client for fetching company submissions and filing documents.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException, HTTPError

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

logger = logging.getLogger(__name__)


class SECClient:
    """Client for interacting with SEC EDGAR with rate limiting and retries."""
    
    def __init__(self, user_agent: Optional[str] = None, base_url: str = "https://www.sec.gov"):
        """
        Initialize SEC client.
        
        Args:
            user_agent: User-Agent string (required by SEC)
            base_url: Base URL for SEC EDGAR
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set User-Agent (required by SEC)
        if user_agent:
            self.session.headers.update({'User-Agent': user_agent})
        else:
            # Try to get from environment
            env_user_agent = os.getenv('SEC_USER_AGENT')
            if env_user_agent:
                self.session.headers.update({'User-Agent': env_user_agent})
            else:
                logger.warning("No User-Agent set. SEC may block requests.")
        
        # Rate limiting settings
        self.rate_limit_delay = float(os.getenv('RATE_LIMIT_DELAY', '0.1'))  # 100ms between requests
        self.max_requests_per_second = 10
        self.last_request_time = 0
        
        # Retry settings
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_delay = 1.0 / self.max_requests_per_second
        
        if time_since_last < min_delay:
            sleep_time = min_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, requests.HTTPError))
    )
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with retries and rate limiting.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request arguments
            
        Returns:
            HTTP response
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        self._rate_limit()
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                logger.warning("Rate limited by SEC. Waiting before retry...")
                time.sleep(5)  # Wait 5 seconds before retry
                raise
            raise
    
    def get_company_submissions(self, cik: str) -> Dict[str, Any]:
        """
        Get company submissions for a CIK.
        
        Args:
            cik: CIK identifier (10-digit zero-padded)
            
        Returns:
            Company submissions data
        """
        # Use the correct SEC submissions endpoint
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        
        logger.info(f"Fetching company submissions for CIK {cik}")
        try:
            response = self._make_request('GET', url)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get company submissions for CIK {cik}: {e}")
            return {}
    
    def get_filing_document(self, accession_number: str, primary_document: str) -> str:
        """
        Get filing document content.
        
        Args:
            accession_number: Filing accession number
            primary_document: Primary document filename
            
        Returns:
            Document content as string
        """
        # Extract CIK from accession number (first 10 digits)
        cik = accession_number[:10]
        
        # Transform accession number: remove hyphens for file path
        file_accession = accession_number.replace('-', '')
        
        url = f"{self.base_url}/Archives/edgar/data/{cik}/{file_accession}/{primary_document}"
        
        logger.info(f"Fetching document: {primary_document}")
        response = self._make_request('GET', url)
        return response.text
    
    def get_filing_document_with_cik(self, accession_number: str, primary_document: str, cik: str) -> str:
        """
        Get filing document content using the provided CIK.
        
        Args:
            accession_number: Filing accession number
            primary_document: Primary document filename
            cik: Company CIK identifier
            
        Returns:
            Document content as string
        """
        # Transform accession number: remove hyphens for file path
        file_accession = accession_number.replace('-', '')
        
        url = f"{self.base_url}/Archives/edgar/data/{cik}/{file_accession}/{primary_document}"
        
        logger.info(f"Fetching document with CIK {cik}: {primary_document}")
        response = self._make_request('GET', url)
        return response.text
    
    def get_information_table(self, accession_number: str, info_table_file: str) -> str:
        """
        Get information table content.
        
        Args:
            accession_number: Filing accession number
            info_table_file: Information table filename
            
        Returns:
            Information table content as string
        """
        # Extract CIK from accession number (first 10 digits)
        cik = accession_number[:10]
        url = f"{self.base_url}/Archives/edgar/data/{cik}/{accession_number}/{info_table_file}"
        
        logger.info(f"Fetching information table: {info_table_file}")
        response = self._make_request('GET', url)
        return response.text
    
    def search_company_by_name(self, company_name: str) -> List[Dict[str, Any]]:
        """
        Search for company by name using SEC EDGAR search endpoint.
        
        Args:
            company_name: Company name to search for
            
        Returns:
            List of matching companies
        """
        url = f"{self.base_url}/cgi-bin/browse-edgar"
        params = {
            'company': company_name,
            'type': '13F-HR',
            'owner': 'exclude',
            'action': 'getcompany',
            'output': 'xml'
        }
        
        try:
            response = self._make_request('GET', url, params=params)
            content = response.text
            
            # Parse XML response to extract company info
            matches = self._parse_company_search_results(content, company_name)
            return matches
            
        except Exception as e:
            logger.error(f"Failed to search company by name: {e}")
            return []
    
    def _parse_company_search_results(self, xml_content: str, search_name: str) -> List[Dict[str, Any]]:
        """
        Parse SEC EDGAR company search results XML.
        
        Args:
            xml_content: XML response content
            search_name: Original search name
            
        Returns:
            List of matching companies
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(xml_content, 'xml')
            companies = []
            
            # Look for companyInfo elements
            company_info_elements = soup.find_all('companyInfo')
            
            for company_elem in company_info_elements:
                cik_elem = company_elem.find('CIK')
                name_elem = company_elem.find('name')  # Changed from 'conformedName' to 'name'
                
                if cik_elem and name_elem:
                    cik = cik_elem.text.strip()
                    name = name_elem.text.strip()
                    
                    # Check if this is a good match
                    if (search_name.upper() in name.upper() or 
                        name.upper() in search_name.upper() or
                        any(word in name.upper() for word in search_name.upper().split())):
                        
                        companies.append({
                            'cik': cik.zfill(10),
                            'name': name,
                            'ticker': ''  # Not available in this endpoint
                        })
            
            return companies
            
        except Exception as e:
            logger.error(f"Failed to parse company search results: {e}")
            return []
    
    def get_company_tickers(self) -> Dict[str, Any]:
        """
        Get all company tickers data.
        
        Returns:
            Company tickers data
        """
        url = f"{self.base_url}/files/company_tickers.json"
        
        try:
            response = self._make_request('GET', url)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get company tickers: {e}")
            return {}
    
    def get_filing_metadata(self, accession_number: str) -> Dict[str, Any]:
        """
        Get filing metadata from the index file.
        
        Args:
            accession_number: Filing accession number
            
        Returns:
            Filing metadata
        """
        # Extract CIK from accession number (first 10 digits)
        cik = accession_number[:10]
        url = f"{self.base_url}/Archives/edgar/data/{cik}/{accession_number}/{accession_number}-index.txt"
        
        try:
            response = self._make_request('GET', url)
            content = response.text
            
            # Parse the index file to extract metadata
            metadata = self._parse_index_file(content)
            return metadata
        except Exception as e:
            logger.error(f"Failed to get filing metadata: {e}")
            return {}
    
    def _parse_index_file(self, content: str) -> Dict[str, Any]:
        """
        Parse SEC index file to extract metadata.
        
        Args:
            content: Index file content
            
        Returns:
            Parsed metadata
        """
        metadata = {
            'filing_date': None,
            'acceptance_datetime': None,
            'form_type': None,
            'primary_document': None,
            'information_table': None,
            'amendments': []
        }
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse different sections
            if line.startswith('--DOCUMENT--'):
                # Document section
                continue
            elif line.startswith('--FILING--'):
                # Filing section
                continue
            elif '|' in line:
                # Data line
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    doc_type = parts[0]
                    company_name = parts[1]
                    cik = parts[2]
                    filing_date = parts[3]
                    
                    if doc_type == '13F-HR' or doc_type == '13F-HR/A':
                        metadata['form_type'] = doc_type
                        metadata['filing_date'] = filing_date
                    elif doc_type == 'INFORMATION TABLE':
                        metadata['information_table'] = company_name
                    elif doc_type == 'PRIMARY DOCUMENT':
                        metadata['primary_document'] = company_name
                    elif doc_type == '13F-HR/A':
                        # Amendment
                        metadata['amendments'].append({
                            'filing_date': filing_date,
                            'document': company_name
                        })
        
        return metadata
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
