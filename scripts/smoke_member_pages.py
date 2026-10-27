"""Integration smoke for actual member/admin Streamlit navigation.

Runs in a separate process with a temporary SQLite ledger configured BEFORE
importing app modules, so production paths/default database arguments cannot
be accidentally used. No real member identities, secrets or banking data.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app.py"

MEMBER_PAGES = (
    "dashboard", "payments", "voice", "constitution", "goals",
    "leaderboard", "directory", "notifications", "reports",
    "ai_advisor", "global_markets", "profile", "features", "whatsapp",
    "fnb_sync", "id_verify",
)
ADMIN_PAGES = (
    "admin", "membership_approvals", "launch_center",
    "reconciliation", "invites", "bank_access", "compliance", "recoveries",
)


def render_page(uid, role, page):
    app = AppTest.from_file(str(SCRIPT), default_timeout=35).run()
    if app.exception:
        raise AssertionError(f"Public landing failed before {role}/{page}: {app.exception}")
    app.session_state["authenticated"] = True
    app.session_state["logged_in"] = True
    app.session_state["user_id"] = uid
    app.session_state["username"] = role + "_example"
    app.session_state["full_name"] = role.title() + " Test Member"
    app.session_state["role"] = role
    app.session_state["theme"] = "dark"
    app.session_state["nav_page"] = page
    app.session_state["_auth_epoch"] = 0
    app.run()
    exceptions = list(app.exception)
    if exceptions:
        raise AssertionError(f"{role}/{page} raised: {exceptions!r}")
    if not app.session_state["authenticated"]:
        raise AssertionError(f"{role}/{page} unexpectedly signed out an active test account")
    if app.session_state["nav_page"] != page:
        raise AssertionError(f"{role}/{page} redirected instead of rendering")
    print(f"PASS {role}/{page}",flush=True)


def run():
    with tempfile.TemporaryDirectory(prefix="khula-route-smoke-") as tmp:
        db = str(Path(tmp) / "temporary-test-ledger.db")
        env = {
            "KHULA_DEMO_MODE": "0", "KHULA_PRODUCTION": "0",
            "RAILWAY_ENVIRONMENT_NAME": "production",
            "KHULA_DB_PATH": db,
            "KHULA_BOOTSTRAP_ADMIN_USER": "",
            "KHULA_BOOTSTRAP_ADMIN_PASSWORD": "",
            "KHULA_ENABLE_ID_PRECHECK": "0",
            "KHULA_ENABLE_PRIVATE_STATEMENT_IMPORT": "0",
            "KHULA_AI_PROVIDER": "none",
            "KHULA_MARKET_DATA_LICENSE_APPROVED": "0",
            "KHULA_PRIVACY_NOTICE_APPROVED": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            # Import *after* setting KHULA_DB_PATH; some production helpers
            # use default DB_PATH=... bound at import.
            import khula_config
            import khula_security
            khula_config.init_database()
            with sqlite3.connect(db) as conn:
                conn.executemany(
                    "INSERT INTO Users "
                    "(user_id,username,full_name,email,password_hash,role,is_active,auth_epoch) "
                    "VALUES (?,?,?,?,?,?,1,0)",
                    [
                        (1, "admin_example", "Club Admin Test", "admin@example.invalid",
                         khula_security.hash_password("Admin-Secure-Test-Only2026!"), "admin"),
                        (2, "member_example", "Club Member Test", "member@example.invalid",
                         khula_security.hash_password("Member-Secure-Test-Only2026!"), "member"),
                    ],
                )
            import khula_sarb
            mock_bundle = {
                "data": [], "retrieved_at": "2026-10-27T00:00:00+00:00",
                "source_url": khula_sarb.API_URL,
            }
            with ExitStack() as stack:
                stack.enter_context(
                    patch("khula_sarb.fetch_sarb_indicators",
                          return_value=mock_bundle)
                )
                for page in MEMBER_PAGES:
                    render_page(2, "member", page)
                for page in ADMIN_PAGES:
                    render_page(1, "admin", page)
        print(
            f"PASSED {len(MEMBER_PAGES) + len(ADMIN_PAGES)} "
            "isolated Streamlit member/admin route checks",
            flush=True,
        )


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"Khula navigation smoke FAILED: {exc!r}",file=sys.stderr,flush=True)
        raise
