from khula_security import register_member, registration_enabled
from khula_config import *
from khula_utils import *
import hashlib
import time
import random
from datetime import datetime, timedelta

# ============================================================
# PAGE 1: Login, Dashboard, Payments, FNB Sync, Features, AI Advisor, Global Markets
# ============================================================

def render_login():
    """Login page with centered branding."""
    is_dark = st.session_state.get("theme", "dark") == "dark"
    bg = "#0f0f23" if is_dark else "#f8f9fa"
    card = "#1e1e30" if is_dark else "#ffffff"
    text = "#ffffff" if is_dark else "#1a1a2e"
    text_muted = "#a0a0b0" if is_dark else "#6c757d"
    border = "#2a2a40" if is_dark else "#dee2e6"
    accent = "#00b894"

    st.markdown(f"""
    <style>
    .stApp {{ background: {bg} !important; color: {text} !important; }}
    .login-container {{ max-width: 420px; margin: 0 auto; padding: 2rem; }}
    .login-logo {{ text-align: center; margin-bottom: 1.5rem; }}
    .login-logo h1 {{ color: {accent}; font-weight: 800; font-size: 2.2rem; margin: 0; }}
    .login-logo p {{ color: {text_muted}; font-size: 1rem; margin-top: 0.25rem; }}
    .login-card {{ background: {card}; padding: 2rem; border-radius: 20px; border: 1px solid {border}; box-shadow: 0 8px 32px rgba(0,0,0,0.12); }}
    .login-input {{ margin-bottom: 1rem; }}
    .login-btn {{ width: 100%; background: linear-gradient(135deg, {accent}, #00cec9); color: white; border: none; padding: 0.85rem; border-radius: 12px; font-weight: 600; font-size: 1rem; cursor: pointer; }}
    .login-btn:hover {{ opacity: 0.9; }}
    .version-tag {{ text-align: center; color: {accent}; font-weight: 600; font-size: 0.9rem; margin-bottom: 1rem; }}
    .demo-box {{ background: {card}; padding: 1rem; border-radius: 12px; border: 1px solid {border}; margin-top: 1.5rem; font-size: 0.85rem; color: {text_muted}; }}
    .powered-by {{ text-align: center; color: {text_muted}; font-size: 0.8rem; margin-top: 2rem; }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='login-container'>
        <div class='login-logo'>
            <h1>📈 Khula Collective</h1>
            <p>Empowering South African stokvels &amp; investment clubs</p>
        </div>
        <div class='version-tag'>v4.0 &middot; Super Live Model</div>
        <div class='login-card'>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        submitted = st.form_submit_button("🔓 Sign In")
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
                return
            user = authenticate(username, password)
            if user:
                st.session_state.authenticated = True
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
                st.error("Invalid username or password")

    if registration_enabled():
        with st.expander("New member? Register with your invitation"):
            with st.form("member_registration"):
                new_user = st.text_input("Choose username")
                new_name = st.text_input("Full legal name")
                new_email = st.text_input("Email")
                new_password = st.text_input("Create a strong password (12+ characters)", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                invite = st.text_input("Invitation code", type="password")
                if st.form_submit_button("Create member account"):
                    if new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            register_member(DB_PATH, new_user, new_name, new_email, new_password, invite)
                            st.success("Account created. Please sign in; member verification is still pending.")
                        except ValueError as exc:
                            st.error(str(exc))

    st.markdown("""
        </div>
        <div class='demo-box'>
            Member onboarding is by invitation only. Please contact your club administrator.
        </div>
        <div class='powered-by'>Powered by FNB Open Banking API &middot; Global Market Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

def render_dashboard():
    """Main dashboard with portfolio overview, market data, and quick actions."""
    track_feature_usage(st.session_state.user_id, "dashboard")
    user_name = st.session_state.get("full_name", "Member")

    st.markdown(f"""
    <div class='main-header'>
        <h1>🏠 Welcome, {user_name}</h1>
        <p>Your club portfolio at a glance</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Market Ticker ───────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COALESCE(SUM(current_value), 0) FROM Investments")
    portfolio_value = c.fetchone()[0] or 0

    c.execute("SELECT COALESCE(SUM(amount_invested), 0) FROM Investments")
    total_invested = c.fetchone()[0] or 0

    c.execute("SELECT COALESCE(SUM(returns), 0) FROM Investments")
    total_returns = c.fetchone()[0] or 0

    current_year = datetime.now().year
    current_month = datetime.now().month
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE year=? AND month=? AND status='paid'", (current_year, current_month))
    month_contrib = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(DISTINCT user_id) FROM Users WHERE is_active=1")
    active_members = c.fetchone()[0] or 0

    conn.close()

    # ── KPI Cards ───────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Portfolio Value</div>
            <div class='metric-value'>R{portfolio_value:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        delta_color = "#2ed573" if total_returns >= 0 else "#ff4757"
        delta_sign = "+" if total_returns >= 0 else ""
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Total Returns</div>
            <div class='metric-value' style='color:{delta_color};'>{delta_sign}R{total_returns:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>This Month</div>
            <div class='metric-value'>R{month_contrib:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Members</div>
            <div class='metric-value'>{active_members}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── News Ticker ─────────────────────────────────────────
    news = random.choice(SA_NEWS_HEADLINES)
    st.markdown(f"""
    <div style='background:#1e1e30;padding:0.75rem 1rem;border-radius:12px;border-left:4px solid #00b894;margin-bottom:1rem;'>
        <span style='color:#00b894;font-weight:600;font-size:0.8rem;'>LATEST</span>
        <span style='color:#ffffff;font-size:0.9rem;margin-left:0.5rem;'>{news}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Portfolio Breakdown ─────────────────────────────────
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("Portfolio Composition")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT type, SUM(current_value) FROM Investments GROUP BY type")
        data = c.fetchall()
        conn.close()
        if data:
            df = pd.DataFrame(data, columns=["Type", "Value"])
            fig = px.pie(df, values="Value", names="Type", hole=0.45, color_discrete_sequence=px.colors.sequential.Teal)
            fig.update_layout(showlegend=True, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No investments yet")

    with col_right:
        st.subheader("Quick Actions")
        actions = [
            ("💰", "Make Contribution", "payment_tracking"),
            ("🗳️", "Vote on Proposal", "member_voice"),
            ("🤖", "Ask AI Advisor", "ai_advisor"),
            ("🌍", "Global Markets", "global_markets"),
            ("🆔", "Verify ID", "id_verify"),
        ]
        for icon, label, page in actions:
            if st.button(f"{icon} {label}", key=f"qa_{page}", use_container_width=True):
                st.session_state.nav_page = page
                st.rerun()

    # Prices must come from a real provider, never seeded values.
    st.info("Live market quotes appear in Global Markets when an authorised data provider is configured.")

def render_fnb_sync():
    """FNB bank sync with statement upload."""
    track_feature_usage(st.session_state.user_id, "fnb_sync")
    st.markdown("""
    <div class='main-header'>
        <h1>🏦 FNB Bank Sync</h1>
        <p>Connect your FNB account or upload bank statements</p>
    </div>
    """, unsafe_allow_html=True)

    # FNB Connect Card
    st.markdown("""
    <div class='fnb-connect-card'>
        <h3>🔗 Connect to FNB</h3>
        <p>Securely link your FNB account for automatic transaction sync</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Connect FNB Account", use_container_width=True, type="primary"):
            st.warning("Live FNB bank connection is not enabled. Use PDF/CSV statement import for review; it is not equivalent to a verified bank feed.")
    with col2:
        if st.button("Test API Connection", use_container_width=True):
            client = FNBAPIClient()
            result = client.connect()
            if result["success"]:
                st.success(result["message"])
            else:
                st.error(result["error"])

    st.divider()

    # Statement Upload
    st.subheader("📄 Upload Bank Statement")
    st.markdown("Support for **PDF** (FNB eStatement) and **CSV** export formats.")

    uploaded = st.file_uploader("Choose statement file", type=["pdf", "csv"], accept_multiple_files=False)
    if uploaded:
        st.info(f"File: `{uploaded.name}` ({uploaded.size:,} bytes)")
        if st.button("Parse & Import", type="primary", use_container_width=True):
            try:
                if uploaded.name.lower().endswith(".pdf"):
                    transactions = parse_pdf_statement(uploaded, st.session_state.user_id)
                else:
                    transactions = parse_csv_statement(uploaded, st.session_state.user_id)
                saved = save_parsed_transactions(st.session_state.user_id, transactions)
                st.success(f"Imported {saved} transactions successfully!")
                if transactions:
                    st.subheader("Preview (first 5)")
                    st.dataframe(pd.DataFrame(transactions[:5]), use_container_width=True)
            except Exception as e:
                st.error(f"Parse error: {e}")

    st.divider()

    # Statement Summary
    st.subheader("📊 Your Financial Snapshot")
    summary = get_user_statement_summary(st.session_state.user_id)
    if summary["total_income"] > 0 or summary["total_expenses"] > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Income", f"R{summary['total_income']:,.2f}")
        with c2:
            st.metric("Total Expenses", f"R{summary['total_expenses']:,.2f}")
        with c3:
            net_color = "normal" if summary["net_flow"] >= 0 else "inverse"
            st.metric("Net Flow", f"R{summary['net_flow']:,.2f}", delta_color=net_color)

        if summary["categories"]:
            st.subheader("Spending by Category")
            df_cat = pd.DataFrame(summary["categories"], columns=["Category", "Amount", "Count"])
            fig = px.bar(df_cat, x="Category", y="Amount", color="Category")
            st.plotly_chart(fig, use_container_width=True)

        if summary["contributions_detected"] > 0:
            st.success(f"💡 Detected {summary['contribution_count']} Khula-related contributions totalling R{summary['contributions_detected']:,.2f}")
    else:
        st.info("Upload a bank statement to see your financial snapshot.")

def render_payment_progress():
    """Payment tracking with detailed progress per member."""
    track_feature_usage(st.session_state.user_id, "payment_tracking")
    st.markdown("""
    <div class='main-header'>
        <h1>💰 Payment Tracking</h1>
        <p>Track contributions and manage arrears</p>
    </div>
    """, unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    current_year = datetime.now().year
    current_month = datetime.now().month

    # Overall stats
    c.execute("SELECT COUNT(*) FROM Users WHERE is_active=1")
    total_members = c.fetchone()[0] or 1
    c.execute("SELECT COUNT(*) FROM Monthly_Contributions WHERE year=? AND month=? AND status='paid'", (current_year, current_month))
    paid_count = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE year=? AND month=? AND status='paid'", (current_year, current_month))
    total_collected = c.fetchone()[0] or 0

    expected = total_members * 500
    collection_rate = (total_collected / expected * 100) if expected > 0 else 0

    st.markdown(f"""
    <div style='display:flex;gap:1rem;margin-bottom:1.5rem;'>
        <div class='metric-card' style='flex:1;'><div class='metric-label'>Collection Rate</div><div class='metric-value'>{collection_rate:.1f}%</div></div>
        <div class='metric-card' style='flex:1;'><div class='metric-label'>Paid / Total</div><div class='metric-value'>{paid_count}/{total_members}</div></div>
        <div class='metric-card' style='flex:1;'><div class='metric-label'>Total Collected</div><div class='metric-value'>R{total_collected:,.0f}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Progress bar
    st.markdown(f"""
    <div class='progress-container'>
        <div class='progress-bar {"success" if collection_rate >= 80 else "warning"}' style='width:{collection_rate}%;'></div>
    </div>
    <p style='text-align:center;font-size:0.8rem;color:#a0a0b0;margin-top:0.25rem;'>{collection_rate:.1f}% of monthly target reached</p>
    """, unsafe_allow_html=True)

    # Member breakdown
    st.subheader("Member Contributions")
    c.execute("SELECT user_id, full_name, monthly_contribution FROM Users WHERE is_active=1 ORDER BY full_name")
    members = c.fetchall()

    for uid, name, target in members:
        c.execute("SELECT amount, status FROM Monthly_Contributions WHERE user_id=? AND year=? AND month=?", (uid, current_year, current_month))
        row = c.fetchone()
        paid = row[0] if row else 0
        status = row[1] if row else "pending"
        pct = (paid / target * 100) if target and target > 0 else 0

        status_class = "success" if status == "paid" else "warning" if status == "partial" else ""
        status_label = status.upper()
        bar_class = "success" if pct >= 100 else "warning" if pct >= 50 else ""

        with st.container():
            st.markdown(f"""
            <div class='arrears-card {status_class}'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <span style='font-weight:600;'>{name}</span>
                    <span class='payment-status {"status-paid" if status=="paid" else "status-partial" if status=="partial" else "status-late"}'>{status_label}</span>
                </div>
                <div style='font-size:0.85rem;color:#a0a0b0;margin-top:0.25rem;'>R{paid:,.0f} / R{target:,.0f}</div>
                <div class='progress-container'><div class='progress-bar {bar_class}' style='width:{min(pct,100)}%;'></div></div>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.user_id == uid and status != "paid":
                with st.expander("Make Payment"):
                    amt = st.number_input("Amount (R)", min_value=0.0, value=float(target - paid), step=50.0, key=f"pay_{uid}")
                    method = st.selectbox("Method", ["EFT", "Cash", "FNB Instant Pay"], key=f"meth_{uid}")
                    if st.button("Confirm Payment", key=f"btn_{uid}"):
                        now = datetime.now().isoformat()
                        if row:
                            c.execute("UPDATE Monthly_Contributions SET amount=amount+?, status=?, payment_date=?, payment_method=? WHERE user_id=? AND year=? AND month=?",
                                      (amt, "paid" if (paid + amt) >= target else "partial", now, method, uid, current_year, current_month))
                        else:
                            c.execute("INSERT INTO Monthly_Contributions (user_id, year, month, amount, status, payment_date, payment_method) VALUES (?,?,?,?,?,?,?)",
                                      (uid, current_year, current_month, amt, "paid" if amt >= target else "partial", now, method))
                        conn.commit()
                        add_notification(uid, "Payment Recorded", f"R{amt:,.2f} recorded via {method}", "success")
                        st.success("Payment recorded!")
                        time.sleep(1)
                        st.rerun()

    conn.close()

# ── Global Markets Helpers ──────────────────────────────────

# The v3 static market snapshots and synthetic stock picks were removed from the
# active user experience. See khula_intelligence for a source-labelled feed and
# conservative savings-based educational guidance.

def render_ai_advisor():
    from khula_intelligence import render_investment_guide
    return render_investment_guide()


def render_global_markets():
    from khula_intelligence import render_market_explorer
    return render_market_explorer()
