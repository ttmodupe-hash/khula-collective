"""Administrator-issued, one-use recovery for real Khula members.

Recovery deliberately requires independent administrator identity checks.
Tokens are never sent automatically or saved in plaintext. Public callers
cannot request a reset token, learn whether an email exists or reset an admin.
"""
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from khula_invitations import email_normalised
from khula_security import hash_password

RESET_VALID_MINUTES = 30
MAX_FAILED_RECOVERIES = 6


def ensure_recovery_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS Member_Recovery_Tokens (
        recovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT UNIQUE NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        consumed_at TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id),
        FOREIGN KEY(created_by) REFERENCES Users(user_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS Recovery_Attempts (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        attempted_at TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recovery_user ON Member_Recovery_Tokens(user_id,created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recovery_attempts ON Recovery_Attempts(username,attempted_at)")


def issue_member_recovery(db_path, admin_id, member_id):
    """Issue a single-use 30-minute code after off-platform identity checks.

    Return plaintext only once to the logged-in administrator. Regenerating
    invalidates earlier outstanding codes for the same member.
    """
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    now = datetime.now(timezone.utc)
    with sqlite3.connect(db_path, timeout=20) as conn:
        conn.execute("BEGIN IMMEDIATE")
        ensure_recovery_tables(conn)
        admin = conn.execute(
            "SELECT role,is_active FROM Users WHERE user_id=?", (admin_id,)
        ).fetchone()
        if not admin or admin != ("admin", 1):
            raise PermissionError("Administrator required.")
        member = conn.execute(
            "SELECT role,is_active FROM Users WHERE user_id=?", (member_id,)
        ).fetchone()
        if not member or member != ("member", 1):
            raise ValueError("Only active members are eligible for this recovery method.")
        conn.execute(
            "UPDATE Member_Recovery_Tokens SET consumed_at=? "
            "WHERE user_id=? AND consumed_at IS NULL",
            (now.isoformat(), member_id),
        )
        conn.execute(
            "INSERT INTO Member_Recovery_Tokens "
            "(user_id,token_hash,created_by,created_at,expires_at) VALUES (?,?,?,?,?)",
            (member_id, digest, admin_id, now.isoformat(),
             (now + timedelta(minutes=RESET_VALID_MINUTES)).isoformat()),
        )
        conn.execute(
            "INSERT INTO Admin_Actions (admin_user_id,action_type,details) "
            "VALUES (?,?,?)",
            (admin_id, "member_password_recovery_issued",
             f"member_id={member_id}; expires_in_min={RESET_VALID_MINUTES}"),
        )
    return token


def redeem_member_recovery(db_path, username, email, token, new_password):
    """Change one active member's password and expire their other sessions.

    No account existence or token details are returned to the public UI.
    """
    username = str(username).strip().lower()
    if not username or len(username) > 64:
        raise ValueError("Recovery information is invalid or expired.")
    try:
        email = email_normalised(email)
    except (TypeError, ValueError) as exc:
        raise ValueError("Recovery information is invalid or expired.") from exc
    if not isinstance(token, str) or not 35 <= len(token) <= 90:
        raise ValueError("Recovery information is invalid or expired.")
    # Validate the new password before using a one-time token.
    new_hash = hash_password(new_password)
    token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    window = (now - timedelta(minutes=15)).isoformat()

    with sqlite3.connect(db_path, timeout=20) as conn:
        conn.execute("BEGIN IMMEDIATE")
        ensure_recovery_tables(conn)
        failed = conn.execute(
            "SELECT COUNT(*) FROM Recovery_Attempts "
            "WHERE username=? AND attempted_at>=?",
            (username, window),
        ).fetchone()[0]
        if failed >= MAX_FAILED_RECOVERIES:
            raise ValueError("Recovery information is invalid or expired.")
        row = conn.execute(
            "SELECT user_id FROM Users WHERE LOWER(username)=? "
            "AND LOWER(email)=? AND role='member' AND is_active=1",
            (username, email),
        ).fetchone()
        accepted = False
        token_id = None
        if row:
            evidence = conn.execute(
                "SELECT recovery_id,token_hash,expires_at FROM Member_Recovery_Tokens "
                "WHERE user_id=? AND consumed_at IS NULL",
                (row[0],),
            ).fetchall()
            for recovery_id, expected_hash, expiry in evidence:
                if hmac.compare_digest(token_digest, expected_hash):
                    try:
                        expiry_date = datetime.fromisoformat(expiry)
                        accepted = expiry_date.tzinfo is not None and now < expiry_date
                    except (TypeError, ValueError):
                        accepted = False
                    token_id = recovery_id
                    break
        if not accepted:
            # Commit failed-attempt evidence even though the public request fails.
            conn.execute(
                "INSERT INTO Recovery_Attempts(username,attempted_at) VALUES (?,?)",
                (username, now.isoformat()),
            )
        else:
            updated = conn.execute(
                "UPDATE Member_Recovery_Tokens SET consumed_at=? "
                "WHERE recovery_id=? AND consumed_at IS NULL",
                (now.isoformat(), token_id),
            )
            if updated.rowcount != 1:
                raise ValueError("Recovery information is invalid or expired.")
            conn.execute(
                "UPDATE Users SET password_hash=?, auth_epoch=auth_epoch+1,"
                "must_change_password=0 WHERE user_id=? AND role='member' AND is_active=1",
                (new_hash, row[0]),
            )
            conn.execute("DELETE FROM Recovery_Attempts WHERE username=?", (username,))
    if not accepted:
        raise ValueError("Recovery information is invalid or expired.")
    return True


def render_member_recovery():
    import streamlit as st
    from khula_config import DB_PATH

    with st.expander("Forgot your password? Recover with your club administrator"):
        st.caption(
            "Ask your club administrator to verify your identity privately and issue "
            "a one-use recovery code. It expires after 30 minutes. "
            "The club never asks for your bank PIN or banking password."
        )
        with st.form("khula_recover_member"):
            username = st.text_input("Existing username", key="recovery_username")
            email = st.text_input("Registered email", key="recovery_email")
            code = st.text_input("One-time recovery code", type="password", key="recovery_token")
            password = st.text_input("New password (12–72 UTF-8 bytes)", type="password",
                                     key="recovery_new_password")
            confirm = st.text_input("Confirm new password", type="password", key="recovery_confirm")
            if st.form_submit_button("Reset my member password"):
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        redeem_member_recovery(DB_PATH, username, email, code, password)
                        st.success("Password changed. Return to login with your new password.")
                    except (ValueError, PermissionError):
                        st.error("Recovery failed. Check with your club administrator.")


def render_recovery_admin():
    import streamlit as st
    from khula_config import DB_PATH

    if st.session_state.get("role") != "admin":
        st.error("Administrator access required.")
        return
    st.title("🔑 Member account recovery")
    st.warning(
        "Before generating any code, independently confirm the member's identity "
        "and registered contact. Deliver codes privately; do not share them in group chats."
    )
    with sqlite3.connect(DB_PATH) as conn:
        members = conn.execute(
            "SELECT user_id,full_name,email FROM Users "
            "WHERE role='member' AND is_active=1 ORDER BY full_name"
        ).fetchall()
    if not members:
        st.info("No active members have been onboarded yet.")
        return
    labels = {
        f"{name} · {email or 'no email'} (#{uid})": uid
        for uid, name, email in members
    }
    member_name = st.selectbox("Select a member", list(labels))
    approved = st.checkbox(
        "I verified the member's identity using a trusted independent channel."
    )
    if st.button("Issue a one-time recovery code", disabled=not approved):
        try:
            token = issue_member_recovery(DB_PATH, st.session_state.user_id, labels[member_name])
            st.session_state["member_recovery_new_token"] = {"token": token, "member_id": labels[member_name]}
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))
    token = st.session_state.get("member_recovery_new_token")
    if token and token.get("member_id") == labels[member_name]:
        st.code(token["token"], language=None)
        st.caption("Copy and deliver privately. This code is not stored in plaintext.")
        if st.button("Clear recovery code from this session"):
            st.session_state.pop("member_recovery_new_token", None)
            st.rerun()
