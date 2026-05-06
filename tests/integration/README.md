# Integration Tests

These tests exercise the real scraper, SQLite database, and API endpoints together. They are slower than the fast tests described in [../README.md](../README.md) because they open a browser and may hit the live Job Bank website.

## Run

```bash
pytest tests/integration -v
pytest tests/integration -v -s
```

Run a single file:

```bash
pytest tests/integration/test_scraper_integration.py -v
```

## Scope

- `test_scraper_integration.py` verifies scraping, persistence, unposted-job filtering, and mark-as-posted behavior.
- `test_database_integration.py` verifies database search, lookup, deletion, and duplicate handling.

## When To Use

Run these tests before larger releases, after scraper selector changes, or after database/API changes. For day-to-day development, prefer the faster unit and API tests.

## Notes

The live website can change or temporarily block requests, so integration failures should be checked against network status and current Job Bank markup before assuming the application is broken.

If Chromium is missing:

```bash
python -m playwright install chromium
```
