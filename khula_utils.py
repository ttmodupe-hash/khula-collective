import sqlite3
import os
import re
from datetime import datetime, timedelta
from passlib.hash import bcrypt
import secrets
import string
import hashlib
from collections import defaultdict

# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = os.environ.get("KOPANO_DB_PATH", "/var/lib/kopano/kopano.db")
UPLOAD_DIR = os.environ.get("KOPANO_UPLOAD_DIR", "/var/lib/kopano/uploads")

# ============================================================
# DATABASE SETUP / MIGRATION
# ============================================================

def init_database():
    """Ensure all required tables exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            mpin_hash TEXT,
            language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 0
        )
    """)

    # Categories table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            icon TEXT,
            color TEXT,
            is_system INTEGER DEFAULT 0,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES Users(id)
        )
    """)

    # Financial Accounts table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Financial_Accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- bank, mobile_money, cash, investment, credit
            provider TEXT, -- FNB, Standard Bank, MTN MoMo, etc.
            account_number TEXT,
            currency TEXT DEFAULT 'ZAR',
            balance REAL DEFAULT 0.0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )
    """)

    # Transactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id INTEGER,
            category_id INTEGER,
            type TEXT NOT NULL, -- income, expense, transfer
            amount REAL NOT NULL,
            description TEXT,
            merchant TEXT,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_recurring INTEGER DEFAULT 0,
            recurring_period TEXT, -- daily, weekly, monthly, yearly
            receipt_path TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES Users(id),
            FOREIGN KEY (account_id) REFERENCES Financial_Accounts(id),
            FOREIGN KEY (category_id) REFERENCES Categories(id)
        )
    """)

    # Budgets table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            amount REAL NOT NULL,
            period TEXT NOT NULL, -- weekly, monthly, yearly
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            alert_threshold REAL DEFAULT 80.0,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES Users(id),
            FOREIGN KEY (category_id) REFERENCES Categories(id)
        )
    """)

    # Savings Goals table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Savings_Goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0.0,
            deadline TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )
    """)

    # AI Conversations table
    c.execute("""
        CREATE TABLE IF NOT EXISTS AI_Conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            response TEXT NOT NULL,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )
    """)

    # Notifications table
    c.execute("""
        CREATE TABLE IF NOT EXISTS Notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info', -- info, warning, success, error
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )
    """)

    # Insert default categories if not exist
    default_categories = [
        ("Food & Dining", "utensils", "#FF6B6B", 1),
        ("Transportation", "car", "#4ECDC4", 1),
        ("Shopping", "shopping-bag", "#45B7D1", 1),
        ("Entertainment", "film", "#96CEB4", 1),
        ("Bills & Utilities", "zap", "#FFEAA7", 1),
        ("Healthcare", "heart-pulse", "#DDA0DD", 1),
        ("Education", "book-open", "#98D8C8", 1),
        ("Income", "trending-up", "#2ECC71", 1),
        ("Savings", "piggy-bank", "#F39C12", 1),
        ("Investments", "bar-chart-2", "#9B59B6", 1),
    ]
    for cat in default_categories:
        c.execute("SELECT id FROM Categories WHERE name = ?", (cat[0],))
        if not c.fetchone():
            c.execute(
                "INSERT INTO Categories (name, icon, color, is_system) VALUES (?, ?, ?, ?)",
                cat
            )

    conn.commit()
    conn.close()

# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def hash_password(password):
    return bcrypt.hash(password)

def verify_password(password, hashed):
    return bcrypt.verify(password, hashed)

def generate_secure_token(length=32):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_mpin():
    """Generate a random 5-digit MPIN."""
    return ''.join(secrets.choice(string.digits) for _ in range(5))

# ============================================================
# USER MANAGEMENT
# ============================================================

def create_user(full_name, email, phone, password, mpin=None, language='en'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        password_hash = hash_password(password)
        mpin_hash = hash_password(mpin) if mpin else None
        c.execute("""
            INSERT INTO Users (full_name, email, phone, password_hash, mpin_hash, language)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (full_name, email, phone, password_hash, mpin_hash, language))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def authenticate_user(email, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, password_hash, full_name, is_admin FROM Users WHERE email = ? AND is_active = 1", (email,))
    row = c.fetchone()
    conn.close()
    if row and verify_password(password, row[1]):
        return {"id": row[0], "name": row[2], "is_admin": bool(row[3])}
    return None

def authenticate_mpin(user_id, mpin):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT mpin_hash FROM Users WHERE id = ? AND is_active = 1", (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row[0] and verify_password(mpin, row[0]):
        return True
    return False

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, full_name, email, phone, language, is_admin, created_at FROM Users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "full_name": row[1], "email": row[2],
            "phone": row[3], "language": row[4], "is_admin": bool(row[5]),
            "created_at": row[6]
        }
    return None

