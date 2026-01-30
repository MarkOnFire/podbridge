#!/bin/bash
# Start The Metadata Neighborhood
#
# Starts the API server, worker process, and frontend dev server.
# Access at http://metadata.neighborhood:8000 (API) and http://metadata.neighborhood:3000 (Web)
#
# Usage: ./scripts/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "🏘️  Starting The Metadata Neighborhood..."
echo ""

# Check if metadata.neighborhood is configured
if ! grep -q "metadata.neighborhood" /etc/hosts 2>/dev/null; then
    echo "⚠️  metadata.neighborhood not found in /etc/hosts"
    echo "   Run: ./scripts/setup-local-domain.sh"
    exit 1
fi

# Ensure virtual environment exists (Python 3.13 for Langfuse compatibility)
if [ ! -d "venv13" ]; then
    echo "❌ Virtual environment not found. Run:"
    echo "   /opt/homebrew/bin/python3.13 -m venv venv13 && ./venv13/bin/pip install -r requirements.txt"
    exit 1
fi

# Check for node_modules in web folder
if [ ! -d "web/node_modules" ]; then
    echo "❌ Frontend dependencies not installed. Run:"
    echo "   cd web && npm install"
    exit 1
fi

# Activate venv
source venv13/bin/activate

# Create logs directory if needed
mkdir -p logs

# Check if API already running
if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use. Stop existing server first:"
    echo "   ./scripts/stop.sh"
    exit 1
fi

# Check if frontend already running
if lsof -i :3000 > /dev/null 2>&1; then
    echo "⚠️  Port 3000 is already in use. Stop existing server first:"
    echo "   ./scripts/stop.sh"
    exit 1
fi

# Run migrations
echo "📦 Running database migrations..."
./venv13/bin/alembic upgrade head

# Start API server
echo "🚀 Starting API server on port 8000..."
uvicorn api.main:app --reload --port 8000 >> logs/api.log 2>&1 &
API_PID=$!

# Start worker
echo "👷 Starting worker..."
./venv13/bin/python run_worker.py >> logs/worker.log 2>&1 &
WORKER_PID=$!

# Start transcript watcher
echo "👀 Starting transcript watcher..."
./venv13/bin/python watch_transcripts.py >> logs/watcher.log 2>&1 &
WATCHER_PID=$!

# Start frontend dev server
echo "🌐 Starting frontend dev server..."
cd web && npm run dev >> ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd "$PROJECT_DIR"

# Check if tunnel is enabled
if [ -f "$PROJECT_DIR/.env" ]; then
    ENABLE_TUNNEL=$(grep '^ENABLE_TUNNEL=' "$PROJECT_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'" | xargs)
fi
ENABLE_TUNNEL="${ENABLE_TUNNEL:-false}"

# Start Cloudflare Tunnel (optional)
TUNNEL_ENABLED=false
if [ "$ENABLE_TUNNEL" = "true" ]; then
    if ! command -v cloudflared &> /dev/null; then
        echo "⚠️  cloudflared not installed. Tunnel will not start."
        echo "   Install: brew install cloudflared"
        echo "   See: docs/REMOTE_ACCESS.md"
    elif [ ! -f "$PROJECT_DIR/config/cloudflared.yml" ]; then
        echo "⚠️  config/cloudflared.yml not found. Tunnel will not start."
    else
        echo "🌐 Starting Cloudflare Tunnel..."
        cloudflared tunnel --config "$PROJECT_DIR/config/cloudflared.yml" run >> logs/tunnel.log 2>&1 &
        TUNNEL_PID=$!
        TUNNEL_ENABLED=true
    fi
fi

# Wait a moment for startup
sleep 3

# Verify API
API_OK=false
if lsof -i :8000 > /dev/null 2>&1; then
    API_OK=true
fi

# Verify Frontend
FRONTEND_OK=false
if lsof -i :3000 > /dev/null 2>&1; then
    FRONTEND_OK=true
fi

# Verify metadata.neighborhood resolves correctly
ALIAS_OK=false
if curl -s --connect-timeout 2 http://metadata.neighborhood:8000/api/system/health > /dev/null 2>&1; then
    ALIAS_OK=true
fi

echo ""
if $API_OK && $FRONTEND_OK; then
    echo "✅ The Metadata Neighborhood is open!"
    echo ""
    echo "   Dashboard: http://metadata.neighborhood:3000"
    echo "   API:       http://metadata.neighborhood:8000"
    echo "   Health:    http://metadata.neighborhood:8000/api/system/health"
    echo "   Watcher:   Monitoring transcripts/ folder"
    echo ""
    if $ALIAS_OK; then
        echo "   ✅ metadata.neighborhood alias working"
    else
        echo "   ⚠️  metadata.neighborhood alias may not be resolving (try localhost)"
    fi
    if $TUNNEL_ENABLED; then
        sleep 2  # Give tunnel a moment to connect
        if pgrep -f 'cloudflared tunnel' > /dev/null 2>&1; then
            echo "   ✅ Tunnel:  https://cardigan.bymarkriechers.com"
        else
            echo "   ⚠️  Tunnel failed to start. Check logs/tunnel.log"
        fi
    fi
    echo ""
    echo "   Logs: tail -f logs/api.log logs/worker.log logs/watcher.log logs/frontend.log"
    echo "   Stop: ./scripts/stop.sh"
else
    if ! $API_OK; then
        echo "❌ API failed to start. Check logs/api.log"
    fi
    if ! $FRONTEND_OK; then
        echo "❌ Frontend failed to start. Check logs/frontend.log"
    fi
    exit 1
fi
