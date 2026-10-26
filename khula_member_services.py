"""Reintroduced member services from the original Khula project.

Stokvel constitution acknowledgements, payment claims, admin audit,
bank-snapshot reconciliation and collective savings goals. Nothing executes
a bank transfer, sends a WhatsApp message, or imports the old seeded DB.
"""
import hashlib
import os
import re
import sqlite3
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from khula_advisory_core import zar, available_savings
from khula_config import DB_PATH


CONSTITUTION_VERSION = "draft-2026-10"
CONSTITUTION_TEXT = """KHULA COLLECTIVE — DRAFT CONSTITUTION FOR MEMBER REVIEW

1. Purpose: Pool agreed contributions for transparent collective saving,
   financial education and investments approved by members.
2. Membership: Members join by invitation. Identity and address checks
   are reviewed separately; ID format validation is not proof of identity.
3. Contributions: The amount and due date are set by the club committee
   and confirmed with members before enforcement.
4. Governance: Investment proposals require a recorded member vote and
   committee review before any action; a software vote alone does not
   authorise payment or a trade.
5. Records: Contributions count as paid only after evidence is reviewed.
   Personal bank statement imports do not confirm club deposits.
6. Custody: Club cash must be reconciled with the actual club bank account.
   Financial statements and access permissions must be reviewed regularly.
7. Exits and disputes: Withdrawal rules and dispute resolutions must be
   ratified by the collective before implementation.

This is a working draft, NOT a final legally approved constitution.
Acknowledgement means the member received this version for review.
"""


def _admin(conn, user_id):
    row = conn.execute(
        "SELECT role, is_active FROM Users WHERE user_id=?", (user_id,)
    ).fetchone()
    return bool(row and row[0] == "admin" and row[1] == 1)


def _audit(conn, admin_id, action, details):
    conn.execute(
        "INSERT INTO Admin_Actions (admin_user_id,action_type,details) VALUES (?,?,?)",
        (admin_id, action, str(details)[:300]),
    )


def submit_payment_claim(user_id, year, month, amount, method, reference, db_path=DB_PATH):
    """A claim is NOT a payment; no ledger entry is posted at this stage."""
    amount = zar(amount)
    reference = str(reference).strip()
    if amount <= 0 or amount > 10000000:
        raise ValueError("Enter a positive amount no more than R10 million.")
    if method not in ("EFT", "Cash", "Other"):
        raise ValueError("Unsupported payment method.")
    if not (3 <= len(reference) <= 80) or any(c in reference for c in "<>\n\r"):
        raise ValueError("Enter the bank or receipt reference (3–80 characters).")
    if not 2020 <= int(year) <= 2100 or not 1 <= int(month) <= 12:
        raise ValueError("Invalid contribution period.")
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT role,is_active FROM Users WHERE user_id=?", (user_id,)).fetchone()
        if not row or row[0] != "member" or not row[1]:
            raise PermissionError("Active member account required.")
        existing = conn.execute(
            "SELECT 1 FROM Payment_Claims WHERE user_id=? AND year=? AND month=? AND payment_reference=? AND status IN ('pending','approved')",
            (user_id, year, month, reference),
        ).fetchone()
        if existing:
            raise ValueError("This payment reference was already submitted.")
        cursor = conn.execute(
            "INSERT INTO Payment_Claims (user_id,year,month,amount_zar,method,payment_reference) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, year, month, float(amount), method, reference),
        )
        return cursor.lastrowid


