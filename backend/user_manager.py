"""
user_manager.py — Whitelist, Client Approval & Multi-User Scan Tracking System
=============================================================================
Manages persistent whitelisted clients, access approval requests, admin roles,
and aggregate / per-user PDF scanning and extraction statistics across all accounts.
"""

import os
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
WHITELIST_FILE = BASE_DIR / "users_whitelist.json"
STATS_FILE = BASE_DIR / "user_stats.json"

# Configurable admin emails (comma-separated from env, e.g. "admin@company.com,sumit@example.com")
ENV_ADMINS = [
    e.strip().lower() 
    for e in os.getenv("ADMIN_EMAILS", "").split(",") 
    if e.strip()
]

DEFAULT_DATA: Dict[str, Any] = {
    "admin_emails": ENV_ADMINS,
    "whitelist": [],
    "pending_requests": []
}

DEFAULT_STATS: Dict[str, Any] = {
    "global_stats": {
        "total_pdfs_scanned": 0,
        "total_pdfs_extracted": 0,
        "total_scans_performed": 0,
        "total_extractions_performed": 0,
        "last_scan_at": None,
        "last_extraction_at": None,
    },
    "user_stats": {},
    "activity_log": []
}


def _ensure_files_exist():
    """Create whitelist and stats files if they do not exist."""
    if not WHITELIST_FILE.exists():
        with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_DATA, f, indent=2)
    if not STATS_FILE.exists():
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_STATS, f, indent=2)


def _load_stats_file() -> Dict[str, Any]:
    """Load persistent stats and activity file."""
    _ensure_files_exist()
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return DEFAULT_STATS.copy()
            if "global_stats" not in data:
                data["global_stats"] = DEFAULT_STATS["global_stats"].copy()
            if "user_stats" not in data:
                data["user_stats"] = {}
            if "activity_log" not in data:
                data["activity_log"] = []
            return data
    except Exception as e:
        print(f"[UserManager] Error loading stats JSON: {e}")
        return DEFAULT_STATS.copy()


def _save_stats_file(data: Dict[str, Any]):
    """Atomically save user stats data."""
    try:
        temp_file = STATS_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_file.replace(STATS_FILE)
    except Exception as e:
        print(f"[UserManager] Error saving stats JSON: {e}")


def _get_master_output_stats() -> Dict[str, Any]:
    """Read actual contracts from master json to aggregate real dataset metrics."""
    json_path = ROOT_DIR / "output" / "gem_contracts.json"
    total_master = 0
    pass_count = 0
    review_count = 0
    total_val = 0.0

    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                if isinstance(records, list):
                    total_master = len(records)
                    for r in records:
                        if r.get("validation_status") == "PASS":
                            pass_count += 1
                        else:
                            review_count += 1
                        val = r.get("total_order_value")
                        if isinstance(val, (int, float)):
                            total_val += float(val)
        except Exception as err:
            print(f"[UserManager] Could not read master JSON stats: {err}")

    return {
        "total_master_records": total_master,
        "pass_count": pass_count,
        "review_count": review_count,
        "total_value_inr": round(total_val, 2)
    }


def record_user_scan(email: Optional[str], total_scanned: int, new_count: int, input_path: str = ""):
    """Record a scan action performed by a user."""
    norm_email = (email or "anonymous").strip().lower()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    stats_data = _load_stats_file()
    g_stats = stats_data.setdefault("global_stats", {})
    g_stats["total_pdfs_scanned"] = g_stats.get("total_pdfs_scanned", 0) + total_scanned
    g_stats["total_scans_performed"] = g_stats.get("total_scans_performed", 0) + 1
    g_stats["last_scan_at"] = now_iso

    # Per-user stats
    u_stats = stats_data.setdefault("user_stats", {})
    user_entry = u_stats.setdefault(norm_email, {
        "email": norm_email,
        "total_pdfs_scanned": 0,
        "total_pdfs_extracted": 0,
        "scans_count": 0,
        "extractions_count": 0,
        "last_active_at": None
    })
    user_entry["total_pdfs_scanned"] = user_entry.get("total_pdfs_scanned", 0) + total_scanned
    user_entry["scans_count"] = user_entry.get("scans_count", 0) + 1
    user_entry["last_active_at"] = now_iso

    # Append activity log
    log_entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": now_iso,
        "user_email": norm_email,
        "action": "scan",
        "total_pdfs": total_scanned,
        "new_to_process": new_count,
        "folder": os.path.basename(input_path) if input_path else "pdfs",
        "description": f"Scanned {total_scanned} PDF(s) ({new_count} new) in '{os.path.basename(input_path) or 'folder'}'"
    }
    activity = stats_data.setdefault("activity_log", [])
    activity.insert(0, log_entry)
    stats_data["activity_log"] = activity[:100]  # Keep latest 100 entries

    _save_stats_file(stats_data)


