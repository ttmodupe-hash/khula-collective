"""Exercise the real Streamlit entrypoint, not only imported helper functions."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import khula_config
from streamlit.testing.v1 import AppTest


class StreamlitPilotSmokeTests(unittest.TestCase):
    @patch("khula_sarb.fetch_sarb_indicators")
    def test_public_login_landing_renders_without_demo_accounts(self, sarb):
        sarb.return_value = {
            "data": [{
                "code": "MMRD002A", "name": "SARB policy rate",
                "value": 7, "as_of": "2026-10-01", "units": "%",
                "days_old": 26, "stale": False,
                "source": "South African Reserve Bank",
            }],
            "retrieved_at": "2026-10-27T01:00:00+00:00",
            "source_url": "https://custom.resbank.co.za/SarbWebApi/WebIndicators/HomePageRates",
        }
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / "pilot.db")
            with patch.dict(os.environ, {
                "KHULA_DEMO_MODE": "0", "KHULA_PRODUCTION": "0",
                "KHULA_DB_PATH": path, "KHULA_BOOTSTRAP_ADMIN_USER": "",
                "KHULA_BOOTSTRAP_ADMIN_PASSWORD": "",
            }):
                with patch.object(khula_config, "DB_PATH", path):
                    at = AppTest.from_file("app.py", default_timeout=25).run()
                    self.assertEqual(
                        len(at.exception), 0,
                        "Public landing should never render a Python exception",
                    )
                    self.assertTrue(Path(path).exists())
                    self.assertTrue(any("Username" in w.label for w in at.text_input))
                    self.assertTrue(any("Password" in w.label for w in at.text_input))
                    self.assertFalse(at.session_state["authenticated"])


if __name__ == "__main__":
    unittest.main()
