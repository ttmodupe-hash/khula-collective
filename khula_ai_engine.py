"""
Khula AI Engine v4.0 — Global Market Intelligence
Supercharged investment advisor with real-time market data.
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta
from khula_messaging import *

# --- Constants ---
DB_PATH = "khula_market.db"
MARKET_TABLE = "Global_Market_Prices"
RECOMMENDATIONS_TABLE = "User_Recommendations"

# --- Database Setup ---
def init_market_db():
    """Create required tables if not present."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {MARKET_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            market TEXT NOT NULL,
            country TEXT,
            current_price REAL NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    c.execute(f"""
        CREATE TABLE IF NOT EXISTS {RECOMMENDATIONS_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            ticker TEXT NOT NULL,
            market TEXT,
            country TEXT,
            recommendation_type TEXT,
            target_price REAL,
            risk_level TEXT,
            confidence TEXT,
            currency TEXT,
            is_actionable INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# --- Market Data Management ---
def update_market_price(ticker, market, country, current_price):
    """Insert or update a market price entry."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"""
        INSERT INTO {MARKET_TABLE} (ticker, market, country, current_price, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            current_price=excluded.current_price,
            last_updated=excluded.last_updated
    """, (ticker, market, country, current_price, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"[Khula AI Engine] Updated {ticker} ({market}, {country}) -> {current_price}")

def get_market_snapshot(ticker, market, country=None):
    """Retrieve latest price snapshot for a ticker."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if country:
        c.execute(f"""
            SELECT current_price, last_updated
            FROM {MARKET_TABLE}
            WHERE ticker = ? AND market = ? AND country = ?
            ORDER BY last_updated DESC LIMIT 1
        """, (ticker, market, country))
    else:
        c.execute(f"""
            SELECT current_price, last_updated
            FROM {MARKET_TABLE}
            WHERE ticker = ? AND market = ?
            ORDER BY last_updated DESC LIMIT 1
        """, (ticker, market))
    result = c.fetchone()
    conn.close()
    return result

def get_all_market_prices():
    """Return all current market prices."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT ticker, market, country, current_price, last_updated FROM {MARKET_TABLE}")
    rows = c.fetchall()
    conn.close()
    return rows

# --- Recommendation Engine ---
def generate_recommendation(user_profile, ticker_data):
    """
    Generate a tailored investment recommendation.
    user_profile: dict with keys like risk_tolerance, investment_goals, etc.
    ticker_data: dict with keys ticker, market, current_price, target_price, etc.
    """
    risk_map = {
        "low": "conservative",
        "medium": "moderate",
        "high": "aggressive"
    }
    user_risk = user_profile.get("risk_tolerance", "medium").lower()
    ticker_risk = ticker_data.get("risk_level", "medium").lower()

    # Match risk level
    if risk_map.get(ticker_risk, "moderate") != user_risk:
        return None

    recommendation_type = "buy"
    if ticker_data.get("current_price", 0) > ticker_data.get("target_price", 0):
        recommendation_type = "hold"
    elif ticker_data.get("current_price", 0) < ticker_data.get("target_price", 0) * 0.9:
        recommendation_type = "strong_buy"

    confidence = "medium"
    if ticker_data.get("confidence_score", 0) > 0.8:
        confidence = "high"
    elif ticker_data.get("confidence_score", 0) < 0.4:
        confidence = "low"

    return {
        "ticker": ticker_data["ticker"],
        "market": ticker_data.get("market"),
        "country": ticker_data.get("country"),
        "recommendation_type": recommendation_type,
        "target_price": ticker_data.get("target_price"),
        "risk_level": ticker_risk,
        "confidence": confidence,
        "currency": ticker_data.get("currency"),
        "is_actionable": 1 if recommendation_type in ["buy", "strong_buy"] else 0
    }

def store_recommendation(user_id, recommendation):
    """Save a recommendation to the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"""
        INSERT INTO {RECOMMENDATIONS_TABLE}
        (user_id, ticker, market, country, recommendation_type, target_price, risk_level, confidence, currency, is_actionable, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        recommendation["ticker"],
        recommendation.get("market"),
        recommendation.get("country"),
        recommendation["recommendation_type"],
        recommendation.get("target_price"),
        recommendation["risk_level"],
        recommendation["confidence"],
        recommendation.get("currency"),
        recommendation["is_actionable"],
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()
    print(f"[Khula AI Engine] Stored recommendation for {user_id}: {recommendation['ticker']} ({recommendation['recommendation_type']})")

def get_user_recommendations(user_id, limit=10):
    """Retrieve recent recommendations for a user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"""
        SELECT * FROM {RECOMMENDATIONS_TABLE}
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# --- AI-Driven Analysis ---
def analyze_market_trends(ticker, market, days=30):
    """
    Analyze market trends for a given ticker.
    Returns a trend summary dict.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    c.execute(f"""
        SELECT current_price, last_updated
        FROM {MARKET_TABLE}
        WHERE ticker = ? AND market = ? AND last_updated >= ?
        ORDER BY last_updated ASC
    """, (ticker, market, cutoff))
    rows = c.fetchall()
    conn.close()

    if not rows or len(rows) < 2:
        return {"trend": "insufficient_data", "volatility": None, "avg_price": None}

    prices = [r[0] for r in rows]
    avg_price = sum(prices) / len(prices)
    volatility = max(prices) - min(prices)
    trend = "upward" if prices[-1] > prices[0] else "downward" if prices[-1] < prices[0] else "stable"

    return {
        "trend": trend,
        "volatility": round(volatility, 4),
        "avg_price": round(avg_price, 4),
        "data_points": len(prices)
    }

def ai_portfolio_suggestion(user_profile, market="all", top_n=5):
    """
    AI-driven portfolio suggestion based on user profile and market data.
    Returns a list of top ticker recommendations.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if market == "all":
        c.execute(f"SELECT ticker, market, country, current_price FROM {MARKET_TABLE} WHERE current_price > 0")
    else:
        c.execute(f"SELECT ticker, market, country, current_price FROM {MARKET_TABLE} WHERE market = ? AND current_price > 0", (market,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return []

    # Risk level filtering

# KHULA_APPEND_MARKER_7a3f9e2d
