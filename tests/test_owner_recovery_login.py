"""Synthetic owner recovery and email/username authentication acceptance."""
import hashlib
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import khula_config as config
from khula_owner_access import activate_owner_admin, setup_or_recover_owner_admin
from khula_security import authenticate_user, hash_password, member_auth_state
from khula_applications import list_membership_requests


class OwnerRecoveryLoginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "synthetic.db")
        with patch.object(config, "DB_PATH", self.db), patch.dict(os.environ, {
            "KHULA_DEMO_MODE": "0", "KHULA_BOOTSTRAP_ADMIN_USER": "",
            "KHULA_BOOTSTRAP_ADMIN_PASSWORD": "",
        }):
            config.init_database()
        self.email = "owner@example.invalid"
        self.old_password = "OldSyntheticOwnerPass2026!"
        self.new_password = "NewSyntheticOwnerPass2026!"
        self.now = datetime.now(timezone.utc)
        self.fresh_code()

    def tearDown(self):
        self.tmp.cleanup()

    def fresh_code(self):
        self.token = secrets.token_urlsafe(32)
        self.env = {
            "KHULA_OWNER_SETUP_EMAIL": self.email,
            "KHULA_OWNER_SETUP_TOKEN_SHA256": hashlib.sha256(self.token.encode()).hexdigest(),
            "KHULA_OWNER_SETUP_EXPIRES_UTC": (self.now + timedelta(minutes=50)).isoformat(),
        }

    def activate(self):
        return activate_owner_admin(self.db, self.email, "real_owner", self.token,
                                    self.old_password, approved=True, env=self.env, now=self.now)

    def recover(self, **kwargs):
        options = dict(approved=True, env=self.env, now=self.now)
        options.update(kwargs)
        return setup_or_recover_owner_admin(
            self.db, self.email, "ignored_new_name", self.token, self.new_password, **options
        )

    def test_fresh_owner_code_resets_existing_owner_and_preserves_identity(self):
        uid = self.activate()
        for _ in range(8):
            self.assertIsNone(authenticate_user(self.db, "real_owner", "wrong"))
        self.assertIsNone(authenticate_user(self.db, self.email, self.old_password))
        before = member_auth_state(self.db, uid)
        self.fresh_code()
        result = self.recover()
        self.assertEqual(result, {"user_id": uid, "username": "real_owner", "action": "recovered"})
        self.assertEqual(member_auth_state(self.db, uid)[3], before[3] + 1)
        self.assertIsNone(authenticate_user(self.db, "real_owner", self.old_password))
        self.assertEqual(authenticate_user(self.db, self.email, self.new_password)[0], uid)
        self.assertEqual(list_membership_requests(self.db, uid), [])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Owner_Admin_Recovery_Uses").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Admin_Actions WHERE action_type='owner_admin_password_recovered'").fetchone()[0], 1)

    def test_consumed_activation_and_recovery_codes_cannot_be_replayed(self):
        self.activate()
        with self.assertRaises(ValueError):
            self.recover()
        self.fresh_code()
        self.recover()
        with self.assertRaises(ValueError):
            self.recover()
        with self.assertRaises(ValueError):
            self.activate()

    def test_wrong_expired_disabled_or_unconfirmed_code_cannot_reset_password(self):
        uid = self.activate()
        self.fresh_code()
        conditions = [
            {"approved": False},
            {"env": {**self.env, "KHULA_OWNER_SETUP_TOKEN_SHA256": "0" * 64}},
            {"env": {**self.env, "KHULA_OWNER_SETUP_EMAIL": "different@example.invalid"}},
            {"env": {**self.env, "KHULA_OWNER_SETUP_DISABLED": "1"}},
            {"now": self.now + timedelta(hours=2)},
        ]
        for overrides in conditions:
            with self.assertRaises(ValueError):
                self.recover(**overrides)
        self.assertEqual(member_auth_state(self.db, uid)[3], 0)
        self.assertEqual(authenticate_user(self.db, "real_owner", self.old_password)[0], uid)

    def test_inactive_or_demoted_owner_is_never_reactivated(self):
        uid = self.activate()
        self.fresh_code()
        for role, active in (("admin", 0), ("member", 1)):
            with sqlite3.connect(self.db) as conn:
                conn.execute("UPDATE Users SET role=?,is_active=? WHERE user_id=?", (role, active, uid))
            with self.assertRaises(ValueError):
                self.recover()
            self.assertEqual(member_auth_state(self.db, uid)[:2], (role, active))

    def test_shared_email_or_username_cannot_claim_unproven_admin(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO Users(username,password_hash,full_name,email,role,is_active) VALUES(?,?,?,?,?,?)",
                         ("ignored_new_name", hash_password(self.old_password), "Fixture", self.email, "admin", 1))
        with self.assertRaises(ValueError):
            self.recover()
        self.assertEqual(authenticate_user(self.db, "ignored_new_name", self.old_password)[1], "ignored_new_name")
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 1)

    def test_first_time_setup_still_works_through_combined_form(self):
        result = self.recover()
        self.assertEqual(result["action"], "activated")
        self.assertEqual(authenticate_user(self.db, self.email, self.new_password)[0], result["user_id"])

    def test_fresh_setup_cannot_create_duplicate_owner_accounts(self):
        self.activate()
        self.fresh_code()
        with self.assertRaises(ValueError):
            activate_owner_admin(self.db, self.email, "second_owner", self.token,
                                 self.new_password, approved=True, env=self.env, now=self.now)

    def test_multiple_proven_owners_fail_closed(self):
        self.activate()
        with sqlite3.connect(self.db) as conn:
            cur = conn.execute("INSERT INTO Users(username,password_hash,full_name,email,role,is_active) VALUES(?,?,?,?,?,?)",
                               ("old_owner", hash_password(self.old_password), "Fixture", self.email, "admin", 1))
            conn.execute("INSERT INTO Owner_Admin_Activations(challenge_sha256,owner_user_id,activated_at) VALUES(?,?,?)",
                         ("1" * 64, cur.lastrowid, self.now.isoformat()))
        self.fresh_code()
        with self.assertRaises(ValueError):
            self.recover()

    def test_concurrent_recovery_consumes_the_code_once(self):
        from concurrent.futures import ThreadPoolExecutor
        self.activate()
        self.fresh_code()
        def attempt():
            try:
                return self.recover()["action"]
            except ValueError:
                return "denied"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: attempt(), range(2)))
        self.assertCountEqual(outcomes, ["recovered", "denied"])

    def test_email_and_username_share_password_attempt_limit(self):
        self.activate()
        for n in range(8):
            identifier = self.email.upper() if n % 2 else " REAL_OWNER "
            self.assertIsNone(authenticate_user(self.db, identifier, "wrong"))
        self.assertIsNone(authenticate_user(self.db, self.email, self.old_password))
        self.assertIsNone(authenticate_user(self.db, "real_owner", self.old_password))

    def test_duplicate_email_is_ambiguous_even_when_one_account_is_inactive(self):
        uid = self.activate()
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO Users(username,password_hash,full_name,email,role,is_active) VALUES(?,?,?,?,?,?)",
                         ("pending_member", hash_password(self.new_password), "Fixture", self.email, "member", 0))
        self.assertIsNone(authenticate_user(self.db, self.email, self.old_password))
        self.assertEqual(authenticate_user(self.db, "real_owner", self.old_password)[0], uid)
        self.assertIsNone(authenticate_user(self.db, "pending_member", self.new_password))

    def test_owner_recovery_form_clears_secrets_and_prefills_actual_username(self):
        from streamlit.testing.v1 import AppTest
        uid = self.activate()
        self.fresh_code()
        script = """
import streamlit as st
from khula_owner_access import render_owner_setup
st.query_params['owner_setup'] = '1'
if st.session_state.get('_khula_owner_setup_complete'):
    st.success(st.session_state['_khula_owner_setup_complete'])
else:
    render_owner_setup()
"""
        with patch.object(config, "DB_PATH", self.db), patch.dict(os.environ, self.env):
            app = AppTest.from_string(script).run()
            app.text_input(key="owner_verified_email").set_value(self.email)
            app.text_input(key="owner_private_activation_code").set_value(self.token)
            app.text_input(key="owner_admin_password").set_value(self.new_password)
            app.text_input(key="owner_admin_password_confirmation").set_value(self.new_password)
            app.checkbox(key="owner_admin_confirm").check()
            app.button[0].click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.success[0].value, "real_owner")
            self.assertEqual(app.session_state['_khula_owner_setup_complete'], "real_owner")
            for key in ("owner_private_activation_code", "owner_admin_password", "owner_admin_password_confirmation"):
                self.assertNotIn(key, app.session_state)
        self.assertEqual(authenticate_user(self.db, "real_owner", self.new_password)[0], uid)


if __name__ == "__main__":
    unittest.main()
