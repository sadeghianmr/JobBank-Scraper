# Bot

`bot/` contains the current Telegram bot. It handles user setup, search configuration, blacklist settings, database search, manual job checks, and posting new jobs to a Telegram channel.

## Main Files

- `main.py`: bot startup, service initialization, and handler registration.
- `handlers/`: Telegram commands, menus, callbacks, and conversation flows.
- `services/api_client.py`: HTTP client for the FastAPI backend.
- `services/config_manager.py`: reads and writes per-user YAML configuration files.
- `services/job_poster.py`: scrape, fetch unposted jobs, apply blacklist, post, and mark-as-posted.
- `ui/`: shared message text and inline keyboards.

## Run

Create `.env` in the project root:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
API_BASE_URL=http://localhost:8000
```

Start the API first, then run:

```bash
./start_bot.sh
```

User settings are saved in `user_configs/user_<telegram_id>.yaml`. Bot logs are written to `logs/bot/bot.log`, with errors also written to `logs/errors/errors.log`.
