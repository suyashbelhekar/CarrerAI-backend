"""
Authentication module — JWT-based login/register.
Uses a local JSON file as a simple user store (no DB dependency).
"""

import json
import os
import hashlib
import hmac
import time
import base64
from pathlib import Path

USERS_FILE = Path(__file__).parent / "users.json"
SECRET_KEY = os.getenv("SECRET_KEY", "resume-ai-secret-2024-xK9mP3qL")
TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days


# ── User store helpers ──────────────────────────────────────────────────────

def _load_users() -> dict:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text())
    except Exception:
        return {}


def _save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2))


def _hash_password(password: str) -> str:
    return hmac.new(SECRET_KEY.encode(), password.encode(), hashlib.sha256).hexdigest()


# ── JWT (minimal, no external lib) ─────────────────────────────────────────

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _create_token(email: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({"sub": email, "exp": time.time() + TOKEN_EXPIRE_HOURS * 3600}).encode())
    sig = _b64(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def _verify_token(token: str) -> str | None:
    """Returns email if valid, None otherwise."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig = parts
        expected_sig = _b64(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected_sig):
            return None
        pad = 4 - len(payload) % 4
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * pad))
        if data.get("exp", 0) < time.time():
            return None
        return data.get("sub")
    except Exception:
        return None


# ── Public API ──────────────────────────────────────────────────────────────

from database import db_create_user, db_get_user_by_email

def register_user(full_name: str, email: str, password: str) -> dict:
    email = email.lower().strip()
    if not full_name.strip():
        raise ValueError("Full name is required.")
    if "@" not in email:
        raise ValueError("Valid email is required.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    
    existing = db_get_user_by_email(email)
    if existing:
        raise ValueError("An account with this email already exists.")
    
    pwd_hash = _hash_password(password)
    user = db_create_user(full_name.strip(), email, pwd_hash)
    token = _create_token(email)
    return {"token": token, "user": {"full_name": full_name.strip(), "email": email}}


def login_user(email: str, password: str) -> dict:
    email = email.lower().strip()
    user = db_get_user_by_email(email)
    if not user:
        raise ValueError("No account found with this email.")
    if user["password_hash"] != _hash_password(password):
        raise ValueError("Incorrect password.")
    token = _create_token(email)
    return {"token": token, "user": {"full_name": user["full_name"], "email": email}}


def get_user_from_token(token: str) -> dict | None:
    email = _verify_token(token)
    if not email:
        return None
    user = db_get_user_by_email(email)
    if not user:
        return None
    return {"full_name": user["full_name"], "email": email}

