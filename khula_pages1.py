from khula_member_services import submit_payment_claim
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
    """Member claims are pending until a real receipt/bank entry is reviewed."""
    track_feature_usage(st.session_state.user_id, "payment_tracking")
    st.title("💰 Contributions and Savings")
    st.warning("Recorded contribution totals are ledger entries, not live FNB balances. Historical entries made before the approval workflow require reconciliation.")
    now = datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        members = conn.execute(
            "SELECT user_id,full_name,COALESCE(monthly_contribution,0) "
            "FROM Users WHERE is_active=1 AND role='member' ORDER BY full_name"
        ).fetchall()
        recorded = conn.execute(
            "SELECT user_id,COALESCE(SUM(amount),0) "
            "FROM Monthly_Contributions WHERE year=? AND month=? AND status='paid' "
            "GROUP BY user_id",
            (now.year, now.month),
        ).fetchall()
        claims = conn.execute(
            "SELECT claim_id,year,month,amount_zar,status,payment_reference "
            "FROM Payment_Claims WHERE user_id=? ORDER BY submitted_at DESC LIMIT 15",
            (st.session_state.user_id,),
        ).fetchall()
    amounts = dict(recorded)
    expected = sum(max(0.0, target) for _, _, target in members)
    collected = sum(max(0.0, amounts.get(uid, 0.0)) for uid, _, _ in members)
    col_a, col_b = st.columns(2)
    col_a.metric("Recorded club contributions this month", f"R{collected:,.2f}")
    col_b.metric("Sum of member monthly targets", f"R{expected:,.2f}")
    if expected:
        st.progress(min(1.0, collected / expected))
        st.caption("This is a contribution-tracking ratio, not verified bank cash.")
    else:
        st.info("No active member contribution targets are recorded.")

    is_admin = st.session_state.get("role") == "admin"
    st.subheader("Monthly member progress")
    for uid, member_name, target in members:
        if not is_admin and uid != st.session_state.user_id:
            continue
        paid = amounts.get(uid, 0.0)
        shortfall = max(0.0, target - paid)
        st.write(f"{member_name}: recorded R{paid:,.2f} / target R{target:,.2f}; remaining R{shortfall:,.2f}")
        if target:
            st.progress(min(1.0, paid / target))

    if st.session_state.get("role") == "member":
        st.subheader("Submit a contribution for verification")
        st.caption("This form does NOT transfer money and cannot mark you as paid. The administrator must check the actual bank statement.")
        with st.form("submit_payment_claim"):
            amount = st.number_input("Amount deposited or paid (ZAR)", min_value=1.0, max_value=10000000.0, step=50.0)
            method = st.selectbox("Payment method", ["EFT", "Cash", "Other"])
            reference = st.text_input("Bank or receipt reference (no account numbers)")
            if st.form_submit_button("Submit for review"):
                try:
                    submit_payment_claim(st.session_state.user_id, now.year, now.month, amount, method, reference)
                    st.success("Payment claim submitted, pending bank/receipt review.")
                    st.rerun()
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
        if claims:
            st.subheader("My recent claims")
            st.dataframe([
                {"Period": f"{month}/{year}", "Amount": amount, "Status": status,
                 "Reference": ref}
                for _, year, month, amount, status, ref in claims
            ], use_container_width=True)
    elif is_admin:
        st.info("Review claims in Admin Reconciliation; only an approved claim posts to the paid ledger.")


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
