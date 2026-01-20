#!/bin/bash
# Stop The Metadata Neighborhood
#
# Stops the API server, worker process, and frontend dev server.
#
# Usage: ./scripts/stop.sh

echo "🏘️  Stopping The Metadata Neighborhood..."
echo ""

# Stop frontend (Vite)
echo -n "Frontend:  "
if pkill -f 'vite' 2>/dev/null || pkill -f 'node.*vite' 2>/dev/null; then
    echo "✅ Stopped"
else
    echo "ℹ️  Was not running"
fi

# Stop API server
echo -n "API:       "
if pkill -f 'uvicorn api.main:app'; then
    echo "✅ Stopped"
else
    echo "ℹ️  Was not running"
fi

# Stop worker
echo -n "Worker:    "
if pkill -f 'run_worker.py'; then
    echo "✅ Stopped"
else
    echo "ℹ️  Was not running"
fi

# Stop watcher
echo -n "Watcher:   "
if pkill -f 'watch_transcripts.py'; then
    echo "✅ Stopped"
else
    echo "ℹ️  Was not running"
fi

echo ""
echo "The Neighborhood is closed. 👋"
