@echo off
title GeM PDF Extractor - Contract Data Suite
cd /d "%~dp0"

echo ===================================================
echo     GeM PDF Extractor - Contract Data Suite
echo ===================================================
echo.

set PYTHON_EXE=
if exist "backend\venv\Scripts\python.exe" (
    set "PYTHON_EXE=backend\venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [*] Starting GeM PDF Extraction Server...
echo [*] Web UI URL: http://127.0.0.1:8000/
echo.

start "" "http://127.0.0.1:8000/"

"%PYTHON_EXE%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

pause
