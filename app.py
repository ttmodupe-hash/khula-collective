"""
Khula Collective - Enhanced Investment Club App
South African Investment Club Management Platform
=================================================
A comprehensive, single-file Streamlit application for managing
investment club members, contributions, investments, and governance.

Features:
- Admin Panel with member management, FICA compliance, data export
- Member Directory with leaderboards and activity status
- Enhanced Notifications with announcement broadcasting
- Reports & Analytics with contribution heatmaps and participation charts
- Enhanced AI Advisor with risk assessment and investment calculator
- WhatsApp Integration UI
- Dark/Light Theme Toggle
- Mobile-first responsive design with bottom navigation
"""

import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import random
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import os
import time
import base64
from io import BytesIO
from functools import wraps

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Khula Collective",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# CONSTANTS & CONFIGURATION
# ============================================================
DB_PATH = "khula_collective.db"
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

INVESTMENT_TYPES = [
    "Stocks (JSE)", "ETF / Index Fund", "Property (REITs)",
    "Government Bonds", "Crypto", "Business Venture",
    "Unit Trust", "Money Market", "Fixed Deposit"
]

SA_NEWS_HEADLINES = [
    ("SARB keeps repo rate steady at 8.25% amid inflation concerns", "The Monetary Policy Committee cited persistent global and domestic inflation risks. Analysts expect a hold until Q3 2025.", "Neutral"),
    ("JSE All Share Index hits new milestone", "The FTSE/JSE All Share Index surged past 82,000 points, driven by strong resource sector performance.", "Positive"),
    ("Rand strengthens against major currencies", "The South African Rand gained 2.3% against the US Dollar following improved trade balance data.", "Positive"),
    ("New tax incentives for small investment clubs announced", "Treasury has introduced Section 12T incentives to encourage collective investment schemes among historically disadvantaged groups.", "Positive"),
    ("FNB launches new investment product for stokvels", "First National Bank has unveiled a dedicated stokvel investment account with zero monthly fees.", "Positive"),
    ("SA inflation cools to 4.5% in latest data", "Consumer Price Index data shows inflation moderating, raising hopes for rate cuts later this year.", "Positive"),
    ("Load shedding impact on mining stocks continues", "Mining shares on the JSE remain volatile as Eskom implements Stage 4 rolling blackouts.", "Negative"),
    ("New FICA regulations effective from next quarter", "Financial Intelligence Centre amendments will require enhanced due diligence for all financial club transactions above R25,000.", "Neutral"),
    ("Discovery Limited announces record earnings", "Discovery's share price rose 5% after reporting a 23% increase in full-year operating profit.", "Positive"),
    ("Property market shows signs of recovery in Gauteng", "Residential property prices in Johannesburg and Pretoria increased by 3.2% year-on-year.", "Positive"),
    ("Nedbank issues cautious outlook for 2025", "Nedbank's economists predict subdued GDP growth of 1.2% for the coming year.", "Neutral"),
    ("South Africa's GDP grows 0.6% in Q4", "Statistics South Africa reports modest growth driven by the agriculture and finance sectors.", "Neutral"),
    ("Crypto regulation framework proposed in Parliament", "A new bill aims to provide clarity on cryptocurrency taxation and trading requirements for South Africans.", "Neutral"),
    ("Absa launches AI-powered investment advisory tool", "Absa customers can now access robo-advisory services for portfolio management.", "Neutral"),
    ("Sasol announces renewable energy transition plan", "Sasol shares dipped 3% as the company outlined a R100 billion decarbonisation strategy.", "Negative"),
]

# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_db_connection():
    """Create a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all database tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            surname TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            id_number TEXT,
            is_admin INTEGER DEFAULT 0,
            constitution_signed INTEGER DEFAULT 0,
            constitution_signed_date TEXT,
            join_date TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            fica_verified INTEGER DEFAULT 0,
            fica_doc_path TEXT,
            last_login TEXT,
            theme_preference TEXT DEFAULT 'dark'
        )
    """)

    # Monthly Contributions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Monthly_Contributions (
            contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            status TEXT DEFAULT 'unpaid',
            payment_date TEXT,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    # Suggestions table (Member Voice)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Suggestions (
            suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            suggestion_text TEXT NOT NULL,
            votes INTEGER DEFAULT 0,
            voters TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    # Announcements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Announcements (
            announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            priority TEXT DEFAULT 'normal',
            FOREIGN KEY (created_by) REFERENCES Users(user_id)
        )
    """)

    # Investments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Investments (
            investment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT,
            amount_invested REAL NOT NULL DEFAULT 0,
            return_rate REAL DEFAULT 0,
            start_date TEXT NOT NULL,
            end_date TEXT,
            status TEXT DEFAULT 'active',
            notes TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (created_by) REFERENCES Users(user_id)
        )
    """)

    # Notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            notification_type TEXT DEFAULT 'general',
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    conn.commit()
    conn.close()


def ensure_db_initialized(func):
    """Decorator to ensure database is initialized before executing function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        init_db()
        return func(*args, **kwargs)
    return wrapper


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


# ============================================================
# USER AUTHENTICATION
# ============================================================

@ensure_db_initialized
def authenticate_user(username: str, password: str):
    """Authenticate a user and return user data if valid."""
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = hash_password(password)
    cursor.execute(
        "SELECT * FROM Users WHERE username = ? AND password_hash = ? AND is_active = 1",
        (username, password_hash)
    )
    user = cursor.fetchone()
    if user:
        cursor.execute(
            "UPDATE Users SET last_login = ? WHERE user_id = ?",
            (datetime.now().isoformat(), user["user_id"])
        )
        conn.commit()
    conn.close()
    return dict(user) if user else None


@ensure_db_initialized
def get_user_by_id(user_id: int):
    """Get user data by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


@ensure_db_initialized
def get_all_active_members():
    """Get all active non-admin members."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Users WHERE is_admin = 0 AND is_active = 1 ORDER BY join_date DESC"
    )
    members = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return members


@ensure_db_initialized
def get_all_members():
    """Get all members including inactive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users ORDER BY join_date DESC")
    members = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return members


@ensure_db_initialized
def add_member(username, password, first_name, surname, email, phone, id_number, is_admin=False):
    """Add a new member to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        password_hash = hash_password(password)
        join_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO Users (username, password_hash, first_name, surname, email, phone, id_number, is_admin, join_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (username, password_hash, first_name, surname, email, phone, id_number, 1 if is_admin else 0, join_date))
        user_id = cursor.lastrowid
        conn.commit()
        # Create notification for new member
        create_notification(user_id, f"Welcome to Khula Collective, {first_name}! Please sign the constitution and make your first contribution.", "welcome")
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


@ensure_db_initialized
def update_member_status(user_id, is_active):
    """Activate or deactivate a member."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET is_active = ? WHERE user_id = ?", (1 if is_active else 0, user_id))
    conn.commit()
    conn.close()


@ensure_db_initialized
def update_fica_status(user_id, fica_verified):
    """Update FICA verification status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET fica_verified = ? WHERE user_id = ?", (1 if fica_verified else 0, user_id))
    conn.commit()
    conn.close()


@ensure_db_initialized
def delete_member(user_id):
    """Delete a member and their associated data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Monthly_Contributions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM Suggestions WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM Notifications WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ============================================================
# CONTRIBUTION FUNCTIONS
# ============================================================

@ensure_db_initialized
def get_member_contributions(user_id: int):
    """Get all contributions for a member."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Monthly_Contributions WHERE user_id = ? ORDER BY year DESC, month DESC",
        (user_id,)
    )
    contributions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return contributions


@ensure_db_initialized
def get_all_contributions():
    """Get all contributions with member details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mc.*, u.first_name, u.surname, u.username
        FROM Monthly_Contributions mc
        JOIN Users u ON mc.user_id = u.user_id
        ORDER BY mc.year DESC, mc.month DESC
    """)
    contributions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return contributions


@ensure_db_initialized
def update_contribution_status(contribution_id, status, payment_date=None):
    """Mark a contribution as paid or unpaid."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if status == 'paid' and not payment_date:
        payment_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "UPDATE Monthly_Contributions SET status = ?, payment_date = ? WHERE contribution_id = ?",
        (status, payment_date, contribution_id)
    )
    conn.commit()
    conn.close()


@ensure_db_initialized
def add_contribution(user_id, year, month, amount, status='unpaid'):
    """Add or update a contribution record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if contribution exists
    cursor.execute(
        "SELECT contribution_id FROM Monthly_Contributions WHERE user_id = ? AND year = ? AND month = ?",
        (user_id, year, month)
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            "UPDATE Monthly_Contributions SET amount = ?, status = ? WHERE contribution_id = ?",
            (amount, status, existing["contribution_id"])
        )
    else:
        cursor.execute(
            "INSERT INTO Monthly_Contributions (user_id, year, month, amount, status) VALUES (?, ?, ?, ?, ?)",
            (user_id, year, month, amount, status)
        )
    conn.commit()
    conn.close()


@ensure_db_initialized
def get_total_contributions():
    """Get total contributions across all members."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM Monthly_Contributions WHERE status = 'paid'")
    total = cursor.fetchone()["total"] or 0
    conn.close()
    return total


@ensure_db_initialized
def get_member_total_contribution(user_id):
    """Get total contribution for a specific member."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM Monthly_Contributions WHERE user_id = ? AND status = 'paid'",
        (user_id,)
    )
    total = cursor.fetchone()["total"] or 0
    conn.close()
    return total


@ensure_db_initialized
def get_contribution_heatmap_data(year=None):
    """Get contribution data formatted for heatmap visualization."""
    if year is None:
        year = datetime.now().year
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.first_name || ' ' || u.surname as member,
               mc.month, mc.status
        FROM Monthly_Contributions mc
        JOIN Users u ON mc.user_id = u.user_id
        WHERE mc.year = ? AND u.is_active = 1 AND u.is_admin = 0
        ORDER BY u.join_date, mc.month
    """, (year,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# SUGGESTION / MEMBER VOICE FUNCTIONS
# ============================================================

@ensure_db_initialized
def get_all_suggestions():
    """Get all suggestions with member details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, u.first_name, u.surname
        FROM Suggestions s
        JOIN Users u ON s.user_id = u.user_id
        ORDER BY s.votes DESC, s.created_at DESC
    """)
    suggestions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return suggestions


@ensure_db_initialized
def add_suggestion(user_id, suggestion_text):
    """Add a new suggestion."""
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO Suggestions (user_id, suggestion_text, created_at) VALUES (?, ?, ?)",
        (user_id, suggestion_text, created_at)
    )
    conn.commit()
    conn.close()


@ensure_db_initialized
def vote_suggestion(suggestion_id, user_id):
    """Vote for a suggestion. Returns True if vote was added, False if already voted."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT voters FROM Suggestions WHERE suggestion_id = ?", (suggestion_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return False
    voters = json.loads(result["voters"])
    if user_id in voters:
        conn.close()
        return False
    voters.append(user_id)
    cursor.execute(
        "UPDATE Suggestions SET votes = votes + 1, voters = ? WHERE suggestion_id = ?",
        (json.dumps(voters), suggestion_id)
    )
    conn.commit()
    conn.close()
    return True


# ============================================================
# ANNOUNCEMENT FUNCTIONS
# ============================================================

@ensure_db_initialized
def get_active_announcements():
    """Get all active announcements."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.first_name || ' ' || u.surname as author_name
        FROM Announcements a
        JOIN Users u ON a.created_by = u.user_id
        WHERE a.is_active = 1
        ORDER BY a.created_at DESC
    """)
    announcements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return announcements


@ensure_db_initialized
def get_all_announcements():
    """Get all announcements (admin view)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.first_name || ' ' || u.surname as author_name
        FROM Announcements a
        JOIN Users u ON a.created_by = u.user_id
        ORDER BY a.created_at DESC
    """)
    announcements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return announcements


@ensure_db_initialized
def add_announcement(title, message, created_by, priority='normal'):
    """Add a new announcement."""
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO Announcements (title, message, created_by, created_at, priority) VALUES (?, ?, ?, ?, ?)",
        (title, message, created_by, created_at, priority)
    )
    announcement_id = cursor.lastrowid
    conn.commit()
    # Notify all members
    cursor.execute("SELECT user_id FROM Users WHERE is_active = 1 AND is_admin = 0")
    members = cursor.fetchall()
    for member in members:
        create_notification(
            member["user_id"],
            f"New announcement: {title}",
            "announcement",
            conn=conn
        )
    conn.close()
    return announcement_id


@ensure_db_initialized
def toggle_announcement_status(announcement_id):
    """Toggle announcement active/inactive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Announcements SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE announcement_id = ?",
        (announcement_id,)
    )
    conn.commit()
    conn.close()


