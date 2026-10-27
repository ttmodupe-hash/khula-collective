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
import os
from khula_compliance import onboarding_gate_status, organisation_details, running_live

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
    # An invitation identifies a real person; require signed-off safeguards
    # before creating this record on the production service.
    if running_live() and not onboarding_gate_status()["ready"]:
        raise ValueError("Invitation issue is paused pending POPIA and governance approvals.")
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


def invitation_email_draft(member_email, token, *, site_url="https://khula-collective-production.up.railway.app",
                           privacy_email=None, days_valid=7):
    """Copyable member invitation; caller must have generated an actual token."""
    email = email_normalised(member_email)
    if not isinstance(token, str) or len(token) < 30:
        raise ValueError("Issue a valid one-use invitation before composing the email.")
    privacy_email = privacy_email or "[the club's Information Officer]"
    subject = "Your private Khula Collective membership invitation"
    message = f"""Hello,

You've been invited to join the Khula Collective members' portal.

Open this address in your browser:
{site_url}

Select “New member? Register with your invitation” and use this email:
{email}

Your personal, single-use registration code:
{token}

This code expires within {days_valid} days. Please do not forward it.
Create your own strong password. After signing up, your account will
remain inactive until a club administrator confirms your membership.

Before registering, read the privacy notice on the sign-in page. It
explains what information Khula collects and its overseas hosting.
The club constitution and contribution rules must be ratified before
financial commitments are enforced. Contributions should only be made
using account details independently confirmed through the club's
authorised banking channel.

Khula will never ask you to share your FNB login, bank PIN or OTP.
If you weren't expecting this invitation, do not use the code and
contact the club directly. You may ask the club to stop contacting you.

Privacy queries: {privacy_email}

Khula Collective Administration
"""
    return {"subject": subject, "body": message}


def render_invitation_admin():
    import streamlit as st
    from khula_config import DB_PATH

    if st.session_state.get("role") != "admin":
        st.error("Administrator access required.")
        return
    st.title("✉️ Invite genuine Khula members")
    status = onboarding_gate_status()
    if running_live() and not status["ready"]:
        st.error("Real-member invitations are paused while privacy and governance prerequisites are outstanding.")
        for blocker in status["missing"]:
            st.write("• " + blocker)
        st.caption("Complete the legal/operational requirements first. No member codes are issued during the hold.")
        return

    st.info(
        "Each token is tied to exactly one intended member email, expires within "
        "seven days and can be used only once. Issue it only to someone who "
        "has requested or expects the club's invitation. Never post codes in a group."
    )
    with st.form("invite_real_member"):
        email = st.text_input("Member email address")
        approved = st.checkbox(
            "This intended member has a legitimate club relationship or has requested an invitation."
        )
        if st.form_submit_button("Create one-time private invitation"):
            if not approved:
                st.error("Confirm the intended member's expectation and use of their contact details.")
            else:
                try:
                    address = email_normalised(email)
                    token = generate_invitation(DB_PATH, st.session_state.user_id, address)
                    st.session_state["last_invitation"] = {"email": address, "token": token}
                    st.success("Private invitation issued. Copy the draft below and send it through an approved channel.")
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))

    last = st.session_state.get("last_invitation")
    if last:
        try:
            draft = invitation_email_draft(
                last["email"], last["token"],
                privacy_email=organisation_details()["contact_email"] or None
            )
            st.text_input("Email recipient", value=last["email"], disabled=True)
            st.text_input("Email subject", value=draft["subject"], disabled=True)
            st.text_area(
                "Copy this member-specific invitation email (includes private one-use code)",
                value=draft["body"], height=390
            )
            st.caption(
                "This draft is NOT sent by Khula. Review the recipient and transmit it "
                "privately through an authorised email or messaging channel."
            )
        except ValueError:
            st.warning("The invitation draft is unavailable.")
        if st.button("Clear the one-use code from this session"):
            st.session_state.pop("last_invitation", None)
            st.rerun()

    invitations = recent_invitations(DB_PATH, st.session_state.user_id)
    if invitations:
        st.subheader("Invitation audit history — tokens are never retrievable")
        st.dataframe([
            {"Email": e, "Issued": created, "Expires": expires,
             "Status": "redeemed" if used else "pending / expired"}
            for e, created, expires, used in invitations
        ], use_container_width=True)
