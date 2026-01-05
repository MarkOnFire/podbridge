#!/bin/bash
# Setup local domain for The Metadata Neighborhood
#
# This script adds metadata.neighborhood to your /etc/hosts file
# so you can access the API at http://metadata.neighborhood:8000
#
# Usage: ./scripts/setup-local-domain.sh

set -e

DOMAIN="metadata.neighborhood"
HOSTS_FILE="/etc/hosts"

echo "🏘️  The Metadata Neighborhood - Local Domain Setup"
echo "=================================================="
echo ""

# Check if already configured
if grep -q "$DOMAIN" "$HOSTS_FILE" 2>/dev/null; then
    echo "✅ $DOMAIN is already configured in $HOSTS_FILE"
    echo ""
    echo "You can access the API at: http://$DOMAIN:8000"
    exit 0
fi

echo "This will add '$DOMAIN' to your hosts file."
echo "You'll be prompted for your password (sudo required)."
echo ""

# Add to hosts file
echo "127.0.0.1 $DOMAIN" | sudo tee -a "$HOSTS_FILE" > /dev/null

if grep -q "$DOMAIN" "$HOSTS_FILE"; then
    echo ""
    echo "✅ Success! $DOMAIN has been added."
    echo ""
    echo "You can now access the API at: http://$DOMAIN:8000"
    echo ""
    echo "To start the server, run:"
    echo "  ./scripts/start.sh"
else
    echo "❌ Failed to add $DOMAIN to hosts file."
    exit 1
fi
