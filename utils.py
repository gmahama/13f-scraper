"""
Utility functions for caching, date handling, and file operations.
"""

import os
import json
import hashlib
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Cache:
    """Simple on-disk JSON cache for CIK data and filing indices."""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a given key."""
        # Create a safe filename from the key
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data for a key."""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    # Check if cache is expired (24 hours)
                    if 'timestamp' in data:
                        cache_time = datetime.fromisoformat(data['timestamp'])
                        if (datetime.now() - cache_time).days < 1:
                            return data
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to read cache for {key}: {e}")
        return None
    
    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Set cached data for a key."""
        cache_path = self._get_cache_path(key)
        try:
            data['timestamp'] = datetime.now().isoformat()
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write cache for {key}: {e}")
    
    def clear(self, key: str = None) -> None:
        """Clear cache for a specific key or all cache."""
        if key:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
        else:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()


def parse_quarter(quarter_str: str) -> tuple[int, int]:
    """
    Parse quarter string (e.g., '2024Q4') into year and quarter number.
    
    Args:
        quarter_str: Quarter string in format 'YYYYQn'
        
    Returns:
        Tuple of (year, quarter_number)
        
    Raises:
        ValueError: If quarter string format is invalid
    """
    if not quarter_str or len(quarter_str) != 6:
        raise ValueError("Quarter must be in format 'YYYYQn' (e.g., '2024Q4')")
    
    try:
        year = int(quarter_str[:4])
        quarter = int(quarter_str[5])
        
        if quarter < 1 or quarter > 4:
            raise ValueError("Quarter must be 1, 2, 3, or 4")
        
        if year < 2000 or year > 2030:
            raise ValueError("Year must be between 2000 and 2030")
        
        return year, quarter
    except ValueError as e:
        raise ValueError(f"Invalid quarter format: {quarter_str}") from e


def format_quarter(year: int, quarter: int) -> str:
    """Format year and quarter into 'YYYYQn' string."""
    return f"{year}Q{quarter}"


def get_quarter_dates(year: int, quarter: int) -> tuple[date, date]:
    """
    Get start and end dates for a quarter.
    
    Args:
        year: Year
        quarter: Quarter number (1-4)
        
    Returns:
        Tuple of (start_date, end_date)
    """
    quarter_starts = {
        1: date(year, 1, 1),
        2: date(year, 4, 1),
        3: date(year, 7, 1),
        4: date(year, 10, 1)
    }
    
    quarter_ends = {
        1: date(year, 3, 31),
        2: date(year, 6, 30),
        3: date(year, 9, 30),
        4: date(year, 12, 31)
    }
    
    return quarter_starts[quarter], quarter_ends[quarter]


def get_latest_quarter() -> str:
    """Get the latest available quarter based on current date."""
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Determine current quarter
    if current_month <= 3:
        quarter = 4
        year = current_year - 1
    elif current_month <= 6:
        quarter = 1
        year = current_year
    elif current_month <= 9:
        quarter = 2
        year = current_year
    else:
        quarter = 3
        year = current_year
    
    # For 13F filings, there's typically a delay, so use the previous quarter
    # This ensures we're looking for filings that are more likely to be available
    if quarter == 1:
        quarter = 4
        year = year - 1
    else:
        quarter = quarter - 1
    
    return format_quarter(year, quarter)


def normalize_cik(cik: str) -> str:
    """
    Normalize CIK to 10-digit zero-padded format.
    
    Args:
        cik: CIK string (may be unpadded)
        
    Returns:
        Normalized 10-digit CIK
    """
    # Remove any non-digit characters
    cik_clean = ''.join(filter(str.isdigit, str(cik)))
    
    # Pad to 10 digits
    return cik_clean.zfill(10)


def normalize_fund_name(name: str) -> str:
    """
    Normalize fund name for consistent comparison.
    
    Args:
        name: Raw fund name
        
    Returns:
        Normalized fund name
    """
    if not name:
        return ""
    
    # Convert to uppercase and trim whitespace
    normalized = name.upper().strip()
    
    # Remove common suffixes
    suffixes = [' LLC', ' LP', ' L.P.', ' INC', ' CORP', ' CORPORATION']
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    
    return normalized.strip()


def ensure_output_dir(output_dir: str = "./output") -> Path:
    """Ensure output directory exists and return Path object."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    return output_path


def generate_filename(cik: str, period: str, suffix: str = "holdings") -> str:
    """
    Generate standardized filename for output files.
    
    Args:
        cik: CIK identifier
        period: Filing period (e.g., '2024Q4')
        suffix: File suffix
        
    Returns:
        Generated filename
    """
    normalized_cik = normalize_cik(cik)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{normalized_cik}_{period}_{suffix}_{timestamp}"


def save_dataframe_to_files(df, cik: str, period: str, output_dir: str = "./output") -> Dict[str, str]:
    """
    Save DataFrame to CSV and JSONL files.
    
    Args:
        df: Pandas DataFrame to save
        cik: CIK identifier
        period: Filing period
        output_dir: Output directory
        
    Returns:
        Dictionary with file paths
    """
    output_path = ensure_output_dir(output_dir)
    
    # Generate filenames
    base_filename = f"{normalize_cik(cik)}_{period}"
    csv_filename = f"{base_filename}_holdings.csv"
    jsonl_filename = f"{base_filename}_holdings.jsonl"
    
    csv_path = output_path / csv_filename
    jsonl_path = output_path / jsonl_filename
    
    # Save CSV
    df.to_csv(csv_path, index=False)
    
    # Save JSONL
    df.to_json(jsonl_path, orient='records', lines=True, date_format='iso')
    
    return {
        'csv': str(csv_path),
        'jsonl': str(jsonl_path)
    }


def load_csv_funds(csv_path: str) -> List[Dict[str, str]]:
    """
    Load fund information from CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of dictionaries with fund information
    """
    import pandas as pd
    
    try:
        df = pd.read_csv(csv_path)
        required_columns = ['cik']
        
        # Check required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Normalize CIKs
        df['cik'] = df['cik'].astype(str).apply(normalize_cik)
        
        # Handle optional name column
        if 'name' not in df.columns:
            df['name'] = df['cik']
        
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"Failed to load CSV file {csv_path}: {e}")
        raise


def format_currency(value: float) -> str:
    """Format currency value for display."""
    if value >= 1e9:
        return f"${value/1e9:.2f}B"
    elif value >= 1e6:
        return f"${value/1e6:.2f}M"
    elif value >= 1e3:
        return f"${value/1e3:.2f}K"
    else:
        return f"${value:.2f}"


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to integer with default fallback."""
    try:
        if value is None or value == '':
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default fallback."""
    try:
        if value is None or value == '':
            return default
        return float(value)
    except (ValueError, TypeError):
        return default
