"""Operational compliance gates and public privacy information for Khula.

An environment flag is an acknowledgement that a human completed a task,
not regulatory certification. These gates prevent unreviewed production
onboarding while leaving existing accounts able to access the app.
"""
import hashlib
import os
import re
import sqlite3
from datetime import datetime, timezone

EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def running_live(env=None):
    """Treat Railway's production environment as real even without app flags."""
    env = env if env is not None else os.environ
    return (env.get("KHULA_PRODUCTION") == "1"
            or env.get("RAILWAY_ENVIRONMENT_NAME", "").lower() == "production")


APPROVAL_FLAGS = {
    "KHULA_PRIVACY_NOTICE_APPROVED": "Approved POPIA privacy notice",
    "KHULA_INFORMATION_OFFICER_REGISTERED": "Information Officer registered with the Information Regulator",
    "KHULA_CROSS_BORDER_REVIEW_APPROVED": "POPIA section 72 transfer assessment and safeguard completed",
    "KHULA_OPERATOR_DPA_REVIEWED": "Railway/cloud operator privacy terms and written safeguards reviewed",
    "KHULA_CONSTITUTION_RATIFIED": "Final member-governance constitution ratified",
}


def organisation_details(env=None):
    env = env if env is not None else os.environ
    name = str(env.get("KHULA_RESPONSIBLE_PARTY_NAME", "")).strip()
    email = str(env.get("KHULA_PRIVACY_CONTACT_EMAIL", "")).strip().lower()
    version = str(env.get("KHULA_PRIVACY_NOTICE_VERSION", "draft-2026-10")).strip()
    return {"name": name, "contact_email": email, "version": version}


def onboarding_gate_status(env=None):
    env = env if env is not None else os.environ
    details = organisation_details(env)
    missing = [
        description for flag, description in APPROVAL_FLAGS.items()
        if env.get(flag) != "1"
    ]
    if not 3 <= len(details["name"]) <= 150:
        missing.append("Responsible party's verified full legal name")
    if not EMAIL.fullmatch(details["contact_email"]) or len(details["contact_email"]) > 254:
        missing.append("Valid Information Officer / privacy contact email")
    if (not re.fullmatch(r"[A-Za-z0-9._-]{4,64}", details["version"])
            or "draft" in details["version"].lower()):
        missing.append("Reviewed and approved (non-draft) privacy notice version")
    doc = str(env.get("KHULA_CONSTITUTION_DOCUMENT_TEXT", ""))
    doc_hash = str(env.get("KHULA_CONSTITUTION_SHA256", "")).lower()
    constitution_version = str(env.get("KHULA_CONSTITUTION_VERSION", "")).strip()
    if (len(doc) < 500 or len(doc) > 50000
            or not re.fullmatch(r"[A-Za-z0-9._-]{4,64}", constitution_version)
            or "draft" in constitution_version.lower()
            or not re.fullmatch(r"[0-9a-f]{64}", doc_hash)
            or hashlib.sha256(doc.encode("utf-8")).hexdigest() != doc_hash):
        missing.append("Ratified constitution text, unique version and matching SHA-256 digest")
    return {
        "ready": not missing,
        "missing": missing,
        "details": details,
        "status": "operator-attested; not external certification",
    }


def ratified_constitution(env=None):
    """Return approved source text only when all integrity fields match."""
    env = env if env is not None else os.environ
    version = str(env.get("KHULA_CONSTITUTION_VERSION", "")).strip()
    document = str(env.get("KHULA_CONSTITUTION_DOCUMENT_TEXT", ""))
    expected = str(env.get("KHULA_CONSTITUTION_SHA256", "")).lower()
    if (env.get("KHULA_CONSTITUTION_RATIFIED") == "1"
            and len(document) >= 500 and len(document) <= 50000
            and "draft" not in version.lower()
            and re.fullmatch(r"[A-Za-z0-9._-]{4,64}", version)
            and re.fullmatch(r"[0-9a-f]{64}", expected)
            and hashlib.sha256(document.encode("utf-8")).hexdigest() == expected):
        return {"version": version, "text": document, "sha256": expected}
    return None


