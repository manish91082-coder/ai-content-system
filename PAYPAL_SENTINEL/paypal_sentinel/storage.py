from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from decimal import Decimal, InvalidOperation
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
                CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_plan_id ON payments(plan_id);
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

    def _daily_amounts(self, day_start: int):
        return self.conn.execute(
            "SELECT amount FROM payments WHERE created_at>=? "
            "AND state IN ('CREATING','CREATED','CAPTURING','CAPTURE_UNKNOWN','COMPLETED')",
            (day_start,),
        ).fetchall()

    def daily_reserved(self) -> Decimal:
        now = int(time.time())
        day_start = now - (now % 86400)
        with self.lock:
            rows = self._daily_amounts(day_start)
        try:
            return sum((Decimal(row["amount"]) for row in rows), Decimal("0"))
        except InvalidOperation as exc:
            raise RuntimeError("payment ledger contains invalid amount") from exc

    def reserve_payment(self, plan_id: str, amount: str, currency: str, daily_limit: str) -> str:
        payment_id = secrets.token_urlsafe(18)
        now = int(time.time())
        day_start = now - (now % 86400)
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                existing = self.conn.execute(
                    "SELECT state FROM payments WHERE plan_id=?", (plan_id,)
                ).fetchone()
                if existing:
                    raise ValueError("this approved plan has already been used")
                amount_decimal = Decimal(amount)
                limit_decimal = Decimal(daily_limit)
                if not amount_decimal.is_finite() or amount_decimal <= 0:
                    raise ValueError("payment amount must be finite and positive")
                if not limit_decimal.is_finite() or limit_decimal <= 0:
                    raise ValueError("daily limit must be finite and positive")
                rows = self._daily_amounts(day_start)
                total = sum((Decimal(row["amount"]) for row in rows), Decimal("0"))
                if total + amount_decimal > limit_decimal:
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

    def begin_capture(self, order_id: str) -> bool:
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                row = self.conn.execute(
                    "SELECT state FROM payments WHERE order_id=?", (order_id,)
                ).fetchone()
                valid = bool(row and row["state"] == "CREATED")
                if valid:
                    self.conn.execute(
                        "UPDATE payments SET state='CAPTURING' WHERE order_id=? AND state='CREATED'",
                        (order_id,),
                    )
                self.conn.execute("COMMIT")
                return valid
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def mark_capture_unknown(self, order_id: str) -> None:
        with self.lock:
            self.conn.execute(
                "UPDATE payments SET state='CAPTURE_UNKNOWN' WHERE order_id=? AND state='CAPTURING'",
                (order_id,),
            )

    def complete_payment(self, order_id: str, capture_id: str) -> None:
        with self.lock:
            self.conn.execute(
                "UPDATE payments SET state='COMPLETED', capture_id=? WHERE order_id=? AND state='CAPTURING'",
                (capture_id, order_id),
            )
