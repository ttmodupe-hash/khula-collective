import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from khula_bank_import import BankImportError, parse_bank_csv, import_club_statement, unallocated_bank_credits
import khula_config


class BankEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "khula.db")
        self.old_path = khula_config.DB_PATH
        khula_config.DB_PATH = self.db
        khula_config.init_database()
        with sqlite3.connect(self.db) as conn:
            conn.execute(
                "INSERT INTO Users(username,password_hash,full_name,role,is_active) "
                "VALUES ('admin-test','hash','Test Admin','admin',1)"
            )
            self.admin = conn.execute("SELECT user_id FROM Users WHERE username='admin-test'").fetchone()[0]
        self.env = patch.dict(os.environ, {"KHULA_BANK_IMPORT_HMAC_KEY":"TestSecretForBankImportIsLongerThan32Chars"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        khula_config.DB_PATH = self.old_path
        self.tmp.cleanup()

    def test_parse_credit_debit_and_masks_reference(self):
        csv = (f"Date,Amount,Reference,Description\n"
               f"{date.today().isoformat()},500.00,ABCD1234,deposit\n"
               f"{date.today().isoformat()},-50.00,COST9988,bank charge\n").encode()
        records = parse_bank_csv(csv)
        self.assertEqual(len(records),2)
        summary = import_club_statement(self.db,self.admin,csv,source_checked=True)
        self.assertEqual(summary["new_rows"],2)
        available = unallocated_bank_credits(self.db,self.admin)
        self.assertEqual(len(available),1)
        self.assertIn("1234",available[0][3])
        with sqlite3.connect(self.db) as conn:
            contents = str(conn.execute(
                "SELECT tx_date,amount_zar,reference_mask FROM Bank_Statement_Rows"
            ).fetchall())
        self.assertNotIn("ABCD1234", contents)
        self.assertNotIn("deposit", contents)

    def test_reupload_does_not_duplicate_transactions(self):
        csv=(f"Date,Amount,Reference\n{date.today().isoformat()},250.00,REF0042\n").encode()
        import_club_statement(self.db,self.admin,csv,source_checked=True)
        with self.assertRaises(BankImportError):
            import_club_statement(self.db,self.admin,csv,source_checked=True)

    def test_import_is_permissioned(self):
        csv=(f"Date,Amount,Reference\n{date.today().isoformat()},500.00,REF0042\n").encode()
        with self.assertRaises(PermissionError):
            import_club_statement(self.db,999,csv,source_checked=True)
        with self.assertRaises(BankImportError):
            import_club_statement(self.db,self.admin,csv,source_checked=False)

    def test_invalid_layout_and_zero_are_rejected(self):
        with self.assertRaises(BankImportError):
            parse_bank_csv(b"SomeOtherColumn,Value\na,10")
        with self.assertRaises(BankImportError):
            parse_bank_csv(b"Date,Amount,Reference\n2026-01-01,0,ANY")

if __name__=="__main__":
    unittest.main()
