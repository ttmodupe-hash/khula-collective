from khula_config import *

# ============================================================
# CSS & THEME
# ============================================================
def load_css(theme="dark"):
    if theme == "dark":
        css = """
        <style>
        .stApp { background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%); color: #e0e0e0; }
        .main-header { text-align: center; padding: 2rem; background: rgba(0, 184, 148, 0.1); border-radius: 16px; margin-bottom: 2rem; border: 1px solid rgba(0, 184, 148, 0.3); }
        .metric-card { background: #1e1e30; padding: 1.5rem; border-radius: 12px; border: 1px solid #2a2a40; text-align: center; }
        .metric-value { font-size: 1.8rem; font-weight: 700; color: #00b894; }
        .metric-label { font-size: 0.85rem; color: #a0a0b0; margin-top: 0.5rem; }
        .feature-card { background: #1e1e30; padding: 1.5rem; border-radius: 12px; border: 1px solid #2a2a40; margin-bottom: 1rem; transition: all 0.3s; }
        .feature-card:hover { border-color: #00b894; transform: translateY(-2px); }
        .feature-icon { font-size: 2rem; margin-bottom: 0.5rem; }
        .feature-name { font-weight: 600; color: #ffffff; margin-bottom: 0.25rem; }
        .feature-desc { font-size: 0.85rem; color: #a0a0b0; }
        .feature-badge { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.7rem; margin-top: 0.5rem; }
        .badge-new { background: #00b894; color: #000; }
        .badge-premium { background: #fdcb6e; color: #000; }
        .badge-core { background: #74b9ff; color: #000; }
        .arrears-card { padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid; }
        .arrears-card.success { background: rgba(0, 184, 148, 0.1); border-color: #00b894; }
        .arrears-card.warning { background: rgba(253, 203, 110, 0.1); border-color: #fdcb6e; }
        .arrears-card.danger { background: rgba(214, 48, 49, 0.1); border-color: #d63031; }
        .payment-status { display: inline-block; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; margin-left: 0.5rem; font-weight: 600; }
        .status-paid { background: #00b894; color: #000; }
        .status-partial { background: #fdcb6e; color: #000; }
        .status-late { background: #d63031; color: #fff; }
        .progress-container { background: #2a2a40; border-radius: 4px; height: 6px; margin-top: 0.5rem; overflow: hidden; }
        .progress-bar { height: 100%; border-radius: 4px; transition: width 0.5s; }
        .progress-bar.success { background: #00b894; }
        .progress-bar.warning { background: #fdcb6e; }
        .progress-bar.danger { background: #d63031; }
        .notification-item { padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; background: #1e1e30; border: 1px solid #2a2a40; }
        .notification-unread { border-left: 3px solid #00b894; }
        .fnb-connect-card { background: linear-gradient(135deg, #009432, #00b894); padding: 2rem; border-radius: 16px; color: white; text-align: center; }
        </style>
        """
    else:
        css = """
        <style>
        .stApp { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); color: #212529; }
        .main-header { text-align: center; padding: 2rem; background: rgba(0, 184, 148, 0.05); border-radius: 16px; margin-bottom: 2rem; border: 1px solid rgba(0, 184, 148, 0.2); }
        .metric-card { background: #ffffff; padding: 1.5rem; border-radius: 12px; border: 1px solid #dee2e6; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .metric-value { font-size: 1.8rem; font-weight: 700; color: #009432; }
        .feature-card { background: #ffffff; padding: 1.5rem; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 1rem; }
        .arrears-card { padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 4px solid; }
        .arrears-card.success { background: rgba(0, 184, 148, 0.05); border-color: #00b894; }
        .arrears-card.warning { background: rgba(253, 203, 110, 0.1); border-color: #fdcb6e; }
        .arrears-card.danger { background: rgba(214, 48, 49, 0.05); border-color: #d63031; }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)

# ============================================================
# FNB API CLIENT (Simulated)
# ============================================================
class FNBAPIClient:
    def __init__(self):
        self.base_url = FNB_API_BASE
        self.token = None

    def connect(self, client_id, client_secret):
        if not client_id or not client_secret:
            return False, "FNB credentials not configured. Set FNB_CLIENT_ID and FNB_CLIENT_SECRET environment variables."
        self.token = f"simulated_token_{hashlib.sha256(f'{client_id}:{client_secret}'.encode()).hexdigest()[:16]}"
        return True, "Connected to FNB Open Banking (Simulated)"

    def get_transactions(self, account_number):
        if not self.token:
            return []
        # Simulated transaction data
        transactions = []
        for i in range(random.randint(3, 8)):
            transactions.append({
                "date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                "description": random.choice(["Khula Contribution", "Monthly Payment", "Investment Club", "Stokvel Deposit"]),
                "amount": random.choice([500, 750, 1000, 1500]),
                "type": "credit",
                "reference": f"KHC{random.randint(1000, 9999)}"
            })
        return transactions

    def sync_contributions(self, user_id, transactions):
        if not transactions:
            return 0
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        synced = 0
        for tx in transactions:
            c.execute("SELECT COUNT(*) FROM Bank_Transactions WHERE user_id=? AND reference=?", (user_id, tx["reference"]))
            if c.fetchone()[0] == 0:
                c.execute("INSERT INTO Bank_Transactions (user_id, transaction_date, description, amount, type, reference, synced_from) VALUES (?,?,?,?,?,?,?)",
                          (user_id, tx["date"], tx["description"], tx["amount"], tx["type"], tx["reference"], "fnb_api"))
                synced += 1
        conn.commit()
        conn.close()
        return synced

# ============================================================
# AUTH & UTILITIES
# ============================================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name, role, theme_preference FROM Users WHERE username=? AND password_hash=? AND is_active=1",
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    return user

def add_notification(user_id, title, message, ntype="info"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Notifications (user_id, title, message, type) VALUES (?,?,?,?)", (user_id, title, message, ntype))
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

def toggle_theme():
    current = st.session_state.get("theme", "dark")
    new_theme = "light" if current == "dark" else "dark"
    st.session_state.theme = new_theme
    if st.session_state.user_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE Users SET theme_preference=? WHERE user_id=?", (new_theme, st.session_state.user_id))
        conn.commit()
        conn.close()

def track_feature_usage(user_id, feature_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Feature_Usage (user_id, feature_id) VALUES (?,?)", (user_id, feature_id))
    conn.commit()
    conn.close()

def get_feature_usage_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT feature_id, COUNT(DISTINCT user_id), COUNT(*) FROM Feature_Usage GROUP BY feature_id")
    stats = c.fetchall()
    conn.close()
    return stats
