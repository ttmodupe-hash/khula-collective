def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 3rem 0;'>
            <div style='font-size: 4rem; margin-bottom: 1rem;'>🏛️</div>
            <h1 style='font-size: 2.5rem; margin-bottom: 0.5rem;'>Khula Collective</h1>
            <p style='color: #8892b0; font-size: 1.1rem; margin-bottom: 2rem;'>South African Investment Club Platform</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                user = authenticate(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_id = user["user_id"]
                    st.session_state.username = user["username"]
                    st.session_state.full_name = user["full_name"]
                    st.session_state.role = user["role"]
                    st.session_state.theme = user["theme"]
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        st.markdown("""
        <div style='text-align: center; margin-top: 2rem; padding: 1.5rem; background: #1e1e3a; border-radius: 12px; border: 1px solid #2a2a50;'>
            <p style='color: #8892b0; margin: 0; font-size: 0.9rem;'>Demo Accounts</p>
            <p style='color: #6366f1; margin: 0.5rem 0 0 0; font-size: 0.85rem;'>admin / admin123  |  siphoo / password1</p>
        </div>
        """, unsafe_allow_html=True)

def render_dashboard():
    track_feature_usage(st.session_state.user_id, "dashboard")
    st.markdown("<h2>Dashboard</h2>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Portfolio metrics
    c.execute("SELECT COALESCE(SUM(current_value), 0), COALESCE(SUM(amount_invested), 0) FROM Investments")
    total_value, total_invested = c.fetchone()
    total_return = ((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0

    c.execute("SELECT COUNT(*) FROM Users WHERE is_active=1")
    member_count = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE year=? AND month=?", (datetime.now().year, datetime.now().month))
    monthly_collected = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM Suggestions WHERE status='open'")
    open_suggestions = c.fetchone()[0]

    cols = st.columns(4)
    metrics = [
        ("Portfolio Value", f"R{total_value:,.0f}", "#6366f1"),
        ("Total Return", f"{total_return:+.1f}%", "#00b894" if total_return >= 0 else "#e74c3c"),
        ("Active Members", str(member_count), "#fdcb6e"),
        ("This Month", f"R{monthly_collected:,.0f}", "#74b9ff"),
    ]
    for i, (label, value, color) in enumerate(metrics):
        with cols[i]:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value' style='color: {color};'>{value}</div>
            </div>
            """, unsafe_allow_html=True)

    # Portfolio breakdown
    c.execute("SELECT type, COALESCE(SUM(current_value), 0) FROM Investments GROUP BY type")
    portfolio_data = c.fetchall()
    conn.close()

    if portfolio_data:
        st.markdown("<h3>Portfolio Allocation</h3>", unsafe_allow_html=True)
        df_portfolio = pd.DataFrame(portfolio_data, columns=["Type", "Value"])
        fig = px.pie(df_portfolio, values="Value", names="Type", hole=0.5,
                     color_discrete_sequence=px.colors.sequential.Plasma)
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # News feed
    st.markdown("<h3>Market News</h3>", unsafe_allow_html=True)
    for news in SA_NEWS_HEADLINES[:5]:
        st.markdown(f"""
        <div style='background: #1e1e3a; padding: 0.8rem; border-radius: 8px; margin: 0.3rem 0; border-left: 3px solid #6366f1;'>
            <p style='margin: 0; color: #e0e0e0; font-size: 0.9rem;'>📰 {news}</p>
        </div>
        """, unsafe_allow_html=True)

def render_fnb_sync():
    track_feature_usage(st.session_state.user_id, "fnb_sync")
    st.markdown("<h2>FNB Bank Sync</h2>", unsafe_allow_html=True)

    # API Status
    status_color = "#00b894" if FNB_ENABLED else "#fdcb6e"
    status_text = "Connected" if FNB_ENABLED else "Simulated Mode"
    st.markdown(f"""
    <div style='background: #1e1e3a; padding: 1rem; border-radius: 12px; border: 1px solid #2a2a50; margin-bottom: 1.5rem;'>
        <div style='display: flex; align-items: center; gap: 0.5rem;'>
            <div style='width: 12px; height: 12px; border-radius: 50%; background: {status_color};'></div>
            <span style='color: #e0e0e0; font-weight: 600;'>FNB API Status: {status_text}</span>
        </div>
        <p style='color: #8892b0; margin: 0.5rem 0 0 0; font-size: 0.85rem;'>
            {'Live API connection active' if FNB_ENABLED else 'Running in simulated mode. Upload statements below for real transaction data.'}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Simulated sync button
    if not FNB_ENABLED:
        if st.button("🔄 Run Simulated Sync", type="primary"):
            with st.spinner("Syncing with FNB..."):
                time.sleep(2)
                client = FNBAPIClient()
                success, msg = client.connect(FNB_CLIENT_ID, FNB_CLIENT_SECRET)
                if success:
                    transactions = client.get_transactions("demo_account", "2024-01-01", datetime.now().strftime("%Y-%m-%d"))
                    synced = client.sync_contributions(st.session_state.user_id, transactions)
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("INSERT INTO FNB_Sync_Log (user_id, sync_type, status, transactions_synced) VALUES (?,?,?,?)",
                              (st.session_state.user_id, "simulated", "success", synced))
                    conn.commit()
                    conn.close()
                    st.success(f"Simulated sync complete! {synced} contributions synced.")
                    add_notification(st.session_state.user_id, "FNB Sync", f"{synced} transactions synced", "success")

    # Sync history
    st.markdown("<h3>Sync History</h3>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df_sync = pd.read_sql_query("SELECT synced_at, sync_type, status, transactions_synced FROM FNB_Sync_Log WHERE user_id=? ORDER BY synced_at DESC LIMIT 10",
                                 conn, params=(st.session_state.user_id,))
    conn.close()
    if not df_sync.empty:
        st.dataframe(df_sync, use_container_width=True, hide_index=True)
    else:
        st.info("No sync history yet")

    # ============================================================
    # STATEMENT UPLOAD (v3.1)
    # ============================================================
    st.markdown("<h3>📄 Upload Bank Statement</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div style='background: #1e1e3a; padding: 1rem; border-radius: 12px; border: 1px solid #2a2a50; margin-bottom: 1rem;'>
        <p style='color: #8892b0; margin: 0;'>
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
            preview_df = pd.DataFrame(transactions[:5])
            st.markdown("<p style='color: #8892b0;'>Preview:</p>", unsafe_allow_html=True)
            st.dataframe(preview_df, use_container_width=True, hide_index=True)

            if st.button("💾 Save All Transactions", type="primary"):
                saved = save_parsed_transactions(st.session_state.user_id, transactions, "statement_upload")
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
    st.markdown("<h2>Payment Progress</h2>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    current_year = datetime.now().year
    current_month = datetime.now().month

    c.execute("SELECT user_id, full_name, monthly_contribution FROM Users WHERE is_active=1 ORDER BY user_id")
    members = c.fetchall()

    st.markdown("<h3>Current Month Status</h3>", unsafe_allow_html=True)
    for uid, name, monthly in members:
        c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE user_id=? AND year=? AND month=?", (uid, current_year, current_month))
        paid = c.fetchone()[0] or 0
        progress = min(paid / monthly * 100, 100) if monthly > 0 else 0
        status_color = "#00b894" if progress >= 100 else "#fdcb6e" if progress >= 50 else "#e74c3c"
        status_text = "Paid" if progress >= 100 else "Partial" if progress > 0 else "Not Paid"

        st.markdown(f"""
        <div style='background: #1e1e3a; padding: 1rem; border-radius: 12px; margin: 0.5rem 0; border: 1px solid #2a2a50;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <span style='font-weight: 600; color: #e0e0e0;'>{name}</span>
                <span style='color: {status_color}; font-weight: 600;'>{status_text}</span>
            </div>
            <div class='progress-bar' style='margin-top: 0.5rem;'>
                <div class='progress-fill' style='width: {progress}%; background: {status_color};'></div>
            </div>
            <p style='color: #8892b0; margin: 0.3rem 0 0 0; font-size: 0.8rem;'>R{paid:,.0f} / R{monthly:,.0f} ({progress:.0f}%)</p>
        </div>
        """, unsafe_allow_html=True)

    # Historical arrears
    st.markdown("<h3>Year-to-Date Arrears</h3>", unsafe_allow_html=True)
    arrears_data = []
    for uid, name, monthly in members:
        for month in range(1, current_month + 1):
            c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE user_id=? AND year=? AND month=?", (uid, current_year, month))
            paid = c.fetchone()[0] or 0
            if paid < monthly:
                arrears_data.append({"Member": name, "Month": MONTHS[month-1], "Expected": monthly, "Paid": paid, "Behind": monthly - paid})

    conn.close()

    if arrears_data:
        df_arrears = pd.DataFrame(arrears_data)
        st.dataframe(df_arrears, use_container_width=True, hide_index=True)
    else:
        st.success("No arrears! All members are up to date.")

# ============================================================
# AI ADVISOR (v3.1 - Smart Contextual AI)
# ============================================================

def generate_ai_response(question, context):
    q = question.lower()
    risk = context.get("risk_profile", "moderate")
    portfolio = context.get("portfolio_value", 0)
    stmt = context.get("statement_summary", {})
    name = context.get("user_name", "Member")

    if any(kw in q for kw in ["arrear", "behind", "missed payment", "not paid"]):
        return f"Hi {name}, I can see your contribution status. If you're behind, consider setting up a debit order for the 1st of each month. The club's monthly target is R{context['monthly_target']:,.0f}. Members who fall behind miss out on compound growth in the collective pool."

    elif any(kw in q for kw in ["invest", "stock", "share", "jse", "buy", "sell"]):
        sector = AI_ADVISOR_KNOWLEDGE["jse_sectors"]
        if "resource" in q or "mining" in q or "gold" in q or "platinum" in q:
            s = sector["resources"]
            return f"Resources outlook is **{s['outlook']}** driven by {', '.join(s['drivers'])}. Top picks: {', '.join(s['top_picks'])}. Risk level: {s['risk']}. Given your {risk} profile, a 10-15% allocation to resources makes sense."
        elif "bank" in q or "financial" in q or "absa" in q or "nedbank" in q:
            s = sector["financials"]
            return f"Financials are **{s['outlook']}** with **{s['risk']} risk**. {', '.join(s['drivers'])}. Consider: {', '.join(s['top_picks'])}. Banking prefs offer 8-10% yield with low volatility."
        elif "property" in q or "reit" in q:
            s = sector["property"]
            return f"Property is **{s['outlook']}** with {', '.join(s['drivers'])}. Top REITs: {', '.join(s['top_picks'])}. The interest rate pause is helping office vacancies decline."
        elif "tech" in q or "naspers" in q or "prosus" in q:
            s = sector["tech"]
            return f"Tech/Naspers is **{s['outlook']}** — high volatility but the NAV discount to Tencent offers value. {', '.join(s['drivers'])}. Only suitable for aggressive investors."
        else:
            strategies = AI_ADVISOR_KNOWLEDGE["stokvel_strategies"]
            return f"For a **{risk}** risk profile, consider this allocation: " + " ".join(strategies[:2]) + f" Your club portfolio is currently R{portfolio:,.0f}."

    elif any(kw in q for kw in ["statement", "transaction", "spend", "income", "expense", "budget"]):
        if stmt.get("total_income", 0) > 0:
            savings_rate = ((stmt['net_flow']) / stmt['total_income'] * 100) if stmt['total_income'] > 0 else 0
            return f"From your uploaded statements: Total income **R{stmt['total_income']:,.0f}**, expenses **R{stmt['total_expenses']:,.0f}**, net flow **R{stmt['net_flow']:,.0f}**. Savings rate: **{savings_rate:.1f}%**. You have {stmt['contribution_count']} contribution transactions detected. {'Great savings discipline!' if savings_rate > 20 else 'Consider reducing discretionary spending to boost your contribution capacity.'}"
        else:
            return "Upload a bank statement in the FNB Sync page and I can analyze your spending patterns, detect contributions, and suggest ways to increase your monthly investment capacity."

    elif any(kw in q for kw in ["risk", "profile", "conservative", "aggressive", "moderate"]):
        rp = AI_ADVISOR_KNOWLEDGE["risk_profiles"].get(risk, {})
        alloc = rp.get("allocation", {})
        alloc_str = ", ".join([f"{k}: {v}%" for k, v in alloc.items()])
        return f"Your profile: **{risk.title()}**. Suggested allocation: {alloc_str}. Expected annual return: **{rp.get('expected_return', '10-15%')}**. Based on your statement data, you can afford a R{context['monthly_target']:,.0f} monthly contribution."

    elif any(kw in q for kw in ["market", "news", "economy", "rand", "interest rate", "inflation", "gdp"]):
        m = SA_MARKET_DATASET
        return f"**SA Market Snapshot** (live data): JSE All Share **{m['jse_allshare']['value']:,}** ({m['jse_allshare']['change']:+.1f}%), SARB Repo Rate **{m['sarb_rate']['value']}%,** USD/ZAR **R{m['usd_zar']['value']}**, Gold **R{m['gold_price']['value']:,}/oz**, Brent Oil **${m['brent_oil']['value']}**. The rand is {m['usd_zar']['trend']} against the dollar."

    elif any(kw in q for kw in ["stokvel", "pool", "collective", "club", "group"]):
        return f"South African stokvels manage over **R50 billion** annually. Your club portfolio is **R{portfolio:,.0f}**. Best practice for a {risk} profile: diversify 40% JSE ETFs, 30% SARB bonds, 20% cash, 10% stock picks. The power of collective investing is compound growth — your contributions grow with the group."

    elif any(kw in q for kw in ["hello", "hi", "hey", "help", "what can you do"]):
        return f"Hello {name}! I'm your Khula AI Advisor. I can help you with: **JSE stock analysis**, **portfolio strategy**, **market conditions**, **contribution tracking**, and **personalized investment advice** based on your risk profile ({risk}). Upload a bank statement for spending analysis, or ask me about any stock!"

    else:
        return f"Hi {name}! I'm analyzing your question in the context of your {risk} risk profile and R{portfolio:,.0f} club portfolio. For JSE stocks, try asking 'Should I invest in mining?' or 'What about property REITs?' For personal insights, upload a bank statement in FNB Sync. Current SARB rate is {SA_MARKET_DATASET['sarb_rate']['value']}%."

def render_ai_advisor():
    track_feature_usage(st.session_state.user_id, "ai_advisor")
    st.markdown("<h2>AI Investment Advisor</h2>", unsafe_allow_html=True)

    # Get user context
    context = get_ai_context(st.session_state.user_id)

    # SA Market Dashboard
    st.markdown("<h3>📊 South African Market Dashboard</h3>", unsafe_allow_html=True)
    m = SA_MARKET_DATASET
    cols = st.columns(5)
    market_metrics = [
        ("JSE All Share", f"{m['jse_allshare']['value']:,}", f"{m['jse_allshare']['change']:+.1f}%", "#6366f1"),
        ("SARB Rate", f"{m['sarb_rate']['value']}%", "Flat", "#fdcb6e"),
        ("USD/ZAR", f"R{m['usd_zar']['value']}", f"{m['usd_zar']['change']:+.1f}%", "#00b894"),
        ("Gold", f"R{m['gold_price']['value']:,}", f"{m['gold_price']['change']:+.1f}%", "#ffd700"),
        ("Brent Oil", f"${m['brent_oil']['value']}", f"{m['brent_oil']['change']:+.1f}%", "#74b9ff"),
    ]
    for i, (label, value, change, color) in enumerate(market_metrics):
        with cols[i]:
            st.markdown(f"""
            <div class='metric-card' style='text-align: center; padding: 1rem;'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value' style='color: {color}; font-size: 1.5rem;'>{value}</div>
                <div style='color: {"#00b894" if "+" in change else "#e74c3c" if "-" in change else "#8892b0"}; font-size: 0.8rem;'>{change}</div>
            </div>
            """, unsafe_allow_html=True)

    # Sector Outlook Cards
    st.markdown("<h3>🏭 Sector Outlook</h3>", unsafe_allow_html=True)
    sector_cols = st.columns(4)
    sectors = AI_ADVISOR_KNOWLEDGE["jse_sectors"]
    sector_colors = {"positive": "#00b894", "stable": "#74b9ff", "recovering": "#fdcb6e", "volatile": "#e74c3c"}
    for i, (name, data) in enumerate(sectors.items()):
        with sector_cols[i]:
            color = sector_colors.get(data["outlook"], "#6366f1")
            st.markdown(f"""
            <div class='feature-card' style='border-left: 4px solid {color};'>
                <div style='font-size: 1.2rem; font-weight: 700; color: {color}; text-transform: uppercase;'>{name}</div>
                <div style='color: #e0e0e0; font-size: 0.9rem; margin: 0.3rem 0;'>Outlook: <strong>{data['outlook'].title()}</strong></div>
                <div style='color: #8892b0; font-size: 0.8rem;'>Risk: {data['risk'].title()}</div>
                <div style='color: #8892b0; font-size: 0.75rem; margin-top: 0.3rem;'>{', '.join(data['top_picks'][:2])}</div>
            </div>
            """, unsafe_allow_html=True)

    # AI Chat Interface
    st.markdown("<h3>💬 Ask Your AI Advisor</h3>", unsafe_allow_html=True)

    # Show statement context hint
    stmt = context.get("statement_summary", {})
    if stmt.get("total_income", 0) > 0:
        st.markdown(f"""
        <div style='background: #1e1e3a; padding: 0.8rem; border-radius: 8px; border: 1px solid #2a2a50; margin-bottom: 1rem;'>
            <p style='color: #00b894; margin: 0; font-size: 0.85rem;'>📄 Statement data active: R{stmt['total_income']:,.0f} income, R{stmt['total_expenses']:,.0f} expenses detected</p>
        </div>
        """, unsafe_allow_html=True)

    # Conversation history
    history = get_ai_conversation_history(st.session_state.user_id, limit=5)
    if history:
        for q, r, ts in reversed(history):
            st.markdown(f"""
            <div style='background: #1e1e3a; padding: 0.8rem; border-radius: 8px; margin: 0.3rem 0; border-left: 3px solid #6366f1;'>
                <p style='color: #6366f1; margin: 0; font-size: 0.85rem; font-weight: 600;'>👤 {q}</p>
                <p style='color: #e0e0e0; margin: 0.3rem 0 0 0; font-size: 0.9rem;'>{r}</p>
            </div>
            """, unsafe_allow_html=True)

    # Input
    with st.form("ai_chat", clear_on_submit=True):
        question = st.text_input("Ask about investments, market, or your portfolio...", placeholder="e.g., Should we invest in mining stocks?")
        col1, col2 = st.columns([3, 1])
        with col2:
            submitted = st.form_submit_button("Ask AI", use_container_width=True, type="primary")

    if submitted and question:
        with st.spinner("Analyzing..."):
            response = generate_ai_response(question, context)
            save_ai_conversation(st.session_state.user_id, question, response, context)
        st.markdown(f"""
        <div style='background: #1e1e3a; padding: 1rem; border-radius: 12px; border: 1px solid #6366f1; margin-top: 0.5rem;'>
            <p style='color: #6366f1; margin: 0; font-size: 0.85rem; font-weight: 600;'>🤖 Khula AI</p>
            <p style='color: #e0e0e0; margin: 0.5rem 0 0 0; font-size: 0.95rem; line-height: 1.5;'>{response}</p>
        </div>
        """, unsafe_allow_html=True)

    # Quick question chips
    st.markdown("<p style='color: #8892b0; font-size: 0.85rem; margin-top: 1rem;'>Quick questions:</p>", unsafe_allow_html=True)
    quick_cols = st.columns(4)
    quick_questions = [
        "What's the JSE doing?",
        "How are my contributions?",
        "Best stocks for my risk?",
        "Analyze my statement",
    ]
    for i, qq in enumerate(quick_questions):
        with quick_cols[i]:
            if st.button(qq, key=f"qq_{i}", use_container_width=True):
                response = generate_ai_response(qq, context)
                save_ai_conversation(st.session_state.user_id, qq, response, context)
                st.markdown(f"""
                <div style='background: #1e1e3a; padding: 1rem; border-radius: 12px; border: 1px solid #6366f1; margin-top: 0.5rem;'>
                    <p style='color: #6366f1; margin: 0; font-size: 0.85rem; font-weight: 600;'>🤖 Khula AI</p>
                    <p style='color: #e0e0e0; margin: 0.5rem 0 0 0; font-size: 0.95rem; line-height: 1.5;'>{response}</p>
                </div>
                """, unsafe_allow_html=True)
