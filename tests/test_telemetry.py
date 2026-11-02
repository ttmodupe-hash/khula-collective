"""Offline, synthetic tests of privacy-gated aggregate telemetry."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from khula_telemetry import (
    EVENTS, RETENTION_DAYS, adaptive_cache_ttl, metrics_for_admin,
    popular_shortcuts, record, telemetry_permitted, timed,
)

APPROVED = {
    "KHULA_PRODUCTION": "1",
    "KHULA_TELEMETRY_ENABLED": "1",
    "KHULA_PRIVACY_NOTICE_APPROVED": "1",
    "KHULA_CROSS_BORDER_REVIEW_APPROVED": "1",
    "KHULA_OPERATOR_DPA_REVIEWED": "1",
    "KHULA_TELEMETRY_POLICY_APPROVED": "1",
}


class TelemetryPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.metrics = Path(self.temp.name) / "anonymous.sqlite3"
        self.ledger = Path(self.temp.name) / "ledger.sqlite3"
        self.now = datetime.now(timezone.utc)
        with sqlite3.connect(self.ledger) as conn:
            conn.execute(
                "CREATE TABLE Users (user_id INTEGER PRIMARY KEY, role TEXT, is_active INTEGER)"
            )
            conn.executemany(
                "INSERT INTO Users(user_id,role,is_active) VALUES (?,?,?)",
                [(1, "admin", 1), (2, "member", 1), (3, "admin", 0)],
            )

    def submit(self, event, outcome="ok", **overrides):
        params = dict(
            db_path=self.metrics, env=APPROVED, consent=True,
            now=self.now, duration_ms=153.7
        )
        params.update(overrides)
        return record(event, outcome, **params)

    def test_production_fails_closed_without_real_approvals(self):
        self.assertFalse(telemetry_permitted({"KHULA_PRODUCTION": "1"}))
        for key in (
            "KHULA_PRIVACY_NOTICE_APPROVED",
            "KHULA_CROSS_BORDER_REVIEW_APPROVED",
            "KHULA_OPERATOR_DPA_REVIEWED",
            "KHULA_TELEMETRY_POLICY_APPROVED",
        ):
            env = {**APPROVED, key: "0"}
            self.assertFalse(telemetry_permitted(env))
            self.assertFalse(self.submit("auth.login", env=env))
            self.assertFalse(self.metrics.exists())
        self.assertFalse(self.submit("auth.login", consent=False))
        self.assertFalse(self.metrics.exists())
        self.assertTrue(telemetry_permitted(APPROVED))

    def test_only_fixed_labels_can_be_stored(self):
        for event in (
            "auth.login:someone@example.com",
            "member.bank_balance",
            "../khula_collective.db",
            "https://example.com/secret?code=x",
            "auth.login\npassword",
        ):
            with self.assertRaises(ValueError):
                self.submit(event)
        for outcome in ("exception:Invalid password", "contact@x.com", "", 1):
            with self.assertRaises(ValueError):
                self.submit("auth.login", outcome)
        self.assertFalse(self.metrics.exists())
        self.assertIn("api.mentor", EVENTS)

    def test_daily_aggregate_no_individual_or_precise_timestamps(self):
        self.assertTrue(self.submit("auth.login"))
        self.assertTrue(self.submit("auth.login", duration_ms=201))
        self.assertTrue(self.submit("auth.login", "blocked", duration_ms=999999))
        with sqlite3.connect(self.metrics) as conn:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(Telemetry_Daily)")]
            counts = conn.execute(
                "SELECT outcome,samples,total_latency_ms,max_latency_ms "
                "FROM Telemetry_Daily ORDER BY outcome"
            ).fetchall()
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM Telemetry_Daily"
            ).fetchone()[0], 2)
        self.assertEqual(
            columns,
            ["utc_day", "event", "outcome", "samples",
             "total_latency_ms", "max_latency_ms"],
        )
        self.assertEqual(counts, [
            ("blocked", 1, 60000, 60000),
            ("ok", 2, 300, 200),
        ])

    def test_auto_retention_runs_without_background_jobs(self):
        earlier = self.now - timedelta(days=RETENTION_DAYS + 3)
        self.assertTrue(self.submit("auth.login", now=earlier))
        self.assertTrue(self.submit("auth.login", now=self.now))
        with sqlite3.connect(self.metrics) as conn:
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM Telemetry_Daily"
            ).fetchone()[0], 1)

    def test_no_write_to_existing_financial_ledger(self):
        with sqlite3.connect(self.ledger) as conn:
            before = conn.execute("SELECT * FROM Users ORDER BY user_id").fetchall()
        self.assertTrue(self.submit("member.review"))
        with sqlite3.connect(self.ledger) as conn:
            self.assertEqual(
                conn.execute("SELECT * FROM Users ORDER BY user_id").fetchall(), before
            )
            self.assertEqual(conn.execute(
                "SELECT name FROM sqlite_master WHERE name='Telemetry_Daily'"
            ).fetchall(), [])

    def test_active_admin_only_can_see_anonymous_counts(self):
        self.submit("member.review")
        for user in (2, 3, 404):
            with self.assertRaises(PermissionError):
                metrics_for_admin(self.ledger, user,
                                  metric_db_path=self.metrics, env=APPROVED)
        snapshot = metrics_for_admin(self.ledger, 1,
                                    metric_db_path=self.metrics, env=APPROVED)
        self.assertTrue(snapshot["enabled"])
        self.assertEqual(snapshot["sample_count"], 1)
        self.assertEqual(snapshot["rows"][0]["Action"], "member.review")
        disabled = metrics_for_admin(
            self.ledger, 1, metric_db_path=self.metrics,
            env={**APPROVED, "KHULA_TELEMETRY_POLICY_APPROVED": "0"},
        )
        self.assertFalse(disabled["enabled"])
        self.assertEqual(disabled["rows"], [])

    def test_public_cache_only_adapts_after_large_error_sample(self):
        self.assertEqual(adaptive_cache_ttl(
            "api.sarb_macro", 3600, metric_db_path=self.metrics, env=APPROVED,
        ), 3600)
        for _ in range(19):
            self.submit("api.sarb_macro", "failed")
        self.assertEqual(adaptive_cache_ttl(
            "api.sarb_macro", 3600, metric_db_path=self.metrics, env=APPROVED,
        ), 3600)
        self.submit("api.sarb_macro", "ok")
        self.assertEqual(adaptive_cache_ttl(
            "api.sarb_macro", 3600, max_seconds=7200,
            metric_db_path=self.metrics, env=APPROVED,
        ), 7200)
        with self.assertRaises(ValueError):
            adaptive_cache_ttl(
                "auth.login", 3600, metric_db_path=self.metrics, env=APPROVED,
            )
        self.assertEqual(adaptive_cache_ttl(
            "api.sarb_macro", 3600, metric_db_path=self.metrics,
            env={**APPROVED, "KHULA_TELEMETRY_POLICY_APPROVED": "0"},
        ), 3600)

    def test_shortcuts_aggregate_only_and_never_prioritize_privileged(self):
        for _ in range(12):
            self.submit("nav.mentor")
        for _ in range(8):
            self.submit("nav.payments")
        for _ in range(50):
            self.submit("nav.membership_approvals")
        self.assertEqual(
            popular_shortcuts(metric_db_path=self.metrics, env=APPROVED),
            ["mentor", "payments", "dashboard"],
        )
        self.assertFalse(
            popular_shortcuts(metric_db_path=self.metrics, env={
                **APPROVED, "KHULA_TELEMETRY_ENABLED": "0",
            }),
        )

    def test_storage_failure_degrades_without_affecting_user_work(self):
        self.assertFalse(
            record("auth.login", consent=True, env=APPROVED,
                   db_path=Path(self.temp.name), now=self.now)
        )

    def test_provider_timer_does_not_swallow_failures(self):
        with self.assertRaisesRegex(RuntimeError, "provider failed"):
            with timed("api.mentor"):
                raise RuntimeError("provider failed")
        with self.assertRaises(ValueError):
            with timed("owner.setup"):
                pass


if __name__ == "__main__":
    unittest.main()
