# Architecture

## Overview

The current application is split into three layers: Telegram bot, FastAPI backend, and shared scraping/database code.

```text
┌─────────────────────────────────────────────────────────────┐
│                      Telegram User                          │
│  /start, /menu, add searches, blacklist, check now          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            v
┌─────────────────────────────────────────────────────────────┐
│                         bot/                                │
│  Telegram UI, user setup, search management, posting flow   │
│                                                             │
│  handlers/       User interactions and callback routing     │
│  services/       API client, config manager, job poster     │
│  ui/             Message templates and inline keyboards     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP
                            v
┌─────────────────────────────────────────────────────────────┐
│                         api/                                │
│  FastAPI backend for scraping, querying, stats, and updates │
│                                                             │
│  routes/         HTTP endpoints                             │
│  services/       Scraper orchestration and DB operations    │
│  models.py       Request/response validation                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            v
┌─────────────────────────────────────────────────────────────┐
│                         src/                                │
│  Shared scraper, SQLite manager, config, and utilities      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            v
┌─────────────────────────────────────────────────────────────┐
│                    SQLite per-user DBs                      │
│              data/user_<telegram_id>/jobs.db                │
└─────────────────────────────────────────────────────────────┘
```

## Main Runtime Flow

`start_api.sh` runs:

```bash
python -m uvicorn api.main:app --reload --port 8000
```

`start_bot.sh` runs:

```bash
python -m bot.main
```

The bot reads runtime secrets and service URLs from `.env`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
API_BASE_URL=http://localhost:8000
API_REQUEST_TIMEOUT_SECONDS=300
BOT_SCHEDULER_POLL_SECONDS=300
```

The current bot is the modular package in `bot/`. Older bot entry points were removed to keep the runtime path unambiguous.

## Check Now Flow

When a user clicks "Check for Jobs Now":

```text
Telegram callback
    |
    v
bot/main.py
    |
    v
bot/handlers/menu_handler.py
    |
    v
bot/services/job_poster.py
    |
    +--> POST /api/v1/scraper/scrape for each configured search
    |       |
    |       v
    |   api/services/scraper_service.py
    |       |
    |       v
    |   src/scraper.py -> src/database.py
    |
    +--> GET /api/v1/jobs/{user_id}?unposted_only=true
    |
    +--> apply blacklist
    |
    +--> post jobs to Telegram channel
    |
    +--> POST /api/v1/jobs/mark-posted
```

## Components

### `src/`

Shared code used by both the CLI and API.

- `main.py`: command-line scraper entry point. Run it with `python -m src.main`.
- `scraper.py`: opens Job Bank pages with Playwright and parses job cards with BeautifulSoup.
- `database.py`: owns the SQLite schema and job operations.
- `config.py`: shared constants such as URLs, timeouts, and request-limit bounds.
- `user_config.py`: reads per-user YAML settings outside the bot layer.
- `utils.py`: text cleanup, file export helpers, and YAML search config loading.

### `api/`

Backend service used by the Telegram bot.

- `api/main.py`: FastAPI app setup.
- `api/routes/scraper.py`: scrape endpoint.
- `api/routes/jobs.py`: job search, stats, mark-as-posted, delete.
- `api/services/scraper_service.py`: runs the synchronous scraper from the async API.
- `api/services/job_service.py`: resolves user databases and applies filters.

### `bot/`

Current Telegram bot implementation.

- `bot/main.py`: initializes services and registers handlers.
- `bot/services/api_client.py`: HTTP client for the API.
- `bot/services/config_manager.py`: reads/writes `user_configs/user_<id>.yaml`.
- `bot/services/job_poster.py`: scrape, fetch, filter, post, and mark-as-posted workflow.
- `bot/handlers/`: setup, menu, search, blacklist, database search, settings.
- `bot/ui/`: messages and inline keyboards.

## User Configuration

Each Telegram user has a YAML config:

```text
user_configs/user_<telegram_id>.yaml
```

Important fields:

```yaml
channel_id: "@JobBankJobs"
scraping:
  interval_hours: 12
  headless: true
  job_bank_only: true
  last_job_search_at: null
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

`user_limit_request` controls how many stored jobs the bot/API request when fetching unposted jobs or searching the database. The API falls back to this value when no explicit `limit` is provided.

`scraping.last_job_search_at` is updated after a successful scrape. The bot runs a background interval check while it is online. On startup and during each interval pass, it compares this timestamp with `scraping.interval_hours`; if enough time has passed, it runs the user's configured searches again.

## Job Bank Only Mode

If `scraping.job_bank_only` is true, the scraper adds Job Bank's source filter to the search URL:

```text
fsrc=16
```

Because the source filter is applied at the URL level, the scraper trusts that result set and marks those rows as `source = "Job Bank"`. If `job_bank_only` is false, the scraper uses the normal URL and parses the source from each listing.

## Database

Each user has an isolated SQLite database:

```text
data/user_<telegram_id>/jobs.db
```

Main table: `JobBank`

| Column | Purpose |
| --- | --- |
| `job_id` | Unique listing identifier |
| `title` | Job title |
| `company` | Employer |
| `location` | Job location |
| `salary` | Salary text |
| `job_type` | On-site, hybrid, remote, or similar |
| `date_posted` | Date shown on Job Bank |
| `url` | Direct job URL |
| `source` | Job Bank or external source |
| `scraped_at` | First scrape time |
| `last_seen` | Last time the listing was seen |
| `is_active` | Active/inactive flag |
| `posted_to_telegram` | Prevents duplicate posting |
| `telegram_message_id` | Message ID returned by Telegram |

## API Endpoints

When the API is running:

```text
GET  /health
POST /api/v1/scraper/scrape
GET  /api/v1/jobs/{user_id}
GET  /api/v1/jobs/{user_id}/stats
GET  /api/v1/jobs/{user_id}/{job_id}
POST /api/v1/jobs/filter
POST /api/v1/jobs/mark-posted
DEL  /api/v1/jobs/{user_id}/{job_id}
```
