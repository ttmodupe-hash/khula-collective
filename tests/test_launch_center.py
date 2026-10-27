"""Khula Launch Control must disclose only honest admin-scoped readiness."""
import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import khula_config as config
from khula_launch_center import launch_status


class LaunchCenterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "launch.db")
        self.before = config.DB_PATH
        config.DB_PATH = self.db
        self.env = patch.dict(os.environ, {
            "KHULA_DEMO_MODE": "0",
            "KHULA_PRODUCTION": "1",
            "KHULA_BOOTSTRAP_ADMIN_PASSWORD": "test-only-should-not-be-disclosed",
        }, clear=True)
        self.env.start()
        config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.executemany(
                "INSERT INTO Users "
                "(user_id,username,full_name,password_hash,role,is_active,email) "
                "VALUES (?,?,?,?,?,?,?)",
                [
                    (1, "admin", "Admin", "hash", "admin", 1, "admin@example.invalid"),
                    (2, "member1", "Private Alice", "hash", "member", 1, "alice@example.invalid"),
                    (3, "member2", "Private Bob", "hash", "member", 0, "bob@example.invalid"),
                ],
            )
            conn.execute(
                "INSERT INTO Payment_Claims(user_id,year,month,amount_zar,"
                "method,payment_reference) VALUES (2,2026,10,500,'EFT','SECRET-REF')"
            )

    def tearDown(self):
        self.env.stop()
        config.DB_PATH = self.before
        self.tmp.cleanup()

    def test_admin_sees_only_aggregate_operational_counts(self):
        result = launch_status(self.db, 1)
        self.assertTrue(result["database_quick_check_ok"])
        self.assertTrue(result["production"])
        self.assertFalse(result["registration_open"])
        self.assertFalse(result["relevant_gate_status"]["ready"])
        self.assertEqual(result["active_members"], 1)
        self.assertEqual(result["inactive_members"], 1)
        self.assertEqual(result["pending_claims"], 1)
        self.assertEqual(result["pending_applications"], 0)
        self.assertFalse(result["bank_api_verified"])
        self.assertFalse(result["restore_test_verified"])
        self.assertFalse(result["outbound_email_verified"])
        self.assertTrue(result["bootstrap_secret_configured"])
        self.assertNotIn("test-only-should-not-be-disclosed", repr(result))
        self.assertNotIn("alice@example.invalid", repr(result))
        self.assertNotIn("SECRET-REF", repr(result))

    def test_member_or_unknown_cannot_read_launch_information(self):
        for uid in (2, 3, 999):
            with self.assertRaises(PermissionError):
                launch_status(self.db, uid)

    def test_stale_manual_bank_record_is_not_fresh(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO Club_Balance_Snapshots("
                "balance_zar,reserved_zar,statement_date,reference,source,attested_by)"
                " VALUES(5000,1500,?,'BANK-CHECK','manual_admin',1)",
                ((date.today()-timedelta(days=30)).isoformat(),),
            )
        result = launch_status(self.db, 1)
        self.assertTrue(result["bank_snapshot_exists"])
        self.assertFalse(result["bank_snapshot_fresh"])
        self.assertEqual(result["cash_source"], "manual_admin")
        self.assertNotIn("5000", repr(result))

    def test_pause_is_respected_when_all_flags_are_pretended(self):
        # This test only verifies the software gate. It is NOT a legal approval.
        import hashlib
        doc = "Test constitution only — no member approval or legal standing. " * 12
        env = {
            "KHULA_DEMO_MODE": "0",
            "KHULA_PRODUCTION": "1",
            "KHULA_PRIVACY_NOTICE_APPROVED": "1",
            "KHULA_INFORMATION_OFFICER_REGISTERED": "1",
            "KHULA_CROSS_BORDER_REVIEW_APPROVED": "1",
            "KHULA_OPERATOR_DPA_REVIEWED": "1",
            "KHULA_CONSTITUTION_RATIFIED": "1",
            "KHULA_RESPONSIBLE_PARTY_NAME": "Fictional Test Association",
            "KHULA_PRIVACY_CONTACT_EMAIL": "privacy@example.invalid",
            "KHULA_PRIVACY_NOTICE_VERSION": "approved-test-2026-10",
            "KHULA_CONSTITUTION_VERSION": "approved-test-2026-10",
            "KHULA_CONSTITUTION_DOCUMENT_TEXT": doc,
            "KHULA_CONSTITUTION_SHA256": hashlib.sha256(doc.encode()).hexdigest(),
        }
        self.assertTrue(launch_status(self.db, 1, env=env)["registration_open"])
        env["KHULA_PUBLIC_REGISTRATION_PAUSED"] = "1"
        self.assertFalse(launch_status(self.db, 1, env=env)["registration_open"])


if __name__ == "__main__":
    unittest.main()
