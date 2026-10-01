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
    {"id": "fnb_sync", "name": "FNB Bank Sync", "icon": "🏦", "description": "Automatic FNB transaction sync + statement upload", "category": "Banking", "new": True, "premium": False},
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

SA_MARKET_DATASET = {
    "jse_allshare": {"value": 82345, "change": +1.2, "trend": "up"},
    "top40": {"value": 74520, "change": +0.8, "trend": "up"},
    "sarb_rate": {"value": 8.25, "change": 0.0, "trend": "flat"},
    "usd_zar": {"value": 18.45, "change": -0.3, "trend": "down"},
    "gold_price": {"value": 35200, "change": +2.1, "trend": "up"},
    "brent_oil": {"value": 78.50, "change": -1.2, "trend": "down"},
    "naspers": {"value": 2850, "change": +3.5, "trend": "up"},
    "sasol": {"value": 445, "change": -2.1, "trend": "down"},
    "anglo_american": {"value": 620, "change": +1.8, "trend": "up"},
    "growthpoint": {"value": 12.45, "change": +0.5, "trend": "up"},
}

AI_ADVISOR_KNOWLEDGE = {
    "jse_sectors": {
        "resources": {"outlook": "positive", "drivers": ["Gold price surge", "Platinum demand"], "risk": "medium", "top_picks": ["Anglo American", "Sibanye-Stillwater", "Gold Fields"]},
        "financials": {"outlook": "stable", "drivers": ["Interest rate stability", "Banking sector resilience"], "risk": "low", "top_picks": ["FNB/FirstRand", "Standard Bank", "Nedbank"]},
        "property": {"outlook": "recovering", "drivers": ["Interest rate pause", "Office vacancy decline"], "risk": "medium", "top_picks": ["Growthpoint", "Redefine", "Emira"]},
        "tech": {"outlook": "volatile", "drivers": ["Naspers/Prosus NAV discount", "Tencent exposure"], "risk": "high", "top_picks": ["Naspers", "Prosus"]},
    },
    "stokvel_strategies": [
        "Rotate 40% into JSE Top 40 ETFs for diversification",
        "Allocate 30% to SARB Retail Savings Bonds for stability",
        "Keep 20% liquid in money market for opportunities",
        "Reserve 10% for high-conviction individual stock picks",
    ],
    "risk_profiles": {
        "conservative": {"allocation": {"bonds": 50, "cash": 30, "equity": 15, "crypto": 5}, "expected_return": "8-10%"},
        "moderate": {"allocation": {"bonds": 30, "cash": 20, "equity": 40, "crypto": 10}, "expected_return": "12-15%"},
        "aggressive": {"allocation": {"bonds": 15, "cash": 10, "equity": 60, "crypto": 15}, "expected_return": "18-25%"},
    },
}

# ============================================================
# V4.0 GLOBAL MARKET INTELLIGENCE
# ============================================================

