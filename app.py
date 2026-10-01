# ============================================================
# Khula Collective v3.0 - South African Investment Club Platform
# FNB API Integration | Payment Progress | Feature Discovery
# Railway Production Ready
# ============================================================
import streamlit as st
import sqlite3
import hashlib
import random
import time
import os
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import matplotlib
matplotlib.use('Agg')

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Khula Collective v3.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed" if st.session_state.get("mobile_view") else "expanded"
)

# ============================================================
# FNB API CONFIG
# ============================================================
FNB_API_BASE = os.getenv("FNB_API_BASE", "https://api.fnb.co.za/openbanking/v1")
FNB_CLIENT_ID = os.getenv("FNB_CLIENT_ID", "")
FNB_CLIENT_SECRET = os.getenv("FNB_CLIENT_SECRET", "")
FNB_ENABLED = os.getenv("FNB_ENABLED", "false").lower() == "true"

# ============================================================
# CONSTANTS
# ============================================================
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "khula_collective.db")
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
INVESTMENT_TYPES = ["JSE Stocks", "SARB Bonds", "Property", "Crypto", "ETFs", "Money Market", "Commodities"]

APP_FEATURES = [
    {"id": "dashboard", "name": "Dashboard", "description": "Overview of contributions, investments, and growth", "icon": "🏠", "category": "Core", "premium": False, "new": False},
    {"id": "payment_tracking", "name": "Payment Progress", "description": "Track who's behind on contributions and payment status", "icon": "💰", "category": "Core", "premium": False, "new": True},
    {"id": "fnb_sync", "name": "FNB Bank Sync", "description": "Connect FNB account for automatic transaction tracking", "icon": "🏦", "category": "Core", "premium": False, "new": True},
    {"id": "member_voice", "name": "Member Voice", "description": "Propose and vote on investment ideas democratically", "icon": "🗳️", "category": "Core", "premium": False, "new": False},
    {"id": "ai_advisor", "name": "AI Advisor", "description": "South African market insights and investment guidance", "icon": "🤖", "category": "Analytics", "premium": False, "new": False},
    {"id": "reports", "name": "Reports", "description": "Detailed analytics and CSV export", "icon": "📈", "category": "Analytics", "premium": False, "new": False},
    {"id": "constitution", "name": "Constitution", "description": "Club rules and governance", "icon": "📜", "category": "Club", "premium": False, "new": False},
    {"id": "directory", "name": "Member Directory", "description": "Contact info and FICA status", "icon": "👥", "category": "Club", "premium": False, "new": False},
    {"id": "whatsapp", "name": "WhatsApp", "description": "Group chat integration and invites", "icon": "💬", "category": "Club", "premium": False, "new": False},
    {"id": "feature_discovery", "name": "Feature Discovery", "description": "Explore all app features and get recommendations", "icon": "✨", "category": "App", "premium": False, "new": True},
    {"id": "notifications", "name": "Notifications", "description": "Alerts for votes, payments, and announcements", "icon": "🔔", "category": "App", "premium": False, "new": False},
    {"id": "profile", "name": "Profile", "description": "Manage your account and preferences", "icon": "👤", "category": "App", "premium": False, "new": False},
    {"id": "admin", "name": "Admin Panel", "description": "Manage members, announcements, and settings", "icon": "👑", "category": "Admin", "premium": True, "new": False},
    {"id": "dark_mode", "name": "Dark Mode", "description": "Toggle between light and dark themes", "icon": "🌓", "category": "App", "premium": False, "new": False},
    {"id": "mobile_nav", "name": "Mobile Navigation", "description": "Optimized mobile bottom nav bar", "icon": "📱", "category": "App", "premium": False, "new": True},
]

SA_NEWS_HEADLINES = [
    ("JSE All-Share Hits Record High", "The JSE All-Share Index reached a new all-time high driven by resource stocks.", "Positive"),
    ("SARB Keeps Repo Rate at 8.25%", "The South African Reserve Bank maintained the repo rate, citing inflation concerns.", "Neutral"),
    ("Sasol Announces Green Hydrogen Investment", "Sasol plans to invest R50 billion in green hydrogen projects.", "Positive"),
    ("Rand Strengthens Against Dollar", "The South African rand gained 2% against the US dollar.", "Positive"),
    ("Retail Bonds at 11.75%", "Government retail bonds now offer an attractive 11.75% interest rate.", "Positive"),
]

