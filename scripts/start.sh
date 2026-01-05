#!/bin/bash
# Start The Metadata Neighborhood
#
# Starts the API server and worker process.
# Access at http://metadata.neighborhood:8000 (after running setup-local-domain.sh)
#
# Usage: ./scripts/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "🏘️  Starting The Metadata Neighborhood..."
echo ""

# Ensure virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run:"
    echo "   python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Create logs directory if needed
mkdir -p logs

# Check if already running
if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use. Stop existing server first:"
    echo "   ./scripts/stop.sh"
    exit 1
fi

# Run migrations
echo "📦 Running database migrations..."
./venv/bin/alembic upgrade head

# Start API server
echo "🚀 Starting API server on port 8000..."
uvicorn api.main:app --reload --port 8000 >> logs/api.log 2>&1 &
API_PID=$!

# Start worker
echo "👷 Starting worker..."
./venv/bin/python run_worker.py >> logs/worker.log 2>&1 &
WORKER_PID=$!

# Wait a moment for startup
sleep 2

# Verify
if lsof -i :8000 > /dev/null 2>&1; then
    echo ""
    echo "✅ The Metadata Neighborhood is open!"
    echo ""
    echo "   API:    http://metadata.neighborhood:8000"
    echo "   Health: http://metadata.neighborhood:8000/api/system/health"
    echo "   Logs:   tail -f logs/api.log logs/worker.log"
    echo ""
    echo "   Stop with: ./scripts/stop.sh"
else
    echo "❌ Failed to start. Check logs/api.log for errors."
    exit 1
fi
