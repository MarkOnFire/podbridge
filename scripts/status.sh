#!/bin/bash
# Check status of The Metadata Neighborhood
#
# Usage: ./scripts/status.sh

echo "🏘️  The Metadata Neighborhood - Status"
echo "======================================"
echo ""

# Check API
echo -n "API Server (port 8000): "
if lsof -i :8000 > /dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Not running"
fi

# Check worker
echo -n "Worker:                 "
if pgrep -f 'run_worker.py' > /dev/null 2>&1; then
    echo "✅ Running (PID $(pgrep -f 'run_worker.py'))"
else
    echo "❌ Not running"
fi

# Check health endpoint
echo ""
echo "Health Check:"
if curl -s http://localhost:8000/api/system/health > /dev/null 2>&1; then
    QUEUE=$(curl -s http://localhost:8000/api/queue/stats 2>/dev/null)
    PENDING=$(echo "$QUEUE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pending',0))" 2>/dev/null || echo "?")
    IN_PROGRESS=$(echo "$QUEUE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('in_progress',0))" 2>/dev/null || echo "?")
    echo "  Queue: $PENDING pending, $IN_PROGRESS in progress"
else
    echo "  ❌ API not responding"
fi

echo ""
echo "URLs:"
echo "  http://metadata.neighborhood:8000"
echo "  http://localhost:8000"
