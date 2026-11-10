#!/usr/bin/env python3
"""Read-only Bounty Agent API connector with complete cursor pagination."""
import json
import os
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.getenv("BOUNTY_API_BASE", "https://api.trybounty.ai").rstrip("/")
API_KEY = os.getenv("BOUNTY_AGENT_API_KEY", "")
OUT = Path(os.getenv("REPORT_DIR", "report"))
HEADERS = {"Accept": "application/json", "User-Agent": "NexusCloudWorkEngine/1.0"}

def request_json(path, query=None, retries=3):
    if not API_KEY:
        raise RuntimeError("BOUNTY_AGENT_API_KEY is not configured")
    url = BASE + path
    if query:
        url += "?" + urlencode(query)
    last_error = None
    for attempt in range(retries):
        req = Request(url, headers={**HEADERS, "Authorization": "Bearer " + API_KEY})
        try:
            with urlopen(req, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            retry_after = exc.headers.get("Retry-After")
            if exc.code == 429 and attempt + 1 < retries:
                try:
                    delay = max(1, min(int(retry_after or "5"), 60))
                except ValueError:
                    delay = 5
                time.sleep(delay)
                last_error = "HTTP 429 rate limited"
                continue
            if exc.code >= 500 and attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
                last_error = "HTTP " + str(exc.code)
                continue
            raise RuntimeError("Bounty API returned HTTP " + str(exc.code)) from None
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = type(exc).__name__
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError("Bounty API request failed: " + str(last_error))

def page_bounties(max_pages=100):
    all_rows, seen, cursor, pages = [], set(), None, 0
    for _ in range(max_pages):
        query = {"status": "open", "limit": "100"}
        if cursor:
            query["cursor"] = cursor
        payload = request_json("/v1/agent/bounties", query)
        if not isinstance(payload, dict) or not isinstance(payload.get("bounties"), list):
            raise RuntimeError("Bounty list schema mismatch")
        for row in payload["bounties"]:
            if not isinstance(row, dict):
                continue
            key = str(row.get("_id") or row.get("id") or "")
            if key and key not in seen:
                seen.add(key)
                all_rows.append(row)
        pages += 1
        if payload.get("has_more") is not True:
            return all_rows, {"pages": pages, "has_more": False, "deduplicated": True}
        next_cursor = payload.get("next_cursor")
        if not next_cursor or next_cursor == cursor:
            raise RuntimeError("Bounty pagination cursor missing or repeated")
        cursor = next_cursor
    raise RuntimeError("Bounty pagination safety cap reached")

def enrich_bounties(rows, max_details=30):
    enriched, failures = [], []
    for row in rows[:max_details]:
        bounty_id = row.get("_id") or row.get("id")
        if not bounty_id:
            enriched.append(row)
            continue
        try:
            payload = request_json("/v1/agent/bounties/" + str(bounty_id))
            detail = payload.get("bounty") if isinstance(payload, dict) else None
            merged = dict(row)
            if isinstance(detail, dict):
                merged.update(detail)
            if isinstance(payload, dict):
                merged["_agent_detail"] = {
                    "attachments": payload.get("attachments", []),
                    "claim": payload.get("claim"),
                    "bid": payload.get("bid"),
                    "comments": payload.get("comments", [])
                }
            enriched.append(merged)
        except Exception as exc:
            failed = dict(row)
            failed["_detail_error"] = str(exc)
            enriched.append(failed)
            failures.append(str(bounty_id))
        time.sleep(0.15)
    return enriched, {"details_attempted": min(len(rows), max_details), "detail_failures": failures}

def money(cents):
    if cents is None:
        return None
    try:
        return str(Decimal(str(cents)) / Decimal(100))
    except (InvalidOperation, ValueError, TypeError):
        return None

def normalize(row):
    flow = row.get("flow")
    payout = row.get("payout_cents")
    budget = row.get("budget_cents")
    is_test = row.get("test") is True
    return {
        "platform": "Bounty",
        "task_id": row.get("_id") or row.get("id"),
        "title": row.get("title"),
        "description": row.get("description"),
        "verification": row.get("verification"),
        "category": row.get("category"),
        "tags": row.get("tags") or [],
        "flow": flow,
        "status": row.get("status"),
        "version": row.get("version"),
        "currency": row.get("currency"),
        "payout_amount": money(payout),
        "budget_amount": money(budget),
        "payout_cents": payout,
        "budget_cents": budget,
        "delivery_window_ms": row.get("delivery_window_ms"),
        "expires_at": row.get("expires_at"),
        "test_bounty": is_test,
        "attachments": row.get("_agent_detail", {}).get("attachments", []),
        "has_existing_bid": bool(row.get("_agent_detail", {}).get("bid")),
        "detail_error": row.get("_detail_error"),
        "url": "https://trybounty.ai",
        "writes_enabled": False
    }

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not API_KEY:
        report = {
            "status": "needs_agent_api_key",
            "platform": "Bounty",
            "discovered": 0,
            "message": "Authenticated reads are dormant until BOUNTY_AGENT_API_KEY is stored as a cloud secret.",
            "writes_enabled": False
        }
    else:
        rows, page_meta = page_bounties()
        rows, detail_meta = enrich_bounties(rows)
        report = {
            "status": "ok",
            "platform": "Bounty",
            "fetched_count": len(rows),
            "page_meta": page_meta,
            "detail_meta": detail_meta,
            "opportunities": [normalize(row) for row in rows],
            "writes_enabled": False
        }
    path = OUT / "bounty-opportunities.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "discovered": report.get("fetched_count", 0), "report": str(path)}))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
