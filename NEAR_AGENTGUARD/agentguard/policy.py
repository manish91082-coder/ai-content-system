from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Iterable


class Decision(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class PaymentIntent:
    agent_id: str
    recipient: str
    amount: Decimal
    asset: str = "NEAR"
    contract_id: str | None = None
    method_name: str | None = None
    purpose: str = ""


@dataclass(frozen=True)
class RiskSignals:
    known_malicious: bool = False
    account_age_days: int | None = None
    recent_code_change: bool = False
    first_interaction: bool = False
    evidence_count: int = 0


@dataclass(frozen=True)
class Policy:
    max_single_payment: Decimal
    max_daily_spend: Decimal
    allowed_recipients: frozenset[str] = field(default_factory=frozenset)
    blocked_recipients: frozenset[str] = field(default_factory=frozenset)
    allowed_contracts: frozenset[str] = field(default_factory=frozenset)
    allowed_methods: frozenset[str] = field(default_factory=frozenset)
    human_approval_above: Decimal = Decimal("0")
    min_account_age_days: int = 0
    warn_on_first_interaction: bool = True


@dataclass(frozen=True)
class Evaluation:
    decision: Decision
    reasons: tuple[str, ...]
    amount: Decimal


def evaluate(
    intent: PaymentIntent,
    policy: Policy,
    spent_today: Decimal,
    signals: RiskSignals | None = None,
) -> Evaluation:
    """Fail-closed deterministic policy. The model cannot override this result."""
    signals = signals or RiskSignals()
    reasons: list[str] = []

    if not intent.recipient.strip():
        return Evaluation(Decision.BLOCK, ("missing_recipient",), intent.amount)
    if intent.amount <= 0:
        return Evaluation(Decision.BLOCK, ("amount_must_be_positive",), intent.amount)
    if signals.known_malicious or intent.recipient in policy.blocked_recipients:
        return Evaluation(Decision.BLOCK, ("recipient_blocklisted",), intent.amount)
    if intent.amount > policy.max_single_payment:
        return Evaluation(Decision.BLOCK, ("single_payment_limit_exceeded",), intent.amount)
    if spent_today + intent.amount > policy.max_daily_spend:
        return Evaluation(Decision.BLOCK, ("daily_spend_limit_exceeded",), intent.amount)

    if intent.contract_id is not None and intent.contract_id not in policy.allowed_contracts:
        return Evaluation(Decision.BLOCK, ("contract_not_allowlisted",), intent.amount)
    if intent.method_name is not None and intent.method_name not in policy.allowed_methods:
        return Evaluation(Decision.BLOCK, ("method_not_allowlisted",), intent.amount)

    if signals.account_age_days is not None and signals.account_age_days < policy.min_account_age_days:
        reasons.append("counterparty_account_too_new")
    if signals.recent_code_change:
        reasons.append("counterparty_recent_code_change")
    if policy.warn_on_first_interaction and signals.first_interaction:
        reasons.append("first_interaction_requires_review")
    if intent.amount > policy.human_approval_above:
        reasons.append("amount_requires_human_approval")

    if reasons:
        return Evaluation(Decision.WARN, tuple(reasons), intent.amount)
    return Evaluation(Decision.ALLOW, ("all_policy_checks_passed",), intent.amount)


def default_demo_policy() -> Policy:
    return Policy(
        max_single_payment=Decimal("5"),
        max_daily_spend=Decimal("10"),
        allowed_recipients=frozenset({"vendor.near", "compute.near"}),
        blocked_recipients=frozenset({"bad.actor.near"}),
        allowed_contracts=frozenset({"agent-payments.near"}),
        allowed_methods=frozenset({"pay", "settle"}),
        human_approval_above=Decimal("2"),
        min_account_age_days=7,
    )
