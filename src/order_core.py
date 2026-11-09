"""Provider-neutral, local-first order and payment-event core.

This module deliberately does not contact a payment provider or deliver public URLs.
It accepts only normalized, already-authenticated provider events. Call
verify_webhook_signature() on the exact raw request body before parsing it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_webhook_signature(raw_body: bytes, supplied_signature: str,
                             secret: str) -> bool:
    """Verify a hex HMAC-SHA256 signature over the exact raw request bytes."""
    if not raw_body or not supplied_signature or not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    candidate = supplied_signature.strip()
    if candidate.lower().startswith("sha256="):
        candidate = candidate[7:]
    return hmac.compare_digest(expected, candidate.lower())


class OrderCore:
    """SQLite transaction ledger for order, event inbox and fulfilment jobs."""

    def __init__(self, database_path: str | Path = "data/revenue_engine.sqlite3"):
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.database_path, timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        return conn

    @contextmanager
    def _transaction(self):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    product_version TEXT NOT NULL,
                    amount_minor INTEGER NOT NULL CHECK(amount_minor > 0),
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payment_status TEXT NOT NULL,
                    entitlement_active INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS payment_events (
                    provider TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    processing_result TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    PRIMARY KEY(provider, environment, event_id)
                );
                CREATE TABLE IF NOT EXISTS fulfilment_jobs (
                    job_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL REFERENCES orders(order_id),
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(order_id, operation)
                );
                CREATE INDEX IF NOT EXISTS idx_fulfilment_status
                    ON fulfilment_jobs(status, created_at);
            """)

    def create_order(self, product_id: str, product_version: str,
                     amount_minor: int, currency: str = "INR") -> dict[str, Any]:
        if not product_id.strip() or not product_version.strip():
            raise ValueError("product_id and product_version are required")
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0:
            raise ValueError("amount_minor must be a positive integer in paise/minor units")
        currency = currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a 3-letter code")
        now, order_id = utc_now(), str(uuid.uuid4())
        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO orders(order_id, product_id, product_version, amount_minor,
                    currency, status, payment_status, entitlement_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'awaiting_payment', 'created', 0, ?, ?)
            """, (order_id, product_id, product_version, amount_minor, currency, now, now))
        return self.get_order(order_id)

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        return dict(row) if row else None

    def process_payment_event(self, *, provider: str, environment: str,
                              event: dict[str, Any]) -> dict[str, Any]:
        """Process a normalized event after provider signature verification.

        Required fields: event_id, order_id, event_type, amount_minor, currency.
        Supported event types: payment.pending, payment.captured,
        payment.failed, payment.refunded, payment.disputed.
        """
        required = ("event_id", "order_id", "event_type", "amount_minor", "currency")
        if any(event.get(key) is None for key in required):
            raise ValueError("payment event is missing required fields")
        if not provider.strip() or not environment.strip():
            raise ValueError("provider and environment are required")
        amount = event["amount_minor"]
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("event amount_minor must be a non-negative integer")
        event_type = str(event["event_type"]).strip().lower()
        allowed = {"payment.pending", "payment.captured", "payment.failed",
                   "payment.refunded", "payment.disputed"}
        if event_type not in allowed:
            raise ValueError("unsupported payment event type")
        event_id, order_id = str(event["event_id"]), str(event["order_id"])
        currency = str(event["currency"]).upper()
        payload_json = json.dumps(event, sort_keys=True, separators=(",", ":"))
        now = utc_now()

        with self._transaction() as conn:
            try:
                conn.execute("""
                    INSERT INTO payment_events(provider, environment, event_id, order_id,
                        event_type, payload_json, processing_result, received_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'processing', ?)
                """, (provider, environment, event_id, order_id, event_type, payload_json, now))
            except sqlite3.IntegrityError:
                return {"accepted": True, "duplicate": True, "result": "already_processed"}

            order = conn.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
            if not order:
                result = "rejected_unknown_order"
            elif amount != order["amount_minor"] or currency != order["currency"]:
                result = "rejected_amount_or_currency_mismatch"
            elif order["status"] in ("refunded", "disputed"):
                result = "ignored_terminal_order"
            elif event_type == "payment.pending":
                conn.execute("UPDATE orders SET payment_status='pending', updated_at=? WHERE order_id=?",
                             (now, order_id))
                result = "payment_pending"
            elif event_type == "payment.failed":
                if order["payment_status"] in ("captured", "refunded", "disputed"):
                    result = "ignored_non_forward_transition"
                else:
                    conn.execute("""UPDATE orders SET payment_status='failed',
                        status='payment_failed', updated_at=? WHERE order_id=?""", (now, order_id))
                    result = "payment_failed"
            elif event_type == "payment.captured":
                if order["payment_status"] in ("captured", "refunded", "disputed"):
                    result = "ignored_non_forward_transition"
                else:
                    conn.execute("""UPDATE orders SET payment_status='captured', status='paid',
                        entitlement_active=1, updated_at=? WHERE order_id=?""", (now, order_id))
                    conn.execute("""
                        INSERT OR IGNORE INTO fulfilment_jobs
                            (job_id, order_id, operation, status, created_at, updated_at)
                        VALUES (?, ?, 'deliver_product', 'pending', ?, ?)
                    """, (str(uuid.uuid4()), order_id, now, now))
                    result = "payment_captured_fulfilment_queued"
            elif event_type == "payment.refunded":
                if order["payment_status"] != "captured":
                    result = "rejected_refund_without_capture"
                else:
                    conn.execute("""UPDATE orders SET payment_status='refunded', status='refunded',
                        entitlement_active=0, updated_at=? WHERE order_id=?""", (now, order_id))
                    conn.execute("""UPDATE fulfilment_jobs SET status='cancelled', updated_at=?
                        WHERE order_id=? AND status IN ('pending','processing')""", (now, order_id))
                    result = "refunded_entitlement_revoked"
            else:  # payment.disputed
                conn.execute("""UPDATE orders SET payment_status='disputed', status='disputed',
                    entitlement_active=0, updated_at=? WHERE order_id=?""", (now, order_id))
                conn.execute("""UPDATE fulfilment_jobs SET status='cancelled', updated_at=?
                    WHERE order_id=? AND status IN ('pending','processing')""", (now, order_id))
                result = "disputed_entitlement_revoked"

            conn.execute("""UPDATE payment_events SET processing_result=?
                WHERE provider=? AND environment=? AND event_id=?""",
                (result, provider, environment, event_id))
        return {"accepted": True, "duplicate": False, "result": result}

    def list_pending_fulfilment(self, limit: int = 20) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT j.*, o.product_id, o.product_version, o.entitlement_active
                FROM fulfilment_jobs j JOIN orders o USING(order_id)
                WHERE j.status='pending' AND o.entitlement_active=1
                ORDER BY j.created_at LIMIT ?
            """, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def complete_fulfilment(self, job_id: str) -> dict[str, Any]:
        """Mark one job complete once. Actual private file delivery is a later adapter."""
        now = utc_now()
        with self._transaction() as conn:
            job = conn.execute("""
                SELECT j.*, o.entitlement_active FROM fulfilment_jobs j
                JOIN orders o USING(order_id) WHERE j.job_id=?
            """, (job_id,)).fetchone()
            if not job:
                raise KeyError("fulfilment job not found")
            if job["status"] == "completed":
                return {"completed": True, "duplicate": True, "job_id": job_id}
            if job["status"] != "pending" or not job["entitlement_active"]:
                raise ValueError("job is not eligible for fulfilment")
            conn.execute("""UPDATE fulfilment_jobs SET status='completed',
                attempts=attempts+1, updated_at=? WHERE job_id=? AND status='pending'""",
                (now, job_id))
            conn.execute("""UPDATE orders SET status='fulfilled', updated_at=?
                WHERE order_id=? AND entitlement_active=1""", (now, job["order_id"]))
        return {"completed": True, "duplicate": False, "job_id": job_id}
