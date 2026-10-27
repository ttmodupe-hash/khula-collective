"""Backup safety tests use generated local data; production is never opened."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.ledger_backup import create_snapshot, verify_restore, file_digest


class LedgerBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "source.sqlite3"
        self.out = self.root / "test.khula-backup"
        self.conn = sqlite3.connect(self.db)
        self.conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA wal_autocheckpoint=0;
            CREATE TABLE Users(user_id INTEGER PRIMARY KEY, label TEXT);
            CREATE TABLE Monthly_Contributions(
                id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES Users(user_id), cents INTEGER);
            CREATE TABLE Admin_Actions(id INTEGER PRIMARY KEY, action TEXT);
            INSERT INTO Users VALUES(1, 'SYNTHETIC PRIVATE ROW');
            INSERT INTO Monthly_Contributions VALUES(1, 1, 12345);
            INSERT INTO Admin_Actions VALUES(1, 'synthetic');
        """)

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_committed_wal_captured_and_restore_is_isolated(self):
        self.assertTrue(Path(str(self.db) + "-wal").exists())
        manifest = create_snapshot(self.db, self.out)
        self.assertEqual(manifest["checks"]["table_counts"]["Monthly_Contributions"], 1)
        report = verify_restore(self.out, self.root)
        self.assertEqual(report["status"], "isolated_sqlite_restore_verified")
        self.assertEqual(report["application_acceptance"], "not_run")
        self.assertEqual(report["independent_storage"], "not_verified")
        self.assertEqual(list(self.root.glob("khula-isolated-restore-*")), [])
        self.assertEqual(self.conn.execute("SELECT cents FROM Monthly_Contributions").fetchone(), (12345,))
        self.assertNotIn("SYNTHETIC PRIVATE ROW", (self.out / "manifest.json").read_text())
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o700)
        for name in ("manifest.json", "ledger.sqlite3"):
            self.assertEqual((self.out / name).stat().st_mode & 0o777, 0o600)

    def test_uncommitted_rows_are_not_in_snapshot(self):
        self.conn.execute("INSERT INTO Users VALUES(2, 'UNCOMMITTED')")
        manifest = create_snapshot(self.db, self.out)
        self.assertEqual(manifest["checks"]["table_counts"]["Users"], 1)
        self.conn.rollback()

    def test_existing_destination_never_overwritten_or_deleted(self):
        create_snapshot(self.db, self.out)
        before = file_digest(self.out / "ledger.sqlite3")
        with self.assertRaises(FileExistsError):
            create_snapshot(self.db, self.out)
        self.assertEqual(file_digest(self.out / "ledger.sqlite3"), before)
        with self.assertRaises(ValueError):
            create_snapshot(self.db, self.db)
        self.assertTrue(self.db.exists())

    def test_missing_source_does_not_create_empty_database(self):
        missing = self.root / "missing.sqlite3"
        with self.assertRaises(FileNotFoundError):
            create_snapshot(missing, self.out)
        self.assertFalse(missing.exists())
        self.assertFalse(self.out.exists())

    def test_corrupt_backup_rejected(self):
        create_snapshot(self.db, self.out)
        with (self.out / "ledger.sqlite3").open("ab") as handle:
            handle.write(b"corrupt")
        with self.assertRaises(ValueError):
            verify_restore(self.out, self.root)

    def test_altered_manifest_counts_rejected_and_copy_cleaned(self):
        create_snapshot(self.db, self.out)
        path = self.out / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["checks"]["table_counts"]["Users"] = 999
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            verify_restore(self.out, self.root)
        self.assertEqual(list(self.root.glob("khula-isolated-restore-*")), [])

    def test_invalid_ledger_and_foreign_keys_fail_without_partial_backup(self):
        self.conn.execute("INSERT INTO Monthly_Contributions VALUES(2, 999, 1)")
        self.conn.commit()
        with self.assertRaises(ValueError):
            create_snapshot(self.db, self.out)
        self.assertFalse(self.out.exists())
        wrong = self.root / "wrong.sqlite3"
        with sqlite3.connect(wrong) as conn:
            conn.execute("CREATE TABLE unrelated(x)")
        with self.assertRaises(ValueError):
            create_snapshot(wrong, self.out)
        self.assertFalse(self.out.exists())

    def test_symlink_destinations_and_files_are_rejected(self):
        self.out.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            create_snapshot(self.db, self.out)
        self.out.unlink()
        create_snapshot(self.db, self.out)
        (self.out / "ledger.sqlite3").unlink()
        (self.out / "ledger.sqlite3").symlink_to(self.db)
        with self.assertRaises(ValueError):
            verify_restore(self.out, self.root)
        self.assertTrue(self.db.exists())

    def test_unexpected_wal_rejected(self):
        create_snapshot(self.db, self.out)
        (self.out / "ledger.sqlite3-wal").write_bytes(b"untrusted")
        with self.assertRaises(ValueError):
            verify_restore(self.out, self.root)

    def test_source_and_original_snapshot_remain_unchanged(self):
        create_snapshot(self.db, self.out)
        original = file_digest(self.out / "ledger.sqlite3")
        self.conn.execute("UPDATE Monthly_Contributions SET cents=56789")
        self.conn.commit()
        verify_restore(self.out, self.root)
        self.assertEqual(file_digest(self.out / "ledger.sqlite3"), original)
        self.assertEqual(self.conn.execute("SELECT cents FROM Monthly_Contributions").fetchone(), (56789,))


if __name__ == "__main__":
    unittest.main()
