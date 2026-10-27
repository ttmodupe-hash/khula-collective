"""Privacy-safe applicant receipt and invited-member admission tests."""
import hashlib
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import khula_config
from khula_applications import request_membership, review_membership_request
from khula_invitations import generate_invitation
from khula_membership_receipts import get_public_application_status, ensure_receipt_schema
from khula_security import hash_password, register_member, authenticate_user
from khula_member_services import update_member_access


TEST_CONSTITUTION = ("Private test fixture for a Khula club constitution. "
                     "Rules include approved membership, governance, withdrawals, "
                     "contributions and review of financial records. " * 10)
SETTINGS = {
    "KHULA_PRODUCTION": "1",
    "KHULA_DEMO_MODE": "0",
    "KHULA_PRIVACY_NOTICE_APPROVED": "1",
    "KHULA_INFORMATION_OFFICER_REGISTERED": "1",
    "KHULA_CROSS_BORDER_REVIEW_APPROVED": "1",
    "KHULA_OPERATOR_DPA_REVIEWED": "1",
    "KHULA_CONSTITUTION_RATIFIED": "1",
    "KHULA_RESPONSIBLE_PARTY_NAME": "Test Khula Association",
    "KHULA_PRIVACY_CONTACT_EMAIL": "privacy@example.invalid",
    "KHULA_PRIVACY_NOTICE_VERSION": "approved-test-2026-10",
    "KHULA_CONSTITUTION_VERSION": "approved-test-2026-10",
    "KHULA_CONSTITUTION_DOCUMENT_TEXT": TEST_CONSTITUTION,
    "KHULA_CONSTITUTION_SHA256": hashlib.sha256(
        TEST_CONSTITUTION.encode("utf-8")).hexdigest(),
}


class MembershipReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = khula_config.DB_PATH
        self.db = str(Path(self.temp.name) / "members.db")
        khula_config.DB_PATH = self.db
        self.env = patch.dict(os.environ, SETTINGS, clear=True)
        self.env.start()
        khula_config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO Users (user_id,username,full_name,email,password_hash,role,is_active) "
                "VALUES (1,'clubadmin','Club admin','admin@example.invalid',?,'admin',1)",
                (hash_password("AReallyGoodAdminPassword2026!"),),
            )

    def tearDown(self):
        self.env.stop()
        khula_config.DB_PATH = self.original
        self.temp.cleanup()

    def apply(self, username="candidate", email="candidate@example.invalid", receipt=True):
        return request_membership(
            self.db, username, "Prospective Member", email,
            "CandidateStrongPassword2026!",
            notice_acknowledged=True,
            international_transfer_acknowledged=True,
            adult_confirmed=True,
            include_receipt=receipt,
        )

    def test_receipt_is_random_secret_and_does_not_leak_member_identity(self):
        result = self.apply()
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["application_id"], int)
        token = result["tracking_code"]
        self.assertGreaterEqual(len(token), 40)
        self.assertEqual(get_public_application_status(self.db, token), {"status": "pending"})
        with sqlite3.connect(self.db) as conn:
            row = conn.execute(
                "SELECT token_sha256,expires_at FROM Membership_Status_Receipts "
                "WHERE application_id=?", (result["application_id"],)
            ).fetchone()
        self.assertNotIn(token, repr(row))
        self.assertEqual(row[0], hashlib.sha256(token.encode("ascii")).hexdigest())
        self.assertNotIn("Prospective Member", repr(get_public_application_status(self.db, token)))
        self.assertNotIn("candidate@example.invalid", repr(get_public_application_status(self.db, token)))
        self.assertIsNone(get_public_application_status(self.db, "invalid"))
        self.assertIsNone(get_public_application_status(self.db, "A" * 43))

    def test_receipt_status_updates_after_real_review_and_account_revocation(self):
        result = self.apply()
        token = result["tracking_code"]
        self.assertIsNone(
            authenticate_user(self.db, "candidate", "CandidateStrongPassword2026!")
        )
        review_membership_request(
            self.db, 1, result["application_id"], "approved",
            identity_confirmed=True, eligibility_confirmed=True,
        )
        self.assertEqual(get_public_application_status(self.db, token), {"status": "approved"})
        update_member_access(1, self._member_id(), "member", False, self.db)
        self.assertEqual(get_public_application_status(self.db, token), {"status": "inactive"})

    def _member_id(self):
        with sqlite3.connect(self.db) as conn:
            return conn.execute("SELECT user_id FROM Users WHERE username='candidate'").fetchone()[0]

    def test_rejected_application_stays_rejected(self):
        result = self.apply()
        review_membership_request(self.db, 1, result["application_id"], "rejected")
        self.assertEqual(
            get_public_application_status(self.db, result["tracking_code"]),
            {"status": "rejected"},
        )

    def test_receipt_expiration_and_missing_database(self):
        result = self.apply()
        future = datetime.now(timezone.utc) + timedelta(days=46)
        self.assertIsNone(get_public_application_status(
            self.db, result["tracking_code"], now=future
        ))
        self.assertIsNone(get_public_application_status(
            self.db + ".missing", result["tracking_code"]
        ))

    def test_receipt_is_not_created_in_old_compatibility_response(self):
        ref = self.apply(receipt=False)
        self.assertIsInstance(ref, int)
        with sqlite3.connect(self.db) as conn:
            ensure_receipt_schema(conn)
            count = conn.execute("SELECT COUNT(*) FROM Membership_Status_Receipts").fetchone()[0]
        self.assertEqual(count, 0)

    def test_invited_members_need_the_same_independent_approval(self):
        invitation = generate_invitation(self.db, 1, "invited@example.invalid")
        result = register_member(
            self.db, "invited", "Invited Adult Member", "invited@example.invalid",
            "InvitedStrongPassword2026!", invitation,
            notice_acknowledged=True,
            international_transfer_acknowledged=True,
            adult_confirmed=True,
            include_receipt=True,
        )
        self.assertIsInstance(result, dict)
        token = result["tracking_code"]
        self.assertEqual(get_public_application_status(self.db, token), {"status": "pending"})
        self.assertIsNone(authenticate_user(self.db, "invited", "InvitedStrongPassword2026!"))
        with sqlite3.connect(self.db) as conn:
            source = conn.execute(
                "SELECT application_id,source FROM Membership_Applications "
                "WHERE user_id=?", (result["user_id"],)
            ).fetchone()
        self.assertEqual(source[1], "invitation")
        with self.assertRaises(ValueError):
            update_member_access(1, result["user_id"], "member", True, self.db)
        review_membership_request(
            self.db, 1, source[0], "approved",
            identity_confirmed=True, eligibility_confirmed=True,
        )
        self.assertIsNotNone(authenticate_user(self.db, "invited", "InvitedStrongPassword2026!"))

    def test_invited_member_cannot_omit_age_or_overseas_acknowledgement(self):
        invitation = generate_invitation(self.db, 1, "notready@example.invalid")
        with self.assertRaises(ValueError):
            register_member(
                self.db, "notready", "Not Ready Member", "notready@example.invalid",
                "NotReadyPassword2026!", invitation, notice_acknowledged=True,
                international_transfer_acknowledged=False, adult_confirmed=True
            )
        with sqlite3.connect(self.db) as conn:
            users = conn.execute(
                "SELECT COUNT(*) FROM Users WHERE username='notready'"
            ).fetchone()[0]
            used = conn.execute(
                "SELECT used_at FROM Member_Invitations WHERE email='notready@example.invalid'"
            ).fetchone()[0]
        self.assertEqual(users, 0)
        self.assertIsNone(used)


if __name__ == "__main__":
    unittest.main()
