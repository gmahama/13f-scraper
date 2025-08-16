#!/usr/bin/env python3
"""
Railway start script for 13F Filing Scraper.
This script ensures proper environment setup and starts the FastAPI server.
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_environment():
    """Set up the environment for Railway deployment."""
    print("🚀 Setting up 13F Filing Scraper for Railway...")
    
    # Create necessary directories
    dirs = ['output', 'cache', 'templates', 'static']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print("✅ Directories created/verified")
    
    # Check environment variables
    user_agent = os.getenv('SEC_USER_AGENT')
    if not user_agent:
        print("⚠️  Warning: SEC_USER_AGENT environment variable not set")
        print("   This is required for making requests to SEC EDGAR")
        print("   Set it in Railway environment variables:")
        print("   SEC_USER_AGENT='Your Name (your.email@domain.com) - Your Firm Name'")
    else:
        print(f"✅ SEC_USER_AGENT is set: {user_agent}")
    
    # Check PORT environment variable
    port = os.getenv('PORT', '8000')
    print(f"✅ Using port: {port}")
    
    return True

def start_server():
    """Start the FastAPI server directly."""
    print("\n🚀 Starting 13F Filing Scraper API Server...")
    
    try:
        # Import and run the FastAPI app directly
        from api import app
        import uvicorn
        
        port = int(os.getenv("PORT", 8000))
        print(f"🌐 Server will be available at: http://0.0.0.0:{port}")
        print("📊 API documentation: /docs")
        print("🔍 Health check: /health")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed:")
        print("pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if not setup_environment():
        sys.exit(1)
    
    if not start_server():
        sys.exit(1)
