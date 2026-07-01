#!/bin/bash
# ==============================================================================
# YouTube Downloader Web-App Shutdown Script
# ==============================================================================

CLEAN=false

for arg in "$@"
do
    if [ "$arg" == "--clean" ]; then
        CLEAN=true
    fi
done

echo "Shutting down YouTube Downloader services..."

# 1. Stop Docker Compose if running
if command -v docker &> /dev/null; then
    echo "Stopping Docker Compose services..."
    docker compose -f web/docker-compose.yml down 2>/dev/null || true
fi

# 2. Stop Native services if running
echo "Stopping Native services..."
# Kill python backend
pkill -f "python3 app.py" 2>/dev/null || true
# Kill frontend vite server
pkill -f "vite" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true

if [ "$CLEAN" = true ]; then
    echo "Performing cleanup of environment..."
    # Remove logs
    rm -f web/backend/backend.log
    rm -f web/frontend/frontend.log
    
    # Remove Python caches
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    
    # Optional: Clean up downloads if you want a complete reset
    # rm -rf web/downloads/* 2>/dev/null || true
    
    echo "✅ Clean up finished."
fi

echo "✅ All services shut down successfully."
