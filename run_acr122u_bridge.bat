@echo off
cd /d "%~dp0"
if not exist ".venv-acr122u\Scripts\python.exe" (
    py -m venv .venv-acr122u
    call ".venv-acr122u\Scripts\python.exe" -m pip install -r scripts\requirements-acr122u.txt
)
call ".venv-acr122u\Scripts\python.exe" scripts\acr122u_bridge.py
