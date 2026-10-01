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
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Collection Rate</div><div class='metric-value'>{((sum(d['paid'] for d in arrears_data)/sum(d['expected'] for d in arrears_data))*100):.0f}%</div></div>", unsafe_allow_html=True)

        # Member progress bars
        for d in arrears_data:
            st.markdown(f"""
            <div class='arrears-card {d['status_class']}'>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong>{d['name']}</strong>
                    <span class="payment-status status-{'paid' if d['progress'] >= 90 else 'partial'}">{d['status_text']}</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar {d['status_class']}" style="width: {d['progress']}%"></div>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:0.5rem; font-size:0.8rem; color:#a0a0b0;">
                    <span>R{d['paid']:,.0f} paid</span>
                    <span>R{d['expected']:,.0f} expected</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Arrears report table
        st.markdown("<h3>📋 Detailed Arrears Report</h3>", unsafe_allow_html=True)
        df_arrears = pd.DataFrame(arrears_data)
        if not df_arrears.empty:
            df_arrears['Progress'] = df_arrears['progress'].round(1).astype(str) + '%'
            df_arrears['Behind'] = df_arrears.apply(lambda x: f"R{x['expected'] - x['paid']:,.0f}" if x['paid'] < x['expected'] else "R0", axis=1)
            st.dataframe(df_arrears[['name', 'Progress', 'paid', 'expected', 'Behind', 'pending']].rename(columns={
                'name': 'Member', 'paid': 'Paid (R)', 'expected': 'Expected (R)', 'pending': 'Pending'
            }), use_container_width=True, hide_index=True)
    else:
        # Member view: personal progress
        c.execute("SELECT monthly_contribution FROM Users WHERE user_id=?", (st.session_state.user_id,))
        monthly = c.fetchone()[0] or 500.0
        c.execute("SELECT year, month, amount, status FROM Monthly_Contributions WHERE user_id=? AND year=? ORDER BY month",
                  (st.session_state.user_id, current_year))
        payments = c.fetchall()
        conn.close()

        expected = monthly * current_month
        paid = sum(p[2] for p in payments if p[3] in ('verified', 'paid'))
        progress = min((paid / expected) * 100, 100) if expected > 0 else 0

        st.markdown(f"""
        <div class='metric-card' style="margin-bottom: 1.5rem;">
            <div class='metric-label'>Your Payment Progress ({datetime.now().strftime('%B %Y')})</div>
            <div class='metric-value'>{progress:.0f}%</div>
            <div class="progress-container" style="margin-top: 1rem;">
                <div class="progress-bar {'success' if progress >= 90 else 'warning'}" style="width: {progress}%"></div>
            </div>
            <p style="margin-top:0.5rem; color:#a0a0b0;">R{paid:,.0f} paid of R{expected:,.0f} expected</p>
        </div>
        """, unsafe_allow_html=True)

        if progress < 100:
            st.warning(f"You are R{expected - paid:,.0f} behind. Please make a payment to catch up.")
            st.markdown("**Payment Options:**")
            col1, col2 = st.columns(2)
            with col1:
                st.info("FNB App: Send to Khula Collective\nAcc: 1234567890\nRef: KHULA-" + str(st.session_state.user_id))
            with col2:
                st.info("EFT:\nBank: FNB\nAcc: 1234567890\nBranch: 250312")

        st.markdown("<h3>📅 Monthly Breakdown</h3>", unsafe_allow_html=True)
        if payments:
            df_payments = pd.DataFrame(payments, columns=['Year', 'Month', 'Amount', 'Status'])
            df_payments['Month Name'] = df_payments['Month'].apply(lambda x: MONTHS[int(x)-1])
            st.dataframe(df_payments[['Month Name', 'Amount', 'Status']], use_container_width=True, hide_index=True)
        else:
            st.info("No payment records found")


# ============================================================
# ============================================================
# AI ADVISOR — v4.0 SUPERCHARGED (Global Market Intelligence)
# ============================================================

# FX Conversion Constants (ZAR-centric)
USD_TO_ZAR = 18.5
EUR_TO_ZAR = 20.2


def _get_region_flag(region: str) -> str:
    """Return emoji flag for a region."""
    return {
        "SA": "🇿🇦",
        "US": "🇺🇸",
        "EU": "🇪🇺",
        "EM": "🌍",
        "Crypto": "₿",
        "Commodity": "🛢️",
    }.get(region, "🌐")


def _get_region_name(region: str) -> str:
    """Return human-readable region name."""
    return {
        "SA": "South Africa",
        "US": "United States",
        "EU": "Europe",
        "EM": "Emerging Markets",
        "Crypto": "Crypto",
        "Commodity": "Commodities",
    }.get(region, region)


def _risk_badge(risk_level: str) -> str:
    """Return HTML risk badge."""
    colors = {"low": ("#00b894", "🟢 Low"), "medium": ("#fdcb6e", "🟡 Medium"), "high": ("#ff4757", "🔴 High")}
    color, label = colors.get(risk_level, ("#a0a0b0", "⚪ Unknown"))
    return f'<span style="background:{color}22; color:{color}; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600; border:1px solid {color}44;">{label}</span>'


def _actionable_badge(is_actionable: bool) -> str:
    """Return actionable status badge."""
    if is_actionable:
        return '<span style="background:#00b89422; color:#00b894; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600;">✅ You can afford this</span>'
    return '<span style="background:#ffa50222; color:#ffa502; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600;">⏳ Save more needed</span>'


def _format_market_cap(mcap: float) -> str:
    """Format market cap in B/M."""
    if mcap >= 1e12:
        return f"${mcap/1e12:.1f}T"
    elif mcap >= 1e9:
        return f"${mcap/1e9:.1f}B"
    elif mcap >= 1e6:
        return f"${mcap/1e6:.1f}M"
    return f"${mcap:,.0f}"


def _convert_to_zar(price: float, currency: str) -> float:
    """Convert foreign currency price to ZAR."""
    if currency == "USD":
        return price * USD_TO_ZAR
    elif currency == "EUR":
        return price * EUR_TO_ZAR
    elif currency == "ZAR":
        return price
    return price * USD_TO_ZAR  # Default fallback


def _get_mock_market_data() -> list:
    """Return fallback mock market data when API fetch fails."""
    return [
        {"ticker": "SHP.JO", "name": "Shoprite Holdings", "price": 285.50, "currency": "ZAR", "change_pct": 1.2, "market_cap": 1.7e11, "sector": "Consumer Defensive", "country": "South Africa", "exchange": "JSE", "risk_level": "low", "region": "SA", "category": "stock"},
        {"ticker": "AGL.JO", "name": "Anglo American plc", "price": 620.00, "currency": "ZAR", "change_pct": -0.8, "market_cap": 8.5e10, "sector": "Basic Materials", "country": "United Kingdom", "exchange": "JSE", "risk_level": "medium", "region": "SA", "category": "stock"},
        {"ticker": "MTN.JO", "name": "MTN Group", "price": 98.50, "currency": "ZAR", "change_pct": 0.5, "market_cap": 1.8e10, "sector": "Communication", "country": "South Africa", "exchange": "JSE", "risk_level": "medium", "region": "SA", "category": "stock"},
        {"ticker": "NPN.JO", "name": "Naspers Ltd", "price": 2850.00, "currency": "ZAR", "change_pct": 2.1, "market_cap": 1.2e12, "sector": "Communication", "country": "South Africa", "exchange": "JSE", "risk_level": "medium", "region": "SA", "category": "stock"},
        {"ticker": "FSR.JO", "name": "FirstRand Ltd", "price": 68.20, "currency": "ZAR", "change_pct": 0.3, "market_cap": 3.8e11, "sector": "Financials", "country": "South Africa", "exchange": "JSE", "risk_level": "low", "region": "SA", "category": "stock"},
        {"ticker": "STX40.JO", "name": "Satrix 40 ETF", "price": 65.40, "currency": "ZAR", "change_pct": 0.7, "market_cap": 5e9, "sector": "ETF", "country": "South Africa", "exchange": "JSE", "risk_level": "low", "region": "SA", "category": "etf"},

# KHULA_APPEND_MARKER_7a3f9e2d
