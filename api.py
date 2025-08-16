"""
FastAPI application for 13F Filing Scraper.
"""

import os
import time
from typing import List, Optional
from datetime import datetime
import logging

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from logic import ThirteenFProcessor
from models import (
    ScrapeRequest, ScrapeResponse, FilingSummary, 
    HealthResponse, ErrorResponse
)
from utils import (
    load_csv_funds, ensure_output_dir, get_latest_quarter,
    normalize_cik
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log environment setup
user_agent = os.getenv('SEC_USER_AGENT')
if user_agent:
    logger.info(f"✅ SEC_USER_AGENT loaded: {user_agent}")
else:
    logger.warning("⚠️  No SEC_USER_AGENT found in .env file or environment")

# Create FastAPI app
app = FastAPI(
    title="13F Filing Scraper API",
    description="API for scraping SEC 13F-HR filings with first-time filer detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates and static files
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main HTML frontend."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request):
    """Serve a demo page with sample data."""
    return templates.TemplateResponse("demo.html", {"request": request})


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_filings(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks
):
    """
    Scrape 13F filings based on request parameters.
    
    Args:
        request: Scrape request with filters and fund information
        background_tasks: Background tasks for async processing
        
    Returns:
        Scrape response with results and file paths
    """
    start_time = time.time()
    
    try:
        # Validate request
        if not request.funds and not request.ciks:
            raise HTTPException(
                status_code=400, 
                detail="Either 'funds' or 'ciks' must be provided"
            )
        
        # Get User-Agent from environment
        user_agent = os.getenv('SEC_USER_AGENT')
        if not user_agent:
            logger.warning("No SEC_USER_AGENT set in environment")
        
        # Process funds
        with ThirteenFProcessor(user_agent=user_agent) as processor:
            summaries = processor.process_funds(
                funds=request.funds,
                ciks=request.ciks,
                quarter=request.quarter,
                only_first_time=request.only_first_time,
                min_holdings=request.min_holdings,
                max_holdings=request.max_holdings,
                between_holdings=request.between_holdings
            )
        
        execution_time = time.time() - start_time
        
        # Generate file paths for holdings
        holdings_files = []
        for summary in summaries:
            base_filename = f"{summary.cik}_{summary.period}_holdings"
            csv_file = f"./output/{base_filename}.csv"
            jsonl_file = f"./output/{base_filename}.jsonl"
            
            # Check if files exist and add to list
            if os.path.exists(csv_file):
                holdings_files.append(csv_file)
            if os.path.exists(jsonl_file):
                holdings_files.append(jsonl_file)
        
        # Create response
        response = ScrapeResponse(
            success=True,
            message=f"Successfully processed {len(summaries)} funds",
            summary=summaries,
            holdings_files=holdings_files,
            total_funds_processed=len(summaries),
            total_first_time_filers=sum(1 for s in summaries if s.is_first_time_filer),
            execution_time=execution_time
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        execution_time = time.time() - start_time
        
        raise HTTPException(
            status_code=500,
            detail=f"Scraping failed: {str(e)}"
        )


@app.get("/files/{filename}")
async def download_file(filename: str):
    """
    Download generated files.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        File response
    """
    file_path = f"./output/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}"
        )
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )


@app.get("/files")
async def list_files():
    """
    List available output files.
    
    Returns:
        List of available files
    """
    output_dir = "./output"
    
    if not os.path.exists(output_dir):
        return {"files": []}
    
    files = []
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        if os.path.isfile(file_path):
            file_stat = os.stat(file_path)
            files.append({
                "filename": filename,
                "size": file_stat.st_size,
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            })
    
    return {"files": files}


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """
    Delete a generated file.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        Deletion confirmation
    """
    file_path = f"./output/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}"
        )
    
    try:
        os.remove(file_path)
        return {"message": f"File {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )


@app.delete("/files")
async def clear_files():
    """
    Clear all generated files.
    
    Returns:
        Clear confirmation
    """
    output_dir = "./output"
    
    if not os.path.exists(output_dir):
        return {"message": "No output directory found"}
    
    try:
        deleted_count = 0
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_count += 1
        
        return {"message": f"Deleted {deleted_count} files successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear files: {str(e)}"
        )


@app.get("/quarters")
async def get_available_quarters():
    """
    Get available quarters for scraping.
    
    Returns:
        List of available quarters
    """
    from utils import get_latest_quarter
    
    current_quarter = get_latest_quarter()
    
    # Generate list of recent quarters
    quarters = []
    current_year = int(current_quarter[:4])
    current_q = int(current_quarter[5])
    
    # Generate last 8 quarters
    for i in range(8):
        year = current_year
        quarter = current_q - i
        
        if quarter <= 0:
            quarter += 4
            year -= 1
        
        quarters.append(f"{year}Q{quarter}")
    
    return {
        "current_quarter": current_quarter,
        "available_quarters": quarters
    }


@app.get("/example-csv")
async def get_example_csv():
    """
    Get example CSV format for fund input.
    
    Returns:
        Example CSV content
    """
    example_content = """name,cik
Citadel Advisors,0001167483
AQR Capital Management,0001056903
Bridgewater Associates,0001350694
Two Sigma Investments,0001040279
Renaissance Technologies,0001029159"""
    
    return {"example_csv": example_content}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    
    return ErrorResponse(
        error="Internal server error",
        detail=str(exc)
    )


if __name__ == "__main__":
    # Run the application
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )
