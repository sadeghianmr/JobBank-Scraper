# Canada Job Bank Scraper

A Python scraper for [Canada's Job Bank](https://www.jobbank.gc.ca) that actually works. Built because the Job Bank website doesn't have an API, and manually browsing through job listings gets old fast.

## What It Does

- Scrapes job postings from Job Bank (keyword, location, you know the drill)
- Saves everything to a SQLite database so you don't scrape the same jobs twice
- Exports to CSV, JSON, or Excel whenever you want
- Filters out jobs from Indeed/CareerBeacon if you only want direct Job Bank postings
- Respects rate limits with built-in delays

## Quick Start

```bash
# Clone the repo
git clone https://github.com/yourusername/JobBank-Scraper.git
cd JobBank-Scraper

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
python -m playwright install chromium

# Run your first search
python main.py -k "python developer" -l "Toronto" -p 3
```

That's it. Check the `data/` folder for your results.

## Usage

### Command Line

```bash
# Basic search
python main.py -k "data analyst" -l "Vancouver"

# Multiple pages (25 jobs per page)
python main.py -k "software engineer" -l "Toronto" -p 5

# Only Job Bank postings (no Indeed, CareerBeacon, etc)
python main.py -k "developer" -l "Montreal" --job-bank-only

# Save as JSON instead of CSV
python main.py -k "designer" -l "Calgary" -f json

# Custom output filename
python main.py -k "engineer" -l "Toronto" -o my_search -f excel

# Check what's in your database
python main.py --stats

# Export database to CSV
python main.py --export my_jobs.csv

# Skip database (only save to file)
python main.py -k "analyst" -l "Montreal" --no-db

# Run with visible browser (for debugging)
python main.py -k "developer" -l "Toronto" --no-headless
```

### Python Code

```python
from src.scraper import quick_search

# Simple search
jobs = quick_search(
    keyword="data scientist",
    location="Toronto",
    max_pages=3
)

print(f"Found {len(jobs)} jobs")
```

More examples in the `examples/` directory.

### CLI Options Reference

| Option | Description |
|--------|-------------|
| `-k, --keyword` | Job keyword or title to search for |
| `-l, --location` | Location (city, province, or postal code) |
| `-p, --pages` | Number of pages to scrape (default: 1) |
| `-o, --output` | Custom output filename (without extension) |
| `-f, --format` | Output format: csv, json, or excel (default: csv) |
| `--job-bank-only` | Only include jobs posted directly on Job Bank |
| `--no-db` | Disable database storage (only save to file) |
| `--no-headless` | Run browser in visible mode (useful for debugging) |
| `--stats` | Show database statistics |
| `--export FILE` | Export database to CSV file |

## Features

### Database Storage
Jobs are automatically saved to SQLite. Run the same search tomorrow? It'll skip jobs you already have and only grab new ones. Use `--no-db` if you want to skip database storage.

### Source Filtering
Job Bank aggregates from multiple sites. Use `--job-bank-only` if you only want jobs posted directly to Job Bank.

### Multiple Export Formats
CSV, JSON, or Excel. Your choice. Set custom filenames with `-o`.

### Smart Scraping
- 2 second delay between pages (so we don't hammer their servers)
- Automatic retry on failures
- Tracks when jobs were first seen and last updated
- Headless by default (use `--no-headless` to see the browser)

## Project Structure

```
JobBank-Scraper/
├── src/
│   ├── scraper.py      # Main scraping logic
│   ├── database.py     # SQLite operations
│   ├── config.py       # Settings
│   └── utils.py        # Helper functions
├── examples/           # Usage examples
├── data/               # Your scraped data + database
├── main.py             # CLI interface
└── README.md           # You are here
```

## Database Schema

Single table called `JobBank`:

| Column | What It Is |
|--------|-----------|
| job_id | Unique ID from Job Bank |
| title | Job title |
| company | Company name |
| location | Where the job is |
| salary | Pay info (if available) |
| job_type | Remote/On-site/Hybrid |
| date_posted | When it was posted |
| url | Direct link to posting |
| source | Job Bank, Indeed, etc |
| scraped_at | When we first found it |
| last_seen | Last time we saw it |
| is_active | Still online or not |

## Configuration

Edit `src/config.py` if you want to change:
- Headless mode (default: enabled)
- Timeouts
- Delays between requests
- User agent strings

## Common Issues

**"No jobs found"**
- Make sure your keyword/location combo has results on the website first
- Try a broader search

**Browser installation fails**
```bash
python -m playwright install --force chromium
```

**Import errors**
Make sure you're in the project root and venv is activated.

## Legal Stuff

This is for personal use. Don't abuse it:
- Scrape responsibly (built-in delays help with this)
- Check Job Bank's Terms of Service
- Don't use this for commercial data harvesting

The website structure might change. If scraping stops working, open an issue.

## Contributing

Found a bug? PRs welcome. Please:
- Test your changes
- Keep the coding style consistent
- Update docs if needed

## License

MIT License - see LICENSE file

---

Built because job hunting is already hard enough.
