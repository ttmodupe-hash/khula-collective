import unittest
from decimal import Decimal
from datetime import date

from khula_advisory_core import (
    available_savings, affordable_units, illustrative_allocation,
    allocation_amounts, no_growth_projection, contribution_progress, zar,
    bank_snapshot_fresh,
)


class AdvisorySafetyTests(unittest.TestCase):
    def test_stale_or_future_bank_snapshot_blocks_affordability(self):
        today = date(2026, 10, 26)
        self.assertTrue(bank_snapshot_fresh("2026-10-20", today=today))
        self.assertFalse(bank_snapshot_fresh("2026-10-01", today=today))
        self.assertFalse(bank_snapshot_fresh("2026-11-01", today=today))
        self.assertFalse(bank_snapshot_fresh("unknown", today=today))

    def test_missing_bank_record_must_not_estimate_cash(self):
        self.assertIsNone(available_savings(None))

    def test_reserved_money_not_investable(self):
        self.assertEqual(available_savings("12000", "5000", "2500"), Decimal("4500.00"))
        self.assertEqual(available_savings("1200", "2000"), Decimal("0.00"))

    def test_invalid_funds_rejected(self):
        for value in ("NaN", "Infinity", -5):
            with self.assertRaises(ValueError):
                available_savings(value)

    def test_no_predicted_market_growth(self):
        self.assertEqual(no_growth_projection(1000, 200, 12), Decimal("3400.00"))

    def test_model_allocations_sum_to_one_hundred(self):
        for risk in ("conservative", "moderate", "aggressive"):
            for years in (1, 3, 5, 10):
                buckets = illustrative_allocation(risk, years)
                self.assertEqual(sum(buckets.values()), 100)
                self.assertTrue(all(0 <= v <= 100 for v in buckets.values()))
                amounts = allocation_amounts(Decimal("1234.56"), buckets)
                self.assertEqual(sum(amounts.values()), Decimal("1234.56"))

    def test_short_horizon_avoids_equity_in_model(self):
        self.assertEqual(illustrative_allocation("aggressive", 1)["diversified_equity"], 0)

    def test_affordability_conservatively_capped(self):
        self.assertIsNone(affordable_units(None, 50))
        self.assertEqual(affordable_units(1000, 50, 10), 2)
        with self.assertRaises(ValueError):
            affordable_units(1000, 0)

    def test_progress(self):
        p = contribution_progress(200, 500)
        self.assertEqual(p["shortfall"], Decimal("300.00"))
        self.assertEqual(p["completion_pct"], Decimal("40.00"))


if __name__ == "__main__":
    unittest.main()
