import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from khula_public_markets import (
    API_URL, SarbMarketError, normalise_current_market_rates,
    fetch_current_market_rates,
)


class PublicMarketsTests(unittest.TestCase):
    def test_official_dated_data_is_not_an_executable_quote(self):
        data = normalise_current_market_rates([
            {"TimeseriesCode": "MMRD203A", "Value": "6.83", "Date": "2026-10-24"},
            {"TimeseriesCode": "EXCX135D", "Value": "17.25", "Date": "2026-10-24"},
            {"TimeseriesCode": "GDPL203D", "Value": "75000", "Date": "2026-10-23"},
        ], today=date(2026, 10, 27))
        self.assertEqual(len(data), 3)
        self.assertEqual({r["source"] for r in data}, {"South African Reserve Bank"})
        self.assertTrue(all(not r["stale"] for r in data))
        self.assertEqual(next(r["value"] for r in data if r["code"] == "MMRD203A"), Decimal("6.83"))

    def test_stale_exchange_rate_is_not_called_live(self):
        values = normalise_current_market_rates([
            {"TimeseriesCode": "EXCX135D", "Value": "16.49", "Date": "2026-08-04"},
            {"TimeseriesCode": "MMRD708A", "Value": "7.795", "Date": "2026-08-03"},
        ], today=date(2026, 10, 27))
        self.assertTrue(all(x["stale"] for x in values))
        self.assertEqual(values[0]["as_of"], "2026-08-03")

    def test_fake_or_invalid_values_rejected(self):
        with self.assertRaises(SarbMarketError):
            normalise_current_market_rates([
                {"TimeseriesCode": "UNTRUSTED_STOCK", "Value": 450, "Date": "2026-10-26"},
            ])
        with self.assertRaises(SarbMarketError):
            normalise_current_market_rates([
                {"TimeseriesCode": "EXCX135D", "Value": "NaN", "Date": "2026-10-26"},
            ])

    @patch("khula_public_markets.requests.get")
    def test_calls_official_source_with_bounded_response(self, get):
        response = Mock()
        response.content = b"[]"
        response.json.return_value = [
            {"TimeseriesCode": "MMRD203A", "Value": 6.83, "Date": "2026-10-26"}
        ]
        get.return_value = response
        value = fetch_current_market_rates()
        self.assertEqual(value["observations"][0]["code"], "MMRD203A")
        self.assertEqual(value["source_url"], API_URL)
        self.assertEqual(get.call_args.args[0], API_URL)
        self.assertEqual(get.call_args.kwargs["timeout"], (4, 12))


if __name__ == "__main__":
    unittest.main()
