from khula_config import *
from khula_utils import *
import json

# ============================================================
# PAGE 3: Member Voice, Constitution, Directory, Reports, Admin
# ============================================================

def render_member_voice():
    track_feature_usage(st.session_state.user_id, "member_voice")
    st.markdown("<div class='main-header'><h1>🗳️ Member Voice</h1><p>Vote on investment proposals and club decisions</p></div>", unsafe_allow_html=True)

    # Create proposal
    with st.expander("✨ Submit a New Proposal", expanded=False):
        with st.form("proposal_form"):
            title = st.text_input("Proposal Title")
            description = st.text_area("Description", height=100)
            duration = st.selectbox("Voting Duration", ["3 days", "7 days", "14 days"])
            submitted = st.form_submit_button("Submit Proposal", use_container_width=True)
            if submitted:
                if title and description:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    days = int(duration.split()[0])
                    closes = (datetime.now() + timedelta(days=days)).isoformat()
                    c.execute("INSERT INTO Proposals (title, description, proposed_by, created_at, closes_at) VALUES (?,?,?,?,?)",
                              (title, description, st.session_state.user_id, datetime.now().isoformat(), closes))
                    conn.commit()
                    proposal_id = c.lastrowid
                    conn.close()
                    add_notification(st.session_state.user_id, "Proposal Submitted", f"Your proposal '{title}' is now open for voting.", "success")
                    st.success("Proposal submitted!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please fill in all fields")

    # List proposals
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT proposal_id, title, description, proposed_by, status, created_at, closes_at, votes_for, votes_against FROM Proposals ORDER BY created_at DESC")
    proposals = c.fetchall()
    conn.close()

    if not proposals:
        st.info("No proposals yet. Be the first to submit one!")
        return

    for prop in proposals:
        pid, title, desc, proposed_by, status, created, closes, vfor, vagainst = prop
        total_votes = vfor + vagainst
        pct_for = (vfor / total_votes * 100) if total_votes > 0 else 0
        pct_against = (vagainst / total_votes * 100) if total_votes > 0 else 0

        with st.container():
            st.markdown(f"""
            <div class='arrears-card'>
                <h4>{title} <span class='payment-status {"status-paid" if status == "closed" else "status-partial"}'>{status.upper()}</span></h4>
                <p style='color:#a0a0b0;font-size:0.9rem;'>{desc}</p>
                <p style='font-size:0.8rem;color:#6c757d;'>Closes: {closes[:10] if closes else 'N/A'}</p>
            </div>
            """, unsafe_allow_html=True)

            if status == "open":
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT vote FROM Votes WHERE user_id=? AND proposal_id=?", (st.session_state.user_id, pid))
                existing = c.fetchone()
                conn.close()

                if existing:
                    st.info(f"You voted: {existing[0].upper()}")
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button(f"👍 Vote FOR", key=f"for_{pid}", use_container_width=True):
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute("INSERT INTO Votes (user_id, proposal_id, vote, voted_at) VALUES (?,?,?,?)",
                                      (st.session_state.user_id, pid, "for", datetime.now().isoformat()))
                            c.execute("UPDATE Proposals SET votes_for = votes_for + 1 WHERE proposal_id=?", (pid,))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    with c2:
                        if st.button(f"👎 Vote AGAINST", key=f"against_{pid}", use_container_width=True):
                            conn = sqlite3.connect(DB_PATH)
                            c = conn.cursor()
                            c.execute("INSERT INTO Votes (user_id, proposal_id, vote, voted_at) VALUES (?,?,?,?)",
                                      (st.session_state.user_id, pid, "against", datetime.now().isoformat()))
                            c.execute("UPDATE Proposals SET votes_against = votes_against + 1 WHERE proposal_id=?", (pid,))
                            conn.commit()
                            conn.close()
                            st.rerun()

            # Progress bars
            st.markdown(f"""
            <div style='margin-top:0.5rem;'>
                <div style='display:flex;justify-content:space-between;font-size:0.8rem;'><span>For: {vfor}</span><span>Against: {vagainst}</span></div>
                <div class='progress-container'><div class='progress-bar success' style='width:{pct_for}%;'></div></div>
            </div>
            """, unsafe_allow_html=True)