# ============================================================
# DATABASE INIT
# ============================================================
def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        email TEXT,
        phone TEXT,
        role TEXT DEFAULT 'member',
        bank_account TEXT,
        bank_name TEXT,
        monthly_contribution REAL DEFAULT 500.0,
        fica_status TEXT DEFAULT 'pending',
        is_active INTEGER DEFAULT 1,
        joined_date TEXT DEFAULT CURRENT_TIMESTAMP,
        last_login TEXT,
        theme_preference TEXT DEFAULT 'dark'
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Monthly_Contributions (
        contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        year INTEGER,
        month INTEGER,
        amount REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Investments (
        investment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        investment_type TEXT,
        amount_invested REAL DEFAULT 0,
        current_value REAL DEFAULT 0,
        purchase_date TEXT,
        notes TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Suggestions (
        suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        investment_type TEXT,
        amount REAL,
        votes INTEGER DEFAULT 0,
        voted_by TEXT DEFAULT '',
        status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        message TEXT,
        type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Announcements (
        announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        posted_by INTEGER,
        priority TEXT DEFAULT 'normal',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # v3.0 new tables
    c.execute('''CREATE TABLE IF NOT EXISTS FNB_Sync_Log (
        sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        sync_type TEXT,
        status TEXT,
        transactions_synced INTEGER DEFAULT 0,
        error_message TEXT,
        synced_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Bank_Transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        transaction_date TEXT,
        description TEXT,
        amount REAL,
        type TEXT,
        reference TEXT,
        source TEXT DEFAULT 'manual',
        fnb_transaction_id TEXT,
        matched_contribution_id INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Payment_Schedules (
        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        year INTEGER,
        month INTEGER,
        due_date TEXT,
        amount_due REAL,
        amount_paid REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        penalty_amount REAL DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Feature_Usage (
        usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        feature_id TEXT,
        used_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

# ============================================================
# DEMO DATA
# ============================================================
def seed_demo_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM Users")
    if c.fetchone()[0] > 0:
        conn.close()
        return
    
    members = [
        ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "Admin User", "admin@khula.co.za", "0821234567", "admin", None, None, 500.0, "verified"),
        ("siphoo", hashlib.sha256("password1".encode()).hexdigest(), "Sipho Mabena", "sipho@email.com", "0834567890", "member", "1234567890", "FNB", 500.0, "verified"),
        ("thandi", hashlib.sha256("password2".encode()).hexdigest(), "Thandi Nkosi", "thandi@email.com", "0845678901", "member", "2345678901", "FNB", 500.0, "verified"),
        ("lindiwe", hashlib.sha256("password3".encode()).hexdigest(), "Lindiwe Dlamini", "lindiwe@email.com", "0856789012", "member", "3456789012", "FNB", 500.0, "pending"),
        ("bongani", hashlib.sha256("password4".encode()).hexdigest(), "Bongani Zulu", "bongani@email.com", "0867890123", "member", "4567890123", "FNB", 500.0, "verified"),
        ("nomvula", hashlib.sha256("password5".encode()).hexdigest(), "Nomvula Shabalala", "nomvula@email.com", "0878901234", "member", "5678901234", "FNB", 500.0, "verified"),
        ("kgosi", hashlib.sha256("password6".encode()).hexdigest(), "Kgosi Moloi", "kgosi@email.com", "0889012345", "member", "6789012345", "FNB", 500.0, "pending"),
        ("lerato", hashlib.sha256("password7".encode()).hexdigest(), "Lerato Mokoena", "lerato@email.com", "0890123456", "member", "7890123456", "FNB", 500.0, "verified"),
        ("mpho", hashlib.sha256("password8".encode()).hexdigest(), "Mpho Ndlovu", "mpho@email.com", "0801234567", "member", "8901234567", "FNB", 500.0, "verified"),
        ("nomsa", hashlib.sha256("password9".encode()).hexdigest(), "Nomsa Khumalo", "nomsa@email.com", "0812345678", "member", "9012345678", "FNB", 500.0, "pending"),
        ("themba", hashlib.sha256("password10".encode()).hexdigest(), "Themba Mthembu", "themba@email.com", "0823456789", "member", "0123456789", "FNB", 500.0, "verified"),
        ("zanele", hashlib.sha256("password11".encode()).hexdigest(), "Zanele Sibiya", "zanele@email.com", "0834567891", "member", "1123456789", "FNB", 500.0, "verified"),
        ("lucas", hashlib.sha256("password12".encode()).hexdigest(), "Lucas Botha", "lucas@email.com", "0845678912", "member", "2123456789", "FNB", 500.0, "verified"),
        ("grace", hashlib.sha256("password13".encode()).hexdigest(), "Grace Molefe", "grace@email.com", "0856789123", "member", "3123456789", "FNB", 500.0, "pending"),
        ("david", hashlib.sha256("password14".encode()).hexdigest(), "David Fourie", "david@email.com", "0867891234", "member", "4123456789", "FNB", 500.0, "verified"),
        ("palesa", hashlib.sha256("password15".encode()).hexdigest(), "Palesa Ramokgopa", "palesa@email.com", "0878912345", "member", "5123456789", "FNB", 500.0, "verified"),
        ("kabelo", hashlib.sha256("password16".encode()).hexdigest(), "Kabelo Maimane", "kabelo@email.com", "0889123456", "member", "6123456789", "FNB", 500.0, "verified"),
        ("amanda", hashlib.sha256("password17".encode()).hexdigest(), "Amanda du Plessis", "amanda@email.com", "0891234567", "member", "7123456789", "FNB", 500.0, "pending"),
        ("jabulani", hashlib.sha256("password18".encode()).hexdigest(), "Jabulane Mchunu", "jabulani@email.com", "0802345678", "member", "8123456789", "FNB", 500.0, "verified"),
        ("ntombi", hashlib.sha256("password19".encode()).hexdigest(), "Ntombi Gcabashe", "ntombi@email.com", "0813456789", "member", "9123456789", "FNB", 500.0, "verified"),
        ("pieter", hashlib.sha256("password20".encode()).hexdigest(), "Pieter van Wyk", "pieter@email.com", "0824567890", "member", "1023456789", "FNB", 500.0, "verified"),
    ]
    
    for m in members:
        c.execute("INSERT OR IGNORE INTO Users (username, password_hash, full_name, email, phone, role, bank_account, bank_name, monthly_contribution, fica_status) VALUES (?,?,?,?,?,?,?,?,?,?)", m)
    
    # Seed contributions with realistic arrears patterns
    c.execute("SELECT user_id, username FROM Users WHERE role='member'")
    uids = c.fetchall()
    current_year = datetime.now().year
    
    # Users with arrears patterns: 3,6,9,13,18 (30% missing, 20% partial)
    arrears_users = {3, 6, 9, 13, 18}
    
    for uid, uname in uids:
        for month in range(1, datetime.now().month + 1):
            if uid in arrears_users:
                r = random.random()
                if r < 0.3:
                    status = "pending"
                    amount = 0.0
                elif r < 0.5:
                    status = "partial"
                    amount = random.choice([250.0, 300.0])
                else:
                    status = random.choice(["verified", "paid"])
                    amount = 500.0
            else:
                status = random.choice(["verified", "paid"])
                amount = 500.0
            c.execute("INSERT INTO Monthly_Contributions (user_id, year, month, amount, status) VALUES (?,?,?,?,?)",
                      (uid, current_year, month, amount, status))
    
    # Seed investments
    investments = [
        ("Sasol Limited", "JSE Stocks", 50000.0, 62000.0, "2024-01-15", "Energy sector exposure"),
        ("SARB Retail Bond", "SARB Bonds", 30000.0, 33525.0, "2024-02-01", "Fixed income at 11.75%"),
        ("Naspers/Prosus", "JSE Stocks", 45000.0, 51000.0, "2024-03-10", "Tech sector exposure"),
        ("Growthpoint Properties", "Property", 25000.0, 27500.0, "2024-04-05", "REIT dividend income"),
        ("Satrix 40 ETF", "ETFs", 20000.0, 22800.0, "2024-05-20", "Broad market exposure"),
    ]
    for inv in investments:
        c.execute("INSERT INTO Investments (name, investment_type, amount_invested, current_value, purchase_date, notes) VALUES (?,?,?,?,?,?)", inv)
    
    # Seed suggestions
    suggestions = [
        (2, "Invest in Kumba Iron Ore", "Strong iron ore prices and demand from China.", "JSE Stocks", 40000.0),
        (3, "Buy Government Retail Bonds", "Safe 11.75% return with no risk.", "SARB Bonds", 50000.0),
        (4, "Add Bitcoin to Portfolio", "Small crypto allocation for diversification.", "Crypto", 10000.0),
    ]
    for s in suggestions:
        c.execute("INSERT INTO Suggestions (user_id, title, description, investment_type, amount) VALUES (?,?,?,?,?)", s)
    
    # Seed notifications for admin
    notifications = [
        (1, "New Member Joined", "Lindiwe Dlamini has completed registration.", "info"),
        (1, "Payment Received", "Sipho Mabena paid R500 for July.", "success"),
        (1, "Vote Required", "New proposal: Invest in Kumba Iron Ore", "warning"),
    ]
    for n in notifications:
        c.execute("INSERT INTO Notifications (user_id, title, message, type) VALUES (?,?,?,?)", n)
    
    conn.commit()
    conn.close()

# ============================================================
# CSS & THEME
# ============================================================
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

# ============================================================
# FNB API CLIENT (Simulated)
# ============================================================
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

# ============================================================
# AUTH & UTILITIES
# ============================================================
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
