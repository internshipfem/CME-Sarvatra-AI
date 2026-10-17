@echo off
title Sarvatra AI - Offline Air-Gapped Installer (CME Pune)
color 0A

echo =====================================================================
echo    Sarvatra AI - College of Military Engineering, Pune (Installer)
echo =====================================================================
echo.

:: 1. Check Python
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.7.9 (or 3.7+) and check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do echo [OK] Found: %%i
echo.

:: 2. Create virtual environment
echo [2/4] Creating virtual environment (venv)...
if exist "venv" (
    echo [*] Virtual environment 'venv' already exists. Reusing existing venv.
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
)
echo.

:: 3. Install packages 100% offline from bundled wheels
echo [3/4] Installing dependencies offline from bundled wheels...
if not exist "wheels" (
    echo [ERROR] 'wheels' directory not found! Offline installation cannot proceed.
    pause
    exit /b 1
)

venv\Scripts\python -m pip install --no-index --find-links=wheels -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install offline dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully.
echo.

:: 4. Apply database migrations
echo [4/4] Setting up database and default superuser...
venv\Scripts\python manage.py migrate --noinput
if errorlevel 1 (
    echo [ERROR] Failed to apply database migrations.
    pause
    exit /b 1
)
echo.

echo =====================================================================
echo                 INSTALLATION COMPLETED SUCCESSFULLY!
echo =====================================================================
echo.
echo Default Superuser Credentials:
echo   Username:     admin
echo   Password:     admin
echo   Employee ID:  EMP-001
echo.
echo To start the application anytime, simply run:
echo   run_app.bat
echo.
echo =====================================================================
echo.
pause
