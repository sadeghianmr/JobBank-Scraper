# Source Package

`src/` contains the shared scraping, database, configuration, logging, and CLI code. Both the API and the command-line scraper depend on this package.

## Main Files

- `main.py`: command-line entry point for manual scraping, database stats, and exports.
- `scraper.py`: Playwright and BeautifulSoup scraper for Canada Job Bank search results.
- `database.py`: SQLite schema and job storage operations.
- `config.py`: shared constants, URL settings, timeouts, and request-limit bounds.
- `user_config.py`: helper for reading `user_configs/user_<id>.yaml`.
- `logging_config.py`: shared file logging setup for API, bot, scraper, and errors.
- `utils.py`: cleanup helpers, export helpers, and YAML search config loading.

## Run The CLI

From the project root:

```bash
python -m src.main -k "data analyst" -l "Vancouver" -p 3
python -m src.main -k "developer" -l "Canada" --job-bank-only --recent-jobs-only
python -m src.main --stats
python -m src.main --export jobs.csv
```

Use the API and bot for the normal multi-user workflow. Use this CLI when you want a quick manual scrape or export without Telegram.
