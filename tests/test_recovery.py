"""Security properties of production member password recovery."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import khula_config
from khula_recovery import (
    MAX_FAILED_RECOVERIES,
    issue_member_recovery,
    redeem_member_recovery,
)
from khula_security import authenticate_user, hash_password


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "khula.db")
        self.oldpath = khula_config.DB_PATH
        khula_config.DB_PATH = self.db
        self.environment = patch.dict(os.environ, {"KHULA_DEMO_MODE": "0"})
        self.environment.start()
        khula_config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO Users (user_id,username,password_hash,full_name,email,role,is_active) "
                "VALUES (1,'clubadmin',?,'Club Admin','admin@example.invalid','admin',1)",
                (hash_password("VeryStrongAdminPassword2026"),),
            )
            conn.execute(
                "INSERT INTO Users (user_id,username,password_hash,full_name,email,role,is_active) "
                "VALUES (2,'memberone',?,'Member One','member@example.invalid','member',1)",
                (hash_password("VeryStrongMemberPassword2026"),),
            )

    def tearDown(self):
        khula_config.DB_PATH = self.oldpath
        self.environment.stop()
        self.tmp.cleanup()

    def test_admin_issues_one_time_code_and_member_changes_password(self):
        token = issue_member_recovery(self.db, 1, 2)
        self.assertTrue(len(token) >= 35)
        with sqlite3.connect(self.db) as conn:
            saved = conn.execute("SELECT token_hash FROM Member_Recovery_Tokens").fetchone()[0]
        self.assertNotEqual(saved, token)
        self.assertIsNotNone(authenticate_user(self.db, "memberone", "VeryStrongMemberPassword2026"))
        self.assertTrue(redeem_member_recovery(
            self.db, "memberone", "member@example.invalid", token,
            "NewMemberPassword2026!!",
        ))
        self.assertIsNone(authenticate_user(self.db, "memberone", "VeryStrongMemberPassword2026"))
        self.assertIsNotNone(authenticate_user(self.db, "memberone", "NewMemberPassword2026!!"))
        with sqlite3.connect(self.db) as conn:
            epoch = conn.execute("SELECT auth_epoch FROM Users WHERE user_id=2").fetchone()[0]
        self.assertEqual(epoch, 1)
        with self.assertRaises(ValueError):
            redeem_member_recovery(
                self.db, "memberone", "member@example.invalid", token,
                "YetAnotherStrongPassword2026!",
            )

    def test_reissuing_revokes_older_code(self):
        first = issue_member_recovery(self.db, 1, 2)
        second = issue_member_recovery(self.db, 1, 2)
        self.assertNotEqual(first, second)
        with self.assertRaises(ValueError):
            redeem_member_recovery(
                self.db, "memberone", "member@example.invalid", first,
                "YetAnotherStrongPassword2026!",
            )
        self.assertTrue(redeem_member_recovery(
            self.db, "memberone", "member@example.invalid", second,
            "YetAnotherStrongPassword2026!",
        ))

    def test_admin_cannot_be_reset_via_member_flow(self):
        with self.assertRaises(ValueError):
            issue_member_recovery(self.db, 1, 1)
        with self.assertRaises(PermissionError):
            issue_member_recovery(self.db, 2, 2)

    def test_expired_code_rejected_without_consumption(self):
        token = issue_member_recovery(self.db, 1, 2)
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "UPDATE Member_Recovery_Tokens SET expires_at=?",
                ("2020-01-01T00:00:00+00:00",),
            )
        with self.assertRaises(ValueError):
            redeem_member_recovery(
                self.db, "memberone", "member@example.invalid", token,
                "YetAnotherStrongPassword2026!",
            )

    def test_failed_attempts_are_committed_and_throttled(self):
        token = issue_member_recovery(self.db, 1, 2)
        for i in range(MAX_FAILED_RECOVERIES):
            with self.assertRaises(ValueError):
                redeem_member_recovery(
                    self.db, "memberone", "member@example.invalid",
                    "A" * 43, "NewPassword2026Version!!",
                )
        with sqlite3.connect(self.db) as conn:
            total = conn.execute("SELECT COUNT(*) FROM Recovery_Attempts").fetchone()[0]
        self.assertEqual(total, MAX_FAILED_RECOVERIES)
        with self.assertRaises(ValueError):
            redeem_member_recovery(
                self.db, "memberone", "member@example.invalid", token,
                "NewPassword2026Version!!",
            )

    def test_inactive_member_is_not_recoverable(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE Users SET is_active=0 WHERE user_id=2")
        with self.assertRaises(ValueError):
            issue_member_recovery(self.db, 1, 2)


if __name__ == "__main__":
    unittest.main()
