import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import khula_config as config
from khula_governance import cast_vote, close_expired_proposals


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "app.db")
        self.previous = config.DB_PATH
        config.DB_PATH = self.path
        config.init_database()
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO Users (username,password_hash,full_name,role,is_active) "
                "VALUES ('a','hash','Member A','member',1)"
            )
            self.uid = conn.execute("SELECT user_id FROM Users WHERE username='a'").fetchone()[0]
            future = (datetime.now() + timedelta(days=1)).isoformat()
            conn.execute(
                "INSERT INTO Proposals (title,status,closes_at,votes_for,votes_against) "
                "VALUES ('Test Vote','open',?,0,0)", (future,)
            )
            self.pid = conn.execute("SELECT proposal_id FROM Proposals").fetchone()[0]

    def tearDown(self):
        config.DB_PATH = self.previous
        self.tmp.cleanup()

    def test_one_vote_and_closed_expiry(self):
        self.assertTrue(cast_vote(self.path, self.uid, self.pid, "for"))
        with self.assertRaises(ValueError):
            cast_vote(self.path, self.uid, self.pid, "against")
        with sqlite3.connect(self.path) as conn:
            tally = conn.execute(
                "SELECT votes_for,votes_against FROM Proposals WHERE proposal_id=?", (self.pid,)
            ).fetchone()
        self.assertEqual(tally, (1, 0))
        close_expired_proposals(self.path, datetime.now() + timedelta(days=2))
        with self.assertRaises(ValueError):
            cast_vote(self.path, self.uid, self.pid, "for", datetime.now() + timedelta(days=2))

    def test_invalid_vote_rejected(self):
        with self.assertRaises(ValueError):
            cast_vote(self.path, self.uid, self.pid, "approve_and_trade")


if __name__ == "__main__":
    unittest.main()
