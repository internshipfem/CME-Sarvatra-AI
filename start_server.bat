@echo off
echo ======================================================================
echo           Sarvatra AI - College of Military Engineering, Pune
echo                 Production Node Initializer (Air-Gapped)
echo ======================================================================

:: 1. Activate virtual environment if present
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

:: 2. Ensure database schema is migrated
echo [*] Applying migrations...
python manage.py migrate --noinput

:: 3. Collect static files
echo [*] Checking static assets...
python manage.py collectstatic --noinput

:: 4. Start Server
:: Checks if waitress is available; falls back cleanly to run_desktop.py / runserver
python -c "import waitress" 2>nul
if %errorlevel% equ 0 (
    echo [*] Starting production WSGI server (waitress) on port 8000...
    python -c "from waitress import serve; from ollama_web.wsgi import application; print('Server active at http://127.0.0.1:8000'); serve(application, host='0.0.0.0', port=8000)"
) else (
    echo [*] Starting desktop application server...
    python run_desktop.py
)

pause
