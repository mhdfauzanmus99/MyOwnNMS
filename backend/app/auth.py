"""Authentication: bcrypt-hashed users + Starlette signed-cookie sessions.

Single-admin model for v1. The session cookie is signed (itsdangerous) and
checked on every protected route via the `require_user` dependency.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import database
from .config import settings

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="nms-session")


# ---------------------------------------------------------------------------
# Password hashing — bcrypt if available, else PBKDF2-HMAC-SHA256 fallback so the
# app still runs without compiled bcrypt (e.g. some sandboxes).
# ---------------------------------------------------------------------------
try:
    import bcrypt  # type: ignore

    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except ValueError:
            return False

    _BCRYPT = True
except Exception:  # pragma: no cover - bcrypt normally present
    _BCRYPT = False

    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        return f"pbkdf2${salt}${dk.hex()}"

    def verify_password(password: str, hashed: str) -> bool:
        try:
            algo, salt, hexhash = hashed.split("$", 2)
        except ValueError:
            return False
        if algo != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        return hmac.compare_digest(dk.hex(), hexhash)


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------
def get_user(username: str) -> Optional[dict]:
    return database.query_one("SELECT * FROM users WHERE username = ?", (username,))


def create_user(username: str, password: str) -> None:
    database.execute(
        "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
        (username, hash_password(password)),
    )


def ensure_admin_user() -> None:
    """Seed the default admin user if the users table is empty."""
    rows = database.query("SELECT id FROM users LIMIT 1")
    if not rows:
        create_user(settings.admin_username, settings.admin_password)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
def start_session(user: dict) -> str:
    payload = {"uid": user["id"], "username": user["username"]}
    return _serializer.dumps(payload)


def read_session(token: str) -> Optional[dict]:
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age)
    except BadSignature:
        return None
    return data


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def require_user(request: Request) -> dict:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    session = read_session(token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    user = database.query_one("SELECT id, username FROM users WHERE id = ?", (session["uid"],))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
