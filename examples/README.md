# Examples

This folder contains small examples for the current project structure. They are meant for quick testing and for showing how the API, scraper, and user config fit together.

## Example List

| File | What It Shows | Uses Real Job Bank? |
| --- | --- | --- |
| `api_workflow.py` | Calls the local FastAPI app, runs one scrape, reads unposted jobs, marks a sample as posted, and prints stats. | Yes |
| `manual_scrape.py` | Uses the shared scraper in `src/` directly, without the API or Telegram bot. | Yes |
| `example_user_config.yaml` | Shows the shape of a user config file saved by the Telegram bot. | No |

`_paths.py` is only an import helper so examples can run from the project root without installing the package.

## Before Running

Activate the virtual environment:

```bash
source venv/bin/activate
```

Install Playwright's browser once if you have not already:

```bash
python -m playwright install chromium
```

## Run The Examples

API workflow:

```bash
# terminal 1
./start_api.sh

# terminal 2
python examples/api_workflow.py
```

Direct scraper:

```bash
python examples/manual_scrape.py
```

The API and scraper examples make real requests to Job Bank. Keep the page count small while testing.
