#!/bin/bash

# Polymarket Scanner - Development Launcher
# Use this for local development without Docker

echo "🚀 Starting Polymarket Scanner in Development Mode..."

# Terminal 1: Backend
echo "📦 Starting Backend..."
osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'/backend\" && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload --port 8000"'

# Wait a bit
sleep 2

# Terminal 2: Frontend
echo "🎨 Starting Frontend..."
osascript -e 'tell application "Terminal" to do script "cd \"'$(pwd)'/frontend\" && npm install && npm run dev"'

echo ""
echo "✅ Development servers starting..."
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
