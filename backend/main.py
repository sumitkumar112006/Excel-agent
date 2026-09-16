"""
main.py — GeM PDF Extraction Backend API
=========================================
Standalone FastAPI backend for GeM PDF to Excel & JSON extraction.
Run with:  python main.py  OR  uvicorn main:app --reload
"""

import os
import sys
import glob
import time
from pathlib import Path
from typing import Optional, List

# ── Path Setup ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent          # backend/
ROOT_DIR = BASE_DIR.parent                          # PDF TO EXCEL/

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ── Third-Party ─────────────────────────────────────────────────────
from fastapi import FastAPI, BackgroundTasks, Depends, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fastapi.staticfiles import StaticFiles

# ── Internal Modules ────────────────────────────────────────────────
from extractor import process_single_pdf
from storage_manager import (
    save_and_append_records,
    save_batch_records,
    load_existing_json,
    load_batch_json,
    clear_batch_json,
    ensure_output_dir,
    write_styled_excel,
    EXCEL_FILENAME,
    JSON_FILENAME,
    BATCH_EXCEL_FILENAME,
    BATCH_JSON_FILENAME,
    DEFAULT_OUTPUT_DIR,
)
from security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    get_current_user,
    require_approved_user,
    require_admin_user,
    safe_resolve_path,
)
from user_manager import (
    load_user_data,
    check_or_register_user,
    approve_user,
    revoke_user,
    add_admin,
    record_user_scan,
    record_user_extraction,
)

# ── App & CORS ──────────────────────────────────────────────────────
app = FastAPI(
    title="GeM PDF Extraction API",
    version="2.0.0",
    description="Secure Backend API with Firebase JWT Auth for GeM PDF extraction.",
)

# Security Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = ROOT_DIR / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
ASSETS_DIR = DIST_DIR / "assets"

# Mount /assets if built React bundle exists
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# ── Default Directories ────────────────────────────────────────────
DEFAULT_INPUT_DIR = ROOT_DIR / "pdfs"
DEFAULT_OUTPUT_PATH = ROOT_DIR / DEFAULT_OUTPUT_DIR
ensure_output_dir(str(DEFAULT_OUTPUT_PATH))

# ── Background Task State ──────────────────────────────────────────
CURRENT_TASK = {
    "is_running": False,
    "current_file": "",
    "processed_count": 0,
    "total_count": 0,
    "pass_count": 0,
    "review_count": 0,
    "start_time": 0,
    "elapsed_seconds": 0.0,
    "speed_fps": 0.0,
    "completed": False,
    "message": "Ready",
    "batch_records": [],
}


# ── Request Models ──────────────────────────────────────────────────
class ScanRequest(BaseModel):
    input_dir: str = "./pdfs"
    output_dir: str = "./output"


class ExtractRequest(BaseModel):
    input_dir: str = "./pdfs"
    output_dir: str = "./output"
    reprocess_all: bool = False


class OpenFolderRequest(BaseModel):
    folder_path: str = "./output"


class SelectFolderRequest(BaseModel):
    initial_dir: Optional[str] = None
    title: Optional[str] = "Select Folder"


class ApproveUserRequest(BaseModel):
    email: str
    role: str = "client"


class RevokeUserRequest(BaseModel):
    email: str


# ── Helper: Resolve Paths with Security Checks ───────────────────────
def _resolve(path_str: str) -> Path:
    """Safely resolve path with path traversal protection."""
    return safe_resolve_path(path_str, ROOT_DIR)


# ═══════════════════════════════════════════════════════════════════
#  STATIC & FRONTEND SERVING
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def serve_index():
    """Serve the frontend single-page application."""
    dist_index = DIST_DIR / "index.html"
    if dist_index.exists():
        return FileResponse(str(dist_index))
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "status": "online",
        "service": "GeM PDF Extraction API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/styles.css")
