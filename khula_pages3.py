from khula_config import *

# ============================================================
# NOTIFICATIONS
# ============================================================
def render_notifications():
    track_feature_usage(st.session_state.user_id, "notifications")
    st.markdown("<div class='main-header'><h1>🔔 Notifications</h1><p>Stay updated with club activity</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    rows = get_notifications(st.session_state.user_id, 50)
    conn.close()

    if rows:
        for nid, title, message, ntype, is_read, created_at in rows:
            unread_class = "notification-unread" if not is_read else ""
            st.markdown(f"""
            <div class='notification-item {unread_class}'>
                <div style="display:flex; justify-content:space-between;">
                    <strong>{title}</strong>
                    <span style="color:#a0a0b0; font-size:0.8rem;">{created_at}</span>
                </div>
                <p style="margin:0.5rem 0 0 0; color:#a0a0b0;">{message}</p>
            </div>
            """, unsafe_allow_html=True)
            if not is_read:
                if st.button("Mark Read", key=f"read_{nid}"):
                    mark_notification_read(nid)
                    st.rerun()
    else:
        st.info("No notifications")

# ============================================================
# REPORTS
# ============================================================
def render_reports():
    track_feature_usage(st.session_state.user_id, "reports")
    st.markdown("<div class='main-header'><h1>📈 Reports</h1><p>Detailed analytics and exportable reports</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    st.markdown("<h3>💰 Contribution Summary</h3>", unsafe_allow_html=True)
    df_contrib = pd.read_sql_query(
        "SELECT u.full_name, SUM(mc.amount) as total FROM Monthly_Contributions mc JOIN Users u ON mc.user_id=u.user_id WHERE mc.status IN ('verified','paid') GROUP BY mc.user_id ORDER BY total DESC",
        conn)
    if not df_contrib.empty:
        st.dataframe(df_contrib.rename(columns={'full_name': 'Member', 'total': 'Total Contributed'}), use_container_width=True, hide_index=True)

    st.markdown("<h3>📊 Investment Performance</h3>", unsafe_allow_html=True)
    df_inv = pd.read_sql_query("SELECT name, amount_invested, current_value FROM Investments", conn)
    if not df_inv.empty:
        df_inv['return_pct'] = ((df_inv['current_value'] - df_inv['amount_invested']) / df_inv['amount_invested'] * 100).round(2)
        st.dataframe(df_inv.rename(columns={'name': 'Investment', 'amount_invested': 'Invested', 'current_value': 'Current Value', 'return_pct': 'Return %'}), use_container_width=True, hide_index=True)

    st.markdown("<h3>📥 Export Data</h3>", unsafe_allow_html=True)
    if st.button("Export Contributions to CSV"):
        df = pd.read_sql_query("SELECT * FROM Monthly_Contributions", conn)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "contributions.csv", "text/csv")

    conn.close()

# ============================================================
# WHATSAPP
# ============================================================
def render_whatsapp():
    track_feature_usage(st.session_state.user_id, "whatsapp")
    st.markdown("<div class='main-header'><h1>💬 WhatsApp</h1><p>Group integration and sharing</p></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#1e1e30;padding:2rem;border-radius:16px;border:1px solid #2a2a40;text-align:center;'>
        <div style='font-size:4rem;margin-bottom:1rem;'>💬</div>
        <h3>WhatsApp Group Integration</h3>
        <p style='color:#a0a0b0;'>Connect your WhatsApp group for automated updates.</p>
        <p style='color:#a0a0b0;'>Share payment reminders, vote notifications, and reports directly to your group chat.</p>
    </div>
    """, unsafe_allow_html=True)

    group_link = st.text_input("WhatsApp Group Link", placeholder="https://chat.whatsapp.com/...")
    if st.button("Connect Group", type="primary"):
        st.success("WhatsApp group connected! (Simulated)")

# ============================================================
# PROFILE
# ============================================================
def render_profile():
    track_feature_usage(st.session_state.user_id, "profile")
    st.markdown("<div class='main-header'><h1>👤 Profile</h1><p>Manage your account and preferences</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT full_name, email, phone, bank_account, bank_name, monthly_contribution, theme_preference, fica_status FROM Users WHERE user_id=?", (st.session_state.user_id,))
    user = c.fetchone()

    if user:
        full_name, email, phone, bank_account, bank_name, monthly, theme, fica = user
        with st.form("profile_form"):
            new_name = st.text_input("Full Name", value=full_name)
            new_email = st.text_input("Email", value=email)
            new_phone = st.text_input("Phone", value=phone)
            new_bank = st.text_input("Bank Account", value=bank_account or "")
            new_bank_name = st.text_input("Bank Name", value=bank_name or "")
            new_monthly = st.number_input("Monthly Contribution", value=float(monthly or 500), step=50.0)
            new_theme = st.selectbox("Theme", ["dark", "light"], index=0 if theme == "dark" else 1)
            submitted = st.form_submit_button("Save Changes", type="primary")
            if submitted:
                c.execute("UPDATE Users SET full_name=?, email=?, phone=?, bank_account=?, bank_name=?, monthly_contribution=?, theme_preference=? WHERE user_id=?",
                          (new_name, new_email, new_phone, new_bank, new_bank_name, new_monthly, new_theme, st.session_state.user_id))
                conn.commit()
                st.session_state.theme = new_theme
                st.success("Profile updated!")

        st.markdown(f"<p>FICA Status: <strong>{fica.upper()}</strong></p>", unsafe_allow_html=True)

    conn.close()

# ============================================================
# ADMIN
# ============================================================
def render_admin():
    track_feature_usage(st.session_state.user_id, "admin")
    if st.session_state.role != "admin":
        st.error("Admin access only")
        return

    st.markdown("<div class='main-header'><h1>👑 Admin Panel</h1><p>Manage members, announcements, and settings</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    tab1, tab2, tab3 = st.tabs(["Members", "Announcements", "Analytics"])

    with tab1:
        st.markdown("<h3>👥 Manage Members</h3>", unsafe_allow_html=True)
        c.execute("SELECT user_id, full_name, email, role, fica_status, is_active FROM Users")
        members = c.fetchall()
        for uid, name, email, role, fica, active in members:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.write(f"**{name}** ({email})")
            with col2:
                st.write(f"Role: {role}")
            with col3:
                st.write(f"FICA: {fica}")
            with col4:
                if st.button("Toggle" if active else "Activate", key=f"toggle_{uid}"):
                    c.execute("UPDATE Users SET is_active=? WHERE user_id=?", (0 if active else 1, uid))
                    conn.commit()
                    st.rerun()

    with tab2:
        st.markdown("<h3>📢 New Announcement</h3>", unsafe_allow_html=True)
        with st.form("announcement_form"):
            title = st.text_input("Title")
            content = st.text_area("Content")
            priority = st.selectbox("Priority", ["normal", "high", "urgent"])
            submitted = st.form_submit_button("Post", type="primary")
            if submitted:
                c.execute("INSERT INTO Announcements (title, content, posted_by, priority) VALUES (?,?,?,?)",
                          (title, content, st.session_state.user_id, priority))
                conn.commit()
                st.success("Announcement posted!")

    with tab3:
        st.markdown("<h3>📊 Feature Usage Analytics</h3>", unsafe_allow_html=True)
        stats = get_feature_usage_stats()
        if stats:
            df = pd.DataFrame(stats, columns=["Feature", "Unique Users", "Total Uses"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No usage data yet")

    conn.close()
