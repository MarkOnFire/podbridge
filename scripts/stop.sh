#!/bin/bash
# Stop The Metadata Neighborhood
#
# Stops the API server and worker process.
#
# Usage: ./scripts/stop.sh

echo "🏘️  Stopping The Metadata Neighborhood..."

# Stop API server
if pkill -f 'uvicorn api.main:app'; then
    echo "✅ API server stopped"
else
    echo "ℹ️  API server was not running"
fi

# Stop worker
if pkill -f 'run_worker.py'; then
    echo "✅ Worker stopped"
else
    echo "ℹ️  Worker was not running"
fi

echo ""
echo "The Neighborhood is closed. 👋"
