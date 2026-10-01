import streamlit as st
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
import time
import random

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURATION
# ============================================================
DB_PATH = "khula_collective.db"

# FNB Open Banking API Configuration
FNB_API_BASE = os.environ.get("FNB_API_BASE", "https://api.fnb.co.za/openbanking/v1")
FNB_CLIENT_ID = os.environ.get("FNB_CLIENT_ID", "")
FNB_CLIENT_SECRET = os.environ.get("FNB_CLIENT_SECRET", "")
FNB_ENABLED = bool(FNB_CLIENT_ID and FNB_CLIENT_SECRET)

INVESTMENT_TYPES = [
    "JSE Listed Equity",
    "SASOL / Resources",
    "Bank Preference Shares",
    "REITs (Property)",
    "SARB Retail Savings Bonds",
    "Stokvel Pool",
    "Crypto (Bitcoin)",
    "Fixed Deposit",
    "Unit Trusts",
    "Money Market",
]

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

APP_FEATURES = [
    {"id": "dashboard", "name": "Dashboard", "icon": "🏠", "description": "Overview of club wealth and portfolio", "category": "Core", "new": False, "premium": False},
    {"id": "payment_tracking", "name": "Payment Tracking", "icon": "💰", "description": "Track contributions and arrears", "category": "Core", "new": False, "premium": False},
    {"id": "fnb_sync", "name": "FNB Bank Sync", "icon": "🏦", "description": "Automatic FNB transaction sync", "category": "Banking", "new": True, "premium": False},
    {"id": "feature_discovery", "name": "Feature Discovery", "icon": "✨", "description": "Explore all app features", "category": "Core", "new": True, "premium": False},
    {"id": "member_voice", "name": "Member Voice", "icon": "🗳️", "description": "Vote on investment proposals", "category": "Governance", "new": False, "premium": False},
    {"id": "ai_advisor", "name": "AI Advisor", "icon": "🤖", "description": "Smart investment insights for JSE", "category": "Analytics", "new": True, "premium": True},
    {"id": "constitution", "name": "Constitution", "icon": "📜", "description": "Club rules and governance", "category": "Governance", "new": False, "premium": False},
    {"id": "directory", "name": "Member Directory", "icon": "👥", "description": "Contact info and FICA status", "category": "Core", "new": False, "premium": False},
    {"id": "notifications", "name": "Notifications", "icon": "🔔", "description": "Alerts and updates", "category": "Core", "new": False, "premium": False},
    {"id": "reports", "name": "Reports", "icon": "📈", "description": "Detailed analytics and exports", "category": "Analytics", "new": False, "premium": True},
    {"id": "whatsapp", "name": "WhatsApp", "icon": "💬", "description": "Group chat integration", "category": "Communication", "new": True, "premium": False},
    {"id": "profile", "name": "Profile", "icon": "👤", "description": "Manage your account", "category": "Core", "new": False, "premium": False},
    {"id": "admin", "name": "Admin Panel", "icon": "👑", "description": "Manage members and settings", "category": "Admin", "new": False, "premium": False},
]

SA_NEWS_HEADLINES = [
    "JSE All Share reaches new highs on mining rally",
    "SARB keeps interest rates unchanged at 8.25%",
    "Sasol announces green hydrogen investment plan",
    "Naspers/Prosus rally on Tencent earnings beat",
    "South African stokvels manage over R50 billion annually",
    "Rand strengthens against dollar on improved trade data",
    "Gold Fields reports record quarterly production",
    "ABSA launches new wealth management platform",
    "FNB expands Open Banking API for fintechs",
    "Johannesburg property market shows signs of recovery",
]

