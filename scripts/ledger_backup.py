"""Operator-only SQLite snapshots and disposable restore checks.

Standard library only; never imports the app, loads credentials, changes access
rules, uploads a file or replaces a running ledger. Backups contain private data
and MUST be kept in approved encrypted storage outside the repository.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time

FORMAT_VERSION = 1
REQUIRED_TABLES = {"Users", "Monthly_Contributions", "Admin_Actions"}
MAX_SECONDS = 120


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def readonly(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError("An existing SQLite file is required.")
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
    conn.execute("PRAGMA query_only=ON")
    return conn


def inspect_snapshot(path):
    with closing(readonly(path)) as conn:
        deadline = time.monotonic() + MAX_SECONDS
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity verification failed.")
        if conn.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("SQLite foreign-key verification failed.")
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        if not REQUIRED_TABLES.issubset(tables):
            raise ValueError("The expected Khula ledger tables are missing.")
        counts = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            counts[table] = conn.execute("SELECT COUNT(*) FROM " + quoted).fetchone()[0]
        schema = conn.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "ORDER BY type,name,tbl_name"
        ).fetchall()
        return {
            "table_counts": counts,
            "schema_sha256": hashlib.sha256(
                json.dumps(schema, ensure_ascii=True).encode("utf-8")
            ).hexdigest(),
            "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
        }


def create_snapshot(source, destination):
    """Capture committed SQLite state, including WAL, in a new private folder."""
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute()
    if not destination.name.endswith(".khula-backup"):
        raise ValueError("Use a new directory ending in .khula-backup.")
    # Parent must already exist. mkdir must fail for ALL existing destinations,
    # including symlinks, and must occur outside cleanup's ownership scope.
    destination.mkdir(mode=0o700)
    try:
        db = destination / "ledger.sqlite3"
        fd = os.open(db, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        deadline = time.monotonic() + MAX_SECONDS

        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise TimeoutError("Snapshot exceeded its time limit; retry in a quieter period.")

        with closing(readonly(source)) as src, closing(sqlite3.connect(db)) as dst:
            src.backup(dst, pages=256, progress=progress, sleep=0.05)
            # A WAL source's journal setting is copied too. Normalize ONLY the
            # new snapshot so later read-only verification needs no sidecars.
            if dst.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",):
                raise ValueError("Cannot finalize a standalone SQLite snapshot.")
        manifest = {
            "format_version": FORMAT_VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "sqlite_version": sqlite3.sqlite_version,
            "sha256": file_digest(db),
            "size_bytes": db.stat().st_size,
            "checks": inspect_snapshot(db),
        }
        with db.open("rb") as handle:
            os.fsync(handle.fileno())
        manifest_path = destination / "manifest.json"
        fd = os.open(manifest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return manifest
    except BaseException:
        # Only this invocation's new directory is removed on failure.
        shutil.rmtree(destination)
        raise


def verify_restore(snapshot, work_dir=None):
    """Verify a disposable copy; no restore destination can be supplied."""
    snapshot = Path(snapshot)
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise ValueError("Use an existing non-symlink snapshot directory.")
    db, manifest_path = snapshot / "ledger.sqlite3", snapshot / "manifest.json"
    for item in (db, manifest_path):
        if item.is_symlink() or not item.is_file():
            raise ValueError("Snapshot files must be regular files, not symlinks.")
    # Completed snapshots are standalone; unexpected journals are ambiguous.
    if any((snapshot / (db.name + suffix)).exists() for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError("Snapshot contains unexpected SQLite sidecar files.")
    if manifest_path.stat().st_size > 1024 * 1024:
        raise ValueError("Snapshot manifest is too large.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("format_version") != FORMAT_VERSION:
        raise ValueError("Unsupported snapshot manifest format.")
    if db.stat().st_size != manifest.get("size_bytes") or file_digest(db) != manifest.get("sha256"):
        raise ValueError("Snapshot checksum or size does not match its manifest.")
    # No app server or network connection is started in the restore directory.
    with tempfile.TemporaryDirectory(prefix="khula-isolated-restore-", dir=work_dir) as tmp:
        restored = Path(tmp) / "ledger.sqlite3"
        shutil.copyfile(db, restored)
        restored.chmod(0o600)
        if file_digest(restored) != manifest["sha256"]:
            raise ValueError("Isolated copy checksum mismatch.")
        if inspect_snapshot(restored) != manifest.get("checks"):
            raise ValueError("Isolated restore does not match the recorded ledger checks.")
    return {
        "status": "isolated_sqlite_restore_verified",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": manifest["sha256"],
        "application_acceptance": "not_run",
        "independent_storage": "not_verified",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Create a new private SQLite snapshot")
    create.add_argument("--source", required=True)
    create.add_argument("--destination", required=True)
    verify = commands.add_parser("verify", help="Check a disposable restore, then remove it")
    verify.add_argument("--snapshot", required=True)
    verify.add_argument("--work-dir", help="Existing directory on approved encrypted storage")
    args = parser.parse_args()
    try:
        if args.command == "create":
            result = create_snapshot(args.source, args.destination)
            # Do not print paths, table counts or row data to operational logs.
            print(json.dumps({"status": "snapshot_created", "sha256": result["sha256"]}))
        else:
            print(json.dumps(verify_restore(args.snapshot, args.work_dir), sort_keys=True))
    except (ValueError, OSError, sqlite3.Error):
        # SQLite exceptions can include identifiers. Keep console failures generic.
        parser.exit(1, "Backup operation failed; no running ledger was replaced. Check paths, permissions, integrity and manifest privately.\n")


if __name__ == "__main__":
    main()
