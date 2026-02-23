# Job Bank Examples

This directory contains example scripts showing how to use the scraper.

## Files

### 📘 `basic_usage.py`
Start here if you're new. Shows:
- Simple job searches
- Multi-page scraping
- Filtering by source (Job Bank only)
- Saving in different formats
- Disabling database

### 🔧 `advanced_usage.py`
For more control. Covers:
- Using the scraper class directly
- Running multiple searches
- Filtering results
- Visible browser mode
- Error handling

### 🗄️ `database_examples.py`
Working with the SQLite database:
- Checking statistics
- Querying stored jobs
- Exporting data
- Understanding deduplication

## How to Run

```bash
# Activate your virtual environment
source venv/bin/activate

# Run any example
python examples/basic_usage.py
python examples/advanced_usage.py
python examples/database_examples.py
```

Each file has multiple examples - uncomment the ones you want to try!

## Quick Tips

- All examples use real scraping (they hit the actual Job Bank website)
- Start with 1-2 pages while testing
- The database automatically prevents duplicates
- Check `python main.py --help` for all command-line options