async def serve_css():
    """Serve main stylesheet."""
    css_path = FRONTEND_DIR / "styles.css"
    if css_path.exists():
        return FileResponse(str(css_path), media_type="text/css")
    return JSONResponse(status_code=404, content={"error": "styles.css not found"})


@app.get("/app.js")
async def serve_js():
    """Serve frontend javascript controller."""
    js_path = FRONTEND_DIR / "app.js"
    if js_path.exists():
        return FileResponse(str(js_path), media_type="application/javascript")
    return JSONResponse(status_code=404, content={"error": "app.js not found"})


@app.get("/app_icon.ico")
async def serve_icon():
    """Serve app favicon."""
    ico_path = ROOT_DIR / "app_icon.ico"
    if ico_path.exists():
        return FileResponse(str(ico_path), media_type="image/x-icon")
    return JSONResponse(status_code=404, content={"error": "app_icon.ico not found"})


# ═══════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health_check():
    """Health-check endpoint for frontend connectivity."""
    return {
        "status": "online",
        "service": "GeM PDF Extraction API",
        "version": "2.0.0",
        "security": "Firebase JWT Verified (RS256)",
        "docs": "/docs",
    }


@app.get("/api/auth/me")
async def get_auth_me(user: Optional[dict] = Depends(get_current_user)):
    """Inspect and verify current authenticated Firebase user from JWT Bearer token."""
    if not user:
        return {"authenticated": False, "message": "No active authenticated session"}
    return {
        "authenticated": True,
        "uid": user.get("uid"),
        "email": user.get("email"),
        "provider": user.get("firebase", {}).get("sign_in_provider", "password"),
        "claims": user,
    }


@app.get("/api/auth/status")
async def get_auth_status(user: Optional[dict] = Depends(get_current_user)):
    """Check approval & whitelist status of current Firebase user."""
    if not user:
        return {
            "status": "unauthenticated",
            "email": None,
            "role": "none",
            "message": "Sign in required."
        }
    
    return check_or_register_user(
        email=user.get("email"),
        uid=user.get("uid"),
        name=user.get("name", "")
    )


# ═══════════════════════════════════════════════════════════════════
#  ADMIN WHITELIST MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/api/admin/users")
async def get_admin_users(admin: dict = Depends(require_admin_user)):
    """List all whitelisted clients, admin emails, pending requests, and global PDF scan counts."""
    return load_user_data()


@app.get("/api/admin/stats")
async def get_admin_stats(admin: dict = Depends(require_admin_user)):
    """Return comprehensive PDF scanning & extraction statistics across all users and accounts."""
    data = load_user_data()
    return {
        "global_stats": data.get("global_stats", {}),
        "activity_log": data.get("activity_log", []),
        "user_stats": data.get("user_stats", {}),
    }


@app.post("/api/admin/approve")
async def approve_client(req: ApproveUserRequest, admin: dict = Depends(require_admin_user)):
    """Approve/whitelist a client email."""
    return approve_user(req.email, approved_by=admin.get("email", "admin"), role=req.role)


@app.post("/api/admin/revoke")
async def revoke_client(req: RevokeUserRequest, admin: dict = Depends(require_admin_user)):
    """Revoke access for a client email."""
    return revoke_user(req.email)


@app.get("/api/config")
async def get_config():
    """Return default input/output directory paths."""
    return {
        "default_input_dir": str(DEFAULT_INPUT_DIR.resolve()),
        "default_output_dir": str(DEFAULT_OUTPUT_PATH.resolve()),
        "cwd": str(ROOT_DIR),
    }


def find_pdf_files(folder_path: Path) -> List[str]:
    """Finds unique PDF files in a folder case-insensitively without duplicate entries."""
    if not folder_path.exists() or not folder_path.is_dir():
        return []
    found = {}
    for f in folder_path.iterdir():
        if f.is_file() and f.suffix.lower() == ".pdf":
            found[os.path.normcase(str(f.resolve()))] = str(f.resolve())
    return sorted(list(found.values()))


