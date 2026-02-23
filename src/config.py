"""Configuration settings for the Job Bank scraper."""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directory
DATA_DIR = BASE_DIR / "data"

# Job Bank URLs
JOB_BANK_BASE_URL = "https://www.jobbank.gc.ca"
JOB_SEARCH_URL = f"{JOB_BANK_BASE_URL}/jobsearch/jobsearch"

# Scraper settings
HEADLESS = True  # Run browser in headless mode
TIMEOUT = 30000  # Page load timeout in milliseconds
WAIT_TIME = 2    # Wait time between requests (in seconds)
MAX_RETRIES = 3  # Maximum number of retries for failed requests

# User agent to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Output formats
OUTPUT_FORMATS = ["csv", "json", "excel"]
DEFAULT_OUTPUT_FORMAT = "csv"

# Job search default parameters
DEFAULT_SEARCH_PARAMS = {
    "searchstring": "",
    "locationstring": "",
    "sort": "D",  # Date posted (newest first)
}
