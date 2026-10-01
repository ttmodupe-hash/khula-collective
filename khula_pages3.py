def render_notifications():
    track_feature_usage(st.session_state.user_id, "notifications")
    st.markdown("<h2>Notifications</h2>", unsafe_allow_html=True)

    notifications = get_notifications(st.session_state.user_id)
    if notifications:
        for nid, title, message, ntype, is_read, created_at in notifications:
            bg = "#1e1e3a" if is_read else "#2a2a50"
            border_color = "#6366f1" if is_read else "#00b894"
            st.markdown(f"""
            <div class='notification-item' style='background: {bg}; border-left-color: {border_color};'>
                <div style='display: flex; justify-content: space-between;'>
                    <strong style='color: #e0e0e0;'>{title}</strong>
                    <span style='color: #8892b0; font-size: 0.75rem;'>{created_at}</span>
                </div>
                <p style='color: #8892b0; margin: 0.3rem 0 0 0; font-size: 0.9rem;'>{message}</p>
            </div>
            """, unsafe_allow_html=True)
            if not is_read:
                if st.button("Mark as Read", key=f"read_{nid}"):
                    mark_notification_read(nid)
                    st.rerun()
    else:
        st.info("No notifications yet")

# ============================================================
# REPORTS (v3.1 - Statement-Based Analytics)
# ============================================================

