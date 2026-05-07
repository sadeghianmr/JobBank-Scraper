# Tests

The test suite is split into fast tests and integration tests.

```text
tests/
├── api/              FastAPI endpoint tests
├── services/         Service-layer tests
├── integration/      Real scraper/database/API workflow tests
└── conftest.py       Shared fixtures
```

## Fast Tests

Run all tests:

```bash
pytest
```

Run the main API and service tests:

```bash
pytest tests/services/test_job_service.py tests/api/test_jobs.py
```

These tests cover:

- Per-user database path handling
- Job filtering and pagination
- Last-30-days filtering for unposted jobs
- Mark-as-posted behavior
- Stats responses
- API validation
- User-configured request limits

## Integration Tests

Integration tests live in `tests/integration/` and use the real scraper/browser/database workflow. They are slower and may hit the live Job Bank website.

Run them manually when needed:

```bash
pytest tests/integration -v
```

See [integration/README.md](integration/README.md) for details.

## Generated Files

Do not commit generated test output:

```text
.coverage
htmlcov/
.pytest_cache/
__pycache__/
*.pyc
```

These are ignored by `.gitignore`.
