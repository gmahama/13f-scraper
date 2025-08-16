# 📊 13F Filing Scraper

A production-quality Python tool for scraping and analyzing 13F-HR filings from SEC EDGAR with intelligent first-time filer detection and advanced holdings filtering capabilities.

## 🌟 Features

- **🔍 First-Time Filer Detection**: Automatically identifies funds filing 13F-HR for the first time
- **📈 Holdings Filtering**: Filter results by minimum/maximum holdings count or specific ranges
- **🌐 Web Interface**: Beautiful, responsive frontend for daily use
- **⚡ REST API**: Programmatic access via FastAPI endpoints
- **📊 Rich Output**: Generate CSV and JSONL files with detailed holdings data
- **🔄 Rate Limiting**: Respects SEC EDGAR guidelines (10 requests/second max)
- **💾 Intelligent Caching**: Reduces redundant API calls and improves performance

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/gmahama/13f-scraper.git
cd 13f-scraper

# Install dependencies
pip3 install -r requirements.txt

# Set SEC User-Agent (required)
export SEC_USER_AGENT="Your Name (your.email@domain.com) - Your Firm Name"
```

### 2. Web Interface (Recommended)

```bash
# Start the frontend server
python3 start_frontend.py

# Open your browser to: http://localhost:8000
```

### 3. Command Line Interface

```bash
# Basic usage
python3 cli.py scrape --funds "Citadel Advisors" "AQR Capital Management"

# First-time filers only
python3 cli.py scrape --funds "New Fund LLC" --only-first-time

# Holdings filtering
python3 cli.py scrape --funds "Large Fund" --min-holdings 100
python3 cli.py scrape --funds "Small Fund" --between-holdings 10 50

# Batch processing
python3 cli.py scrape --funds-csv sample_funds.csv --quarter 2024Q4
```

### 4. Programmatic Usage

```python
from logic import ThirteenFProcessor

with ThirteenFProcessor() as processor:
    results = processor.process_funds(
        funds=["Citadel Advisors"],
        quarter="2024Q4",
        min_holdings=100
    )
    
    for result in results:
        print(f"{result.fund_name}: {result.num_holdings} holdings")
        print(f"First-time filer: {result.is_first_time_filer}")
```

## 🌐 Web Interface Features

- **Input Methods**: Fund names, CIKs, or CSV file upload
- **Scraping Options**: Quarter selection, first-time filer filtering
- **Holdings Filters**: Minimum/maximum holdings count
- **Real-time Results**: Live progress and results display
- **File Downloads**: Direct links to generated CSV/JSONL files

## 📊 Output Files

The tool generates comprehensive output files:

### Summary File
- `summary_YYYYMMDD_HHMM.csv` - Overview of all processed filings
- Columns: fund_name, cik, period, is_first_time_filer, num_holdings, filing_url, info_table_url

### Holdings Files
- `{cik}_{period}_holdings.csv` - Detailed holdings per fund
- `{cik}_{period}_holdings.jsonl` - JSON lines format for programmatic processing

## 🔧 Configuration

### Environment Variables
```bash
# Required
SEC_USER_AGENT="Your Name (your.email@domain.com) - Your Firm Name"

# Optional
MAX_RETRIES=3
RATE_LIMIT_DELAY=0.1
```

### File Structure
```
13f-scraper/
├── 🌐 Frontend
│   ├── templates/          # HTML templates
│   ├── static/             # CSS and static assets
│   └── api.py              # FastAPI application
├── 🖥️ CLI & Core
│   ├── cli.py              # Command-line interface
│   ├── logic.py            # Core business logic
│   ├── sec_client.py       # SEC EDGAR client
│   └── parser.py           # 13F data parser
├── 🧪 Testing
│   ├── tests/              # Unit tests
│   └── pytest.ini         # Test configuration
└── 📚 Documentation
    ├── README.md           # This file
    ├── demo.py             # Interactive demo script
    └── example_usage.py    # Usage examples
```

## 🧪 Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_logic.py -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html
```

## 📡 API Endpoints

### Core Endpoints
- `GET /` - Main web interface
- `POST /scrape` - Scrape 13F filings
- `GET /health` - Health check

### File Management
- `GET /files` - List generated files
- `GET /files/{filename}` - Download specific file
- `DELETE /files/{filename}` - Delete specific file
- `DELETE /files` - Clear all files

## 🚨 Important Notes

### SEC Guidelines
- **Rate Limiting**: Maximum 10 requests per second
- **User-Agent**: Must include contact information
- **Respectful Usage**: Avoid overwhelming SEC servers

### First-Time Filer Logic
- Checks for prior 13F-HR or 13F-HR/A filings
- Ignores 13F-NT (notice) filings
- Compares filing dates to determine earliest period

## 🚀 Deployment

This tool is ready for deployment to various platforms:

- **Railway**: Easy deployment with `railway.json`
- **Heroku**: Use the provided `Procfile`
- **Render**: Web service deployment
- **Local Network**: Share with your team

See `DEPLOYMENT.md` for detailed deployment instructions.

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the demo mode for examples
- Review API documentation at `/docs`
- Run tests to verify functionality
- Check environment variable setup

---

**Happy Scraping! 🚀**
