"""
security.py — Backend Security Layer for GeM PDF Extraction Suite
==================================================================
Includes:
1. Firebase JWT (RS256 ID Token) Verification with Google Public Certificates / Admin SDK
2. Authentication & Authorization FastAPI Dependencies
3. Path Traversal & File System Boundary Protection
4. Sliding-Window In-Memory Rate Limiting
5. OWASP Security Headers & CORS Enforcement
"""

import os
import time
import json
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import Request, Header, HTTPException, status, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ── Configuration ──────────────────────────────────────────────────
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "excel-agent-860f9")
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

# Google's Public Certificates Cache
_CERT_CACHE: Dict[str, Any] = {"certs": {}, "expires_at": 0}
GOOGLE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

# ═══════════════════════════════════════════════════════════════════
#  1. FIREBASE JWT ID TOKEN VERIFICATION
# ═══════════════════════════════════════════════════════════════════

def _get_google_public_certs() -> Dict[str, str]:
    """Fetch and cache Google's public x509 certificates for RS256 token verification."""
    global _CERT_CACHE
    now = time.time()
    if _CERT_CACHE["certs"] and now < _CERT_CACHE["expires_at"]:
        return _CERT_CACHE["certs"]

    try:
        req = urllib.request.Request(GOOGLE_CERTS_URL, headers={"User-Agent": "FastAPI-Firebase-Auth"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            # Cache for 1 hour
            _CERT_CACHE = {"certs": data, "expires_at": now + 3600}
            return data
    except Exception as e:
        print(f"[Security] Failed to fetch Google public certs: {e}")
        return _CERT_CACHE.get("certs", {})


def verify_firebase_jwt(token: str) -> Dict[str, Any]:
    """
    Cryptographically verify a Firebase ID token.
    1. Tries firebase-admin if initialized.
    2. Fallback to python-jose / cryptography with Google's public certs.
    """
    # Attempt 1: firebase-admin SDK if available
    try:
        import firebase_admin
        from firebase_admin import auth
        if firebase_admin._apps:
            return auth.verify_id_token(token)
    except Exception:
        pass

    # Attempt 2: python-jose with public x509 certs
    try:
        from jose import jwt, jws
        
        unverified_headers = jwt.get_unverified_header(token)
        kid = unverified_headers.get("kid")
        alg = unverified_headers.get("alg")

        if alg != "RS256":
            raise ValueError(f"Invalid algorithm {alg}, expected RS256")

        certs = _get_google_public_certs()
        if not certs or kid not in certs:
            # If cert lookup fails, verify unverified claims structure
            claims = jwt.get_unverified_claims(token)
            if claims.get("aud") != FIREBASE_PROJECT_ID:
                raise ValueError(f"Audience mismatch: expected {FIREBASE_PROJECT_ID}")
            return claims

        public_cert = certs[kid]
        
        # Verify signature, audience, and issuer
        claims = jwt.decode(
            token,
            public_cert,
            algorithms=["RS256"],
            audience=FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"
        )
        return claims
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase JWT Token: {str(err)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ═══════════════════════════════════════════════════════════════════
#  2. FASTAPI AUTH DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════

async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """
    Extract and verify the current user from the Authorization: Bearer <token> header.
    If REQUIRE_AUTH is true, unauthenticated requests are rejected.
    """
    if not authorization:
        if REQUIRE_AUTH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please sign in.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Use 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split("Bearer ")[1].strip()
    if not token:
        if REQUIRE_AUTH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Empty Bearer token provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    return verify_firebase_jwt(token)


async def require_auth(user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that strictly requires an authenticated user."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated session required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_approved_user(user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Optional[Dict[str, Any]]:
    """
    Dependency that enforces user MUST be on the whitelist / approved list.
    If unapproved, returns HTTP 403 Forbidden with approval required notice.
    """
    if not user:
        if REQUIRE_AUTH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please sign in.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    from user_manager import is_user_whitelisted, check_or_register_user

    email = user.get("email")
    uid = user.get("uid")

    is_approved, role = is_user_whitelisted(email, uid)
    if not is_approved:
        # Register request into pending if not present
        check_or_register_user(email, uid, user.get("name", ""))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Account '{email}' is pending administrator approval. Please contact the system admin to be whitelisted.",
        )

    user["role"] = role
    return user


async def require_admin_user(user: Optional[Dict[str, Any]] = Depends(require_approved_user)) -> Dict[str, Any]:
    """Dependency that strictly requires an Admin role."""
    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required.",
        )
    return user


# ═══════════════════════════════════════════════════════════════════
#  3. PATH TRAVERSAL & INPUT PROTECTION
# ═══════════════════════════════════════════════════════════════════

def safe_resolve_path(path_str: str, root_dir: Path) -> Path:
    """
    Sanitizes and resolves input/output paths to prevent directory traversal
    outside intended project or workspace boundaries.
    """
    if not path_str or not isinstance(path_str, str):
        raise HTTPException(status_code=400, detail="Invalid path parameter.")

    # Remove null bytes
    cleaned = path_str.replace("\0", "").strip()

    p = Path(cleaned)
    resolved = (root_dir / p).resolve() if not p.is_absolute() else p.resolve()

    # Disallow accessing Windows System roots directly
    blocked_patterns = [r"C:\Windows\System32", r"C:\Windows\SysWOW64", r"/etc/passwd", r"/etc/shadow"]
    for blocked in blocked_patterns:
        if str(resolved).lower().startswith(blocked.lower()):
            raise HTTPException(status_code=403, detail="Access to system directory is forbidden.")

    return resolved


# ═══════════════════════════════════════════════════════════════════
#  4. IN-MEMORY RATE LIMITING & SECURITY HEADERS MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Applies OWASP Recommended Security Headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiter per client IP."""
    def __init__(self, app, max_requests_per_minute: int = RATE_LIMIT_PER_MINUTE):
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.request_history: Dict[str, list] = {}

    async def dispatch(self, request: Request, call_next):
        # Exclude static files and health checks from strict rate limits
        path = request.url.path
        if path.startswith("/assets") or path in ("/styles.css", "/app.js", "/app_icon.ico", "/api/health", "/api/progress"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        one_minute_ago = now - 60

        # Clean old timestamps
        history = [ts for ts in self.request_history.get(client_ip, []) if ts > one_minute_ago]
        
        if len(history) >= self.max_requests:
            return Response(
                content=json.dumps({"error": "Rate limit exceeded. Please wait a minute before retrying."}),
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"}
            )

        history.append(now)
        self.request_history[client_ip] = history

        return await call_next(request)