def render_reports():
    track_feature_usage(st.session_state.user_id, "reports")
    st.markdown("<h2>Reports & Analytics</h2>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Contribution Report", "💳 Statement Analytics", "📈 Portfolio Analysis", "📥 Export Data"])

    # === Tab 1: Contribution Report ===
    with tab1:
        st.markdown("<h3>Contribution Report</h3>", unsafe_allow_html=True)
        conn = sqlite3.connect(DB_PATH)
        df_contrib = pd.read_sql_query("""
            SELECT u.full_name, c.year, c.month, c.amount, c.status, c.payment_date
            FROM Monthly_Contributions c JOIN Users u ON c.user_id = u.user_id
            ORDER BY c.year DESC, c.month DESC
        """, conn)
        conn.close()

        if not df_contrib.empty:
            st.dataframe(df_contrib, use_container_width=True, hide_index=True)

            # Monthly trend chart
            monthly_summary = df_contrib.groupby(['year', 'month'])['amount'].sum().reset_index()
            monthly_summary['period'] = monthly_summary['year'].astype(str) + '-' + monthly_summary['month'].astype(str).str.zfill(2)
            fig = px.bar(monthly_summary, x='period', y='amount', title='Monthly Collections',
                         color_discrete_sequence=['#6366f1'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No contribution data yet")

    # === Tab 2: Statement Analytics ===
    with tab2:
        st.markdown("<h3>Statement-Based Analytics</h3>", unsafe_allow_html=True)

        conn = sqlite3.connect(DB_PATH)
        df_txns = pd.read_sql_query("""
            SELECT transaction_date, description, amount, type, category
            FROM Bank_Transactions
            WHERE user_id = ?
            ORDER BY transaction_date DESC
        """, conn, params=(st.session_state.user_id,))
        conn.close()

        if df_txns.empty:
            st.info("No statement transactions yet. Go to **FNB Bank Sync** and upload a PDF or CSV bank statement to see analytics here.")
        else:
            # Summary metrics
            total_income = df_txns[df_txns['type'] == 'credit']['amount'].sum()
            total_expense = df_txns[df_txns['type'] == 'debit']['amount'].sum()
            net_flow = total_income - total_expense
            savings_rate = (net_flow / total_income * 100) if total_income > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Income</div><div class='metric-value' style='color:#00b894;'>R{total_income:,.0f}</div></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Expenses</div><div class='metric-value' style='color:#e74c3c;'>R{total_expense:,.0f}</div></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Net Flow</div><div class='metric-value' style='color:{\"#00b894\" if net_flow >= 0 else \"#e74c3c\"};'>R{net_flow:,.0f}</div></div>", unsafe_allow_html=True)
            with c4:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Savings Rate</div><div class='metric-value' style='color:{\"#00b894\" if savings_rate > 20 else \"#fdcb6e\"};'>{savings_rate:.1f}%</div></div>", unsafe_allow_html=True)

            # Category breakdown pie chart
            st.markdown("<h4>Spending by Category</h4>", unsafe_allow_html=True)
            cat_summary = df_txns[df_txns['type'] == 'debit'].groupby('category')['amount'].sum().reset_index()
            if not cat_summary.empty:
                fig = px.pie(cat_summary, values='amount', names='category', hole=0.4,
                             color_discrete_sequence=px.colors.sequential.Plasma)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No categorized expenses yet")

            # Monthly trend line chart
            st.markdown("<h4>Income vs Expenses Trend</h4>", unsafe_allow_html=True)
            df_txns['month'] = pd.to_datetime(df_txns['transaction_date'], errors='coerce').dt.to_period('M').astype(str)
            monthly = df_txns.groupby(['month', 'type'])['amount'].sum().unstack(fill_value=0).reset_index()
            if 'credit' in monthly.columns and 'debit' in monthly.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['credit'], mode='lines+markers', name='Income', line=dict(color='#00b894')))
                fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['debit'], mode='lines+markers', name='Expenses', line=dict(color='#e74c3c')))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation='h', yanchor='bottom', y=1.02))
                st.plotly_chart(fig, use_container_width=True)

            # Transaction table
            st.markdown("<h4>All Transactions</h4>", unsafe_allow_html=True)
            st.dataframe(df_txns.sort_values('transaction_date', ascending=False), use_container_width=True, hide_index=True)

    # === Tab 3: Portfolio Analysis ===
    with tab3:
        st.markdown("<h3>Portfolio Analysis</h3>", unsafe_allow_html=True)
        conn = sqlite3.connect(DB_PATH)
        df_inv = pd.read_sql_query("SELECT name, type, amount_invested, current_value, return_pct FROM Investments", conn)
        conn.close()

        if not df_inv.empty:
            total_invested = df_inv['amount_invested'].sum()
            total_current = df_inv['current_value'].sum()
            overall_return = ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Total Invested</div><div class='metric-value'>R{total_invested:,.0f}</div></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Current Value</div><div class='metric-value'>R{total_current:,.0f}</div></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='metric-card'><div class='metric-label'>Overall Return</div><div class='metric-value' style='color:{\"#00b894\" if overall_return >= 0 else \"#e74c3c\"};'>{overall_return:+.1f}%</div></div>", unsafe_allow_html=True)

            # Return by investment bar chart
            fig = px.bar(df_inv, x='name', y='return_pct', color='return_pct',
                         color_continuous_scale=['#e74c3c', '#fdcb6e', '#00b894'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No investments recorded yet")

    # === Tab 4: Export ===
    with tab4:
        st.markdown("<h3>Export Data</h3>", unsafe_allow_html=True)

        conn = sqlite3.connect(DB_PATH)
        export_options = {
            "Contributions": "SELECT * FROM Monthly_Contributions",
            "Transactions": "SELECT * FROM Bank_Transactions WHERE user_id=?",
            "Investments": "SELECT * FROM Investments",
            "Suggestions": "SELECT * FROM Suggestions",
        }

        for label, query in export_options.items():
            if "?" in query:
                df = pd.read_sql_query(query, conn, params=(st.session_state.user_id,))
            else:
                df = pd.read_sql_query(query, conn)
            if not df.empty:
                csv = df.to_csv(index=False)
                st.download_button(f"📥 Download {label} (CSV)", data=csv, file_name=f"khula_{label.lower()}.csv", mime="text/csv", key=f"dl_{label}")
        conn.close()

def render_whatsapp():
    track_feature_usage(st.session_state.user_id, "whatsapp")
    st.markdown("<h2>WhatsApp Integration</h2>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background: #1e1e3a; padding: 1.5rem; border-radius: 12px; border: 1px solid #2a2a50; text-align: center;'>
        <div style='font-size: 3rem; margin-bottom: 1rem;'>💬</div>
        <h3 style='color: #e0e0e0; margin-bottom: 0.5rem;'>WhatsApp Group Chat</h3>
        <p style='color: #8892b0; margin-bottom: 1.5rem;'>Connect with your investment club members</p>
        <a href='https://wa.me/?text=Join%20Khula%20Collective' target='_blank' style='text-decoration: none;'>
            <div style='background: #00b894; color: white; padding: 0.8rem 2rem; border-radius: 8px; display: inline-block; font-weight: 600;'>
                Open WhatsApp
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h3 style='margin-top: 2rem;'>Quick Actions</h3>", unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        if st.button("📢 Share Portfolio Update", use_container_width=True):
            st.success("Portfolio summary copied to clipboard (simulated)")
    with cols[1]:
        if st.button("💰 Share Contribution Link", use_container_width=True):
            st.success("Payment link shared (simulated)")
    with cols[2]:
        if st.button("📊 Share Market News", use_container_width=True):
            st.success("Latest market news shared (simulated)")

def render_profile():
    track_feature_usage(st.session_state.user_id, "profile")
    st.markdown("<h2>My Profile</h2>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT full_name, email, phone, bank_account, monthly_contribution, risk_profile, theme_preference FROM Users WHERE user_id=?", (st.session_state.user_id,))
    user = c.fetchone()
    conn.close()

    if user:
        full_name, email, phone, bank_account, monthly, risk_profile, theme = user
        with st.form("profile_form"):
            st.text_input("Full Name", value=full_name, key="prof_name")
            st.text_input("Email", value=email or "", key="prof_email")
            st.text_input("Phone", value=phone or "", key="prof_phone")
            st.text_input("Bank Account", value=bank_account or "", key="prof_bank")
            st.number_input("Monthly Contribution (R)", value=float(monthly), min_value=100.0, step=50.0, key="prof_contrib")
            st.selectbox("Risk Profile", ["conservative", "moderate", "aggressive"], index=["conservative", "moderate", "aggressive"].index(risk_profile), key="prof_risk")
            if st.form_submit_button("Update Profile", use_container_width=True):
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("UPDATE Users SET full_name=?, email=?, phone=?, bank_account=?, monthly_contribution=?, risk_profile=? WHERE user_id=?",
                          (st.session_state.prof_name, st.session_state.prof_email, st.session_state.prof_phone,
                           st.session_state.prof_bank, st.session_state.prof_contrib, st.session_state.prof_risk, st.session_state.user_id))
                conn.commit()
                conn.close()
                st.success("Profile updated!")

        # Theme toggle
        current_theme = st.session_state.get("theme", "dark")
        if st.button(f"🌙 Switch to {'Light' if current_theme == 'dark' else 'Dark'} Theme", use_container_width=True):
            new_theme = toggle_theme(st.session_state.user_id, current_theme)
            st.session_state.theme = new_theme
            st.rerun()

def render_admin():
    if st.session_state.role != "admin":
        st.error("Admin access only")
        return
    track_feature_usage(st.session_state.user_id, "admin")
    st.markdown("<h2>Admin Panel</h2>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Member management
    st.markdown("<h3>Members</h3>", unsafe_allow_html=True)
    c.execute("SELECT user_id, full_name, username, role, is_active, monthly_contribution, risk_profile FROM Users")
    members = c.fetchall()
    df_members = pd.DataFrame(members, columns=["ID", "Name", "Username", "Role", "Active", "Monthly", "Risk"])
    st.dataframe(df_members, use_container_width=True, hide_index=True)

    # Feature usage stats
    st.markdown("<h3>Feature Usage Stats</h3>", unsafe_allow_html=True)
    df_usage = pd.read_sql_query("""
        SELECT u.full_name, f.feature_id, COUNT(*) as uses
        FROM Feature_Usage f JOIN Users u ON f.user_id = u.user_id
        GROUP BY f.user_id, f.feature_id
        ORDER BY uses DESC
    """, conn)
    if not df_usage.empty:
        st.dataframe(df_usage, use_container_width=True, hide_index=True)

    # Announcements
    st.markdown("<h3>Post Announcement</h3>", unsafe_allow_html=True)
    with st.form("announcement"):
        title = st.text_input("Title")
        content = st.text_area("Content")
        priority = st.selectbox("Priority", ["normal", "high", "urgent"])
        if st.form_submit_button("Post"):
            c.execute("INSERT INTO Announcements (title, content, posted_by, priority) VALUES (?,?,?,?)",
                      (title, content, st.session_state.user_id, priority))
            conn.commit()
            st.success("Announcement posted!")

    conn.close()
