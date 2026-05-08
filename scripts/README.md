# Mac Automation

This folder contains optional local scripts for running the API and bot on a Mac for a limited time.

## Run The Stack

```bash
scripts/run_stack.sh
```

The script checks the selected user's config first. If the user is due, it starts the API, waits until it is healthy, starts the bot, keeps both running for the configured run window, then stops both processes.

If the user is not due yet, the script sleeps until the exact next due time. It does not keep the API or bot running while waiting.

When a new runner starts, it stops any older runner recorded in the lock file first. This is useful after login, reloads, or manual restarts because the new process recalculates the next due time from the latest YAML config.

You can change the runtime:

```bash
RUN_DURATION_SECONDS=3600 scripts/run_stack.sh
```

The script has user-editable variables at the top:

```bash
JOBBANK_USER_ID="${JOBBANK_USER_ID:-6192760553}"
PROJECT_DIR="${PROJECT_DIR:-/Users/mrsadeghian/Code/JobBank-Scraper}"
RUN_DURATION_SECONDS="${RUN_DURATION_SECONDS:-3600}"
```

## LaunchAgent

`com.jobbank.scraper.plist.example` is a macOS LaunchAgent example. It runs the stack scheduler:

- when you log in
- keeps the lightweight scheduler alive
- starts the API and bot only when the selected user's interval is due
- sleeps until the next due time when the selected user is not due

Install it locally:

```bash
mkdir -p ~/Library/LaunchAgents
cp scripts/com.jobbank.scraper.plist.example ~/Library/LaunchAgents/com.jobbank.scraper.plist
launchctl load ~/Library/LaunchAgents/com.jobbank.scraper.plist
```

If you keep a Desktop shortcut, make it a symlink to the real project folder:

```bash
mkdir -p ~/Code
mv "/Users/mrsadeghian/Desktop/MrS/Code/JobBank-Scraper" ~/Code/JobBank-Scraper
ln -s ~/Code/JobBank-Scraper "/Users/mrsadeghian/Desktop/MrS/Code/JobBank-Scraper"
```

Stop it:

```bash
launchctl unload ~/Library/LaunchAgents/com.jobbank.scraper.plist
```

Check status:

```bash
launchctl list | grep jobbank
```