# ============================================================
# ACCOUNT MANAGEMENT
# ============================================================

def add_account(user_id, name, acc_type, provider=None, account_number=None, currency='ZAR', balance=0.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO Financial_Accounts (user_id, name, type, provider, account_number, currency, balance)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, name, acc_type, provider, account_number, currency, balance))
    conn.commit()
    acc_id = c.lastrowid
    conn.close()
    return acc_id

def get_user_accounts(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, type, provider, account_number, currency, balance, is_active, created_at
        FROM Financial_Accounts WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    accounts = []
    for row in rows:
        accounts.append({
            "id": row[0], "name": row[1], "type": row[2], "provider": row[3],
            "account_number": row[4], "currency": row[5], "balance": row[6],
            "is_active": bool(row[7]), "created_at": row[8]
        })
    return accounts

def update_account_balance(account_id, new_balance):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE Financial_Accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
    conn.commit()
    conn.close()

# ============================================================
# TRANSACTION MANAGEMENT
# ============================================================

def add_transaction(user_id, account_id, category_id, t_type, amount, description=None,
                    merchant=None, transaction_date=None, is_recurring=0,
                    recurring_period=None, receipt_path=None, notes=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if transaction_date is None:
        transaction_date = datetime.now().isoformat()
    c.execute("""
        INSERT INTO Transactions
        (user_id, account_id, category_id, type, amount, description, merchant,
         transaction_date, is_recurring, recurring_period, receipt_path, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, account_id, category_id, t_type, amount, description, merchant,
          transaction_date, is_recurring, recurring_period, receipt_path, notes))
    conn.commit()
    tx_id = c.lastrowid

    # Update account balance
    if account_id:
        c.execute("SELECT balance FROM Financial_Accounts WHERE id = ?", (account_id,))
        row = c.fetchone()
        if row:
            current_balance = row[0] or 0.0
            if t_type == 'income':
                new_balance = current_balance + amount
            elif t_type == 'expense':
                new_balance = current_balance - amount
            else:
                new_balance = current_balance
            c.execute("UPDATE Financial_Accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
            conn.commit()

    conn.close()
    return tx_id

def get_transactions(user_id, limit=50, offset=0, account_id=None, category_id=None,
                     t_type=None, start_date=None, end_date=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = """
        SELECT t.id, t.account_id, t.category_id, t.type, t.amount, t.description,
               t.merchant, t.transaction_date, t.is_recurring, t.recurring_period,
               t.receipt_path, t.notes,
               a.name as account_name, c.name as category_name, c.color as category_color
        FROM Transactions t
        LEFT JOIN Financial_Accounts a ON t.account_id = a.id
        LEFT JOIN Categories c ON t.category_id = c.id
        WHERE t.user_id = ?
    """
    params = [user_id]
    if account_id:
        query += " AND t.account_id = ?"
        params.append(account_id)
    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)
    if t_type:
        query += " AND t.type = ?"
        params.append(t_type)
    if start_date:
        query += " AND t.transaction_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND t.transaction_date <= ?"
        params.append(end_date)
    query += " ORDER BY t.transaction_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    transactions = []
    for row in rows:
        transactions.append({
            "id": row[0], "account_id": row[1], "category_id": row[2], "type": row[3],
            "amount": row[4], "description": row[5], "merchant": row[6],
            "transaction_date": row[7], "is_recurring": bool(row[8]),
            "recurring_period": row[9], "receipt_path": row[10], "notes": row[11],
            "account_name": row[12], "category_name": row[13], "category_color": row[14]
        })
    return transactions

def get_transaction_summary(user_id, period='month'):
    """Get income vs expense summary for a period."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    if period == 'week':
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
    elif period == 'month':
        start = now.replace(day=1, hour=0, minute=0, second=0)
    elif period == 'year':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0)

    c.execute("""
        SELECT type, SUM(amount) FROM Transactions
        WHERE user_id = ? AND transaction_date >= ?
        GROUP BY type
    """, (user_id, start.isoformat()))
    rows = c.fetchall()
    conn.close()
    summary = {"income": 0.0, "expense": 0.0, "net": 0.0}
    for row in rows:
        if row[0] == 'income':
            summary["income"] = row[1] or 0.0
        elif row[0] == 'expense':
            summary["expense"] = row[1] or 0.0
    summary["net"] = summary["income"] - summary["expense"]
    return summary

# ============================================================
# BUDGET MANAGEMENT
# ============================================================

def create_budget(user_id, category_id, amount, period='monthly', start_date=None,
                  end_date=None, alert_threshold=80.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if start_date is None:
        start_date = datetime.now().isoformat()
    c.execute("""
        INSERT INTO Budgets (user_id, category_id, amount, period, start_date, end_date, alert_threshold)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, category_id, amount, period, start_date, end_date, alert_threshold))
    conn.commit()
    budget_id = c.lastrowid
    conn.close()
    return budget_id

def get_budgets(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT b.id, b.category_id, b.amount, b.period, b.start_date, b.end_date,
               b.alert_threshold, b.is_active, c.name as category_name, c.color as category_color
        FROM Budgets b
        LEFT JOIN Categories c ON b.category_id = c.id
        WHERE b.user_id = ? AND b.is_active = 1
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    budgets = []
    for row in rows:
        budgets.append({
            "id": row[0], "category_id": row[1], "amount": row[2], "period": row[3],
            "start_date": row[4], "end_date": row[5], "alert_threshold": row[6],
            "is_active": bool(row[7]), "category_name": row[8], "category_color": row[9]
        })
    return budgets

def get_budget_usage(user_id, budget_id):
    """Calculate how much of a budget has been used."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT category_id, amount, start_date FROM Budgets WHERE id = ? AND user_id = ?",
              (budget_id, user_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    category_id, amount, start_date = row
    c.execute("""
        SELECT SUM(amount) FROM Transactions
        WHERE user_id = ? AND category_id = ? AND type = 'expense' AND transaction_date >= ?
    """, (user_id, category_id, start_date))
    spent = c.fetchone()[0] or 0.0
    conn.close()
    percentage = (spent / amount * 100) if amount > 0 else 0
    return {"spent": spent, "budget": amount, "remaining": amount - spent,
            "percentage": round(percentage, 2)}

# ============================================================
# SAVINGS GOALS
# ============================================================

def create_savings_goal(user_id, name, target_amount, deadline=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO Savings_Goals (user_id, name, target_amount, deadline)
        VALUES (?, ?, ?, ?)
    """, (user_id, name, target_amount, deadline))
    conn.commit()
    goal_id = c.lastrowid
    conn.close()
    return goal_id

def get_savings_goals(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, target_amount, current_amount, deadline, is_active, created_at
        FROM Savings_Goals WHERE user_id = ? AND is_active = 1
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    goals = []
    for row in rows:
        percentage = (row[3] / row[2] * 100) if row[2] > 0 else 0
        goals.append({
            "id": row[0], "name": row[1], "target_amount": row[2],
            "current_amount": row[3], "deadline": row[4], "is_active": bool(row[5]),
            "created_at": row[6], "percentage": round(percentage, 2)
        })
    return goals

def update_savings_goal(goal_id, user_id, amount_to_add):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT current_amount FROM Savings_Goals WHERE id = ? AND user_id = ?",
              (goal_id, user_id))
    row = c.fetchone()
    if row:
        new_amount = row[0] + amount_to_add
        c.execute("UPDATE Savings_Goals SET current_amount = ? WHERE id = ?",
                  (new_amount, goal_id))
        conn.commit()
    conn.close()

# ============================================================
# STATEMENT PARSING (FNB, Standard Bank, Capitec)
# ============================================================

def parse_bank_statement(user_id, account_id, statement_text, bank_type='fnb'):
    """
    Parse bank statement text and extract transactions.
    Supports: 'fnb', 'standard_bank', 'capitec'
    """
    transactions = []
    lines = statement_text.split('\n')

    if bank_type.lower() == 'fnb':
        for line in lines:
            # Try to match transaction lines with amounts

# KHULA_APPEND_MARKER_7a3f9e2d