def record_user_extraction(email: Optional[str], processed_count: int, pass_count: int, review_count: int, output_path: str = ""):
    """Record an extraction run performed by a user."""
    norm_email = (email or "anonymous").strip().lower()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    stats_data = _load_stats_file()
    g_stats = stats_data.setdefault("global_stats", {})
    g_stats["total_pdfs_extracted"] = g_stats.get("total_pdfs_extracted", 0) + processed_count
    g_stats["total_extractions_performed"] = g_stats.get("total_extractions_performed", 0) + 1
    g_stats["last_extraction_at"] = now_iso

    # Per-user stats
    u_stats = stats_data.setdefault("user_stats", {})
    user_entry = u_stats.setdefault(norm_email, {
        "email": norm_email,
        "total_pdfs_scanned": 0,
        "total_pdfs_extracted": 0,
        "scans_count": 0,
        "extractions_count": 0,
        "last_active_at": None
    })
    user_entry["total_pdfs_extracted"] = user_entry.get("total_pdfs_extracted", 0) + processed_count
    user_entry["extractions_count"] = user_entry.get("extractions_count", 0) + 1
    user_entry["last_active_at"] = now_iso

    # Append activity log
    log_entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": now_iso,
        "user_email": norm_email,
        "action": "extract",
        "total_pdfs": processed_count,
        "pass_count": pass_count,
        "review_count": review_count,
        "folder": os.path.basename(output_path) if output_path else "output",
        "description": f"Extracted {processed_count} PDF(s) ({pass_count} PASS, {review_count} REVIEW)"
    }
    activity = stats_data.setdefault("activity_log", [])
    activity.insert(0, log_entry)
    stats_data["activity_log"] = activity[:100]

    _save_stats_file(stats_data)


def load_user_data() -> Dict[str, Any]:
    """Load the user whitelist, pending requests, and enriched scan/extraction stats."""
    _ensure_files_exist()
    try:
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[UserManager] Error loading whitelist JSON: {e}")
        data = DEFAULT_DATA.copy()

    # Merge with env admin emails
    current_admins = set(data.get("admin_emails", []))
    for admin_e in ENV_ADMINS:
        current_admins.add(admin_e)
    data["admin_emails"] = list(current_admins)

    # Load stats
    stats_data = _load_stats_file()
    master_stats = _get_master_output_stats()
    user_stats = stats_data.get("user_stats", {})
    g_stats = stats_data.get("global_stats", {})

    # Ensure baseline includes master records count if fresh start
    lifetime_scanned = g_stats.get("total_pdfs_scanned", 0)
    lifetime_extracted = g_stats.get("total_pdfs_extracted", 0)
    if lifetime_extracted < master_stats["total_master_records"]:
        lifetime_extracted = master_stats["total_master_records"]
    if lifetime_scanned < lifetime_extracted:
        lifetime_scanned = lifetime_extracted

    # Enrich whitelist items with user-specific statistics
    enriched_whitelist = []
    for entry in data.get("whitelist", []):
        entry_copy = dict(entry)
        email = entry.get("email", "").strip().lower()
        u_info = user_stats.get(email, {})
        entry_copy["total_pdfs_scanned"] = u_info.get("total_pdfs_scanned", 0)
        entry_copy["total_pdfs_extracted"] = u_info.get("total_pdfs_extracted", 0)
        entry_copy["scans_count"] = u_info.get("scans_count", 0)
        entry_copy["extractions_count"] = u_info.get("extractions_count", 0)
        entry_copy["last_active_at"] = u_info.get("last_active_at") or entry.get("approved_at")
        enriched_whitelist.append(entry_copy)

    data["whitelist"] = enriched_whitelist

    # Calculate active users count
    active_users_set = set(user_stats.keys())
    for e in enriched_whitelist:
        if (e.get("total_pdfs_scanned", 0) > 0 or e.get("total_pdfs_extracted", 0) > 0):
            active_users_set.add(e["email"])

    data["global_stats"] = {
        "total_pdfs_scanned": lifetime_scanned,
        "total_pdfs_extracted": lifetime_extracted,
        "total_scans_performed": g_stats.get("total_scans_performed", 0),
        "total_extractions_performed": g_stats.get("total_extractions_performed", 0),
        "total_master_records": master_stats["total_master_records"],
        "pass_count": master_stats["pass_count"],
        "review_count": master_stats["review_count"],
        "total_value_inr": master_stats["total_value_inr"],
        "total_whitelisted_users": len(enriched_whitelist),
        "total_pending_users": len(data.get("pending_requests", [])),
        "total_admin_users": len(data.get("admin_emails", [])),
        "active_users_count": len(active_users_set),
        "last_scan_at": g_stats.get("last_scan_at"),
        "last_extraction_at": g_stats.get("last_extraction_at"),
    }

    data["activity_log"] = stats_data.get("activity_log", [])[:30]
    data["user_stats"] = user_stats
    return data


