def load_css(theme):
    if theme == "dark":
        return """
        <style>
            .stApp { background: #0a0a1a; color: #e0e0e0; }
            .css-18e3th9 { padding: 0; }
            h1, h2, h3, h4 { color: #f0f0f0; font-family: 'Inter', sans-serif; }
            .stButton>button { background: #6366f1; color: white; border-radius: 12px; padding: 0.6rem 1.2rem; font-weight: 600; border: none; transition: all 0.3s; }
            .stButton>button:hover { background: #4f46e5; transform: translateY(-2px); box-shadow: 0 8px 25px rgba(99,102,241,0.3); }
            .metric-card { background: #1e1e3a; border-radius: 16px; padding: 1.5rem; border: 1px solid #2a2a50; margin: 0.5rem 0; }
            .metric-value { font-size: 2rem; font-weight: 700; color: #6366f1; }
            .metric-label { font-size: 0.875rem; color: #8892b0; text-transform: uppercase; letter-spacing: 1px; }
            .feature-card { background: #1e1e3a; border-radius: 12px; padding: 1.5rem; border: 1px solid #2a2a50; margin: 0.5rem 0; transition: all 0.3s; cursor: pointer; }
            .feature-card:hover { border-color: #6366f1; transform: translateY(-3px); box-shadow: 0 12px 30px rgba(99,102,241,0.15); }
            .feature-icon { font-size: 2rem; margin-bottom: 0.5rem; }
            .stTabs [data-baseweb="tab-list"] { gap: 8px; }
            .stTabs [data-baseweb="tab"] { background: #1e1e3a; border-radius: 8px 8px 0 0; padding: 10px 20px; color: #8892b0; }
            .stTabs [aria-selected="true"] { background: #6366f1 !important; color: white !important; }
            .progress-bar { background: #2a2a50; border-radius: 10px; height: 8px; overflow: hidden; }
            .progress-fill { background: #00b894; height: 100%; border-radius: 10px; transition: width 0.5s ease; }
            .progress-fill.warning { background: #fdcb6e; }
            .progress-fill.danger { background: #e74c3c; }
            .notification-item { background: #1e1e3a; border-radius: 12px; padding: 1rem; margin: 0.5rem 0; border-left: 4px solid #6366f1; }
            .notification-item.unread { border-left-color: #00b894; }
            .mobile-nav { position: fixed; bottom: 0; left: 0; right: 0; background: #1e1e3a; border-top: 1px solid #2a2a50; padding: 0.8rem; display: flex; justify-content: space-around; z-index: 9999; }
            .mobile-nav-item { text-align: center; color: #8892b0; font-size: 0.75rem; }
            .mobile-nav-item.active { color: #6366f1; }
            .stDataFrame { background: #1e1e3a; border-radius: 12px; }
            div[data-testid="stSidebarNav"] { background: #0f0f23; }
            .css-1d391kg { background: #0f0f23; }
        </style>
        """
    else:
        return """
        <style>
            .stApp { background: #f8fafc; color: #1e293b; }
            h1, h2, h3, h4 { color: #0f172a; font-family: 'Inter', sans-serif; }
            .stButton>button { background: #6366f1; color: white; border-radius: 12px; padding: 0.6rem 1.2rem; font-weight: 600; border: none; }
            .metric-card { background: white; border-radius: 16px; padding: 1.5rem; border: 1px solid #e2e8f0; margin: 0.5rem 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            .metric-value { font-size: 2rem; font-weight: 700; color: #6366f1; }
            .metric-label { font-size: 0.875rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }
            .feature-card { background: white; border-radius: 12px; padding: 1.5rem; border: 1px solid #e2e8f0; margin: 0.5rem 0; }
            .progress-bar { background: #e2e8f0; border-radius: 10px; height: 8px; overflow: hidden; }
            .progress-fill { background: #00b894; height: 100%; border-radius: 10px; }
            .mobile-nav { position: fixed; bottom: 0; left: 0; right: 0; background: white; border-top: 1px solid #e2e8f0; padding: 0.8rem; display: flex; justify-content: space-around; z-index: 9999; }
        </style>
        """

class FNBAPIClient:
    def __init__(self):
        self.base_url = FNB_API_BASE
        self.token = None

    def connect(self, client_id, client_secret):
        if not client_id or not client_secret:
            return False, "FNB credentials not configured. Set FNB_CLIENT_ID and FNB_CLIENT_SECRET environment variables."
        self.token = f"simulated_token_{hashlib.sha256(f'{client_id}:{client_secret}'.encode()).hexdigest()[:16]}"
        return True, "Connected to FNB Open Banking (Simulated)"

    def get_transactions(self, account_id, start_date, end_date):
        if not self.token:
            return []
        simulated = [
            {"date": start_date, "description": "FNB Monthly Contribution", "amount": 500.00, "type": "credit", "reference": "SIM001"},
            {"date": end_date, "description": "FNB Investment Dividend", "amount": 1250.00, "type": "credit", "reference": "SIM002"},
            {"date": start_date, "description": "FNB Bank Charges", "amount": -45.00, "type": "debit", "reference": "SIM003"},
        ]
        return simulated

    def sync_contributions(self, user_id, transactions):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        synced = 0
        for tx in transactions:
            if "contribution" in tx["description"].lower() and tx["type"] == "credit":
                c.execute("INSERT INTO Monthly_Contributions (user_id, year, month, amount, status, payment_date) VALUES (?,?,?,?,?,?)",
                          (user_id, datetime.now().year, datetime.now().month, tx["amount"], 'verified', tx["date"]))
                synced += 1
        conn.commit()
        conn.close()
        return synced

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, full_name, role, theme_preference FROM Users WHERE username=? AND password_hash=? AND is_active=1",
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    if user:
        return {"user_id": user[0], "username": user[1], "full_name": user[2], "role": user[3], "theme": user[4]}
    return None

