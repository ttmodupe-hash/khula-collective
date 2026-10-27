"""FNB read-only Integration Channel application tracking.

This is not a bank adapter. Only an actual bank-approved OAuth connection and
verified bank-sourced reads can change the production 'connected' status.
There is intentionally no API credential input, bank login or token collection.
"""
import os
import re
import sqlite3
from datetime import datetime, timezone

from khula_compliance import onboarding_gate_status, organisation_details

OFFICIAL_CATALOGUE = (
    "https://www.fnb.co.za/integration-channel/catalogue/serviceCatalogue-ZA/"
    "services.html?catalogue=serviceCatalogue-ZA&service=Transaction-History&type=API"
)
INTEGRATION_CHANNEL = "https://www.fnb.co.za/integration-channel/index.html"


def bank_integration_email(legal_name=None, contact_email=None):
    """Safe email for the bank's known relationship manager; no account numbers."""
    details = organisation_details()
    organisation = str(legal_name or details["name"] or "Khula Collective").strip()
    reply_to = str(contact_email or details["contact_email"] or
                   "[authorised club representative's email]").strip()
    if "\n" in organisation or "\r" in organisation or len(organisation) > 150:
        raise ValueError("Invalid organisation name.")
    subject = "Khula Collective — request for read-only FNB Transaction History API access"
    body = f"""Dear FNB Integration Channel / Business Banking Team,

I am contacting you on behalf of {organisation}, a South African
members-only collective savings and investment-club project.

We would like to apply for an approved, secure read-only integration
between our authorised FNB club account and the Khula Collective member
application: https://khula-collective-production.up.railway.app

Our purpose is to reconcile members' contributions against actual bank
transactions, confirm available bank cash after reserved funds, and
produce transparent audited member and governance reports.

We are requesting the Transaction History / account-information API
ONLY. We do not seek payment initiation, debit-order creation,
beneficiary changes, account-to-account transfers, trading authority,
or the ability to move or withdraw money from the club account.

Please advise on:

1. Eligibility of our actual club-account type and whether FNB Online
   Banking Enterprise or Integration Channel registration is required.
2. The authorised signatory mandate, required club constitution,
   registration, FICA/KYC and other bank onboarding documents.
3. Direct client API versus an FNB-approved intermediary and the
   account-holder consent/delegation and revocation process.
4. Documentation and sandbox access for the Transaction History API,
   available fields (dated balances, credits, debits, references),
   OAuth 2.0 authorisation, client credentials, least-privilege scopes,
   redirect URI and token refresh/revocation.
5. API polling limits, reconciliation history, uptime, cost,
   commercial terms, security standards and production certification.
6. Data-protection and cross-border requirements: our current hosting
   arrangement includes an overseas cloud region, so we need guidance
   on whether your agreement permits this and on safeguards required
   under POPIA and FNB's technical/contractual policies.
7. Whether a secure read-only Host-to-Host or bank-statement delivery
   alternative is available if Transaction History API eligibility
   cannot be granted to our account.

We can provide proof of authority from the club signatories and the
required documents through FNB's approved secure channel. Please do
not request passwords, PINs, OTPs or full bank statements in ordinary
email. We are not asking for API secrets to be included in email.

Kindly refer us to the appropriate Digital Profile, Transactional
Portfolio or Implementation Manager and advise how to begin the
eligibility assessment.

Regards,
[Authorised Khula Collective representative]
{reply_to}
Khula Collective
"""
    return {"subject": subject, "body": body}


def ensure_tracking_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS FNB_Access_Requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT NOT NULL DEFAULT 'draft',
        summary TEXT NOT NULL,
        fnb_reference TEXT,
        submitted_by INTEGER NOT NULL,
        submitted_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(submitted_by) REFERENCES Users(user_id)
    )""")


def record_application_submission(db_path, admin_id, reference):
    """Tracks the bank-application step, not a live connection or bank approval."""
    reference = str(reference).strip()
    if not 5 <= len(reference) <= 70 or not re.fullmatch(r"[A-Za-z0-9_./-]+", reference):
        raise ValueError("Use only the official FNB contact/application reference (5–70 characters).")
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute("SELECT role,is_active FROM Users WHERE user_id=?", (admin_id,)).fetchone()
        if user != ("admin", 1):
            raise PermissionError("Active administrator required.")
        ensure_tracking_schema(conn)
        cursor = conn.execute(
            "INSERT INTO FNB_Access_Requests(state,summary,fnb_reference,submitted_by,submitted_at,updated_at) "
            "VALUES ('application_submitted','Read-only Transaction History API eligibility requested',?,?,?,?)",
            (reference, admin_id, now, now),
        )
        conn.execute(
            "INSERT INTO Admin_Actions(admin_user_id,action_type,details) VALUES (?,?,?)",
            (admin_id, "fnb_api_application_logged", "tracking_id=" + str(cursor.lastrowid)),
        )
    return cursor.lastrowid


def latest_application(db_path, admin_id):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT role,is_active FROM Users WHERE user_id=?", (admin_id,)).fetchone()
        if row != ("admin", 1):
            raise PermissionError("Administrator required.")
        ensure_tracking_schema(conn)
        state = conn.execute(
            "SELECT request_id,state,summary,fnb_reference,submitted_at "
            "FROM FNB_Access_Requests ORDER BY request_id DESC LIMIT 1"
        ).fetchone()
    return state


def render_bank_access_admin():
    import streamlit as st
    from khula_config import DB_PATH

    if st.session_state.get("role") != "admin":
        st.error("Administrator access required.")
        return

    st.title("🏦 FNB read-only account connection")
    st.error("LIVE BANK FEED: NOT CONNECTED")
    st.caption(
        "This page prepares a bank application and tracks your official reference. "
        "It does not connect to FNB, authenticate to online banking, "
        "or approve an application on behalf of the bank."
    )
    status = onboarding_gate_status()
    if not status["ready"]:
        st.warning(
            "Some POPIA/governance conditions remain outstanding. "
            "Bank application discussions may proceed, but don't import "
            "real-member data or activate bank credentials until approvals are complete."
        )
    st.write("FNB official Integration Channel:", INTEGRATION_CHANNEL)
    st.write("Transaction History API:", OFFICIAL_CATALOGUE)
    letter = bank_integration_email()
    st.subheader("Ready-to-review application email")
    st.text_input("Email subject", letter["subject"], disabled=True)
    st.text_area("Copy and send through your FNB relationship manager", letter["body"], height=420)
    st.info(
        "Never disclose your bank login, OTP, account number, OAuth client secret or "
        "other sensitive credentials in this application email. "
        "Use the bank's authenticated onboarding channel."
    )
    existing = latest_application(DB_PATH, st.session_state.user_id)
    if existing:
        st.caption(
            "Latest tracked application: #" + str(existing[0]) + " · " + existing[1]
            + " · submitted " + existing[4]
            + ". This is NOT bank approval or account-link verification."
        )
    with st.form("fnb_api_request_tracking"):
        reference = st.text_input("FNB official application / case reference (not a bank account number)")
        proof = st.checkbox(
            "I confirm an application or request was actually submitted through an authorised FNB channel."
        )
        if st.form_submit_button("Log submitted FNB request"):
            if not proof:
                st.error("An application must be submitted to FNB before it is logged.")
            else:
                try:
                    record_application_submission(DB_PATH, st.session_state.user_id, reference)
                    st.success("Bank application reference logged. No account has been connected.")
                    st.rerun()
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