def review_payment_claim(admin_id, claim_id, approve, evidence_checked, db_path=DB_PATH):
    if approve and not evidence_checked:
        raise ValueError("Check the actual bank statement/receipt before approving.")
    with sqlite3.connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not _admin(conn, admin_id):
            raise PermissionError("Admin only.")
        claim = conn.execute(
            "SELECT user_id,year,month,amount_zar,method,payment_reference,status "
            "FROM Payment_Claims WHERE claim_id=?",
            (claim_id,),
        ).fetchone()
        if not claim or claim[6] != "pending":
            raise ValueError("Claim already reviewed or not found.")
        member_id, year, month, amount, method, reference, _ = claim
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE Payment_Claims SET status=?,reviewed_by=?,reviewed_at=? WHERE claim_id=? AND status='pending'",
            ("approved" if approve else "rejected", admin_id, now, claim_id),
        )
        if approve:
            conn.execute(
                "INSERT INTO Monthly_Contributions "
                "(user_id,year,month,amount,status,payment_date,payment_method,reference) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (member_id, year, month, amount, "paid", now, method, reference),
            )
        _audit(conn, admin_id, "payment_claim_review", f"claim={claim_id}; approved={approve}")
    return True


def save_club_balance(admin_id, balance, reserve, statement_date, reference, db_path=DB_PATH):
    """Admin-attested manual snapshot. NOT a live bank feed."""
    balance, reserve = zar(balance), zar(reserve)
    if balance < 0 or reserve < 0 or balance > 10000000000 or reserve > 10000000000:
        raise ValueError("Invalid balance/reserve.")
    reference = str(reference).strip()
    if len(reference) < 4 or len(reference) > 100:
        raise ValueError("Enter a statement reference (avoid account numbers).")
    try:
        when = date.fromisoformat(str(statement_date))
    except ValueError as exc:
        raise ValueError("Enter a valid statement date.") from exc
    if when > date.today():
        raise ValueError("Bank statement date cannot be in the future.")
    with sqlite3.connect(db_path) as conn:
        if not _admin(conn, admin_id):
            raise PermissionError("Admin only.")
        cursor = conn.execute(
            "INSERT INTO Club_Balance_Snapshots "
            "(balance_zar,reserved_zar,statement_date,reference,source,attested_by) "
            "VALUES (?,?,?,?,'manual_admin',?)",
            (float(balance), float(reserve), when.isoformat(), reference, admin_id),
        )
        _audit(conn, admin_id, "club_balance_attested", f"snapshot={cursor.lastrowid}; as_of={when}")
    return cursor.lastrowid


def latest_club_balance(db_path=DB_PATH):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT snapshot_id,balance_zar,reserved_zar,statement_date,source,created_at "
            "FROM Club_Balance_Snapshots ORDER BY snapshot_id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return {
        "snapshot_id": row[0],
        "cash": zar(row[1]),
        "reserved": zar(row[2]),
        "as_of": row[3],
        "source": row[4],
        "recorded_at": row[5],
        "available": available_savings(row[1], row[2]),
        "is_live_bank_data": False,
    }


def acknowledgement_status(user_id, db_path=DB_PATH):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT signed_at FROM Constitution_Signatures WHERE user_id=? AND constitution_version=?",
            (user_id, CONSTITUTION_VERSION),
        ).fetchone()
    return row[0] if row else None


def acknowledge_constitution(user_id, db_path=DB_PATH):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT full_name FROM Users WHERE user_id=? AND is_active=1",
            (user_id,),
        ).fetchone()
        if not row:
            raise PermissionError("Active member required.")
        conn.execute(
            "INSERT OR IGNORE INTO Constitution_Signatures "
            "(user_id,constitution_version,document_sha256,full_name_at_signature) VALUES (?,?,?,?)",
            (user_id, CONSTITUTION_VERSION,
             hashlib.sha256(CONSTITUTION_TEXT.encode("utf-8")).hexdigest(), row[0]),
        )
    return True


def create_goal(admin_id, name, target, due_date, db_path=DB_PATH):
    name = str(name).strip()
    target = zar(target)
    if len(name) < 4 or len(name) > 120 or target <= 0:
        raise ValueError("Enter a name and positive target.")
    if due_date:
        try:
            date.fromisoformat(str(due_date))
        except ValueError as exc:
            raise ValueError("Invalid target date.") from exc
    with sqlite3.connect(db_path) as conn:
        if not _admin(conn, admin_id):
            raise PermissionError("Admin only.")
        cursor = conn.execute(
            "INSERT INTO Savings_Goals (name,target_zar,target_date,created_by) VALUES (?,?,?,?)",
            (name, float(target), str(due_date) if due_date else None, admin_id),
        )
        _audit(conn, admin_id, "savings_goal_created", f"goal={cursor.lastrowid}")
    return cursor.lastrowid


