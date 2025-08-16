#!/usr/bin/env python3
"""
Command-line interface for 13F Filing Scraper.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple
import argparse
import logging

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

from logic import ThirteenFProcessor
from utils import (
    load_csv_funds, ensure_output_dir, get_latest_quarter,
    format_currency, normalize_cik
)
from models import FilingSummary

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="13F Filing Scraper - Extract and analyze SEC 13F-HR filings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape latest quarter for specific funds
  python cli.py scrape --funds "Citadel Advisors" "AQR Capital Management"
  
  # Scrape specific quarter by CIK
  python cli.py scrape --cik 0001167483 --quarter 2024Q4
  
  # Scrape with first-time filer filter
  python cli.py scrape --funds "New Fund LLC" --only-first-time
  
  # Scrape with holdings filters
  python cli.py scrape --funds "Large Fund" --min-holdings 100
  python cli.py scrape --funds "Small Fund" --between-holdings 10 50
  
  # Batch processing from CSV
  python cli.py scrape --funds-csv funds.csv --quarter 2024Q4
        """
    )
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape 13F filings')
    
    # Input options (mutually exclusive)
    input_group = scrape_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--funds', 
        nargs='+', 
        help='Fund names to search'
    )
    input_group.add_argument(
        '--ciks', 
        nargs='+', 
        help='CIKs to search'
    )
    input_group.add_argument(
        '--funds-csv', 
        type=str, 
        help='CSV file with fund information (columns: name, cik)'
    )
    
    # Quarter and filtering options
    scrape_parser.add_argument(
        '--quarter', 
        type=str, 
        help='Target quarter (e.g., 2024Q4). Default: latest available'
    )
    scrape_parser.add_argument(
        '--only-first-time', 
        action='store_true', 
        help='Return only first-time filers'
    )
    
    # Holdings filters
    scrape_parser.add_argument(
        '--min-holdings', 
        type=int, 
        help='Minimum number of holdings'
    )
    scrape_parser.add_argument(
        '--max-holdings', 
        type=int, 
        help='Maximum number of holdings'
    )
    scrape_parser.add_argument(
        '--between-holdings', 
        nargs=2, 
        type=int, 
        metavar=('MIN', 'MAX'),
        help='Holdings count range (min max)'
    )
    
    # Output options
    scrape_parser.add_argument(
        '--output-dir', 
        type=str, 
        default='./output',
        help='Output directory (default: ./output)'
    )
    scrape_parser.add_argument(
        '--cache-dir', 
        type=str, 
        default='./cache',
        help='Cache directory (default: ./cache)'
    )
    
    # Other options
    scrape_parser.add_argument(
        '--user-agent', 
        type=str, 
        help='SEC User-Agent string (overrides SEC_USER_AGENT env var)'
    )
    scrape_parser.add_argument(
        '--verbose', 
        action='store_true', 
        help='Enable verbose logging'
    )
    
    return parser


def validate_arguments(args: argparse.Namespace) -> bool:
    """Validate command-line arguments."""
    # Validate quarter format if provided
    if args.quarter:
        try:
            from utils import parse_quarter
            parse_quarter(args.quarter)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return False
    
    # Validate holdings filters
    if args.between_holdings:
        min_holdings, max_holdings = args.between_holdings
        if min_holdings >= max_holdings:
            console.print("[red]Error: MIN holdings must be less than MAX holdings[/red]")
            return False
    
    # Validate CSV file if provided
    if args.funds_csv:
        csv_path = Path(args.funds_csv)
        if not csv_path.exists():
            console.print(f"[red]Error: CSV file not found: {args.funds_csv}[/red]")
            return False
    
    return True


def display_banner():
    """Display application banner."""
    banner = Text("13F Filing Scraper", style="bold blue")
    subtitle = Text("SEC EDGAR 13F-HR Analysis Tool", style="dim")
    
    panel = Panel(
        f"{banner}\n{subtitle}",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(panel)


def display_summary_table(summaries: List[FilingSummary]) -> None:
    """Display filing summaries in a rich table."""
    if not summaries:
        console.print("[yellow]No filings found matching criteria[/yellow]")
        return
    
    table = Table(title="13F Filing Summaries")
    
    # Add columns
    table.add_column("Fund Name", style="cyan", no_wrap=True)
    table.add_column("CIK", style="green")
    table.add_column("Period", style="blue")
    table.add_column("First Time", style="magenta")
    table.add_column("Holdings", style="yellow", justify="right")
    table.add_column("Period End", style="dim")
    
    # Add rows
    for summary in summaries:
        first_time_text = "✓" if summary.is_first_time_filer else "✗"
        holdings_text = f"{summary.num_holdings:,}"
        
        table.add_row(
            summary.fund_name,
            summary.cik,
            summary.period,
            first_time_text,
            holdings_text,
            summary.period_end or "N/A"
        )
    
    console.print(table)


def display_statistics(summaries: List[FilingSummary], execution_time: float) -> None:
    """Display processing statistics."""
    if not summaries:
        return
    
    total_funds = len(summaries)
    first_time_count = sum(1 for s in summaries if s.is_first_time_filer)
    total_holdings = sum(s.num_holdings for s in summaries)
    avg_holdings = total_holdings / total_funds if total_funds > 0 else 0
    
    stats_table = Table(title="Processing Statistics", show_header=False)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="yellow")
    
    stats_table.add_row("Total Funds Processed", str(total_funds))
    stats_table.add_row("First-Time Filers", str(first_time_count))
    stats_table.add_row("Total Holdings", f"{total_holdings:,}")
    stats_table.add_row("Average Holdings per Fund", f"{avg_holdings:.1f}")
    stats_table.add_row("Execution Time", f"{execution_time:.2f}s")
    
    console.print(stats_table)


