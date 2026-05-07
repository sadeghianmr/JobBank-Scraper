#!/bin/bash
# Keep a lightweight scheduler alive, and run API + bot only when the user is due.

set -euo pipefail

# User-editable settings.
JOBBANK_USER_ID="${JOBBANK_USER_ID:-6192760553}"
PROJECT_DIR="${PROJECT_DIR:-/Users/mrsadeghian/Desktop/MrS/Code/JobBank-Scraper}"
RUN_DURATION_SECONDS="${RUN_DURATION_SECONDS:-1800}"
API_URL="${API_URL:-http://localhost:8000}"
LOCK_FILE="${LOCK_FILE:-/tmp/jobbank-scraper-runner.lock}"

cd "$PROJECT_DIR"

mkdir -p logs/api logs/bot logs/errors

if [ -e "$LOCK_FILE" ]; then
    existing_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
    if [ -n "$existing_pid" ] && [ "$existing_pid" != "$$" ] && kill -0 "$existing_pid" 2>/dev/null; then
        echo "$(date) Stopping previous runner with PID $existing_pid."
        kill "$existing_pid" 2>/dev/null || true
        sleep 2
        if kill -0 "$existing_pid" 2>/dev/null; then
            echo "$(date) Previous runner still active; forcing stop."
            kill -9 "$existing_pid" 2>/dev/null || true
        fi
    fi
fi

echo "$$" > "$LOCK_FILE"

api_pid=""
bot_pid=""
started_api=0

stop_stack() {
    echo "$(date) Stopping JobBank API and bot..."

    if [ -n "$bot_pid" ] && kill -0 "$bot_pid" 2>/dev/null; then
        kill "$bot_pid" 2>/dev/null || true
        wait "$bot_pid" 2>/dev/null || true
    fi

    if [ "$started_api" -eq 1 ] && [ -n "$api_pid" ] && kill -0 "$api_pid" 2>/dev/null; then
        kill "$api_pid" 2>/dev/null || true
        wait "$api_pid" 2>/dev/null || true
    fi

    api_pid=""
    bot_pid=""
    started_api=0
}

cleanup() {
    stop_stack
    rm -f "$LOCK_FILE"
}

trap cleanup EXIT INT TERM

source venv/bin/activate

seconds_until_due() {
    JOBBANK_USER_ID="$JOBBANK_USER_ID" PROJECT_DIR="$PROJECT_DIR" python - <<'PY'
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

project_dir = Path(os.environ["PROJECT_DIR"])
user_id = os.environ["JOBBANK_USER_ID"]
config_path = project_dir / "user_configs" / f"user_{user_id}.yaml"

if not config_path.exists():
    print(-1)
    raise SystemExit

config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
scraping = config.get("scraping") or {}

try:
    interval_hours = float(scraping.get("interval_hours", 1))
except (TypeError, ValueError):
    interval_hours = 1

last_search = scraping.get("last_job_search_at")
if not last_search:
    print(0)
    raise SystemExit

try:
    parsed = datetime.fromisoformat(str(last_search).replace("Z", "+00:00"))
except ValueError:
    print(0)
    raise SystemExit

if parsed.tzinfo is None:
    parsed = parsed.replace(tzinfo=timezone.utc)
else:
    parsed = parsed.astimezone(timezone.utc)

due_at = parsed + timedelta(hours=interval_hours)
wait_seconds = int((due_at - datetime.now(timezone.utc)).total_seconds())
print(max(0, wait_seconds))
PY
}

run_stack_once() {
    if curl -fsS "$API_URL/health" >/dev/null 2>&1; then
        echo "$(date) API already running at $API_URL. Reusing it."
        started_api=0
    else
        echo "$(date) Starting JobBank API..."
        python -m uvicorn api.main:app --port 8000 >> logs/api/api.log 2>> logs/errors/errors.log &
        api_pid="$!"
        started_api=1

        echo "$(date) Waiting for API health check..."
        for _ in {1..30}; do
            if curl -fsS "$API_URL/health" >/dev/null 2>&1; then
                break
            fi
            sleep 1
        done
    fi

    if ! curl -fsS "$API_URL/health" >/dev/null 2>&1; then
        echo "$(date) API did not become healthy. Skipping this run."
        stop_stack
        return 1
    fi

    echo "$(date) Starting JobBank Telegram bot for user $JOBBANK_USER_ID..."
    python -m bot.main >> logs/bot/bot.log 2>> logs/errors/errors.log &
    bot_pid="$!"

    echo "$(date) Running for $RUN_DURATION_SECONDS seconds..."
    sleep "$RUN_DURATION_SECONDS"

    echo "$(date) Run window finished."
    stop_stack
}

echo "$(date) Scheduler started for user $JOBBANK_USER_ID."

while true; do
    wait_seconds="$(seconds_until_due)"

    if [ "$wait_seconds" -lt 0 ]; then
        echo "$(date) No config found for user $JOBBANK_USER_ID. Checking again in 1 hour."
        sleep 3600
        continue
    fi

    if [ "$wait_seconds" -gt 0 ]; then
        echo "$(date) User $JOBBANK_USER_ID is not due yet. Sleeping for $wait_seconds seconds."
        sleep "$wait_seconds"
        continue
    fi

    echo "$(date) User $JOBBANK_USER_ID is due. Starting run window."
    run_stack_once || true
    sleep 5
done