def set_member_contribution_target(admin_id, member_id, target, db_path=DB_PATH):
    """Governance-controlled monthly target; members cannot change this."""
    amount = zar(target)
    if amount < 0 or amount > 1000000:
        raise ValueError("Choose a monthly target between R0 and R1 million.")
    with sqlite3.connect(db_path) as conn:
        if not _admin(conn, admin_id):
            raise PermissionError("Admin only.")
        row = conn.execute(
            "SELECT user_id FROM Users WHERE user_id=? AND role='member' AND is_active=1",
            (member_id,),
        ).fetchone()
        if not row:
            raise ValueError("Active member not found.")
        conn.execute(
            "UPDATE Users SET monthly_contribution=? WHERE user_id=?",
            (float(amount), member_id),
        )
        _audit(conn, admin_id, "contribution_target_changed",
               f"member={member_id}; target_zar={amount}")
    return True


def render_constitution_review():
    import streamlit as st
    user_id = st.session_state.user_id
    st.title("📜 Khula Constitution & Member Governance")
    st.info("Reintroduced from the original Khula app. This is a draft for member review, not an executed legal agreement.")
    st.text_area("Version " + CONSTITUTION_VERSION, CONSTITUTION_TEXT, height=360, disabled=True)
    st.download_button("Download draft text", CONSTITUTION_TEXT, file_name="khula_constitution_draft.txt", mime="text/plain")
    when = acknowledgement_status(user_id)
    if when:
        st.success(f"You acknowledged receiving this version on {when}.")
    else:
        agreed = st.checkbox("I have read this draft and acknowledge receipt for review.")
        if st.button("Record acknowledgement", disabled=not agreed):
            acknowledge_constitution(user_id)
            st.success("Acknowledgement recorded.")
            st.rerun()


def render_club_goals():
    import streamlit as st
    st.title("🎯 Collective Savings Goals")
    snap = latest_club_balance()
    if not snap:
        st.warning("No admin-attested club bank balance yet. Target progress cannot be calculated reliably.")
    else:
        st.caption("Based on a MANUAL administrator-attested bank snapshot as of " + snap["as_of"])
    with sqlite3.connect(DB_PATH) as conn:
        goals = conn.execute(
            "SELECT name,target_zar,target_date FROM Savings_Goals ORDER BY goal_id DESC"
        ).fetchall()
    for name, target, due in goals:
        st.subheader(name)
        if due:
            st.caption("Target date: " + due)
        if snap:
            achieved = min(1.0, float(snap["cash"]) / target) if target > 0 else 0
            st.progress(achieved)
            st.write(f"R{snap['cash']:,.2f} of R{target:,.2f} (club cash, not investment NAV)")
        else:
            st.write(f"Target R{target:,.2f}")
    if st.session_state.role == "admin":
        with st.expander("Create a goal"):
            with st.form("new_savings_goal"):
                name = st.text_input("Goal name")
                amount = st.number_input("Target (ZAR)", min_value=1.0, step=500.0)
                due = st.date_input("Target date", value=None)
                if st.form_submit_button("Save goal"):
                    try:
                        create_goal(st.session_state.user_id, name, amount, due.isoformat() if due else None)
                        st.success("Goal saved.")
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))


