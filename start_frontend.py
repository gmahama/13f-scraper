#!/usr/bin/env python3
"""
Start the 13F Filing Scraper frontend server.
"""

import os
import sys
import subprocess
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env file loaded successfully")
except ImportError:
    print("⚠️  python-dotenv not installed, .env file won't be loaded")
    print("   Install with: pip3 install python-dotenv")

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        import jinja2
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip3 install -r requirements.txt")
        return False

def check_environment():
    """Check environment setup."""
    user_agent = os.getenv('SEC_USER_AGENT')
    if not user_agent:
        print("⚠️  Warning: SEC_USER_AGENT environment variable not set")
        print("   This is required for making requests to SEC EDGAR")
        print("   Set it in your .env file or with:")
        print("   export SEC_USER_AGENT='Your Name (your.email@domain.com) - Your Firm Name'")
        print()
    else:
        print(f"✅ SEC_USER_AGENT is set: {user_agent}")
    
    return True

def create_directories():
    """Create necessary directories if they don't exist."""
    dirs = ['output', 'cache', 'templates', 'static']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
    print("✅ Directories created/verified")

def start_server():
    """Start the FastAPI server."""
    print("\n🚀 Starting 13F Filing Scraper Frontend...")
    print("   Server will be available at: http://localhost:8000")
    print("   Press Ctrl+C to stop the server")
    print()
    
    try:
        # Start the server
        subprocess.run([
            sys.executable, "api.py"
        ], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting server: {e}")
        return False
    
    return True

def main():
    """Main function."""
    print("13F Filing Scraper - Frontend Server")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check environment
    check_environment()
    
    # Create directories
    create_directories()
    
    # Start server
    if start_server():
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
