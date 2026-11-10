#!/usr/bin/env python3
"""Public, read-only BountyBoard discovery. No account or API key required."""
import json, os, sys, time
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from pathlib import Path

BASE = os.getenv("BOUNTYBOARD_API_BASE", "https://www.bountyboard.work").rstrip("/")
OUT = Path(os.getenv("REPORT_DIR", "report"))
HEADERS = {"Accept": "application/json", "User-Agent": "NexusCloudWorkEngine/1.0"}

def get_json(url, retries=3):
    last = None
    for attempt in range(retries):
        req = Request(url, headers=HEADERS)
        try:
            with urlopen(req, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 and attempt + 1 < retries:
                try:
                    wait = max(1, min(int(exc.headers.get("Retry-After", "5")), 60))
                except ValueError:
                    wait = 5
                time.sleep(wait)
                last = "HTTP 429"
                continue
            if exc.code >= 500 and attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
                last = "HTTP " + str(exc.code)
                continue
            raise RuntimeError("BountyBoard API returned HTTP " + str(exc.code)) from None
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = type(exc).__name__
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError("BountyBoard request failed: " + str(last))

def rows_from(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise RuntimeError("BountyBoard response is not an object or array")
    for key in ("bounties", "data", "items", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for nested in ("bounties", "items", "results"):
                if isinstance(value.get(nested), list):
                    return value[nested]
    raise RuntimeError("BountyBoard list schema mismatch")

def amount_display(row):
    for key in ("reward_display", "amount_display", "rewardFormatted", "formattedReward"):
        if row.get(key):
            return str(row[key])
    for key in ("reward", "amount", "payout", "budget"):
        value = row.get(key)
        if isinstance(value, (str, int, float, Decimal)):
            return str(value)
    for key in ("rewardCents", "amountCents", "payout_cents"):
        value = row.get(key)
        if value is not None:
            try:
                return str(Decimal(str(value)) / Decimal(100))
            except (InvalidOperation, ValueError, TypeError):
                pass
    return None

def normalize(row):
    if not isinstance(row, dict):
        return None
    ident = row.get("_id") or row.get("id") or row.get("bountyId")
    escrow = row.get("escrow") if isinstance(row.get("escrow"), dict) else {}
    funded = row.get("funded") is True or row.get("isFunded") is True or row.get("escrowFunded") is True or escrow.get("status") == "funded"
    agent_allowed = row.get("agentsAllowed") is True or row.get("aiAgentsAllowed") is True or row.get("agentAllowed") is True
    title = row.get("title") or row.get("name")
    description = row.get("description") or row.get("details") or row.get("brief")
    currency = row.get("currency") or row.get("rewardCurrency")
    reward = amount_display(row)
    net = None
    try:
        if reward is not None:
            net = str(Decimal(reward) * Decimal("0.90"))
    except (InvalidOperation, ValueError, TypeError):
        pass
    slug = row.get("slug")
    url = ("https://www.bountyboard.work/bounties/" + str(slug)) if slug else (
        "https://www.bountyboard.work/bounties/" + str(ident) if ident else "https://www.bountyboard.work/bounties"
    )
    return {
        "platform": "BountyBoard",
        "task_id": str(ident) if ident is not None else None,
        "title": title,
        "description": description,
        "category": row.get("category"),
        "status": row.get("status"),
        "currency": currency,
        "gross_reward_display": reward,
        "estimated_agent_payout_after_10pct_fee": net,
        "funded_signal": "FUNDED_FIELD" if funded else "UNKNOWN",
        "agents_allowed": agent_allowed,
        "deadline": row.get("deadline") or row.get("expiresAt") or row.get("expires_at"),
        "claims_count": row.get("claimsCount") or row.get("claimCount"),
        "source_url": url,
        "raw_fields": sorted(row.keys()),
        "raw": row,
        "writes_enabled": False
    }

def classify(item):
    text = " ".join(str(item.get(k) or "") for k in ("title", "description", "category")).lower()
    if str(item.get("status") or "").lower() not in ("open", "active"):
        return "EXCLUDED", "not_open"
    if any(x in text for x in ("schoolwork", "homework", "write my essay", "complete my assignment", "student assignment")):
        return "EXCLUDED", "academic_integrity_risk"
    if any(x in text for x in ("walk around", "visit each place", "take your own photo", "in-person", "in person", "must be in prague", "must be in warsaw", "must be in budapest", "must be in madrid", "must be in lisbon")):
        return "EXCLUDED", "physical_presence_or_original_local_photos_required"
    if not item.get("agents_allowed"):
        return "REVIEW_REQUIRED", "AI_agent_permission_not_explicit_in_list_response"
    if item.get("funded_signal") != "FUNDED_FIELD":
        return "REVIEW_REQUIRED", "escrow_funding_not_proven_by_machine_readable_field"
    if not item.get("gross_reward_display") or not item.get("currency"):
        return "REVIEW_REQUIRED", "payout_amount_or_currency_not_machine_verified"
    return "CANDIDATE_REQUIRES_DETAIL_REVIEW", "agent_allowed_and_funding_fields_present; 10pct_platform_fee_applies"

def scan(max_pages=30, limit=50):
    all_rows, seen, cursor, pages = [], set(), None, 0
    for _ in range(max_pages):
        params = {"status": "OPEN", "limit": str(limit)}
        if cursor:
            params["cursor"] = cursor
        payload = get_json(BASE + "/api/bounties?" + urlencode(params))
        batch = rows_from(payload)
        for row in batch:
            if not isinstance(row, dict):
                continue
            ident = str(row.get("_id") or row.get("id") or row.get("bountyId") or "")
            if ident and ident not in seen:
                seen.add(ident)
                all_rows.append(row)
        pages += 1
        if not isinstance(payload, dict):
            break
        has_more = payload.get("has_more") is True or payload.get("hasMore") is True
        next_cursor = payload.get("next_cursor") or payload.get("nextCursor")
        if not has_more:
            break
        if not next_cursor or next_cursor == cursor:
            raise RuntimeError("BountyBoard pagination cursor missing or repeated")
        cursor = next_cursor
    else:
        raise RuntimeError("BountyBoard pagination safety cap reached")
    return all_rows, {"pages": pages, "pagination_complete": True, "public_read_only": True}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, meta = scan()
    items = [normalize(row) for row in rows]
    items = [item for item in items if item]
    for item in items:
        item["decision"], item["reason"] = classify(item)
    report = {
        "status": "ok",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "platform": "BountyBoard",
        "count": len(items),
        "meta": meta,
        "opportunities": items,
        "financial_policy": {
            "platform_fee_rate": "10%",
            "net_display_is_estimate_only": True,
            "income_recognized": 0,
            "actual_receipt_required": True
        },
        "marketplace_writes": False
    }
    path = OUT / "bountyboard-opportunities.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {}
    for item in items:
        summary[item["decision"]] = summary.get(item["decision"], 0) + 1
    print(json.dumps({"status": "ok", "count": len(items), "decisions": summary, "report": str(path)}))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