def save_summary_csv(summaries: List[FilingSummary], output_dir: str) -> str:
    """Save filing summaries to CSV file."""
    import pandas as pd
    from datetime import datetime
    
    output_path = ensure_output_dir(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"summary_{timestamp}.csv"
    filepath = output_path / filename
    
    # Convert to DataFrame - use model_dump() for Pydantic v2 compatibility
    df = pd.DataFrame([summary.model_dump() for summary in summaries])
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    
    return str(filepath)


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'scrape':
        return run_scrape(args)
    
    return 0


def run_scrape(args: argparse.Namespace) -> int:
    """Run the scrape command."""
    try:
        # Display banner
        display_banner()
        
        # Validate arguments
        if not validate_arguments(args):
            return 1
        
        # Set up logging
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Get User-Agent
        user_agent = args.user_agent or os.getenv('SEC_USER_AGENT')
        if not user_agent:
            console.print("[red]Warning: No SEC User-Agent set. Set SEC_USER_AGENT env var or use --user-agent[/red]")
        
        # Prepare fund list
        funds = []
        ciks = []
        
        if args.funds:
            funds = args.funds
        elif args.ciks:
            ciks = [normalize_cik(cik) for cik in args.ciks]
        elif args.funds_csv:
            try:
                fund_data = load_csv_funds(args.funds_csv)
                for fund in fund_data:
                    if 'name' in fund and fund['name'] != fund['cik']:
                        funds.append(fund['name'])
                    else:
                        ciks.append(fund['cik'])
            except Exception as e:
                console.print(f"[red]Error loading CSV file: {e}[/red]")
                return 1
        
        # Determine target quarter
        quarter = args.quarter or get_latest_quarter()
        console.print(f"[blue]Target Quarter: {quarter}[/blue]")
        
        # Display processing options
        options_table = Table(title="Processing Options", show_header=False)
        options_table.add_column("Option", style="cyan")
        options_table.add_column("Value", style="yellow")
        
        if funds:
            options_table.add_row("Funds", ", ".join(funds))
        if ciks:
            options_table.add_row("CIKs", ", ".join(ciks))
        
        options_table.add_row("Quarter", quarter)
        options_table.add_row("Only First-Time", "Yes" if args.only_first_time else "No")
        
        if args.min_holdings:
            options_table.add_row("Min Holdings", str(args.min_holdings))
        if args.max_holdings:
            options_table.add_row("Max Holdings", str(args.max_holdings))
        if args.between_holdings:
            min_h, max_h = args.between_holdings
            options_table.add_row("Holdings Range", f"{min_h} - {max_h}")
        
        console.print(options_table)
        console.print()
        
        # Process funds
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing funds...", total=None)
            
            with ThirteenFProcessor(
                user_agent=user_agent,
                cache_dir=args.cache_dir
            ) as processor:
                summaries = processor.process_funds(
                    funds=funds,
                    ciks=ciks,
                    quarter=quarter,
                    only_first_time=args.only_first_time,
                    min_holdings=args.min_holdings,
                    max_holdings=args.max_holdings,
                    between_holdings=args.between_holdings
                )
        
        execution_time = time.time() - start_time
        
        # Display results
        console.print()
        console.print("[green]Processing completed![/green]")
        console.print()
        
        display_summary_table(summaries)
        console.print()
        
        display_statistics(summaries, execution_time)
        console.print()
        
        # Save summary CSV
        if summaries:
            summary_file = save_summary_csv(summaries, args.output_dir)
            console.print(f"[green]Summary saved to: {summary_file}[/green]")
            
            # Display output files
            output_files = []
            for summary in summaries:
                base_filename = f"{summary.cik}_{summary.period}_holdings"
                csv_file = f"{base_filename}.csv"
                jsonl_file = f"{base_filename}.jsonl"
                output_files.extend([csv_file, jsonl_file])
            
            if output_files:
                console.print("\n[blue]Generated files:[/blue]")
                for file in output_files:
                    console.print(f"  • {file}")
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        return 1


if __name__ == '__main__':
    sys.exit(main())