@app.post("/api/scan")
async def scan_folder(req: ScanRequest, user: Optional[dict] = Depends(require_approved_user)):
    """Scan input folder, report PDF counts, and record scan audit log for the caller."""
    input_path = _resolve(req.input_dir)
    output_path = _resolve(req.output_dir)

    if not input_path.exists() or not input_path.is_dir():
        return JSONResponse(status_code=400, content={"error": f"Input folder not found: {input_path}"})

    pdf_files = find_pdf_files(input_path)
    existing_records = load_existing_json(str(output_path))
    processed_filenames = {r.get("file_name") for r in existing_records}
    unprocessed = [f for f in pdf_files if os.path.basename(f) not in processed_filenames]

    caller_email = user.get("email") if user else "anonymous"
    # Record scan in persistent stats
    record_user_scan(
        email=caller_email,
        total_scanned=len(pdf_files),
        new_count=len(unprocessed),
        input_path=str(input_path)
    )

    return {
        "input_dir": str(input_path),
        "output_dir": str(output_path),
        "total_pdfs": len(pdf_files),
        "already_processed": len(pdf_files) - len(unprocessed),
        "new_to_process": len(unprocessed),
        "sample_files": [os.path.basename(f) for f in pdf_files[:5]],
        "caller_email": caller_email,
        "caller_role": user.get("role") if user else "guest",
    }


# ── Extraction Worker (Background) ─────────────────────────────────
def _run_extraction(input_dir: str, output_dir: str, reprocess_all: bool, user_email: str = "anonymous"):
    """Background worker that processes PDFs, updates CURRENT_TASK state, and records stats."""
    global CURRENT_TASK
    CURRENT_TASK.update({
        "is_running": True,
        "completed": False,
        "processed_count": 0,
        "pass_count": 0,
        "review_count": 0,
        "start_time": time.time(),
        "message": "Starting extraction...",
    })

    try:
        input_path = _resolve(input_dir)
        output_path = _resolve(output_dir)
        ensure_output_dir(str(output_path))

        pdf_files = find_pdf_files(input_path)
        existing_records = load_existing_json(str(output_path))
        processed_filenames = {r.get("file_name") for r in existing_records}

        files_to_run = pdf_files if reprocess_all else [
            f for f in pdf_files if os.path.basename(f) not in processed_filenames
        ]

        CURRENT_TASK["total_count"] = len(files_to_run)

        if not files_to_run:
            CURRENT_TASK.update({"is_running": False, "completed": True, "message": "All files are already processed."})
            return

        batch_results = []
        t0 = time.time()

        for idx, pdf_file in enumerate(files_to_run, start=1):
            filename = os.path.basename(pdf_file)
            CURRENT_TASK["current_file"] = filename
            CURRENT_TASK["processed_count"] = idx

            try:
                record = process_single_pdf(pdf_file)
                batch_results.append(record)
                if record.get("validation_status") == "PASS":
                    CURRENT_TASK["pass_count"] += 1
                else:
                    CURRENT_TASK["review_count"] += 1
            except Exception as e:
                CURRENT_TASK["review_count"] += 1
                batch_results.append({
                    "file_name": filename,
                    "contract_no": "NA",
                    "validation_status": "REVIEW",
                    "validation_errors": [str(e)],
                })

            elapsed = max(0.001, time.time() - t0)
            CURRENT_TASK["elapsed_seconds"] = round(elapsed, 2)
            CURRENT_TASK["speed_fps"] = round(idx / elapsed, 1)

        CURRENT_TASK["message"] = "Updating Excel & JSON records..."
        save_batch_records(batch_results, str(output_path))
        CURRENT_TASK["batch_records"] = batch_results

        # Record user extraction stats
        record_user_extraction(
            email=user_email,
            processed_count=len(batch_results),
            pass_count=CURRENT_TASK["pass_count"],
            review_count=CURRENT_TASK["review_count"],
            output_path=str(output_path)
        )

        CURRENT_TASK.update({
            "is_running": False,
            "completed": True,
            "message": f"Extraction complete. {len(batch_results)} files processed.",
        })
    except Exception as err:
        CURRENT_TASK.update({
            "is_running": False,
            "completed": True,
            "message": f"Extraction failed: {str(err)}",
        })
    finally:
        CURRENT_TASK["is_running"] = False


