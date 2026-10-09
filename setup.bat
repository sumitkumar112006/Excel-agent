@echo off
setlocal enabledelayedexpansion
title GeM PDF Extractor - Complete Automated Setup
cd /d "%~dp0"

echo =====================================================================
echo       GeM PDF Extractor & Contract Data Suite - Client Setup
echo =====================================================================
echo.

:: 1. Check for Python
echo [*] Step 1/5: Checking for Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [!] Python is NOT detected on this system.
        echo [*] Attempting automated Python 3.11 installation via Windows Package Manager (winget)...
        echo.
        winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements --accept-package-agreements
        if %errorlevel% neq 0 (
            echo.
            echo [X] Automated Python installation failed or winget is not available.
            echo [!] Please manually download and install Python from:
            echo     https://www.python.org/downloads/
            echo     *** IMPORTANT: Check the box "Add python.exe to PATH" during installation! ***
            echo.
            pause
            exit /b 1
        )
        echo [✓] Python installed successfully! Refreshing environment...
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%ProgramFiles%\Python311;%ProgramFiles%\Python311\Scripts;%PATH%"
    )
)

:: Find python executable command
set "PY_CMD=python"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PY_CMD=py"
)

echo [✓] Python is ready:
%PY_CMD% --version
echo.

:: 2. Create required folders
echo [*] Step 2/5: Creating required project directories (pdfs, output)...
if not exist "pdfs" mkdir pdfs
if not exist "output" mkdir output
echo [✓] Directories verified.
echo.

:: 3. Setup Virtual Environment in backend\venv
echo [*] Step 3/5: Setting up Python virtual environment (backend\venv)...
if not exist "backend\venv\Scripts\python.exe" (
    echo [*] Creating virtual environment...
    %PY_CMD% -m venv backend\venv
    if %errorlevel% neq 0 (
        echo [!] Virtual environment creation failed. Retrying in root folder...
        %PY_CMD% -m venv venv
    )
) else (
    echo [✓] Virtual environment already exists.
)

:: Detect venv python
set "VENV_PYTHON="
if exist "backend\venv\Scripts\python.exe" (
    set "VENV_PYTHON=backend\venv\Scripts\python.exe"
    set "VENV_PIP=backend\venv\Scripts\pip.exe"
) else if exist "venv\Scripts\python.exe" (
    set "VENV_PYTHON=venv\Scripts\python.exe"
    set "VENV_PIP=venv\Scripts\pip.exe"
) else (
    set "VENV_PYTHON=%PY_CMD%"
    set "VENV_PIP=%PY_CMD% -m pip"
)

echo [✓] Using environment Python: %VENV_PYTHON%
echo.

:: 4. Upgrade pip and install backend requirements
echo [*] Step 4/5: Installing required Python libraries from backend\requirements.txt...
"%VENV_PYTHON%" -m pip install --upgrade pip
"%VENV_PIP%" install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [X] Error occurred while installing dependencies.
    echo [!] Please ensure internet connection is active and rerun setup.bat.
    pause
    exit /b 1
)
echo [✓] All Python libraries installed successfully!
echo.

:: 5. Setup Environment Configuration (.env)
echo [*] Step 5/5: Checking configuration files...
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy "backend\.env.example" "backend\.env" >nul
        echo [✓] Created backend\.env from template backend\.env.example
    )
) else (
    echo [✓] backend\.env already exists.
)

echo.
echo =====================================================================
echo       🎉 SETUP COMPLETE! SYSTEM IS READY TO RUN
echo =====================================================================
echo.
echo To start the application anytime:
echo   -> Double-click "start_app.bat" in this folder
echo.
set /p START_NOW="Do you want to launch the application right now? (Y/N): "
if /i "%START_NOW%"=="Y" (
    echo [*] Launching application...
    start "" start_app.bat
)

exit /b 0
