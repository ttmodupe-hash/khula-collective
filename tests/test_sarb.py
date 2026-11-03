import unittest
from datetime import date
from unittest.mock import Mock, patch
from decimal import Decimal

from khula_sarb import normalise_indicators, fetch_sarb_indicators, SarbDataError


class SarbTests(unittest.TestCase):
    def test_date_and_source_are_not_inferred(self):
        data = normalise_indicators([
            {"Name":"SARB Policy Rate", "TimeseriesCode":"MMRD002A",
             "Value":7.0,"Date":"2026-10-23"},
            {"TimeseriesCode":"EXCX135D","Value":17.42,"Date":"2026-10-22"},
            {"TimeseriesCode":"MMRD000A","Value":"NaN","Date":"2026-10-22"},
        ], today=date(2026, 10, 26))
        self.assertEqual(len(data),2)
        self.assertTrue(all(d["source"]=="South African Reserve Bank" for d in data))
        self.assertTrue(all(not d["stale"] for d in data))

    def test_stale_rates_are_not_called_live(self):
        r=normalise_indicators([{"TimeseriesCode":"EXCX135D",
                                "Value":16.3,"Date":"2026-08-07"}], today=date(2026,10,26))
        self.assertTrue(r[0]["stale"])
        self.assertEqual(r[0]["as_of"],"2026-08-07")

    def test_missing_data_fails_closed(self):
        with self.assertRaises(SarbDataError):
            normalise_indicators([{"TimeseriesCode":"JSE_FAKE", "Value":100, "Date":"2026-10-26"}])

    @patch("khula_sarb.requests.get")
    def test_official_endpoint_parsed(self,get):
        response=Mock()
        response.content=b'[]'
        response.json.return_value=[{"TimeseriesCode":"MMRD002A","Value":7,"Date":"2026-10-23"}]
        get.return_value=response
        bundle=fetch_sarb_indicators()
        self.assertEqual(bundle["data"][0]["value"],Decimal("7"))
        self.assertIn("resbank.co.za", bundle["source_url"])
        self.assertEqual(get.call_args.kwargs["timeout"],(4,12))

if __name__=="__main__":
    unittest.main()
