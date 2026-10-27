"""Evidence-labelled, privacy-aware home dashboard for Khula club members.

Club cash is sourced only from recorded bank snapshots. It is never derived
by adding member payment claims, investment valuations or projections.
"""
import sqlite3
from datetime import date, datetime, timezone

from khula_advisory_core import bank_snapshot_fresh, zar
from khula_member_services import latest_club_balance


def compass_snapshot(db_path, user_id):
    with sqlite3.connect(db_path) as conn:
        current = conn.execute(
            "SELECT role,is_active,COALESCE(monthly_contribution,0),full_name "
            "FROM Users WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not current or current[1] != 1 or current[0] not in ("member", "admin"):
            raise PermissionError("An approved member account is required.")
        role, _, target, own_name = current
        today = date.today()
        own_paid = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM Monthly_Contributions "
            "WHERE user_id=? AND year=? AND month=? AND status='paid'",
            (user_id, today.year, today.month),
        ).fetchone()[0]
        awaiting_review = conn.execute(
            "SELECT COUNT(*) FROM Payment_Claims "
            "WHERE user_id=? AND status='pending'",
            (user_id,),
        ).fetchone()[0]
        member_count = conn.execute(
            "SELECT COUNT(*) FROM Users WHERE role='member' AND is_active=1"
        ).fetchone()[0]
        proposals = conn.execute(
            "SELECT COUNT(*) FROM Proposals "
            "WHERE status='open' AND (closes_at IS NULL OR closes_at>?)",
            (datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),),
        ).fetchone()[0]
        goal_rows = conn.execute(
            "SELECT name,target_zar,target_date "
            "FROM Savings_Goals ORDER BY goal_id DESC LIMIT 5"
        ).fetchall()
        if role == "admin":
            pending_claims = conn.execute(
                "SELECT COUNT(*) FROM Payment_Claims WHERE status='pending'"
            ).fetchone()[0]
            pending_registrations = 0
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='Membership_Applications'"
            ).fetchone()
            if table:
                pending_registrations = conn.execute(
                    "SELECT COUNT(*) FROM Membership_Applications WHERE status='pending'"
                ).fetchone()[0]
        else:
            pending_claims = None
            pending_registrations = None
    snap = latest_club_balance(db_path=db_path)
    bank_fresh = bool(snap and bank_snapshot_fresh(snap["as_of"]))
    return {
        "role": role,
        "own_name": own_name,
        "member_count": member_count,
        "own_paid_current_month": zar(own_paid),
        "own_contribution_target": zar(target),
        "pending_own_claims": awaiting_review,
        "open_proposals": proposals,
        "goals": [(str(name), zar(target), due) for name,target,due in goal_rows],
        "bank_snapshot": snap,
        "bank_fresh": bank_fresh,
        "planning_cash": snap["available"] if bank_fresh else None,
        "pending_club_claims": pending_claims,
        "pending_registrations": pending_registrations,
    }


def _go(st, name):
    st.session_state.nav_page = name
    st.rerun()


def render_compass():
    import streamlit as st
    from khula_config import DB_PATH

    try:
        data = compass_snapshot(DB_PATH, st.session_state.user_id)
    except PermissionError:
        st.error("An approved club account is required.")
        return
    st.title("🏛️ Khula Compass")
    st.caption(
        "Your private club overview · Figures are sourced from recorded club data. "
        "Khula does not claim bank API access, a live trading account or audited returns."
    )
    st.write(f"Welcome, **{data['own_name']}**. Here's what is known today.")
    cash = data["bank_snapshot"]
    cash_label = (
        f"R{data['planning_cash']:,.2f}" if data["planning_cash"] is not None
        else "Not verified"
    )
    a,b,c,d = st.columns(4)
    with a:
        st.metric(
            "Planning cash after reserves", cash_label,
            help="Only a recent, administrator-attested bank balance less recorded reserves; not independently bank-verified.",
        )
    with b:
        st.metric(
            "Your recorded paid contributions this month",
            f"R{data['own_paid_current_month']:,.2f}",
            help="Ledger entries marked paid; historical entries may still need independent bank reconciliation.",
        )
    with c:
        st.metric("Active club members", data["member_count"])
    with d:
        st.metric("Open member proposals", data["open_proposals"])

    st.divider()
    st.subheader("Where does our cash figure come from?")
    if not cash:
        st.warning(
            "The club has no bank-balance snapshot on record. Available cash "
            "and investment capacity cannot be calculated."
        )
    else:
        st.write("**Origin:** Administrator-attested club-bank statement; not a live FNB API connection.")
        st.write(f"**Statement date:** {cash['as_of']}")
        st.write(f"**Recorded bank balance:** R{cash['cash']:,.2f}")
        st.write(f"**Explicitly recorded reserves:** R{cash['reserved']:,.2f}")
        if data["bank_fresh"]:
            st.info(
                f"**Cash after recorded reserves:** R{cash['available']:,.2f}. "
                "This is provisional planning information, not independently "
                "reconciled investable cash or permission to buy an asset."
            )
        else:
            st.warning(
                "The manual bank snapshot is over 14 days old or invalid; "
                "planning cash is withheld until the treasurer updates the evidence."
            )
    if data["pending_own_claims"]:
        st.info(
            f"You have {data['pending_own_claims']} contribution claim(s) awaiting "
            "administrator reconciliation. Claims do not count as paid contributions."
        )

    st.divider()
    st.subheader("Collective savings goals")
    if data["goals"]:
        for name,target,due in data["goals"]:
            st.write(
                f"**{name}** · Target R{target:,.2f}"
                + (f" · Due {due}" if due else "")
            )
        st.caption(
            "Goal targets are approved planning objectives, not guaranteed "
            "returns. Recorded club cash is not counted separately for each goal."
        )
    else:
        st.info("No savings goals recorded yet. A club administrator can create the first goal.")

    st.subheader("Your next actions")
    first,second,third = st.columns(3)
    with first:
        if st.button("💰 My contributions", use_container_width=True):
            _go(st, "payments")
    with second:
        if st.button("🗳️ Club decisions", use_container_width=True):
            _go(st, "voice")
    with third:
        if st.button("🎯 Club goals", use_container_width=True):
            _go(st, "goals")

    if data["role"] == "admin":
        st.divider()
        st.subheader("Treasurer and membership review")
        x,y = st.columns(2)
        with x:
            st.metric("Pending club payment claims", data["pending_club_claims"])
            if st.button("Open bank reconciliation", use_container_width=True):
                _go(st, "reconciliation")
        with y:
            st.metric("Pending public membership requests", data["pending_registrations"])
            if st.button("Review membership requests", use_container_width=True):
                _go(st, "membership_approvals")
        st.caption(
            "Only an active administrator may access these member-application "
            "and bank-evidence review tools. They are not visible to other members."
        )
