"""
test_approval_flow.py — Comprehensive Test Suite for User Whitelist & Approval Mechanism
"""

import os
import sys
import json
from pathlib import Path

# Force UTF-8 stdout
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import user_manager

def run_tests():
    print("=" * 60)
    print("[*] RUNNING COMPREHENSIVE APPROVAL & WHITELIST TEST SUITE")
    print("=" * 60)

    # ── Test 1: Load Current State ────────────────────────────────
    data = user_manager.load_user_data()
    print(f"\n[Test 1] Loaded users_whitelist.json:")
    print(f"  - Admins ({len(data.get('admin_emails', []))}): {data.get('admin_emails')}")
    print(f"  - Whitelist ({len(data.get('whitelist', []))}): {[w['email'] for w in data.get('whitelist', [])]}")
    print(f"  - Pending ({len(data.get('pending_requests', []))}): {[p['email'] for p in data.get('pending_requests', [])]}")
    assert "amitk839170@gmail.com" in data.get("admin_emails", []), "Admin email missing!"
    print("  [PASS] Test 1: Whitelist JSON loaded correctly.")

    # ── Test 2: Admin Whitelist Check ─────────────────────────────
    is_approved, role = user_manager.is_user_whitelisted("amitk839170@gmail.com")
    print(f"\n[Test 2] Checking Admin User ('amitk839170@gmail.com'):")
    print(f"  - is_approved: {is_approved}, role: {role}")
    assert is_approved is True, "Admin should be approved"
    assert role == "admin", "Admin role should be 'admin'"
    print("  [PASS] Test 2: Admin access recognized correctly.")

    # ── Test 3: Approved Client Check ─────────────────────────────
    is_approved, role = user_manager.is_user_whitelisted("indonesiaka30@gmail.com")
    print(f"\n[Test 3] Checking Whitelisted Client ('indonesiaka30@gmail.com'):")
    print(f"  - is_approved: {is_approved}, role: {role}")
    assert is_approved is True, "Whitelisted client should be approved"
    assert role == "client", "Role should be 'client'"
    print("  [PASS] Test 3: Whitelisted client access recognized correctly.")

    # ── Test 4: Pending Unapproved User Check ─────────────────────
    is_approved, role = user_manager.is_user_whitelisted("amitguptacom61@gmail.com")
    print(f"\n[Test 4] Checking Pending User ('amitguptacom61@gmail.com'):")
    print(f"  - is_approved: {is_approved}, role: {role}")
    assert is_approved is False, "Pending user should NOT be approved"
    assert role == "unapproved", "Role should be 'unapproved'"
    print("  [PASS] Test 4: Pending user is correctly blocked from access.")

    # ── Test 5: Auto-Registration of New Sign-in Request ───────────
    test_new_email = "test_client_99@company.com"
    status_res = user_manager.check_or_register_user(test_new_email, uid="uid_99", name="Test User 99")
    print(f"\n[Test 5] Auto-Registering New User ('{test_new_email}'):")
    print(f"  - Status Response: {status_res}")
    assert status_res["status"] == "pending", "New user should get 'pending' status"
    
    # Verify they were added to pending_requests
    updated_data = user_manager.load_user_data()
    pending_emails = [p["email"] for p in updated_data.get("pending_requests", [])]
    assert test_new_email in pending_emails, f"{test_new_email} should be in pending_requests"
    print("  [PASS] Test 5: New user is automatically queued into pending_requests.")

    # ── Test 6: Approval Action ────────────────────────────────────
    print(f"\n[Test 6] Approving Pending User ('{test_new_email}'):")
    appr_res = user_manager.approve_user(test_new_email, approved_by="amitk839170@gmail.com", role="client")
    print(f"  - Approve Result: {appr_res}")
    
    # Verify user is now approved and removed from pending
    is_approved, role = user_manager.is_user_whitelisted(test_new_email)
    print(f"  - Verification: is_approved={is_approved}, role={role}")
    assert is_approved is True, "User should now be approved"
    assert role == "client", "User role should be 'client'"
    
    updated_data = user_manager.load_user_data()
    pending_emails = [p["email"] for p in updated_data.get("pending_requests", [])]
    assert test_new_email not in pending_emails, "User should be removed from pending"
    print("  [PASS] Test 6: User successfully approved and removed from pending queue.")

    # ── Test 7: Revocation Action ──────────────────────────────────
    print(f"\n[Test 7] Revoking Access for ('{test_new_email}'):")
    rev_res = user_manager.revoke_user(test_new_email)
    print(f"  - Revoke Result: {rev_res}")
    
    # Verify user is no longer whitelisted
    is_approved, role = user_manager.is_user_whitelisted(test_new_email)
    print(f"  - Verification: is_approved={is_approved}, role={role}")
    assert is_approved is False, "User access should now be revoked"
    assert role == "unapproved", "Role should be 'unapproved'"
    print("  [PASS] Test 7: Access revoked successfully.")

    # ── Test 8: Case-Insensitivity Check ──────────────────────────
    print(f"\n[Test 8] Case-Insensitivity Check ('AMITK839170@GMAIL.COM'):")
    is_approved, role = user_manager.is_user_whitelisted("AMITK839170@GMAIL.COM")
    assert is_approved is True and role == "admin", "Email matching should be case-insensitive"
    print("  [PASS] Test 8: Email matching is 100% case-insensitive.")

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL 8 APPROVAL & WHITELIST UNIT TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