# ============================================================
# INVESTMENT FUNCTIONS
# ============================================================

@ensure_db_initialized
def get_all_investments():
    """Get all investments."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.*, u.first_name || ' ' || u.surname as created_by_name
        FROM Investments i
        LEFT JOIN Users u ON i.created_by = u.user_id
        ORDER BY i.created_at DESC
    """)
    investments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return investments


@ensure_db_initialized
def add_investment(name, inv_type, amount_invested, return_rate, start_date, notes="", created_by=None):
    """Add a new investment."""
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO Investments (name, type, amount_invested, return_rate, start_date, notes, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (name, inv_type, amount_invested, return_rate, start_date, notes, created_by, created_at)
    )
    conn.commit()
    conn.close()


@ensure_db_initialized
def update_investment_status(investment_id, status):
    """Update investment status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Investments SET status = ? WHERE investment_id = ?",
        (status, investment_id)
    )
    conn.commit()
    conn.close()


# ============================================================
# NOTIFICATION FUNCTIONS
# ============================================================

@ensure_db_initialized
def create_notification(user_id, message, notification_type='general', conn=None):
    """Create a notification for a user. If conn is provided, use it (transactional)."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO Notifications (user_id, message, notification_type, created_at) VALUES (?, ?, ?, ?)",
        (user_id, message, notification_type, created_at)
    )
    if close_conn:
        conn.commit()
        conn.close()


@ensure_db_initialized
def get_user_notifications(user_id):
    """Get all notifications for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user_id,)
    )
    notifications = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return notifications


@ensure_db_initialized
def get_unread_notification_count(user_id):
    """Get count of unread notifications."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as count FROM Notifications WHERE user_id = ? AND is_read = 0",
        (user_id,)
    )
    count = cursor.fetchone()["count"]
    conn.close()
    return count


@ensure_db_initialized
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Notifications SET is_read = 1 WHERE notification_id = ?",
        (notification_id,)
    )
    conn.commit()
    conn.close()


@ensure_db_initialized
def mark_all_notifications_read(user_id):
    """Mark all notifications as read for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE Notifications SET is_read = 1 WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


# ============================================================
# CONSTITUTION FUNCTIONS
# ============================================================

@ensure_db_initialized
def sign_constitution(user_id):
    """Mark constitution as signed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    signed_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE Users SET constitution_signed = 1, constitution_signed_date = ? WHERE user_id = ?",
        (signed_date, user_id)
    )
    conn.commit()
    conn.close()


# ============================================================
# DEMO DATA SEEDING
# ============================================================