@app.post("/api/extract")
async def start_extraction(req: ExtractRequest, bg_tasks: BackgroundTasks, user: Optional[dict] = Depends(require_approved_user)):
    """Kick off PDF extraction in the background (Requires Approved User)."""
    if CURRENT_TASK["is_running"]:
        return JSONResponse(status_code=400, content={"error": "An extraction task is already running."})

    caller_email = user.get("email") if user else "anonymous"
    bg_tasks.add_task(_run_extraction, req.input_dir, req.output_dir, req.reprocess_all, caller_email)
    return {
        "status": "started", 
        "message": "Extraction process initiated.",
        "caller_email": caller_email,
        "caller_role": user.get("role") if user else "guest",
    }


@app.get("/api/progress")
async def get_progress():
    """Return current extraction progress."""
    total = CURRENT_TASK["total_count"]
    processed = CURRENT_TASK["processed_count"]
    pct = round((processed / total) * 100, 1) if total > 0 else 0.0

    return {
        "is_running": CURRENT_TASK["is_running"],
        "completed": CURRENT_TASK["completed"],
        "processed": processed,
        "total": total,
        "pass_count": CURRENT_TASK["pass_count"],
        "review_count": CURRENT_TASK["review_count"],
        "current_file": CURRENT_TASK["current_file"],
        "percentage": pct,
        "elapsed_seconds": CURRENT_TASK["elapsed_seconds"],
        "speed_fps": CURRENT_TASK["speed_fps"],
        "message": CURRENT_TASK["message"],
    }


@app.post("/api/upload-and-extract")
async def upload_and_extract(
    files: List[UploadFile] = File(...),
    output_dir: str = "./output",
    user: Optional[dict] = Depends(require_approved_user),
):
    """
    Directly receives uploaded PDFs from the browser, extracts records,
    maintains Server Master Excel while returning ONLY the current batch data.
    """
    global CURRENT_TASK
    if CURRENT_TASK["is_running"]:
        return JSONResponse(status_code=400, content={"error": "An extraction task is already running."})

    output_path = _resolve(output_dir)
    ensure_output_dir(str(output_path))

    import uuid
    batch_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    batch_upload_dir = ROOT_DIR / "pdfs" / batch_id
    batch_upload_dir.mkdir(parents=True, exist_ok=True)

    saved_pdf_paths = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            continue
        dest = batch_upload_dir / Path(f.filename).name
        with open(dest, "wb") as out_f:
            content = await f.read()
            out_f.write(content)
        saved_pdf_paths.append(str(dest))

    if not saved_pdf_paths:
        return JSONResponse(status_code=400, content={"error": "No valid PDF files were uploaded."})

    CURRENT_TASK.update({
        "is_running": True,
        "completed": False,
        "processed_count": 0,
        "total_count": len(saved_pdf_paths),
        "pass_count": 0,
        "review_count": 0,
        "start_time": time.time(),
        "elapsed_seconds": 0.0,
        "speed_fps": 0.0,
        "message": f"Extracting {len(saved_pdf_paths)} files...",
        "batch_records": [],
    })

    batch_results = []
    t0 = time.time()

    try:
        for idx, pdf_path in enumerate(saved_pdf_paths, start=1):
            filename = os.path.basename(pdf_path)
            CURRENT_TASK["current_file"] = filename
            CURRENT_TASK["processed_count"] = idx

            try:
                record = process_single_pdf(pdf_path)
                batch_results.append(record)
                if record.get("validation_status") == "PASS":
                    CURRENT_TASK["pass_count"] += 1
                else:
                    CURRENT_TASK["review_count"] += 1
            except Exception as e:
                CURRENT_TASK["review_count"] += 1
                batch_results.append({
                    "file_name": filename,
                    "contract_no": "NA",
                    "validation_status": "REVIEW",
                    "validation_errors": [str(e)],
                })

            elapsed = max(0.001, time.time() - t0)
            CURRENT_TASK["elapsed_seconds"] = round(elapsed, 2)
            CURRENT_TASK["speed_fps"] = round(idx / elapsed, 1)

        # Save batch records for UI and append all records into Server Master Excel
        save_batch_records(batch_results, str(output_path))
        CURRENT_TASK["batch_records"] = batch_results

        caller_email = user.get("email") if user else "anonymous"
        record_user_extraction(
            email=caller_email,
            processed_count=len(batch_results),
            pass_count=CURRENT_TASK["pass_count"],
            review_count=CURRENT_TASK["review_count"],
            output_path=str(output_path)
        )

        CURRENT_TASK.update({
            "is_running": False,
            "completed": True,
            "message": f"Extraction complete: {len(batch_results)} files processed.",
        })

        return {
            "status": "success",
            "batch_count": len(batch_results),
            "pass_count": CURRENT_TASK["pass_count"],
            "review_count": CURRENT_TASK["review_count"],
            "records": batch_results,
        }

    except Exception as err:
        CURRENT_TASK.update({
            "is_running": False,
            "completed": True,
            "message": f"Upload extraction failed: {str(err)}",
        })
        return JSONResponse(status_code=500, content={"error": str(err)})
    finally:
        CURRENT_TASK["is_running"] = False


