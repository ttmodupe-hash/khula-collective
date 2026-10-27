import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class SourceContracts(unittest.TestCase):
    def test_all_app_python_files_parse(self):
        for path in sorted(ROOT.glob("*.py")):
            with self.subTest(file=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_startup_does_not_call_missing_demo_seed(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("seed_demo_data()", source)
        self.assertIn("bootstrap_admin(DB_PATH)", source)

    def test_no_synthetic_bank_connection_in_active_app(self):
        content = (ROOT / "khula_utils.py").read_text(encoding="utf-8")
        self.assertNotIn("simulated_fnb_token_", content)

    def test_payment_page_does_not_self_mark_paid(self):
        content = (ROOT / "khula_pages1.py").read_text(encoding="utf-8")
        self.assertNotIn("Confirm Payment", content)
        self.assertIn("submit_payment_claim(", content)


if __name__ == "__main__":
    unittest.main()
