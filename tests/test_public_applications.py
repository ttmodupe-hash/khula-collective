"""Public sign-up and human-controlled membership approval security tests."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import khula_config as config
from khula_applications import (
    list_membership_requests, public_registration_enabled,
    request_membership, review_membership_request,
)
from khula_security import authenticate_user, hash_password, member_auth_state
from khula_member_services import update_member_access
import hashlib

TEST_CONSTITUTION = (
    "Non-production Khula governance example for testing account access; "
    "memberships, savings, conflicts of interest, custody, exits and disputes. "
    * 10
)
FLAGS = {
    "KHULA_PRIVACY_NOTICE_APPROVED": "1",
    "KHULA_INFORMATION_OFFICER_REGISTERED": "1",
    "KHULA_CROSS_BORDER_REVIEW_APPROVED": "1",
    "KHULA_OPERATOR_DPA_REVIEWED": "1",
    "KHULA_CONSTITUTION_RATIFIED": "1",
    "KHULA_RESPONSIBLE_PARTY_NAME": "Khula Test Collective",
    "KHULA_PRIVACY_CONTACT_EMAIL": "privacy@example.invalid",
    "KHULA_PRIVACY_NOTICE_VERSION": "approved-2026-10",
    "KHULA_CONSTITUTION_VERSION": "approved-test-2026-10",
    "KHULA_CONSTITUTION_DOCUMENT_TEXT": TEST_CONSTITUTION,
    "KHULA_CONSTITUTION_SHA256": hashlib.sha256(
        TEST_CONSTITUTION.encode("utf-8")
    ).hexdigest(),
    "KHULA_PRODUCTION": "1",
    "KHULA_DEMO_MODE": "0",
}


class PublicMembershipApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "applications.db")
        self.old_path = config.DB_PATH
        config.DB_PATH = self.db
        self.env = patch.dict(os.environ, FLAGS, clear=True)
        self.env.start()
        config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO Users (user_id,username,full_name,email,password_hash,role,is_active) "
                "VALUES (1,'memberadmin','Club Administrator','admin@example.invalid',?,'admin',1)",
                (hash_password("StrongAdminPassword2026!"),),
            )
        self.admin = 1

    def tearDown(self):
        self.env.stop()
        config.DB_PATH = self.old_path
        self.temp.cleanup()

    def apply(self, username="newmember", email="newmember@example.invalid"):
        return request_membership(
            self.db, username, "Prospective Member", email,
            "LongPrivatePassword2026!",
            notice_acknowledged=True,
            international_transfer_acknowledged=True,
            adult_confirmed=True,
        )

    def test_public_application_is_not_authentication_or_membership(self):
        application_id = self.apply()
        self.assertGreater(application_id, 0)
        with sqlite3.connect(self.db) as conn:
            user = conn.execute(
                "SELECT user_id,is_active,role,fica_verified FROM Users "
                "WHERE username='newmember'"
            ).fetchone()
            contribution_count = conn.execute(
                "SELECT COUNT(*) FROM Monthly_Contributions"
            ).fetchone()[0]
            self.assertEqual(contribution_count, 0)
            consent = conn.execute(
                "SELECT notice_version FROM Member_Privacy_Acknowledgements "
                "WHERE user_id=?", (user[0],)
            ).fetchone()
            source = conn.execute(
                "SELECT status,source,cross_border_consent_at "
                "FROM Membership_Applications WHERE application_id=?", (application_id,),
            ).fetchone()
        self.assertEqual(user[1:], (0, "member", 0))
        self.assertEqual(consent[0], FLAGS["KHULA_PRIVACY_NOTICE_VERSION"])
        self.assertEqual(source[:2], ("pending", "public"))
        self.assertTrue(source[2])
        self.assertIsNone(
            authenticate_user(self.db, "newmember", "LongPrivatePassword2026!")
        )
        with self.assertRaises(ValueError):
            update_member_access(self.admin, user[0], "member", True, self.db)

    def test_approval_requires_real_admin_and_both_attestations(self):
        aid = self.apply()
        with sqlite3.connect(self.db) as conn:
            user_id = conn.execute(
                "SELECT user_id FROM Users WHERE username='newmember'"
            ).fetchone()[0]
        with self.assertRaises(PermissionError):
            list_membership_requests(self.db, user_id)
        with self.assertRaises(PermissionError):
            review_membership_request(
                self.db, user_id, aid, "approved",
                identity_confirmed=True, eligibility_confirmed=True,
            )
        with self.assertRaises(ValueError):
            review_membership_request(
                self.db, self.admin, aid, "approved",
                identity_confirmed=True, eligibility_confirmed=False,
            )
        with self.assertRaises(ValueError):
            review_membership_request(
                self.db, self.admin, aid, "approved",
                identity_confirmed=False, eligibility_confirmed=True,
            )
        self.assertEqual(
            len(list_membership_requests(self.db, self.admin)), 1
        )
        result = review_membership_request(
            self.db, self.admin, aid, "approved",
            identity_confirmed=True, eligibility_confirmed=True,
        )
        self.assertEqual(result["status"], "approved")
        self.assertIsNotNone(
            authenticate_user(self.db, "newmember", "LongPrivatePassword2026!")
        )
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT role,is_active,auth_epoch FROM Users WHERE user_id=?",
                (user_id,),
            ).fetchone()
            audits = conn.execute(
                "SELECT action_type FROM Admin_Actions WHERE action_type=?",
                ("membership_application_approved",),
            ).fetchall()
        self.assertEqual(row, ("member", 1, 1))
        self.assertEqual(len(audits), 1)
        with self.assertRaises(ValueError):
            review_membership_request(
                self.db, self.admin, aid, "approved",
                identity_confirmed=True, eligibility_confirmed=True,
            )

    def test_rejection_never_activates_an_account(self):
        aid = self.apply()
        result = review_membership_request(self.db, self.admin, aid, "rejected")
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(
            authenticate_user(self.db, "newmember", "LongPrivatePassword2026!")
        )
        with self.assertRaises(ValueError):
            update_member_access(
                self.admin, result["user_id"], "member", True, self.db
            )
        with self.assertRaises(ValueError):
            review_membership_request(
                self.db, self.admin, aid, "approved",
                identity_confirmed=True, eligibility_confirmed=True,
            )

    def test_public_signup_denied_when_compliance_missing(self):
        with patch.dict(os.environ, {
            "KHULA_PRIVACY_NOTICE_APPROVED": "0"
        }):
            self.assertFalse(public_registration_enabled())
            with self.assertRaises(ValueError):
                self.apply()
        with sqlite3.connect(self.db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM Users").fetchone()[0]
        self.assertEqual(count, 1)

    def test_public_pause_and_consent_checks(self):
        with patch.dict(os.environ, {"KHULA_PUBLIC_REGISTRATION_PAUSED": "1"}):
            self.assertFalse(public_registration_enabled())
            with self.assertRaises(ValueError):
                self.apply()
        for key in ("notice_acknowledged",
                    "international_transfer_acknowledged", "adult_confirmed"):
            choices = dict(
                notice_acknowledged=True,
                international_transfer_acknowledged=True,
                adult_confirmed=True,
            )
            choices[key] = False
            with self.assertRaises(ValueError):
                request_membership(
                    self.db, "another", "Example Applicant",
                    "somebody@example.invalid", "LongPrivatePassword2026!",
                    **choices,
                )

    def test_duplicate_and_invalid_details_blocked(self):
        self.apply()
        with self.assertRaises(ValueError):
            self.apply(username="someone", email="NEWMember@EXAMPLE.invalid")
        with self.assertRaises(ValueError):
            self.apply(username="newmember", email="other@example.invalid")
        with self.assertRaises(ValueError):
            self.apply(username="someoneelse", email="bad-address")
        with self.assertRaises(ValueError):
            request_membership(
                self.db, "another", "Example Applicant", "person@example.invalid",
                "short", notice_acknowledged=True,
                international_transfer_acknowledged=True, adult_confirmed=True,
            )

    def test_global_hourly_limit_and_no_bypass(self):
        self.apply()
        with patch("khula_applications.MAX_HOURLY_APPLICATIONS", 1):
            with self.assertRaises(ValueError):
                self.apply(username="second", email="second@example.invalid")
        self.assertEqual(
            len(list_membership_requests(self.db, self.admin)), 1
        )

    def test_review_and_role_changes_invalidate_member_sessions(self):
        aid = self.apply()
        uid = review_membership_request(
            self.db, self.admin, aid, "approved",
            identity_confirmed=True, eligibility_confirmed=True,
        )["user_id"]
        before = member_auth_state(self.db, uid)
        update_member_access(self.admin, uid, "member", False, self.db)
        after = member_auth_state(self.db, uid)
        self.assertEqual(after[3], before[3] + 1)
        self.assertEqual(after[1], 0)
        self.assertIsNone(authenticate_user(
            self.db, "newmember", "LongPrivatePassword2026!"
        ))
        with self.assertRaises(ValueError):
            update_member_access(self.admin, uid, "admin", True, self.db)


if __name__ == "__main__":
    unittest.main()
