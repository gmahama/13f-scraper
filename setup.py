#!/usr/bin/env python3
"""
Setup script for 13F Filing Scraper.
"""

from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="13f-filing-scraper",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@domain.com",
    description="A production-quality Python tool for scraping SEC 13F-HR filings",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/13f-filing-scraper",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.11",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "13f-scraper=cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="sec, edgar, 13f, filings, investment, holdings, scraper",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/13f-filing-scraper/issues",
        "Source": "https://github.com/yourusername/13f-filing-scraper",
        "Documentation": "https://github.com/yourusername/13f-filing-scraper#readme",
    },
)