def render_constitution():
    track_feature_usage(st.session_state.user_id, "constitution")
    st.markdown("<div class='main-header'><h1>📜 Constitution</h1><p>Club rules, governance, and operating procedures</p></div>", unsafe_allow_html=True)

    sections = [
        ("Article 1: Purpose", "The Khula Collective is established to pool member contributions for collective investment, wealth building, and financial education."),
        ("Article 2: Membership", "Members must be South African citizens or permanent residents, 18 years or older, with valid FICA documentation."),
        ("Article 3: Contributions", "Monthly contributions are R500 minimum, due by the 7th of each month. Late payments incur a R50 penalty after 14 days."),
        ("Article 4: Investment Strategy", "The club invests across JSE equities, property, bonds, and approved alternative assets. All investments require majority vote."),
        ("Article 5: Governance", "Decisions are made by simple majority vote. The Admin committee manages day-to-day operations."),
        ("Article 6: Withdrawals", "Members may withdraw after 12 months with 30 days notice. Withdrawal value based on current NAV."),
        ("Article 7: Dissolution", "The club may be dissolved by 75% majority vote. Assets distributed pro-rata after settling liabilities."),
    ]

    for title, text in sections:
        with st.expander(title):
            st.write(text)

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button("📥 Download Constitution (PDF)", data=b"Khula Collective Constitution v1.0\n\n[Full legal text would go here]", file_name="khula_constitution.pdf", mime="application/pdf", use_container_width=True)

def render_directory():
    track_feature_usage(st.session_state.user_id, "directory")
    st.markdown("<div class='main-header'><h1>👥 Member Directory</h1><p>Contact information and FICA status</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, email, phone, role, fica_verified, join_date, is_active FROM Users ORDER BY join_date DESC")
    members = c.fetchall()
    conn.close()

    for m in members:
        uid, name, email, phone, role, fica, joined, active = m
        fica_badge = "✅ FICA Verified" if fica else "⚠️ FICA Pending"
        status_color = "#2ed573" if active else "#ff4757"
        with st.container():
            st.markdown(f"""
            <div class='arrears-card' style='border-left:4px solid {status_color};'>
                <h4>{name} <span style='font-size:0.75rem;color:#a0a0b0;'>[{role.upper()}]</span></h4>
                <p style='font-size:0.85rem;margin:0;'>📧 {email or 'N/A'} | 📱 {phone or 'N/A'}</p>
                <p style='font-size:0.8rem;margin-top:0.5rem;'><span class='payment-status {"status-paid" if fica else "status-partial"}'>{fica_badge}</span></p>
                <p style='font-size:0.75rem;color:#6c757d;'>Joined: {joined[:10] if joined else 'N/A'}</p>
            </div>
            """, unsafe_allow_html=True)

