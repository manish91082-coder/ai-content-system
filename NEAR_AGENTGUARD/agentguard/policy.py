from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


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

    def __post_init__(self) -> None:
        limits = (self.max_single_payment, self.max_daily_spend, self.human_approval_above)
        if any(not isinstance(value, Decimal) or not value.is_finite() for value in limits):
            raise ValueError("policy limits must be finite Decimal values")
        if self.max_single_payment <= 0 or self.max_daily_spend <= 0:
            raise ValueError("payment limits must be positive")
        if self.max_daily_spend < self.max_single_payment:
            raise ValueError("daily limit must be at least the single-payment limit")
        if self.human_approval_above < 0 or self.min_account_age_days < 0:
            raise ValueError("approval threshold and minimum account age cannot be negative")
        for values in (self.allowed_recipients, self.blocked_recipients,
                       self.allowed_contracts, self.allowed_methods):
            if any(not value or not value.strip() for value in values):
                raise ValueError("policy allow/block lists cannot contain blank values")


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

    def block(reason: str) -> Evaluation:
        return Evaluation(Decision.BLOCK, (reason,), intent.amount)

    if not isinstance(intent.agent_id, str) or not intent.agent_id.strip():
        return block("missing_agent_id")
    if intent.asset != "NEAR":
        return block("unsupported_asset")
    if not isinstance(intent.recipient, str) or not intent.recipient.strip():
        return block("missing_recipient")
    if not isinstance(intent.amount, Decimal) or not intent.amount.is_finite():
        return block("amount_must_be_finite_decimal")
    if intent.amount <= 0:
        return block("amount_must_be_positive")
    if not isinstance(spent_today, Decimal) or not spent_today.is_finite() or spent_today < 0:
        return block("invalid_spend_counter")
    if signals.account_age_days is not None and signals.account_age_days < 0:
        return block("invalid_counterparty_age")
    if signals.evidence_count < 0:
        return block("invalid_evidence_count")
    if signals.known_malicious or intent.recipient in policy.blocked_recipients:
        return block("recipient_blocklisted")
    if intent.amount > policy.max_single_payment:
        return block("single_payment_limit_exceeded")
    if spent_today + intent.amount > policy.max_daily_spend:
        return block("daily_spend_limit_exceeded")

    if not policy.allowed_recipients:
        return block("recipient_allowlist_not_configured")

    reasons: list[str] = []
    if intent.recipient not in policy.allowed_recipients:
        reasons.append("recipient_not_allowlisted")

    if not policy.allowed_contracts:
        return block("contract_allowlist_not_configured")
    if not intent.contract_id:
        return block("contract_id_required")
    if intent.contract_id not in policy.allowed_contracts:
        return block("contract_not_allowlisted")

    if not policy.allowed_methods:
        return block("method_allowlist_not_configured")
    if not intent.method_name:
        return block("method_name_required")
    if intent.method_name not in policy.allowed_methods:
        return block("method_not_allowlisted")

    if signals.account_age_days is None:
        reasons.append("counterparty_age_unknown")
    elif signals.account_age_days < policy.min_account_age_days:
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
