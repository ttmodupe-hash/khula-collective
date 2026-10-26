"""Khula account security and controlled member onboarding.

No default production accounts or public registration. Credentials for initial
admin/member invitation are supplied through private environment variables.
"""
import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime, timezone

import bcrypt


def _is_demo_mode():
    return os.environ.get("KHULA_DEMO_MODE") == "1"


def hash_password(password):
    if len(password.encode("utf-8")) < 12 or len(password.encode("utf-8")) > 128:
        raise ValueError("Use a password between 12 and 128 UTF-8 bytes.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def _verify_password(password, stored_hash):
    """Return (valid, optional-upgraded-hash). Legacy SHA-256 is opt-in only."""
    if not stored_hash:
        return False, None
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii")), None
        except (ValueError, TypeError):
            return False, None
    legacy_enabled = _is_demo_mode() or os.environ.get("KHULA_ENABLE_LEGACY_HASH_LOGIN") == "1"
    if not legacy_enabled or not re.fullmatch(r"[0-9a-f]{64}", stored_hash):
        return False, None
    actual = hashlib.sha256(password.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(actual, stored_hash):
        return False, None
    if _is_demo_mode() and len(password) < 12:
        return True, None
    # Force a reset for short/weak legacy passwords; never upgrade them silently.
    if len(password.encode("utf-8")) < 12:
        return False, None
    return True, hash_password(password)


def authenticate_user(db_path, username, password):
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    username = username.strip().lower()
    if len(username) > 64 or len(password.encode("utf-8")) > 128:
        return None
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT user_id,username,full_name,role,theme_preference,password_hash "
            "FROM Users WHERE LOWER(username)=? AND is_active=1",
            (username,),
        ).fetchone()
        if not row:
            return None
        stored_hash = row[5]
        # Previously published demo credentials must never grant production access,
        # including if they persisted from an earlier deployment.
        exposed = {
            hashlib.sha256(b"admin123").hexdigest(),
            hashlib.sha256(b"password1").hexdigest(),
        }
        if not _is_demo_mode() and stored_hash in exposed:
            return None
        accepted, upgraded = _verify_password(password, stored_hash)
        if not accepted:
            return None
        if upgraded:
            conn.execute("UPDATE Users SET password_hash=? WHERE user_id=?", (upgraded, row[0]))
        conn.execute(
            "UPDATE Users SET last_login=? WHERE user_id=?",
            (datetime.now(timezone.utc).isoformat(), row[0]),
        )
        return tuple(row[:5])


def bootstrap_admin(db_path):
    """Create first admin only from a strong, private bootstrap credential."""
    username = os.environ.get("KHULA_BOOTSTRAP_ADMIN_USER", "").strip().lower()
    password = os.environ.get("KHULA_BOOTSTRAP_ADMIN_PASSWORD", "")
    if not username or not password or not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", username):
        return False
    if len(password.encode("utf-8")) < 12 or password in ("admin123", "password123"):
        return False
    with sqlite3.connect(db_path) as conn:
        # Previously seeded demo admins must not block secure first-time setup.
        demo_hash = hashlib.sha256(b"admin123").hexdigest()
        existing = conn.execute(
            "SELECT 1 FROM Users WHERE role='admin' AND is_active=1 "
            "AND password_hash != ? LIMIT 1", (demo_hash,)
        ).fetchone()
        if existing:
            return False
        existing_user = conn.execute("SELECT 1 FROM Users WHERE username=? LIMIT 1", (username,)).fetchone()
        if existing_user:
            return False
        conn.execute(
            "INSERT INTO Users (username,password_hash,full_name,role,join_date,is_active) "
            "VALUES (?,?,?,?,?,1)",
            (username, hash_password(password), "Khula Administrator", "admin",
             datetime.now(timezone.utc).isoformat()),
        )
    return True


def registration_enabled():
    return bool(os.environ.get("KHULA_INVITE_CODE", "")) and not _is_demo_mode()


def register_member(db_path, username, full_name, email, password, invite_code):
    """Invitation-only registration. Neither role nor FICA status is user-supplied."""
    expected = os.environ.get("KHULA_INVITE_CODE", "")
    if not expected or len(expected) < 12:
        raise ValueError("Member registration has not been configured.")
    if not hmac.compare_digest(str(invite_code).encode("utf-8"), expected.encode("utf-8")):
        raise ValueError("Invalid invitation code.")
    username = str(username).strip().lower()
    full_name = str(full_name).strip()
    email = str(email).strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", username):
        raise ValueError("Use 3–30 letters, numbers or underscores; start with a letter.")
    if not (3 <= len(full_name) <= 120):
        raise ValueError("Please enter your full name.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
        raise ValueError("Enter a valid email address.")
    pwd = hash_password(password)
    with sqlite3.connect(db_path) as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO Users (username,password_hash,full_name,email,role,join_date,is_active,fica_verified) "
                "VALUES (?,?,?,?,'member',?,0,0)",
                (username, pwd, full_name, email, datetime.now(timezone.utc).isoformat()),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("That username is already in use.") from exc
    return cursor.lastrowid
