#!/usr/bin/env python3
"""Read-only Elgora public bounty discovery and owner-signing readiness audit.

This adapter never registers a Solver, signs messages, uploads submissions,
claims awards, or sends transactions. Public escrow is opportunity evidence,
not income or an entitlement to payment.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = os.getenv("ELGORA_API_BASE", "https://elgora.ai").rstrip("/")
OUT = Path(os.getenv("REPORT_DIR", "report"))
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "NexusCloudWorkEngine/1.0",
}
BASE_CHAIN_ID = 8453
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
USDC_DECIMALS = 6


def get_json(path, retries=3):
    """Bounded GET-only request. No POST/PATCH/DELETE methods exist here."""
    url = BASE + path
    last = None
    for attempt in range(retries):
        request = Request(url, headers=HEADERS, method="GET")
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise RuntimeError("Elgora response must be a JSON object")
                return payload, {
                    "http_status": response.status,
                    "url": url,
                }
        except HTTPError as exc:
            if exc.code == 429 and attempt + 1 < retries:
                try:
                    delay = max(1, min(int(exc.headers.get("Retry-After", "5")), 60))
                except (TypeError, ValueError):
                    delay = 5
                time.sleep(delay)
                last = "HTTP 429"
                continue
            if exc.code >= 500 and attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
                last = "HTTP " + str(exc.code)
                continue
            raise RuntimeError("Elgora public API HTTP " + str(exc.code)) from None
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = type(exc).__name__
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError("Elgora public API failed: " + str(last))


def parse_amount(raw, decimals=USDC_DECIMALS):
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return Decimal(str(raw)) / (Decimal(10) ** decimals)
    except (InvalidOperation, ValueError, TypeError):
        return None


def utc_from_epoch(value):
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def title_from_challenge(challenge):
    if not isinstance(challenge, str):
        return None
    match = re.search(r"(?m)^#\s+([^\r\n]+)", challenge)
    return match.group(1).strip() if match else None


def expected_solver_reward(escrow_amount, guardian_fee_bps, treasury_fee_bps):
    """Estimate only; final settlement_amount from chain is authoritative."""
    gross = parse_amount(escrow_amount)
    if gross is None:
        return None
    try:
        guardian = Decimal(str(guardian_fee_bps or 0))
        treasury = Decimal(str(treasury_fee_bps or 0))
        total_bps = guardian + treasury
        if total_bps < 0 or total_bps > 10_000:
            return None
        return str(gross * (Decimal(10_000) - total_bps) / Decimal(10_000))
    except (InvalidOperation, ValueError, TypeError):
        return None


def normalize(detail, list_row=None, now_epoch=None):
    if not isinstance(detail, dict):
        raise RuntimeError("Elgora bounty detail must be an object")
    bounty = detail.get("bounty")
    if not isinstance(bounty, dict):
        raise RuntimeError("Elgora detail missing bounty object")
    list_row = list_row if isinstance(list_row, dict) else {}
    now_epoch = int(now_epoch if now_epoch is not None else time.time())

    bounty_id = str(bounty.get("bounty_id") or list_row.get("bounty_id") or "")
    status = str(bounty.get("status") or list_row.get("status") or "unknown").lower()
    chain_id = bounty.get("chain_id")
    escrow = bounty.get("escrow") if isinstance(bounty.get("escrow"), dict) else {}
    token = str(escrow.get("token_address") or "").lower()
    amount_raw = escrow.get("amount")
    gross = parse_amount(amount_raw)
    deadline = bounty.get("submission_deadline")
    try:
        deadline_epoch = int(deadline)
    except (TypeError, ValueError):
        deadline_epoch = None
    time_left = deadline_epoch - now_epoch if deadline_epoch is not None else None
    submissions = bounty.get("submissions")
    submissions = submissions if isinstance(submissions, list) else []
    count_raw = bounty.get("submission_count", list_row.get("submission_count"))
    try:
        submission_count = int(count_raw)
    except (TypeError, ValueError):
        submission_count = len(submissions)
    guardian_bps = bounty.get("guardian_fee_bps", 0)
    treasury_bps = bounty.get("treasury_fee_bps", 0)
    reward_estimate = expected_solver_reward(
        amount_raw, guardian_bps, treasury_bps
    )
    challenge = detail.get("challenge")
    title = title_from_challenge(challenge)
    record = detail.get("verification_record")
    if not isinstance(record, dict):
        record = {}
    winner = bounty.get("winner")

    if status != "open":
        decision, reason = "EXCLUDED", "bounty_not_open"
    elif deadline_epoch is None:
        decision, reason = "REVIEW_REQUIRED", "submission_deadline_missing_or_invalid"
    elif time_left <= 0:
        decision, reason = "EXCLUDED", "submission_deadline_passed"
    elif chain_id != BASE_CHAIN_ID:
        decision, reason = "REVIEW_REQUIRED", "unsupported_or_unverified_chain"
    elif token != BASE_USDC:
        decision, reason = "REVIEW_REQUIRED", "escrow_token_not_verified_base_usdc"
    elif gross is None or gross <= 0:
        decision, reason = "EXCLUDED", "zero_or_invalid_escrow"
    elif not isinstance(challenge, str) or not challenge.strip():
        decision, reason = "REVIEW_REQUIRED", "canonical_challenge_text_missing"
    elif winner:
        decision, reason = "EXCLUDED", "winner_already_recorded"
    else:
        decision = "PREPARABLE_OWNER_SIGNING_REQUIRED"
        reason = "open_usdc_escrowed_bounty; private submission and Base transaction require Solver wallet signatures"

    return {
        "platform": "Elgora",
        "bounty_id": bounty_id,
        "title": title,
        "status": status,
        "chain_id": chain_id,
        "chain": "Base mainnet" if chain_id == BASE_CHAIN_ID else None,
        "escrow_token_address": token or None,
        "escrow_currency": "USDC" if token == BASE_USDC else None,
        "escrow_amount_minor": str(amount_raw) if amount_raw is not None else None,
        "escrow_gross_usdc": str(gross) if gross is not None else None,
        "guardian_fee_bps": guardian_bps,
        "treasury_fee_bps": treasury_bps,
        "expected_solver_reward_usdc": reward_estimate,
        "reward_is_estimate_only": True,
        "settlement_amount_is_authoritative": True,
        "payout_policy": bounty.get("payout_policy"),
        "submission_deadline_epoch": deadline_epoch,
        "submission_deadline_utc": utc_from_epoch(deadline_epoch),
        "seconds_until_submission_deadline": time_left,
        "submission_count": submission_count,
        "winner": winner,
        "verification_record_status": record.get("status"),
        "verification_record_winner": record.get("winner"),
        "challenge_available": isinstance(challenge, str) and bool(challenge.strip()),
        "spec_commitment": bounty.get("spec_commitment"),
        "decision": decision,
        "reason": reason,
        "wallet_signature_required": decision == "PREPARABLE_OWNER_SIGNING_REQUIRED",
        "base_native_gas_required_for_transaction": True,
        "solver_wallet_or_gas_balance_verified": False,
        "solver_capacity_limit_verified": False,
        "submission_attempted": False,
        "submission_recorded": False,
        "claim_attempted": False,
        "marketplace_writes": False,
        "recognized_external_income": "0",
        "source_url": BASE + "/bounties/" + bounty_id if bounty_id else BASE + "/bounties",
    }


def run_scan(now_epoch=None):
    now_epoch = int(now_epoch if now_epoch is not None else time.time())
    listing, listing_meta = get_json("/api/bounties?status=open")
    rows = listing.get("bounties")
    if not isinstance(rows, list):
        raise RuntimeError("Elgora open-bounty response missing bounties array")

    items = []
    detail_reads = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        bounty_id = str(row.get("bounty_id") or "")
        if not bounty_id or bounty_id in seen:
            continue
        seen.add(bounty_id)
        try:
            detail, meta = get_json("/api/bounties/" + bounty_id)
            item = normalize(detail, row, now_epoch)
            detail_reads.append({
                "bounty_id": bounty_id,
                "status": "ok",
                "http_status": meta.get("http_status"),
            })
        except Exception as exc:
            item = {
                "platform": "Elgora",
                "bounty_id": bounty_id,
                "title": None,
                "status": row.get("status"),
                "escrow_amount_minor": (
                    str((row.get("escrow") or {}).get("amount"))
                    if isinstance(row.get("escrow"), dict) else None
                ),
                "submission_deadline_epoch": row.get("submission_deadline"),
                "submission_count": row.get("submission_count"),
                "decision": "REVIEW_REQUIRED",
                "reason": "canonical_detail_read_failed:" + type(exc).__name__,
                "wallet_signature_required": True,
                "submission_attempted": False,
                "submission_recorded": False,
                "claim_attempted": False,
                "marketplace_writes": False,
                "recognized_external_income": "0",
                "source_url": BASE + "/bounties/" + bounty_id,
            }
            detail_reads.append({
                "bounty_id": bounty_id,
                "status": "error",
                "reason": type(exc).__name__,
            })
        items.append(item)

    counts = {}
    for item in items:
        decision = item.get("decision", "REVIEW_REQUIRED")
        counts[decision] = counts.get(decision, 0) + 1

    return {
        "status": "ok",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": "Elgora",
        "chain_id": BASE_CHAIN_ID,
        "open_listing_count": len(rows),
        "unique_bounty_count": len(items),
        "decision_counts": counts,
        "canonical_detail_reads": detail_reads,
        "opportunities": items,
        "financial_policy": {
            "escrow_is_not_solver_income": True,
            "winner_take_all_is_competitive": True,
            "estimated_solver_reward_is_not_settlement": True,
            "final_reward_must_match_onchain_settlement_amount": True,
            "base_transaction_requires_owner_wallet_signature_and_gas": True,
            "recognized_external_income": "0",
        },
        "marketplace_writes": False,
        "submissions_attempted": 0,
        "claims_attempted": 0,
        "source": listing_meta,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = run_scan()
    path = OUT / "elgora-opportunities.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "open_listings": result["unique_bounty_count"],
        "decisions": result["decision_counts"],
        "submissions_attempted": 0,
        "claims_attempted": 0,
        "recognized_external_income": "0",
        "report": str(path),
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({
            "status": "error",
            "reason": type(exc).__name__ + ":" + str(exc)[:300],
            "marketplace_writes": False,
        }), file=sys.stderr)
        raise SystemExit(1)
