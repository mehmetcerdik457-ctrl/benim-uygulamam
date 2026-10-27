"""Durable, fail-closed Copilot dispatch journal. No network access."""
import json
import os
import sqlite3
import stat
from pathlib import Path

class DispatchJournal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise RuntimeError("JOURNAL_SYMLINK_DENIED")
        if self.path.exists() and (self.path.stat().st_mode & 0o077):
            raise RuntimeError("JOURNAL_PERMISSIONS_DENIED")
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise RuntimeError("JOURNAL_NOT_REGULAR")
            if os.fstat(fd).st_mode & 0o077:
                raise RuntimeError("JOURNAL_PERMISSIONS_DENIED")
        finally:
            os.close(fd)
        self.db = sqlite3.connect(str(self.path), isolation_level=None, timeout=15)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS batches(batch TEXT PRIMARY KEY)")
        self.db.execute("""CREATE TABLE IF NOT EXISTS submissions(
            batch TEXT NOT NULL, role TEXT NOT NULL, issue INTEGER NOT NULL,
            state TEXT NOT NULL, task_id TEXT, receipt TEXT,
            PRIMARY KEY(batch,role))""")

    def claim_batch(self, batch):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("INSERT INTO batches(batch) VALUES(?)", (batch,))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def reserve(self, batch, role, issue):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("INSERT INTO submissions(batch,role,issue,state) VALUES(?,?,?,?)",
                            (batch, role, issue, "PENDING"))
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def confirmed(self, batch, role, receipt):
        if not isinstance(receipt, dict) or not receipt.get("task_id"):
            raise ValueError("MISSING_TASK_ID")
        self.db.execute("UPDATE submissions SET state=?,task_id=?,receipt=? WHERE batch=? AND role=? AND state=?",
                        ("CONFIRMED", str(receipt["task_id"]), json.dumps(receipt), batch, role, "PENDING"))
        if self.db.execute("SELECT changes()").fetchone()[0] != 1:
            raise RuntimeError("JOURNAL_STATE_CONFLICT")

    def entries(self, batch):
        return [{"role":r,"issue":i,"state":s,"task_id":t} for r,i,s,t in
                self.db.execute("SELECT role,issue,state,task_id FROM submissions WHERE batch=? ORDER BY rowid", (batch,))]

    def close(self):
        self.db.close()
