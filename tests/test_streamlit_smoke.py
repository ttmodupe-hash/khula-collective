"""Exercise the real Streamlit entrypoint, not only imported helper functions."""
import os
import tempfile
import unittest
from pathlib import Path
import sqlite3

import khula_pages1
import khula_utils
from khula_security import hash_password
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
                    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=25).run()
                    self.assertEqual(
                        len(at.exception), 0,
                        "Public landing should never render a Python exception",
                    )
                    self.assertTrue(Path(path).exists())
                    self.assertTrue(any("Username" in w.label for w in at.text_input))
                    self.assertTrue(any("Password" in w.label for w in at.text_input))
                    self.assertFalse(at.session_state["authenticated"])

                    # Regression for the literal "None" and raw HTML-only card
                    # seen on the deployed production screenshot.
                    self.assertFalse(
                        any(str(w.value).strip() == "None" for w in at.markdown),
                        "Do not render the None return of load_css().",
                    )
                    self.assertTrue(
                        any("Welcome back" in str(w.value) for w in at.get("subheader")),
                        "The member sign-in card should render.",
                    )
                    self.assertTrue(
                        any("New to Khula?" in str(w.value) for w in at.get("subheader")),
                        "The prospective member section should render.",
                    )


    def test_login_uses_native_responsive_columns_not_raw_html_wrappers(self):
        import inspect
        source = inspect.getsource(khula_pages1.render_login)
        self.assertIn("st.columns([1, 2.2, 1]", source)
        self.assertIn("with main_col:", source)
        self.assertIn("with st.container(border=True):", source)
        self.assertNotIn("<div class='login-container'>", source)
        self.assertNotIn("<div class='login-card'>", source)
        self.assertNotIn("st.markdown(load_css", source)

    @patch("khula_sarb.fetch_sarb_indicators")
    def test_closed_onboarding_still_renders_a_calm_sign_in(self, sarb):
        sarb.return_value = {
            "data": [], "retrieved_at": "2026-10-27T04:00:00+00:00",
            "source_url": "https://custom.resbank.co.za/SarbWebApi/WebIndicators/HomePageRates",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "closed.db")
            with patch.dict(os.environ, {
                "KHULA_DEMO_MODE": "0",
                "KHULA_PRODUCTION": "0",
                "RAILWAY_ENVIRONMENT_NAME": "production",
                "KHULA_DB_PATH": path,
                "KHULA_BOOTSTRAP_ADMIN_USER": "",
                "KHULA_BOOTSTRAP_ADMIN_PASSWORD": "",
                "KHULA_PRIVACY_NOTICE_APPROVED": "0",
            }):
                with patch.object(khula_config, "DB_PATH", path):
                    at = AppTest.from_file(
                        str(Path(__file__).resolve().parents[1] / "app.py"),
                        default_timeout=25,
                    ).run()
                    self.assertEqual(len(at.exception), 0)
                    self.assertTrue(any(w.label == "Username" for w in at.text_input))
                    self.assertTrue(any(w.label == "Password" for w in at.text_input))
                    self.assertFalse(any(
                        "Submit membership request" in w.label for w in list(at.button)
                    ))
                    self.assertFalse(any(
                        str(w.value).strip() == "None" for w in at.markdown
                    ))

    @patch("khula_sarb.fetch_sarb_indicators")
    def test_real_member_can_sign_in_and_open_dashboard(self, sarb):
        sarb.return_value = {
            "data": [{
                "code": "MMRD002A", "name": "SARB policy rate",
                "value": 7, "as_of": "2026-10-01", "units": "%",
                "days_old": 26, "stale": False, "source": "South African Reserve Bank",
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
                with patch.object(khula_config, "DB_PATH", path), \
                     patch.object(khula_utils, "DB_PATH", path), \
                     patch.object(khula_pages1, "DB_PATH", path):
                    khula_config.init_database()
                    with sqlite3.connect(path) as conn:
                        conn.execute(
                            "INSERT INTO Users (username,password_hash,full_name,email,"
                            "role,is_active,monthly_contribution) "
                            "VALUES (?,?,?,?,'member',1,300)",
                            ("pilotmember", hash_password("UniquePilotMemberPass2026!"),
                             "Real-Pilot Test Member", "pilot@example.invalid"),
                        )
                    at = AppTest.from_file(
                        str(Path(__file__).resolve().parents[1] / "app.py"),
                        default_timeout=30,
                    ).run()
                    self.assertEqual(len(at.exception), 0)
                    username = next(w for w in at.text_input if w.label == "Username")
                    password = next(w for w in at.text_input if w.label == "Password")
                    username.set_value("pilotmember")
                    password.set_value("UniquePilotMemberPass2026!")
                    candidates = list(at.button) + list(at.get("form_submit_button"))
                    sign_in = next((w for w in candidates if "Sign In" in w.label), None)
                    self.assertIsNotNone(
                        sign_in,
                        "No login submit button found. Visible controls: "
                        + repr([w.label for w in candidates]),
                    )
                    sign_in.click()
                    at.run()
                    self.assertEqual(len(at.exception), 0)
                    self.assertTrue(at.session_state["authenticated"])
                    self.assertEqual(at.session_state["role"], "member")


if __name__ == "__main__":
    unittest.main()