@app.post("/api/clear-batch")
async def clear_current_batch(output_dir: str = "./output", user: Optional[dict] = Depends(require_approved_user)):
    """Clears current batch data from the UI while preserving Server Master Excel."""
    global CURRENT_TASK
    CURRENT_TASK["batch_records"] = []
    output_path = _resolve(output_dir)
    clear_batch_json(str(output_path))
    return {"status": "cleared", "message": "Batch data removed from UI."}


@app.get("/api/records")
async def get_records(
    output_dir: str = "./output",
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    batch_only: bool = True,
    user: Optional[dict] = Depends(require_approved_user),
):
    """Return extracted records with optional filtering, search, and pagination (Requires Approved User).
    When batch_only=True (default for UI), displays only records from the current extraction batch."""
    output_path = _resolve(output_dir)
    if batch_only:
        records = list(CURRENT_TASK.get("batch_records") or [])
        if not records:
            records = load_batch_json(str(output_path))
    else:
        records = load_existing_json(str(output_path))

    # Filter by status
    if status and status.upper() in ("PASS", "REVIEW"):
        records = [r for r in records if r.get("validation_status") == status.upper()]

    # Search across key fields
    if search:
        q = search.lower()
        records = [
            r for r in records
            if q in str(r.get("contract_no", "")).lower()
            or q in str(r.get("seller_company_name", "")).lower()
            or q in str(r.get("seller_gstin", "")).lower()
            or q in str(r.get("file_name", "")).lower()
            or q in str(r.get("product_name", "")).lower()
        ]

    total_matched = len(records)
    paginated = records[offset : offset + limit]

    # Stats calculated strictly on current batch
    total_val = sum(
        float(r["total_order_value"])
        for r in records
        if isinstance(r.get("total_order_value"), (int, float))
    )

    return {
        "total": total_matched,
        "total_master": total_matched,
        "total_value_inr": round(total_val, 2),
        "pass_count": sum(1 for r in records if r.get("validation_status") == "PASS"),
        "review_count": sum(1 for r in records if r.get("validation_status") == "REVIEW"),
        "records": paginated,
        "is_batch_only": batch_only,
        "caller_email": user.get("email") if user else "anonymous",
        "caller_role": user.get("role") if user else "guest",
    }


