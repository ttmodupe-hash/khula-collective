from khula_recovery import render_member_recovery
from html import escape
from khula_member_services import submit_payment_claim, latest_club_balance
from khula_security import register_member, registration_enabled, member_auth_state
from khula_applications import request_membership, public_registration_enabled
from khula_membership_receipts import render_receipt_lookup
from khula_owner_access import render_owner_setup
from khula_compliance import render_public_notice, onboarding_gate_status
from khula_advisory_core import bank_snapshot_fresh
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
    """A responsive, properly contained public login and membership landing.

    Use native Streamlit layout containers: ordinary HTML div wrappers
    cannot contain Streamlit form widgets, and were causing the screenshot's
    full-width form with an empty, narrow HTML-only brand panel.
    """
    st.markdown("""
    <style>
      .stApp { background: #0d1022 !important; }
      [data-testid="stMainBlockContainer"] {
        padding-top: clamp(1.25rem, 4vh, 2.75rem);
        padding-bottom: 2rem;
      }
      .khula-auth-hero { text-align: center; margin: 0 auto 1.2rem; max-width: 34rem; }
      .khula-auth-hero img { display:block; width:72px; height:72px; margin:0 auto 1rem;
        border-radius:20px; box-shadow:0 15px 36px rgba(0,0,0,.32); }
      .khula-auth-hero h1 { margin:.25rem 0 .55rem; color:#f5fff7;
        font-size:clamp(1.75rem,4.6vw,2.4rem); line-height:1.15; font-weight:800;
        letter-spacing:-.04em; }
      .khula-auth-hero .eyebrow { color:#6be0ad; letter-spacing:.13em;
        font-size:.72rem; font-weight:800; text-transform:uppercase; }
      .khula-auth-hero p { margin:.3rem auto; color:#afc8bd;
        font-size:.98rem; line-height:1.5; max-width:33ch; }
      .khula-login-steps { display:flex; flex-wrap:wrap; justify-content:center;
        gap:.4rem; margin:.9rem auto 1.25rem; }
      .khula-login-steps span { padding:.38rem .65rem; border:1px solid #285945;
        border-radius:99px; background:#18382c; color:#c1ecd0; font-size:.75rem; }
      @media (max-width:640px) {
        [data-testid="stMainBlockContainer"] {padding-left:1rem;padding-right:1rem;}
        .khula-auth-hero img {width:60px;height:60px;}
        .khula-auth-hero {margin-bottom:.7rem;}
      }
    </style>
    """, unsafe_allow_html=True)

    # Center actual Streamlit widgets, not a raw HTML wrapper.
    _, main_col, _ = st.columns([1, 2.2, 1], gap="large")
    with main_col:
        st.markdown("""
        <header class="khula-auth-hero">
          <img src="/app/static/khula-icon-192.png" alt="Khula Collective icon">
          <div class="eyebrow">Members · Savings · Shared decisions</div>
          <h1>Khula Collective</h1>
          <p>A private home for collective savings, transparent records
          and better financial decisions.</p>
        </header>
        <div class="khula-login-steps">
          <span>1. Request access</span>
          <span>2. Club approval</span>
          <span>3. Secure sign-in</span>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.pop("_khula_owner_setup_complete", False):
            st.success(
                "Your Khula administrator account has been activated. "
                "Sign in below using your chosen username and password. "
                "You can then approve requests under Membership Approvals."
            )

        with st.container(border=True):
            st.subheader("Welcome back")
            st.caption("Use your approved Khula member account.")
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter username")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                submitted = st.form_submit_button("Sign in to Khula", use_container_width=True, type="primary")
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
                        state = member_auth_state(DB_PATH, user[0])
                        st.session_state._auth_epoch = state[3]
                        st.session_state.theme = user[4] or "dark"
                        st.session_state.nav_page = "dashboard"
                        st.session_state._last_activity_monotonic = time.monotonic()
                        st.success(f"Welcome back, {user[2]}!")
                        st.rerun()
                    else:
                        st.error("Sign-in failed. Check your credentials, or ask the administrator whether your membership is approved.")

            st.link_button(
                "📲 Add Khula to your phone",
                "/app/static/install.html",
                use_container_width=True,
                type="secondary",
            )
            st.caption("Installing the app does not approve or create a member account.")

        # The private owner setup link has no token in the URL. Only a fresh
        # email-delivered code plus verified Railway owner email can grant admin.
        render_owner_setup()

        with st.container(border=True):
            st.subheader("New to Khula? Apply for membership")
            st.caption(
                "Anyone may request an account when enrolment is open. "
                "Only the club's administrator can approve access to member records "
                "and financial features. Signing up does not automatically make you a member."
            )
            render_public_notice()

            if not public_registration_enabled():
                if registration_enabled():
                    st.info(
                        "Public applications are temporarily paused by the club administrator. "
                        "Existing approved members can still sign in."
                    )
                else:
                    st.info(
                        "New requests are temporarily closed until Khula's privacy notice, "
                        "club governance and overseas-hosting safeguards have been formally "
                        "reviewed. No personal registration data is collected while closed."
                    )
            else:
                with st.expander("Apply for access — invitation code optional", expanded=True):
                    with st.form("member_registration"):
                        new_user = st.text_input(
                            "Choose username", key="join_username",
                            help="Letters, digits and underscore; first character a letter."
                        )
                        new_name = st.text_input(
                            "Full name", key="join_name"
                        )
                        new_email = st.text_input(
                            "Your email address", key="join_email",
                            help="The administrator must verify that you control this email address before approval."
                        )
                        new_password = st.text_input(
                            "Create password (12–72 UTF-8 bytes)",
                            type="password", key="join_password"
                        )
                        confirm_password = st.text_input(
                            "Confirm password", type="password", key="join_password_confirmation"
                        )
                        invite = st.text_input(
                            "Invitation code (leave blank to request membership)",
                            type="password", key="join_invitation"
                        )
                        adult = st.checkbox(
                            "I confirm I am at least 18 years old and am applying for myself.",
                            key="join_adult"
                        )
                        acknowledged = st.checkbox(
                            "I have read the Khula privacy notice and understand the "
                            "purpose of my registration details and administrator review.",
                            key="join_privacy"
                        )
                        transferred = st.checkbox(
                            "I acknowledge and expressly consent to the transfer "
                            "of my registration details to the overseas Railway hosting region "
                            "identified in the privacy notice.",
                            key="join_overseas"
                        )
                        st.caption(
                            "Applications are private. No contribution is due for registration; "
                            "do not send bank account details, identity images, PINs or OTPs."
                        )
                        submitted = st.form_submit_button("Submit membership request")
                        if submitted:
                            if not (adult and acknowledged and transferred):
                                st.error(
                                    "Please read the privacy information and confirm all "
                                    "three eligibility and consent statements."
                                )
                            elif new_password != confirm_password:
                                st.error("Passwords do not match.")
                            else:
                                try:
                                    st.session_state.pop("_khula_last_receipt", None)
                                    if invite.strip():
                                        result = register_member(
                                            DB_PATH, new_user, new_name, new_email,
                                            new_password, invite,
                                            notice_acknowledged=acknowledged,
                                            international_transfer_acknowledged=transferred,
                                            adult_confirmed=adult,
                                            include_receipt=True,
                                        )
                                    else:
                                        result = request_membership(
                                            DB_PATH, new_user, new_name, new_email,
                                            new_password,
                                            notice_acknowledged=acknowledged,
                                            international_transfer_acknowledged=transferred,
                                            adult_confirmed=adult,
                                            include_receipt=True,
                                        )
                                    if isinstance(result, dict):
                                        st.session_state["_khula_last_receipt"] = result["tracking_code"]
                                    st.success(
                                        "Your request was recorded, but you CANNOT sign in yet. "
                                        "An active club administrator must independently verify "
                                        "and approve your membership. "
                                        "No automatic email has been sent."
                                    )
                                except (ValueError, PermissionError) as exc:
                                    st.error(str(exc))

        tracking = st.session_state.get("_khula_last_receipt")
        if tracking:
            st.success("Save your private membership tracking code now. It is displayed only in this browser session.")
            st.code(tracking, language=None)
            st.caption(
                "Use the code in 'Check your membership status' below. "
                "Never share it in a group. The code lasts up to 45 days."
            )
            if st.button("Hide the tracking code"):
                st.session_state.pop("_khula_last_receipt", None)
                st.rerun()

        render_receipt_lookup()
        render_member_recovery()
        with st.expander("🇿🇦 Explore sourced South African economic data"):
            from khula_sarb import render_sarb_panel
            render_sarb_panel(expanded=False)
        st.caption(
            "Khula Collective · Only approved members may access private records · "
            "No live bank account connection is claimed."
        )


def render_dashboard():
    """Main dashboard with portfolio overview, market data, and quick actions."""
    track_feature_usage(st.session_state.user_id, "dashboard")
    user_name = escape(str(st.session_state.get("full_name", "Member")))

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

    c.execute("SELECT COUNT(DISTINCT user_id) FROM Users WHERE is_active=1 AND role='member'")
    active_members = c.fetchone()[0] or 0

    conn.close()

    # Club bank balances are sourced separately from investment holdings
    # and ledger entries. Never add them together as "available savings".
    snapshot = latest_club_balance(DB_PATH)
    if snapshot and bank_snapshot_fresh(snapshot["as_of"]):
        snapshot_balance_label = f"R{snapshot['available']:,.0f}"
        bank_label = f"Manual bank snapshot: {snapshot['as_of']}"
    else:
        snapshot_balance_label = "Unverified"
        bank_label = "No recent administrator-attested bank statement"

    # ── KPI Cards ───────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Recorded investment valuation</div>
            <div class='metric-value'>R{portfolio_value:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        delta_color = "#2ed573" if total_returns >= 0 else "#ff4757"
        delta_sign = "+" if total_returns >= 0 else ""
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Recorded returns (not independently audited)</div>
            <div class='metric-value' style='color:{delta_color};'>{delta_sign}R{total_returns:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Contributions marked paid this month</div>
            <div class='metric-value'>R{month_contrib:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Active club members (excluding admins)</div>
            <div class='metric-value'>{active_members}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Verified-source financial status ────────────────────
    st.subheader("Club cash — not the same as investment valuations")
    st.metric("Cash available after reserve (manual attestation)", snapshot_balance_label)
    st.caption(bank_label + " · This is not a live bank API or an independent audit.")
    st.warning(
        "Contribution and investment figures are recorded ledger entries. "
        "They must be reconciled with actual club bank and brokerage evidence."
    )

    # Never label hard-coded or synthetic headlines as latest news.
    from khula_sarb import render_sarb_panel
    with st.expander("🇿🇦 See independently sourced South African economic data"):
        render_sarb_panel(expanded=False)

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
            ("💰", "Review Contributions", "payments"),
            ("🗳️", "Vote on Proposal", "voice"),
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
