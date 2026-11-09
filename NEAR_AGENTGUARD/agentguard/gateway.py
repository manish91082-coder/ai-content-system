from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Protocol

from .policy import Decision, PaymentIntent, Policy, RiskSignals, evaluate
from .receipts import ReceiptLog


class Signer(Protocol):
    def sign_and_submit(self, intent: PaymentIntent) -> str: ...


class DemoSigner:
    """Intentionally non-broadcasting signer boundary. Never sends funds."""
    def sign_and_submit(self, intent: PaymentIntent) -> str:
        return "SIMULATED_ONLY"


def intent_fingerprint(intent: PaymentIntent) -> str:
    canonical = json.dumps(
        {
            "agent_id": intent.agent_id,
            "recipient": intent.recipient,
            "amount": str(intent.amount),
            "asset": intent.asset,
            "contract_id": intent.contract_id,
            "method_name": intent.method_name,
            "purpose": intent.purpose,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ApprovalAuthority:
    """Demo approval issuer; production requires authenticated owner identity and durable nonce storage."""

    def __init__(self, secret: bytes, clock: Callable[[], float] = time.time):
        if len(secret) < 32:
            raise ValueError("approval secret must contain at least 32 bytes")
        self._secret = secret
        self._clock = clock
        self._used_nonces: set[str] = set()
        self._lock = threading.Lock()

    def issue(self, intent: PaymentIntent, ttl_seconds: int = 120) -> str:
        if ttl_seconds < 1 or ttl_seconds > 300:
            raise ValueError("approval TTL must be between 1 and 300 seconds")
        payload = {
            "intent_hash": intent_fingerprint(intent),
            "expires_at": int(self._clock()) + ttl_seconds,
            "nonce": secrets.token_urlsafe(18),
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).decode("ascii").rstrip("=")
        signature = hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def consume(self, token: str, intent: PaymentIntent) -> bool:
        try:
            encoded, supplied_signature = token.split(".", 1)
            expected_signature = hmac.new(
                self._secret, encoded.encode("ascii"), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(supplied_signature, expected_signature):
                return False
            raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
            payload = json.loads(raw.decode("utf-8"))
            if set(payload) != {"intent_hash", "expires_at", "nonce"}:
                return False
            if payload["intent_hash"] != intent_fingerprint(intent):
                return False
            if not isinstance(payload["expires_at"], int) or payload["expires_at"] < int(self._clock()):
                return False
            nonce = payload["nonce"]
            if not isinstance(nonce, str) or not nonce:
                return False
            with self._lock:
                if nonce in self._used_nonces:
                    return False
                self._used_nonces.add(nonce)
            return True
        except (ValueError, TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError):
            return False


@dataclass(frozen=True)
class GatewayResult:
    decision: str
    reasons: tuple[str, ...]
    signer_called: bool
    transaction_reference: str | None


class PaymentGateway:
    def __init__(
        self,
        policy: Policy,
        signer: Signer,
        receipt_path: str | Path,
        approval_authority: ApprovalAuthority | None = None,
    ):
        self.policy = policy
        self.signer = signer
        self.receipts = ReceiptLog(receipt_path)
        self.approval_authority = approval_authority
        self._spend_day = datetime.now(timezone.utc).date()
        self._lock = threading.RLock()
        self.spent_today = self._restore_daily_spend(self._spend_day)

    def _restore_daily_spend(self, day) -> Decimal:
        if not self.receipts.verify():
            raise RuntimeError("receipt log integrity check failed; gateway startup refused")
        total = Decimal("0")
        for timestamp, event in self.receipts.events():
            try:
                event_day = datetime.fromisoformat(timestamp).astimezone(timezone.utc).date()
                if event_day == day and event.get("signer_called") is True:
                    amount = Decimal(event["amount"])
                    if not amount.is_finite() or amount <= 0 or event.get("asset") != "NEAR":
                        raise ValueError("invalid settled-intent receipt")
                    total += amount
            except (ValueError, TypeError, KeyError) as exc:
                raise RuntimeError("receipt contains invalid spend history") from exc
        return total

    def authorize(
        self,
        intent: PaymentIntent,
        signals: RiskSignals | None = None,
        human_approval_token: str | None = None,
    ) -> GatewayResult:
        with self._lock:
            today = datetime.now(timezone.utc).date()
            if today != self._spend_day:
                self.spent_today = self._restore_daily_spend(today)
                self._spend_day = today

            result = evaluate(intent, self.policy, self.spent_today, signals)
            signer_called = False
            tx_ref = None

            if result.decision == Decision.ALLOW:
                tx_ref = self.signer.sign_and_submit(intent)
                signer_called = True
            elif (
                result.decision == Decision.WARN
                and human_approval_token
                and self.approval_authority
                and self.approval_authority.consume(human_approval_token, intent)
            ):
                tx_ref = self.signer.sign_and_submit(intent)
                signer_called = True

            if signer_called:
                self.spent_today += intent.amount

            self.receipts.append({
                "agent_id": intent.agent_id,
                "recipient": intent.recipient,
                "amount": str(intent.amount),
                "asset": intent.asset,
                "contract_id": intent.contract_id,
                "method_name": intent.method_name,
                "decision": result.decision.value,
                "reasons": list(result.reasons),
                "signer_called": signer_called,
                "transaction_reference": tx_ref,
            })
            return GatewayResult(result.decision.value, result.reasons, signer_called, tx_ref)
