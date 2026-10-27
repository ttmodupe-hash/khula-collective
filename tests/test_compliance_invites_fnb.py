"""Protect personal invitations, bank-access claims and POPIA acknowledgement."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import khula_config
from khula_bank_access import bank_integration_email, record_application_submission, latest_application
from khula_compliance import onboarding_gate_status, record_notice_acknowledgement
from khula_invitations import generate_invitation, invitation_email_draft
from khula_security import hash_password, register_member, registration_enabled, authenticate_user

FLAGS = {
    "KHULA_PRIVACY_NOTICE_APPROVED": "1",
    "KHULA_INFORMATION_OFFICER_REGISTERED": "1",
    "KHULA_CROSS_BORDER_REVIEW_APPROVED": "1",
    "KHULA_OPERATOR_DPA_REVIEWED": "1",
    "KHULA_CONSTITUTION_RATIFIED": "1",
    "KHULA_RESPONSIBLE_PARTY_NAME": "Khula Collective Association",
    "KHULA_PRIVACY_CONTACT_EMAIL": "privacy@example.invalid",
    "KHULA_PRIVACY_NOTICE_VERSION": "v2026-10-approved",
    "KHULA_PRODUCTION": "1",
    "KHULA_DEMO_MODE": "0",
}


class ComplianceInvitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "khula.db")
        self.config_before = khula_config.DB_PATH
        khula_config.DB_PATH = self.db
        khula_config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO Users (user_id,username,full_name,password_hash,role,is_active) "
                "VALUES (1,'clubadmin','Administrator',?,'admin',1)",
                (hash_password("AdminGoodPassword2026!!"),),
            )
            conn.execute(
                "INSERT INTO Users (user_id,username,full_name,password_hash,email,role,is_active) "
                "VALUES (2,'existing','Existing Member',?,'existing@example.invalid','member',1)",
                (hash_password("MemberGoodPassword2026!"),),
            )

    def tearDown(self):
        khula_config.DB_PATH = self.config_before
        self.tmp.cleanup()

    def test_real_registration_blocked_without_all_approvals(self):
        with patch.dict(os.environ, {"KHULA_PRODUCTION": "1", "KHULA_DEMO_MODE": "0",
                                     "KHULA_PRIVACY_NOTICE_APPROVED": "0"}, clear=True):
            status = onboarding_gate_status()
            self.assertFalse(status["ready"])
            self.assertFalse(registration_enabled())
            with self.assertRaises(ValueError):
                generate_invitation(self.db, 1, "expected@example.invalid")

    def test_railway_production_environment_never_bypasses_gate(self):
        with patch.dict(os.environ, {
                "RAILWAY_ENVIRONMENT_NAME": "production",
                "KHULA_PRODUCTION": "0", "KHULA_DEMO_MODE": "0",
                "KHULA_PRIVACY_NOTICE_APPROVED": "0"
            }, clear=True):
            self.assertFalse(registration_enabled())
            with self.assertRaises(ValueError):
                generate_invitation(self.db, 1, "newmember@example.invalid")

    def test_one_time_invitation_requires_acknowledgement(self):
        with patch.dict(os.environ, FLAGS, clear=True):
            self.assertTrue(onboarding_gate_status()["ready"])
            self.assertTrue(registration_enabled())
            token = generate_invitation(self.db, 1, "newmember@example.invalid")
            with self.assertRaises(ValueError):
                register_member(
                    self.db, "newmember", "New Member", "newmember@example.invalid",
                    "MemberStrongPassword2026!", token,
                    notice_acknowledged=False,
                )
            member = register_member(
                self.db, "newmember", "New Member", "newmember@example.invalid",
                "MemberStrongPassword2026!", token,
                notice_acknowledged=True,
            )
            with sqlite3.connect(self.db) as conn:
                ack = conn.execute(
                    "SELECT notice_version,notice_sha256 FROM Member_Privacy_Acknowledgements "
                    "WHERE user_id=?", (member,),
                ).fetchone()
                invitation = conn.execute(
                    "SELECT token_sha256,used_by FROM Member_Invitations WHERE email=?",
                    ("newmember@example.invalid",),
                ).fetchone()
                user = conn.execute("SELECT is_active FROM Users WHERE user_id=?", (member,)).fetchone()
            self.assertEqual(ack[0], FLAGS["KHULA_PRIVACY_NOTICE_VERSION"])
            self.assertEqual(len(ack[1]), 64)
            self.assertEqual(invitation[1], member)
            self.assertNotEqual(invitation[0], token)
            self.assertEqual(user[0], 0)
            self.assertIsNone(authenticate_user(self.db,"newmember","MemberStrongPassword2026!"))
            with self.assertRaises(ValueError):
                register_member(
                    self.db, "newmember2", "Second Member", "newmember@example.invalid",
                    "AnotherMemberPassword2026!", token,
                    notice_acknowledged=True,
                )

    def test_private_invitation_email_uses_actual_token_without_links_with_query_secrets(self):
        fake = "A" * 43
        mail = invitation_email_draft(
            "expected@example.invalid", fake,
            privacy_email="privacy@example.invalid",
        )
        self.assertIn(fake, mail["body"])
        self.assertIn("expires within 7 days", mail["body"])
        self.assertIn("privacy@example.invalid", mail["body"])
        self.assertNotIn("?token=", mail["body"])
        self.assertNotIn("FNB login", mail["subject"])

    def test_only_admin_can_log_real_application_reference(self):
        with self.assertRaises(PermissionError):
            record_application_submission(self.db, 2, "FNBCASE-001")
        with self.assertRaises(ValueError):
            record_application_submission(self.db, 1, "1234567890")
        rid = record_application_submission(self.db, 1, "FNBCASE-001")
        latest = latest_application(self.db, 1)
        self.assertEqual(latest[0], rid)
        self.assertEqual(latest[1], "application_submitted")
        with sqlite3.connect(self.db) as conn:
            events=conn.execute("SELECT action_type FROM Admin_Actions").fetchall()
        self.assertIn(("fnb_api_application_logged",), events)

    def test_bank_email_requests_read_only_no_secrets(self):
        letter = bank_integration_email(
            legal_name="Khula Collective",
            contact_email="committee@example.invalid",
        )
        self.assertIn("Transaction History", letter["subject"])
        self.assertIn("read-only", letter["body"].lower())
        self.assertIn("no", letter["body"].lower())
        self.assertIn("OAuth 2.0", letter["body"])
        self.assertNotIn("1234567890", letter["body"])


if __name__ == "__main__":
    unittest.main()