def add_notification(user_id, title, message, notif_type="info"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Notifications (user_id, title, message, type) VALUES (?,?,?,?)", (user_id, title, message, notif_type))
    conn.commit()
    conn.close()

def get_notifications(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT notification_id, title, message, type, is_read, created_at FROM Notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def mark_notification_read(notification_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE Notifications SET is_read=1 WHERE notification_id=?", (notification_id,))
    conn.commit()
    conn.close()

def toggle_theme(user_id, current_theme):
    new_theme = "light" if current_theme == "dark" else "dark"
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE Users SET theme_preference=? WHERE user_id=?", (new_theme, user_id))
    conn.commit()
    conn.close()
    return new_theme

def track_feature_usage(user_id, feature_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO Feature_Usage (user_id, feature_id) VALUES (?,?)", (user_id, feature_id))
    conn.commit()
    conn.close()

def get_feature_usage_stats(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT feature_id, COUNT(*) FROM Feature_Usage WHERE user_id=? GROUP BY feature_id", (user_id,))
    rows = c.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

# ============================================================
# STATEMENT PARSER (v3.1)
# ============================================================

def parse_pdf_statement(pdf_file, user_id):
    """Parse FNB PDF bank statement and extract transactions.
    Returns list of dicts: {date, description, amount, type, reference}
    """
    import pdfplumber
    import re
    transactions = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                for line in lines:
                    # Match date at start: DD MMM YYYY or DD/MM/YYYY
                    date_match = re.search(r'(\d{2}\s+[A-Za-z]{3}\s+\d{4}|\d{2}/\d{2}/\d{4})', line)
                    # Match amount (R xxx.xx or just xxx.xx)
                    amount_match = re.search(r'([\d,]+\.\d{2})', line)
                    if date_match and amount_match:
                        # Determine if debit or credit
                        tx_type = "debit" if any(kw in line.lower() for kw in ["debit", "dr", "fee", "charge", "withdrawal"]) else "credit"
                        # Extract description (between date and amount)
                        desc = line[date_match.end():amount_match.start()].strip()
                        if len(desc) < 3:
                            desc = "Unknown Transaction"
                        transactions.append({
                            "date": date_match.group(1),
                            "description": desc[:100],
                            "amount": float(amount_match.group(1).replace(",", "")),
                            "type": tx_type,
                            "reference": f"STMT{hashlib.sha256(line.encode()).hexdigest()[:8].upper()}"
                        })
    return transactions

def parse_csv_statement(csv_file, user_id):
    """Parse FNB CSV bank statement. Returns list of transaction dicts."""
    import pandas as pd
    df = pd.read_csv(csv_file)
    transactions = []
    # Try common FNB CSV column names
    date_col = next((c for c in df.columns if 'date' in c.lower()), df.columns[0])
    desc_col = next((c for c in df.columns if any(x in c.lower() for x in ['desc', 'narrative', 'detail'])), df.columns[1])
    amount_col = next((c for c in df.columns if 'amount' in c.lower()), None)
    debit_col = next((c for c in df.columns if 'debit' in c.lower()), None)
    credit_col = next((c for c in df.columns if 'credit' in c.lower()), None)

    for _, row in df.iterrows():
        desc = str(row.get(desc_col, ""))
        if pd.isna(desc) or desc.strip() == "":
            continue

        if amount_col and not pd.isna(row.get(amount_col)):
            amount = abs(float(row[amount_col]))
            tx_type = "debit" if float(row[amount_col]) < 0 else "credit"
        elif debit_col and not pd.isna(row.get(debit_col)) and float(row[debit_col]) > 0:
            amount = float(row[debit_col])
            tx_type = "debit"
        elif credit_col and not pd.isna(row.get(credit_col)) and float(row[credit_col]) > 0:
            amount = float(row[credit_col])
            tx_type = "credit"
        else:
            continue

        transactions.append({
            "date": str(row.get(date_col, datetime.now().strftime("%Y-%m-%d"))),
            "description": desc[:100],
            "amount": amount,
            "type": tx_type,
            "reference": f"CSV{hashlib.sha256(str(row).encode()).hexdigest()[:8].upper()}"
        })
    return transactions

def categorize_transaction(description, amount, tx_type):
    """Categorize a transaction based on description keywords."""
    desc_lower = description.lower()

    contribution_keywords = ["khula", "stokvel", "contribution", "monthly payment", "club", "collective", "pool"]
    income_keywords = ["salary", "wage", "deposit", "transfer in", "payment received"]
    investment_keywords = ["investment", "buy", "purchase", "dividend", "interest"]
    expense_keywords = ["shop", "store", "restaurant", "fuel", "petrol", "uber", "takealot", "checkers", "woolworths"]
    fee_keywords = ["fee", "charge", "commission", "bank charge", "service fee"]

    if any(kw in desc_lower for kw in contribution_keywords):
        return "contribution"
    elif any(kw in desc_lower for kw in income_keywords):
        return "income"
    elif any(kw in desc_lower for kw in investment_keywords):
        return "investment"
    elif any(kw in desc_lower for kw in expense_keywords):
        return "expense"
    elif any(kw in desc_lower for kw in fee_keywords):
        return "fee"
    elif tx_type == "credit":
        return "income"
    else:
        return "expense"

def save_parsed_transactions(user_id, transactions, source="statement_upload"):
    """Save parsed transactions to Bank_Transactions table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    saved = 0
    for tx in transactions:
        category = categorize_transaction(tx["description"], tx["amount"], tx["type"])
        # Check for duplicates by reference
        c.execute("SELECT COUNT(*) FROM Bank_Transactions WHERE user_id=? AND reference=?", (user_id, tx["reference"]))
        if c.fetchone()[0] == 0:
            c.execute("""
                INSERT INTO Bank_Transactions (user_id, transaction_date, description, amount, type, reference, category, synced_from)
                VALUES (?,?,?,?,?,?,?,?)
            """, (user_id, tx["date"], tx["description"], tx["amount"], tx["type"], tx["reference"], category, source))
            saved += 1
    conn.commit()
    conn.close()
    return saved

def get_user_statement_summary(user_id):
    """Get summary of user's bank transactions for AI context."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Total income vs expenses
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Bank_Transactions WHERE user_id=? AND type='credit'", (user_id,))
    total_income = c.fetchone()[0] or 0
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Bank_Transactions WHERE user_id=? AND type='debit'", (user_id,))
    total_expenses = c.fetchone()[0] or 0

    # Category breakdown
    c.execute("SELECT category, COALESCE(SUM(amount), 0), COUNT(*) FROM Bank_Transactions WHERE user_id=? GROUP BY category", (user_id,))
    categories = c.fetchall()

    # Recent contributions detected
    c.execute("SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM Bank_Transactions WHERE user_id=? AND category='contribution'", (user_id,))
    contrib_data = c.fetchone()

    # Monthly trend (last 3 months)
    c.execute("""
        SELECT strftime('%Y-%m', transaction_date) as month,
               COALESCE(SUM(CASE WHEN type='credit' THEN amount ELSE 0 END), 0) as income,
               COALESCE(SUM(CASE WHEN type='debit' THEN amount ELSE 0 END), 0) as expense
        FROM Bank_Transactions
        WHERE user_id=? AND transaction_date >= date('now', '-3 months')
        GROUP BY month ORDER BY month DESC LIMIT 3
    """, (user_id,))
    monthly_trend = c.fetchall()

    conn.close()
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_flow": total_income - total_expenses,
        "categories": categories,
        "contributions_detected": contrib_data[0] if contrib_data else 0,
        "contribution_count": contrib_data[1] if contrib_data else 0,
        "monthly_trend": monthly_trend
    }

def get_ai_context(user_id):
    """Build rich context for AI advisor based on user's data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # User profile
    c.execute("SELECT full_name, monthly_contribution, risk_profile FROM Users WHERE user_id=?", (user_id,))
    user = c.fetchone()

    # Portfolio
    c.execute("SELECT COALESCE(SUM(current_value), 0) FROM Investments")
    portfolio_value = c.fetchone()[0] or 0

    # Contribution status
    current_year = datetime.now().year
    current_month = datetime.now().month
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM Monthly_Contributions WHERE user_id=? AND year=? AND month=?", (user_id, current_year, current_month))
    this_month_contrib = c.fetchone()[0] or 0

    # Statement summary
    stmt_summary = get_user_statement_summary(user_id)

    conn.close()

    return {
        "user_name": user[0] if user else "Member",
        "monthly_target": user[1] if user else 500,
        "risk_profile": user[2] if user else "moderate",
        "portfolio_value": portfolio_value,
        "this_month_contrib": this_month_contrib,
        "statement_summary": stmt_summary
    }

def save_ai_conversation(user_id, question, response, context):
    """Save AI conversation to database."""
    import json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO AI_Conversations (user_id, question, response, context_data) VALUES (?,?,?,?)",
              (user_id, question, response, json.dumps(context)))
    conn.commit()
    conn.close()

def get_ai_conversation_history(user_id, limit=10):
    """Get recent AI conversations for context."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT question, response, created_at FROM AI_Conversations WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows
