"""
run_app.py — One-click launcher for GeM PDF Extractor
=====================================================
Starts the FastAPI backend and opens the Web UI in your default browser.
"""

import os
import sys
import time
import webbrowser
import threading
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000/"
    print(f"[*] Opening {url} in your browser...")
    webbrowser.open(url)

if __name__ == "__main__":
    import uvicorn

    # Launch browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()

    host = "127.0.0.1"
    port = int(os.environ.get("PORT", 8000))
    print(f"[*] GeM PDF Extractor running at http://{host}:{port}/")
    print(f"[*] Press CTRL+C to stop.")

    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
