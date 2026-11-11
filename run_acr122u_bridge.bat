@echo off
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
    echo Python was not found on PATH.
    pause
    exit /b 1
)
if not exist ".venv-acr122u\Scripts\python.exe" (
    echo Creating the ACR122U Python environment...
    python -m venv .venv-acr122u
    if errorlevel 1 (
        echo Failed to create the Python environment.
        pause
        exit /b 1
    )
    echo Installing pyscard...
    call ".venv-acr122u\Scripts\python.exe" -m pip install -r scripts\requirements-acr122u.txt
    if errorlevel 1 (
        echo Failed to install pyscard.
        pause
        exit /b 1
    )
)
call ".venv-acr122u\Scripts\python.exe" scripts\acr122u_bridge.py
if errorlevel 1 (
    echo The ACR122U bridge stopped unexpectedly.
    pause
)
