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
    {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "region": "US", "risk_level": "low", "category": "etf", "exchange": "NYSE"},
    {"ticker": "QQQ", "name": "Invesco Nasdaq-100 ETF", "region": "US", "risk_level": "medium", "category": "etf", "exchange": "NASDAQ"},
    # EU
    {"ticker": "ASML", "name": "ASML Holding NV", "region": "EU", "risk_level": "medium", "category": "stock", "exchange": "NASDAQ"},
    {"ticker": "SAP", "name": "SAP SE", "region": "EU", "risk_level": "medium", "category": "stock", "exchange": "NYSE"},

# KHULA_APPEND_MARKER_7a3f9e2d
