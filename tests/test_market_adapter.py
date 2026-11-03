import os
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from khula_market_data import fetch_quote, fetch_fx_rate, MarketDataError


class MarketAdapterTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "KHULA_MARKET_DATA_PROVIDER": "twelvedata",
            "KHULA_MARKET_DATA_LICENSE_APPROVED": "1",
            "KHULA_TWELVEDATA_API_KEY": "TEST_KEY_NOT_REAL",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()

    @patch("khula_market_data.requests.get")
    def test_quote_has_timestamp_currency_source(self, get):
        r = Mock()
        r.json.return_value = {
            "symbol": "AAPL", "name": "Apple", "close": "100.21", "currency": "USD",
            "exchange": "NASDAQ", "timestamp": int(datetime.now(timezone.utc).timestamp())
        }
        get.return_value = r
        result = fetch_quote("AAPL")
        self.assertEqual(result["source"], "Twelve Data")
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(str(result["price"]), "100.21")
        self.assertIn(str(datetime.now(timezone.utc).year), result["as_of"])

    @patch("khula_market_data.requests.get")
    def test_original_jse_symbol_is_translated_for_provider(self, get):
        r = Mock()
        r.json.return_value = {
            "symbol": "SHP", "close": "250.0", "currency": "ZAR",
            "exchange": "JSE", "timestamp": int(datetime.now(timezone.utc).timestamp())
        }
        get.return_value = r
        result = fetch_quote("SHP.JO")
        self.assertEqual(result["symbol"], "SHP.JO")
        kwargs = get.call_args.kwargs
        self.assertEqual(kwargs["params"]["symbol"], "SHP")
        self.assertEqual(kwargs["params"]["exchange"], "JSE")

    @patch("khula_market_data.requests.get")
    def test_stale_quote_fails_closed(self, get):
        r = Mock()
        r.json.return_value = {
            "close": "10", "currency": "ZAR", "timestamp": 1760000000
        }
        get.return_value = r
        with self.assertRaises(MarketDataError):
            fetch_quote("SHP.JO")

    @patch("khula_market_data.requests.get")
    def test_no_invented_price_on_failure(self, get):
        r = Mock()
        r.json.return_value = {"status": "error", "code": 429, "message": "rate limited"}
        get.return_value = r
        with self.assertRaises(MarketDataError):
            fetch_quote("AAPL")

    @patch("khula_market_data.requests.get")
    def test_recent_fx_rate(self, get):
        r = Mock()
        r.json.return_value = {"rate": 18.2, "timestamp": int(datetime.now(timezone.utc).timestamp())}
        get.return_value = r
        self.assertEqual(str(fetch_fx_rate("USD", "ZAR")["rate"]), "18.2")

    def test_not_licensed_is_disabled(self):
        os.environ.pop("KHULA_MARKET_DATA_LICENSE_APPROVED", None)
        with self.assertRaises(MarketDataError):
            fetch_quote("MSFT")

    def test_reject_symbol_injection(self):
        with self.assertRaises(MarketDataError):
            fetch_quote("AAPL&apikey=secret")


if __name__ == "__main__":
    unittest.main()
