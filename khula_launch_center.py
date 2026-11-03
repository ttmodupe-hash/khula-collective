"""Read-only Khula pilot-readiness diagnostics; does not self-certify compliance.

Security, banking and privacy sign-offs are external obligations. These
checks never expose database contents, credentials, email lists or financial
amounts to an unauthorised session, and cannot enable an approval flag.
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from khula_advisory_core import bank_snapshot_fresh
from khula_compliance import onboarding_gate_status
from khula_member_services import latest_club_balance


def launch_status(db_path, admin_id, *, env=None):
    env = os.environ if env is None else env
    with sqlite3.connect(db_path, timeout=10) as conn:
        admin = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND role='admin' AND is_active=1",
            (admin_id,),
        ).fetchone()
        if not admin:
            raise PermissionError("Active Khula administrator required.")
        rows = {
            "active_members": conn.execute(
                "SELECT COUNT(*) FROM Users WHERE role='member' AND is_active=1"
            ).fetchone()[0],
            "inactive_members": conn.execute(
                "SELECT COUNT(*) FROM Users WHERE role='member' AND is_active=0"
            ).fetchone()[0],
            "pending_claims": conn.execute(
                "SELECT COUNT(*) FROM Payment_Claims WHERE status='pending'"
            ).fetchone()[0],
        }
        existing = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='Membership_Applications'"
            )
        }
        if existing:
            rows["pending_applications"] = conn.execute(
                "SELECT COUNT(*) FROM Membership_Applications "
                "WHERE status='pending'"
            ).fetchone()[0]
            rows["approved_applications"] = conn.execute(
                "SELECT COUNT(*) FROM Membership_Applications "
                "WHERE status='approved'"
            ).fetchone()[0]
            rows["rejected_applications"] = conn.execute(
                "SELECT COUNT(*) FROM Membership_Applications "
                "WHERE status='rejected'"
            ).fetchone()[0]
        else:
            rows.update(
                pending_applications=0, approved_applications=0,
                rejected_applications=0,
            )
        check = conn.execute("PRAGMA quick_check(1)").fetchone()
        database_healthy = bool(check and check[0] == "ok")
    try:
        size = Path(db_path).stat().st_size
    except OSError:
        size = None
    snap = latest_club_balance(db_path=db_path)
    flags = onboarding_gate_status(env)
    production = (
        env.get("KHULA_PRODUCTION") == "1"
        or env.get("RAILWAY_ENVIRONMENT_NAME", "").lower() == "production"
    )
    paused = env.get("KHULA_PUBLIC_REGISTRATION_PAUSED") == "1"
    can_register = (
        env.get("KHULA_DEMO_MODE") != "1"
        and not paused
        and (flags["ready"] or not production)
    )
    return {
        **rows,
        "database_quick_check_ok": database_healthy,
        "database_size_bytes": size,
        "bank_snapshot_exists": snap is not None,
        "bank_snapshot_fresh": bool(
            snap and bank_snapshot_fresh(snap["as_of"])
        ),
        "cash_source": "manual_admin" if snap else "none",
        "registration_open": can_register,
        "production": production,
        "relevant_gate_status": flags,
        "bootstrap_secret_configured": bool(
            env.get("KHULA_BOOTSTRAP_ADMIN_PASSWORD")
        ),
        "bank_api_verified": False,
        "outbound_email_verified": False,
        "restore_test_verified": False,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def render_launch_center():
    import streamlit as st
    from khula_config import DB_PATH

    if st.session_state.get("role") != "admin":
        st.error("Administrator access required.")
        return
    try:
        state = launch_status(DB_PATH, st.session_state.user_id)
    except (PermissionError, sqlite3.Error):
        st.error("Unable to verify the current operational readiness.")
        return

    st.title("🚦 Khula Launch Control")
    st.caption(
        "Current local application data, technical self-checks and outstanding "
        "club approvals. These are NOT a banking or regulatory certificate."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active club members", state["active_members"])
    c2.metric("Inactive applicants", state["inactive_members"])
    c3.metric("Awaiting membership review", state["pending_applications"])
    c4.metric("Pending payment claims", state["pending_claims"])
    st.divider()
    st.subheader("Member registration")
    if state["registration_open"]:
        st.success(
            "The software's configured registration gate is open. "
            "Confirm actual source documents and the operator's authorisation "
            "before sharing the public signup link."
        )
    else:
        st.warning(
            "New real-member registration is closed; already approved "
            "members can still sign in."
        )
    ready = state["relevant_gate_status"]
    if not ready["ready"]:
        st.write("**Outstanding legal/operator confirmations:**")
        for item in ready["missing"]:
            st.write("• " + item)
    else:
        st.caption(
            "Flags are self-attested by the operator. They do not establish "
            "independent regulator approval or bank-account authorisation."
        )
    st.write(
        "Shareable website: https://khula-collective-production.up.railway.app"
    )
    st.caption(
        "Send invitations only to consenting prospective adult members. "
        "A registration request does not grant account access; the club "
        "administrator must approve via Membership Approvals."
    )

    st.subheader("Technical and financial assurance")
    if state["database_quick_check_ok"]:
        st.success("SQLite quick_check returned ok.")
    else:
        st.error("SQLite quick_check failed; pause new financial operations.")
    if state["bank_snapshot_exists"]:
        if state["bank_snapshot_fresh"]:
            st.info(
                "Recent administrator-recorded bank snapshot exists, but the "
                "club's actual FNB API remains unconnected."
            )
        else:
            st.warning(
                "The recorded bank snapshot is stale or not usable for "
                "current cash planning."
            )
    else:
        st.warning("No actual bank snapshot has been recorded yet.")
    st.warning(
        "Disaster-recovery backup and independent restore: NOT VERIFIED from "
        "this application. Configure Railway volume backups and perform a "
        "separate recovery test before processing real financial documents."
    )
    st.write(
        "Railway backup instructions: https://docs.railway.com/volumes/backups"
    )
    if state["bootstrap_secret_configured"]:
        st.warning(
            "A bootstrap administrator password variable remains configured. "
            "Verify the first administrator has changed the password, then "
            "remove the one-time bootstrap secret securely from Railway."
        )

    st.subheader("Next steps")
    st.markdown(
        "1. Confirm the club legal name, privacy contact, registered "
        "Information Officer, actual constitution and overseas-transfer "
        "operator agreement.\n"
        "2. Review new membership applications only after independent "
        "verification of the applicant.\n"
        "3. Test the backup/restore process and strengthen edge bot "
        "controls before broad public signup.\n"
        "4. Ask FNB for authorised read-only Transaction History API access; "
        "do not enable customer payments or regulated investment advice here."
    )
    st.caption(
        "The app does not enable missing approvals, generate fake bank "
        "balances, request passwords, or send member messages."
    )
