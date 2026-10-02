@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment. Is Python installed and on PATH?
        pause
        exit /b 1
    )
    echo [setup] Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -e "%~dp0" --quiet
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -m video_converter
if errorlevel 1 (
    echo.
    echo App exited with an error.
    pause
)
