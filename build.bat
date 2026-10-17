@echo off
title Ollama Workspace - Build Air-Gapped Package
color 0B

echo =====================================================================
echo            Building Air-Gapped Deployment Package
echo =====================================================================
echo.

:: 1. Check Python
echo [1/3] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)

:: 2. Ensure offline wheels are downloaded
echo [2/3] Downloading/verifying offline wheels into wheels/ directory...
if not exist "wheels" mkdir wheels

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python -m pip download -r requirements.txt -d wheels --quiet
) else (
    python -m pip download -r requirements.txt -d wheels --quiet
)

if errorlevel 1 (
    echo [WARNING] Could not refresh wheels from pip. Using existing wheels if available.
) else (
    echo [OK] Offline wheels verified in wheels/
)
echo.

:: 3. Create bundled ZIP archive
echo [3/3] Creating bundled ZIP archive (excluding venv, cache, and db)...
if exist "venv\Scripts\python.exe" (
    venv\Scripts\python package_bundle.py
) else (
    python package_bundle.py
)

if errorlevel 1 (
    echo [ERROR] Failed to create ZIP bundle.
    pause
    exit /b 1
)

echo.
echo =====================================================================
echo                     BUILD COMPLETE!
echo =====================================================================
echo.
echo The deployment package has been generated:
echo   --^> Ollama_Chat_AirGapped_Bundle.zip
echo.
echo To install on any Air-Gapped machine:
echo   1. Copy 'Ollama_Chat_AirGapped_Bundle.zip' to the air-gapped machine.
echo   2. Extract the ZIP file into a folder.
echo   3. Double-click 'install.bat' to install the app completely offline.
echo   4. Double-click 'run_app.bat' to launch the app!
echo.
echo =====================================================================
pause
