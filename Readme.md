# GeM PDF to Excel & JSON Extraction Suite (v2.0)

Automated, high-speed contract data extraction suite for Government e-Marketplace (GeM) order PDFs.

---

## 🚀 How to Run the Application

### Option 1: Double-Click Launcher (Easiest for Windows)
Simply double click **`start_app.bat`**.
It will start the server and automatically open the application in your browser at:
`http://127.0.0.1:8000/`

---

### Option 2: Run via Terminal / Python
```bash
# Using venv python:
.\backend\venv\Scripts\python.exe run_app.py

# Or using uvicorn directly:
.\backend\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

---

## 🌟 Key Features
- **Human-Crafted Yellow & Porcelain White UI**: Designed with warm amber gold gradients, tactile buttons, rich typography (Outfit, Plus Jakarta Sans, JetBrains Mono), responsive layout, and smooth animations.
- **Full React + Vite Architecture**: Powered by React 18, Tailwind CSS, Lucide icons, and Canvas-Confetti celebration triggers.
- **High-Speed Non-LLM Parser**: Process 50+ PDFs in seconds using PyMuPDF and deterministic extraction rules.
- **Real-Time Live Telemetry**: Live extraction progress bar, file ticker, speed meter (PDFs/sec), elapsed counter, and pass/review distribution.
- **Interactive Records Explorer**: Instant search (keyboard shortcut `/`), status filtering pills (All, Passed, Review Needed), pagination, and 1-click contract inspector modal with JSON copy.
- **Master Excel & JSON Exports**: Export multi-tab formatted Excel spreadsheets (`output/gem_contracts.xlsx`) and structured JSON (`output/gem_contracts.json`).
- **Direct Windows Explorer Integration**: 1-click folder opening directly in Windows Explorer.

---

## 💻 Frontend Development (Optional)
If you wish to modify the React frontend with Hot Module Replacement (HMR):
```bash
cd frontend
npm run dev
# Vite runs at http://localhost:3000 and proxies API calls to port 8000
```
To re-build the production bundle:
```bash
cd frontend
npm run build
```

---

## 📡 API Endpoints Reference
- `GET /` — Serves Frontend Web UI (React SPA)
- `GET /api/health` — Backend health check & latency measurement
- `GET /api/config` — Returns default folders & paths
- `POST /api/scan` — Scans PDF directory and reports pending/processed counts
- `POST /api/extract` — Starts background extraction worker
- `GET /api/progress` — Real-time progress polling (speed, current file, percentage)
- `GET /api/records` — Fetch extracted records with search and pagination
- `GET /api/download/excel` — Downloads master Excel `.xlsx`
- `GET /api/download/json` — Downloads master JSON `.json`
- `POST /api/open-folder` — Opens output folder in Windows File Explorer