# ============================================================
# DATABASE
# ============================================================
def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users
    c.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            role TEXT DEFAULT 'member',
            bank_account TEXT,
            bank_name TEXT DEFAULT 'FNB',
            monthly_contribution REAL DEFAULT 500,
            is_active INTEGER DEFAULT 1,
            theme_preference TEXT DEFAULT 'dark',
            fica_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Monthly Contributions
    c.execute("""
        CREATE TABLE IF NOT EXISTS Monthly_Contributions (
            contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            year INTEGER,
            month INTEGER,
            amount REAL DEFAULT 0,
            status TEXT DEFAULT 'pending',
            payment_date DATE,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    # Payment Schedules
    c.execute("""
        CREATE TABLE IF NOT EXISTS Payment_Schedules (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            due_date DATE,
            amount REAL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    # Investments
    c.execute("""
        CREATE TABLE IF NOT EXISTS Investments (
            investment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            amount_invested REAL,
            current_value REAL,
            return_pct REAL,
            start_date DATE,
            maturity_date DATE
        )
    """)

    # Suggestions
    c.execute("""
        CREATE TABLE IF NOT EXISTS Suggestions (
            suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            description TEXT,
            investment_type TEXT,
            amount REAL,
            votes INTEGER DEFAULT 0,
            voted_by TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    # Notifications
    c.execute("""
        CREATE TABLE IF NOT EXISTS Notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            message TEXT,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    # Announcements
    c.execute("""
        CREATE TABLE IF NOT EXISTS Announcements (
            announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            posted_by INTEGER,
            priority TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # FNB Sync Log
    c.execute("""
        CREATE TABLE IF NOT EXISTS FNB_Sync_Log (
            sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sync_type TEXT,
            status TEXT,
            transactions_synced INTEGER DEFAULT 0,
            error_message TEXT,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    # Bank Transactions
    c.execute("""
        CREATE TABLE IF NOT EXISTS Bank_Transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            transaction_date DATE,
            description TEXT,
            amount REAL,
            type TEXT,
            reference TEXT,
            synced_from TEXT DEFAULT 'manual',
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

    # Feature Usage
    c.execute("""
        CREATE TABLE IF NOT EXISTS Feature_Usage (
            usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            feature_id TEXT,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)

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

    users = [
        ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "Thabo Modupe", "admin@khula.co.za", "0821234567", "admin", "10010012345", "FNB", 1000),
        ("siphoo", hashlib.sha256("password1".encode()).hexdigest(), "Sipho Dlamini", "sipho@email.com", "0827654321", "member", "10010054321", "FNB", 500),
        ("lerato", hashlib.sha256("password2".encode()).hexdigest(), "Lerato Mokoena", "lerato@email.com", "0834567890", "member", "10010098765", "FNB", 750),
        ("james", hashlib.sha256("password3".encode()).hexdigest(), "James Nkosi", "james@email.com", "0845678901", "member", "10010011111", "FNB", 500),
        ("nomvula", hashlib.sha256("password4".encode()).hexdigest(), "Nomvula Zuma", "nomvula@email.com", "0856789012", "member", "10010022222", "FNB", 1000),
    ]

    for user in users:
        c.execute("INSERT INTO Users (username, password_hash, full_name, email, phone, role, bank_account, bank_name, monthly_contribution) VALUES (?,?,?,?,?,?,?,?,?)", user)

    # Demo contributions with some arrears
    current_year = datetime.now().year
    for uid in range(1, 6):
        for month in range(1, datetime.now().month + 1):
            c.execute("SELECT monthly_contribution FROM Users WHERE user_id=?", (uid,))
            mc = c.fetchone()[0]
            # Introduce deliberate arrears for demo
            if uid == 3 and month in [2, 3]:
                continue  # Lerato is behind
            if uid == 5 and month == 1:
                continue  # Nomvula missed January
            c.execute("INSERT INTO Monthly_Contributions (user_id, year, month, amount, status, payment_date) VALUES (?,?,?,?,?,?)",
                      (uid, current_year, month, mc, 'verified', f"{current_year}-{month:02d}-0{random.randint(1,7)}"))

    # Demo investments
    investments = [
        ("Naspers Ltd", "JSE Listed Equity", 50000, 62000, 24.0, "2024-01-15", "2025-01-15"),
        ("Sasol Ltd", "SASOL / Resources", 30000, 28500, -5.0, "2024-02-01", "2025-02-01"),
        ("Growthpoint REIT", "REITs (Property)", 25000, 26800, 7.2, "2024-03-10", "2025-03-10"),
        ("ABSA Bank Pref", "Bank Preference Shares", 20000, 21000, 5.0, "2024-01-20", "2025-01-20"),
    ]
    for inv in investments:
        c.execute("INSERT INTO Investments (name, type, amount_invested, current_value, return_pct, start_date, maturity_date) VALUES (?,?,?,?,?,?,?)", inv)

    # Demo suggestions
    suggestions = [
        (2, "Buy Anglo American", "Strong dividend yield and commodity exposure", "JSE Listed Equity", 15000),
        (3, "SARB Retail Bond", "Risk-free government backed investment", "SARB Retail Savings Bonds", 10000),
        (4, "Bitcoin Allocation", "5% portfolio exposure to crypto", "Crypto (Bitcoin)", 5000),
    ]
    for s in suggestions:
        c.execute("INSERT INTO Suggestions (user_id, title, description, investment_type, amount) VALUES (?,?,?,?,?)", s)

    conn.commit()
    conn.close()
