@echo off
title Ollama Air-Gapped AI Workspace
color 0B

echo =====================================================================
echo                Ollama Air-Gapped AI Workspace (Windows)
echo =====================================================================
echo.

:: 1. Check Virtual Environment
if not exist "venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Creating venv with Python 3.7.9...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Ensure Python 3.7.9 is installed and in PATH.
        pause
        exit /b 1
    )
    echo [*] Installing dependencies from requirements.txt...
    call venv\Scripts\pip install -r requirements.txt
)

:: 2. Check Ollama Service
echo [*] Checking local Ollama service...
ollama list >nul 2>&1
if errorlevel 1 (
    echo [WARNING] 'ollama' command was not found or Ollama service is not responding.
    echo Please make sure Ollama is installed and running on this machine.
    echo.
) else (
    echo [OK] Ollama is available. Discovered models:
    ollama list
    echo.
)

:: 3. Run database migrations
echo [*] Applying database migrations...
venv\Scripts\python manage.py migrate --noinput
echo.

:: 4. Launch web browser automatically
echo [*] Opening browser to http://127.0.0.1:8000...
start "" "http://127.0.0.1:8000"

:: 5. Start Django development server
echo =====================================================================
echo [*] Starting server on http://127.0.0.1:8000 (Press Ctrl+C to stop)
echo =====================================================================
echo.
venv\Scripts\python manage.py runserver 0.0.0.0:8000

pause
