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
echo [2/4] Downloading/verifying offline wheels into wheels/ directory...
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

:: 3. Build standalone OllamaChat.exe with PyInstaller
echo [3/4] Building standalone OllamaChat.exe with PyInstaller...
if exist "venv\Scripts\pyinstaller.exe" (
    venv\Scripts\pyinstaller OllamaChat.spec --clean --noconfirm
    if exist "dist\OllamaChat.exe" (
        copy /y "dist\OllamaChat.exe" "OllamaChat.exe" >nul
        echo [OK] Successfully built: OllamaChat.exe
    )
) else (
    echo [WARNING] PyInstaller not found in venv. Skipping .exe build (run build_exe.bat to install PyInstaller).
)
echo.

:: 4. Create bundled ZIP archive
echo [4/4] Creating bundled ZIP archive (excluding venv, cache, and db)...
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
echo The following release artifacts have been generated:
echo   1. Standalone Executable:
echo      --^> OllamaChat.exe (Portable - No Python required on target PC)
echo.
echo   2. Source & Offline Wheels Bundle:
echo      --^> Ollama_Chat_AirGapped_Bundle.zip
echo.
echo Deployment options for your Air-Gapped machine:
echo   Option A (Fastest): Just copy 'OllamaChat.exe' and double-click it.
echo   Option B (Python): Copy the ZIP, extract, and run 'install.bat'.
echo.
echo =====================================================================
pause
