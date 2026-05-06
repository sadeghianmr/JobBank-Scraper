# API

`api/` contains the FastAPI backend used by the Telegram bot. It starts scrape jobs, reads user databases, returns stats, and marks jobs as posted after the bot sends them to Telegram.

## Main Files

- `main.py`: FastAPI app setup, CORS, routers, and health check.
- `models.py`: request and response validation models.
- `routes/scraper.py`: scrape endpoint.
- `routes/jobs.py`: job query, stats, filter, delete, and mark-posted endpoints.
- `services/scraper_service.py`: runs the scraper from the API layer.
- `services/job_service.py`: database access and job filtering.

## Run

From the project root:

```bash
./start_api.sh
```

The API runs at `http://localhost:8000` by default. Interactive docs are available at `http://localhost:8000/docs`.

Logs are written to `logs/api/api.log`, with errors also written to `logs/errors/errors.log`.
