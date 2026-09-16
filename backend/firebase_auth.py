"""
firebase_auth.py — Firebase JWT ID Token Verification for FastAPI
=================================================================
Provides dependency for verifying Firebase JWT Bearer tokens in incoming requests.
"""

import os
from typing import Optional
from fastapi import Header, HTTPException, status, Depends

# Optional: Using firebase_admin if installed and configured
_firebase_initialized = False

def init_firebase_admin(service_account_path: Optional[str] = None):
    global _firebase_initialized
    if _firebase_initialized:
        return
    
    try:
        import firebase_admin
        from firebase_admin import credentials
        
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # Initialize with default environment credentials if available
            firebase_admin.initialize_app()
        _firebase_initialized = True
    except Exception as e:
        print(f"[Firebase Admin] Initialization notice: {e}")

async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    FastAPI dependency to extract and verify the Firebase JWT token from:
    Authorization: Bearer <token>
    """
    if not authorization:
        # If authentication is optional or during initial setup
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    token = authorization.split("Bearer ")[1].strip()
    
    try:
        import firebase_admin
        from firebase_admin import auth
        
        # Verify the Firebase JWT Token with Google's public certificates
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except ImportError:
        # Fallback if firebase-admin is not yet installed
        return {"uid": "unverified", "raw_token": token[:15] + "..."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Firebase JWT token verification failed: {str(e)}"
        )
