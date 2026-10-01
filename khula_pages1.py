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

# KHULA_APPEND_MARKER_7a3f9e2d