@app.post("/api/open-folder")
async def open_output_folder(req: OpenFolderRequest, user: Optional[dict] = Depends(require_approved_user)):
    """Open output folder in OS file explorer (Requires Approved User)."""
    folder_path = _resolve(req.folder_path)
    ensure_output_dir(str(folder_path))

    try:
        if sys.platform == "win32":
            os.startfile(str(folder_path))
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", str(folder_path)])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(folder_path)])
        return {"status": "opened", "path": str(folder_path)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to open folder: {e}"})


@app.post("/api/select-folder")
async def select_folder_dialog(req: SelectFolderRequest, user: Optional[dict] = Depends(require_approved_user)):
    """Opens native OS folder picker dialog in a worker thread and returns the chosen path (Requires Approved User)."""
    import asyncio

    def _open_dialog():
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            root.focus_force()

            init_dir = ""
            if req.initial_dir:
                resolved = _resolve(req.initial_dir)
                if resolved.exists() and resolved.is_dir():
                    init_dir = str(resolved)
                elif resolved.parent.exists() and resolved.parent.is_dir():
                    init_dir = str(resolved.parent)

            folder = filedialog.askdirectory(
                parent=root,
                initialdir=init_dir if init_dir else str(ROOT_DIR),
                title=req.title or "Select Folder"
            )
            root.destroy()
            if folder:
                return str(Path(folder).resolve())
            return None
        except Exception as e:
            print(f"Error opening folder picker dialog: {e}")
            return None

    selected = await asyncio.to_thread(_open_dialog)
    if selected:
        return {"status": "selected", "path": selected}
    return {"status": "cancelled", "path": None}


@app.get("/api/download/batch-excel")
async def download_batch_excel(output_dir: str = "./output", user: Optional[dict] = Depends(require_approved_user)):
    """Download the Current Batch Excel spreadsheet (Validation columns removed, clean output)."""
    output_path = _resolve(output_dir)
    batch_file = output_path / BATCH_EXCEL_FILENAME
    if not batch_file.exists():
        # Fallback: check if we have records to generate clean batch output excel on the fly
        batch_records = list(CURRENT_TASK.get("batch_records") or [])
        if not batch_records:
            batch_records = load_batch_json(str(output_path))
        if not batch_records:
            batch_records = load_existing_json(str(output_path))
        if batch_records:
            write_styled_excel(batch_records, str(batch_file), is_master=False)
        else:
            return JSONResponse(status_code=404, content={"error": "Batch Excel file not found. Process PDFs first."})

    return FileResponse(
        path=str(batch_file),
        filename=BATCH_EXCEL_FILENAME,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/download/excel")
async def download_excel(output_dir: str = "./output", user: Optional[dict] = Depends(require_approved_user)):
    """Download the latest Master Excel file (Requires Approved User)."""
    output_path = _resolve(output_dir)
    xlsx_files = sorted(output_path.glob("gem_contracts*.xlsx"), key=os.path.getmtime, reverse=True)

    if not xlsx_files:
        return JSONResponse(status_code=404, content={"error": "Excel file not found. Process PDFs first."})

    return FileResponse(
        path=str(xlsx_files[0]),
        filename=EXCEL_FILENAME,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/download/json")
async def download_json(output_dir: str = "./output", user: Optional[dict] = Depends(require_approved_user)):
    """Download the Master JSON file (Requires Approved User)."""
    output_path = _resolve(output_dir)
    file_path = output_path / JSON_FILENAME

    if not file_path.exists():
        return JSONResponse(status_code=404, content={"error": "JSON file not found. Process PDFs first."})

    return FileResponse(
        path=str(file_path),
        filename=JSON_FILENAME,
        media_type="application/json",
    )


# ═══════════════════════════════════════════════════════════════════
#  Run Directly:  python main.py
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"[*] GeM PDF Extraction API running on http://{host}:{port}")
    print(f"[*] API Docs: http://{host}:{port}/docs")
    uvicorn.run("main:app", host=host, port=port, reload=True)
