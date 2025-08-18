"""
Pydantic models for API requests and responses.
"""

from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ScrapeRequest(BaseModel):
    """Request model for scraping 13F filings."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "funds": ["Citadel Advisors", "AQR Capital Management"],
                "quarter": "2024Q4",
                "only_first_time": False,
                "min_holdings": 50,
                "max_holdings": 1000,
                "between_holdings": [100, 500]
            }
        }
    )
    
    funds: Optional[List[str]] = Field(None, description="List of fund names to search")
    ciks: Optional[List[str]] = Field(None, description="List of CIKs to search")
    quarter: Optional[str] = Field(None, description="Quarter in format YYYYQn (e.g., 2024Q4)")
    only_first_time: bool = Field(False, description="Return only first-time filers")
    min_holdings: Optional[int] = Field(None, description="Minimum number of holdings")
    max_holdings: Optional[int] = Field(None, description="Maximum number of holdings")
    between_holdings: Optional[Tuple[int, int]] = Field(None, description="Holdings count range (min, max)")


class FirstTimeFilerDiscoveryRequest(BaseModel):
    """Request model for discovering first-time 13F filers."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "quarter": "2025Q2",
                "min_holdings": 1,
                "max_holdings": 10000
            }
        }
    )
    
    quarter: str = Field(..., description="Quarter to search for first-time filers (e.g., 2025Q2)")
    min_holdings: Optional[int] = Field(1, description="Minimum number of holdings to include")
    max_holdings: Optional[int] = Field(None, description="Maximum number of holdings to include")


class FirstTimeFiler(BaseModel):
    """Model for first-time filer data."""
    
    fund_name: str = Field(..., description="Name of the fund")
    cik: str = Field(..., description="CIK identifier")
    quarter: str = Field(..., description="Filing quarter (e.g., 2025Q2)")
    num_holdings: int = Field(..., description="Number of distinct holdings")
    filing_url: str = Field(..., description="URL to the filing")
    info_table_url: str = Field(..., description="URL to the information table")
    filing_date: str = Field(..., description="Filing date")
    accession_number: str = Field(..., description="Filing accession number")


class FirstTimeFilerDiscoveryResponse(BaseModel):
    """Response model for first-time filer discovery."""
    
    success: bool = Field(..., description="Whether the discovery was successful")
    message: str = Field(..., description="Status message")
    quarter: str = Field(..., description="Quarter searched")
    total_first_time_filers: int = Field(..., description="Total number of first-time filers found")
    first_time_filers: List[FirstTimeFiler] = Field(..., description="List of first-time filers")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    job_id: Optional[str] = Field(None, description="Background job ID if processing is ongoing")


class DiscoveryJobStatus(BaseModel):
    """Model for discovery job status."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status (pending, processing, completed, failed)")
    progress: Optional[float] = Field(None, description="Progress percentage (0-100)")
    message: str = Field(..., description="Status message")
    created_at: datetime = Field(default_factory=datetime.now, description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    total_filers_processed: Optional[int] = Field(None, description="Total filers processed")
    total_first_time_filers: Optional[int] = Field(None, description="Total first-time filers found")


class Holding(BaseModel):
    """Model for individual holding data."""
    
    cusip: str = Field(..., description="CUSIP identifier")
    issuer_name: str = Field(..., description="Name of the issuer")
    class_title: str = Field(..., description="Class of security")
    value_usd: float = Field(..., description="Value in USD")
    ssh_prnamt: int = Field(..., description="Shares or principal amount")
    ssh_prnamt_type: str = Field(..., description="Type of shares/principal amount")
    put_call: Optional[str] = Field(None, description="Put/call indicator")
    investment_discretion: str = Field(..., description="Investment discretion")
    other_managers: Optional[str] = Field(None, description="Other managers")
    voting_authority_sole: int = Field(..., description="Sole voting authority")
    voting_authority_shared: int = Field(..., description="Shared voting authority")
    voting_authority_none: int = Field(None, description="No voting authority")


class FilingSummary(BaseModel):
    """Model for filing summary data."""
    
    fund_name: str = Field(..., description="Name of the fund")
    cik: str = Field(..., description="CIK identifier")
    period: str = Field(..., description="Filing period (e.g., 2024Q4)")
    period_end: str = Field(..., description="Period end date")
    is_first_time_filer: bool = Field(..., description="Whether this is a first-time filer")
    num_holdings: int = Field(..., description="Number of distinct holdings")
    filing_url: str = Field(..., description="URL to the filing")
    info_table_url: str = Field(..., description="URL to the information table")
    earliest_filing_period: Optional[str] = Field(None, description="Earliest filing period if not first-time")


class ScrapeResponse(BaseModel):
    """Response model for scraping results."""
    
    success: bool = Field(..., description="Whether the scraping was successful")
    message: str = Field(..., description="Status message")
    summary: List[FilingSummary] = Field(..., description="List of filing summaries")
    holdings_files: List[str] = Field(..., description="List of generated holdings file paths")
    total_funds_processed: int = Field(..., description="Total number of funds processed")
    total_first_time_filers: int = Field(..., description="Total number of first-time filers")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    version: str = Field(..., description="API version")


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