def render_admin_reconciliation():
    import streamlit as st
    if st.session_state.role != "admin":
        st.error("Admin only.")
        return
    st.title("🏦 Reconciliation & Payment Review")
    st.warning("Manual administrator evidence only. This does NOT authenticate against FNB or any other bank.")
    last = latest_club_balance()
    if last:
        st.metric("Last recorded club cash", f"R{last['cash']:,.2f}")
        st.caption("As of " + last["as_of"] + "; manually attested, not live bank verified")
        st.write(f"Less reserved: R{last['reserved']:,.2f}; scenario available: R{last['available']:,.2f}")
    with st.form("bank_balance_attestation"):
        balance = st.number_input("Club bank balance (ZAR)", min_value=0.0, step=100.0)
        reserve = st.number_input("Committed/reserved amount (ZAR)", min_value=0.0, step=100.0)
        statement_date = st.date_input("Actual bank statement date", max_value=date.today())
        reference = st.text_input("Statement/ledger reference (not an account number)")
        checked = st.checkbox("I reviewed the club's actual bank record and understand this is a manual attestation.")
        if st.form_submit_button("Record snapshot"):
            if not checked:
                st.error("Bank evidence review must be attested.")
            else:
                try:
                    save_club_balance(st.session_state.user_id, balance, reserve, statement_date.isoformat(), reference)
                    st.success("Manual bank snapshot saved and audit-logged.")
                    st.rerun()
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))

    with st.expander("Set member contribution targets (R300/R500 policy must be ratified)"):
        st.caption("The earlier Khula build used R300/month; v4 used R500. Confirm the club decision before setting targets.")
        with sqlite3.connect(DB_PATH) as conn:
            members = conn.execute(
                "SELECT user_id,full_name,COALESCE(monthly_contribution,0) "
                "FROM Users WHERE is_active=1 AND role='member' ORDER BY full_name"
            ).fetchall()
        for member_id, full_name, target in members:
            left, mid, right = st.columns([2, 2, 1])
            with left:
                st.write(full_name)
            with mid:
                new_target = st.number_input(
                    "Monthly ZAR target", min_value=0.0, max_value=1000000.0,
                    value=float(target), step=50.0, key=f"target_{member_id}"
                )
            with right:
                if st.button("Save", key=f"save_target_{member_id}"):
                    try:
                        set_member_contribution_target(st.session_state.user_id, member_id, new_target)
                        st.success("Target recorded in audit log.")
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))

    st.subheader("Pending member payment claims")
    with sqlite3.connect(DB_PATH) as conn:
        pending = conn.execute(
            "SELECT pc.claim_id,u.full_name,pc.year,pc.month,pc.amount_zar,pc.method,pc.payment_reference "
            "FROM Payment_Claims pc JOIN Users u ON u.user_id=pc.user_id "
            "WHERE pc.status='pending' ORDER BY pc.claim_id ASC LIMIT 40"
        ).fetchall()
    if not pending:
        st.info("No pending claims.")
    for cid, member, year, month, amount, method, ref in pending:
        with st.expander(f"Claim #{cid} — {member}: R{amount:,.2f} ({month}/{year})"):
            st.write(f"Method: {method}; reference: {ref}")
            checked = st.checkbox("I checked the actual bank statement or receipt", key=f"proof_{cid}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Approve and post contribution", disabled=not checked, key=f"approve_{cid}"):
                    try:
                        review_payment_claim(st.session_state.user_id, cid, True, checked)
                        st.success("Contribution posted.")
                        st.rerun()
                    except (ValueError, PermissionError) as exc:
                        st.error(str(exc))
            with c2:
                if st.button("Reject claim", key=f"reject_{cid}"):
                    review_payment_claim(st.session_state.user_id, cid, False, False)
                    st.warning("Claim rejected.")
                    st.rerun()
    st.subheader("Recent administration audit")
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT action_type,details,created_at FROM Admin_Actions ORDER BY action_id DESC LIMIT 20"
        ).fetchall()
    if rows:
        st.dataframe([{"action": a, "details": d, "at": t} for a, d, t in rows], use_container_width=True)


def render_communications():
    import streamlit as st
    st.title("💬 Member Communications")
    st.info("Original WhatsApp capabilities preserved in the migration roadmap. No automated messages are sent without configured consent and an approved provider.")
    link = os.environ.get("KHULA_WHATSAPP_GROUP_LINK", "").strip()
    parsed = urlparse(link)
    if parsed.scheme == "https" and parsed.hostname == "chat.whatsapp.com":
        st.link_button("Open members' WhatsApp group", link)
    else:
        st.caption("No official WhatsApp group link configured. Ask the administrator for the verified group invitation.")
