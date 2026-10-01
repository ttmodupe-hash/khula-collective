from khula_config import *
from khula_utils import *

# ============================================================
# FEATURE DISCOVERY
# ============================================================
def render_feature_discovery():
    track_feature_usage(st.session_state.user_id, "feature_discovery")
    st.markdown("<div class='main-header'><h1>✨ Discover Khula</h1><p>Explore all features and capabilities</p></div>", unsafe_allow_html=True)

    st.markdown("<h3>🎯 Recommended For You</h3>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT feature_id FROM Feature_Usage WHERE user_id=?", (st.session_state.user_id,))
    used = set(row[0] for row in c.fetchall())
    conn.close()

    unused = [f for f in APP_FEATURES if f["id"] not in used]
    if unused:
        featured = unused[:3]
        cols = st.columns(len(featured))
        for col, feat in zip(cols, featured):
            with col:
                st.markdown(f"""
                <div class='feature-card'>
                    <div class='feature-icon'>{feat['icon']}</div>
                    <div class='feature-name'>{feat['name']}</div>
                    <div class='feature-desc'>{feat['description']}</div>
                    <span class='feature-badge badge-new'>New</span>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Try {feat['name']}", key=f"try_{feat['id']}"):
                    st.session_state.page = feat["id"]
                    st.rerun()

    st.markdown("<h3>📂 All Features</h3>", unsafe_allow_html=True)
    categories = {}
    for f in APP_FEATURES:
        categories.setdefault(f["category"], []).append(f)

    for cat, feats in categories.items():
        st.markdown(f"<h4>{cat}</h4>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, feat in enumerate(feats):
            with cols[idx % 3]:
                badge = ""
                if feat["new"]:
                    badge = "<span class='feature-badge badge-new'>New</span>"
                elif feat["premium"]:
                    badge = "<span class='feature-badge badge-premium'>Premium</span>"
                else:
                    badge = "<span class='feature-badge badge-core'>Core</span>"
                st.markdown(f"""
                <div class='feature-card'>
                    <div class='feature-icon'>{feat['icon']}</div>
                    <div class='feature-name'>{feat['name']}</div>
                    <div class='feature-desc'>{feat['description']}</div>
                    {badge}
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<h3>📊 App Usage Analytics</h3>", unsafe_allow_html=True)
    stats = get_feature_usage_stats()
    if stats:
        df = pd.DataFrame(stats, columns=["Feature", "Users", "Uses"])
        fig = px.bar(df, x="Feature", y="Uses", color="Users", color_continuous_scale="Greens")
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#ffffff')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No usage data yet")

# ============================================================
# FNB API GUIDE
# ============================================================
def render_fnb_api_guide():
    track_feature_usage(st.session_state.user_id, "fnb_api_guide")
    st.markdown("<h2>🏦 FNB API Access Guide</h2>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background: #1e1e3a; padding: 1.5rem; border-radius: 12px; border: 1px solid #2a2a50; margin-bottom: 1.5rem;'>
        <h3 style='color: #00b894; margin-top: 0;'>Current Status: Statement Upload Mode ✅</h3>
        <p style='color: #e0e0e0;'>Your club can already generate reports from uploaded FNB statements (PDF/CSV).
        This guide explains how to get <strong>real-time API access</strong> for automatic sync.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h3>🚪 Step 1: Register a Business Entity</h3>", unsafe_allow_html=True)
    st.markdown("""
    FNB does not offer self-serve developer APIs for personal transaction history.
    You need a **registered business or trust** to apply:
    - Register your stokvel/investment club as a **stokvel association** or **private company**
    - Obtain a tax number from SARS
    - Open a **FNB Business Account** (or ensure your club banks with FNB)
    """, unsafe_allow_html=True)

    st.markdown("<h3>📝 Step 2: Contact FNB Business Solutions</h3>", unsafe_allow_html=True)
    st.markdown("""
    Reach out to FNB via:
    - **Email:** business@fnb.co.za
    - **Phone:** 087 575 9404 (Business Banking)
    - **Branch:** Visit your relationship manager

    Request access to **FNB Open Banking / API Services** for:
    - Account information (read-only transaction history)
    - Payment initiation (optional, for automated contributions)
    """, unsafe_allow_html=True)

    st.markdown("<h3>📋 Step 3: Submit Application</h3>", unsafe_allow_html=True)
    st.markdown("""
    FNB will require:
    1. **Business registration documents** (CIPC certificate)
    2. **FICA compliance** (ID copies, proof of address for all signatories)
    3. **Tax clearance certificate** (SARS)
    4. **API use case description** (explain you're building an investment club management tool)
    5. **Data protection plan** (how you'll secure member transaction data)
    6. **Expected transaction volume** (monthly API call estimates)
    """, unsafe_allow_html=True)

    st.markdown("<h3>⏱️ Step 4: Wait for Approval</h3>", unsafe_allow_html=True)
    st.markdown("""
    - Approval typically takes **4–8 weeks**
    - FNB will provide **sandbox credentials** first for testing
    - After successful UAT, you'll receive **production API keys**
    - You'll need to sign an **API Service Agreement** with liability clauses
    """, unsafe_allow_html=True)

    st.markdown("<h3>⚡ Alternative: Bank Aggregator (Faster)</h3>", unsafe_allow_html=True)
    st.markdown("""
    While waiting for direct FNB API approval, consider these SA fintech aggregators:

    | Provider | FNB Support | Setup Time | Cost |
    |----------|------------|------------|------|
    | **Banklink** | ✅ Live | 1–2 weeks | From R500/mo |
    | **Ozow** | ✅ Live | 1–2 weeks | Per-transaction |
    | **Stitch** | ✅ Available | 1–2 weeks | Developer-friendly |
    | **Investec Programmable Banking** | ✅ Direct API | 2–3 weeks | Free for devs |

    These providers already have FNB partnerships and can provide transaction data via their APIs.
    """, unsafe_allow_html=True)

    st.markdown("<h3>🔐 Security Requirements</h3>", unsafe_allow_html=True)
    st.markdown("""
    Before handling real banking data, ensure:
    - **HTTPS only** (SSL certificate installed)
    - **AES-256 encryption** for data at rest
    - **OAuth 2.0** for API authentication
    - **PCI-DSS compliance** if handling card data
    - **POPIA compliance** (South Africa's data protection law)
    - Regular **penetration testing** and security audits
    """, unsafe_allow_html=True)

    st.markdown("<h3>🛠️ What We Need From You</h3>", unsafe_allow_html=True)
    st.markdown("""
    Once you have API credentials, simply add them as environment variables in Railway:
    ```
    FNB_CLIENT_ID=your_client_id
    FNB_CLIENT_SECRET=your_client_secret
    FNB_API_BASE=https://api.fnb.co.za/openbanking/v1
    ```
    The app will automatically switch from **Statement Upload Mode** to **Live API Mode**.
    """, unsafe_allow_html=True)

    st.info("💡 **Tip:** For now, the statement upload feature gives you 90% of the value. Upload PDFs or CSVs from FNB Online Banking and the app will auto-parse transactions, categorize spending, and generate reports.")

# ============================================================
# MEMBER VOICE
# ============================================================
def render_member_voice():
    track_feature_usage(st.session_state.user_id, "member_voice")
    st.markdown("<div class='main-header'><h1>🗳️ Member Voice</h1><p>Democratic voting on investment proposals</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    st.markdown("<h3>📋 Active Proposals</h3>", unsafe_allow_html=True)
    c.execute("SELECT s.suggestion_id, s.title, s.description, s.investment_type, s.amount, s.votes, s.voted_by, u.full_name, s.status FROM Suggestions s JOIN Users u ON s.user_id=u.user_id WHERE s.status='open' ORDER BY s.votes DESC")
    proposals = c.fetchall()

    if proposals:
        for prop in proposals:
            sid, title, desc, inv_type, amount, votes, voted_by, author, status = prop
            voted_list = voted_by.split(",") if voted_by else []
            has_voted = str(st.session_state.user_id) in voted_list

            with st.container():
                st.markdown(f"""
                <div style='background:#1e1e30;padding:1.5rem;border-radius:16px;border:1px solid #2a2a40;margin-bottom:1rem;'>
                    <div style='display:flex;justify-content:space-between;align-items:start;'>
                        <div>
                            <h4 style='margin:0 0 0.5rem 0;color:#00b894;'>{title}</h4>
                            <p style='margin:0;color:#a0a0b0;font-size:0.9rem;'>by {author} · {inv_type} · R{amount:,.0f}</p>
                        </div>
                        <div style='text-align:right;'>
                            <div style='font-size:1.5rem;font-weight:700;color:#00b894;'>{votes} votes</div>
                        </div>
                    </div>
                    <p style='margin:0.75rem 0 0 0;'>{desc}</p>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    if has_voted:
                        st.button("✅ Voted", disabled=True, key=f"voted_{sid}")
                    else:
                        if st.button("🗳️ Vote", key=f"vote_{sid}"):
                            new_voted = voted_by + "," + str(st.session_state.user_id) if voted_by else str(st.session_state.user_id)
                            c.execute("UPDATE Suggestions SET votes=votes+1, voted_by=? WHERE suggestion_id=?", (new_voted, sid))
                            conn.commit()
                            add_notification(st.session_state.user_id, "Vote Recorded", f"You voted for: {title}", "success")
                            st.rerun()
                with col2:
                    if st.session_state.role == "admin":
                        if st.button("✓ Approve", key=f"approve_{sid}"):
                            c.execute("UPDATE Suggestions SET status='approved' WHERE suggestion_id=?", (sid,))
                            conn.commit()
                            st.rerun()
    else:
        st.info("No active proposals")

    st.markdown("<h3>➕ New Proposal</h3>", unsafe_allow_html=True)
    with st.form("proposal_form"):
        title = st.text_input("Title")
        desc = st.text_area("Description")
        inv_type = st.selectbox("Investment Type", INVESTMENT_TYPES)
        amount = st.number_input("Amount (R)", min_value=1000, step=1000)
        submitted = st.form_submit_button("Submit Proposal", type="primary")
        if submitted:
            c.execute("INSERT INTO Suggestions (user_id, title, description, investment_type, amount) VALUES (?,?,?,?,?)",
                      (st.session_state.user_id, title, desc, inv_type, amount))
            conn.commit()
            add_notification(1, "New Proposal", f"{st.session_state.full_name} submitted: {title}", "info")
            st.success("Proposal submitted!")

    conn.close()

# ============================================================
# CONSTITUTION
# ============================================================
def render_constitution():
    track_feature_usage(st.session_state.user_id, "constitution")
    st.markdown("<div class='main-header'><h1>📜 Constitution</h1><p>Club rules and governance</p></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='background:#1e1e30;padding:2rem;border-radius:16px;border:1px solid #2a2a40;'>
        <h3 style='color:#00b894;'>Khula Collective Constitution</h3>
        <p><strong>Article 1 - Purpose:</strong> To collectively grow wealth through disciplined savings and informed investments.</p>
        <p><strong>Article 2 - Membership:</strong> Members must be 18+, provide valid ID for FICA, and commit to monthly contributions.</p>
        <p><strong>Article 3 - Contributions:</strong> Minimum monthly contribution is R500, due by the 7th of each month.</p>
        <p><strong>Article 4 - Voting:</strong> Investment decisions require majority vote (51%). Major decisions (R50k+) require 75%.</p>
        <p><strong>Article 5 - Arrears:</strong> Members 2+ months behind lose voting rights. 3+ months may face membership review.</p>
        <p><strong>Article 6 - Withdrawal:</strong> Members may withdraw with 30 days notice. Funds returned at end of quarter.</p>
        <p><strong>Article 7 - FICA Compliance:</strong> All members must complete FICA verification within 30 days of joining.</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# DIRECTORY
# ============================================================
def render_directory():
    track_feature_usage(st.session_state.user_id, "directory")
    st.markdown("<div class='main-header'><h1>👥 Member Directory</h1><p>Contact info and FICA status</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT full_name, email, phone, role, fica_status, bank_name, monthly_contribution, joined_date FROM Users WHERE is_active=1", conn)
    conn.close()

    if not df.empty:
        st.dataframe(df.rename(columns={
            'full_name': 'Name', 'email': 'Email', 'phone': 'Phone',
            'role': 'Role', 'fica_status': 'FICA', 'bank_name': 'Bank',
            'monthly_contribution': 'Monthly', 'joined_date': 'Joined'
        }), use_container_width=True, hide_index=True)
    else:
        st.info("No members found")
