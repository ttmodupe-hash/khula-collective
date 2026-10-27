"""Safely recover Khula administrator access through verified Railway ownership.

All tests use fake email, one-time test challenge and a temporary local SQLite
database. They never touch the production service, member records or secrets.
"""
import hashlib
import os
import secrets
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import khula_config as config
from khula_owner_access import activate_owner_admin, owner_setup_available
from khula_security import authenticate_user, hash_password
from khula_applications import list_membership_requests


class RailwayOwnerActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "owner.db")
        self.old_path = config.DB_PATH
        config.DB_PATH = self.db
        config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.executemany(
                "INSERT INTO Users "
                "(user_id,username,full_name,email,password_hash,role,is_active) "
                "VALUES (?,?,?,?,?,?,?)",
                [
                    (1, "existingadmin", "Prior Admin", "prior@example.invalid",
                     hash_password("PriorAdminStrongPassword2026!"), "admin", 1),
                    (2, "memberone", "Example Member", "member@example.invalid",
                     hash_password("MemberStrongPassword2026!"), "member", 1),
                ],
            )
        self.token = secrets.token_urlsafe(32)
        self.email = "owner@example.invalid"
        self.now = datetime.now(timezone.utc)
        self.env = {
            "KHULA_OWNER_SETUP_EMAIL": self.email,
            "KHULA_OWNER_SETUP_TOKEN_SHA256": hashlib.sha256(
                self.token.encode("ascii")
            ).hexdigest(),
            "KHULA_OWNER_SETUP_EXPIRES_UTC": (
                self.now + timedelta(minutes=50)
            ).isoformat(),
            "KHULA_PRODUCTION": "1",
            "KHULA_DEMO_MODE": "0",
        }

    def tearDown(self):
        config.DB_PATH = self.old_path
        self.temp.cleanup()

    def claim(self, *, token=None, email=None, username="khula_owner",
              password="OwnerPrivateStrongPassword2026!",
              now=None, env=None, approved=True):
        return activate_owner_admin(
            self.db, self.email if email is None else email,
            username, self.token if token is None else token, password,
            approved=approved, env=self.env if env is None else env,
            now=self.now if now is None else now,
        )

    def test_valid_private_owner_claim_grants_approver_role_only_once(self):
        self.assertTrue(owner_setup_available(env=self.env, now=self.now))
        uid = self.claim()
        with sqlite3.connect(self.db) as conn:
            account = conn.execute(
                "SELECT username,email,password_hash,role,is_active,"
                "must_change_password FROM Users WHERE user_id=?", (uid,)
            ).fetchone()
            audit = conn.execute(
                "SELECT admin_user_id,action_type,details FROM Admin_Actions "
                "WHERE action_type='owner_admin_activated'",
            ).fetchall()
            claim = conn.execute(
                "SELECT challenge_sha256,owner_user_id FROM Owner_Admin_Activations"
            ).fetchone()
            preexisting = conn.execute(
                "SELECT username,role,is_active FROM Users WHERE user_id IN (1,2) "
                "ORDER BY user_id",
            ).fetchall()
        self.assertEqual(account[:2], ("khula_owner", self.email))
        self.assertEqual(account[3:], ("admin", 1, 0))
        self.assertTrue(account[2].startswith("$2"))
        self.assertNotIn("OwnerPrivateStrongPassword2026!", repr(account))
        self.assertEqual(claim[0], self.env["KHULA_OWNER_SETUP_TOKEN_SHA256"])
        self.assertEqual(claim[1], uid)
        self.assertNotIn(self.token, repr(claim))
        self.assertEqual(audit[0][:2], (uid, "owner_admin_activated"))
        self.assertNotIn(self.token, repr(audit))
        self.assertEqual(
            preexisting, [("existingadmin", "admin", 1),
                          ("memberone", "member", 1)]
        )
        self.assertEqual(
            authenticate_user(self.db, "khula_owner",
                              "OwnerPrivateStrongPassword2026!")[0],
            uid,
        )
        # All authorisation checks for the actual Membership Approvals queue
        # recognise the independently activated, active admin.
        self.assertEqual(list_membership_requests(self.db, uid), [])
        with self.assertRaises(ValueError):
            self.claim(username="another_admin")

    def test_owner_claim_denies_wrong_email_and_weak_password(self):
        for email in ("attacker@example.invalid", "bad", "owner@different.invalid"):
            with self.assertRaises(ValueError):
                self.claim(email=email)
        for password in ("weak", "A" * 90):
            with self.assertRaises(ValueError):
                self.claim(password=password)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 2
            )

    def test_random_or_malformed_token_does_not_change_any_access(self):
        for token in ("", "bad-token", secrets.token_urlsafe(32)):
            with self.assertRaises(ValueError):
                self.claim(token=token)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 2
            )

    def test_disabled_expired_or_unsafe_lifetime_refuses_activation(self):
        conditions = (
            {**self.env, "KHULA_OWNER_SETUP_DISABLED": "1"},
            {**self.env, "KHULA_OWNER_SETUP_EXPIRES_UTC":
             (self.now-timedelta(minutes=1)).isoformat()},
            {**self.env, "KHULA_OWNER_SETUP_EXPIRES_UTC":
             (self.now+timedelta(days=2)).isoformat()},
            {**self.env, "KHULA_OWNER_SETUP_TOKEN_SHA256": "garbage"},
            {**self.env, "KHULA_OWNER_SETUP_EMAIL": ""},
            {**self.env, "KHULA_OWNER_SETUP_EXPIRES_UTC": "invalid"},
        )
        for changed in conditions:
            self.assertFalse(owner_setup_available(env=changed, now=self.now))
            with self.assertRaises(ValueError):
                self.claim(env=changed)
        self.assertFalse(
            owner_setup_available(env=self.env, now=self.now+timedelta(days=1))
        )
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 2)

    def test_reject_owner_self_attestation_missing_and_username_collision(self):
        with self.assertRaises(ValueError):
            self.claim(approved=False)
        with self.assertRaises(ValueError):
            self.claim(username="memberone")
        with self.assertRaises(ValueError):
            self.claim(username="existingadmin")
        with self.assertRaises(ValueError):
            self.claim(username="1badname")
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0], 2)

    def test_owner_form_is_secret_free_and_only_on_private_query_route(self):
        source = (Path(__file__).resolve().parents[1] /
                  "khula_owner_access.py").read_text(encoding="utf-8")
        self.assertIn('st.query_params.get("owner_setup")', source)
        self.assertIn("type=\"password\"", source)
        self.assertIn("hmac.compare_digest", source)
        self.assertIn("BEGIN IMMEDIATE", source)
        self.assertIn("Owner_Admin_Activations", source)
        self.assertNotIn("admin123", source)
        self.assertNotIn("password1", source)

    def test_claim_does_not_override_closed_member_onboarding(self):
        self.claim()
        from khula_compliance import onboarding_gate_status
        with patch.dict(os.environ, {"KHULA_PRODUCTION": "1",
                                     "KHULA_PRIVACY_NOTICE_APPROVED": "0"}, clear=True):
            self.assertFalse(onboarding_gate_status()["ready"])


if __name__ == "__main__":
    unittest.main()
