from khula_config import *
from khula_utils import *

def render_notifications():
    track_feature_usage(st.session_state.user_id, "notifications")
    st.markdown("<div class='main-header'><h1>🔔 Notifications</h1><p>Stay updated with club activity</p></div>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT notification_id, title, message, type, is_read, created_at FROM Notifications WHERE user_id=? ORDER BY created_at DESC", (st.session_state.user_id,))
    notifs = c.fetchall()
    conn.close()

    if notifs:
        for nid, title, message, ntype, is_read, created in notifs:
            unread_class = "notification-unread" if not is_read else ""
            st.markdown(f"""
            <div class='notification-item {unread_class}'>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <strong>{title}</strong>
                    <span style="font-size:0.75rem; color:#a0a0b0;">{created[:16]}</span>
                </div>
                <p style="margin:0; color:#a0a0b0;">{message}</p>
            </div>
            """, unsafe_allow_html=True)
            if not is_read:
                if st.button("Mark Read", key=f"read_{nid}"):
                    mark_notification_read(nid)
                    st.rerun()
    else:
        st.info("No notifications")

# ============================================================
# COMPREHENSIVE REPORTING ENGINE v3.1
# ============================================================

def render_reports():
    track_feature_usage(st.session_state.user_id, "reports")
    st.markdown("<div class='main-header'><h1>📈 Reports</h1><p>Analytics, insights & exports</p></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Contribution Report",
        "🏦 Statement Analytics",
        "📊 Investment Report",
        "📥 Export Center"
    ])

    # ──────────────────────────────────────────────
    # TAB 1: CONTRIBUTION REPORT
    # ──────────────────────────────────────────────
    with tab1:
        _render_contribution_tab()

    # ──────────────────────────────────────────────
    # TAB 2: STATEMENT ANALYTICS
    # ──────────────────────────────────────────────
    with tab2:
        _render_statement_analytics_tab()

    # ──────────────────────────────────────────────
    # TAB 3: INVESTMENT REPORT
    # ──────────────────────────────────────────────
    with tab3:
        _render_investment_tab()

    # ──────────────────────────────────────────────
    # TAB 4: EXPORT CENTER
    # ──────────────────────────────────────────────
    with tab4:
        _render_export_center_tab()


def _render_contribution_tab():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Current month info
    now = datetime.now()
    current_year, current_month = now.year, now.month
    month_name = MONTHS[current_month - 1]

    # All active members + their monthly contribution target
    c.execute("""
        SELECT u.user_id, u.full_name, u.monthly_contribution
        FROM Users u
        WHERE u.role='member' AND u.is_active=1
        ORDER BY u.full_name
    """)
    members = c.fetchall()

    # Current month contributions
    c.execute("""
        SELECT user_id, amount, status
        FROM Monthly_Contributions
        WHERE year=? AND month=?
    """, (current_year, current_month))
    contrib_map = {row[0]: {"amount": row[1], "status": row[2]} for row in c.fetchall()}

    # Target vs collected
    total_target = sum(m[2] for m in members)
    total_collected = sum(
        contrib_map.get(m[0], {}).get("amount", 0)
        for m in members
        if contrib_map.get(m[0], {}).get("status") in ("verified", "paid")
    )
    collection_pct = (total_collected / total_target * 100) if total_target > 0 else 0

    # Metric cards
    cols = st.columns(4)
    with cols[0]:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Active Members</div>
            <div class='metric-value' style='color:#74b9ff;'>{len(members)}</div>
        </div>""", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Target ({month_name})</div>
            <div class='metric-value'>R{total_target:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with cols[2]:
        color = "#00b894" if collection_pct >= 90 else "#fdcb6e" if collection_pct >= 50 else "#d63031"
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Collected ({month_name})</div>
            <div class='metric-value' style='color:{color};'>R{total_collected:,.0f}</div>
        </div>""", unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Collection Rate</div>
            <div class='metric-value' style='color:{color};'>{collection_pct:.1f}%</div>
        </div>""", unsafe_allow_html=True)

    # Progress bar
    st.markdown("""
    <div style="margin: 1.5rem 0;">
        <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
            <span style="color:#a0a0b0; font-size:0.9rem;">Monthly Collection Progress</span>
            <span style="color:#a0a0b0; font-size:0.9rem;">{} / {}</span>
        </div>
        <div class='progress-container'>
            <div class='progress-bar {}' style="width:{}%;"></div>
        </div>
    </div>
    """.format(
        f"R{total_collected:,.0f}", f"R{total_target:,.0f}",
        "success" if collection_pct >= 90 else "warning" if collection_pct >= 50 else "",
        min(collection_pct, 100)
    ), unsafe_allow_html=True)

    st.markdown("---")

    # Member contribution status table
    st.markdown(f"<h3 style='color:#ffffff;'>👥 Member Contribution Status — {month_name} {current_year}</h3>", unsafe_allow_html=True)

    member_data = []
    for uid, name, target in members:
        contrib = contrib_map.get(uid, {})
        amt = contrib.get("amount", 0)
        status = contrib.get("status", "missing")

        if status in ("verified", "paid") and amt >= target:
            status_label = "<span class='payment-status status-paid'>✓ PAID</span>"
            status_color = "#00b894"
            pct = 100
        elif status in ("verified", "paid", "pending") and amt > 0:
            status_label = f"<span class='payment-status status-partial'>◐ PARTIAL</span>"
            status_color = "#fdcb6e"
            pct = (amt / target * 100) if target > 0 else 0
        else:
            status_label = "<span class='payment-status status-late'>✗ LATE / MISSING</span>"
            status_color = "#d63031"
            pct = 0

        member_data.append({
            "Member": name,
            "Target": f"R{target:,.0f}",
            "Paid": f"R{amt:,.0f}",
            "%": pct,
            "Status": status_label,
            "Status Color": status_color,
            "Amount": amt,
            "TargetVal": target,
        })

    # Display as styled cards
    for m in member_data:
        st.markdown(f"""
        <div class='arrears-card' style="border-left: 4px solid {m['Status Color']};">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong style="color:#ffffff;">{m['Member']}</strong>
                    {m['Status']}
                </div>
                <div style="text-align:right;">
                    <div style="color:#a0a0b0; font-size:0.8rem;">{m['Paid']} of {m['Target']}</div>
                    <div style="color:{m['Status Color']}; font-weight:700;">{m['%']:.0f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Charts
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
