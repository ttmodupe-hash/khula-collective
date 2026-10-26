"""Per-member single-use invitation codes for real club onboarding.

The club administrator creates one code tied to an exact email; only its digest
is stored, and the code is consumed atomically upon signup. Sharing is manual
until a verified transactional-email provider has been connected.
"""
import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def email_normalised(value):
    email = str(value).strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Provide a valid member email address.")
    return email


def ensure_invitation_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS Member_Invitations (
        invitation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        token_sha256 TEXT UNIQUE NOT NULL,
        created_by INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used_at TEXT,
        used_by INTEGER,
        FOREIGN KEY(created_by) REFERENCES Users(user_id),
        FOREIGN KEY(used_by) REFERENCES Users(user_id)
    )""")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_invitation_email ON Member_Invitations(email)"
    )


def generate_invitation(db_path, admin_id, email, hours=168):
    email = email_normalised(email)
    if not isinstance(hours, int) or not 1 <= hours <= 168:
        raise ValueError("Invitation must expire within seven days.")
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    now = datetime.now(timezone.utc)
    with sqlite3.connect(db_path, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        ensure_invitation_table(conn)
        admin = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND role='admin' AND is_active=1",
            (admin_id,),
        ).fetchone()
        if not admin:
            raise PermissionError("Only an active administrator can invite members.")
        if conn.execute("SELECT 1 FROM Users WHERE LOWER(email)=?", (email,)).fetchone():
            raise ValueError("An account with this email already exists.")
        conn.execute(
            "INSERT INTO Member_Invitations "
            "(email,token_sha256,created_by,created_at,expires_at) VALUES (?,?,?,?,?)",
            (email, digest, admin_id, now.isoformat(), (now + timedelta(hours=hours)).isoformat()),
        )
    return token


def verify_and_use_invitation(conn, email, token, member_id):
    """Must execute within the same write transaction that creates the user."""
    email = email_normalised(email)
    if not isinstance(token, str) or len(token) < 30 or len(token) > 90:
        raise ValueError("Invalid or expired invitation.")
    ensure_invitation_table(conn)
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = conn.execute(
        "SELECT invitation_id, expires_at FROM Member_Invitations "
        "WHERE email=? AND token_sha256=? AND used_at IS NULL",
        (email, digest),
    ).fetchone()
    now = datetime.now(timezone.utc)
    if not row:
        raise ValueError("Invalid or expired invitation.")
    try:
        expires = datetime.fromisoformat(row[1])
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid or expired invitation.") from exc
    if expires.tzinfo is None or now >= expires:
        raise ValueError("Invalid or expired invitation.")
    updated = conn.execute(
        "UPDATE Member_Invitations SET used_at=?, used_by=? "
        "WHERE invitation_id=? AND used_at IS NULL",
        (now.isoformat(), member_id, row[0]),
    )
    if updated.rowcount != 1:
        raise ValueError("Invitation already used.")
    return True


def recent_invitations(db_path, admin_id):
    with sqlite3.connect(db_path) as conn:
        admin = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND role='admin' AND is_active=1",
            (admin_id,),
        ).fetchone()
        if not admin:
            raise PermissionError("Only administrators can see invitation status.")
        ensure_invitation_table(conn)
        return conn.execute(
            "SELECT email,created_at,expires_at,used_at "
            "FROM Member_Invitations ORDER BY invitation_id DESC LIMIT 25"
        ).fetchall()


def render_invitation_admin():
    import streamlit as st
    from khula_config import DB_PATH

    if st.session_state.get("role") != "admin":
        st.error("Administrator access required.")
        return
    st.title("✉️ Invite real Khula members")
    st.info(
        "Issue a unique single-use code for each intended member's email. "
        "The code expires after seven days. Share it directly through a trusted "
        "channel, never a public post. Every new account requires your separate activation."
    )
    with st.form("invite_real_member"):
        email = st.text_input("Member email address")
        if st.form_submit_button("Create single-use invitation"):
            try:
                token = generate_invitation(DB_PATH, st.session_state.user_id, email)
                st.session_state["last_invitation"] = {"email": email, "token": token}
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
    last = st.session_state.get("last_invitation")
    if last:
        st.success(f"One-time code generated for {last['email']}. Copy and share privately.")
        st.code(last["token"], language=None)
        if st.button("Hide this code from my session"):
            st.session_state.pop("last_invitation", None)
            st.rerun()
    invitations = recent_invitations(DB_PATH, st.session_state.user_id)
    if invitations:
        st.subheader("Invitation records (codes are not stored)")
        st.dataframe([
            {"Email": e, "Created": created, "Expires": expires,
             "Status": "used" if used else "pending/expired"}
            for e, created, expires, used in invitations
        ], use_container_width=True)
