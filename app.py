import streamlit as st
import sqlite3
import os
import time
from datetime import datetime

from khula_config import *
from khula_utils import *
# Explicit module routing prevents wildcard re-exports from silently replacing
# the v4 member login with an obsolete v3 implementation.
import khula_pages1 as member_core
import khula_pages2 as identity_pages
import khula_pages3 as club_pages
from khula_security import bootstrap_admin, member_auth_state
from khula_account import render_change_password
from khula_recovery import render_recovery_admin
from khula_sarb import render_sarb_page, render_sarb_panel
from khula_invitations import render_invitation_admin
from khula_compliance import render_compliance_status
from khula_bank_access import render_bank_access_admin
from khula_applications import render_membership_approvals
from khula_compass import render_compass
from khula_mentor_ui import render_mentor
from khula_launch_center import render_launch_center
from khula_member_services import (
    render_admin_reconciliation,
    render_club_goals,
    render_constitution_review,
    render_leaderboard,
    render_communications,
)

st.set_page_config(
    page_title="Khula Collective",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _get_verification_stats():
    """Get ID verification stats for admin sidebar widget."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT verified_status, COUNT(*) FROM ID_Verifications GROUP BY verified_status
        """)
        rows = c.fetchall()
        conn.close()
        stats = {"pending": 0, "verified": 0, "rejected": 0}
        for status, count in rows:
            if status in stats:
                stats[status] = count
        return stats
    except Exception:
        return {"pending": 0, "verified": 0, "rejected": 0}


def render_mobile_nav():
    page = st.session_state.get("nav_page", "dashboard")
    nav_links = [
        ("dashboard", "🏠", "Home"),
        ("fnb_sync", "🏦", "FNB"),
        ("payments", "💰", "Pay"),
        ("features", "✨", "More"),
        ("profile", "👤", "Profile"),
    ]

    links_html = ""
    for key, icon, label in nav_links:
        active_cls = "active" if page == key else ""
        links_html += f'<a href="?nav={key}" class="mobile-nav-item {active_cls}"><span class="icon">{icon}</span>{label}</a>'

    st.markdown(f"""
    <style>
    @media (min-width: 768px) {{
        .mobile-nav {{ display: none !important; }}
    }}
    @media (max-width: 767px) {{
        .mobile-nav {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #1e1e3a;
            border-top: 1px solid #2a2a50;
            padding: 0.5rem 0;
            display: flex;
            justify-content: space-around;
            z-index: 9999;
        }}
        .mobile-nav-item {{
            text-align: center;
            color: #8892b0;
            font-size: 0.65rem;
            text-decoration: none;
            padding: 0.2rem 0.5rem;
        }}
        .mobile-nav-item.active {{ color: #6366f1; }}
        .mobile-nav-item .icon {{ font-size: 1.3rem; display: block; }}
    }}
    </style>
    <div class="mobile-nav">
        {links_html}
    </div>
    """, unsafe_allow_html=True)


