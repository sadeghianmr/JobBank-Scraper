# Canada Job Bank Scraper

This project collects job postings from Canada Job Bank and manages them through a FastAPI backend and a Telegram bot.

I designed it this way because I wanted to practice building an API, connecting it to a real client, and keeping the scraper logic separate from the user interface. Right now the project runs locally, but the structure is ready for a future deployment where the API can run on a server and provide a better experience for users.

## What It Does

- Scrapes Canada Job Bank search results
- Stores jobs in SQLite databases
- Keeps each Telegram user's jobs and settings separate
- Lets users manage searches, blacklist keywords, and request new jobs from Telegram
- Posts new jobs to a configured Telegram channel
- Avoids reposting the same job twice
- Provides a FastAPI backend with API docs
- Includes a command-line scraper for manual checks and exports
- Includes tests for the API, services, database, and scraper workflow

## Tech Stack

- Python
- FastAPI
- Playwright
- BeautifulSoup
- SQLite
- python-telegram-bot
- Pytest

## Project Structure

```text
api/                  FastAPI backend
bot/                  Telegram bot
src/                  Shared scraper, database, config, utilities, and CLI
tests/                Unit and integration tests
examples/             Small API, scraper, and database examples
data/                 Local runtime databases and exports
logs/                 Runtime logs grouped by app area
user_configs/         Per-user Telegram configuration files
```

Folder details:

- [api/README.md](api/README.md)
- [bot/README.md](bot/README.md)
- [src/README.md](src/README.md)
- [tests/README.md](tests/README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)

## How It Works

The Telegram bot is the user-facing part of the app. It does not scrape directly. Instead, it calls the FastAPI backend.

The API receives scrape and database requests, then uses the shared code in `src/` to scrape Job Bank, store results, query jobs, and update posting status.

When a user clicks "Check for Jobs Now":

```text
Telegram bot
    -> FastAPI backend
    -> Job Bank scraper
    -> user SQLite database
    -> bot filters unposted jobs
    -> bot posts jobs to Telegram
    -> API marks posted jobs as posted
```

Each user has a config file:

```text
user_configs/user_<telegram_id>.yaml
```

Each user also has a separate database:

```text
data/user_<telegram_id>/jobs.db
```

## Setup

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Create a local environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
API_BASE_URL=http://localhost:8000
```

Do not commit `.env`, runtime databases, logs, or generated files.

## Run The App

Start the API:

```bash
./start_api.sh
```

Start the Telegram bot in another terminal:

```bash
./start_bot.sh
```

Then open Telegram and send `/start` to the bot.

The API docs are available at:

```text
http://localhost:8000/docs
```

## User Config Example

```yaml
channel_id: "@JobBankJobs"
scraping:
  interval_hours: 12
  headless: true
  job_bank_only: true
searches:
  - keyword: "Data Analyst"
    location: "Canada"
    pages: 10
filters:
  keywords_blacklist: []
posting:
  add_hashtags: true
  show_search_separator: true
user_limit_request: 1000
user_post_delay: 3
```

## Command-Line Scraper

The API and bot are the main workflow, but the CLI is useful for manual scraping, quick testing, and exports.

```bash
python -m src.main -k "data analyst" -l "Vancouver" -p 3
python -m src.main -k "developer" -l "Toronto" --job-bank-only
python -m src.main --stats
python -m src.main --export jobs.csv
```

## Testing

Run the test suite:

```bash
pytest
```

Run focused API/service tests:

```bash
pytest tests/services/test_job_service.py tests/api/test_jobs.py
```

Integration tests use the real Job Bank website, so they are slower and should be run only when needed:

```bash
pytest tests/integration -v
```

## Runtime Files

These are created while the app runs and should stay out of Git:

- `.env`
- `data/`
- `logs/**/*.log`
- `user_configs/user_*.yaml`
- `.coverage`
- `.pytest_cache/`
- `__pycache__/`

The repo keeps placeholder folders where useful, such as `logs/api/.gitkeep`.

## Notes

This project is for personal job-search automation and learning. Use reasonable request limits and delays. The scraper depends on the public Job Bank website structure, so selectors may need updates if the site changes.

## Future Improvements

- Deploy the API to a server
- Move from local SQLite files to a hosted database
- Add authentication for API access
- Add scheduled background scraping
- Improve monitoring and error reporting

## License

MIT License. See [LICENSE](LICENSE).
