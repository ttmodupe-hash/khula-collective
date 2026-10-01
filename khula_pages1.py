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

    st.markdown("""
        </div>
        <div class='demo-box'>
            <strong>Demo Credentials</strong><br>
            Admin: <code>admin</code> / <code>admin123</code><br>
            Member: <code>siphoo</code> / <code>password1</code>
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

    # ── Market Snapshot ─────────────────────────────────────
    st.subheader("SA Market Snapshot")
    mcols = st.columns(5)
    snapshot_items = [
        ("JSE All Share", SA_MARKET_DATASET["jse_allshare"]),
        ("USD/ZAR", SA_MARKET_DATASET["usd_zar"]),
        ("Gold", SA_MARKET_DATASET["gold_price"]),
        ("Brent Oil", SA_MARKET_DATASET["brent_oil"]),
        ("SARB Rate", SA_MARKET_DATASET["sarb_rate"]),
    ]
    for col, (label, data) in zip(mcols, snapshot_items):
        with col:
            change_color = "#2ed573" if data["change"] >= 0 else "#ff4757"
            change_sign = "+" if data["change"] >= 0 else ""
            st.markdown(f"""
            <div style='background:#1e1e30;padding:0.75rem;border-radius:12px;text-align:center;border:1px solid #2a2a40;'>
                <div style='font-size:0.75rem;color:#a0a0b0;'>{label}</div>
                <div style='font-size:1.1rem;font-weight:700;color:#ffffff;'>{data['value']:,.2f}</div>
                <div style='font-size:0.75rem;color:{change_color};'>{change_sign}{data['change']}%</div>
            </div>
            """, unsafe_allow_html=True)

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
            st.info("FNB OAuth would open here in production. Simulating connection...")
            time.sleep(1)
            st.success("Simulated FNB connection successful!")
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

def _get_region_flag(region):
    flags = {"SA": "🇿🇦", "US": "🇺🇸", "EU": "🇪🇺", "EM": "🌏", "Crypto": "₿", "Commodity": "🛢️"}
    return flags.get(region, "🌐")

def _get_region_name(region):
    names = {"SA": "South Africa / JSE", "US": "United States", "EU": "Europe", "EM": "Emerging Markets", "Crypto": "Cryptocurrency", "Commodity": "Commodities"}
    return names.get(region, region)

def _risk_badge(risk):
    colors = {"low": ("#2ed573", "Low"), "medium": ("#ffa502", "Medium"), "high": ("#ff4757", "High")}
    color, label = colors.get(risk, ("#a0a0b0", risk.title()))
    return f"<span style='display:inline-block;padding:0.15rem 0.5rem;border-radius:8px;font-size:0.7rem;font-weight:600;background:{color}22;color:{color};'>{label}</span>"

def _actionable_badge(actionable):
    colors = {"buy": ("#2ed573", "BUY"), "watch": ("#ffa502", "WATCH"), "hold": ("#00b894", "HOLD"), "avoid": ("#ff4757", "AVOID")}
    color, label = colors.get(actionable, ("#a0a0b0", actionable.upper()))
    return f"<span style='display:inline-block;padding:0.15rem 0.5rem;border-radius:8px;font-size:0.7rem;font-weight:600;background:{color}33;color:{color};'>{label}</span>"

def _format_market_cap(cap):
    if cap is None or cap == "N/A":
        return "N/A"
    try:
        val = float(cap)
        if val >= 1e12:
            return f"${val/1e12:.2f}T"
        elif val >= 1e9:
            return f"${val/1e9:.2f}B"
        elif val >= 1e6:
            return f"${val/1e6:.2f}M"
        else:
            return f"${val:,.0f}"
    except:
        return str(cap)

def _convert_to_zar(price_usd, region):
    if region == "SA":
        return price_usd
    if price_usd is None or price_usd == "N/A":
        return None
    try:
        return float(price_usd) * ZAR_RATES.get("USD", 18.5)
    except:
        return None

def _get_mock_market_data(ticker_info):
    """Generate realistic mock market data when live API fails."""
    random.seed(hash(ticker_info["ticker"]) % 10000)
    base_prices = {
        "SHP.JO": 28500, "AGL.JO": 62000, "MTN.JO": 15200, "NPN.JO": 320000, "FSR.JO": 6800,
        "STX40.JO": 6500, "AAPL": 185, "MSFT": 420, "GOOGL": 175, "AMZN": 185,
        "TSLA": 245, "NVDA": 890, "JPM": 195, "BRK-B": 415, "VOO": 470,
        "SAP.DE": 185, "ASML.AS": 890, "NESN.SW": 105, "LVMH.PA": 875, "AIR.PA": 155,
        "EXS1.DE": 52, "0700.HK": 385, "BABA": 78, "TCEHY": 42,
        "BTC-USD": 68500, "ETH-USD": 3550, "GC=F": 2350, "CL=F": 82,
    }
    base = base_prices.get(ticker_info["ticker"], 100)
    # Add some randomness
    price = base * (1 + random.uniform(-0.05, 0.05))
    change_pct = random.uniform(-3.5, 3.5)
    pe = random.uniform(12, 35) if ticker_info["category"] == "stock" else None
    div_yield = random.uniform(1.5, 4.5) if ticker_info["category"] == "stock" else (random.uniform(0, 0.5) if ticker_info["category"] == "crypto" else None)
    mcap = base * random.uniform(1e8, 5e9) if ticker_info["category"] != "commodity" else None
    return {
        "price_usd": round(price, 2),
        "change_pct": round(change_pct, 2),
        "pe_ratio": round(pe, 2) if pe else None,
        "dividend_yield": round(div_yield, 2) if div_yield else None,
        "market_cap": mcap,
    }

def _calculate_affordability_cards(price_zar, bank_balance):
    """Return affordability stats for an asset."""
    if not price_zar or price_zar <= 0:
        return None
    units = int((bank_balance * 0.8) / price_zar) if bank_balance else 0
    total = units * price_zar
    return {
        "units_affordable": units,
        "total_cost_zar": round(total, 2),
        "percent_of_balance": round((total / bank_balance * 100), 1) if bank_balance else 0,
    }

def _group_by_region(assets):
    groups = {}
    for a in assets:
        r = a.get("region", "Other")
        groups.setdefault(r, []).append(a)
    return groups

# ── AI Advisor ──────────────────────────────────────────────

def generate_ai_response(question, context):
    """Generate contextual AI advisor response based on user data and SA market knowledge."""
    q_lower = question.lower()
    user_risk = context.get("risk_profile", "moderate")
    portfolio = context.get("portfolio_value", 0)
    statement = context.get("statement_summary", {})
    monthly_target = context.get("monthly_target", 500)
    this_month = context.get("this_month_contrib", 0)

    # Default greeting
    if any(w in q_lower for w in ["hello", "hi", "hey", "greetings"]):
        return f"Hello {context.get('user_name', 'there')}! I'm your Khula Collective AI Advisor. Ask me about JSE stocks, investment strategies, or your portfolio."

    # Contribution advice
    if any(w in q_lower for w in ["contribution", "payment", "monthly", "arrears", "owed"]):
        if this_month >= monthly_target:
            return f"Great job! You've contributed R{this_month:,.2f} this month (target: R{monthly_target:,.2f}). You're fully paid up. 🎉"
        else:
            shortfall = monthly_target - this_month
            return f"You're R{shortfall:,.2f} short of your R{monthly_target:,.2f} monthly target. Consider topping up before the 7th to avoid penalties."

    # Portfolio advice
    if any(w in q_lower for w in ["portfolio", "returns", "performance", "how am i doing", "wealth"]):
        if portfolio > 0:
            return f"Your club portfolio is valued at R{portfolio:,.2f}. Based on your {user_risk} risk profile, consider rebalancing quarterly. Would you like specific JSE stock picks?"
        return "Your portfolio is just getting started! Once contributions flow in, I can recommend allocation strategies tailored to your risk profile."

    # JSE / Stock picks
    if any(w in q_lower for w in ["jse", "stock", "share", "pick", "buy", "invest", "anglo", "sasol", "naspers", "shoprite", "satrix"]):
        picks = AI_ADVISOR_KNOWLEDGE["jse_sectors"]
        if "resource" in q_lower or "mining" in q_lower or "anglo" in q_lower or "sibanye" in q_lower or "gold" in q_lower:
            sector = picks["resources"]
            return f"Resources outlook: {sector['outlook'].title()}. Key drivers: {', '.join(sector['drivers'])}. Top picks: {', '.join(sector['top_picks'])}. Risk: {sector['risk'].title()}."
        if "bank" in q_lower or "financial" in q_lower or "firstrand" in q_lower or "standard" in q_lower:
            sector = picks["financials"]
            return f"Financials outlook: {sector['outlook'].title()}. Key drivers: {', '.join(sector['drivers'])}. Top picks: {', '.join(sector['top_picks'])}. Risk: {sector['risk'].title()}."
        if "property" in q_lower or "reit" in q_lower or "growthpoint" in q_lower:
            sector = picks["property"]
            return f"Property outlook: {sector['outlook'].title()}. Key drivers: {', '.join(sector['drivers'])}. Top picks: {', '.join(sector['top_picks'])}. Risk: {sector['risk'].title()}."
        if "tech" in q_lower or "naspers" in q_lower or "prosus" in q_lower or "tencent" in q_lower:
            sector = picks["tech"]
            return f"Tech outlook: {sector['outlook'].title()}. Key drivers: {', '.join(sector['drivers'])}. Top picks: {', '.join(sector['top_picks'])}. Risk: {sector['risk'].title()}."
        # General JSE
        strategies = AI_ADVISOR_KNOWLEDGE["stokvel_strategies"]
        return f"For a {user_risk} risk profile, here's a proven stokvel strategy: {'; '.join(strategies)}. Want me to analyse a specific sector?"

    # Risk profile
    if any(w in q_lower for w in ["risk", "conservative", "moderate", "aggressive", "safe"]):
        profile = AI_ADVISOR_KNOWLEDGE["risk_profiles"].get(user_risk, AI_ADVISOR_KNOWLEDGE["risk_profiles"]["moderate"])
        return f"Your current profile is **{user_risk.title()}**. Recommended allocation: Bonds {profile['allocation']['bonds']}%, Cash {profile['allocation']['cash']}%, Equity {profile['allocation']['equity']}%, Crypto {profile['allocation']['crypto']}%. Expected return: {profile['expected_return']}."

    # Statement analysis
    if any(w in q_lower for w in ["statement", "bank", "spending", "income", "expense", "budget"]):
        if statement.get("total_income", 0) > 0:
            return f"From your bank statements: Income R{statement['total_income']:,.2f}, Expenses R{statement['total_expenses']:,.2f}, Net R{statement['net_flow']:,.2f}. I detected {statement.get('contribution_count', 0)} Khula contributions."
        return "Upload your FNB statement on the Bank Sync page and I'll analyse your spending patterns and contribution capacity."

    # Market / general
    if any(w in q_lower for w in ["market", "rand", "usd", "interest rate", "sarb", "inflation", "economy"]):
        return f"Latest SA market: JSE All Share {SA_MARKET_DATASET['jse_allshare']['value']:,} ({SA_MARKET_DATASET['jse_allshare']['change']:+.1f}%), USD/ZAR R{SA_MARKET_DATASET['usd_zar']['value']:.2f}, SARB rate {SA_MARKET_DATASET['sarb_rate']['value']:.2f}%. Gold is at R{SA_MARKET_DATASET['gold_price']['value']:,.0f}/oz."

    # FNB / Crypto
    if any(w in q_lower for w in ["fnb", "bank", "sync", "api"]):
        return "FNB Open Banking integration allows automatic transaction sync. You can also upload PDF or CSV statements. Connect on the Bank Sync page."

    if any(w in q_lower for w in ["bitcoin", "btc", "crypto", "ethereum", "eth"]):
        return "Cryptocurrency is available as a high-risk allocation (up to 15% for aggressive profiles). Consider BTC and ETH via regulated SA exchanges like Luno or VALR."

    # Fallback
    return f"I'm your Khula Collective AI Advisor. I can help with JSE stock picks, contribution tracking, portfolio allocation, and market updates. Your current risk profile: {user_risk.title()}. What would you like to explore?"

def render_ai_advisor():
    """AI Advisor page with chat interface and contextual insights."""
    track_feature_usage(st.session_state.user_id, "ai_advisor")
    st.markdown("""
    <div class='main-header'>
        <h1>🤖 AI Advisor</h1>
        <p>Smart investment insights powered by your data</p>
    </div>
    """, unsafe_allow_html=True)

    context = get_ai_context(st.session_state.user_id)

    # Context summary
    with st.expander("📊 Your Context", expanded=False):
        st.write(f"**Risk Profile:** {context['risk_profile'].title()}")
        st.write(f"**Portfolio Value:** R{context['portfolio_value']:,.2f}")
        st.write(f"**Monthly Target:** R{context['monthly_target']:,.2f}")
        st.write(f"**This Month Contributed:** R{context['this_month_contrib']:,.2f}")
        stmt = context.get("statement_summary", {})
        if stmt.get("total_income", 0) > 0:
            st.write(f"**Statement Income:** R{stmt['total_income']:,.2f}")
            st.write(f"**Statement Expenses:** R{stmt['total_expenses']:,.2f}")

    # Quick questions
    st.subheader("Quick Questions")
    quick_qs = [
        "How is my portfolio doing?",
        "What JSE stocks should I buy?",
        "Am I on track with contributions?",
        "What's the market outlook?",
        "Should I invest in property REITs?",
    ]
    qcols = st.columns(len(quick_qs))
    selected_q = None
    for col, q in zip(qcols, quick_qs):
        with col:
            if st.button(q, key=f"qq_{q[:20]}", use_container_width=True):
                selected_q = q

    # Chat interface
    st.subheader("Ask Your AI Advisor")
    user_q = st.text_input("Your question", value=selected_q or "", placeholder="e.g., What JSE stocks are good for moderate risk?")

    if st.button("Get Advice", type="primary", use_container_width=True) or selected_q:
        if user_q:
            with st.spinner("Analysing..."):
                time.sleep(0.5)
                response = generate_ai_response(user_q, context)
                save_ai_conversation(st.session_state.user_id, user_q, response, context)
            st.markdown(f"""
            <div style='background:#1e1e30;padding:1rem;border-radius:12px;border:1px solid #2a2a40;margin-top:1rem;'>
                <p style='color:#00b894;font-weight:600;margin:0;'>🤖 AI Advisor</p>
                <p style='margin:0.5rem 0 0 0;'>{response}</p>
            </div>
            """, unsafe_allow_html=True)

    # Conversation history
    history = get_ai_conversation_history(st.session_state.user_id, limit=5)
    if history:
        st.subheader("Recent Conversations")
        for q, r, created in history:
            with st.expander(f"🧑 {q[:60]}..."):
                st.write(f"**AI:** {r}")
                st.caption(f"{created[:16] if created else ''}")

def render_global_markets():
    """Dedicated Global Markets Explorer — browse all investable assets worldwide."""
    track_feature_usage(st.session_state.user_id, "global_markets")
    st.markdown("""
    <div class='main-header'>
        <h1>🌍 Global Markets</h1>
        <p>Explore investment opportunities across JSE, NYSE, LSE, crypto &amp; commodities</p>
    </div>
    """, unsafe_allow_html=True)

    # Bank balance for affordability
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(current_value), 0) FROM Investments")
    portfolio_value = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE status='paid'")
    total_contributions = c.fetchone()[0] or 0
    conn.close()
    bank_balance = portfolio_value + total_contributions

    # ── Filters ─────────────────────────────────────────────
    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        region_filter = st.multiselect("Region", ["SA", "US", "EU", "EM", "Crypto", "Commodity"], default=[])
    with f2:
        risk_filter = st.multiselect("Risk", ["low", "medium", "high"], default=[])
    with f3:
        cat_filter = st.multiselect("Category", ["stock", "etf", "crypto", "commodity"], default=[])
    with f4:
        sort_by = st.selectbox("Sort", ["Name", "Price (High-Low)", "Price (Low-High)", "Region"], index=0)

    # ── Fetch / Mock Data ───────────────────────────────────
    assets = []
    for t in GLOBAL_TICKER_UNIVERSE:
        if region_filter and t["region"] not in region_filter:
            continue
        if risk_filter and t["risk_level"] not in risk_filter:
            continue
        if cat_filter and t["category"] not in cat_filter:
            continue

        mock = _get_mock_market_data(t)
        price_zar = _convert_to_zar(mock["price_usd"], t["region"])
        afford = _calculate_affordability_cards(price_zar, bank_balance)

        assets.append({
            **t,
            "price_usd": mock["price_usd"],
            "price_zar": price_zar,
            "change_pct": mock["change_pct"],
            "pe_ratio": mock["pe_ratio"],
            "dividend_yield": mock["dividend_yield"],
            "market_cap": _format_market_cap(mock["market_cap"]),
            "affordability": afford,
        })

    if sort_by == "Price (High-Low)":
        assets.sort(key=lambda x: x["price_zar"] or 0, reverse=True)
    elif sort_by == "Price (Low-High)":
        assets.sort(key=lambda x: x["price_zar"] or float('inf'))
    elif sort_by == "Region":
        assets.sort(key=lambda x: x["region"])
    else:
        assets.sort(key=lambda x: x["name"])

    if not assets:
        st.info("No assets match your filters. Try adjusting your criteria.")
        return

    # ── Summary ─────────────────────────────────────────────
    st.markdown(f"""
    <p style='color:#a0a0b0;font-size:0.9rem;'>
        Showing <strong>{len(assets)}</strong> assets 
        &middot; Estimated balance: <strong>R{bank_balance:,.0f}</strong>
    </p>
    """, unsafe_allow_html=True)

    # ── Asset Cards ─────────────────────────────────────────
    grouped = _group_by_region(assets)
    for region, group in grouped.items():
        st.subheader(f"{_get_region_flag(region)} {_get_region_name(region)}")
        cols = st.columns(2)
        for i, a in enumerate(group):
            with cols[i % 2]:
                change_color = "#2ed573" if a["change_pct"] >= 0 else "#ff4757"
                change_sign = "+" if a["change_pct"] >= 0 else ""
                price_display = f"R{a['price_zar']:,.2f}" if a["price_zar"] else "N/A"

                afford_html = ""
                if a["affordability"] and a["affordability"]["units_affordable"] > 0:
                    afford_html = f"<p style='font-size:0.8rem;color:#00b894;margin:0;'>💰 You can afford <strong>{a['affordability']['units_affordable']}</strong> units (R{a['affordability']['total_cost_zar']:,.0f})</p>"
                elif a["affordability"]:
                    afford_html = f"<p style='font-size:0.8rem;color:#ff4757;margin:0;'>⚠️ Requires R{a['price_zar']:,.0f} per unit — beyond 80% balance limit</p>"

                pe_display = f"P/E: {a['pe_ratio']:.1f}" if a['pe_ratio'] else ""
                div_display = f"Div: {a['dividend_yield']:.1f}%" if a['dividend_yield'] else ""
                meta = " &middot; ".join(filter(None, [a["exchange"], pe_display, div_display, a["market_cap"]]))

                st.markdown(f"""
                <div style='background:#1e1e30;padding:1rem;border-radius:14px;border:1px solid #2a2a40;margin-bottom:0.75rem;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <span style='font-weight:700;font-size:1rem;'>{a['name']}</span>
                        {_risk_badge(a['risk_level'])}
                    </div>
                    <p style='font-size:0.8rem;color:#a0a0b0;margin:0;'>{a['ticker']} &middot; {meta}</p>
                    <div style='display:flex;justify-content:space-between;align-items:center;margin-top:0.5rem;'>
                        <span style='font-size:1.3rem;font-weight:700;color:#ffffff;'>{price_display}</span>
                        <span style='color:{change_color};font-weight:600;'>{change_sign}{a['change_pct']:.2f}%</span>
                    </div>
                    {afford_html}
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"View {a['name']}", key=f"view_{a['ticker']}", use_container_width=True):
                    st.session_state.selected_ticker = a
                    st.info(f"Selected {a['name']} ({a['ticker']}) at {price_display}. This would open a detail view in production.")

# End of khula_pages1.py
