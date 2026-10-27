"""Public Khula membership applications with explicit administrator admission.

Public sign-up is NOT access. Applicants are inactive members until an active
administrator independently verifies the person, approves the request and
commits the approval in a single SQLite transaction. No banking credentials,
ID numbers, sensitive documents or payment proof are accepted here.
"""
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta

from khula_compliance import onboarding_gate_status, record_notice_acknowledgement, running_live
from khula_invitations import email_normalised

USERNAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,29}$")
MAX_HOURLY_APPLICATIONS = 30
MAX_DAILY_APPLICATIONS = 120


def ensure_applications_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS Membership_Applications (
        application_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        source TEXT NOT NULL CHECK(source IN ('public','invitation')),
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','approved','rejected')),
        submitted_at TEXT NOT NULL,
        cross_border_consent_at TEXT,
        notice_version TEXT,
        reviewed_by INTEGER,
        reviewed_at TEXT,
        review_result TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id),
        FOREIGN KEY(reviewed_by) REFERENCES Users(user_id)
    )""")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_khula_application_queue "
        "ON Membership_Applications(status,submitted_at)"
    )


def public_registration_enabled():
    from khula_security import registration_enabled
    return (registration_enabled()
            and os.environ.get("KHULA_PUBLIC_REGISTRATION_PAUSED") != "1")


def _application_count(conn, since):
    return conn.execute(
        "SELECT COUNT(*) FROM Membership_Applications "
        "WHERE source='public' AND submitted_at>=?",
        (since.isoformat(),),
    ).fetchone()[0]


def request_membership(
        db_path, username, full_name, email, password, *,
        notice_acknowledged, international_transfer_acknowledged,
        adult_confirmed):
    """Request a real account without needing an administrator invitation.

    A successful request cannot authenticate and has role=member,is_active=0.
    It has no effect on the financial ledger or savings balances.
    """
    if not public_registration_enabled():
        raise ValueError(
            "Membership applications are not accepting personal information "
            "until the club's required privacy and governance approvals are recorded."
        )
    if (notice_acknowledged is not True
            or international_transfer_acknowledged is not True
            or adult_confirmed is not True):
        raise ValueError(
            "Please confirm the privacy notice, overseas hosting and that "
            "you are at least 18 years old before submitting."
        )
    username = str(username).strip().lower()
    full_name = str(full_name).strip()
    email = email_normalised(email)
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Use a username of 3–30 letters/numbers/underscores, starting with a letter.")
    if not (3 <= len(full_name) <= 120) or any(ord(ch) < 32 for ch in full_name):
        raise ValueError("Enter a full name between 3 and 120 characters.")
    # Imported here to avoid circular module imports at application import time.
    from khula_security import hash_password
    password_hash = hash_password(password)
    now = datetime.now(timezone.utc)
    with sqlite3.connect(db_path, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        # Recheck safety gate after lock to avoid accepting data during a
        # temporary config change or administrator pause.
        if not public_registration_enabled():
            raise ValueError("Membership applications are temporarily closed.")
        ensure_applications_schema(conn)
        if (_application_count(conn, now - timedelta(hours=1)) >= MAX_HOURLY_APPLICATIONS
                or _application_count(conn, now - timedelta(days=1)) >= MAX_DAILY_APPLICATIONS):
            raise ValueError("Membership requests are at capacity. Contact the club administrator.")
        existing = conn.execute(
            "SELECT 1 FROM Users WHERE username=? OR LOWER(email)=? LIMIT 1",
            (username, email),
        ).fetchone()
        if existing:
            raise ValueError("These details cannot be registered. Contact the club administrator privately.")
        try:
            user = conn.execute(
                "INSERT INTO Users (username,password_hash,full_name,email,role,join_date,"
                "is_active,fica_verified,must_change_password) "
                "VALUES (?,?,?,?,'member',?,0,0,0)",
                (username, password_hash, full_name, email, now.isoformat()),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("These details cannot be registered. Contact the club administrator privately.") from exc
        user_id = user.lastrowid
        # Notice/hash acknowledgement is atomic with the account and queue.
        record_notice_acknowledgement(conn, user_id)
        notice = onboarding_gate_status()["details"]["version"]
        cursor = conn.execute(
            "INSERT INTO Membership_Applications "
            "(user_id,source,status,submitted_at,cross_border_consent_at,notice_version) "
            "VALUES (?,'public','pending',?,?,?)",
            (user_id, now.isoformat(), now.isoformat(), notice),
        )
        return cursor.lastrowid


def list_membership_requests(db_path, admin_id, *, status="pending"):
    if status not in ("pending", "approved", "rejected"):
        raise ValueError("Unsupported application status.")
    with sqlite3.connect(db_path) as conn:
        active_admin = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND role='admin' AND is_active=1",
            (admin_id,),
        ).fetchone()
        if not active_admin:
            raise PermissionError("An active administrator must review members.")
        ensure_applications_schema(conn)
        return conn.execute(
            "SELECT a.application_id,u.user_id,u.username,u.full_name,u.email,"
            "a.source,a.submitted_at,a.status "
            "FROM Membership_Applications a JOIN Users u ON u.user_id=a.user_id "
            "WHERE a.status=? ORDER BY a.submitted_at ASC LIMIT 100",
            (status,),
        ).fetchall()


def review_membership_request(
        db_path, admin_id, application_id, decision, *,
        identity_confirmed=False, eligibility_confirmed=False):
    """An auditable approval is the ONLY public-application activation path."""
    if decision not in ("approved", "rejected"):
        raise ValueError("Unsupported membership decision.")
    if type(application_id) is not int or application_id <= 0:
        raise ValueError("Choose a valid membership request.")
    if decision == "approved" and (
            identity_confirmed is not True or eligibility_confirmed is not True):
        raise ValueError(
            "Confirm the applicant's identity/contact and club eligibility "
            "independently before approving."
        )
    if running_live() and not onboarding_gate_status()["ready"]:
        raise ValueError(
            "Member access must not be activated before the privacy and "
            "governance review has been completed."
        )
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        active_admin = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND role='admin' AND is_active=1",
            (admin_id,),
        ).fetchone()
        if not active_admin:
            raise PermissionError("Active administrator required.")
        ensure_applications_schema(conn)
        record = conn.execute(
            "SELECT a.user_id,a.status,u.role,u.is_active,u.email "
            "FROM Membership_Applications a JOIN Users u ON u.user_id=a.user_id "
            "WHERE a.application_id=?",
            (application_id,),
        ).fetchone()
        if not record or record[1] != "pending":
            raise ValueError("Membership request already handled or not found.")
        user_id, _, role, active, email = record
        if role != "member" or active != 0 or user_id == admin_id:
            raise PermissionError("Only inactive applicant members may be reviewed.")
        if decision == "approved":
            # Confirm a previously acknowledged privacy notice exists. An
            # unverified email must not be treated as authenticated by the app.
            ack = conn.execute(
                "SELECT 1 FROM Member_Privacy_Acknowledgements WHERE user_id=?",
                (user_id,),
            ).fetchone()
            if not ack:
                raise ValueError("No approved privacy acknowledgement is recorded.")
            updated = conn.execute(
                "UPDATE Users SET is_active=1,auth_epoch=auth_epoch+1 "
                "WHERE user_id=? AND role='member' AND is_active=0",
                (user_id,),
            )
            if updated.rowcount != 1:
                raise ValueError("Application already activated.")
        else:
            # Rejection never destroys a financial or historical record.
            conn.execute(
                "UPDATE Users SET is_active=0,auth_epoch=auth_epoch+1 WHERE user_id=?",
                (user_id,),
            )
        changed = conn.execute(
            "UPDATE Membership_Applications SET status=?,reviewed_by=?,"
            "reviewed_at=?,review_result=? "
            "WHERE application_id=? AND status='pending'",
            (decision, admin_id, now, "member identity/eligibility reviewed"
             if decision == "approved" else "membership not approved", application_id),
        )
        if changed.rowcount != 1:
            raise ValueError("Application state has changed.")
        conn.execute(
            "INSERT INTO Admin_Actions(admin_user_id,action_type,details) "
            "VALUES (?,?,?)",
            (admin_id, "membership_application_" + decision,
             "application_id=" + str(application_id)
             + "; applicant_user_id=" + str(user_id)),
        )
        return {"application_id": application_id, "user_id": user_id, "status": decision}


def render_membership_approvals():
    import streamlit as st
    from khula_config import DB_PATH

    if st.session_state.get("role") != "admin":
        st.error("Administrator access required.")
        return
    st.title("✅ Membership applications")
    st.caption(
        "Anyone may request membership once the approved privacy setup is active. "
        "Only an authorised administrator can admit a person to private data."
    )
    if running_live() and not onboarding_gate_status()["ready"]:
        st.warning(
            "The privacy/constitution onboarding review remains incomplete. "
            "No applicant can be activated until the club records genuine approvals."
        )
    pending = list_membership_requests(DB_PATH, st.session_state.user_id)
    st.metric("Awaiting review", len(pending))
    if not pending:
        st.success("No pending public membership applications.")
        return
    for aid, uid, username, name, email, source, submitted, status in pending:
        with st.expander(f"Request #{aid}: {name} — {source}"):
            st.write(f"Username: {username}")
            st.write(f"Contact email: {email} (not automatically verified)")
            st.caption(f"Submitted (UTC): {submitted}")
            st.info(
                "Verify the applicant through a trusted, independent club contact "
                "channel. Do NOT request banking passwords, OTPs or identity photos "
                "in the chat. Completing checkboxes records an administrator's "
                "attestation; it is not automatic identity or FICA verification."
            )
            checked_identity = st.checkbox(
                "I independently verified this person's identity and contact",
                key=f"identity_{aid}",
            )
            checked_club = st.checkbox(
                "The applicant is authorised to join under the club rules",
                key=f"eligibility_{aid}",
            )
            a, b = st.columns(2)
            with a:
                if st.button(
                    "Approve membership",
                    key=f"approve_membership_{aid}",
                    disabled=not (checked_identity and checked_club),
                    type="primary",
                ):
                    try:
                        review_membership_request(
                            DB_PATH, st.session_state.user_id, aid, "approved",
                            identity_confirmed=checked_identity,
                            eligibility_confirmed=checked_club,
                        )
                        st.success("Membership approved; credentials may now access the private portal.")
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))
            with b:
                if st.button("Reject request", key=f"reject_membership_{aid}"):
                    try:
                        review_membership_request(
                            DB_PATH, st.session_state.user_id, aid, "rejected"
                        )
                        st.warning("Application rejected. No login access was granted.")
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))
    st.caption(
        "Approvals and rejections are audit-logged. Khula does not currently "
        "send automatic acceptance emails; notify members privately after review."
    )