@ensure_db_initialized
def seed_demo_data():
    """Seed the database with demo data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if we already have users
    cursor.execute("SELECT COUNT(*) as count FROM Users")
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return

    # Create admin user
    admin_id = add_member(
        username="admin",
        password="admin123",
        first_name="Thabo",
        surname="Mokoena",
        email="admin@khulacollective.co.za",
        phone="+27 82 123 4567",
        id_number="7501015800085",
        is_admin=True
    )
    if admin_id:
        cursor.execute("UPDATE Users SET is_admin = 1, fica_verified = 1, constitution_signed = 1 WHERE user_id = ?", (admin_id,))

    # Create member users
    members = [
        ("siphoo", "password1", "Sipho", "Dlamini", "sipho.d@email.co.za", "+27 83 234 5678", "8002155103087"),
        ("lerato", "password2", "Lerato", "Nkosi", "lerato.n@email.co.za", "+27 84 345 6789", "9003106209083"),
        ("jabulani", "password3", "Jabulani", "Zulu", "jabulani.z@email.co.za", "+27 85 456 7890", "8504127502081"),
        ("nomvula", "password4", "Nomvula", "Mahlangu", "nomvula.m@email.co.za", "+27 86 567 8901", "9205250804089"),
        ("tendai", "password5", "Tendai", "Mupfumi", "tendai.m@email.co.za", "+27 87 678 9012", "7806305101082"),
        ("amahle", "password6", "Amahle", "Buthelezi", "amahle.b@email.co.za", "+27 88 789 0123", "9501014405086"),
        ("kagiso", "password7", "Kagiso", "Molefe", "kagiso.m@email.co.za", "+27 89 890 1234", "8107126206084"),
    ]

    member_ids = []
    for username, pwd, fname, surname, email, phone, id_num in members:
        mid = add_member(username, pwd, fname, surname, email, phone, id_num)
        if mid:
            member_ids.append(mid)
            # Sign constitution for most members
            if random.random() > 0.2:
                cursor.execute("UPDATE Users SET constitution_signed = 1 WHERE user_id = ?", (mid,))
            # FICA verify some members
            if random.random() > 0.3:
                cursor.execute("UPDATE Users SET fica_verified = 1 WHERE user_id = ?", (mid,))

    # Seed contributions for 2024 and 2025
    current_year = datetime.now().year
    for year in [current_year - 1, current_year]:
        for month in range(1, 13):
            if year == current_year and month > datetime.now().month:
                continue
            for mid in member_ids:
                amount = 500.00  # Monthly contribution
                # Random status based on month
                if year < current_year or (year == current_year and month < datetime.now().month):
                    status = random.choice(['paid', 'paid', 'paid', 'unpaid'])
                elif month == datetime.now().month:
                    status = random.choice(['paid', 'unpaid', 'unpaid'])
                else:
                    continue
                payment_date = None
                if status == 'paid':
                    day = random.randint(1, 28)
                    payment_date = f"{year}-{month:02d}-{day:02d}"
                cursor.execute(
                    "INSERT INTO Monthly_Contributions (user_id, year, month, amount, status, payment_date) VALUES (?, ?, ?, ?, ?, ?)",
                    (mid, year, month, amount, status, payment_date)
                )

    # Seed suggestions
    suggestions = [
        (member_ids[0], "Invest in Top 40 JSE ETFs for stable long-term growth"),
        (member_ids[1], "Consider Sasol shares - they are undervalued right now"),
        (member_ids[2], "Buy property in Soweto - gentrification is pushing values up"),
        (member_ids[3], "Diversify into renewable energy stocks"),
        (member_ids[4], "Create an emergency fund of 3 months expenses first"),
    ]
    for mid, text in suggestions:
        votes = random.randint(2, 6)
        voters = json.dumps(random.sample(member_ids, min(votes, len(member_ids))))
        created_at = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO Suggestions (user_id, suggestion_text, votes, voters, created_at) VALUES (?, ?, ?, ?, ?)",
            (mid, text, votes, voters, created_at)
        )

    # Seed investments
    investments = [
        ("JSE Top 40 ETF", "ETF / Index Fund", 15000, 12.5, "2024-01-15", "Core portfolio holding tracking the FTSE/JSE Top 40 index"),
        ("Discovery Limited Shares", "Stocks (JSE)", 8000, 18.2, "2024-03-10", "Insurance and healthcare conglomerate with strong growth"),
        ("Sasol Recovery Play", "Stocks (JSE)", 5000, -3.5, "2024-06-01", "Speculative position on Sasol turnaround and energy transition"),
        ("Government Retail Savings Bonds", "Government Bonds", 10000, 9.75, "2024-02-20", "Fixed rate retail savings bond, 5-year term"),
        ("TSIBA Property Fund", "Property (REITs)", 7000, 7.8, "2024-08-15", "Commercial property REIT focused on township retail"),
    ]
    for name, inv_type, amount, rate, start, notes in investments:
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO Investments (name, type, amount_invested, return_rate, start_date, notes, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, inv_type, amount, rate, start, notes, admin_id, created_at)
        )

    # Seed announcements
    announcements = [
        ("Welcome to Khula Collective!", "We are excited to launch our investment club. Please complete your profile and sign the digital constitution.", "normal"),
        ("Monthly Contribution Due", "Remember that monthly contributions of R500 are due by the 7th of each month. Use the FNB account details in your profile.", "normal"),
        ("JSE Top 40 Investment Approved", "The club has approved our first investment of R15,000 in the JSE Top 40 ETF. Great start everyone!", "success"),
        ("FICA Reminder", "All members must submit FICA documents before the end of the quarter. Please upload your ID and proof of address.", "urgent"),
    ]
    for title, msg, priority in announcements:
        created_at = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO Announcements (title, message, created_by, created_at, priority, is_active) VALUES (?, ?, ?, ?, ?, 1)",
            (title, msg, admin_id, created_at, priority)
        )

    conn.commit()
    conn.close()


# ============================================================
# CUSTOM CSS STYLING
# ============================================================

def load_css(theme="dark"):
    """Load custom CSS with theme support."""
    if theme == "dark":
        css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .main {
            background: linear-gradient(135deg, #0a0a0a 0%, #111827 50%, #0f172a 100%);
            color: #e5e7eb;
        }

        /* Card Styling */
        .stCard {
            background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(31,41,55,0.9));
            border: 1px solid rgba(75,85,99,0.3);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .metric-card {
            background: linear-gradient(145deg, rgba(16,185,129,0.1), rgba(6,182,212,0.05));
            border: 1px solid rgba(16,185,129,0.2);
            border-radius: 16px;
            padding: 1.25rem;
            text-align: center;
            backdrop-filter: blur(10px);
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #10b981, #06b6d4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .metric-label {
            font-size: 0.85rem;
            color: #9ca3af;
            margin-top: 0.25rem;
        }

        /* Header */
        .app-header {
            text-align: center;
            padding: 2rem 1rem;
            background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(6,182,212,0.1));
            border-radius: 20px;
            margin-bottom: 2rem;
            border: 1px solid rgba(16,185,129,0.2);
        }

        .app-title {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #10b981, #06b6d4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }

        .app-subtitle {
            color: #9ca3af;
            font-size: 1rem;
        }

        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #10b981, #06b6d4) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 0.6rem 1.5rem !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 15px rgba(16,185,129,0.4) !important;
        }

        .stButton > button[kind="secondary"] {
            background: transparent !important;
            border: 1px solid rgba(16,185,129,0.4) !important;
            color: #10b981 !important;
        }

        /* Inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            background: rgba(31,41,55,0.8) !important;
            border: 1px solid rgba(75,85,99,0.4) !important;
            color: #e5e7eb !important;
            border-radius: 10px !important;
        }

        /* Select */
        .stSelectbox > div > div > select,
        div[data-baseweb="select"] {
            background: rgba(31,41,55,0.8) !important;
            border-color: rgba(75,85,99,0.4) !important;
        }

        /* Notification badge */
        .notification-badge {
            position: relative;
            display: inline-block;
        }

        .notification-badge .badge {
            position: absolute;
            top: -8px;
            right: -8px;
            background: linear-gradient(135deg, #ef4444, #f97316);
            color: white;
            border-radius: 50%;
            padding: 2px 6px;
            font-size: 0.7rem;
            font-weight: 700;
        }

        /* Member card */
        .member-card {
            background: linear-gradient(145deg, rgba(17,24,39,0.95), rgba(31,41,55,0.9));
            border: 1px solid rgba(75,85,99,0.3);
            border-radius: 14px;
            padding: 1.25rem;
            margin-bottom: 0.75rem;
            transition: all 0.2s ease;
        }

        .member-card:hover {
            border-color: rgba(16,185,129,0.4);
            transform: translateY(-2px);
        }

        /* Status badges */
        .badge-paid {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-unpaid {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-fica-yes {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-fica-no {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        /* Section titles */
        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #e5e7eb;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid rgba(16,185,129,0.3);
        }

        /* Bottom nav for mobile */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(17,24,39,0.95);
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(75,85,99,0.3);
            padding: 0.5rem 0;
            z-index: 999;
            display: flex;
            justify-content: space-around;
            align-items: center;
        }

        .bottom-nav-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            color: #9ca3af;
            font-size: 0.7rem;
            cursor: pointer;
            transition: color 0.2s ease;
            padding: 0.25rem 0.75rem;
        }

        .bottom-nav-item:hover,
        .bottom-nav-item.active {
            color: #10b981;
        }

        .bottom-nav-item i {
            font-size: 1.25rem;
            margin-bottom: 2px;
        }

        /* Suggestion card */
        .suggestion-card {
            background: rgba(31,41,55,0.6);
            border: 1px solid rgba(75,85,99,0.3);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            border-left: 4px solid #10b981;
        }

        /* Chart container */
        .chart-container {
            background: rgba(17,24,39,0.5);
            border-radius: 16px;
            padding: 1rem;
            border: 1px solid rgba(75,85,99,0.2);
        }

        /* Data table styling */
        .dataframe {
            background: rgba(17,24,39,0.5) !important;
            border-radius: 10px !important;
        }

        .dataframe th {
            background: rgba(16,185,129,0.2) !important;
            color: #e5e7eb !important;
        }

        .dataframe td {
            color: #d1d5db !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(17,24,39,0.5);
            padding: 8px;
            border-radius: 12px;
        }

        .stTabs [data-baseweb="tab"] {
            color: #9ca3af;
            border-radius: 8px;
            padding: 8px 16px;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #10b981, #06b6d4) !important;
            color: white !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #111827;
        }
        ::-webkit-scrollbar-thumb {
            background: #374151;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #4b5563;
        }

        /* Animation */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .animate-fade-in {
            animation: fadeIn 0.5s ease forwards;
        }

        /* Constitution section */
        .constitution-box {
            background: rgba(31,41,55,0.6);
            border: 1px solid rgba(75,85,99,0.3);
            border-radius: 12px;
            padding: 1.5rem;
            max-height: 400px;
            overflow-y: auto;
            font-size: 0.85rem;
            line-height: 1.6;
        }

        /* Toast notification */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #10b981, #06b6d4);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }

        @keyframes slideIn {
            from { transform: translateX(100%); }
            to { transform: translateX(0); }
        }
        </style>
        """
    else:
        # Light theme CSS
        css = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .main {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #ecfdf5 100%);
            color: #1f2937;
        }

        .stCard {
            background: white;
            border: 1px solid rgba(16,185,129,0.2);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .metric-card {
            background: linear-gradient(145deg, rgba(16,185,129,0.1), rgba(6,182,212,0.05));
            border: 1px solid rgba(16,185,129,0.2);
            border-radius: 16px;
            padding: 1.25rem;
            text-align: center;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #059669, #0891b2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .metric-label {
            font-size: 0.85rem;
            color: #6b7280;
        }

        .app-header {
            text-align: center;
            padding: 2rem 1rem;
            background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(6,182,212,0.05));
            border-radius: 20px;
            margin-bottom: 2rem;
            border: 1px solid rgba(16,185,129,0.2);
        }

        .app-title {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #059669, #0891b2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stButton > button {
            background: linear-gradient(135deg, #10b981, #06b6d4) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


# ============================================================
# SESSION STATE MANAGEMENT
# ============================================================

def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "authenticated": False,
        "user": None,
        "current_page": "dashboard",
        "theme": "dark",
        "notifications_read": False,
        "show_login": True,
        "constitution_signed": False,
        "risk_score": None,
        "risk_answers": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout():
    """Clear session state and log out."""
    keys = list(st.session_state.keys())
    for key in keys:
        del st.session_state[key]
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.current_page = "dashboard"
    st.session_state.theme = "dark"
    st.session_state.show_login = True
    st.rerun()


def navigate_to(page: str):
    """Navigate to a specific page."""
    st.session_state.current_page = page
    st.rerun()


# ============================================================
# PAGE RENDERING FUNCTIONS
# ============================================================

def render_login():
    """Render the login page."""
    st.markdown("""
    <div class="app-header">
        <div class="app-title">📈 Khula Collective</div>
        <div class="app-subtitle">South African Investment Club Platform</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h3 style="color: #9ca3af; font-weight: 400;">Welcome Back</h3>
            <p style="color: #6b7280; font-size: 0.9rem;">Sign in to your investment club account</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.session_state.theme = user.get("theme_preference", "dark")
                        st.success(f"Welcome back, {user['first_name']}! ✓")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")

        st.markdown("""
        <div style="margin-top: 1.5rem; padding: 1rem; background: rgba(31,41,55,0.5); border-radius: 12px;">
            <p style="color: #10b981; font-weight: 600; margin-bottom: 0.5rem;">👋 Demo Credentials</p>
            <p style="color: #9ca3af; font-size: 0.8rem; margin: 0;"><b>Admin:</b> username: <code>admin</code> | password: <code>admin123</code></p>
            <p style="color: #9ca3af; font-size: 0.8rem; margin: 0;"><b>Member:</b> username: <code>siphoo</code> | password: <code>password1</code></p>
        </div>
        """, unsafe_allow_html=True)


def render_header():
    """Render the app header with navigation and notification bell."""
    user = st.session_state.user

    # Theme toggle
    theme_icon = "☀️" if st.session_state.theme == "dark" else "🌙"
    theme_label = "Light" if st.session_state.theme == "dark" else "Dark"

    col1, col2, col3, col4 = st.columns([3, 1, 0.5, 0.5])

    with col1:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.5rem;">📈</span>
            <span style="font-size: 1.2rem; font-weight: 700; background: linear-gradient(135deg, #10b981, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Khula Collective
            </span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="text-align: right; color: #9ca3af; font-size: 0.85rem;">
            👋 {user['first_name']} {user['surname']}
            {' <span style="color: #fbbf24;">👑</span>' if user.get('is_admin') else ''}
        </div>
        """, unsafe_allow_html=True)

    with col3:
        if st.button(theme_icon, help=f"Switch to {theme_label} mode", key="theme_toggle"):
            new_theme = "light" if st.session_state.theme == "dark" else "dark"
            st.session_state.theme = new_theme
            st.rerun()

    with col4:
        unread = get_unread_notification_count(user["user_id"])
        bell_html = f"""
        <div style="position: relative; display: inline-block; cursor: pointer; font-size: 1.3rem;" onclick="window.location.reload()">
            🔔
            {f'<span style="position: absolute; top: -5px; right: -5px; background: linear-gradient(135deg, #ef4444, #f97316); color: white; border-radius: 50%; padding: 1px 5px; font-size: 0.6rem; font-weight: 700;">{unread}</span>' if unread > 0 else ''}
        </div>
        """
        st.markdown(bell_html, unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0.5rem 0; border-color: rgba(75,85,99,0.3);'>", unsafe_allow_html=True)


def render_sidebar_nav():
    """Render sidebar navigation."""
    user = st.session_state.user
    is_admin = user.get("is_admin", False)

    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <span style="font-size: 2rem;">📈</span>
        <br><strong style="color: #10b981;">Khula Collective</strong>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<hr>", unsafe_allow_html=True)

    nav_items = [
        ("dashboard", "📊", "Dashboard"),
        ("notifications", "🔔", "Notifications"),
        ("directory", "👥", "Members"),
        ("member_voice", "🗳️", "Member Voice"),
        ("ai_advisor", "🤖", "AI Advisor"),
        ("reports", "📈", "Reports"),
        ("profile", "👤", "My Profile"),
    ]

    if is_admin:
        nav_items.insert(1, ("admin", "👑", "Admin Panel"))

    for page, icon, label in nav_items:
        is_active = st.session_state.current_page == page
        btn_type = "primary" if is_active else "secondary"
        if st.sidebar.button(f"{icon} {label}", key=f"nav_{page}", use_container_width=True, type=btn_type):
            st.session_state.current_page = page
            st.rerun()

    st.sidebar.markdown("<hr>", unsafe_allow_html=True)

    # WhatsApp quick link
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 0.5rem;">
        <a href="https://wa.me/?text=Join%20Khula%20Collective%20on%20WhatsApp!" target="_blank" 
           style="text-decoration: none; color: #25D366; font-weight: 600;">
            💬 Join WhatsApp Group
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<hr>", unsafe_allow_html=True)

    if st.sidebar.button("🚪 Logout", use_container_width=True, type="secondary"):
        logout()


def render_dashboard():
    """Render the main dashboard."""
    user = st.session_state.user

    st.markdown("""
    <div class="section-title">📊 Dashboard</div>
    """, unsafe_allow_html=True)

    # Key metrics
    total_contributions = get_total_contributions()
    all_members = get_all_active_members()
    all_investments = get_all_investments()
    total_invested = sum(i["amount_invested"] for i in all_investments)
    total_return = sum(i["amount_invested"] * (i["return_rate"] / 100) for i in all_investments)
    current_value = total_invested + total_return

    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        ("💰 Collective Pot", f"R{total_contributions:,.2f}"),
        ("📈 Portfolio Value", f"R{current_value:,.2f}"),
        ("👥 Members", f"{len(all_members)}"),
        ("📊 Active Investments", f"{len([i for i in all_investments if i['status'] == 'active'])}"),
    ]
    for col, (label, value) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("""
        <div class="section-title" style="font-size: 1.1rem;">📈 Portfolio Growth (12-Month Projection)</div>
        """, unsafe_allow_html=True)

        # Project portfolio value
        months_ahead = 12
        monthly_contribution = len(all_members) * 500
        avg_return = 10.0  # assumed annual return
        monthly_rate = avg_return / 100 / 12

        projection_data = []
        current_val = current_value
        for m in range(months_ahead + 1):
            month_date = datetime.now() + relativedelta(months=m)
            projection_data.append({
                "Month": month_date.strftime("%b %Y"),
                "Projected Value": round(current_val, 2),
                "Contributions": round(total_invested + m * monthly_contribution * 0.5, 2)
            })
            current_val = current_val * (1 + monthly_rate) + monthly_contribution

        proj_df = pd.DataFrame(projection_data)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=proj_df["Month"], y=proj_df["Projected Value"],
            mode='lines+markers', name='Projected Value',
            line=dict(color='#10b981', width=3),
            fill='tozeroy', fillcolor='rgba(16,185,129,0.1)'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e5e7eb', family='Inter'),
            xaxis=dict(gridcolor='rgba(75,85,99,0.2)', tickangle=-45),
            yaxis=dict(gridcolor='rgba(75,85,99,0.2)', tickprefix='R'),
            margin=dict(l=40, r=40, t=30, b=60),
            height=350,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("""
        <div class="section-title" style="font-size: 1.1rem;">📊 Investment Allocation</div>
        """, unsafe_allow_html=True)

        if all_investments:
            inv_df = pd.DataFrame(all_investments)
            inv_summary = inv_df.groupby("type")["amount_invested"].sum().reset_index()

            fig = px.pie(inv_summary, values="amount_invested", names="type",
                        color_discrete_sequence=px.colors.sequential.Emerald)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e5e7eb', family='Inter'),
                margin=dict(l=20, r=20, t=30, b=20),
                height=350,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No investments yet. Visit the Member Voice to propose investments!")

    # Recent activity and announcements
    st.markdown("<br>", unsafe_allow_html=True)
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.markdown("""
        <div class="section-title" style="font-size: 1.1rem;">📢 Latest Announcements</div>
        """, unsafe_allow_html=True)

        announcements = get_active_announcements()
        for ann in announcements[:3]:
            priority_color = {"urgent": "#ef4444", "normal": "#10b981", "success": "#10b981"}.get(ann.get("priority", "normal"), "#10b981")
            st.markdown(f"""
            <div style="background: rgba(31,41,55,0.6); border-left: 4px solid {priority_color}; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
                <strong style="color: {priority_color};">{ann["title"]}</strong>
                <p style="color: #9ca3af; font-size: 0.8rem; margin: 0.25rem 0;">{ann["message"][:100]}{"..." if len(ann["message"]) > 100 else ""}</p>
                <span style="color: #6b7280; font-size: 0.7rem;">📅 {ann["created_at"][:10]}</span>
            </div>
            """, unsafe_allow_html=True)

    with col_right2:
        st.markdown("""
        <div class="section-title" style="font-size: 1.1rem;">🗳️ Top Member Suggestions</div>
        """, unsafe_allow_html=True)

        suggestions = get_all_suggestions()
        for sug in suggestions[:3]:
            st.markdown(f"""
            <div style="background: rgba(31,41,55,0.6); border-left: 4px solid #10b981; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
                <p style="color: #e5e7eb; font-size: 0.85rem; margin: 0 0 0.25rem 0;">{sug["suggestion_text"][:120]}{"..." if len(sug["suggestion_text"]) > 120 else ""}</p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #6b7280; font-size: 0.7rem;">💡 {sug["first_name"]} {sug["surname"]}</span>
                    <span style="color: #10b981; font-size: 0.8rem; font-weight: 600;">▲ {sug["votes"]} votes</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Quick actions
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="section-title" style="font-size: 1.1rem;">⚡ Quick Actions</div>
    """, unsafe_allow_html=True)

    qa_col1, qa_col2, qa_col3, qa_col4 = st.columns(4)
    with qa_col1:
        if st.button("🗳️ Vote Now", use_container_width=True, key="qa_vote"):
            st.session_state.current_page = "member_voice"
            st.rerun()
    with qa_col2:
        if st.button("📊 View Reports", use_container_width=True, key="qa_reports"):
            st.session_state.current_page = "reports"
            st.rerun()
    with qa_col3:
        if st.button("🤖 AI Advisor", use_container_width=True, key="qa_advisor"):
            st.session_state.current_page = "ai_advisor"
            st.rerun()
    with qa_col4:
        if st.button("👥 Members", use_container_width=True, key="qa_members"):
            st.session_state.current_page = "directory"
            st.rerun()



def render_admin_panel():
    """Render the admin panel page."""
    user = st.session_state.user
    if not user.get("is_admin"):
        st.error("⛔ Access Denied. Admin privileges required.")
        return

    st.markdown("""
    <div class="section-title">👑 Admin Panel</div>
    """, unsafe_allow_html=True)

    tab_members, tab_contributions, tab_announcements, tab_export, tab_investments = st.tabs([
        "👥 Member Management", "💰 Contributions", "📢 Announcements", "📤 Export Data", "📊 Investments"
    ])

    # Tab 1: Member Management
    with tab_members:
        st.markdown("### Add New Member")
        with st.form("add_member_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username*", key="new_username")
                new_password = st.text_input("Password*", type="password", key="new_password")
                new_fname = st.text_input("First Name*", key="new_fname")
                new_email = st.text_input("Email", key="new_email")
            with col2:
                new_surname = st.text_input("Surname*", key="new_surname")
                new_phone = st.text_input("Phone", key="new_phone")
                new_id = st.text_input("ID Number", key="new_id")
                new_admin = st.checkbox("Is Admin", key="new_admin")

            if st.form_submit_button("➕ Add Member", use_container_width=True):
                if not all([new_username, new_password, new_fname, new_surname]):
                    st.error("Please fill in all required fields (marked with *).")
                else:
                    uid = add_member(new_username, new_password, new_fname, new_surname,
                                   new_email, new_phone, new_id, new_admin)
                    if uid:
                        st.success(f"✅ Member '{new_fname} {new_surname}' added successfully!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Username already exists. Please choose a different username.")

        st.markdown("### All Members")
        all_members = get_all_members()
        members_df = pd.DataFrame(all_members) if all_members else pd.DataFrame()
        if not members_df.empty:
            display_df = members_df[["user_id", "username", "first_name", "surname", "email", "phone",
                                     "join_date", "is_active", "fica_verified", "constitution_signed", "is_admin"]].copy()
            display_df.columns = ["ID", "Username", "First Name", "Surname", "Email", "Phone",
                                 "Join Date", "Active", "FICA", "Constitution", "Admin"]
            display_df["Active"] = display_df["Active"].apply(lambda x: "✅ Yes" if x else "❌ No")
            display_df["FICA"] = display_df["FICA"].apply(lambda x: "✅" if x else "⚠️")
            display_df["Constitution"] = display_df["Constitution"].apply(lambda x: "✅" if x else "❌")
            display_df["Admin"] = display_df["Admin"].apply(lambda x: "👑" if x else "")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Member actions
            st.markdown("### Member Actions")
            member_action_col1, member_action_col2, member_action_col3 = st.columns(3)
            member_ids = [m["user_id"] for m in all_members if not m["is_admin"]]
            member_names = [f"{m['first_name']} {m['surname']} ({m['username']})" for m in all_members if not m["is_admin"]]

            with member_action_col1:
                if member_ids:
                    selected_member = st.selectbox("Select member", options=member_ids,
                                                   format_func=lambda x: member_names[member_ids.index(x)] if x in member_ids else "",
                                                   key="admin_member_select")
                else:
                    selected_member = None
                    st.info("No non-admin members.")

            with member_action_col2:
                if selected_member:
                    member_data = get_user_by_id(selected_member)
                    if member_data:
                        new_status = st.toggle("Active", value=bool(member_data["is_active"]), key="toggle_active")
                        if new_status != bool(member_data["is_active"]):
                            update_member_status(selected_member, new_status)
                            st.success(f"Member {'activated' if new_status else 'deactivated'}!")
                            time.sleep(0.5)
                            st.rerun()

            with member_action_col3:
                if selected_member and member_data:
                    new_fica = st.toggle("FICA Verified", value=bool(member_data["fica_verified"]), key="toggle_fica")
                    if new_fica != bool(member_data["fica_verified"]):
                        update_fica_status(selected_member, new_fica)
                        st.success(f"FICA status updated!")
                        time.sleep(0.5)

                        st.rerun()
        else:
            st.info("No members found. Add your first member above.")

    # Tab 2: Contributions
    with tab_contributions:
        st.markdown("### All Contributions")
        all_contribs = get_all_contributions()
        if all_contribs:
            contrib_df = pd.DataFrame(all_contribs)
            contrib_df["Month Name"] = contrib_df["month"].apply(lambda x: MONTHS[x-1])
            display_contrib = contrib_df[["first_name", "surname", "year", "Month Name", "amount", "status", "payment_date"]].copy()
            display_contrib.columns = ["First Name", "Surname", "Year", "Month", "Amount", "Status", "Payment Date"]

            # Filters
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                status_filter = st.multiselect("Filter by Status", options=["paid", "unpaid"], default=["paid", "unpaid"])
            with filter_col2:
                year_filter = st.multiselect("Filter by Year", options=sorted(display_contrib["Year"].unique()), default=sorted(display_contrib["Year"].unique()))

            filtered = display_contrib[
                (display_contrib["Status"].isin(status_filter)) &
                (display_contrib["Year"].isin(year_filter))
            ]

            st.dataframe(filtered, use_container_width=True, hide_index=True)

            # Mark as paid/unpaid
            st.markdown("### Update Contribution Status")
            update_col1, update_col2 = st.columns(2)
            with update_col1:
                contrib_ids = contrib_df["contribution_id"].tolist()
                contrib_labels = [f"{r['first_name']} {r['surname']} - {MONTHS[r['month']-1]} {r['year']} ({r['status']})" for _, r in contrib_df.iterrows()]
                selected_contrib = st.selectbox("Select contribution", options=contrib_ids, format_func=lambda x: contrib_labels[contrib_ids.index(x)], key="contrib_select")
            with update_col2:
                new_status = st.selectbox("New Status", options=["paid", "unpaid"], key="contrib_status")
                if st.button("Update Status", use_container_width=True):
                    update_contribution_status(selected_contrib, new_status)
                    st.success(f"Contribution marked as {new_status}!")
                    time.sleep(0.5)
                    st.rerun()

            # Summary stats
            st.markdown("### Contribution Summary")
            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
            total_expected = len(all_members) * 500 * 12 if all_members else 0
            total_paid = contrib_df[contrib_df["status"] == "paid"]["amount"].sum()
            paid_count = len(contrib_df[contrib_df["status"] == "paid"])
            unpaid_count = len(contrib_df[contrib_df["status"] == "unpaid"])

            with summary_col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem;">R{total_paid:,.2f}</div>
                    <div class="metric-label">Total Paid</div>
                </div>
                """, unsafe_allow_html=True)
            with summary_col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem;">R{total_expected - total_paid:,.2f}</div>
                    <div class="metric-label">Outstanding</div>
                </div>
                """, unsafe_allow_html=True)
            with summary_col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem; color: #10b981;">{paid_count}</div>
                    <div class="metric-label">Paid</div>
                </div>
                """, unsafe_allow_html=True)
            with summary_col4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem; color: #ef4444;">{unpaid_count}</div>
                    <div class="metric-label">Unpaid</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No contribution records found.")

    # Tab 3: Announcements
    with tab_announcements:
        st.markdown("### Broadcast Announcement")
        with st.form("announcement_form"):
            ann_title = st.text_input("Announcement Title*", key="ann_title")
            ann_message = st.text_area("Message*", key="ann_message", height=100)
            ann_priority = st.selectbox("Priority", options=["normal", "urgent", "success"], key="ann_priority")

            if st.form_submit_button("📢 Broadcast", use_container_width=True):
                if ann_title and ann_message:
                    add_announcement(ann_title, ann_message, user["user_id"], ann_priority)
                    st.success("✅ Announcement broadcasted to all members!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Please provide both title and message.")

        st.markdown("### Manage Announcements")
        all_ann = get_all_announcements()
        if all_ann:
            for ann in all_ann:
                with st.expander(f"{ann['title']} ({'Active' if ann['is_active'] else 'Inactive'}) - {ann['created_at'][:10]}"):
                    st.write(ann["message"])
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("Toggle Status", key=f"toggle_ann_{ann['announcement_id']}", use_container_width=True):
                            toggle_announcement_status(ann["announcement_id"])
                            st.rerun()
        else:
            st.info("No announcements yet.")

    # Tab 4: Export
    with tab_export:
        st.markdown("### Export Data")
        export_col1, export_col2 = st.columns(2)

        with export_col1:
            st.markdown("#### Members Export")
            if all_members:
                members_exp_df = pd.DataFrame(all_members)
                members_exp_df = members_exp_df[["user_id", "username", "first_name", "surname", "email", "phone",
                                                  "id_number", "join_date", "is_active", "fica_verified", "constitution_signed"]]
                csv_members = members_exp_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Members CSV",
                    data=csv_members,
                    file_name=f"khula_members_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with export_col2:
            st.markdown("#### Contributions Export")
            all_contribs_exp = get_all_contributions()
            if all_contribs_exp:
                contrib_exp_df = pd.DataFrame(all_contribs_exp)
                csv_contrib = contrib_exp_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Contributions CSV",
                    data=csv_contrib,
                    file_name=f"khula_contributions_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        # Full data export
        st.markdown("#### Full Database Export")
        if st.button("📦 Export All Data as Excel", use_container_width=True, type="primary"):
            try:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if all_members:
                        pd.DataFrame(all_members).to_excel(writer, sheet_name='Members', index=False)
                    all_contribs_xl = get_all_contributions()
                    if all_contribs_xl:
                        pd.DataFrame(all_contribs_xl).to_excel(writer, sheet_name='Contributions', index=False)
                    all_sugs = get_all_suggestions()
                    if all_sugs:
                        pd.DataFrame(all_sugs).to_excel(writer, sheet_name='Suggestions', index=False)
                    all_ann_xl = get_all_announcements()
                    if all_ann_xl:
                        pd.DataFrame(all_ann_xl).to_excel(writer, sheet_name='Announcements', index=False)
                    all_invs = get_all_investments()
                    if all_invs:
                        pd.DataFrame(all_invs).to_excel(writer, sheet_name='Investments', index=False)

                excel_data = output.getvalue()
                st.download_button(
                    label="📥 Download Excel File",
                    data=excel_data,
                    file_name=f"khula_full_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except ImportError:
                st.error("Please install openpyxl: `pip install openpyxl` for Excel export. CSV exports are available above.")

    # Tab 5: Investments Management
    with tab_investments:
        st.markdown("### Add Investment")
        with st.form("add_investment_form"):
            inv_name = st.text_input("Investment Name*", key="inv_name")
            inv_type = st.selectbox("Type", options=INVESTMENT_TYPES, key="inv_type")
            inv_amount = st.number_input("Amount Invested (R)*", min_value=0.0, step=100.0, key="inv_amount")
            inv_return = st.number_input("Expected Annual Return (%)", min_value=-100.0, max_value=100.0, step=0.5, key="inv_return")
            inv_date = st.date_input("Start Date", value=date.today(), key="inv_date")
            inv_notes = st.text_area("Notes", key="inv_notes")

            if st.form_submit_button("➕ Add Investment", use_container_width=True):
                if inv_name and inv_amount > 0:
                    add_investment(inv_name, inv_type, inv_amount, inv_return, inv_date.isoformat(), inv_notes, user["user_id"])
                    st.success(f"✅ Investment '{inv_name}' added!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Please provide investment name and amount.")

        st.markdown("### Manage Investments")
        all_invs = get_all_investments()
        if all_invs:
            inv_df = pd.DataFrame(all_invs)
            display_inv = inv_df[["name", "type", "amount_invested", "return_rate", "start_date", "status"]].copy()
            st.dataframe(display_inv, use_container_width=True, hide_index=True)

            # Update status
            st.markdown("### Update Investment Status")
            inv_col1, inv_col2 = st.columns(2)
            with inv_col1:
                inv_ids = inv_df["investment_id"].tolist()
                inv_labels = [f"{r['name']} ({r['type']})" for _, r in inv_df.iterrows()]
                selected_inv = st.selectbox("Select investment", options=inv_ids, format_func=lambda x: inv_labels[inv_ids.index(x)], key="inv_select")
            with inv_col2:
                new_inv_status = st.selectbox("New Status", options=["active", "closed", "paused"], key="inv_status")
                if st.button("Update Status", use_container_width=True):
                    update_investment_status(selected_inv, new_inv_status)
                    st.success("Investment status updated!")
                    time.sleep(0.5)
                    st.rerun()
        else:
            st.info("No investments recorded yet.")



def render_member_directory():
    """Render the member directory page."""
    st.markdown("""
    <div class="section-title">👥 Member Directory</div>
    """, unsafe_allow_html=True)

    members = get_all_active_members()
    if not members:
        st.info("No active members found.")
        return

    # Summary stats
    total_members = len(members)
    fica_verified = sum(1 for m in members if m.get("fica_verified"))
    constitution_signed = sum(1 for m in members if m.get("constitution_signed"))

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    with stat_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="font-size: 1.5rem;">{total_members}</div>
            <div class="metric-label">Active Members</div>
        </div>
        """, unsafe_allow_html=True)
    with stat_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="font-size: 1.5rem; color: #10b981;">{fica_verified}</div>
            <div class="metric-label">FICA Verified</div>
        </div>
        """, unsafe_allow_html=True)
    with stat_col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="font-size: 1.5rem; color: #10b981;">{constitution_signed}</div>
            <div class="metric-label">Constitution Signed</div>
        </div>
        """, unsafe_allow_html=True)
    with stat_col4:
        avg_contrib = get_total_contributions() / total_members if total_members > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="font-size: 1.5rem;">R{avg_contrib:,.0f}</div>
            <div class="metric-label">Avg. Contribution</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Member cards grid
    st.markdown("### 🏠 Members")
    cols = st.columns(3)
    for idx, member in enumerate(members):
        with cols[idx % 3]:
            initials = f"{member['first_name'][0]}{member['surname'][0]}"
            total_contrib = get_member_total_contribution(member["user_id"])
            join_year = member["join_date"][:4] if member["join_date"] else "N/A"

            st.markdown(f"""
            <div class="member-card">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                    <div style="width: 50px; height: 50px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #06b6d4);
                        display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; font-size: 1.1rem;">
                        {initials}
                    </div>
                    <div>
                        <div style="font-weight: 600; color: #e5e7eb; font-size: 0.95rem;">{member["first_name"]} {member["surname"]}</div>
                        <div style="color: #6b7280; font-size: 0.75rem;">@{member["username"]}</div>
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
                    {'<span class="badge-fica-yes">FICA ✓</span>' if member.get("fica_verified") else '<span class="badge-fica-no">FICA Pending</span>'}
                    {'<span class="badge-paid">Constitution ✓</span>' if member.get("constitution_signed") else '<span class="badge-unpaid">Constitution ✗</span>'}
                </div>
                <div style="color: #9ca3af; font-size: 0.8rem;">
                    <div>💰 Total Contributed: <strong style="color: #10b981;">R{total_contrib:,.2f}</strong></div>
                    <div>📅 Joined: {join_year}</div>
                    {f'<div>📧 {member["email"]}</div>' if member.get("email") else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Leaderboard
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🏆 Contribution Leaderboard")

    leaderboard_data = []
    for member in members:
        total = get_member_total_contribution(member["user_id"])
        leaderboard_data.append({
            "Member": f"{member['first_name']} {member['surname']}",
            "Total Contributed": total,
            "Status": "✅ Active" if member.get("is_active") else "❌ Inactive"
        })

    leaderboard_df = pd.DataFrame(leaderboard_data).sort_values("Total Contributed", ascending=False)
    leaderboard_df["Rank"] = range(1, len(leaderboard_df) + 1)
    leaderboard_df = leaderboard_df[["Rank", "Member", "Total Contributed", "Status"]]

    # Color code the top 3
    def highlight_top3(row):
        if row["Rank"] == 1:
            return ['background-color: rgba(255,215,0,0.15)'] * len(row)
        elif row["Rank"] == 2:
            return ['background-color: rgba(192,192,192,0.1)'] * len(row)
        elif row["Rank"] == 3:
            return ['background-color: rgba(205,127,50,0.1)'] * len(row)
        return [''] * len(row)

    st.dataframe(
        leaderboard_df.style.apply(highlight_top3, axis=1),
        use_container_width=True,
        hide_index=True
    )

    # FICA compliance summary
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📋 FICA Compliance Summary")

    fica_data = []
    for member in members:
        fica_data.append({
            "Member": f"{member['first_name']} {member['surname']}",
            "ID Number": member.get("id_number", "N/A") or "N/A",
            "FICA Verified": "✅ Yes" if member.get("fica_verified") else "❌ No",
            "Constitution": "✅ Signed" if member.get("constitution_signed") else "❌ Not Signed",
            "Phone": member.get("phone", "N/A") or "N/A"
        })
    fica_df = pd.DataFrame(fica_data)
    st.dataframe(fica_df, use_container_width=True, hide_index=True)



def render_notifications():
    """Render the notifications page."""
    user = st.session_state.user

    st.markdown("""
    <div class="section-title">🔔 Notifications</div>
    """, unsafe_allow_html=True)

    notifications = get_user_notifications(user["user_id"])

    if not notifications:
        st.info("📭 No notifications yet. Check back later!")
        return

    # Mark all as read option
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("✓ Mark All Read", use_container_width=True):
            mark_all_notifications_read(user["user_id"])
            st.success("All notifications marked as read!")
            time.sleep(0.5)
            st.rerun()

    unread_count = sum(1 for n in notifications if not n.get("is_read"))
    st.markdown(f"<p style='color: #9ca3af;'>You have <strong style='color: #10b981;'>{unread_count}</strong> unread notification(s)</p>", unsafe_allow_html=True)

    # Display notifications
    for notif in notifications:
        is_read = notif.get("is_read", False)
        bg_color = "rgba(31,41,55,0.6)" if is_read else "rgba(16,185,129,0.1)"
        border_color = "rgba(75,85,99,0.3)" if is_read else "rgba(16,185,129,0.4)"
        icon = {"welcome": "🎉", "announcement": "📢", "payment": "💰", "vote": "🗳️", "general": "📌"}.get(notif.get("notification_type", "general"), "📌")

        with st.container():
            st.markdown(f"""
            <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 12px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <span style="margin-right: 0.5rem;">{icon}</span>
                        <span style="font-weight: {'400' if is_read else '600'}; color: {'#9ca3af' if is_read else '#e5e7eb'};">
                            {notif["message"]}
                        </span>
                    </div>
                    <span style="color: #6b7280; font-size: 0.7rem; white-space: nowrap; margin-left: 0.5rem;">
                        {notif["created_at"][:10]}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if not is_read:
                if st.button("Mark as Read", key=f"read_{notif['notification_id']}", use_container_width=False):
                    mark_notification_read(notif["notification_id"])
                    st.rerun()


def render_reports():
    """Render the reports and analytics page."""
    st.markdown("""
    <div class="section-title">📈 Reports & Analytics</div>
    """, unsafe_allow_html=True)

    tab_heatmap, tab_participation, tab_performance, tab_monthly = st.tabs([
        "🗓️ Contribution Heatmap", "📊 Participation Rate", "📈 Investment Performance", "📋 Monthly Summary"
    ])

    # Tab 1: Contribution Heatmap
    with tab_heatmap:
        st.markdown("### Contribution Heatmap")
        st.markdown("<p style='color: #9ca3af; font-size: 0.85rem;'>Green = Paid | Red = Unpaid | Gray = No Record</p>", unsafe_allow_html=True)

        selected_year = st.selectbox("Select Year", options=[datetime.now().year, datetime.now().year - 1], key="heatmap_year")

        # Get contribution data
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.first_name || ' ' || u.surname as member, mc.month, mc.status
            FROM Monthly_Contributions mc
            JOIN Users u ON mc.user_id = u.user_id
            WHERE mc.year = ? AND u.is_active = 1 AND u.is_admin = 0
            ORDER BY u.join_date, mc.month
        """, (selected_year,))
        rows = cursor.fetchall()
        conn.close()

        if rows:
            heatmap_df = pd.DataFrame([dict(r) for r in rows])
            # Pivot for heatmap
            heatmap_pivot = heatmap_df.pivot_table(index="member", columns="month", values="status",
                                                   aggfunc=lambda x: 'paid' if 'paid' in list(x) else 'unpaid')
            heatmap_pivot = heatmap_pivot.reindex(columns=range(1, 13))
            heatmap_pivot.columns = [MONTHS[i-1][:3] for i in heatmap_pivot.columns]

            # Create numeric mapping for colors
            numeric_df = heatmap_pivot.copy()
            for col in numeric_df.columns:
                numeric_df[col] = numeric_df[col].apply(lambda x: 1 if x == 'paid' else (0 if x == 'unpaid' else -1))

            fig = px.imshow(numeric_df,
                          color_continuous_scale=[['No Record', '#374151'], ['Unpaid', '#ef4444'], ['Paid', '#10b981']],
                          aspect="auto",
                          labels=dict(x="Month", y="Member", color="Status"))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e5e7eb', family='Inter'),
                xaxis=dict(side="top"),
                height=max(400, len(numeric_df) * 60),
                margin=dict(l=150, r=40, t=60, b=40)
            )
            fig.update_traces(text=heatmap_pivot.values, texttemplate="%{text}", textfont=dict(size=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No contribution data available for the selected year.")

    # Tab 2: Participation Rate
    with tab_participation:
        st.markdown("### Member Participation Rate")

        members = get_all_active_members()
        participation_data = []
        for member in members:
            contribs = get_member_contributions(member["user_id"])
            total_months = len(contribs)
            paid_months = len([c for c in contribs if c["status"] == "paid"])
            rate = (paid_months / total_months * 100) if total_months > 0 else 0
            participation_data.append({
                "Member": f"{member['first_name']} {member['surname']}",
                "Participation Rate": round(rate, 1),
                "Months Paid": paid_months,
                "Total Months": total_months
            })

        if participation_data:
            part_df = pd.DataFrame(participation_data).sort_values("Participation Rate", ascending=True)

            fig = go.Figure(go.Bar(
                x=part_df["Participation Rate"],
                y=part_df["Member"],
                orientation='h',
                marker=dict(
                    color=part_df["Participation Rate"],
                    colorscale=[[0, '#ef4444'], [0.5, '#f59e0b'], [1, '#10b981']],
                    showscale=False
                ),
                text=part_df["Participation Rate"].apply(lambda x: f"{x:.0f}%"),
                textposition='outside'
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e5e7eb', family='Inter'),
                xaxis=dict(title="Participation Rate (%)", gridcolor='rgba(75,85,99,0.2)', range=[0, 110]),
                yaxis=dict(gridcolor='rgba(75,85,99,0.2)'),
                height=max(400, len(part_df) * 50),
                margin=dict(l=150, r=60, t=30, b=40),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

            # Overall participation
            avg_rate = part_df["Participation Rate"].mean()
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem;">{avg_rate:.1f}%</div>
                    <div class="metric-label">Avg. Participation Rate</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                top_performer = part_df.iloc[-1]["Member"] if len(part_df) > 0 else "N/A"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem;">🏆</div>
                    <div class="metric-label">Top: {top_performer}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No participation data available.")

    # Tab 3: Investment Performance
    with tab_performance:
        st.markdown("### Investment Performance Tracker")

        investments = get_all_investments()
        if investments:
            inv_df = pd.DataFrame(investments)

            # Performance bar chart
            fig = go.Figure()
            colors = ['#10b981' if r >= 0 else '#ef4444' for r in inv_df["return_rate"]]
            fig.add_trace(go.Bar(
                x=inv_df["name"],
                y=inv_df["return_rate"],
                marker=dict(color=colors),
                text=inv_df["return_rate"].apply(lambda x: f"{x:+.1f}%"),
                textposition='outside'
            ))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e5e7eb', family='Inter'),
                xaxis=dict(title="", gridcolor='rgba(75,85,99,0.2)'),
                yaxis=dict(title="Return Rate (%)", gridcolor='rgba(75,85,99,0.2)'),
                height=400,
                margin=dict(l=60, r=40, t=30, b=80),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

            # Investment summary table
            st.markdown("### Investment Details")
            summary_df = inv_df[["name", "type", "amount_invested", "return_rate", "start_date", "status"]].copy()
            summary_df["Current Value"] = summary_df["amount_invested"] * (1 + summary_df["return_rate"] / 100)
            summary_df.columns = ["Name", "Type", "Invested", "Return %", "Start Date", "Status", "Current Value"]
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

            # Portfolio overview
            total_invested = inv_df["amount_invested"].sum()
            total_current = sum(inv_df["amount_invested"] * (1 + inv_df["return_rate"] / 100))
            overall_return = ((total_current / total_invested) - 1) * 100 if total_invested > 0 else 0

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem;">R{total_invested:,.2f}</div>
                    <div class="metric-label">Total Invested</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem;">R{total_current:,.2f}</div>
                    <div class="metric-label">Current Value</div>
                </div>
                """, unsafe_allow_html=True)
            with col3:
                color = "#10b981" if overall_return >= 0 else "#ef4444"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.5rem; color: {color};">{overall_return:+.1f}%</div>
                    <div class="metric-label">Overall Return</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No investment data available. Add investments from the Admin Panel.")

    # Tab 4: Monthly Summary
    with tab_monthly:
        st.markdown("### Monthly Summary Report")

        summary_month = st.selectbox("Select Month", options=range(1, 13),
                                     format_func=lambda x: MONTHS[x-1], key="summary_month")
        summary_year = st.selectbox("Select Year", options=[datetime.now().year, datetime.now().year - 1], key="summary_year")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Total contributions for the month
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) as total FROM Monthly_Contributions
            WHERE year = ? AND month = ? AND status = 'paid'
        """, (summary_year, summary_month))
        month_total = cursor.fetchone()["total"] or 0

        # Paid vs Unpaid counts
        cursor.execute("""
            SELECT status, COUNT(*) as count FROM Monthly_Contributions
            WHERE year = ? AND month = ? GROUP BY status
        """, (summary_year, summary_month))
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

        # Member details
        cursor.execute("""
            SELECT u.first_name || ' ' || u.surname as member, mc.amount, mc.status, mc.payment_date
            FROM Monthly_Contributions mc
            JOIN Users u ON mc.user_id = u.user_id
            WHERE mc.year = ? AND mc.month = ? AND u.is_active = 1
            ORDER BY mc.status, u.surname
        """, (summary_year, summary_month))
        member_details = [dict(r) for r in cursor.fetchall()]
        conn.close()

        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <h3 style="color: #10b981;">{MONTHS[summary_month-1]} {summary_year}</h3>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.5rem;">R{month_total:,.2f}</div>
                <div class="metric-label">Total Collected</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.5rem; color: #10b981;">{status_counts.get('paid', 0)}</div>
                <div class="metric-label">Paid</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.5rem; color: #ef4444;">{status_counts.get('unpaid', 0)}</div>
                <div class="metric-label">Unpaid</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            collection_rate = (status_counts.get('paid', 0) / (status_counts.get('paid', 0) + status_counts.get('unpaid', 0)) * 100) if (status_counts.get('paid', 0) + status_counts.get('unpaid', 0)) > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.5rem;">{collection_rate:.0f}%</div>
                <div class="metric-label">Collection Rate</div>
            </div>
            """, unsafe_allow_html=True)

        if member_details:
            st.markdown("### Member Details")
            details_df = pd.DataFrame(member_details)
            st.dataframe(details_df, use_container_width=True, hide_index=True)

            # Pie chart of paid vs unpaid
            pie_data = pd.DataFrame([
                {"Status": "Paid", "Count": status_counts.get('paid', 0)},
                {"Status": "Unpaid", "Count": status_counts.get('unpaid', 0)}
            ])
            fig = px.pie(pie_data, values="Count", names="Status",
                        color="Status", color_discrete_map={"Paid": "#10b981", "Unpaid": "#ef4444"},
                        hole=0.4)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e5e7eb', family='Inter'),
                height=300,
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No contribution records for this month.")