GLOBAL_TICKER_UNIVERSE = [
    # SA / JSE — Blue-chip & ETF
    {"ticker": "SHP.JO", "name": "Shoprite Holdings", "region": "SA", "risk_level": "low", "category": "stock", "exchange": "JSE"},
    {"ticker": "AGL.JO", "name": "Anglo American plc", "region": "SA", "risk_level": "medium", "category": "stock", "exchange": "JSE"},
    {"ticker": "MTN.JO", "name": "MTN Group", "region": "SA", "risk_level": "medium", "category": "stock", "exchange": "JSE"},
    {"ticker": "NPN.JO", "name": "Naspers Ltd", "region": "SA", "risk_level": "medium", "category": "stock", "exchange": "JSE"},
    {"ticker": "FSR.JO", "name": "FirstRand Ltd", "region": "SA", "risk_level": "low", "category": "stock", "exchange": "JSE"},
    {"ticker": "STX40.JO", "name": "Satrix 40 ETF", "region": "SA", "risk_level": "low", "category": "etf", "exchange": "JSE"},
    # US / NYSE + NASDAQ
    {"ticker": "AAPL", "name": "Apple Inc", "region": "US", "risk_level": "low", "category": "stock", "exchange": "NASDAQ"},
    {"ticker": "MSFT", "name": "Microsoft Corp", "region": "US", "risk_level": "low", "category": "stock", "exchange": "NASDAQ"},
    {"ticker": "GOOGL", "name": "Alphabet Inc", "region": "US", "risk_level": "medium", "category": "stock", "exchange": "NASDAQ"},
    {"ticker": "AMZN", "name": "Amazon.com Inc", "region": "US", "risk_level": "medium", "category": "stock", "exchange": "NASDAQ"},
    {"ticker": "TSLA", "name": "Tesla Inc", "region": "US", "risk_level": "high", "category": "stock", "exchange": "NASDAQ"},
    {"ticker": "NVDA", "name": "NVIDIA Corp", "region": "US", "risk_level": "medium", "category": "stock", "exchange": "NASDAQ"},
    {"ticker": "JPM", "name": "JPMorgan Chase", "region": "US", "risk_level": "low", "category": "stock", "exchange": "NYSE"},
    {"ticker": "BRK-B", "name": "Berkshire Hathaway", "region": "US", "risk_level": "low", "category": "stock", "exchange": "NYSE"},
    {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "region": "US", "risk_level": "low", "category": "etf", "exchange": "NYSEARCA"},
    # EU / LSE + Euronext
    {"ticker": "SAP.DE", "name": "SAP SE", "region": "EU", "risk_level": "low", "category": "stock", "exchange": "XETRA"},
    {"ticker": "ASML.AS", "name": "ASML Holding", "region": "EU", "risk_level": "medium", "category": "stock", "exchange": "Euronext"},
    {"ticker": "NESN.SW", "name": "Nestlé SA", "region": "EU", "risk_level": "low", "category": "stock", "exchange": "SIX"},
    {"ticker": "LVMH.PA", "name": "LVMH Moët Hennessy", "region": "EU", "risk_level": "medium", "category": "stock", "exchange": "Euronext"},
    {"ticker": "AIR.PA", "name": "Airbus SE", "region": "EU", "risk_level": "medium", "category": "stock", "exchange": "Euronext"},
    {"ticker": "EXS1.DE", "name": "iShares EURO STOXX 50", "region": "EU", "risk_level": "low", "category": "etf", "exchange": "XETRA"},
    # Emerging Markets
    {"ticker": "0700.HK", "name": "Tencent Holdings", "region": "EM", "risk_level": "medium", "category": "stock", "exchange": "HKEX"},
    {"ticker": "BABA", "name": "Alibaba Group", "region": "EM", "risk_level": "high", "category": "stock", "exchange": "NYSE"},
    {"ticker": "TCEHY", "name": "Tesla rival / EV EM", "region": "EM", "risk_level": "high", "category": "stock", "exchange": "OTC"},
    # Crypto
    {"ticker": "BTC-USD", "name": "Bitcoin USD", "region": "Crypto", "risk_level": "high", "category": "crypto", "exchange": "CCY"},
    {"ticker": "ETH-USD", "name": "Ethereum USD", "region": "Crypto", "risk_level": "high", "category": "crypto", "exchange": "CCY"},
    # Commodities
    {"ticker": "GC=F", "name": "Gold Futures", "region": "Commodity", "risk_level": "medium", "category": "commodity", "exchange": "COMEX"},
    {"ticker": "CL=F", "name": "Crude Oil WTI", "region": "Commodity", "risk_level": "medium", "category": "commodity", "exchange": "NYMEX"},
]

ZAR_RATES = {"USD": 18.5, "EUR": 20.2, "GBP": 23.8}

SA_ID_RULES = {
    "length": 13,
    "dob_start": 0, "dob_end": 6,
    "gender_start": 6, "gender_end": 7,
    "citizenship_start": 10, "citizenship_end": 11,
    "checksum_start": 12, "checksum_end": 13,
}

# ============================================================
# DATABASE INITIALISATION
# ============================================================

