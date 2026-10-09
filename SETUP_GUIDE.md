# 🚀 Complete Setup & Installation Guide (Client System)

This guide provides all the exact commands and step-by-step instructions to set up and run the **GeM PDF Extractor & Contract Data Suite** on a fresh client system where **nothing is currently installed**.

---

## 📋 System Requirements
- **OS**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version 3.10, 3.11, or 3.12
- **Internet**: Required for the initial setup to install dependencies

---

## ⚡ FASTEST METHOD: Automated 1-Click Setup

We have included an automated installer script that handles Python detection, virtual environment creation, package installation, and folder structure setup.

1. Copy or Clone the project folder to the client's PC (e.g., on Desktop: `C:\Users\<Client>\Desktop\PDF TO EXCEL`).
2. **Double-click `setup.bat`** in the project root folder.
3. If Python is not installed, it will automatically download & install Python via Windows Package Manager (`winget`).
4. Once completed, simply double-click **`start_app.bat`** to start the application.

---

## 🛠️ MANUAL STEP-BY-STEP SETUP & COMMANDS

If you prefer to run the commands manually via **Command Prompt (cmd)** or **PowerShell**, follow the steps below:

### Step 1: Install Python (If not installed)

#### Option A: Install via Windows Terminal (Recommended - Fastest)
Open **PowerShell as Administrator** or Command Prompt and run:
```powershell
winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements --accept-package-agreements
```
*After installation, close and reopen your terminal to refresh system PATH.*

#### Option B: Install via Official Installer
1. Download Python 3.11 from: [python.org/downloads](https://www.python.org/downloads/)
2. Run the installer `.exe`.
3. ⚠️ **CRITICAL STEP**: At the bottom of the first setup screen, **check the box**:
   `[✓] Add python.exe to PATH`
4. Click **Install Now** and finish the installation.

#### Verify Python Installation:
Open Command Prompt and type:
```cmd
python --version
pip --version
```
*(Should output `Python 3.11.x` and pip version).*

---

### Step 2: Open Project Root in Terminal

Open Command Prompt or PowerShell, then navigate into the project directory:
```cmd
cd "C:\Users\<Your_Username>\Desktop\PDF TO EXCEL"
```

---

### Step 3: Create & Activate Python Virtual Environment

Create an isolated virtual environment inside `backend\venv`:

```cmd
:: Create virtual environment
python -m venv backend\venv

:: Activate virtual environment (Windows Command Prompt)
backend\venv\Scripts\activate.bat

:: OR if using PowerShell:
backend\venv\Scripts\Activate.ps1
```

*(Note: If PowerShell blocks script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and then run the activation script again).*

---

### Step 4: Upgrade Pip and Install Dependencies

With the virtual environment active (or directly using the venv python executable):

```cmd
:: Upgrade pip to latest version
backend\venv\Scripts\python.exe -m pip install --upgrade pip

:: Install all backend requirements
backend\venv\Scripts\pip.exe install -r backend\requirements.txt
```

---

### Step 5: Configure Environment Variables

Create the `backend\.env` file from the provided example template:

```cmd
copy backend\.env.example backend\.env
```

*(Open `backend\.env` in Notepad if you need to configure custom Supabase/PostgreSQL database credentials or host/port settings).*

---

### Step 6: Create Required Folders

Ensure the default input and output folders exist:
```cmd
if not exist "pdfs" mkdir pdfs
if not exist "output" mkdir output
```

---

## 🏃 How to Run the Application

### Option 1: 1-Click Launcher (Recommended for Daily Use)
Simply double-click:
```
start_app.bat
```
This will:
1. Start the FastAPI backend server on `http://127.0.0.1:8000/`.
2. Automatically launch your default web browser to the application interface.

### Option 2: Run via Terminal Command
```cmd
backend\venv\Scripts\python.exe run_app.py
```
Or directly with Uvicorn:
```cmd
backend\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 📂 Project Structure Overview

```text
PDF TO EXCEL/
├── backend/
│   ├── venv/                 # Python virtual environment (created by setup)
│   ├── extractor.py          # High-speed PDF parser engine
│   ├── main.py               # FastAPI backend & Static files server
│   ├── requirements.txt      # Python dependencies list
│   ├── security.py           # Rate limiting & token security
│   ├── storage_manager.py    # Excel & JSON writer with custom styling
│   └── user_manager.py       # User approval & whitelist manager
├── frontend/
│   ├── dist/                 # Pre-compiled React frontend UI
│   ├── src/                  # React source code
│   └── package.json          # Frontend build configuration (optional)
├── pdfs/                     # Default input folder for GeM PDFs
├── output/                   # Default output folder for gem_contracts.xlsx & .json
├── setup.bat                 # Automated 1-click setup script for client PC
├── start_app.bat             # 1-click launcher for client
├── run_app.py                # Python launcher with automatic browser popup
└── SETUP_GUIDE.md            # This instruction file
```

---

## ❓ Troubleshooting & FAQs

### 1. `'python'` is not recognized as an internal or external command
- **Cause**: Python was installed without checking "Add python.exe to PATH".
- **Fix**: Re-run the Python installer, choose **Modify**, check **Add Python to environment variables**, and complete setup. Alternatively, use the full path to Python.

### 2. PowerShell Script Execution Disabled (`PSSecurityException`)
- **Fix**: In PowerShell, run:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```

### 3. Port 8000 already in use
- **Cause**: Another service or a previous instance of the app is running.
- **Fix**: Open Task Manager and terminate any running `python.exe` processes, or run the app on a different port:
  ```cmd
  backend\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8080
  ```

### 4. Windows Defender / Firewall Prompt
- If Windows Firewall asks to allow Python network access, click **"Allow Access"** (Private Networks).
