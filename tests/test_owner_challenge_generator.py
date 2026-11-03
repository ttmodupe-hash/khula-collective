"""Local-only owner challenge generator: no secret disclosure in CI output."""
import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from scripts.generate_owner_challenge import (
    generate_owner_challenge, main,
)
from khula_owner_access import owner_setup_available


class OwnerChallengeGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.when = datetime(2026, 11, 3, 4, 30, 0, tzinfo=timezone.utc)

    def test_fresh_owner_challenge_compatible_with_existing_app_validator(self):
        result = generate_owner_challenge(
            "  Owner@Example.invalid  ", now=self.when, hours=6
        )
        self.assertEqual(result.email, "owner@example.invalid")
        self.assertEqual(len(result.code), 43)
        self.assertEqual(
            hashlib.sha256(result.code.encode("ascii")).hexdigest(),
            result.sha256,
        )
        self.assertEqual(result.expires_utc, "2026-11-03T10:30:00Z")
        settings = {
            "KHULA_OWNER_SETUP_EMAIL": result.email,
            "KHULA_OWNER_SETUP_TOKEN_SHA256": result.sha256,
            "KHULA_OWNER_SETUP_EXPIRES_UTC": result.expires_utc,
            "KHULA_OWNER_SETUP_DISABLED": "0",
        }
        self.assertTrue(owner_setup_available(env=settings, now=self.when))
        self.assertFalse(owner_setup_available(
            env=settings, now=self.when + timedelta(hours=7)
        ))
        settings["KHULA_OWNER_SETUP_DISABLED"] = "1"
        self.assertFalse(owner_setup_available(env=settings, now=self.when))
        # The returned digest is safe to configure; it must not contain
        # any fragment of the cleartext bearer code.
        self.assertNotIn(result.code, repr(settings))

    def test_code_is_random_and_uniquely_generated(self):
        first = generate_owner_challenge(
            "owner@example.invalid", now=self.when
        )
        second = generate_owner_challenge(
            "owner@example.invalid", now=self.when
        )
        self.assertNotEqual(first.code, second.code)
        self.assertNotEqual(first.sha256, second.sha256)

    def test_bad_expiry_email_and_clock_rejected(self):
        for hours in (0, 13, 24, True, "6"):
            with self.assertRaises(ValueError):
                generate_owner_challenge(
                    "owner@example.invalid", now=self.when, hours=hours
                )
        for bad in ("", "not-an-email", "someone@",
                    "owner@example.invalid\nINJECTED=1", None):
            with self.assertRaises(ValueError):
                generate_owner_challenge(bad, now=self.when)
        with self.assertRaises(ValueError):
            generate_owner_challenge(
                "owner@example.invalid", now=datetime(2026, 11, 3)
            )

    def test_noninteractive_cli_refuses_secret_logging(self):
        with patch("sys.stdout.isatty", return_value=False):
            with patch("sys.stderr"):
                with self.assertRaises(SystemExit) as failure:
                    main(["--owner-email", "owner@example.invalid"])
        self.assertEqual(failure.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
