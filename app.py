import streamlit as st
import sqlite3
from datetime import datetime

from khula_config import *
from khula_utils import *
from khula_pages1 import *
from khula_pages2 import *
from khula_pages3 import *

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
    init_database()
    seed_demo_data()

    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "dashboard"

    # Handle mobile nav query params
    query_params = st.query_params
    if "nav" in query_params and query_params["nav"]:
        st.session_state.nav_page = query_params["nav"]
        st.query_params.clear()

    st.markdown(load_css(st.session_state.theme), unsafe_allow_html=True)

    if not st.session_state.authenticated:
        render_login()
        return

    with st.sidebar:
        st.markdown(f"""
        <div style="text-align:center; padding:1rem 0;">
            <div style="font-size:3rem;">🏛️</div>
            <h3 style="color:#6366f1; margin:0;">Khula Collective</h3>
            <p style="color:#8892b0; font-size:0.85rem;">v4.0 · Super Live Model</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

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
            ("voice", "🗳️ Member Voice"),
            ("constitution", "📜 Constitution"),
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
        render_dashboard()
    elif page == "fnb_sync":
        render_fnb_sync()
    elif page == "payments":
        render_payment_progress()
    elif page == "features":
        render_feature_discovery()
    elif page == "voice":
        render_member_voice()
    elif page == "constitution":
        render_constitution()
    elif page == "directory":
        render_directory()
    elif page == "notifications":
        render_notifications()
    elif page == "reports":
        render_reports()
    elif page == "ai_advisor":
        render_ai_advisor()
    elif page == "global_markets":
        render_global_markets()
    elif page == "whatsapp":
        render_whatsapp()
    elif page == "fnb_api_guide":
        render_fnb_api_guide()
    elif page == "admin":
        render_admin()
    elif page == "id_verify":
        render_id_verification()
    elif page == "profile":
        render_profile()
    else:
        render_dashboard()

    render_mobile_nav()


if __name__ == "__main__":
    main()
