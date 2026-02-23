"""Utility functions for the Job Bank scraper."""

import random
import time
import yaml
from datetime import datetime
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any
from src.config import USER_AGENTS, WAIT_TIME, DATA_DIR


def get_random_user_agent() -> str:
    """Return a random user agent string."""
    return random.choice(USER_AGENTS)


def wait_random(min_seconds: float = None, max_seconds: float = None) -> None:
    """
    Wait for a random amount of time to mimic human behavior.
    
    Args:
        min_seconds: Minimum wait time (default: WAIT_TIME)
        max_seconds: Maximum wait time (default: WAIT_TIME + 2)
    """
    min_time = min_seconds if min_seconds is not None else WAIT_TIME
    max_time = max_seconds if max_seconds is not None else WAIT_TIME + 2
    wait_time = random.uniform(min_time, max_time)
    time.sleep(wait_time)


def save_jobs_to_file(jobs: List[Dict[str, Any]], filename: str = None, 
                      format: str = "csv") -> str:
    """
    Save scraped jobs to a file.
    
    Args:
        jobs: List of job dictionaries
        filename: Output filename (without extension)
        format: Output format ('csv', 'json', or 'excel')
        
    Returns:
        Path to the saved file
    """
    if not jobs:
        print("No jobs to save.")
        return None
    
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    # Generate filename if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jobbank_jobs_{timestamp}"
    
    # Convert to DataFrame
    df = pd.DataFrame(jobs)
    
    # Save based on format
    if format.lower() == "csv":
        filepath = DATA_DIR / f"{filename}.csv"
        df.to_csv(filepath, index=False, encoding='utf-8')
    elif format.lower() == "json":
        filepath = DATA_DIR / f"{filename}.json"
        df.to_json(filepath, orient='records', indent=2, force_ascii=False)
    elif format.lower() in ["excel", "xlsx"]:
        filepath = DATA_DIR / f"{filename}.xlsx"
        df.to_excel(filepath, index=False, engine='openpyxl')
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    print(f"✓ Saved {len(jobs)} jobs to {filepath}")
    return str(filepath)


def clean_text(text: str) -> str:
    """
    Clean and normalize text by removing extra whitespace.
    
    Args:
        text: Raw text string
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    cleaned = " ".join(text.split()).strip()
    
    # Remove common prefixes from Job Bank
    prefixes_to_remove = ['Location ', 'Salary ', 'Employer ']
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    
    return cleaned


def format_job_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format and clean job data.
    
    Args:
        job_data: Raw job data dictionary
        
    Returns:
        Formatted job data
    """
    cleaned = {}
    for key, value in job_data.items():
        if isinstance(value, str):
            cleaned[key] = clean_text(value)
        else:
            cleaned[key] = value
    
    # Add scrape timestamp
    cleaned['scraped_at'] = datetime.now().isoformat()
    
    return cleaned


def load_search_config(config_file: str) -> Dict[str, Any]:
    """
    Load search configuration from a YAML file.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        Dictionary containing configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML file: {str(e)}")
    
    # Validate config structure
    if not isinstance(config, dict):
        raise ValueError("Config file must contain a dictionary")
    
    if 'searches' not in config:
        raise ValueError("Config file must contain 'searches' key")
    
    if not isinstance(config['searches'], list):
        raise ValueError("'searches' must be a list")
    
    # Validate each search entry
    for i, search in enumerate(config['searches']):
        if not isinstance(search, dict):
            raise ValueError(f"Search entry {i} must be a dictionary")
        
        if 'keyword' not in search and 'location' not in search:
            raise ValueError(f"Search entry {i} must have at least 'keyword' or 'location'")
    
    return config
