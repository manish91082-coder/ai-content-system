from decimal import Decimal

import pytest

from paypal_sentinel.storage import Store


def plan_payload(decision="WARN"):
    return {
        "sku": "ai-pro-month",
        "quantity": 1,
        "amount": "12.00",
        "currency": "USD",
        "decision": decision,
        "intent_hash": "a" * 64,
    }


def test_approval_is_bound_to_plan_and_consumed_once(tmp_path):
    store = Store(str(tmp_path / "state.sqlite3"))
    plan_id = store.save_plan(plan_payload())
    token = store.issue_approval(plan_id)
    assert store.consume_approval(plan_id, token) is True
    assert store.consume_approval(plan_id, token) is False


def test_daily_reservations_are_exact_and_persistent(tmp_path):
    path = str(tmp_path / "state.sqlite3")
    store = Store(path)
    store.reserve_payment("plan-a", "12.10", "USD", "100.00")
    assert store.daily_reserved() == Decimal("12.10")
    store.reserve_payment("plan-b", "87.90", "USD", "100.00")
    with pytest.raises(ValueError):
        store.reserve_payment("plan-c", "0.01", "USD", "100.00")
    restarted = Store(path)
    assert restarted.daily_reserved() == Decimal("100.00")


def test_capture_state_is_single_transition(tmp_path):
    store = Store(str(tmp_path / "state.sqlite3"))
    payment_id = store.reserve_payment("plan-a", "12.00", "USD", "100.00")
    store.set_order(payment_id, "ORDER-123")
    assert store.begin_capture("ORDER-123") is True
    assert store.begin_capture("ORDER-123") is False
    store.complete_payment("ORDER-123", "CAPTURE-123")
    payment = store.get_payment("ORDER-123")
    assert payment["state"] == "COMPLETED"
    assert payment["capture_id"] == "CAPTURE-123"
