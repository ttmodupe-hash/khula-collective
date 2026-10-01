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
    risk_allowed = {"conservative": ["low"], "moderate": ["low", "medium"], "aggressive": ["low", "medium", "high"]}
    allowed_risks = risk_allowed.get(risk_profile, ["low", "medium"])

    # Get risk profile from user_profile
    risk_profile = user_profile.get("risk_tolerance", "moderate").lower()

    # Filter rows by risk (simulated: even=low, odd=medium)
    filtered = []
    for idx, row in enumerate(rows):
        simulated_risk = "low" if idx % 2 == 0 else "medium"
        if simulated_risk in allowed_risks:
            filtered.append(row)

    # Sort by simulated potential return (descending)
    filtered.sort(key=lambda x: x[3], reverse=True)

    recommendations = []
    for row in filtered[:top_n]:
        ticker, market, country, price = row
        rec = {
            "ticker": ticker,
            "market": market,
            "country": country,
            "current_price": price,
            "risk_level": "low" if filtered.index(row) % 2 == 0 else "medium",
            "potential_return_pct": round(5 + (filtered.index(row) * 2.5), 2),
            "currency": "ZAR" if country == "South Africa" else "USD",
            "min_investment_amount": 100,
            "is_actionable": 1
        }
        recommendations.append(rec)

    return recommendations

def store_portfolio_suggestion(user_id, suggestions):
    """Store multiple portfolio suggestions for a user."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for rec in suggestions:
        c.execute(f"""
            INSERT INTO {RECOMMENDATIONS_TABLE}
            (user_id, ticker, market, country, recommendation_type, target_price, risk_level, confidence, currency, is_actionable, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            rec["ticker"],
            rec.get("market"),
            rec.get("country"),
            "portfolio_suggestion",
            rec.get("current_price"),
            rec["risk_level"],
            "medium",
            rec.get("currency"),
            rec["is_actionable"],
            datetime.now().isoformat()
        ))
    conn.commit()
    conn.close()
    print(f"[Khula AI Engine] Stored {len(suggestions)} portfolio suggestions for {user_id}")

# --- Notification & Alert System ---
def send_price_alert(user_id, ticker, target_price, current_price, market, channel="whatsapp"):
    """Send a price alert to the user via preferred channel."""
    message = (f"🚨 Khula Price Alert: {ticker} ({market}) is now at {current_price}! "
               f"Your target was {target_price}.")
    if channel == "whatsapp":
        send_whatsapp_message(user_id, message)
    elif channel == "sms":
        send_sms_message(user_id, message)
    else:
        print(f"[Khula AI Engine] Alert for {user_id}: {message}")

def notify_new_recommendation(user_id, recommendation, channel="whatsapp"):
    """Notify user about a new recommendation."""
    msg = (f"📊 New Khula Recommendation: {recommendation['ticker']} ({recommendation['market']}) - "
           f"{recommendation['recommendation_type'].upper()} | Risk: {recommendation['risk_level']} | "
           f"Confidence: {recommendation['confidence']}")
    if channel == "whatsapp":
        send_whatsapp_message(user_id, msg)
    elif channel == "sms":
        send_sms_message(user_id, msg)
    else:
        print(f"[Khula AI Engine] Notification for {user_id}: {msg}")

# --- Batch Operations ---
def batch_update_market_prices(price_list):
    """
    Batch update market prices.
    price_list: list of dicts with keys ticker, market, country, current_price
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for item in price_list:
        c.execute(f"""
            INSERT INTO {MARKET_TABLE} (ticker, market, country, current_price, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (item["ticker"], item["market"], item.get("country"), item["current_price"], datetime.now().isoformat()))
    conn.commit()
    conn.close()
    print(f"[Khula AI Engine] Batch updated {len(price_list)} market prices.")

def batch_store_recommendations(user_id, recommendations):
    """Store multiple recommendations at once."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for rec in recommendations:
        c.execute(f"""
            INSERT INTO {RECOMMENDATIONS_TABLE}
            (user_id, ticker, market, country, recommendation_type, target_price, risk_level, confidence, currency, is_actionable, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            rec["ticker"],
            rec.get("market"),
            rec.get("country"),
            rec.get("recommendation_type", "buy"),
            rec.get("target_price"),
            rec.get("risk_level", "medium"),
            rec.get("confidence", "medium"),
            rec.get("currency"),
            rec.get("is_actionable", 1),
            datetime.now().isoformat()
        ))
    conn.commit()
    conn.close()
    print(f"[Khula AI Engine] Batch stored {len(recommendations)} recommendations for {user_id}")

# --- Utility Functions ---
def hash_user_id(user_id):
    """Hash a user ID for privacy."""
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]

def get_db_summary():
    """Return a summary of the database contents."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {MARKET_TABLE}")
    market_count = c.fetchone()[0]
    c.execute(f"SELECT COUNT(*) FROM {RECOMMENDATIONS_TABLE}")
    rec_count = c.fetchone()[0]
    conn.close()
    return {"market_entries": market_count, "recommendation_entries": rec_count}

# --- Main Entry Point ---
if __name__ == "__main__":
    init_market_db()
    print("[Khula AI Engine v4.0] Database initialized. Ready for market intelligence.")
