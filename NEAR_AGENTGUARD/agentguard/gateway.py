from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from .policy import Decision, PaymentIntent, Policy, RiskSignals, evaluate
from .receipts import ReceiptLog


class Signer(Protocol):
    def sign_and_submit(self, intent: PaymentIntent) -> str: ...


class DemoSigner:
    """Intentionally non-broadcasting signer boundary. Never sends funds."""
    def sign_and_submit(self, intent: PaymentIntent) -> str:
        return "SIMULATED_ONLY"


@dataclass(frozen=True)
class GatewayResult:
    decision: str
    reasons: tuple[str, ...]
    signer_called: bool
    transaction_reference: str | None


class PaymentGateway:
    def __init__(self, policy: Policy, signer: Signer, receipt_path: str | Path):
        self.policy = policy
        self.signer = signer
        self.receipts = ReceiptLog(receipt_path)
        self.spent_today = Decimal("0")
        self._spend_day = datetime.now(timezone.utc).date()

    def authorize(
        self,
        intent: PaymentIntent,
        signals: RiskSignals | None = None,
        human_approval_token: str | None = None,
    ) -> GatewayResult:
        today = datetime.now(timezone.utc).date()
        if today != self._spend_day:
            self.spent_today = Decimal("0")
            self._spend_day = today
        result = evaluate(intent, self.policy, self.spent_today, signals)
        signer_called = False
        tx_ref = None

        if result.decision == Decision.ALLOW:
            tx_ref = self.signer.sign_and_submit(intent)
            signer_called = True
            self.spent_today += intent.amount
        elif result.decision == Decision.WARN and human_approval_token == "DEMO-APPROVED":
            # Demo-only approval token. Production must use authenticated,
            # single-use, expiring approval bound to the exact intent hash.
            tx_ref = self.signer.sign_and_submit(intent)
            signer_called = True
            self.spent_today += intent.amount

        self.receipts.append({
            "agent_id": intent.agent_id,
            "recipient": intent.recipient,
            "amount": str(intent.amount),
            "asset": intent.asset,
            "decision": result.decision.value,
            "reasons": list(result.reasons),
            "signer_called": signer_called,
            "transaction_reference": tx_ref,
        })
        return GatewayResult(result.decision.value, result.reasons, signer_called, tx_ref)
