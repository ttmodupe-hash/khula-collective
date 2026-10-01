from khula_config import *

# ============================================================
# LOGIN
# ============================================================
def render_login():
    st.markdown("""
    <div class='main-header'>
        <div style='font-size:4rem; margin-bottom:1rem;'>📈</div>
        <h1>Khula Collective</h1>
        <p>South African Investment Club Platform</p>
        <p style='color:#00b894; font-size:0.9rem;'>v3.0 · FNB API Ready · Railway Deployed</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            st.markdown("<div style='background:#1e1e30; padding:2rem; border-radius:16px; border:1px solid #2a2a40;'>" , unsafe_allow_html=True)
            tab1, tab2 = st.tabs(["Sign In", "Register"])

            with tab1:
                with st.form("login_form"):
                    username = st.text_input("Username", placeholder="Enter username")
                    password = st.text_input("Password", type="password", placeholder="Enter password")
                    submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                    if submitted:
                        user = authenticate(username, password)
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user[0]
                            st.session_state.username = user[1]
                            st.session_state.full_name = user[2]
                            st.session_state.role = user[3]
                            st.session_state.theme = user[4] if user[4] else "dark"
                            st.rerun()
                        else:
                            st.error("Invalid credentials or account inactive")

            with tab2:
                with st.form("register_form"):
                    new_user = st.text_input("Username")
                    new_pass = st.text_input("Password", type="password")
                    new_name = st.text_input("Full Name")
                    new_email = st.text_input("Email")
                    new_phone = st.text_input("Phone")
                    submitted = st.form_submit_button("Register", use_container_width=True, type="primary")
                    if submitted:
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        try:
                            c.execute("INSERT INTO Users (username, password_hash, full_name, email, phone) VALUES (?, ?, ?, ?, ?)",
                                      (new_user, hash_password(new_pass), new_name, new_email, new_phone))
                            conn.commit()
                            st.success("Account created! Please sign in.")
                        except sqlite3.IntegrityError:
                            st.error("Username already exists")
                        conn.close()
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center; margin-top:2rem; color:#a0a0b0;'>
        <p><strong>Demo Credentials:</strong></p>
        <p>Admin: admin / admin123</p>
        <p>Member: siphoo / password1</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# DASHBOARD
# ============================================================
def render_dashboard():
    track_feature_usage(st.session_state.user_id, "dashboard")
    st.markdown("<div class='main-header'><h1>🏠 Dashboard</h1><p>Your collective wealth overview</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM Users WHERE role='member' AND is_active=1")
    total_members = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE status IN ('verified', 'paid')")
    total_contrib = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(current_value), 0) FROM Investments")
    portfolio = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE status IN ('verified', 'paid') AND user_id=?", (st.session_state.user_id,))
    my_contrib = c.fetchone()[0] or 0

    cols = st.columns(4)
    metrics = [
        ("👥 Members", str(total_members)),
        ("💰 Total Raised", f"R{total_contrib:,.0f}"),
        ("📈 Portfolio", f"R{portfolio:,.0f}"),
        ("🎯 My Contribution", f"R{my_contrib:,.0f}"),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>", unsafe_allow_html=True)

    st.markdown("<h3>📊 Portfolio Breakdown</h3>", unsafe_allow_html=True)
    df_inv = pd.read_sql_query("SELECT name, current_value FROM Investments", conn)
    if not df_inv.empty:
        fig = px.pie(df_inv, values='current_value', names='name', hole=0.4, color_discrete_sequence=px.colors.sequential.Greens)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<h3>🔔 Recent Activity</h3>", unsafe_allow_html=True)
    df_activity = pd.read_sql_query(
        "SELECT u.full_name, mc.amount, mc.payment_date, mc.status FROM Monthly_Contributions mc JOIN Users u ON mc.user_id=u.user_id WHERE mc.status IN ('verified', 'paid') ORDER BY mc.payment_date DESC LIMIT 5", conn)
    if not df_activity.empty:
        st.dataframe(df_activity.rename(columns={'full_name': 'Member', 'amount': 'Amount', 'payment_date': 'Date', 'status': 'Status'}), use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity")

    conn.close()

# ============================================================
# FNB SYNC
# ============================================================
def render_fnb_sync():
    track_feature_usage(st.session_state.user_id, "fnb_sync")
    st.markdown("<div class='main-header'><h1>🏦 FNB Bank Sync</h1><p>Connect your FNB account for automatic tracking</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT bank_account, bank_name FROM Users WHERE user_id=?", (st.session_state.user_id,))
    bank_info = c.fetchone()
    conn.close()

    if FNB_ENABLED:
        st.markdown("""
        <div class='fnb-connect-card'>
            <h3>✅ FNB API Connected</h3>
            <p>Your FNB account is linked and syncing automatically.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: #1e1e30; padding: 1.5rem; border-radius: 16px; border: 1px solid #2a2a40; margin-bottom: 1.5rem;'>
            <h3>🏦 FNB Open Banking</h3>
            <p style='color: #a0a0b0;'>Connect your FNB account to automatically track contributions and sync transactions.</p>
            <p style='color: #ffa502; font-size: 0.9rem;'>⚠️ FNB API credentials not configured. Set FNB_CLIENT_ID and FNB_CLIENT_SECRET environment variables.</p>
        </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Sync Now", use_container_width=True, type="primary"):
            with st.spinner("Syncing with FNB..."):
                time.sleep(2)
                client = FNBAPIClient()
                if bank_info and bank_info[0]:
                    success, msg = client.connect(FNB_CLIENT_ID, FNB_CLIENT_SECRET)
                    if success:
                        transactions = client.get_transactions(bank_info[0])
                        synced = client.sync_contributions(st.session_state.user_id, transactions)
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("INSERT INTO FNB_Sync_Log (user_id, sync_type, status, transactions_synced) VALUES (?, 'manual', 'success', ?)",
                                  (st.session_state.user_id, synced))
                        conn.commit()
                        conn.close()
                        st.success(f"Synced {synced} transactions from FNB!")
                    else:
                        st.warning(msg)
                else:
                    st.warning("No bank account linked. Update your profile first.")

    with col2:
        if st.button("📋 View Transactions", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            df_tx = pd.read_sql_query(
                "SELECT transaction_date, description, amount, type, reference FROM Bank_Transactions WHERE user_id=? ORDER BY transaction_date DESC LIMIT 20",
                conn, params=(st.session_state.user_id,))
            conn.close()
            if not df_tx.empty:
                st.dataframe(df_tx, use_container_width=True, hide_index=True)
            else:
                st.info("No transactions synced yet")

    st.markdown("<h3>📜 Sync History</h3>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df_sync = pd.read_sql_query(
        "SELECT synced_at, sync_type, status, transactions_synced, error_message FROM FNB_Sync_Log WHERE user_id=? ORDER BY synced_at DESC LIMIT 10",
        conn, params=(st.session_state.user_id,))
    conn.close()
    if not df_sync.empty:
        st.dataframe(df_sync, use_container_width=True, hide_index=True)
    else:
        st.info("No sync history")

# ============================================================
# PAYMENT PROGRESS
# ============================================================
def render_payment_progress():
    track_feature_usage(st.session_state.user_id, "payment_tracking")
    st.markdown("<div class='main-header'><h1>💰 Payment Progress</h1><p>Track contributions and identify arrears</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    current_year = datetime.now().year
    current_month = datetime.now().month

    c.execute("SELECT COUNT(*) FROM Users WHERE role='member' AND is_active=1")
    total_members = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM Monthly_Contributions WHERE year=? AND month=? AND status IN ('verified', 'paid')", (current_year, current_month))
    paid_this_month = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM Monthly_Contributions WHERE year=? AND month=? AND status='partial'", (current_year, current_month))
    partial_this_month = c.fetchone()[0]

    cols = st.columns(3)
    with cols[0]:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Paid This Month</div><div class='metric-value'>{paid_this_month}/{total_members}</div></div>", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Partial</div><div class='metric-value'>{partial_this_month}</div></div>", unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Behind</div><div class='metric-value'>{total_members - paid_this_month - partial_this_month}</div></div>", unsafe_allow_html=True)

    st.progress(paid_this_month / total_members if total_members > 0 else 0)

    st.markdown("<h3>👥 Member Payment Status</h3>", unsafe_allow_html=True)
    c.execute("SELECT user_id, full_name, monthly_contribution FROM Users WHERE role='member' AND is_active=1 ORDER BY full_name")
    members = c.fetchall()

    for uid, name, monthly in members:
        c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE user_id=? AND year=? AND month=?", (uid, current_year, current_month))
        paid = c.fetchone()[0] or 0

        if paid >= monthly:
            status_class = "success"
            status_text = "PAID"
            progress = 100
        elif paid > 0:
            status_class = "warning"
            status_text = "PARTIAL"
            progress = int((paid / monthly) * 100)
        else:
            status_class = "danger"
            status_text = "LATE"
            progress = 0

        st.markdown(f"""
        <div class='arrears-card {status_class}'>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong>{name}</strong>
                    <span class='payment-status status-{status_text.lower()}'>{status_text}</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:0.85rem; color:#a0a0b0;">R{paid:,.0f} / R{monthly:,.0f}</span>
                </div>
            </div>
            <div class='progress-container'>
                <div class='progress-bar {status_class}' style='width: {progress}%;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<h3>📈 Monthly Collection Rate</h3>", unsafe_allow_html=True)
    df_monthly = pd.read_sql_query(
        "SELECT month, COUNT(DISTINCT user_id) as paid FROM Monthly_Contributions WHERE year=? AND status IN ('verified', 'paid') GROUP BY month ORDER BY month",
        conn, params=(current_year,))
    if not df_monthly.empty:
        df_monthly['month_name'] = df_monthly['month'].apply(lambda x: MONTHS[int(x)-1])
        fig = px.bar(df_monthly, x='month_name', y='paid', color_discrete_sequence=['#00b894'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#ffffff')
        st.plotly_chart(fig, use_container_width=True)

    conn.close()
