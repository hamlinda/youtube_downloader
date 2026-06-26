@echo off
title YouTube Downloader Setup and Deploy (Windows)
color 0B
cls

echo ==============================================================================
echo  YouTube Downloader - Windows Setup & Deployment Utility
echo ==============================================================================
echo.

:menu
echo Select an option:
echo [1] Install Dependencies (Python + Node.js)
echo [2] Launch Desktop App (Local Python)
echo [3] Compile Desktop App to Single Executable (.exe)
echo [4] Run Web Application (Native Dev Mode)
echo [5] Run Web Application (Docker Compose Mode)
echo [6] Exit
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto install_deps
if "%choice%"=="2" goto run_desktop
if "%choice%"=="3" goto compile_desktop
if "%choice%"=="4" goto run_native_web
if "%choice%"=="5" goto run_docker_web
if "%choice%"=="6" goto exit_app
goto invalid_choice

:install_deps
echo.
echo === Installing Python Dependencies ===
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in your PATH.
    echo Please install Python 3.10+ and select "Add python.exe to PATH".
    pause
    goto menu
)
echo Python detected. Installing pip packages...
python -m pip install --upgrade pip
python -m pip install customtkinter yt-dlp imageio-ffmpeg pyinstaller fastapi uvicorn pydantic staticfiles
echo.
echo === Checking Node.js for Web Frontend ===
node --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Warning: Node.js is not installed or not in PATH.
    echo Node.js is only required if running the Web App natively without Docker.
) else (
    echo Node.js detected. Installing frontend packages...
    cd web\frontend
    call npm install
    cd ..\..
)
echo.
echo ✅ Dependency installation complete!
pause
cls
goto menu

:run_desktop
echo.
echo === Launching YouTube Downloader Desktop App ===
python desktop\desktop_app.py
pause
cls
goto menu

:compile_desktop
echo.
echo === Compiling Desktop App to Single Executable ===
python build.py
echo.
if exist "dist\youtube_downloader.exe" (
    echo ✅ Executable built successfully: .\dist\youtube_downloader.exe
) else (
    echo ❌ Error: PyInstaller build failed. Check the output logs above.
)
pause
cls
goto menu

:run_native_web
echo.
echo === Launching Native Web App ===
call run.bat --native
pause
cls
goto menu

:run_docker_web
echo.
echo === Launching Docker Web App ===
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not installed or not in PATH.
    echo Please install Docker Desktop and ensure the daemon is running.
    pause
    cls
    goto menu
)
call run.bat
pause
cls
goto menu

:invalid_choice
echo Invalid choice. Please select 1-6.
pause
cls
goto menu

:exit_app
echo Goodbye!
exit /b 0
