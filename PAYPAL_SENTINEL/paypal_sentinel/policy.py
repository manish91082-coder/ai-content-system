from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

CATALOG = {
    "ai-pro-month": {"name": "AI Pro Monthly Sandbox Plan", "unit_price": Decimal("12.00")},
    "cloud-credit-pack": {"name": "Cloud Compute Credit Pack", "unit_price": Decimal("24.00")},
    "research-data-pack": {"name": "Research Data Pack", "unit_price": Decimal("7.50")},
}


@dataclass(frozen=True)
class PurchasePlan:
    sku: str
    quantity: int
    item_name: str
    unit_price: str
    amount: str
    currency: str
    risk_flags: tuple[str, ...]
    decision: str
    reasons: tuple[str, ...]
    rationale: str
    intent_hash: str


def canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_plan(ai_result: dict[str, Any], user_prompt: str, daily_reserved: Decimal) -> PurchasePlan:
    sku = ai_result.get("sku")
    quantity = ai_result.get("quantity")
    rationale = str(ai_result.get("rationale", "AI parsed purchase request"))[:500]
    flags = tuple(sorted({str(x).lower() for x in ai_result.get("risk_flags", []) if isinstance(x, str)}))
    reasons: list[str] = []

    if not isinstance(sku, str) or sku not in CATALOG:
        sku = "invalid"
        item_name = "Unknown product"
        unit_price = Decimal("0")
        amount = Decimal("0")
        decision = "BLOCK"
        reasons.append("product_not_in_verified_catalog")
    else:
        item_name = CATALOG[sku]["name"]
        unit_price = CATALOG[sku]["unit_price"]
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            quantity = 0
            decision = "BLOCK"
            reasons.append("invalid_quantity")
        elif quantity > 5:
            decision = "BLOCK"
            reasons.append("quantity_exceeds_hard_limit")
        else:
            decision = "ALLOW"
        amount = unit_price * quantity

    prompt_lower = user_prompt.lower()
    injection_markers = ("ignore previous", "bypass policy", "override the rules", "change the price", "pay a different seller")
    if any(marker in prompt_lower for marker in injection_markers) or any(
        flag in {"prompt_injection", "price_override", "seller_substitution"} for flag in flags
    ):
        decision = "BLOCK"
        reasons.append("prompt_injection_or_payment_parameter_tampering")

    try:
        max_single = Decimal(os.getenv("MAX_SINGLE_USD", "75.00"))
        daily_limit = Decimal(os.getenv("DAILY_LIMIT_USD", "100.00"))
    except InvalidOperation as exc:
        raise ValueError("invalid payment policy configuration") from exc

    if not amount.is_finite() or amount <= 0:
        decision = "BLOCK"
        reasons.append("invalid_amount")
    elif amount > max_single:
        decision = "BLOCK"
        reasons.append("single_payment_limit_exceeded")
    elif daily_reserved + amount > daily_limit:
        decision = "BLOCK"
        reasons.append("daily_spend_limit_exceeded")

    if decision != "BLOCK":
        if flags:
            decision = "WARN"
            reasons.extend("ai_risk_flag:" + flag for flag in flags)
        elif amount > Decimal("30.00") or quantity >= 3:
            decision = "WARN"
            reasons.append("high_value_or_bulk_purchase_requires_human_review")

    payload = {
        "sku": sku,
        "quantity": quantity,
        "item_name": item_name,
        "unit_price": str(unit_price),
        "amount": str(amount.quantize(Decimal("0.01"))),
        "currency": "USD",
        "risk_flags": list(flags),
        "rationale": rationale,
    }
    return PurchasePlan(
        sku=sku,
        quantity=quantity,
        item_name=item_name,
        unit_price=str(unit_price),
        amount=str(amount.quantize(Decimal("0.01"))),
        currency="USD",
        risk_flags=flags,
        decision=decision,
        reasons=tuple(dict.fromkeys(reasons or ["all_deterministic_checks_passed"])),
        rationale=rationale,
        intent_hash=canonical_hash(payload),
    )
