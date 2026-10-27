"""Ensure contribution reporting and the directory do not expose other members."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import khula_config
from khula_reporting import read_reports, read_member_directory


class ReportingPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = str(Path(self.folder.name) / "privacy.db")
        self.original = khula_config.DB_PATH
        khula_config.DB_PATH = self.db
        self.env = patch.dict(os.environ, {"KHULA_DEMO_MODE": "0"})
        self.env.start()
        khula_config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.executemany(
                "INSERT INTO Users (user_id,username,full_name,email,phone,"
                "password_hash,role,is_active,fica_verified) VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    (1, "admin", "Admin Only", "admin@example.invalid",
                     "0111111111", "hash", "admin", 1, 0),
                    (2, "first", "Private Member Alpha", "alpha@example.invalid",
                     "0222222222", "hash", "member", 1, 0),
                    (3, "second", "Private Member Beta", "beta@example.invalid",
                     "0333333333", "hash", "member", 1, 1),
                    (4, "inactive", "Suspended Member", "inactive@example.invalid",
                     "0444444444", "hash", "member", 0, 0),
                ],
            )
            conn.executemany(
                "INSERT INTO Monthly_Contributions "
                "(user_id,year,month,amount,status) VALUES (?,?,10,?,?)",
                [
                    (2, 2026, 200, "paid"),
                    (3, 2026, 900, "paid"),
                    (2, 2026, 500, "pending"),
                ],
            )
            conn.execute(
                "INSERT INTO Investments(name,type,amount_invested,current_value,returns)"
                " VALUES ('Example Holding','ETF',1000,1200,200)"
            )

    def tearDown(self):
        khula_config.DB_PATH = self.original
        self.env.stop()
        self.folder.cleanup()

    def test_member_only_sees_own_payment_data(self):
        result = read_reports(self.db, 2)
        self.assertFalse(result["is_admin"])
        self.assertEqual(str(result["viewer_recorded_paid_zar"]), "200.00")
        self.assertEqual(str(result["club_recorded_paid_zar"]), "1100.00")
        self.assertEqual(result["member_totals"], [])
        self.assertEqual(result["admin_csv"], [])
        self.assertNotIn("Private Member Beta", repr(result))
        self.assertNotIn("beta@example.invalid", repr(result))
        self.assertNotIn("0333333333", repr(result))

    def test_administrator_can_reconcile_member_totals(self):
        result = read_reports(self.db, 1)
        self.assertTrue(result["is_admin"])
        self.assertIn(("Private Member Alpha", 200), result["member_totals"])
        self.assertIn(("Private Member Beta", 900), result["member_totals"])
        self.assertEqual(len(result["admin_csv"]), 3)

    def test_member_directory_excludes_other_people(self):
        rows = read_member_directory(self.db, 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], 2)
        self.assertNotIn("Private Member Beta", repr(rows))
        self.assertNotIn("beta@example.invalid", repr(rows))
        self.assertNotIn("0333333333", repr(rows))

    def test_admin_directory_is_role_gated(self):
        rows = read_member_directory(self.db, 1)
        self.assertEqual(len(rows), 4)

    def test_inactive_and_unknown_users_cannot_access_reports_or_directory(self):
        for user in (4, 999):
            with self.assertRaises(PermissionError):
                read_reports(self.db, user)
            with self.assertRaises(PermissionError):
                read_member_directory(self.db, user)


if __name__ == "__main__":
    unittest.main()
