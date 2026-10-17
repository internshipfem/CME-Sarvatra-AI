@echo off
title Build Standalone OllamaChat.exe
color 0B

echo =====================================================================
echo            Building Standalone OllamaChat.exe (PyInstaller)
echo =====================================================================
echo.

:: 1. Check Python and venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Please run install.bat first to set up the environment.
    pause
    exit /b 1
)

:: 2. Check PyInstaller
echo [1/3] Checking PyInstaller...
venv\Scripts\pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [*] Installing PyInstaller in venv...
    venv\Scripts\pip install "pyinstaller<6.0"
)

:: 3. Build Executable
echo [2/3] Compiling standalone executable from OllamaChat.spec...
echo (This may take 1-2 minutes to package all dependencies and templates)...
echo.
venv\Scripts\pyinstaller OllamaChat.spec --clean --noconfirm

if errorlevel 1 (
    echo [ERROR] PyInstaller compilation failed!
    pause
    exit /b 1
)

:: 4. Copy to root directory for easy access
if exist "dist\OllamaChat.exe" (
    echo.
    echo [3/3] Copying OllamaChat.exe to current folder...
    copy /y "dist\OllamaChat.exe" "OllamaChat.exe" >nul
    echo [OK] Standalone executable ready: OllamaChat.exe
)

echo.
echo =====================================================================
echo                     EXE BUILD SUCCESSFUL!
echo =====================================================================
echo.
echo You can now run:
echo   --^> OllamaChat.exe
echo.
echo It is completely self-contained. It will connect to your local Ollama,
echo run migrations automatically, and open your browser to http://127.0.0.1:8000.
echo.
echo =====================================================================
pause
