"""READ-ONLY schema/count inventory for a privately provided old Khula DB.

Usage: python scripts/legacy_inventory.py /secure/offline/khula_collective.db
Does not output names, IDs, references, balances, password hashes or other PII.
Does NOT migrate or mutate any record.
"""
import argparse
import json
import sqlite3
from pathlib import Path

TABLES = (
    "Users", "Monthly_Contributions", "Transactions", "Investment_Goals",
    "GlobalAccountSync", "WhatsApp_Notifications", "Investment_Suggestions",
    "Admin_Actions", "Constitution",
)


def inspect_legacy_database(path):
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("Expected a regular SQLite file.")
    # SQLite URI read-only opens must never create an absent database.
    uri = path.as_uri() + "?mode=ro"
    output = {"tables": {}}
    with sqlite3.connect(uri, uri=True) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for name in TABLES:
            if name not in tables:
                output["tables"][name] = {"exists": False}
                continue
            # Name is from the constant allowlist; never interpolation of user input.
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({name})")]
            count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            output["tables"][name] = {
                "exists": True, "row_count": count, "column_names": columns
            }
    output["warning"] = (
        "Inventory only. All financial entries, consent, credentials and bank "
        "balances still require independent, controlled migration and reconciliation."
    )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy_sqlite_path", help="Local legacy database file; never commit")
    args = parser.parse_args()
    print(json.dumps(inspect_legacy_database(args.legacy_sqlite_path), indent=2))
