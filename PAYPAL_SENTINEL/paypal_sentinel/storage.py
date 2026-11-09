from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("DATABASE_PATH", "./paypal_sentinel.sqlite3")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        with self.lock:
            self.conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY, payload TEXT NOT NULL, decision TEXT NOT NULL,
                    intent_hash TEXT NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    plan_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL,
                    expires_at INTEGER NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, order_id TEXT UNIQUE,
                    amount TEXT NOT NULL, currency TEXT NOT NULL, state TEXT NOT NULL,
                    created_at INTEGER NOT NULL, capture_id TEXT
                );
            """)

    def save_plan(self, payload: dict[str, Any], ttl: int = 600) -> str:
        plan_id = secrets.token_urlsafe(18)
        now = int(time.time())
        with self.lock:
            self.conn.execute(
                "INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?)",
                (plan_id, json.dumps(payload), payload["decision"], payload["intent_hash"], now, now + ttl),
            )
        return plan_id

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.conn.execute(
                "SELECT payload, expires_at FROM plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
        if not row or row["expires_at"] < int(time.time()):
            return None
        return json.loads(row["payload"])

    def issue_approval(self, plan_id: str, ttl: int = 120) -> str:
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode()).hexdigest()
        now = int(time.time())
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO approvals VALUES (?, ?, ?, 0)",
                (plan_id, digest, now + ttl),
            )
        return token

    def consume_approval(self, plan_id: str, token: str) -> bool:
        digest = hashlib.sha256(token.encode()).hexdigest()
        now = int(time.time())
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                row = self.conn.execute(
                    "SELECT token_hash, expires_at, consumed FROM approvals WHERE plan_id=?",
                    (plan_id,),
                ).fetchone()
                valid = bool(
                    row and row["consumed"] == 0 and row["expires_at"] >= now
                    and secrets.compare_digest(row["token_hash"], digest)
                )
                if valid:
                    self.conn.execute(
                        "UPDATE approvals SET consumed=1 WHERE plan_id=? AND consumed=0",
                        (plan_id,),
                    )
                self.conn.execute("COMMIT")
                return valid
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def reserve_payment(self, plan_id: str, amount: str, currency: str, daily_limit: str) -> str:
        payment_id = secrets.token_urlsafe(18)
        now = int(time.time())
        day_start = now - (now % 86400)
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                row = self.conn.execute(
                    "SELECT COALESCE(SUM(CAST(amount AS REAL)), 0) AS total FROM payments "
                    "WHERE created_at>=? AND state IN ('CREATING','CREATED','COMPLETED')",
                    (day_start,),
                ).fetchone()
                if float(row["total"]) + float(amount) > float(daily_limit):
                    raise ValueError("daily spend limit exceeded")
                self.conn.execute(
                    "INSERT INTO payments VALUES (?, ?, NULL, ?, ?, 'CREATING', ?, NULL)",
                    (payment_id, plan_id, amount, currency, now),
                )
                self.conn.execute("COMMIT")
                return payment_id
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def set_order(self, payment_id: str, order_id: str) -> None:
        with self.lock:
            self.conn.execute(
                "UPDATE payments SET order_id=?, state='CREATED' WHERE payment_id=? AND state='CREATING'",
                (order_id, payment_id),
            )

    def fail_payment(self, payment_id: str) -> None:
        with self.lock:
            self.conn.execute(
                "UPDATE payments SET state='FAILED' WHERE payment_id=? AND state='CREATING'",
                (payment_id,),
            )

    def get_payment(self, order_id: str) -> dict[str, Any] | None:
        with self.lock:
            row = self.conn.execute(
                "SELECT * FROM payments WHERE order_id=?", (order_id,)
            ).fetchone()
        return dict(row) if row else None

    def complete_payment(self, order_id: str, capture_id: str) -> None:
        with self.lock:
            self.conn.execute(
                "UPDATE payments SET state='COMPLETED', capture_id=? WHERE order_id=? AND state='CREATED'",
                (capture_id, order_id),
            )
