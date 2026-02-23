# Quick Start Guide

Get up and running in 5 minutes.

## Install

```bash
# Clone and enter directory
git clone https://github.com/yourusername/JobBank-Scraper.git
cd JobBank-Scraper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install everything
pip install -r requirements.txt
python -m playwright install chromium
```

## Your First Search

```bash
python main.py -k "software developer" -l "Toronto" -p 3
```

This searches for "software developer" jobs in Toronto, scrapes 3 pages, and saves to `data/jobs_timestamp.csv`.

## Common Commands

```bash
# Different location
python main.py -k "data analyst" -l "Vancouver"

# More pages (25 jobs per page)
python main.py -k "engineer" -l "Montreal" -p 10

# Only Job Bank posts (no Indeed, etc)
python main.py -k "developer" -l "Toronto" --job-bank-only

# Export as JSON
python main.py -k "designer" -l "Calgary" -f json

# See database stats
python main.py --stats

# Export database
python main.py --export all_jobs.csv
```

## Use in Python

```python
from src.scraper import quick_search

jobs = quick_search(
    keyword="python developer",
    location="Toronto",
    max_pages=5
)

for job in jobs:
    print(f"{job['title']} at {job['company']}")
```

Check `examples/` folder for more code samples.

## Output

Results go to the `data/` folder:
- CSV/JSON/Excel files from each search
- SQLite database (`jobs.db`) tracking all jobs

Run the same search again? The database prevents duplicates.

## Need Help?

- Can't find jobs? Try your search on the website first
- Browser issues? Run `python -m playwright install --force chromium`
- Import errors? Make sure venv is activated

See the full [README](README.md) for detailed docs.
