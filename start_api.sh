#!/bin/bash
# Start the FastAPI backend

echo "🚀 Starting JobBank API..."
echo "API will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

source venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000
