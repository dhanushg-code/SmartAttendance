"""Admin authentication (app-level login against the admins table)."""
from __future__ import annotations

import hashlib
import secrets
from typing import Optional

from config import settings
from database.supabase_client import db


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        _scheme, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
        return secrets.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


_current_admin: Optional[dict] = None


def login(username: str, password: str) -> Optional[dict]:
    """Verify credentials. In demo mode accepts admin/admin123."""
    global _current_admin
    if settings.DEMO_MODE:
        if username == "admin" and password == "admin123":
            _current_admin = {"id": "demo-admin", "username": "admin"}
            return _current_admin
        return None
    rows = db.table("admins").select("*").eq("username", username).execute().data
    if rows and _verify_password(password, rows[0]["password_hash"]):
        _current_admin = {"id": rows[0]["id"], "username": username}
        return _current_admin
    return None


def current_admin() -> Optional[dict]:
    return _current_admin


def logout() -> None:
    global _current_admin
    _current_admin = None


def create_admin(username: str, password: str) -> dict:
    resp = db.table("admins").insert({
        "username": username,
        "password_hash": _hash_password(password),
    }).execute()
    return resp.data[0]
