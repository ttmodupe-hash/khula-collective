"""Synthetic bounded backoff acceptance; no real network, bank or member data."""
import unittest
from unittest.mock import patch

import requests

from khula_resilience import (
    ProviderBackoff, _clear_test_state, public_request_guard,
)
from khula_sarb import SarbDataError, fetch_sarb_indicators


class PublicProviderBackoffTests(unittest.TestCase):
    def setUp(self):
        _clear_test_state()
        self.addCleanup(_clear_test_state)
        self.ticks = [100.0]
        self.clock = lambda: self.ticks[0]

    def fail_once(self, provider):
        with self.assertRaises(TimeoutError):
            with public_request_guard(provider, clock=self.clock):
                raise TimeoutError("synthetic upstream timeout")

    def test_three_failures_pause_but_do_not_hide_original_errors(self):
        for n in range(3):
            self.fail_once("sarb_macro")
            self.ticks[0] += 1
        with self.assertRaises(ProviderBackoff):
            with public_request_guard("sarb_macro", clock=self.clock):
                self.fail("No external request allowed during cooldown")
        self.ticks[0] += 16
        with public_request_guard("sarb_macro", clock=self.clock):
            pass
        # Success resets the budget.
        self.fail_once("sarb_macro")
        with public_request_guard("sarb_macro", clock=self.clock):
            pass

    def test_provider_isolation_and_stale_failure_decay(self):
        for _ in range(3):
            self.fail_once("licensed_market")
            self.ticks[0] += 1
        with public_request_guard("sarb_markets", clock=self.clock):
            pass
        self.ticks[0] += 62
        # The old streak falls outside the rolling one-minute window.
        self.fail_once("licensed_market")
        with public_request_guard("licensed_market", clock=self.clock):
            pass

    def test_rejects_unknown_source_without_executing_body(self):
        with self.assertRaises(ValueError):
            with public_request_guard("auth.login", clock=self.clock):
                self.fail("Should not enter restricted provider code")

    @patch("khula_sarb.requests.get", side_effect=requests.Timeout("synthetic"))
    def test_existing_sarb_error_and_no_fabricated_data_on_cooldown(self, get):
        for _ in range(4):
            with self.assertRaises(SarbDataError):
                fetch_sarb_indicators()
        self.assertEqual(get.call_count, 3)


if __name__ == "__main__":
    unittest.main()