def save_user_data(data: Dict[str, Any]):
    """Atomically persist user whitelist data."""
    try:
        # Strip computed stats fields before writing to whitelist.json
        clean_data = {
            "admin_emails": data.get("admin_emails", []),
            "whitelist": [
                {
                    "email": w.get("email"),
                    "role": w.get("role", "client"),
                    "approved_by": w.get("approved_by"),
                    "approved_at": w.get("approved_at"),
                }
                for w in data.get("whitelist", [])
            ],
            "pending_requests": data.get("pending_requests", [])
        }
        temp_file = WHITELIST_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(clean_data, f, indent=2)
        temp_file.replace(WHITELIST_FILE)
    except Exception as e:
        print(f"[UserManager] Error saving whitelist JSON: {e}")


def is_user_whitelisted(email: Optional[str], uid: Optional[str] = None) -> Tuple[bool, str]:
    """
    Checks if a user is approved to use the application.
    Returns: (is_approved: bool, role: str)
    Role can be 'admin', 'client', or 'unapproved'.
    """
    if not email:
        return False, "unapproved"

    norm_email = email.strip().lower()
    data = load_user_data()

    # 1. Check if user is Admin
    admins = [a.strip().lower() for a in data.get("admin_emails", [])]
    if norm_email in admins:
        return True, "admin"

    # 2. Check Whitelist
    for entry in data.get("whitelist", []):
        entry_email = entry.get("email", "").strip().lower()
        entry_uid = entry.get("uid", "")
        if (norm_email and norm_email == entry_email) or (uid and entry_uid and uid == entry_uid):
            return True, entry.get("role", "client")

    return False, "unapproved"


def check_or_register_user(email: Optional[str], uid: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Called when a user logs in. If they are whitelisted, returns approved status.
    If not, automatically records their pending approval request.
    """
    if not email:
        return {"status": "unauthorized", "message": "Email is required"}

    norm_email = email.strip().lower()
    is_approved, role = is_user_whitelisted(norm_email, uid)

    if is_approved:
        return {
            "status": "approved",
            "email": norm_email,
            "role": role,
            "message": "User is whitelisted and approved for access."
        }

    # User is not whitelisted -> Record/Check in pending requests
    data = load_user_data()
    pending = data.setdefault("pending_requests", [])

    existing = next((p for p in pending if p.get("email", "").strip().lower() == norm_email), None)
    if not existing:
        pending.append({
            "email": norm_email,
            "uid": uid or "",
            "name": name or "",
            "requested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "pending"
        })
        save_user_data(data)

    return {
        "status": "pending",
        "email": norm_email,
        "role": "unapproved",
        "message": "Access requested. Your account is pending administrator approval."
    }


def approve_user(email: str, approved_by: str = "admin", role: str = "client") -> Dict[str, Any]:
    """Approve a user by email and move from pending to whitelist."""
    norm_email = email.strip().lower()
    data = load_user_data()

    # Remove from pending if exists
    data["pending_requests"] = [
        p for p in data.get("pending_requests", []) 
        if p.get("email", "").strip().lower() != norm_email
    ]

    # Check if already in whitelist
    whitelist = data.setdefault("whitelist", [])
    existing = next((w for w in whitelist if w.get("email", "").strip().lower() == norm_email), None)
    
    if existing:
        existing["role"] = role
        existing["approved_by"] = approved_by
        existing["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    else:
        whitelist.append({
            "email": norm_email,
            "role": role,
            "approved_by": approved_by,
            "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

    save_user_data(data)
    return {"status": "success", "message": f"User {norm_email} successfully approved as {role}."}


def revoke_user(email: str) -> Dict[str, Any]:
    """Revoke user access by removing them from the whitelist."""
    norm_email = email.strip().lower()
    data = load_user_data()

    data["whitelist"] = [
        w for w in data.get("whitelist", []) 
        if w.get("email", "").strip().lower() != norm_email
    ]

    save_user_data(data)
    return {"status": "success", "message": f"User {norm_email} access revoked."}


def add_admin(email: str) -> Dict[str, Any]:
    """Add an email to the permanent admin list."""
    norm_email = email.strip().lower()
    data = load_user_data()
    admins = set(data.setdefault("admin_emails", []))
    admins.add(norm_email)
    data["admin_emails"] = list(admins)
    save_user_data(data)
    return {"status": "success", "message": f"Admin {norm_email} added."}

