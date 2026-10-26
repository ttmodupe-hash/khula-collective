"""Khula account security and controlled member onboarding.

No default production accounts or public registration. Credentials for initial
admin/member invitation are supplied through private environment variables.
"""
import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta

import bcrypt
from khula_invitations import email_normalised, verify_and_use_invitation


def _is_demo_mode():
    return os.environ.get("KHULA_DEMO_MODE") == "1"


def hash_password(password):
    if len(password.encode("utf-8")) < 12 or len(password.encode("utf-8")) > 72:
        raise ValueError("Use a password between 12 and 72 UTF-8 bytes.")
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


def _init_login_tracking(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS Login_Attempts (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        attempted_at TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_login_attempts ON Login_Attempts(username, attempted_at)")


def _record_failed_login(conn, username, now):
    conn.execute(
        "INSERT INTO Login_Attempts(username, attempted_at) VALUES (?,?)",
        (username, now.isoformat()),
    )


def authenticate_user(db_path, username, password):
    """Fail-closed authentication with persistent bounded password attempts.

    Eight failed attempts trigger a fifteen-minute per-username cooldown.
    Also rate-limit by IP at the Railway/Cloudflare edge before broad launch.
    """
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    username = username.strip().lower()
    if not username or len(username) > 64 or not password or len(password.encode("utf-8")) > 72:
        return None
    now = datetime.now(timezone.utc)
    window = (now - timedelta(minutes=15)).isoformat()
    with sqlite3.connect(db_path, timeout=15) as conn:
        _init_login_tracking(conn)
        recent_failures = conn.execute(
            "SELECT COUNT(*) FROM Login_Attempts WHERE username=? AND attempted_at>=?",
            (username, window),
        ).fetchone()[0]
        if recent_failures >= 8:
            return None
        row = conn.execute(
            "SELECT user_id,username,full_name,role,theme_preference,password_hash "
            "FROM Users WHERE LOWER(username)=? AND is_active=1",
            (username,),
        ).fetchone()
        known_demo_passwords = {
            hashlib.sha256(b"admin123").hexdigest(),
            hashlib.sha256(b"password1").hexdigest(),
        }
        accepted = False
        upgraded = None
        if row and (_is_demo_mode() or row[5] not in known_demo_passwords):
            accepted, upgraded = _verify_password(password, row[5])
        if not accepted:
            _record_failed_login(conn, username, now)
            return None
        if upgraded:
            conn.execute("UPDATE Users SET password_hash=? WHERE user_id=?", (upgraded, row[0]))
        conn.execute("UPDATE Users SET last_login=? WHERE user_id=?", (now.isoformat(), row[0]))
        conn.execute("DELETE FROM Login_Attempts WHERE username=?", (username,))
        # Bound table growth without storing passwords, tokens, IP addresses or user PII.
        conn.execute(
            "DELETE FROM Login_Attempts WHERE attempted_at<?",
            (now - timedelta(days=1)).isoformat(),
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
    # Real registration requires a unique, admin-issued invitation.
    return not _is_demo_mode()


def register_member(db_path, username, full_name, email, password, invite_code):
    """Create an inactive member using an individually issued one-time token.

    The token and the account creation share the same SQLite transaction,
    preventing simultaneous redemption or uninvited registration.
    """
    username = str(username).strip().lower()
    full_name = str(full_name).strip()
    email = email_normalised(email)
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", username):
        raise ValueError("Use 3–30 letters, numbers or underscores; start with a letter.")
    if not (3 <= len(full_name) <= 120):
        raise ValueError("Please enter your full name.")
    password_hash = hash_password(password)
    with sqlite3.connect(db_path, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM Users WHERE LOWER(email)=?", (email,)).fetchone():
            raise ValueError("An account with this email already exists.")
        # Member ID is created before token redemption but rolled back on error.
        try:
            cursor = conn.execute(
                "INSERT INTO Users (username,password_hash,full_name,email,role,join_date,is_active,fica_verified) "
                "VALUES (?,?,?,?,'member',?,0,0)",
                (username, password_hash, full_name, email,
                 datetime.now(timezone.utc).isoformat()),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("That username is already in use.") from exc
        verify_and_use_invitation(conn, email, invite_code, cursor.lastrowid)
        return cursor.lastrowid