def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        id_number TEXT,
        monthly_contribution REAL DEFAULT 500,
        join_date TEXT,
        role TEXT DEFAULT 'member',
        is_active INTEGER DEFAULT 1,
        fica_verified INTEGER DEFAULT 0,
        theme_preference TEXT DEFAULT 'dark',
        risk_profile TEXT DEFAULT 'moderate',
        last_login TEXT,
        notification_prefs TEXT DEFAULT 'all'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Monthly_Contributions (
        contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        year INTEGER,
        month INTEGER,
        amount REAL DEFAULT 0,
        status TEXT DEFAULT 'pending',
        payment_date TEXT,
        payment_method TEXT,
        reference TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Investments (
        investment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT,
        amount_invested REAL DEFAULT 0,
        current_value REAL DEFAULT 0,
        purchase_date TEXT,
        maturity_date TEXT,
        interest_rate REAL,
        returns REAL DEFAULT 0,
        status TEXT DEFAULT 'active',
        risk_level TEXT DEFAULT 'moderate',
        notes TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Portfolio (
        portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
        investment_id INTEGER,
        user_id INTEGER,
        shares REAL DEFAULT 0,
        purchase_price REAL,
        purchase_date TEXT,
        FOREIGN KEY(investment_id) REFERENCES Investments(investment_id),
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Votes (
        vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        proposal_id INTEGER,
        vote TEXT,
        voted_at TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Proposals (
        proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        proposed_by INTEGER,
        status TEXT DEFAULT 'open',
        created_at TEXT,
        closes_at TEXT,
        votes_for INTEGER DEFAULT 0,
        votes_against INTEGER DEFAULT 0,
        FOREIGN KEY(proposed_by) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        message TEXT,
        type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Bank_Transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        transaction_date TEXT,
        description TEXT,
        amount REAL,
        type TEXT,
        reference TEXT,
        category TEXT,
        synced_from TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Feature_Usage (
        usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        feature_id TEXT,
        used_at TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS AI_Conversations (
        conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question TEXT,
        response TEXT,
        context_data TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    # V4.0 TABLES
    c.execute('''CREATE TABLE IF NOT EXISTS ID_Verifications (
        verification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        id_hash TEXT,
        last_four_digits TEXT,
        verified_status TEXT,
        gender TEXT,
        citizenship TEXT,
        age INTEGER,
        verified_at TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS AI_Recommendations (
        recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ticker TEXT,
        name TEXT,
        region TEXT,
        rationale TEXT,
        estimated_return TEXT,
        risk_level TEXT,
        actionable TEXT,
        price_zar REAL,
        units_affordable INTEGER,
        total_cost_zar REAL,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Global_Market_Prices (
        price_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT UNIQUE,
        name TEXT,
        region TEXT,
        category TEXT,
        price_usd REAL,
        price_zar REAL,
        change_pct REAL,
        market_cap TEXT,
        pe_ratio REAL,
        dividend_yield REAL,
        updated_at TEXT
    )''')

    # Seed demo users
    demo_users = [
        ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "Admin User", "admin", "moderate"),
        ("siphoo", hashlib.sha256("password1".encode()).hexdigest(), "Sipho Mabena", "member", "moderate"),
    ]
    for username, pw_hash, full_name, role, risk in demo_users:
        c.execute("INSERT OR IGNORE INTO Users (username, password_hash, full_name, role, risk_profile, join_date, is_active) VALUES (?,?,?,?,?,?,1)",
                  (username, pw_hash, full_name, role, risk, datetime.now().isoformat()))

    # Seed sample investments
    sample_investments = [
        ("JSE Top 40 Tracker", "Unit Trusts", 15000, 16200, "2024-01-15", None, 8.0, 1200, "active", "low"),
        ("SASOL Resources Basket", "SASOL / Resources", 5000, 4850, "2024-03-01", None, None, -150, "active", "high"),
        ("Growthpoint REIT", "REITs (Property)", 8000, 8200, "2024-02-10", None, 6.5, 200, "active", "medium"),
        ("SARB Retail Savings Bond", "SARB Retail Savings Bonds", 10000, 10500, "2024-01-01", "2027-01-01", 10.0, 500, "active", "low"),
    ]
    for name, itype, invested, current, purchase, maturity, rate, ret, status, risk in sample_investments:
        c.execute("INSERT OR IGNORE INTO Investments (name, type, amount_invested, current_value, purchase_date, maturity_date, interest_rate, returns, status, risk_level) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (name, itype, invested, current, purchase, maturity, rate, ret, status, risk))

    conn.commit()
    conn.close()
