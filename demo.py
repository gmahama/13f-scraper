#!/usr/bin/env python3
"""
Demo script for 13F Filing Scraper.

This script demonstrates the tool's functionality without making actual API calls.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    parse_quarter, format_quarter, get_quarter_dates, 
    get_latest_quarter, normalize_cik, normalize_fund_name,
    format_currency, safe_int, safe_float
)
from models import FilingSummary


def demo_utils():
    """Demonstrate utility functions."""
    print("=== Utility Functions Demo ===")
    
    # Quarter parsing and formatting
    print("\n1. Quarter Functions:")
    quarter_str = "2024Q4"
    year, quarter = parse_quarter(quarter_str)
    print(f"  Parsed '{quarter_str}' -> Year: {year}, Quarter: {quarter}")
    
    formatted = format_quarter(2023, 1)
    print(f"  Formatted (2023, 1) -> '{formatted}'")
    
    start_date, end_date = get_quarter_dates(2024, 2)
    print(f"  Q2 2024 dates: {start_date} to {end_date}")
    
    latest = get_latest_quarter()
    print(f"  Latest available quarter: {latest}")
    
    # CIK normalization
    print("\n2. CIK Normalization:")
    ciks = ["1234567", "0001234567", "1234567890"]
    for cik in ciks:
        normalized = normalize_cik(cik)
        print(f"  '{cik}' -> '{normalized}'")
    
    # Fund name normalization
    print("\n3. Fund Name Normalization:")
    fund_names = ["Citadel Advisors LLC", "AQR Capital Management LP", "Bridgewater Associates"]
    for name in fund_names:
        normalized = normalize_fund_name(name)
        print(f"  '{name}' -> '{normalized}'")
    
    # Safe conversions
    print("\n4. Safe Conversions:")
    test_values = ["123", "123.45", "", "abc", None]
    for val in test_values:
        safe_int_val = safe_int(val)
        safe_float_val = safe_float(val)
        print(f"  '{val}' -> int: {safe_int_val}, float: {safe_float_val}")
    
    # Currency formatting
    print("\n5. Currency Formatting:")
    amounts = [1234.56, 1234567.89, 1234567890.12, 123.45, 0]
    for amount in amounts:
        formatted = format_currency(amount)
        print(f"  ${amount:,.2f} -> {formatted}")


def demo_models():
    """Demonstrate Pydantic models."""
    print("\n=== Pydantic Models Demo ===")
    
    # Create a sample filing summary
    summary = FilingSummary(
        fund_name="Citadel Advisors",
        cik="0001167483",
        period="2024Q4",
        period_end="2024-12-31",
        is_first_time_filer=False,
        num_holdings=1250,
        filing_url="https://www.sec.gov/Archives/edgar/data/0001167483/0001167483-24-000001.txt",
        info_table_url="https://www.sec.gov/Archives/edgar/data/0001167483/0001167483-24-000001-info.xml"
    )
    
    print(f"Created FilingSummary for {summary.fund_name}")
    print(f"  CIK: {summary.cik}")
    print(f"  Period: {summary.period}")
    print(f"  Holdings: {summary.num_holdings:,}")
    print(f"  First-time filer: {summary.is_first_time_filer}")
    
    # Convert to dict for serialization
    summary_dict = summary.model_dump()
    print(f"\nSerialized to dict with {len(summary_dict)} fields")
    print(f"  Keys: {list(summary_dict.keys())}")


def demo_parser_logic():
    """Demonstrate parser and logic concepts."""
    print("\n=== Parser & Logic Concepts ===")
    
    print("1. File Type Detection:")
    print("  - XML files: Start with <?xml or contain <informationTable")
    print("  - TXT files: Contain 'nameofissuer' or 'cusip' keywords")
    
    print("\n2. Holdings Parsing:")
    print("  - Extract CUSIP, issuer name, class title, value, shares")
    print("  - Handle voting authority (sole, shared, none)")
    print("  - Normalize data types and clean invalid entries")
    
    print("\n3. First-Time Filer Detection:")
    print("  - Check company submission history")
    print("  - Look for prior 13F-HR or 13F-HR/A filings")
    print("  - Ignore 13F-NT (notice) filings")
    print("  - Compare filing dates to determine earliest period")
    
    print("\n4. Holdings Filtering:")
    print("  - Minimum holdings count")
    print("  - Maximum holdings count")
    print("  - Range filtering (between min and max)")
    print("  - Filter combinations")


def demo_cli_usage():
    """Demonstrate CLI usage examples."""
    print("\n=== CLI Usage Examples ===")
    
    print("1. Basic Usage:")
    print("  python cli.py scrape --funds 'Citadel Advisors' --quarter 2024Q4")
    print("  python cli.py scrape --cik 0001167483 --min-holdings 100")
    
    print("\n2. First-Time Filer Detection:")
    print("  python cli.py scrape --funds 'New Fund LLC' --only-first-time")
    
    print("\n3. Holdings Filtering:")
    print("  python cli.py scrape --funds 'Large Fund' --min-holdings 500")
    print("  python cli.py scrape --funds 'Small Fund' --between-holdings 10 50")
    
    print("\n4. Batch Processing:")
    print("  python cli.py scrape --funds-csv funds.csv --quarter 2024Q4")
    
    print("\n5. Output Options:")
    print("  python cli.py scrape --funds 'Test Fund' --output-dir ./my_output")


def demo_api_usage():
    """Demonstrate API usage examples."""
    print("\n=== API Usage Examples ===")
    
    print("1. Start the API server:")
    print("  python api.py")
    
    print("\n2. Health check:")
    print("  curl http://localhost:8000/health")
    
    print("\n3. Scrape filings:")
    print("  curl -X POST http://localhost:8000/scrape \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"funds\": [\"Citadel Advisors\"], \"quarter\": \"2024Q4\"}'")
    
    print("\n4. List available files:")
    print("  curl http://localhost:8000/files")
    
    print("\n5. Download a file:")
    print("  curl http://localhost:8000/files/filename.csv")


def main():
    """Run all demos."""
    print("13F Filing Scraper - Demo & Examples")
    print("=" * 50)
    
    try:
        demo_utils()
        demo_models()
        demo_parser_logic()
        demo_cli_usage()
        demo_api_usage()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nNext steps:")
        print("1. Set SEC_USER_AGENT environment variable")
        print("2. Try the CLI: python cli.py --help")
        print("3. Run tests: python -m pytest tests/")
        print("4. Start API: python api.py")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        print("This might be expected if dependencies aren't fully installed")


if __name__ == "__main__":
    main()