def main():
    if os.environ.get("KHULA_PRODUCTION") == "1":
        if os.environ.get("KHULA_DEMO_MODE") == "1":
            st.error("Demo users and holdings are forbidden in production.")
            st.stop()
        mount_root = os.environ.get("KHULA_VOLUME_MOUNT", "/data")
        if (not os.path.isabs(DB_PATH)
                or not os.path.isabs(mount_root)
                or not os.path.ismount(mount_root)
                or os.path.commonpath((os.path.realpath(DB_PATH), os.path.realpath(mount_root))) != os.path.realpath(mount_root)):
            st.error("Production requires KHULA_DB_PATH on a verified persistent volume mount.")
            st.stop()
    init_database()
    bootstrap_admin(DB_PATH)

    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "dashboard"

    # Streamlit's tab-level state is not perpetual authorisation. Refresh
    # server-side role/activation on every rerun and expire idle sessions.
    if st.session_state.authenticated:
        last_seen = st.session_state.get("_last_activity_monotonic")
        now_monotonic = time.monotonic()
        if last_seen is not None and now_monotonic - last_seen > 1800:
            st.session_state.clear()
            st.warning("Your session expired after 30 minutes of inactivity. Please sign in again.")
            st.session_state.authenticated = False
        else:
            uid = st.session_state.get("user_id")
            status = member_auth_state(DB_PATH, uid) if uid is not None else None
            if (not status or status[1] != 1
                    or status[3] != st.session_state.get("_auth_epoch")):
                st.session_state.clear()
                st.session_state.authenticated = False
                st.warning("Account access is inactive. Please contact the club administrator.")
            else:
                st.session_state.role = status[0]
                st.session_state.full_name = status[2]
                st.session_state["_last_activity_monotonic"] = now_monotonic


    # Handle mobile nav query params
    query_params = st.query_params
    if "nav" in query_params and query_params["nav"]:
        st.session_state.nav_page = query_params["nav"]
        st.query_params.clear()

    # load_css renders the stylesheet itself. Passing its None return value
    # to st.markdown printed a literal "None" above the login screen.
    load_css(st.session_state.get("theme", "dark"))

    if st.session_state.authenticated:
        current = member_auth_state(DB_PATH, st.session_state.user_id)
        if current and current[4]:
            render_change_password(force=True)
            return

    if not st.session_state.authenticated:
        # The public landing renders every section in one responsive, native
        # Streamlit column; do not append a full-width expander outside it.
        member_core.render_login()
        return

    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:1rem 0;">
            <div style="font-size:3rem;">🏛️</div>
            <h3 style="color:#6366f1; margin:0;">Khula Collective</h3>
            <p style="color:#8892b0; font-size:0.85rem;">Members · Governance · Savings</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.link_button(
            "📲 Install Khula on your phone",
            "/app/static/install.html",
            use_container_width=True,
        )

        new_theme = st.toggle("🌓 Dark Mode", value=(st.session_state.theme == "dark"))
        if new_theme != (st.session_state.theme == "dark"):
            st.session_state.theme = "dark" if new_theme else "light"
            toggle_theme(st.session_state.user_id, "light" if new_theme else "dark")
            st.rerun()

        st.divider()
        st.markdown("<p style='color:#8892b0; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;'>Menu</p>", unsafe_allow_html=True)

        nav_items = [
            ("dashboard", "🏠 Dashboard"),
            ("fnb_sync", "🏦 FNB Sync"),
            ("payments", "💰 Payments"),
            ("features", "✨ Discover"),
            ("mentor", "🌱 Khula Mentor"),
            ("voice", "🗳️ Member Voice"),
            ("constitution", "📜 Constitution"),
            ("goals", "🎯 Savings Goals"),
            ("economy", "🇿🇦 SA Economic Data"),
            ("leaderboard", "🏆 Hall of Fame"),
            ("directory", "👥 Directory"),
            ("notifications", "🔔 Notifications"),
            ("reports", "📈 Reports"),
            ("ai_advisor", "🤖 AI Advisor"),
            ("global_markets", "🌍 Global Markets"),
            ("whatsapp", "💬 WhatsApp"),
            ("fnb_api_guide", "🏦 FNB API Guide"),
        ]
        if st.session_state.role == "admin":
            nav_items.append(("admin", "👑 Admin Panel"))
            nav_items.append(("membership_approvals", "✅ Membership Approvals"))
            nav_items.append(("launch_center", "🚦 Launch Control"))
            nav_items.append(("reconciliation", "🧾 Reconciliation"))
            nav_items.append(("invites", "✉️ Member Invitations"))
            nav_items.append(("bank_access", "🏦 FNB Bank Access"))
            nav_items.append(("compliance", "🛡️ POPIA Readiness"))
            nav_items.append(("recoveries", "🔑 Account Recovery"))
        nav_items.append(("id_verify", "🆔 ID Verify"))
        nav_items.append(("profile", "👤 Profile"))

        for page_key, label in nav_items:
            if st.button(label, use_container_width=True, key=f"nav_{page_key}",
                        type="primary" if st.session_state.nav_page == page_key else "secondary"):
                st.session_state.nav_page = page_key
                st.rerun()

        st.divider()

        # Admin verification stats widget
        if st.session_state.role == "admin":
            vstats = _get_verification_stats()
            total = vstats["verified"] + vstats["pending"] + vstats["rejected"]
            st.markdown(f"""
            <div style="background:#1e1e3a; border:1px solid #2a2a50; border-radius:8px; padding:0.75rem; margin-bottom:0.75rem;">
                <p style="color:#8892b0; font-size:0.7rem; text-transform:uppercase; letter-spacing:1px; margin:0 0 0.4rem 0;">ID Verification</p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="text-align:center;">
                        <div style="color:#2ed573; font-size:1.1rem; font-weight:bold;">{vstats['verified']}</div>
                        <div style="color:#8892b0; font-size:0.6rem;">Verified</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:#ffa502; font-size:1.1rem; font-weight:bold;">{vstats['pending']}</div>
                        <div style="color:#8892b0; font-size:0.6rem;">Pending</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="color:#ff4757; font-size:1.1rem; font-weight:bold;">{vstats['rejected']}</div>
                        <div style="color:#8892b0; font-size:0.6rem;">Rejected</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        unread = get_unread_count(st.session_state.user_id)
        if unread > 0:
            st.markdown(f"""
            <div style="background:#ff4757; color:white; padding:0.5rem; border-radius:8px; text-align:center;">
                🔴 {unread} unread notification(s)
            </div>
            """, unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    page = st.session_state.nav_page
    if page == "dashboard":
        render_compass()
    elif page == "fnb_sync":
        if os.environ.get("KHULA_ENABLE_PRIVATE_STATEMENT_IMPORT") == "1":
            member_core.render_fnb_sync()
        else:
            st.warning("Private bank-statement import is disabled until storage, retention, privacy consent and reconciliation controls are approved.")
    elif page == "payments":
        member_core.render_payment_progress()
    elif page == "features":
        club_pages.render_feature_discovery()
    elif page == "voice":
        club_pages.render_member_voice()
    elif page == "constitution":
        render_constitution_review()
    elif page == "goals":
        render_club_goals()
    elif page == "leaderboard":
        render_leaderboard()
    elif page == "directory":
        club_pages.render_directory()
    elif page == "notifications":
        club_pages.render_notifications()
    elif page == "reports":
        club_pages.render_reports()
    elif page == "ai_advisor":
        member_core.render_ai_advisor()
    elif page == "mentor":
        render_mentor()
    elif page == "global_markets":
        member_core.render_global_markets()
    elif page == "economy":
        render_sarb_page()
    elif page == "whatsapp":
        render_communications()
    elif page == "fnb_api_guide":
        identity_pages.render_fnb_api_guide()
    elif page == "admin":
        club_pages.render_admin()
    elif page == "membership_approvals":
        render_membership_approvals()
    elif page == "launch_center":
        render_launch_center()
    elif page == "reconciliation":
        render_admin_reconciliation()
    elif page == "invites":
        render_invitation_admin()
    elif page == "bank_access":
        render_bank_access_admin()
    elif page == "compliance":
        render_compliance_status()
    elif page == "recoveries":
        render_recovery_admin()
    elif page == "id_verify":
        if os.environ.get("KHULA_ENABLE_ID_PRECHECK") == "1" and os.environ.get("KHULA_ID_HMAC_KEY"):
            identity_pages.render_id_verification()
        else:
            st.warning("ID image processing is disabled until the privacy review and keyed-digest secret are configured.")
    elif page == "profile":
        club_pages.render_profile()
    else:
        render_compass()

    render_mobile_nav()


if __name__ == "__main__":
    main()
