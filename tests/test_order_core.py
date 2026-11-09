import hashlib
import hmac
import json
import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from order_core import OrderCore, verify_webhook_signature


class OrderCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.core = OrderCore(Path(self.tmp.name) / "orders.sqlite3")
        self.order = self.core.create_order("regional-content-pack", "v1", 49900, "INR")

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, event_id, event_type, **overrides):
        value = {
            "event_id": event_id, "order_id": self.order["order_id"],
            "event_type": event_type, "amount_minor": 49900, "currency": "INR"
        }
        value.update(overrides)
        return value

    def process(self, event):
        return self.core.process_payment_event(
            provider="test-provider", environment="sandbox", event=event
        )

    def test_order_starts_unpaid_without_entitlement(self):
        self.assertEqual(self.order["status"], "awaiting_payment")
        self.assertEqual(self.order["payment_status"], "created")
        self.assertEqual(self.order["entitlement_active"], 0)

    def test_pending_payment_does_not_create_fulfilment(self):
        result = self.process(self.event("evt-pending", "payment.pending"))
        self.assertEqual(result["result"], "payment_pending")
        self.assertEqual(self.core.list_pending_fulfilment(), [])

    def test_duplicate_event_is_idempotent(self):
        event = self.event("evt-captured", "payment.captured")
        first = self.process(event)
        second = self.process(event)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(len(self.core.list_pending_fulfilment()), 1)

    def test_amount_mismatch_rejected_without_entitlement(self):
        result = self.process(self.event("evt-wrong", "payment.captured", amount_minor=1))
        self.assertEqual(result["result"], "rejected_amount_or_currency_mismatch")
        self.assertEqual(self.core.get_order(self.order["order_id"])["entitlement_active"], 0)
        self.assertEqual(self.core.list_pending_fulfilment(), [])

    def test_currency_mismatch_rejected(self):
        result = self.process(self.event("evt-currency", "payment.captured", currency="USD"))
        self.assertEqual(result["result"], "rejected_amount_or_currency_mismatch")

    def test_failed_event_after_capture_cannot_regress_order(self):
        self.process(self.event("evt-captured", "payment.captured"))
        result = self.process(self.event("evt-failed-late", "payment.failed"))
        self.assertEqual(result["result"], "ignored_non_forward_transition")
        order = self.core.get_order(self.order["order_id"])
        self.assertEqual(order["payment_status"], "captured")
        self.assertEqual(order["status"], "paid")
        self.assertEqual(len(self.core.list_pending_fulfilment()), 1)

    def test_capture_creates_exactly_one_fulfilment_job(self):
        self.process(self.event("evt-captured", "payment.captured"))
        self.process(self.event("evt-captured-2", "payment.captured"))
        self.assertEqual(len(self.core.list_pending_fulfilment()), 1)

    def test_refund_revokes_entitlement_and_cancels_pending_delivery(self):
        self.process(self.event("evt-captured", "payment.captured"))
        result = self.process(self.event("evt-refund", "payment.refunded"))
        self.assertEqual(result["result"], "refunded_entitlement_revoked")
        order = self.core.get_order(self.order["order_id"])
        self.assertEqual(order["status"], "refunded")
        self.assertEqual(order["entitlement_active"], 0)
        self.assertEqual(self.core.list_pending_fulfilment(), [])

    def test_refund_without_capture_is_rejected(self):
        result = self.process(self.event("evt-refund", "payment.refunded"))
        self.assertEqual(result["result"], "rejected_refund_without_capture")

    def test_late_capture_after_refund_cannot_restore_access(self):
        self.process(self.event("evt-captured", "payment.captured"))
        self.process(self.event("evt-refund", "payment.refunded"))
        result = self.process(self.event("evt-capture-late", "payment.captured"))
        self.assertEqual(result["result"], "ignored_terminal_order")
        self.assertEqual(self.core.get_order(self.order["order_id"])["entitlement_active"], 0)

    def test_fulfilment_completes_once(self):
        self.process(self.event("evt-captured", "payment.captured"))
        job = self.core.list_pending_fulfilment()[0]
        first = self.core.complete_fulfilment(job["job_id"])
        second = self.core.complete_fulfilment(job["job_id"])
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(self.core.get_order(self.order["order_id"])["status"], "fulfilled")

    def test_unknown_order_is_recorded_but_not_delivered(self):
        result = self.process(self.event("evt-unknown", "payment.captured", order_id="missing"))
        self.assertEqual(result["result"], "rejected_unknown_order")
        self.assertEqual(self.core.list_pending_fulfilment(), [])

    def test_signature_verification_uses_raw_body(self):
        raw = json.dumps({"id": "evt-1"}).encode()
        secret = "sandbox-secret"
        signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(raw, signature, secret))
        self.assertFalse(verify_webhook_signature(raw + b" ", signature, secret))
        self.assertFalse(verify_webhook_signature(raw, signature, ""))


if __name__ == "__main__":
    unittest.main()