def notice_text(env=None):
    status = onboarding_gate_status(env)
    detail = status["details"]
    name = detail["name"] or "[Legal name not yet confirmed]"
    contact = detail["contact_email"] or "[Privacy contact pending]"
    return f"""KHULA COLLECTIVE — PRIVACY NOTICE
Version: {detail['version']}
Responsible party: {name}
Privacy/Information Officer contact: {contact}

1. What Khula processes
Member usernames, contact details, hashed passwords, constitution
acknowledgements, contribution claims, administrator-approved ledger entries,
and records of club-governance decisions. Additional verification documents
are not collected without a separate approved onboarding process.

2. Why this information is used
To authenticate approved club members; administer lawful savings-club
membership and participation; reconcile club payments; keep audited member
records; and communicate member-governance decisions. Khula does not use
financial records for unrelated direct marketing or sell member data.

3. Financial records and bank connections
Club balances and contributions are not treated as verified bank data until
supported by evidence. FNB or another bank may be connected in future only
after formal authorisation, appropriate limited read-only scopes and bank
consent. No user must disclose an online-banking password or PIN to Khula.

4. Hosting and cross-border processing
The current app is hosted on Railway; the attached ledger volume has been
observed in a United States region. The responsible party must document a
lawful POPIA section 72 transfer basis and appropriate contractual and
technical safeguards before processing new real-member data there.

5. Operators and service providers
Railway acts as a hosting operator. Optional data providers (such as a
transactional email service or AI provider) require their own approvals,
operator agreements and access controls before receiving member data.
Khula's educational AI uses aggregate scenarios rather than identity or
raw personal bank statements.

6. Access, retention and deletion
Member data is accessible only to authorised roles as needed. Financial
records may require retention under applicable law and club rules. The
responsible party must adopt a documented schedule for retention, correction,
secure deletion and backup restoration; this version does not promise an
unsupported fixed deletion period.

7. Your rights and queries
Members may ask the responsible party how their personal information is
used, request access/correction, raise an objection where applicable, or
contact the Information Regulator. Direct requests to {contact}.
Provide only information needed for the request; never share banking logins.

8. Security and incidents
Passwords are hashed and ledger updates are role-restricted. The responsible
party remains responsible for periodic risk assessments, backup-and-restore
tests, access reviews and prompt breach-response and notification under
POPIA section 22 where applicable.

9. Club membership
This notice does not replace the separately ratified constitution or any
required financial-services licensing. Invitations are personal and must not
be treated as permission to solicit unrelated services.

For general POPIA information: https://inforegulator.org.za/popia/
"""


def ensure_notice_acknowledgement_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS Member_Privacy_Acknowledgements (
        acknowledgement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        notice_version TEXT NOT NULL,
        notice_sha256 TEXT NOT NULL,
        acknowledged_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES Users(user_id),
        UNIQUE(user_id, notice_version)
    )""")


def record_notice_acknowledgement(conn, user_id, env=None):
    if not onboarding_gate_status(env)["ready"]:
        raise ValueError("Approved onboarding notice is not configured.")
    source = notice_text(env)
    details = organisation_details(env)
    ensure_notice_acknowledgement_table(conn)
    conn.execute(
        "INSERT OR IGNORE INTO Member_Privacy_Acknowledgements "
        "(user_id,notice_version,notice_sha256,acknowledged_at) VALUES (?,?,?,?)",
        (user_id, details["version"], hashlib.sha256(source.encode("utf-8")).hexdigest(),
         datetime.now(timezone.utc).isoformat()),
    )


def render_public_notice():
    import streamlit as st
    status = onboarding_gate_status()
    with st.expander("Privacy notice and how Khula handles your information"):
        if not status["ready"]:
            st.warning(
                "This notice is an operational draft. Real-member registration "
                "is disabled until the responsible party completes its legal review."
            )
        st.text_area(
            "Khula Privacy Notice",
            notice_text(),
            height=320,
            disabled=True,
        )
        st.caption("POPIA review is an ongoing organisational obligation, not a website certificate.")


def render_compliance_status():
    import streamlit as st
    if st.session_state.get("role") != "admin":
        st.error("Administrator access required.")
        return
    st.title("🛡️ Khula POPIA & Financial Services readiness")
    status = onboarding_gate_status()
    if status["ready"]:
        st.success(
            "The required readiness flags are operator-attested. "
            "This does NOT mean an official regulator has certified Khula."
        )
    else:
        st.error("Member onboarding is gated pending required organisation/legal controls.")
        for item in status["missing"]:
            st.write("• " + item)
    st.subheader("Privacy notice preview")
    st.text_area("Notice for members", notice_text(), height=420, disabled=True)
    st.info(
        "Complete the external Information Officer registration, cloud operator "
        "agreements, overseas-transfer assessment, membership rules, bank permissions "
        "and legal licensing evaluation outside this application. Do not upload "
        "identity documents or member bank statements to this checklist."
    )
