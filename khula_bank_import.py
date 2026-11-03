"""Admin-only import of real bank-exported CSV evidence for club contributions.

This is NOT an authenticated bank connection. It requires administrator
provenance review. Raw statements are never retained; only masked references,
amounts, dates and keyed, non-reversible row digests are stored.
"""
import csv
import hashlib
import hmac
import io
import os
import re
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from khula_advisory_core import zar


class BankImportError(ValueError):
    pass


def _key():
    value = os.environ.get("KHULA_BANK_IMPORT_HMAC_KEY", "")
    if len(value) < 32:
        raise BankImportError("Bank-statement import has not been enabled by the administrator.")
    return value.encode("utf-8")


def _normalize_header(raw):
    return re.sub(r"[^a-z0-9]", "", str(raw).strip().lower())


def _parse_date(raw):
    value = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%Y/%m/%d"):
        try:
            dated = datetime.strptime(value, fmt).date()
            if dated.year < 2020 or dated > date.today():
                raise BankImportError("An imported bank transaction has an invalid date.")
            return dated.isoformat()
        except ValueError:
            continue
    raise BankImportError("Unsupported bank date format; use YYYY-MM-DD or DD/MM/YYYY.")


def _parse_money(raw):
    value = str(raw).strip().replace(" ", "").replace(",", "").upper()
    value = value.replace("R", "")
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    try:
        amount = zar(value)
    except ValueError as exc:
        raise BankImportError("Statement contains an invalid amount.") from exc
    if abs(amount) > Decimal("50000000.00"):
        raise BankImportError("Transaction amount is outside the supported bounds.")
    return amount


def parse_bank_csv(blob):
    """Accept a narrowly defined, reviewable CSV layout, never guess columns."""
    if not isinstance(blob, bytes) or not (1 <= len(blob) <= 2 * 1024 * 1024):
        raise BankImportError("CSV must be nonempty and at most 2 MB.")
    try:
        text = blob.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BankImportError("Please export UTF-8 CSV from the bank.") from exc
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if not reader.fieldnames or len(reader.fieldnames) > 35:
            raise BankImportError("Statement is missing a supported header.")
        names = {_normalize_header(x): x for x in reader.fieldnames if x}
        columns = {
            "date": next((names[k] for k in ("transactiondate", "postingdate", "date") if k in names), None),
            "amount": next((names[k] for k in ("amount", "transactionamount") if k in names), None),
            "credit": next((names[k] for k in ("credit", "credits") if k in names), None),
            "debit": next((names[k] for k in ("debit", "debits") if k in names), None),
            "reference": next((names[k] for k in ("reference", "paymentreference", "bankreference") if k in names), None),
            "description": next((names[k] for k in ("description", "narrative", "details") if k in names), None),
        }
        if not columns["date"] or not (columns["amount"] or columns["credit"]):
            raise BankImportError("CSV needs Date and Amount, or Date/Credit/Debit columns.")
        parsed = []
        for row in reader:
            if len(parsed) >= 1000:
                raise BankImportError("Upload at most 1,000 transactions per file.")
            if not isinstance(row, dict) or None in row:
                raise BankImportError("CSV contains extra/malformed columns.")
            if not any(str(v or "").strip() for v in row.values()):
                continue
            tx_date = _parse_date(row[columns["date"]])
            if columns["amount"]:
                amount = _parse_money(row[columns["amount"]])
            else:
                credit = _parse_money(row.get(columns["credit"], "") or "0")
                debit = _parse_money(row.get(columns["debit"], "") or "0") if columns["debit"] else Decimal(0)
                amount = credit - abs(debit)
            if amount == 0:
                continue
            ref = str(row.get(columns["reference"], "") or "").strip()[:160] if columns["reference"] else ""
            desc = str(row.get(columns["description"], "") or "").strip()[:200] if columns["description"] else ""
            if not ref and not desc:
                raise BankImportError("Statement rows must contain a reference or description.")
            parsed.append({"date": tx_date, "amount": amount, "reference": ref, "description": desc})
        if not parsed:
            raise BankImportError("No valid non-zero bank transactions found.")
        return parsed
    except csv.Error as exc:
        raise BankImportError("Bank CSV cannot be parsed.") from exc


