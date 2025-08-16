#!/usr/bin/env python3
"""
Example usage of the 13F Filing Scraper.

This script demonstrates how to use the scraper programmatically.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from logic import ThirteenFProcessor
from utils import get_latest_quarter


def example_basic_usage():
    """Basic usage example."""
    print("=== Basic Usage Example ===")
    
    # Set your SEC User-Agent (required)
    user_agent = "Your Name (your.email@domain.com) - Your Firm Name"
    
    # Create processor
    with ThirteenFProcessor(user_agent=user_agent) as processor:
        # Process a single fund by CIK
        summaries = processor.process_funds(
            ciks=["0001167483"],  # Citadel Advisors
            quarter="2024Q4"
        )
        
        print(f"Found {len(summaries)} filings")
        for summary in summaries:
            print(f"- {summary.fund_name}: {summary.num_holdings} holdings")
            print(f"  First-time filer: {summary.is_first_time_filer}")


def example_multiple_funds():
    """Example with multiple funds."""
    print("\n=== Multiple Funds Example ===")
    
    user_agent = "Your Name (your.email@domain.com) - Your Firm Name"
    
    with ThirteenFProcessor(user_agent=user_agent) as processor:
        # Process multiple funds by name
        summaries = processor.process_funds(
            funds=["Citadel Advisors", "AQR Capital Management"],
            quarter="2024Q4"
        )
        
        print(f"Processed {len(summaries)} funds")
        for summary in summaries:
            print(f"- {summary.fund_name} ({summary.cik}): {summary.num_holdings} holdings")


def example_with_filters():
    """Example with holdings filters."""
    print("\n=== Holdings Filters Example ===")
    
    user_agent = "Your Name (your.email@domain.com) - Your Firm Name"
    
    with ThirteenFProcessor(user_agent=user_agent) as processor:
        # Process funds with holdings filters
        summaries = processor.process_funds(
            ciks=["0001167483", "0001056903"],
            quarter="2024Q4",
            min_holdings=50,      # Only funds with 50+ holdings
            max_holdings=500      # And less than 500 holdings
        )
        
        print(f"Found {len(summaries)} funds matching criteria")
        for summary in summaries:
            print(f"- {summary.fund_name}: {summary.num_holdings} holdings")


def example_first_time_filers():
    """Example finding only first-time filers."""
    print("\n=== First-Time Filers Example ===")
    
    user_agent = "Your Name (your.email@domain.com) - Your Firm Name"
    
    with ThirteenFProcessor(user_agent=user_agent) as processor:
        # Find only first-time filers
        summaries = processor.process_funds(
            ciks=["0001167483", "0001056903", "0001350694"],
            quarter="2024Q4",
            only_first_time=True
        )
        
        print(f"Found {len(summaries)} first-time filers")
        for summary in summaries:
            print(f"- {summary.fund_name} ({summary.cik})")
            print(f"  Holdings: {summary.num_holdings}")
            print(f"  Filing URL: {summary.filing_url}")


def example_latest_quarter():
    """Example using the latest available quarter."""
    print("\n=== Latest Quarter Example ===")
    
    user_agent = "Your Name (your.email@domain.com) - Your Firm Name"
    
    with ThirteenFProcessor(user_agent=user_agent) as processor:
        # Get latest available quarter
        latest_quarter = get_latest_quarter()
        print(f"Latest available quarter: {latest_quarter}")
        
        # Process funds for latest quarter
        summaries = processor.process_funds(
            ciks=["0001167483"],
            quarter=latest_quarter
        )
        
        print(f"Found {len(summaries)} filings for {latest_quarter}")
        for summary in summaries:
            print(f"- {summary.fund_name}: {summary.num_holdings} holdings")


def example_error_handling():
    """Example with error handling."""
    print("\n=== Error Handling Example ===")
    
    user_agent = "Your Name (your.email@domain.com) - Your Firm Name"
    
    try:
        with ThirteenFProcessor(user_agent=user_agent) as processor:
            # Try to process an invalid CIK
            summaries = processor.process_funds(
                ciks=["0000000000"],  # Invalid CIK
                quarter="2024Q4"
            )
            
            print(f"Processed {len(summaries)} funds")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        print("This is expected for invalid CIKs")


def main():
    """Run all examples."""
    print("13F Filing Scraper - Example Usage")
    print("=" * 50)
    
    # Check if User-Agent is set
    if not os.getenv('SEC_USER_AGENT'):
        print("⚠️  Warning: SEC_USER_AGENT environment variable not set")
        print("   Set it to: 'Your Name (your.email@domain.com) - Your Firm Name'")
        print("   Or modify the examples below to include your User-Agent")
        print()
    
    try:
        # Run examples (comment out if you don't want to make actual API calls)
        # example_basic_usage()
        # example_multiple_funds()
        # example_with_filters()
        # example_first_time_filers()
        # example_latest_quarter()
        # example_error_handling()
        
        print("Examples completed!")
        print("\nTo run examples with actual API calls:")
        print("1. Set SEC_USER_AGENT environment variable")
        print("2. Uncomment the example calls in main()")
        print("3. Run: python example_usage.py")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        print("This is expected if SEC_USER_AGENT is not set")


if __name__ == "__main__":
    main()
