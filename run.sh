#!/bin/bash
# ==============================================================================
# YouTube Downloader Web-App Startup Script
# ==============================================================================

# Exit on error
set -e

# Default to Docker mode
USE_DOCKER=true

# Parse command line arguments
for arg in "$@"
do
    if [ "$arg" == "--native" ]; then
        USE_DOCKER=false
    fi
done

cleanup() {
    echo ""
    echo "Stopping background services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Register cleanup on CTRL+C (SIGINT)
trap cleanup SIGINT

if [ "$USE_DOCKER" = true ]; then
    echo "========================================================="
    echo " Starting YouTube Downloader Web-App via Docker..."
    echo "========================================================="
    
    # 1. Verify Docker CLI is installed
    if ! command -v docker &> /dev/null; then
        echo "❌ Error: 'docker' command-line tool not found."
        echo "Please install Docker or run with the native option: ./run.sh --native"
        exit 1
    fi

    # 2. Verify Docker daemon is running
    if ! docker info &> /dev/null; then
        echo "❌ Error: Docker daemon is not running."
        echo "Please start the Docker daemon or run with: ./run.sh --native"
        exit 1
    fi

    # 3. Start Docker Compose
    echo "Running docker-compose..."
    docker compose -f web/docker-compose.yml up --build -d

    # Find mapped port
    MAPPED_PORT=$(docker compose -f web/docker-compose.yml port youtube-downloader 8000 2>/dev/null | grep -o -E "[0-9]+$")
    if [ -z "$MAPPED_PORT" ]; then
        MAPPED_PORT="8081" # Fallback
    fi

    echo "✅ Containers started successfully!"
    echo "🌐 Access the application at: http://localhost:$MAPPED_PORT"
    echo "📂 Downloaded media will be saved to: ./web/downloads"
    echo "---------------------------------------------------------"
    echo "To stop:   docker compose -f web/docker-compose.yml down"
    echo "To logs:   docker compose -f web/docker-compose.yml logs -f"
    echo "========================================================="

else
    echo "========================================================="
    echo " Starting YouTube Downloader Web-App Natively..."
    echo "========================================================="

    # 1. Start Backend FastAPI Server
    echo "Starting Backend API Server..."
    cd web/backend
    # Check and install requirements if needed
    pip3 install -r requirements.txt --quiet || pip install --break-system-packages -r requirements.txt --quiet
    
    # Run backend in the background
    python3 app.py > backend.log 2>&1 &
    BACKEND_PID=$!
    cd ../..

    # 2. Start Frontend Vite Server
    echo "Starting Frontend Dev Server..."
    cd web/frontend
    if [ ! -d "node_modules" ]; then
        echo "Installing Node modules..."
        npm install --quiet
    fi
    
    # Run Vite in background and pipe output
    npm run dev > frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ../..

    # Wait for Vite to bind and read the port
    echo "Waiting for dev server to start..."
    VITE_PORT=""
    for i in {1..15}; do
        VITE_PORT=$(grep -o -E "http://(localhost|[0-9\.]+):[0-9]+" web/frontend/frontend.log | head -n 1 | grep -o -E "[0-9]+")
        if [ ! -z "$VITE_PORT" ]; then
            break
        fi
        sleep 0.5
    done
    
    if [ -z "$VITE_PORT" ]; then
        VITE_PORT="5173" # Fallback
    fi

    echo "✅ Native services started successfully!"
    echo "🌐 Access the frontend at: http://localhost:$VITE_PORT"
    echo "🔌 Backend API running at: http://localhost:8000"
    echo "📝 Logs: web/backend/backend.log and web/frontend/frontend.log"
    echo "---------------------------------------------------------"
    echo "Press CTRL+C to stop both servers."
    echo "========================================================="

    # Keep script alive to hold trap listener
    while true; do
        sleep 1
    done
fi
