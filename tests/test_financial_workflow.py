import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import khula_config as config
from khula_member_services import (
    submit_payment_claim, review_payment_claim, save_club_balance,
    latest_club_balance, create_goal, set_member_contribution_target,
    acknowledge_constitution, acknowledgement_status,
)
from khula_security import bootstrap_admin, authenticate_user, register_member


class FinancialWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "khula.db")
        self.was = config.DB_PATH
        config.DB_PATH = self.db
        self.env = patch.dict(os.environ, {
            "KHULA_BOOTSTRAP_ADMIN_USER": "khulaadmin",
            "KHULA_BOOTSTRAP_ADMIN_PASSWORD": "CorrectHorseBatteryStaple2026!",
            "KHULA_INVITE_CODE": "KhulaPrivateInvite2026!!",
            "KHULA_DEMO_MODE": "0",
        })
        self.env.start()
        config.init_database()
        self.assertTrue(bootstrap_admin(self.db))
        self.admin = authenticate_user(self.db, "khulaadmin", "CorrectHorseBatteryStaple2026!")[0]
        self.member = register_member(self.db, "memberone", "Demo Member One",
                                      "member@example.invalid", "StrongUniquePassword2026!",
                                      "KhulaPrivateInvite2026!!")

    def tearDown(self):
        self.env.stop()
        config.DB_PATH = self.was
        self.temp.cleanup()

    def test_demo_accounts_not_created_and_onboarding(self):
        with sqlite3.connect(self.db) as conn:
            members = conn.execute("SELECT username FROM Users").fetchall()
        self.assertNotIn(("admin",), members)
        self.assertEqual(len(members), 2)
        self.assertIsNone(authenticate_user(self.db, "admin", "admin123"))
        self.assertIsNotNone(authenticate_user(self.db, "memberone", "StrongUniquePassword2026!"))

    def test_invitation_cannot_be_skipped(self):
        with self.assertRaises(ValueError):
            register_member(self.db, "second", "Second Member", "second@example.invalid",
                            "LongPasswordVersion2026!", "invalid")

    def test_claim_never_posts_to_paid_ledger_without_admin_review(self):
        claim = submit_payment_claim(self.member, 2026, 10, 500, "EFT", "REF-TEST-2026", self.db)
        with sqlite3.connect(self.db) as conn:
            count = conn.execute("SELECT count(*) FROM Monthly_Contributions").fetchone()[0]
        self.assertEqual(count, 0)
        with self.assertRaises(ValueError):
            review_payment_claim(self.admin, claim, True, False, self.db)
        with self.assertRaises(PermissionError):
            review_payment_claim(self.member, claim, True, True, self.db)
        self.assertTrue(review_payment_claim(self.admin, claim, True, True, self.db))
        with sqlite3.connect(self.db) as conn:
            amt = conn.execute("SELECT amount FROM Monthly_Contributions").fetchone()[0]
        self.assertEqual(amt, 500.0)
        with self.assertRaises(ValueError):
            review_payment_claim(self.admin, claim, True, True, self.db)

    def test_club_cash_requires_admin(self):
        with self.assertRaises(PermissionError):
            save_club_balance(self.member, 10000, 3000, "2026-10-25", "BANKREF-1", self.db)
        save_club_balance(self.admin, 10000, 3000, "2026-10-25", "BANKREF-1", self.db)
        self.assertEqual(latest_club_balance(self.db)["available"], 7000)
        self.assertFalse(latest_club_balance(self.db)["is_live_bank_data"])

    def test_only_admin_sets_member_target_and_goals(self):
        with self.assertRaises(PermissionError):
            set_member_contribution_target(self.member, self.member, 300, self.db)
        set_member_contribution_target(self.admin, self.member, 300, self.db)
        with sqlite3.connect(self.db) as conn:
            amt = conn.execute("SELECT monthly_contribution FROM Users WHERE user_id=?", (self.member,)).fetchone()[0]
        self.assertEqual(amt, 300.0)
        with self.assertRaises(PermissionError):
            create_goal(self.member, "Future fund", 10000, None, self.db)
        create_goal(self.admin, "Future fund", 10000, None, self.db)

    def test_constitution_receipt_has_version(self):
        self.assertIsNone(acknowledgement_status(self.member, self.db))
        self.assertTrue(acknowledge_constitution(self.member, self.db))
        self.assertIsNotNone(acknowledgement_status(self.member, self.db))


if __name__ == "__main__":
    unittest.main()