def render_ai_advisor():
    """Render the enhanced AI advisor page."""
    st.markdown("""
    <div class="section-title">🤖 AI Investment Advisor</div>
    """, unsafe_allow_html=True)

    tab_advice, tab_news, tab_risk, tab_calculator, tab_portfolio = st.tabs([
        "💡 Advice", "📰 Market News", "⚖️ Risk Assessment", "🧮 Calculator", "🥧 Portfolio"
    ])

    # Tab 1: AI Advice
    with tab_advice:
        st.markdown("### SA Market-Aware Investment Recommendations")
        st.markdown("<p style='color: #9ca3af;'>Based on current South African market conditions</p>", unsafe_allow_html=True)

        risk_tolerance = st.select_slider(
            "Your Risk Tolerance",
            options=["Conservative", "Moderate", "Balanced", "Growth", "Aggressive"],
            value="Balanced"
        )

        investment_horizon = st.select_slider(
            "Investment Horizon",
            options=["1 year", "3 years", "5 years", "10 years", "15+ years"],
            value="5 years"
        )

        if st.button("🤖 Get Personalized Advice", use_container_width=True, type="primary"):
            with st.spinner("Analyzing SA market conditions..."):
                time.sleep(1.2)

                # Generate advice based on selections
                advice_data = {
                    "Conservative": {
                        "allocation": {"Government Bonds": 40, "Money Market": 25, "Fixed Deposit": 20, "ETF / Index Fund": 15},
                        "advice": [
                            "🛡️ Prioritize capital preservation with government retail savings bonds",
                            "🏦 Keep 25% in money market funds for liquidity (FNB/Standard Bank)",
                            "📊 Consider SARB-fixed deposits for guaranteed 9-10% returns",
                            "⚠️ Avoid crypto and individual stocks at this risk level"
                        ]
                    },
                    "Moderate": {
                        "allocation": {"ETF / Index Fund": 30, "Government Bonds": 25, "Unit Trust": 20, "Property (REITs)": 15, "Stocks (JSE)": 10},
                        "advice": [
                            "📊 Start with Satrix 40 ETF for broad JSE exposure",
                            "🏘️ Consider REITs like Growthpoint for property exposure",
                            "📈 Small allocation to quality JSE blue chips (Naspers, Richemont)",
                            "🏦 Keep bonds for stability during market volatility"
                        ]
                    },
                    "Balanced": {
                        "allocation": {"ETF / Index Fund": 30, "Stocks (JSE)": 20, "Property (REITs)": 15, "Government Bonds": 15, "Unit Trust": 10, "Crypto": 5, "Business Venture": 5},
                        "advice": [
                            "🎯 Diversify across asset classes with 30% in JSE ETFs",
                            "🏢 Select 3-5 JSE blue chips: SSW, SHP, BHP, DSY",
                            "🏘️ Add property via REITs like Vukile or Hyprop",
                            "₿ Small 5% crypto allocation via Luno for upside potential",
                            "📊 Review and rebalance quarterly with the collective"
                        ]
                    },
                    "Growth": {
                        "allocation": {"Stocks (JSE)": 35, "ETF / Index Fund": 25, "Crypto": 15, "Business Venture": 10, "Property (REITs)": 10, "Unit Trust": 5},
                        "advice": [
                            "🚀 Focus on high-growth JSE sectors: tech and resources",
                            "📈 Consider Capitec, Prosus, and Anglo American",
                            "₿ Increase crypto allocation to quality coins (BTC, ETH)",
                            "💼 Explore township business venture opportunities",
                            "⚠️ Accept higher volatility for long-term growth potential"
                        ]
                    },
                    "Aggressive": {
                        "allocation": {"Stocks (JSE)": 40, "Crypto": 25, "Business Venture": 15, "ETF / Index Fund": 10, "Unit Trust": 5, "Property (REITs)": 5},
                        "advice": [
                            "🔥 Maximum equity exposure: Small-cap JSE stocks",
                            "₿ Significant crypto portfolio via Luno or VALR",
                            "💼 High-risk, high-reward township business ventures",
                            "📈 Consider leveraged ETFs for amplified returns",
                            "⚠️ High volatility expected - strong stomach required!"
                        ]
                    }
                }

                data = advice_data[risk_tolerance]

                # Show allocation pie chart
                alloc_df = pd.DataFrame(list(data["allocation"].items()), columns=["Asset", "Allocation"])
                fig = px.pie(alloc_df, values="Allocation", names="Asset",
                           color_discrete_sequence=px.colors.sequential.Emerald)
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#e5e7eb', family='Inter'),
                    height=350,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2)
                )
                st.plotly_chart(fig, use_container_width=True)

                # Show advice cards
                for tip in data["advice"]:
                    st.markdown(f"""
                    <div style="background: rgba(16,185,129,0.1); border-left: 4px solid #10b981; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
                        {tip}
                    </div>
                    """, unsafe_allow_html=True)

    # Tab 2: Market News
    with tab_news:
        st.markdown("### 📰 South African Financial News")
        st.markdown("<p style='color: #9ca3af;'>Simulated SA market news feed</p>", unsafe_allow_html=True)

        # Show news articles
        for headline, summary, sentiment in SA_NEWS_HEADLINES:
            sentiment_color = {"Positive": "#10b981", "Negative": "#ef4444", "Neutral": "#f59e0b"}.get(sentiment, "#9ca3af")
            sentiment_bg = {"Positive": "rgba(16,185,129,0.1)", "Negative": "rgba(239,68,68,0.1)", "Neutral": "rgba(245,158,11,0.1)"}.get(sentiment, "rgba(75,85,99,0.1)")

            with st.expander(f"[{sentiment}] {headline}"):
                st.markdown(f"""
                <div style="background: {sentiment_bg}; border-radius: 8px; padding: 1rem;">
                    <p style="color: #d1d5db; margin: 0; line-height: 1.6;">{summary}</p>
                    <div style="margin-top: 0.5rem;">
                        <span style="background: {sentiment_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">
                            {sentiment}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Tab 3: Risk Assessment Quiz
    with tab_risk:
        st.markdown("### ⚖️ Investment Risk Assessment Quiz")
        st.markdown("<p style='color: #9ca3af;'>Answer these questions to determine your risk profile</p>", unsafe_allow_html=True)

        q1 = st.radio("1. If your investment lost 20% in a month, you would:",
                     ["Sell everything immediately",
                      "Sell some investments",
                      "Do nothing and wait",
                      "Buy more at lower prices"],
                     index=2)

        q2 = st.radio("2. Your investment goal is:",
                     ["Preserve capital", "Generate income",
                      "Moderate growth", "Maximum growth"],
                     index=2)

        q3 = st.radio("3. How long can you leave your money invested?",
                     ["Less than 1 year", "1-3 years", "3-5 years", "5+ years"],
                     index=3)

        q4 = st.radio("4. What percentage of your income can you invest?",
                     ["Less than 5%", "5-10%", "10-20%", "More than 20%"],
                     index=2)

        q5 = st.radio("5. How familiar are you with investment products?",
                     ["Not familiar", "Somewhat familiar",
                      "Quite familiar", "Very experienced"],
                     index=2)

        if st.button("📊 Calculate Risk Profile", use_container_width=True, type="primary"):
            score = 0
            score_map = {
                q1: {"Sell everything immediately": 1, "Sell some investments": 2, "Do nothing and wait": 3, "Buy more at lower prices": 4},
                q2: {"Preserve capital": 1, "Generate income": 2, "Moderate growth": 3, "Maximum growth": 4},
                q3: {"Less than 1 year": 1, "1-3 years": 2, "3-5 years": 3, "5+ years": 4},
                q4: {"Less than 5%": 1, "5-10%": 2, "10-20%": 3, "More than 20%": 4},
                q5: {"Not familiar": 1, "Somewhat familiar": 2, "Quite familiar": 3, "Very experienced": 4}
            }
            for answer, mapping in score_map.items():
                score += mapping.get(answer, 2)

            if score <= 8:
                profile = "Conservative"
                desc = "You prioritize capital preservation and are uncomfortable with market volatility."
                color = "#3b82f6"
            elif score <= 12:
                profile = "Moderate"
                desc = "You seek a balance between growth and stability."
                color = "#10b981"
            elif score <= 16:
                profile = "Balanced"
                desc = "You are comfortable with moderate risk for better long-term returns."
                color = "#f59e0b"
            elif score <= 18:
                profile = "Growth"
                desc = "You prioritize long-term growth and can tolerate significant volatility."
                color = "#f97316"
            else:
                profile = "Aggressive"
                desc = "You seek maximum returns and are comfortable with high volatility."
                color = "#ef4444"

            st.session_state.risk_score = score
            st.session_state.risk_profile = profile

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {color}20, {color}10); border: 2px solid {color}; border-radius: 16px; padding: 2rem; text-align: center; margin: 1rem 0;">
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">📊</div>
                <div style="font-size: 2rem; font-weight: 800; color: {color}; margin-bottom: 0.5rem;">{profile}</div>
                <div style="color: #9ca3af; margin-bottom: 1rem;">{desc}</div>
                <div style="font-size: 0.85rem; color: #6b7280;">Risk Score: {score}/20</div>
            </div>
            """, unsafe_allow_html=True)

            st.info("💡 Use this risk profile in the 'Advice' tab to get personalized recommendations!")

    # Tab 4: Investment Calculator
    with tab_calculator:
        st.markdown("### 🧮 Compound Interest Calculator")
        st.markdown("<p style='color: #9ca3af;'>Project your investment growth over time</p>", unsafe_allow_html=True)

        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
            initial = st.number_input("Initial Investment (R)", min_value=0, value=10000, step=1000)
            monthly = st.number_input("Monthly Contribution (R)", min_value=0, value=500, step=100)
        with calc_col2:
            annual_rate = st.slider("Annual Return Rate (%)", min_value=0.0, max_value=30.0, value=10.0, step=0.5)
            years = st.slider("Investment Period (Years)", min_value=1, max_value=30, value=10)

        # Calculate
        monthly_rate = annual_rate / 100 / 12
        months = years * 12
        values = []
        total_contributed = initial
        current_value = initial

        for m in range(months + 1):
            if m > 0:
                current_value = current_value * (1 + monthly_rate) + monthly
                total_contributed += monthly
            year_num = m / 12
            values.append({
                "Month": m,
                "Year": round(year_num, 1),
                "Portfolio Value": round(current_value, 2),
                "Total Contributed": round(total_contributed, 2),
                "Interest Earned": round(current_value - total_contributed, 2)
            })

        calc_df = pd.DataFrame(values)

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=calc_df["Year"], y=calc_df["Portfolio Value"],
                                  mode='lines', name='Portfolio Value', line=dict(color='#10b981', width=3),
                                  fill='tozeroy', fillcolor='rgba(16,185,129,0.1)'))
        fig.add_trace(go.Scatter(x=calc_df["Year"], y=calc_df["Total Contributed"],
                                  mode='lines', name='Total Contributed', line=dict(color='#f59e0b', width=2, dash='dash')))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e5e7eb', family='Inter'),
            xaxis=dict(title="Years", gridcolor='rgba(75,85,99,0.2)'),
            yaxis=dict(title="Amount (R)", gridcolor='rgba(75,85,99,0.2)', tickprefix='R'),
            height=400,
            margin=dict(l=60, r=40, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Summary
        final = calc_df.iloc[-1]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.3rem;">R{final["Portfolio Value"]:,.2f}</div>
                <div class="metric-label">Final Portfolio Value</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.3rem;">R{final["Total Contributed"]:,.2f}</div>
                <div class="metric-label">Total Contributed</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.3rem; color: #10b981;">R{final["Interest Earned"]:,.2f}</div>
                <div class="metric-label">Interest Earned</div>
            </div>
            """, unsafe_allow_html=True)

    # Tab 5: Portfolio Visualizer
    with tab_portfolio:
        st.markdown("### 🥧 Portfolio Allocation Visualizer")
        st.markdown("<p style='color: #9ca3af;'>See how your club's portfolio is allocated</p>", unsafe_allow_html=True)

        investments = get_all_investments()
        if investments:
            inv_df = pd.DataFrame(investments)

            # By Type
            st.markdown("#### By Investment Type")
            type_summary = inv_df.groupby("type")["amount_invested"].sum().reset_index()
            fig1 = px.pie(type_summary, values="amount_invested", names="type",
                         color_discrete_sequence=px.colors.sequential.Emerald)
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e5e7eb'), height=350)
            st.plotly_chart(fig1, use_container_width=True)

            # By Status
            st.markdown("#### By Investment Status")
            status_summary = inv_df.groupby("status")["amount_invested"].sum().reset_index()
            fig2 = px.pie(status_summary, values="amount_invested", names="status",
                         color_discrete_sequence=["#10b981", "#f59e0b", "#ef4444"])
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e5e7eb'), height=300)
            st.plotly_chart(fig2, use_container_width=True)

            # Treemap
            st.markdown("#### Investment Breakdown")
            fig3 = px.treemap(inv_df, path=["type", "name"], values="amount_invested",
                             color="return_rate", color_continuous_scale="RdYlGn",
                             color_continuous_midpoint=0)
            fig3.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#e5e7eb'), height=400)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No investments to visualize. Add investments from the Admin Panel.")



def render_member_voice():
    """Render the member voice (suggestions/voting) page."""
    user = st.session_state.user

    st.markdown("""
    <div class="section-title">🗳️ Member Voice</div>
    """, unsafe_allow_html=True)
    st.markdown("<p style='color: #9ca3af;'>Propose investments and vote on club decisions</p>", unsafe_allow_html=True)

    # Submit new suggestion
    with st.expander("💡 Submit New Proposal"):
        with st.form("suggestion_form"):
            suggestion_text = st.text_area("Your Proposal", height=100,
                placeholder="E.g., I propose we invest R5,000 in Satrix 40 ETF...",
                key="suggestion_text")
            if st.form_submit_button("Submit Proposal", use_container_width=True):
                if suggestion_text.strip():
                    add_suggestion(user["user_id"], suggestion_text.strip())
                    st.success("✅ Proposal submitted successfully!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Please enter a proposal.")

    # Display all suggestions
    st.markdown("### Active Proposals")
    suggestions = get_all_suggestions()

    if not suggestions:
        st.info("No proposals yet. Be the first to submit one!")
        return

    for sug in suggestions:
        voter_list = json.loads(sug.get("voters", "[]"))
        has_voted = user["user_id"] in voter_list
        can_vote = not has_voted and sug.get("status") == "open"

        with st.container():
            st.markdown(f"""
            <div class="suggestion-card">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #06b6d4); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.8rem;">
                            {sug["first_name"][0]}{sug["surname"][0]}
                        </div>
                        <div>
                            <span style="font-weight: 600; color: #e5e7eb; font-size: 0.85rem;">{sug["first_name"]} {sug["surname"]}</span>
                            <span style="color: #6b7280; font-size: 0.7rem;"> • {sug["created_at"][:10]}</span>
                        </div>
                    </div>
                    <span style="background: {'#10b981' if sug.get('status') == 'open' else '#6b7280'}; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.7rem;">
                        {sug.get('status', 'open').title()}
                    </span>
                </div>
                <p style="color: #d1d5db; margin: 0.5rem 0; line-height: 1.5;">{sug["suggestion_text"]}</p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #10b981; font-weight: 700; font-size: 1.1rem;">▲ {sug["votes"]} votes</span>
                    <span style="color: #6b7280; font-size: 0.75rem;">{len(voter_list)} member(s) voted</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if can_vote:
                if st.button(f"▲ Vote for this proposal", key=f"vote_{sug['suggestion_id']}", use_container_width=True):
                    if vote_suggestion(sug["suggestion_id"], user["user_id"]):
                        st.success("✅ Vote recorded!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.warning("You have already voted for this proposal.")
            elif has_voted:
                st.markdown("<span style='color: #10b981; font-size: 0.8rem;'>✓ You voted for this</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color: #6b7280; font-size: 0.8rem;'>🔒 Voting closed</span>", unsafe_allow_html=True)

            st.markdown("<hr style='margin: 0.5rem 0; border-color: rgba(75,85,99,0.2);'>", unsafe_allow_html=True)


def render_constitution():
    """Render the digital constitution signing page."""
    user = st.session_state.user

    st.markdown("""
    <div class="section-title">📜 Digital Constitution</div>
    """, unsafe_allow_html=True)

    constitution_text = """
    <h3 style="color: #10b981;">KULA COLLECTIVE - INVESTMENT CLUB CONSTITUTION</h3>

    <h4>Article 1: Name and Purpose</h4>
    <p>The name of this investment club shall be "Khula Collective." The purpose of the club is to pool our financial resources, knowledge, and networks to collectively invest in wealth-building opportunities, with a focus on the South African market.</p>

    <h4>Article 2: Membership</h4>
    <p>2.1 Membership is open to individuals who share our vision of collective wealth building.<br>
    2.2 Each member must contribute a minimum of R500 per month.<br>
    2.3 New members must be approved by a majority vote of existing members.<br>
    2.4 Members may resign with 30 days written notice.</p>

    <h4>Article 3: Contributions</h4>
    <p>3.1 Monthly contributions of R500 are due by the 7th of each month.<br>
    3.2 Contributions must be made to the designated FNB account.<br>
    3.3 Late contributions may incur a R50 penalty after the 14th.<br>
    3.4 Members missing 3 consecutive contributions may face review.</p>

    <h4>Article 4: Investment Decisions</h4>
    <p>4.1 All investment decisions require a majority vote (50%+1).<br>
    4.2 Proposals must be submitted via the Member Voice platform.<br>
    4.3 No single investment may exceed 30% of total club assets.<br>
    4.4 A minimum of 5 members must vote for a decision to be valid.</p>

    <h4>Article 5: Governance</h4>
    <p>5.1 The club shall have an elected Chairperson, Treasurer, and Secretary.<br>
    5.2 Elections shall be held annually in January.<br>
    5.3 All financial records shall be transparent and accessible to members.</p>

    <h4>Article 6: FICA Compliance</h4>
    <p>6.1 All members must provide valid FICA documentation.<br>
    6.2 This includes a certified ID copy and proof of address.<br>
    6.3 Non-compliant members may have voting rights suspended.</p>

    <h4>Article 7: Profit Distribution</h4>
    <p>7.1 Profits shall be reinvested unless members vote otherwise.<br>
    7.2 Annual profit distribution requires a 75% majority vote.<br>
    7.3 Distribution is proportional to total contributions made.</p>

    <h4>Article 8: Amendments</h4>
    <p>8.1 This constitution may be amended by a two-thirds majority vote.<br>
    8.2 Proposed amendments must be circulated 14 days before voting.</p>

    <h4>Article 9: Dispute Resolution</h4>
    <p>9.1 Disputes shall first be addressed through internal mediation.<br>
    9.2 If unresolved, disputes may be escalated to external arbitration.</p>

    <h4>Article 10: Dissolution</h4>
    <p>10.1 The club may be dissolved by a 75% majority vote.<br>
    10.2 Assets shall be distributed proportionally to contributions.</p>
    """

    st.markdown(f"""
    <div class="constitution-box">
        {constitution_text}
    </div>
    """, unsafe_allow_html=True)

    # Signing status
    if user.get("constitution_signed"):
        signed_date = user.get("constitution_signed_date", "Unknown")
        st.markdown(f"""
        <div style="background: rgba(16,185,129,0.1); border: 2px solid #10b981; border-radius: 12px; padding: 1rem; text-align: center; margin-top: 1rem;">
            <span style="font-size: 1.5rem;">✅</span>
            <p style="color: #10b981; font-weight: 600; margin: 0.5rem 0;">You have signed the constitution</p>
            <p style="color: #9ca3af; font-size: 0.8rem; margin: 0;">Signed on: {signed_date}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        st.warning("⚠️ You have not yet signed the constitution. Please read it carefully and sign below.")

        with st.form("constitution_sign_form"):
            st.markdown("<p style='color: #9ca3af; font-size: 0.85rem;'>By entering your full name below, you agree to abide by the Khula Collective constitution.</p>", unsafe_allow_html=True)
            full_name = st.text_input("Type your full name to sign", key="constitution_sign_name")
            if st.form_submit_button("✍️ Sign Constitution", use_container_width=True, type="primary"):
                expected_name = f"{user['first_name']} {user['surname']}"
                if full_name.strip().lower() == expected_name.lower():
                    sign_constitution(user["user_id"])
                    st.success("✅ Constitution signed successfully!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"Please type your exact full name: '{expected_name}'")

    # Show signing status of all members
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Member Signing Status")

    members = get_all_active_members()
    signed_count = sum(1 for m in members if m.get("constitution_signed"))
    total_count = len(members)
    progress = signed_count / total_count if total_count > 0 else 0

    st.progress(progress, text=f"{signed_count}/{total_count} members have signed")

    signing_data = []
    for m in members:
        signing_data.append({
            "Member": f"{m['first_name']} {m['surname']}",
            "Status": "✅ Signed" if m.get("constitution_signed") else "❌ Not Signed",
            "Date": m.get("constitution_signed_date", "—") if m.get("constitution_signed") else "—"
        })
    st.dataframe(pd.DataFrame(signing_data), use_container_width=True, hide_index=True)



def render_profile():
    """Render the user profile page."""
    user = st.session_state.user

    st.markdown("""
    <div class="section-title">👤 My Profile</div>
    """, unsafe_allow_html=True)

    # Refresh user data from DB
    user = get_user_by_id(user["user_id"])
    st.session_state.user = user

    col1, col2 = st.columns([1, 2])

    with col1:
        initials = f"{user['first_name'][0]}{user['surname'][0]}"
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="width: 100px; height: 100px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #06b6d4); display: flex; align-items: center; justify-content: center; margin: 0 auto; font-weight: 800; color: white; font-size: 2rem;">
                {initials}
            </div>
            <div style="margin-top: 0.75rem; font-weight: 700; color: #e5e7eb; font-size: 1.1rem;">{user['first_name']} {user['surname']}</div>
            <div style="color: #6b7280; font-size: 0.8rem;">@{user['username']}</div>
            {'<div style="color: #fbbf24; font-size: 0.8rem; margin-top: 0.25rem;">👑 Administrator</div>' if user.get("is_admin") else '<div style="color: #10b981; font-size: 0.8rem; margin-top: 0.25rem;">👤 Member</div>'}
        </div>
        """, unsafe_allow_html=True)

        # Status badges
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Status")
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 1.5rem;">{'✅' if user.get('constitution_signed') else '❌'}</div>
                <div style="font-size: 0.7rem; color: #9ca3af;">Constitution</div>
            </div>
            """, unsafe_allow_html=True)
        with status_col2:
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 1.5rem;">{'✅' if user.get('fica_verified') else '⚠️'}</div>
                <div style="font-size: 0.7rem; color: #9ca3af;">FICA</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("### Personal Information")
        st.markdown(f"""
        <div style="background: rgba(31,41,55,0.6); border-radius: 12px; padding: 1rem;">
            <table style="width: 100%; color: #d1d5db; font-size: 0.9rem;">
                <tr><td style="color: #9ca3af; width: 40%;">Email</td><td>{user.get('email') or 'Not set'}</td></tr>
                <tr><td style="color: #9ca3af;">Phone</td><td>{user.get('phone') or 'Not set'}</td></tr>
                <tr><td style="color: #9ca3af;">ID Number</td><td>{user.get('id_number') or 'Not set'}</td></tr>
                <tr><td style="color: #9ca3af;">Join Date</td><td>{user.get('join_date')}</td></tr>
                <tr><td style="color: #9ca3af;">Member Status</td><td>{'Active' if user.get('is_active') else 'Inactive'}</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Contribution tracking
    st.markdown("### 💰 My Contribution History")
    contributions = get_member_contributions(user["user_id"])

    if contributions:
        contrib_df = pd.DataFrame(contributions)
        contrib_df["Month Name"] = contrib_df["month"].apply(lambda x: MONTHS[x-1])
        contrib_df["Status Badge"] = contrib_df["status"].apply(
            lambda x: f'<span class="badge-paid">PAID</span>' if x == "paid" else f'<span class="badge-unpaid">UNPAID</span>'
        )

        total_contributed = contrib_df[contrib_df["status"] == "paid"]["amount"].sum()
        paid_months = len(contrib_df[contrib_df["status"] == "paid"])
        unpaid_months = len(contrib_df[contrib_df["status"] == "unpaid"])

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.3rem;">R{total_contributed:,.2f}</div>
                <div class="metric-label">Total Contributed</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.3rem; color: #10b981;">{paid_months}</div>
                <div class="metric-label">Months Paid</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="font-size: 1.3rem; color: #ef4444;">{unpaid_months}</div>
                <div class="metric-label">Months Unpaid</div>
            </div>
            """, unsafe_allow_html=True)

        # Contribution chart
        contrib_chart = contrib_df.sort_values(["year", "month"])
        fig = go.Figure()
        colors = ["#10b981" if s == "paid" else "#ef4444" for s in contrib_chart["status"]]
        fig.add_trace(go.Bar(
            x=contrib_chart["Month Name"],
            y=contrib_chart["amount"],
            marker=dict(color=colors),
            text=contrib_chart["status"].str.upper(),
            textposition='outside'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e5e7eb', family='Inter'),
            xaxis=dict(title="", gridcolor='rgba(75,85,99,0.2)'),
            yaxis=dict(title="Amount (R)", gridcolor='rgba(75,85,99,0.2)'),
            height=350,
            margin=dict(l=60, r=40, t=30, b=60),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

        # Payment details table
        st.markdown("### Payment Details")
        display_df = contrib_df[["year", "Month Name", "amount", "status", "payment_date"]].copy()
        display_df.columns = ["Year", "Month", "Amount", "Status", "Payment Date"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No contribution records found. Contact your admin to set up your contribution tracking.")

    # Quick links
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### ⚡ Quick Links")
    ql_col1, ql_col2, ql_col3 = st.columns(3)
    with ql_col1:
        if st.button("📜 Constitution", use_container_width=True, key="profile_const"):
            st.session_state.current_page = "constitution"
            st.rerun()
    with ql_col2:
        if st.button("🗳️ Member Voice", use_container_width=True, key="profile_voice"):
            st.session_state.current_page = "member_voice"
            st.rerun()
    with ql_col3:
        if st.button("🤖 AI Advisor", use_container_width=True, key="profile_advisor"):
            st.session_state.current_page = "ai_advisor"
            st.rerun()


def render_whatsapp():
    """Render WhatsApp integration page."""
    st.markdown("""
    <div class="section-title">💬 WhatsApp Integration</div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <div style="font-size: 4rem; margin-bottom: 1rem;">💬</div>
        <h3 style="color: #25D366;">Stay Connected on WhatsApp</h3>
        <p style="color: #9ca3af; max-width: 500px; margin: 0 auto 1.5rem auto;">
            Join the Khula Collective WhatsApp group for instant updates, quick discussions, and community building.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <a href="https://chat.whatsapp.com/invite/example-group-link" target="_blank" style="text-decoration: none;">
            <div style="background: linear-gradient(135deg, #25D366, #128C7E); color: white; padding: 1rem; border-radius: 12px; text-align: center; font-weight: 600; cursor: pointer; transition: transform 0.2s; margin-bottom: 1rem;">
                📲 Join WhatsApp Group
            </div>
        </a>
        """, unsafe_allow_html=True)

        # Share summary
        st.markdown("### Share Investment Summary")
        total = get_total_contributions()
        members = get_all_active_members()
        investments = get_all_investments()

        summary_text = f"""📈 *Khula Collective Update*

💰 Collective Pot: R{total:,.2f}
👥 Members: {len(members)}
📊 Investments: {len(investments)}

Join us in building wealth together! 🚀
"""
        st.text_area("Copy this message to share:", value=summary_text, height=150)

        # Generate WhatsApp share link
        encoded_msg = base64.b64encode(summary_text.encode()).decode()
        share_url = f"https://wa.me/?text={summary_text.replace(chr(10), '%0A').replace(' ', '%20')}"
        st.markdown(f"""
        <a href="{share_url}" target="_blank" style="text-decoration: none;">
            <div style="background: rgba(37,211,102,0.2); border: 1px solid #25D366; color: #25D366; padding: 0.75rem; border-radius: 10px; text-align: center; font-weight: 600; cursor: pointer;">
                📤 Share on WhatsApp
            </div>
        </a>
        """, unsafe_allow_html=True)


def render_bottom_nav():
    """Render bottom navigation bar for mobile."""
    if st.session_state.get("show_bottom_nav", True):
        st.markdown("""
        <style>
        @media (min-width: 768px) {
            .bottom-nav { display: none !important; }
        }
        .main { padding-bottom: 70px !important; }
        </style>
        <div class="bottom-nav">
            <div class="bottom-nav-item" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'dashboard'}, '*')">
                <span>📊</span>
                <span>Home</span>
            </div>
            <div class="bottom-nav-item" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'member_voice'}, '*')">
                <span>🗳️</span>
                <span>Vote</span>
            </div>
            <div class="bottom-nav-item" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'ai_advisor'}, '*')">
                <span>🤖</span>
                <span>Advisor</span>
            </div>
            <div class="bottom-nav-item" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'notifications'}, '*')">
                <span>🔔</span>
                <span>Alerts</span>
            </div>
            <div class="bottom-nav-item" onclick="window.parent.postMessage({type: 'streamlit:setComponentValue', value: 'profile'}, '*')">
                <span>👤</span>
                <span>Profile</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_pull_to_refresh():
    """Simulate pull-to-refresh with a button."""
    if st.button("🔄 Refresh Data", use_container_width=False, key="refresh_btn"):
        st.cache_data.clear()
        st.success("Data refreshed!")
        time.sleep(0.3)
        st.rerun()


# ============================================================
# MAIN APP ENTRY POINT
# ============================================================

def main():
    """Main application entry point."""
    init_session_state()
    seed_demo_data()

    # Apply theme CSS
    load_css(st.session_state.theme)

    # Check authentication
    if not st.session_state.authenticated:
        render_login()
        return

    # User is authenticated
    user = st.session_state.user

    # Render header
    render_header()

    # Render sidebar navigation
    render_sidebar_nav()

    # Render current page
    page = st.session_state.current_page

    if page == "dashboard":
        render_dashboard()
    elif page == "admin":
        render_admin_panel()
    elif page == "directory":
        render_member_directory()
    elif page == "notifications":
        render_notifications()
    elif page == "reports":
        render_reports()
    elif page == "ai_advisor":
        render_ai_advisor()
    elif page == "member_voice":
        render_member_voice()
    elif page == "constitution":
        render_constitution()
    elif page == "profile":
        render_profile()
    elif page == "whatsapp":
        render_whatsapp()
    else:
        render_dashboard()

    # Render bottom nav for mobile
    render_bottom_nav()


# Run the app
if __name__ == "__main__":
    main()
