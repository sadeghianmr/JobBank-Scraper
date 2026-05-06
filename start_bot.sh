#!/bin/bash
# Start the Telegram bot (new modular version)

echo "🤖 Starting JobBank Telegram Bot (Modular Version)..."
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Check if API is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Warning: API doesn't seem to be running at http://localhost:8000"
    echo "Please start the API first in another terminal:"
    echo "  ./start_api.sh"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

source venv/bin/activate
python -m bot.main