def _ensure_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS Bank_Statement_Imports (
        import_id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_digest TEXT UNIQUE NOT NULL,
        row_count INTEGER NOT NULL,
        imported_by INTEGER NOT NULL,
        imported_at TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'manual_admin_export'
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS Bank_Statement_Rows (
        row_id INTEGER PRIMARY KEY AUTOINCREMENT,
        import_id INTEGER NOT NULL,
        row_digest TEXT UNIQUE NOT NULL,
        tx_date TEXT NOT NULL,
        amount_zar REAL NOT NULL,
        reference_mask TEXT,
        assigned_claim_id INTEGER UNIQUE,
        FOREIGN KEY(import_id) REFERENCES Bank_Statement_Imports(import_id),
        FOREIGN KEY(assigned_claim_id) REFERENCES Payment_Claims(claim_id)
    )""")


def import_club_statement(db_path, admin_id, blob, *, source_checked):
    """The administrator must have inspected the actual club bank export."""
    if not source_checked:
        raise BankImportError("Confirm the source is the real club bank export.")
    secret = _key()
    rows = parse_bank_csv(blob)
    digest_file = hmac.new(secret, blob, hashlib.sha256).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        admin = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND role='admin' AND is_active=1",
            (admin_id,),
        ).fetchone()
        if not admin:
            raise PermissionError("Only administrators can import club bank evidence.")
        _ensure_schema(conn)
        if conn.execute("SELECT 1 FROM Bank_Statement_Imports WHERE file_digest=?", (digest_file,)).fetchone():
            raise BankImportError("This bank file has already been imported.")
        cursor = conn.execute(
            "INSERT INTO Bank_Statement_Imports(file_digest,row_count,imported_by,imported_at) "
            "VALUES (?,?,?,?)", (digest_file, len(rows), admin_id, now),
        )
        inserted, duplicates = 0, 0
        for row in rows:
            payload = (row["date"] + "|" + str(row["amount"]) + "|" + row["reference"] +
                       "|" + row["description"]).encode("utf-8")
            fingerprint = hmac.new(secret, payload, hashlib.sha256).hexdigest()
            mask = ("••••" + row["reference"][-4:]) if row["reference"] else "description-only"
            try:
                conn.execute(
                    "INSERT INTO Bank_Statement_Rows "
                    "(import_id,row_digest,tx_date,amount_zar,reference_mask) VALUES (?,?,?,?,?)",
                    (cursor.lastrowid, fingerprint, row["date"], float(row["amount"]), mask),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                duplicates += 1
        conn.execute(
            "INSERT INTO Admin_Actions(admin_user_id,action_type,details) VALUES (?,?,?)",
            (admin_id, "bank_statement_imported",
             f"batch={cursor.lastrowid}; unique_rows={inserted}; repeated_rows={duplicates}"),
        )
    return {"new_rows": inserted, "duplicates_skipped": duplicates,
            "source": "administrator-provided CSV (not API-verified)", "imported_at": now}


def unallocated_bank_credits(db_path, admin_id, amount=None):
    """Offer only unassigned positive bank rows for manual matching."""
    with sqlite3.connect(db_path) as conn:
        admin = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND role='admin' AND is_active=1",
            (admin_id,),
        ).fetchone()
        if not admin:
            raise PermissionError("Only an administrator may view bank evidence.")
        _ensure_schema(conn)
        sql = (
            "SELECT row_id,tx_date,amount_zar,reference_mask "
            "FROM Bank_Statement_Rows WHERE assigned_claim_id IS NULL AND amount_zar>0"
        )
        params = []
        if amount is not None:
            sql += " AND ABS(amount_zar-?)<0.005"
            params.append(float(zar(amount)))
        sql += " ORDER BY tx_date DESC, row_id DESC LIMIT 150"
        return conn.execute(sql, params).fetchall()


def attach_credit_to_claim(conn, claim_id, evidence_id, expected_amount):
    """Atomic when called inside review_payment_claim's write transaction."""
    _ensure_schema(conn)
    row = conn.execute(
        "SELECT amount_zar,assigned_claim_id FROM Bank_Statement_Rows WHERE row_id=? AND amount_zar>0",
        (evidence_id,),
    ).fetchone()
    if not row or row[1] is not None or zar(row[0]) != zar(expected_amount):
        raise BankImportError("Select one unallocated incoming bank transaction matching the claim amount.")
    changed = conn.execute(
        "UPDATE Bank_Statement_Rows SET assigned_claim_id=? "
        "WHERE row_id=? AND assigned_claim_id IS NULL",
        (claim_id, evidence_id),
    )
    if changed.rowcount != 1:
        raise BankImportError("That bank transaction was already allocated.")