def render_reports():
    track_feature_usage(st.session_state.user_id, "reports")
    st.markdown("<div class='main-header'><h1>📈 Reports</h1><p>Detailed analytics and data exports</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Portfolio summary
    c.execute("SELECT name, type, amount_invested, current_value, returns, status FROM Investments")
    investments = c.fetchall()

    if investments:
        df = pd.DataFrame(investments, columns=["Name", "Type", "Invested", "Current Value", "Returns", "Status"])
        st.subheader("Portfolio Performance")
        st.dataframe(df, use_container_width=True)

        fig = px.pie(df, values="Current Value", names="Type", title="Portfolio Allocation by Type", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    # Member contribution summary
    c.execute("SELECT u.full_name, SUM(mc.amount) as total FROM Monthly_Contributions mc JOIN Users u ON mc.user_id = u.user_id WHERE mc.status='paid' GROUP BY mc.user_id")
    contrib = c.fetchall()
    if contrib:
        df_c = pd.DataFrame(contrib, columns=["Member", "Total Contributions"])
        fig2 = px.bar(df_c, x="Member", y="Total Contributions", title="Total Contributions by Member")
        st.plotly_chart(fig2, use_container_width=True)

    # Download data
    st.subheader("Export Data")
    c.execute("SELECT * FROM Monthly_Contributions")
    all_contrib = c.fetchall()
    if all_contrib:
        df_all = pd.DataFrame(all_contrib, columns=["ID", "User ID", "Year", "Month", "Amount", "Status", "Date", "Method", "Reference"])
        csv = df_all.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Contributions CSV", data=csv, file_name="contributions.csv", mime="text/csv")

    conn.close()

def render_admin():
    if st.session_state.role != "admin":
        st.error("Admin access only")
        return
    track_feature_usage(st.session_state.user_id, "admin")
    st.markdown("<div class='main-header'><h1>👑 Admin Panel</h1><p>Manage members, investments, and settings</p></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Members", "Investments", "Analytics", "Settings"])

    with tab1:
        st.subheader("Member Management")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_id, username, full_name, email, role, is_active, monthly_contribution, fica_verified FROM Users")
        users = c.fetchall()
        conn.close()

        for u in users:
            uid, uname, name, email, role, active, contrib, fica = u
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{name}** (@{uname}) — {email or 'No email'}")
            with col2:
                new_role = st.selectbox("Role", ["member", "admin"], index=0 if role == "member" else 1, key=f"role_{uid}")
                if new_role != role:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("UPDATE Users SET role=? WHERE user_id=?", (new_role, uid))
                    conn.commit()
                    conn.close()
                    st.rerun()
            with col3:
                toggle = st.toggle("Active", value=bool(active), key=f"active_{uid}")
                if toggle != bool(active):
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("UPDATE Users SET is_active=? WHERE user_id=?", (1 if toggle else 0, uid))
                    conn.commit()
                    conn.close()
                    st.rerun()

    with tab2:
        st.subheader("Add Investment")
        with st.form("add_investment"):
            name = st.text_input("Investment Name")
            itype = st.selectbox("Type", INVESTMENT_TYPES)
            amount = st.number_input("Amount Invested (R)", min_value=0.0, step=1000.0)
            current = st.number_input("Current Value (R)", min_value=0.0, step=1000.0)
            rate = st.number_input("Interest Rate (%)", min_value=0.0, max_value=100.0, step=0.5)
            risk = st.selectbox("Risk Level", ["low", "medium", "high"])
            submitted = st.form_submit_button("Add Investment")
            if submitted and name:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("INSERT INTO Investments (name, type, amount_invested, current_value, interest_rate, risk_level, status, purchase_date) VALUES (?,?,?,?,?,?,?,?)",
                          (name, itype, amount, current, rate, risk, "active", datetime.now().isoformat()))
                conn.commit()
                conn.close()
                st.success("Investment added!")
                st.rerun()

    with tab3:
        st.subheader("Feature Usage Analytics")
        stats = get_feature_usage_stats()
        if stats:
            df_stats = pd.DataFrame(stats, columns=["Feature", "Unique Users", "Total Uses"])
            st.dataframe(df_stats, use_container_width=True)
            fig = px.bar(df_stats, x="Feature", y="Total Uses", title="Feature Usage")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No usage data yet")

    with tab4:
        st.subheader("App Settings")
        st.write("Database path:", DB_PATH)
        st.write("FNB API Enabled:", FNB_ENABLED)
        if st.button("🗑️ Reset Database (DANGER)", type="secondary"):
            st.warning("This will delete all data. Not implemented for safety.")

def render_profile():
    track_feature_usage(st.session_state.user_id, "profile")
    st.markdown("<div class='main-header'><h1>👤 Your Profile</h1><p>Manage your account and preferences</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT full_name, email, phone, monthly_contribution, theme_preference, risk_profile, notification_prefs FROM Users WHERE user_id=?", (st.session_state.user_id,))
    user = c.fetchone()
    conn.close()

    if not user:
        st.error("User not found")
        return

    full_name, email, phone, contrib, theme, risk, notif = user

    with st.form("profile_form"):
        new_name = st.text_input("Full Name", value=full_name or "")
        new_email = st.text_input("Email", value=email or "")
        new_phone = st.text_input("Phone", value=phone or "")
        new_contrib = st.number_input("Monthly Contribution (R)", min_value=100.0, value=float(contrib or 500), step=50.0)
        new_theme = st.selectbox("Theme", ["dark", "light"], index=0 if theme == "dark" else 1)
        new_risk = st.selectbox("Risk Profile", ["conservative", "moderate", "aggressive"], index=["conservative", "moderate", "aggressive"].index(risk or "moderate"))
        new_notif = st.multiselect("Notifications", ["all", "payments", "votes", "ai_advisor", "none"], default=(notif or "all").split(",") if notif else ["all"])

        if st.form_submit_button("💾 Save Changes", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""UPDATE Users SET full_name=?, email=?, phone=?, monthly_contribution=?,
                      theme_preference=?, risk_profile=?, notification_prefs=? WHERE user_id=?""",
                      (new_name, new_email, new_phone, new_contrib, new_theme, new_risk, ",".join(new_notif), st.session_state.user_id))
            conn.commit()
            conn.close()
            st.session_state.theme = new_theme
            st.success("Profile updated!")
            time.sleep(1)
            st.rerun()

def render_notifications():
    track_feature_usage(st.session_state.user_id, "notifications")
    st.markdown("<div class='main-header'><h1>🔔 Notifications</h1><p>Stay updated on club activity</p></div>", unsafe_allow_html=True)

    unread = get_unread_count(st.session_state.user_id)
    if unread > 0:
        st.markdown(f"<p style='color:#00b894;font-weight:600;'>You have {unread} unread notification(s)</p>", unsafe_allow_html=True)

    notifs = get_notifications(st.session_state.user_id)
    if not notifs:
        st.info("No notifications yet")
        return

    for nid, title, message, ntype, is_read, created in notifs:
        css_class = "notification-item notification-unread" if not is_read else "notification-item"
        icon = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(ntype, "📌")
        with st.container():
            st.markdown(f"""
            <div class='{css_class}'>
                <h5>{icon} {title}</h5>
                <p style='font-size:0.9rem;color:#a0a0b0;'>{message}</p>
                <p style='font-size:0.75rem;color:#6c757d;'>{created[:16] if created else ''}</p>
            </div>
            """, unsafe_allow_html=True)
            if not is_read:
                if st.button("Mark as read", key=f"read_{nid}"):
                    mark_notification_read(nid)
                    st.rerun()

def render_whatsapp():
    track_feature_usage(st.session_state.user_id, "whatsapp")
    st.markdown("<div class='main-header'><h1>💬 WhatsApp</h1><p>Group chat and updates</p></div>", unsafe_allow_html=True)

    st.info("WhatsApp integration is coming soon. For now, use the group link below.")
    st.markdown("""
    <div class='feature-card'>
        <div class='feature-icon'>📱</div>
        <div class='feature-name'>Join Khula Collective WhatsApp</div>
        <div class='feature-desc'>Get instant updates on contributions, votes, and investment news</div>
        <a href='https://chat.whatsapp.com/example' target='_blank' style='color:#00b894;font-weight:600;'>Join Group</a>
    </div>
    """, unsafe_allow_html=True)

    # Simulated chat
    st.subheader("Recent Messages")
    messages = [
        ("Admin", "Welcome to the new Khula Collective platform! 🎉", "10:00 AM"),
        ("Sipho Mabena", "Just made my monthly contribution 💰", "10:15 AM"),
        ("Admin", "Great work everyone — we're at 95% collection this month!", "10:30 AM"),
        ("Thandi Nkosi", "Voted FOR the SASOL proposal", "11:00 AM"),
    ]
    for sender, msg, time_str in messages:
        is_me = sender == st.session_state.full_name
        align = "right" if is_me else "left"
        color = "#00b89433" if is_me else "#1e1e30"
        st.markdown(f"""
        <div style='text-align:{align};margin:0.5rem 0;'>
            <div style='display:inline-block;background:{color};padding:0.75rem 1rem;border-radius:12px;max-width:80%;text-align:left;'>
                <p style='font-size:0.75rem;color:#a0a0b0;margin:0;'>{sender} · {time_str}</p>
                <p style='margin:0.25rem 0 0 0;'>{msg}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_feature_discovery():
    track_feature_usage(st.session_state.user_id, "feature_discovery")
    st.markdown("<div class='main-header'><h1>✨ Feature Discovery</h1><p>Explore everything Khula Collective can do</p></div>", unsafe_allow_html=True)

    categories = {}
    for feat in APP_FEATURES:
        cat = feat["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(feat)

    for cat, feats in categories.items():
        st.subheader(f"📂 {cat}")
        cols = st.columns(2)
        for i, feat in enumerate(feats):
            with cols[i % 2]:
                badge = ""
                if feat.get("new"):
                    badge = "<span class='feature-badge badge-new'>NEW</span>"
                elif feat.get("premium"):
                    badge = "<span class='feature-badge badge-premium'>PREMIUM</span>"
                st.markdown(f"""
                <div class='feature-card'>
                    <div class='feature-icon'>{feat['icon']}</div>
                    <div class='feature-name'>{feat['name']} {badge}</div>
                    <div class='feature-desc'>{feat['description']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Try {feat['name']}", key=f"try_{feat['id']}", use_container_width=True):
                    st.session_state.nav_page = feat["id"]
                    st.rerun()

# End of khula_pages3.py
