"""Real-data-only Khula Compass calculations and cross-member privacy."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

import khula_config as config
from khula_compass import compass_snapshot


class CompassTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = config.DB_PATH
        self.db = str(Path(self.tmp.name) / "compass.db")
        config.DB_PATH = self.db
        config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.executemany(
                "INSERT INTO Users(user_id,username,full_name,password_hash,email,"
                "role,is_active,monthly_contribution) VALUES(?,?,?,?,?,?,?,?)",
                [
                    (1, "adminperson", "Admin", "hash", "admin@example.invalid", "admin", 1, 0),
                    (2, "memberalice", "Alice Member", "hash", "alice@example.invalid", "member", 1, 500),
                    (3, "memberbob", "Bob Member", "hash", "bob@example.invalid", "member", 1, 300),
                    (4, "pendingperson", "Pending Member", "hash", "pending@example.invalid", "member", 0, 0),
                ],
            )
            today = date.today()
            conn.executemany(
                "INSERT INTO Monthly_Contributions(user_id,year,month,amount,status) "
                "VALUES(?,?,?,?,?)",
                [
                    (2, today.year, today.month, 500, "paid"),
                    (3, today.year, today.month, 900, "paid"),
                    (2, today.year, today.month, 2000, "pending"),
                ],
            )
            conn.execute(
                "INSERT INTO Payment_Claims(user_id,year,month,amount_zar,method,"
                "payment_reference,status) VALUES(?,?,?,?,?,'SECRET-PAY','pending')",
                (3, today.year, today.month, 500, "EFT"),
            )
            conn.execute(
                "INSERT INTO Investments(name,type,amount_invested,current_value)"
                " VALUES('Unverified record','ETF',500000,900000)"
            )
            conn.execute(
                "INSERT INTO Savings_Goals(name,target_zar,created_by)"
                " VALUES('Emergency fund',10000,1)"
            )

    def tearDown(self):
        config.DB_PATH = self.old
        self.tmp.cleanup()

    def test_no_bank_snapshot_is_not_zero_or_fake_cash(self):
        member = compass_snapshot(self.db, 2)
        self.assertIsNone(member["planning_cash"])
        self.assertIsNone(member["bank_snapshot"])
        self.assertEqual(member["own_paid_current_month"], Decimal("500.00"))
        self.assertEqual(member["pending_own_claims"], 0)
        self.assertEqual(member["member_count"], 2)
        self.assertIsNone(member["pending_club_claims"])
        self.assertIsNone(member["pending_registrations"])
        self.assertNotIn("Bob Member", repr(member))
        self.assertNotIn("SECRET-PAY", repr(member))

    def test_manual_bank_snapshot_not_increased_by_ledger_or_portfolio(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO Club_Balance_Snapshots "
                "(balance_zar,reserved_zar,statement_date,reference,source,attested_by) "
                "VALUES (5000,1000,?,'REDACTED','manual_admin',1)",
                (date.today().isoformat(),),
            )
        member = compass_snapshot(self.db, 3)
        self.assertEqual(member["planning_cash"], Decimal("4000.00"))
        self.assertEqual(member["own_paid_current_month"], Decimal("900.00"))
        self.assertEqual(member["pending_own_claims"], 1)
        self.assertFalse(member["bank_snapshot"]["is_live_bank_data"])
        self.assertEqual(member["bank_snapshot"]["source"], "manual_admin")

    def test_expired_statement_blocks_available_amount(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO Club_Balance_Snapshots "
                "(balance_zar,reserved_zar,statement_date,reference,source,attested_by) "
                "VALUES(20000,1000,?,'STALE','manual_admin',1)",
                ((date.today() - timedelta(days=20)).isoformat(),),
            )
        member = compass_snapshot(self.db, 2)
        self.assertIsNone(member["planning_cash"])
        self.assertFalse(member["bank_fresh"])

    def test_only_admin_sees_administrative_queue_counts(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "CREATE TABLE Membership_Applications(application_id INTEGER PRIMARY KEY,"
                "status TEXT)"
            )
            conn.execute(
                "INSERT INTO Membership_Applications(application_id,status)"
                " VALUES(1,'pending')"
            )
        admin = compass_snapshot(self.db, 1)
        member = compass_snapshot(self.db, 2)
        self.assertEqual(admin["pending_club_claims"], 1)
        self.assertEqual(admin["pending_registrations"], 1)
        self.assertIsNone(member["pending_club_claims"])
        self.assertIsNone(member["pending_registrations"])

    def test_pending_and_unknown_users_blocked(self):
        for uid in (4, 999):
            with self.assertRaises(PermissionError):
                compass_snapshot(self.db, uid)


if __name__ == "__main__":
    unittest.main()
