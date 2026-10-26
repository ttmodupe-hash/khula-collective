"""Atomic club voting with expiry and one-vote-per-member enforcement."""
import sqlite3
from datetime import datetime, timezone


def close_expired_proposals(db_path, now=None):
    when = (now or datetime.now(timezone.utc)).replace(tzinfo=None).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE Proposals SET status='closed' "
            "WHERE status='open' AND closes_at IS NOT NULL AND closes_at<=?",
            (when,),
        )


def cast_vote(db_path, user_id, proposal_id, choice, now=None):
    if choice not in ("for", "against"):
        raise ValueError("Invalid vote.")
    timestamp = (now or datetime.now(timezone.utc)).replace(tzinfo=None).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        active = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND is_active=1",
            (user_id,),
        ).fetchone()
        if not active:
            raise PermissionError("Active member required.")
        proposal = conn.execute(
            "SELECT status,closes_at FROM Proposals WHERE proposal_id=?",
            (proposal_id,),
        ).fetchone()
        if not proposal or proposal[0] != "open" or not proposal[1] or proposal[1] <= timestamp:
            raise ValueError("Voting is closed.")
        existing = conn.execute(
            "SELECT 1 FROM Votes WHERE user_id=? AND proposal_id=?",
            (user_id, proposal_id),
        ).fetchone()
        if existing:
            raise ValueError("You have already voted.")
        conn.execute(
            "INSERT INTO Votes (user_id,proposal_id,vote,voted_at) VALUES (?,?,?,?)",
            (user_id, proposal_id, choice, timestamp),
        )
        column = "votes_for" if choice == "for" else "votes_against"
        conn.execute(
            f"UPDATE Proposals SET {column} = {column} + 1 WHERE proposal_id=?",
            (proposal_id,),
        )
    return True
