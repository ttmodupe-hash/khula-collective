from khula_config import *

def load_css(theme):
    is_dark = theme == "dark"
    bg = "#0f0f23" if is_dark else "#f8f9fa"
    card = "#1e1e30" if is_dark else "#ffffff"
    text = "#ffffff" if is_dark else "#1a1a2e"
    text_muted = "#a0a0b0" if is_dark else "#6c757d"
    border = "#2a2a40" if is_dark else "#dee2e6"
    accent = "#00b894"
    css = f"""
    <style>
    .stApp {{ background: {bg} !important; color: {text} !important; }}
    .main-header {{ text-align: center; padding: 2rem 0; margin-bottom: 1rem; }}
    .main-header h1 {{ color: {accent}; font-weight: 800; margin-bottom: 0.5rem; }}
    .main-header p {{ color: {text_muted}; font-size: 1.1rem; }}
    .metric-card {{ background: {card}; padding: 1.5rem; border-radius: 16px; border: 1px solid {border}; text-align: center; }}
    .metric-label {{ font-size: 0.85rem; color: {text_muted}; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem; }}
    .metric-value {{ font-size: 2rem; font-weight: 700; color: {accent}; }}
    .arrears-card {{ background: {card}; padding: 1rem 1.5rem; border-radius: 12px; border: 1px solid {border}; margin-bottom: 0.75rem; }}
    .arrears-card.success {{ border-left: 4px solid #2ed573; }}
    .arrears-card.warning {{ border-left: 4px solid #ffa502; }}
    .fnb-connect-card {{ background: linear-gradient(135deg, #00b894, #00cec9); padding: 1.5rem; border-radius: 16px; color: white; margin-bottom: 1.5rem; }}
    .fnb-connect-card h3 {{ color: white; margin: 0 0 0.5rem 0; }}
    .progress-container {{ width: 100%; height: 12px; background: {border}; border-radius: 6px; overflow: hidden; margin-top: 0.5rem; }}
    .progress-bar {{ height: 100%; background: linear-gradient(90deg, #00b894, #00cec9); border-radius: 6px; }}
    .progress-bar.success {{ background: linear-gradient(90deg, #2ed573, #7bed9f); }}
    .progress-bar.warning {{ background: linear-gradient(90deg, #ffa502, #ffdd59); }}
    .payment-status {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem; }}
    .status-paid {{ background: #2ed57333; color: #2ed573; }}
    .status-partial {{ background: #ffa50233; color: #ffa502; }}
    .status-late {{ background: #ff475733; color: #ff4757; }}
    .feature-card {{ background: {card}; padding: 1.5rem; border-radius: 16px; border: 1px solid {border}; text-align: center; margin-bottom: 1rem; transition: transform 0.2s; }}
    .feature-card:hover {{ transform: translateY(-4px); border-color: {accent}; }}
    .feature-icon {{ font-size: 2.5rem; margin-bottom: 0.75rem; }}
    .feature-name {{ font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem; }}
    .feature-desc {{ font-size: 0.85rem; color: {text_muted}; }}
    .feature-badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.7rem; font-weight: 600; margin-top: 0.5rem; }}
    .badge-new {{ background: #ff4757; color: white; }}
    .badge-premium {{ background: #ffa502; color: white; }}
    .badge-core {{ background: {accent}; color: white; }}
    .notification-item {{ padding: 1rem; background: {card}; border-radius: 12px; margin-bottom: 0.75rem; border: 1px solid {border}; }}
    .notification-unread {{ border-left: 4px solid {accent}; }}
    .mobile-bottom-nav {{ display: none; position: fixed; bottom: 0; left: 0; right: 0; background: {card}; border-top: 1px solid {border}; padding: 0.5rem; z-index: 999; justify-content: space-around; }}
    .mobile-bottom-nav a {{ text-align: center; color: {text_muted}; text-decoration: none; font-size: 0.75rem; padding: 0.5rem; }}
    .mobile-bottom-nav a.active {{ color: {accent}; }}
    .mobile-bottom-nav .nav-icon {{ display: block; font-size: 1.25rem; margin-bottom: 0.25rem; }}
    @media (max-width: 768px) {{ .mobile-bottom-nav {{ display: flex !important; }} }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

class FNBAPIClient:
    def __init__(self, client_id=None, client_secret=None):
        self.client_id = client_id or FNB_CLIENT_ID
        self.client_secret = client_secret or FNB_CLIENT_SECRET
        self.base_url = FNB_API_BASE
        self.connected = False
        self.access_token = None
    def connect(self):
        if not self.client_id or not self.client_secret:
            return {"success": False, "error": "FNB API credentials not configured"}
        self.connected = True
        self.access_token = "simulated_fnb_token_" + hashlib.sha256((self.client_id + self.client_secret).encode()).hexdigest()[:16]
        return {"success": True, "message": "Connected to FNB"}
    def get_transactions(self, account_number, days=30):
        if not self.connected:
            return {"success": False, "error": "Not connected to FNB"}
        transactions = []
        for i in range(random.randint(5, 15)):
            date = datetime.now() - timedelta(days=random.randint(1, days))
            amount = random.choice([500.00, 250.00, 1000.00, 500.00, 500.00])
            transactions.append({
                "transaction_id": f"FNB{random.randint(10000000, 99999999)}",
                "date": date.strftime("%Y-%m-%d"),
                "description": random.choice(["Khula Collective Contribution", "STOKVEL CONTRIBUTION", "Monthly Payment - Khula", "Investment Club Deposit"]),
                "amount": amount, "type": "credit",
                "reference": f"KHULA-{random.randint(1000, 9999)}", "status": "completed"
            })
        return {"success": True, "transactions": transactions}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    pw_hash = hash_password(password)
    c.execute("SELECT user_id, username, full_name, role, theme_preference FROM Users WHERE username=? AND password_hash=? AND is_active=1", (username, pw_hash))
    user = c.fetchone()
    if user:
        c.execute("UPDATE Users SET last_login=? WHERE user_id=?", (datetime.now().isoformat(), user[0]))
        conn.commit()
    conn.close()
    return user

def add_notification(user_id, title, message, notif_type="info"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Notifications (user_id, title, message, type) VALUES (?, ?, ?, ?)", (user_id, title, message, notif_type))
    conn.commit()
    conn.close()

def get_notifications(user_id, limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT notification_id, title, message, type, is_read, created_at FROM Notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def mark_notification_read(notification_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE Notifications SET is_read=1 WHERE notification_id=?", (notification_id,))
    conn.commit()
    conn.close()

def get_unread_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM Notifications WHERE user_id=? AND is_read=0", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def track_feature_usage(user_id, feature_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Feature_Usage (user_id, feature_id) VALUES (?, ?)", (user_id, feature_id))
    conn.commit()
    conn.close()

def get_feature_usage_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT feature_id, COUNT(DISTINCT user_id), COUNT(*) FROM Feature_Usage GROUP BY feature_id ORDER BY COUNT(*) DESC")
    stats = c.fetchall()
    conn.close()
    return stats

# ============================================================
# STATEMENT PARSER FUNCTIONS
# ============================================================

def parse_pdf_statement(pdf_file, user_id):