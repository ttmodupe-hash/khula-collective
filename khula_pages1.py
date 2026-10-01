from khula_config import *
from khula_utils import *

from khula_ai_engine import fetch_all_market_data, get_balance_aware_recommendations, save_market_prices_to_db, generate_ai_reasoning, get_global_market_summary, save_recommendations_to_db

# ============================================================
def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='main-header'><h1>📈 Khula Collective</h1><p>Empowering South African stokvels and investment clubs</p></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#00b894;font-weight:600;'>v3.1 - Now with Statement Upload & AI Advisor</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("🔓 Login", use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password")
                    return
                user = authenticate(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.session_state.full_name = user[2]
                    st.session_state.role = user[3]
                    st.session_state.theme = user[4] or "dark"
                    st.session_state.nav_page = "dashboard"
                    st.success(f"Welcome back, {user[2]}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("Demo Credentials"):
            st.code("Admin: admin / admin123\nMember: siphoo / password1")
        st.markdown("<p style='text-align:center;color:#a0a0b0;font-size:0.85rem;'>Powered by FNB Open Banking API</p>", unsafe_allow_html=True)

def render_dashboard():
    track_feature_usage(st.session_state.user_id, "dashboard")
    st.markdown("<div class='main-header'><h1>🏠 Dashboard</h1><p>Your collective at a glance</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Total contributions
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE status IN ('verified', 'paid')")
    total_contrib = c.fetchone()[0] or 0

    # Total investments
    c.execute("SELECT COALESCE(SUM(current_value), 0) FROM Investments")
    total_invested = c.fetchone()[0] or 0

    # Members count
    c.execute("SELECT COUNT(*) FROM Users WHERE role='member' AND is_active=1")
    member_count = c.fetchone()[0]

    # Active proposals
    c.execute("SELECT COUNT(*) FROM Suggestions WHERE status='open'")
    active_proposals = c.fetchone()[0]

    # Total growth
    c.execute("SELECT COALESCE(SUM(amount_invested), 0) FROM Investments")
    total_invested_cost = c.fetchone()[0] or 0
    growth = ((total_invested - total_invested_cost) / total_invested_cost * 100) if total_invested_cost > 0 else 0

    # Recent arrears count
    c.execute("""SELECT COUNT(DISTINCT user_id) FROM Monthly_Contributions 
                  WHERE status IN ('pending', 'partial') AND year=? AND month=?""", 
              (datetime.now().year, datetime.now().month))
    arrears_count = c.fetchone()[0]

    conn.close()

    # Metrics
    cols = st.columns(5)
    metrics = [
        ("💰 Total Contributions", f"R{total_contrib:,.0f}"),
        ("📈 Portfolio Value", f"R{total_invested:,.0f}"),
        ("👥 Members", str(member_count)),
        ("📊 Active Proposals", str(active_proposals)),
        ("📈 Growth", f"{growth:.1f}%"),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>", unsafe_allow_html=True)

    # Arrears alert for admin
    if st.session_state.role == "admin" and arrears_count > 0:
        st.markdown(f"""
        <div style="background: #ff475720; border: 1px solid #ff4757; padding: 1rem; border-radius: 12px; margin: 1rem 0;">
            <strong>⚠️ Arrears Alert:</strong> {arrears_count} member(s) have pending or partial payments this month.
            <a href="#" style="color:#ff4757;">View Payment Progress</a>
        </div>
        """, unsafe_allow_html=True)

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h3 style='margin-bottom:1rem;'>💵 Monthly Contributions</h3>", unsafe_allow_html=True)
        conn = sqlite3.connect(DB_PATH)
        df_contrib = pd.read_sql_query(
            "SELECT year, month, SUM(amount) as total FROM Monthly_Contributions WHERE status IN ('verified', 'paid') GROUP BY year, month ORDER BY year, month", conn)
        conn.close()
        if not df_contrib.empty:
            df_contrib['label'] = df_contrib.apply(lambda x: f"{MONTHS[int(x['month'])-1]} {int(x['year'])}", axis=1)
            fig = px.bar(df_contrib, x='label', y='total', color_discrete_sequence=['#00b894'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', showlegend=False)
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No contribution data available")

    with col2:
        st.markdown("<h3 style='margin-bottom:1rem;'>📊 Investment Portfolio</h3>", unsafe_allow_html=True)
        conn = sqlite3.connect(DB_PATH)
        df_inv = pd.read_sql_query("SELECT name, current_value FROM Investments", conn)
        conn.close()
        if not df_inv.empty:
            fig = px.pie(df_inv, names='name', values='current_value', hole=0.4, color_discrete_sequence=['#00b894', '#00cec9', '#0984e3', '#6c5ce7', '#fdcb6e'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff', showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No investment data available")

    # Investment table
    st.markdown("<h3 style='margin-top:1.5rem;'>📈 Holdings</h3>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df_holdings = pd.read_sql_query(
        "SELECT name, investment_type, amount_invested, current_value, (current_value - amount_invested) as gain FROM Investments", conn)
    conn.close()
    if not df_holdings.empty:
        df_holdings['ROI'] = ((df_holdings['current_value'] - df_holdings['amount_invested']) / df_holdings['amount_invested'] * 100).round(1)
        st.dataframe(df_holdings, use_container_width=True, hide_index=True)

    # Participation heatmap
    st.markdown("<h3 style='margin-top:1.5rem;'>🔥 Participation Heatmap</h3>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df_heat = pd.read_sql_query(
        "SELECT u.full_name, mc.year, mc.month, mc.amount FROM Monthly_Contributions mc JOIN Users u ON mc.user_id=u.user_id WHERE mc.status IN ('verified', 'paid')", conn)
    conn.close()
    if not df_heat.empty:
        pivot = df_heat.pivot_table(index='full_name', columns='month', values='amount', aggfunc='sum').fillna(0)
        fig = px.imshow(pivot, color_continuous_scale='YlGn', aspect='auto')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#ffffff')
        st.plotly_chart(fig, use_container_width=True)

def render_fnb_sync():
    track_feature_usage(st.session_state.user_id, "fnb_sync")
    st.markdown("<div class='main-header'><h1>🏦 FNB Bank Sync</h1><p>Connect your FNB account for automatic contribution tracking</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT bank_account, bank_name FROM Users WHERE user_id=?", (st.session_state.user_id,))
    bank_info = c.fetchone()
    conn.close()

    # Connection status
    if bank_info and bank_info[0] and bank_info[1] == "FNB":
        st.markdown(f"""
        <div class='fnb-connect-card'>
            <h3>✅ Connected to FNB</h3>
            <p>Account ending in {bank_info[0][-4:]} is linked. Transactions are syncing automatically.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Sync Now", use_container_width=True, type="primary"):
                with st.spinner("Syncing with FNB..."):
                    time.sleep(2)
                    # Simulate sync
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("INSERT INTO FNB_Sync_Log (user_id, sync_type, status, transactions_synced) VALUES (?, 'full', 'success', ?)",
                              (st.session_state.user_id, random.randint(3, 8)))
                    conn.commit()
                    conn.close()
                    st.success("Sync completed! 5 transactions imported.")
        with col2:
            if st.button("🔌 Disconnect", use_container_width=True, type="secondary"):
                st.warning("Disconnect functionality coming in v3.1")

        # Sync history
        st.markdown("<h3>📋 Recent Sync History</h3>", unsafe_allow_html=True)
        conn = sqlite3.connect(DB_PATH)
        df_sync = pd.read_sql_query(
            "SELECT synced_at, sync_type, status, transactions_synced, error_message FROM FNB_Sync_Log WHERE user_id=? ORDER BY synced_at DESC LIMIT 10",
            conn, params=(st.session_state.user_id,))
        conn.close()
        if not df_sync.empty:
            st.dataframe(df_sync, use_container_width=True, hide_index=True)
        else:
            st.info("No sync history yet")

        # Simulated transactions
        st.markdown("<h3>💳 Recent Bank Transactions</h3>", unsafe_allow_html=True)
        client = FNBAPIClient()
        client.connect()
        result = client.get_transactions(bank_info[0])
        if result["success"]:
            df_txns = pd.DataFrame(result["transactions"])
            st.dataframe(df_txns[["date", "description", "amount", "reference", "status"]], use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div style="background: #1e1e30; padding: 2rem; border-radius: 16px; text-align: center; border: 1px dashed #2a2a40;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🏦</div>
            <h3>Connect Your FNB Account</h3>
            <p style="color: #a0a0b0;">Link your FNB account to automatically track contributions, detect payments, and sync balances.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("fnb_link"):
            st.text_input("FNB Account Number", placeholder="Enter your FNB account number")
            st.text_input("Branch Code", value="250312")
            st.checkbox("I authorize Khula Collective to read my transaction history for contribution tracking")
            submitted = st.form_submit_button("🔗 Link FNB Account", use_container_width=True, type="primary")
            if submitted:
                with st.spinner("Connecting to FNB..."):
                    time.sleep(2)
                    st.success("Account linked successfully! (Simulation mode)")
                    st.balloons()

    # ============================================================
    # STATEMENT UPLOAD SECTION (new in v3.1)
    # ============================================================
    st.markdown("<hr style='border-color:#2a2a40;margin:2rem 0;'>", unsafe_allow_html=True)
    st.markdown("<h3>📄 Upload Bank Statement</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background: #1e1e30; padding: 1rem; border-radius: 12px; border: 1px solid #2a2a40; margin-bottom: 1rem;'>
        <p style='color: #a0a0b0; margin: 0;'>
            Upload your FNB bank statement (PDF or CSV) to automatically extract and categorize transactions.
            No real FNB API access needed — we parse your statement directly.
        </p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Choose statement file", type=["pdf", "csv"])
    if uploaded_file is not None:
        file_type = uploaded_file.name.split('.')[-1].lower()
        with st.spinner(f"Parsing {file_type.upper()} statement..."):
            if file_type == 'pdf':
                transactions = parse_pdf_statement(uploaded_file, st.session_state.user_id)
            else:
                transactions = parse_csv_statement(uploaded_file, st.session_state.user_id)

        if transactions:
            st.success(f"Found {len(transactions)} transactions!")
            # Preview
            preview_df = pd.DataFrame(transactions[:5])
            st.markdown("<p style='color: #a0a0b0;'>Preview:</p>", unsafe_allow_html=True)
            st.dataframe(preview_df, use_container_width=True, hide_index=True)

            if st.button("💾 Save All Transactions", type="primary"):
                saved = save_parsed_transactions(st.session_state.user_id, transactions, "statement_upload")
                # Log upload
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO Statement_Uploads (user_id, filename, file_type, transactions_parsed, status) VALUES (?,?,?,?,?)",
                          (st.session_state.user_id, uploaded_file.name, file_type, saved, "completed"))
                conn.commit()
                conn.close()
                st.success(f"Saved {saved} new transactions to your account!")
                add_notification(st.session_state.user_id, "Statement Parsed", f"{saved} transactions imported from {uploaded_file.name}", "success")
        else:
            st.warning("No transactions found. Try a different file or check the format.")

    # Show upload history
    st.markdown("<h3>📜 Upload History</h3>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df_uploads = pd.read_sql_query(
        "SELECT upload_date, filename, file_type, transactions_parsed, status FROM Statement_Uploads WHERE user_id=? ORDER BY upload_date DESC LIMIT 10",
        conn, params=(st.session_state.user_id,))
    conn.close()
    if not df_uploads.empty:
        st.dataframe(df_uploads, use_container_width=True, hide_index=True)
    else:
        st.info("No statements uploaded yet")

def render_payment_progress():
    track_feature_usage(st.session_state.user_id, "payment_tracking")
    st.markdown("<div class='main-header'><h1>💰 Payment Progress</h1><p>Track contributions, arrears, and payment status</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    current_year = datetime.now().year
    current_month = datetime.now().month

    if st.session_state.role == "admin":
        # Admin view: all members
        st.markdown("<h3>📊 Member Payment Status</h3>", unsafe_allow_html=True)
        c.execute("SELECT user_id, full_name, monthly_contribution FROM Users WHERE role='member' AND is_active=1")
        members = c.fetchall()

        arrears_data = []
        for uid, name, monthly in members:
            c.execute("SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Monthly_Contributions WHERE user_id=? AND year=? AND status IN ('verified', 'paid')",
                      (uid, current_year))
            paid_total, paid_months = c.fetchone()
            c.execute("SELECT COUNT(*) FROM Monthly_Contributions WHERE user_id=? AND year=? AND status IN ('pending', 'partial')",
                      (uid, current_year))
            pending_count = c.fetchone()[0] or 0
            expected = monthly * current_month
            progress = min((paid_total / expected) * 100, 100) if expected > 0 else 0
            status_class = "success" if progress >= 90 else "warning"
            status_text = "Up to date" if progress >= 90 else f"R{expected - paid_total:.0f} behind"

            arrears_data.append({
                "name": name, "progress": progress, "status_class": status_class,
                "status_text": status_text, "paid": paid_total, "expected": expected,
                "pending": pending_count
            })

        conn.close()

        # Summary cards
        total_behind = sum(d["expected"] - d["paid"] for d in arrears_data if d["paid"] < d["expected"])
        members_behind = sum(1 for d in arrears_data if d["progress"] < 90)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Behind</div><div class='metric-value'>R{total_behind:,.0f}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Members Behind</div><div class='metric-value'>{members_behind}</div></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Avg Progress</div><div class='metric-value'>{sum(d['progress'] for d in arrears_data) / len(arrears_data):.0f}%</div></div>", unsafe_allow_html=True) if arrears_data else st.info("No member data")

        # Member table
        st.markdown("<h3>📋 Member Details</h3>", unsafe_allow_html=True)
        df_arrears = pd.DataFrame(arrears_data)
        if not df_arrears.empty:
            st.dataframe(df_arrears, use_container_width=True, hide_index=True)

        # Monthly detail
        st.markdown("<h3>📅 Monthly Detail</h3>", unsafe_allow_html=True)
        for uid, name, monthly in members:
            with st.expander(f"{name} — R{monthly:.0f}/month"):
                conn = sqlite3.connect(DB_PATH)
                df_monthly = pd.read_sql_query(
                    "SELECT month, amount, status, payment_date FROM Monthly_Contributions WHERE user_id=? AND year=? ORDER BY month",
                    conn, params=(uid, current_year))
                conn.close()
                if not df_monthly.empty:
                    df_monthly['month_name'] = df_monthly['month'].apply(lambda x: MONTHS[int(x) - 1])
                    st.dataframe(df_monthly, use_container_width=True, hide_index=True)
                else:
                    st.info("No payments recorded yet")
    else:
        # Member view
        st.markdown("<h3>📊 Your Payment Status</h3>", unsafe_allow_html=True)
        uid = st.session_state.user_id
        c.execute("SELECT monthly_contribution FROM Users WHERE user_id=?", (uid,))
        monthly = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Monthly_Contributions WHERE user_id=? AND year=? AND status IN ('verified', 'paid')",
                  (uid, current_year))
        paid_total, paid_months = c.fetchone()
        expected = monthly * current_month
        progress = min((paid_total / expected) * 100, 100) if expected > 0 else 0

        # Summary
        st.markdown(f"""
        <div style="display: flex; gap: 1rem; margin: 1rem 0;">
            <div class="metric-card" style="flex: 1;">
                <div class="metric-label">Your Monthly Target</div>
                <div class="metric-value">R{monthly:,.0f}</div>
            </div>
            <div class="metric-card" style="flex: 1;">
                <div class="metric-label">Paid This Year</div>
                <div class="metric-value">R{paid_total:,.0f}</div>
            </div>
            <div class="metric-card" style="flex: 1;">
                <div class="metric-label">Progress</div>
                <div class="metric-value">{progress:.0f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Progress bar
        progress_color = "#00b894" if progress >= 90 else "#fdcb6e" if progress >= 50 else "#ff4757"
        st.markdown(f"""
        <div class="progress-bar" style="background: #2a2a40; border-radius: 8px; height: 20px; margin: 1rem 0;">
            <div class="progress-fill" style="width: {progress}%; background: {progress_color}; height: 100%; border-radius: 8px; transition: width 0.5s ease;"></div>
        </div>
        """, unsafe_allow_html=True)

        # Monthly table
        conn = sqlite3.connect(DB_PATH)
        df_monthly = pd.read_sql_query(
            "SELECT month, amount, status, payment_date FROM Monthly_Contributions WHERE user_id=? AND year=? ORDER BY month",
            conn, params=(uid, current_year))
        conn.close()
        if not df_monthly.empty:
            df_monthly['month_name'] = df_monthly['month'].apply(lambda x: MONTHS[int(x) - 1])
            st.dataframe(df_monthly, use_container_width=True, hide_index=True)
        else:
            st.info("No payments recorded yet")

        conn.close()

# ============================================================
# AI ADVISOR (v3.1 - Super Live with Market Data)
# ============================================================

def get_ai_context(user_id):
    """Build rich context for AI advisor including portfolio, risk, statement data"""
    context = {
        "user_name": st.session_state.get("full_name", "Member"),
        "risk_profile": "moderate",
        "portfolio_value": 0,
        "monthly_target": 0,
        "statement_summary": {}
    }
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Risk profile & monthly target
    c.execute("SELECT risk_profile, monthly_contribution FROM Users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        context["risk_profile"] = row[0] or "moderate"
        context["monthly_target"] = row[1] or 0

    # Portfolio value
    c.execute("SELECT COALESCE(SUM(current_value), 0) FROM Investments")
    context["portfolio_value"] = c.fetchone()[0] or 0

    # Statement summary
    c.execute("""SELECT COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) as income,
                        COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as expenses,
                        COUNT(*) as txn_count
                 FROM Parsed_Transactions WHERE user_id=?""", (user_id,))
    stmt = c.fetchone()
    if stmt:
        context["statement_summary"] = {
            "total_income": stmt[0],
            "total_expenses": stmt[1],
            "net_flow": stmt[0] - stmt[1],
            "contribution_count": stmt[2]
        }

    conn.close()
    return context

# KHULA_APPEND_MARKER_7a3f9e2d
