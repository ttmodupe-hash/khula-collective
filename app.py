from khula_config import *
from khula_utils import *
from khula_pages1 import *
from khula_pages2 import *
from khula_pages3 import *

# ============================================================
# MOBILE NAVIGATION
# ============================================================
def render_mobile_nav():
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"

    pages = [
        ("dashboard", "🏠", "Home"),
        ("payment_progress", "💰", "Payments"),
        ("member_voice", "🗳️", "Vote"),
        ("feature_discovery", "✨", "Discover"),
        ("profile", "👤", "Profile"),
    ]

    st.markdown("""
    <style>
    .mobile-nav { position: fixed; bottom: 0; left: 0; right: 0; background: #1e1e30; border-top: 1px solid #2a2a40; padding: 0.5rem; z-index: 9999; display: flex; justify-content: space-around; }
    .mobile-nav-item { text-align: center; color: #a0a0b0; text-decoration: none; font-size: 0.75rem; }
    .mobile-nav-item.active { color: #00b894; }
    .mobile-nav-item .icon { font-size: 1.5rem; display: block; }
    </style>
    """, unsafe_allow_html=True)

    nav_html = "<div class='mobile-nav'>"
    for pid, icon, label in pages:
        active = "active" if st.session_state.page == pid else ""
        nav_html += f"<a href='?page={pid}' class='mobile-nav-item {active}'><span class='icon'>{icon}</span>{label}</a>"
    nav_html += "</div>"
    st.markdown(nav_html, unsafe_allow_html=True)

# ============================================================
# MAIN APP
# ============================================================
def main():
    st.set_page_config(
        page_title="Khula Collective",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    init_database()
    seed_demo_data()

    # Session state
    for key in ["logged_in", "user_id", "username", "full_name", "role", "page", "theme"]:
        if key not in st.session_state:
            st.session_state[key] = None if key != "logged_in" else False
    if st.session_state.theme is None:
        st.session_state.theme = "dark"
    if st.session_state.page is None:
        st.session_state.page = "dashboard"

    query_params = st.query_params
    if "page" in query_params:
        st.session_state.page = query_params["page"]

    load_css(st.session_state.theme)

    if not st.session_state.logged_in:
        render_login()
        return

    # Sidebar
    with st.sidebar:
        st.markdown(f"<h3>👤 {st.session_state.full_name}</h3>", unsafe_allow_html=True)
        st.caption(f"Role: {st.session_state.role.title()}")

        menu_items = [
            ("dashboard", "🏠 Dashboard"),
            ("fnb_sync", "🏦 FNB Sync"),
            ("payment_progress", "💰 Payments"),
            ("feature_discovery", "✨ Discover"),
            ("member_voice", "🗳️ Member Voice"),
            ("ai_advisor", "🤖 AI Advisor"),
            ("constitution", "📜 Constitution"),
            ("directory", "👥 Directory"),
            ("notifications", "🔔 Notifications"),
            ("reports", "📈 Reports"),
            ("whatsapp", "💬 WhatsApp"),
            ("profile", "👤 Profile"),
        ]
        if st.session_state.role == "admin":
            menu_items.append(("admin", "👑 Admin"))

        for page_id, label in menu_items:
            if st.button(label, use_container_width=True, key=f"nav_{page_id}"):
                st.session_state.page = page_id
                st.rerun()

        if st.button("🌓 Toggle Theme", use_container_width=True):
            toggle_theme()
            st.rerun()

        if st.button("🚪 Sign Out", use_container_width=True):
            for key in ["logged_in", "user_id", "username", "full_name", "role", "page"]:
                st.session_state[key] = None if key != "logged_in" else False
            st.rerun()

    # Render page
    page = st.session_state.page
    if page == "dashboard":
        render_dashboard()
    elif page == "fnb_sync":
        render_fnb_sync()
    elif page == "payment_progress":
        render_payment_progress()
    elif page == "feature_discovery":
        render_feature_discovery()
    elif page == "member_voice":
        render_member_voice()
    elif page == "ai_advisor":
        render_ai_advisor()
    elif page == "constitution":
        render_constitution()
    elif page == "directory":
        render_directory()
    elif page == "notifications":
        render_notifications()
    elif page == "reports":
        render_reports()
    elif page == "whatsapp":
        render_whatsapp()
    elif page == "profile":
        render_profile()
    elif page == "admin":
        render_admin()
    else:
        render_dashboard()

    render_mobile_nav()

if __name__ == "__main__":
    main()
