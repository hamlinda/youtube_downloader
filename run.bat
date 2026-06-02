@echo off
rem ==============================================================================
rem YouTube Downloader Web-App Startup Script (Windows)
rem ==============================================================================

set USE_DOCKER=true

if "%1"=="--native" (
    set USE_DOCKER=false
)

if "%USE_DOCKER%"=="true" (
    echo =========================================================
    echo  Starting YouTube Downloader Web-App via Docker...
    echo =========================================================
    
    docker compose -f web\docker-compose.yml up --build -d
    
    echo.
    echo ✅ Containers started successfully!
    echo 🌐 Access the application at: http://localhost:8081
    echo 📂 Downloaded media will be saved to: .\web\downloads
    echo ---------------------------------------------------------
    echo To stop:   docker compose -f web\docker-compose.yml down
    echo To logs:   docker compose -f web\docker-compose.yml logs -f
    echo =========================================================
) else (
    echo =========================================================
    echo  Starting YouTube Downloader Web-App Natively...
    echo =========================================================

    echo Starting Backend API Server...
    cd web\backend
    pip install -r requirements.txt --quiet
    start "YouTube Downloader Backend" cmd /c "python app.py"
    cd ..\..

    echo Starting Frontend Dev Server...
    cd web\frontend
    if not exist "node_modules" (
        echo Installing Node modules...
        npm install --quiet
    )
    start "YouTube Downloader Frontend" cmd /c "npm run dev"
    cd ..\..

    echo.
    echo ✅ Native services started successfully in separate windows!
    echo 🌐 Access the frontend at: http://localhost:5173 (or next free port)
    echo 🔌 Backend API running at: http://localhost:8000
    echo =========================================================
)
