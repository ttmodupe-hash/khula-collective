import sqlite3
import tempfile
import unittest
from pathlib import Path
from scripts.legacy_inventory import inspect_legacy_database


class LegacyInventoryTests(unittest.TestCase):
    def test_read_only_inventory_does_not_disclose_member_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.db"
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TABLE Users (user_id INTEGER PRIMARY KEY, full_name TEXT, id_number TEXT)")
                conn.execute(
                    "INSERT INTO Users (user_id,full_name,id_number) VALUES (1,?,?)",
                    ("Private Test Member", "9001011234088")
                )
            result = inspect_legacy_database(path)
            self.assertEqual(result["tables"]["Users"]["row_count"], 1)
            self.assertTrue(result["tables"]["Users"]["exists"])
            rendered = str(result)
            self.assertNotIn("Private Test Member", rendered)
            self.assertNotIn("9001011234088", rendered)

    def test_does_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "missing.db"
            with self.assertRaises(FileNotFoundError):
                inspect_legacy_database(path)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
