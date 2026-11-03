"""Unforgeable, privacy-preserving self-service membership status receipts.

Receipts are random bearer credentials displayed once to an applicant.
Only SHA-256 digests are stored. Status queries reveal no identity, banking,
private correspondence or membership records. They expire after 45 days.
"""
import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

RECEIPT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{40,90}$")
RECEIPT_DAYS = 45


def ensure_receipt_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS Membership_Status_Receipts (
        application_id INTEGER PRIMARY KEY,
        token_sha256 TEXT NOT NULL UNIQUE,
        issued_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY(application_id)
          REFERENCES Membership_Applications(application_id)
    )""")


def issue_status_receipt(conn, application_id):
    """Issue within the caller's membership-application write transaction."""
    if type(application_id) is not int or application_id < 1:
        raise ValueError("Valid application required.")
    ensure_receipt_schema(conn)
    existing = conn.execute(
        "SELECT 1 FROM Membership_Status_Receipts WHERE application_id=?",
        (application_id,),
    ).fetchone()
    if existing:
        raise ValueError("An application receipt already exists.")
    token = secrets.token_urlsafe(32)
    if not RECEIPT_PATTERN.fullmatch(token):
        raise RuntimeError("Receipt generation failed.")
    now = datetime.now(timezone.utc)
    conn.execute(
        "INSERT INTO Membership_Status_Receipts "
        "(application_id,token_sha256,issued_at,expires_at) "
        "VALUES (?,?,?,?)",
        (application_id, hashlib.sha256(token.encode("ascii")).hexdigest(),
         now.isoformat(), (now + timedelta(days=RECEIPT_DAYS)).isoformat()),
    )
    return token


def get_public_application_status(db_path, receipt, *, now=None):
    """Return only a non-identifying status, or None for invalid/expired.

    Application IDs, names, emails, phone numbers, admin identities and
    reviews are deliberately excluded from this public result.
    """
    if not isinstance(receipt, str):
        return None
    candidate = receipt.strip()
    if not RECEIPT_PATTERN.fullmatch(candidate):
        return None
    digest = hashlib.sha256(candidate.encode("ascii")).hexdigest()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Status check requires an aware UTC time.")
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5) as conn:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('Membership_Applications','Membership_Status_Receipts')"
                )
            }
            if len(tables) != 2:
                return None
            record = conn.execute(
                "SELECT a.status,u.is_active,r.expires_at "
                "FROM Membership_Status_Receipts r "
                "JOIN Membership_Applications a ON a.application_id=r.application_id "
                "JOIN Users u ON u.user_id=a.user_id "
                "WHERE r.token_sha256=?",
                (digest,),
            ).fetchone()
    except (sqlite3.Error, ValueError):
        return None
    if not record:
        return None
    status, active, expires = record
    try:
        expiry = datetime.fromisoformat(expires)
    except (TypeError, ValueError):
        return None
    if expiry.tzinfo is None or now >= expiry:
        return None
    if status == "approved" and active != 1:
        return {"status": "inactive"}
    if status not in ("pending", "approved", "rejected"):
        return None
    return {"status": status}


def render_receipt_lookup():
    """Available on the public landing even when new registration is closed."""
    import streamlit as st
    from khula_config import DB_PATH

    with st.expander("Already applied? Check your membership status"):
        st.caption(
            "Use the private tracking code shown once when you registered. "
            "The lookup does not require a password and never reveals names "
            "or financial data. Tracking codes expire after 45 days."
        )
        with st.form("membership_receipt_lookup"):
            code = st.text_input(
                "Private application tracking code", type="password",
                key="lookup_membership_receipt"
            )
            if st.form_submit_button("Check application status"):
                result = get_public_application_status(DB_PATH, code)
                if not result:
                    st.warning(
                        "The code is invalid or expired. Please contact the "
                        "club administrator through a verified channel."
                    )
                elif result["status"] == "pending":
                    st.info(
                        "Your application is awaiting administrator review. "
                        "Do not submit another account request."
                    )
                elif result["status"] == "approved":
                    st.success(
                        "Your application was approved. You can use your "
                        "registered username and password to sign in."
                    )
                elif result["status"] == "rejected":
                    st.warning(
                        "This application was not approved. Contact the club "
                        "administrator privately if you believe there is an error."
                    )
                else:
                    st.warning(
                        "This account is currently inactive. Contact the club "
                        "administrator before attempting to sign in."
                    )
