#!/usr/bin/env python3
"""Hourly read-only Jobbi JSON Feed importer and evidence-first task ranker."""
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = os.getenv("JOBBI_FEED_URL", "https://jobbi.org/gigs.json")
OUT = Path(os.getenv("REPORT_DIR", "report"))
STATE_DIR = Path(os.getenv("NEXUS_STATE_DIR", ".nexus_state"))
STATE_FILE = STATE_DIR / "jobbi_feed_state.json"
HEADERS = {
    "Accept": "application/feed+json, application/json;q=0.9",
    "User-Agent": "NexusCloudWorkEngine/1.0"
}
CASH_CURRENCIES = {"USD", "USDC", "USDT"}
GRADE_SCORE = {"A-": 100, "B": 85, "B-": 72, "C+": 55, "C": 40, "C-": 25, "D": 5}
RISK_TERMS = {
    "exploit", "malware", "credential theft", "steal credentials", "private key",
    "security remediation", "iam key", "civil id", "identity document",
    "personal health", "diagnosis", "medical advice", "legal advice",
    "financial advice", "investment advice", "trading strategy", "gambling",
    "physical visit", "in person", "in-person", "take your own photo",
    "schoolwork", "homework", "write my essay", "complete my assignment",
    "human subjects", "private customer data"
}
TASK_TERMS = {
    "code": 12, "coding": 12, "github": 10, "pull request": 10, "feature": 8,
    "bug": 8, "python": 10, "javascript": 10, "typescript": 10,
    "documentation": 8, "openapi": 8, "research": 6, "data": 6,
    "automation": 8, "api": 8, "test": 7, "testing": 7,
    "parsing": 8, "cli": 6, "mcp": 8, "stdlib": 8
}

def load_state():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.stem + "-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def fetch_feed():
    state = load_state()
    query = urlencode({"lane": "agent", "limit": "1000"})
    url = BASE + ("&" if "?" in BASE else "?") + query
    headers = dict(HEADERS)
    if state.get("etag"):
        headers["If-None-Match"] = state["etag"]
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=45) as response:
            body = response.read().decode("utf-8")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as exc:
                raise RuntimeError("Jobbi feed body is not valid JSON Feed") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                raise RuntimeError("Jobbi JSON Feed schema mismatch: items must be an array")
            state["etag"] = response.headers.get("ETag") or state.get("etag")
            state["last_modified"] = response.headers.get("Last-Modified")
            state["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
            state["feed_hash"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
            state["feed_body"] = body
            atomic_write(STATE_FILE, json.dumps(state, ensure_ascii=False, indent=2))
            return payload, {"http_status": 200, "not_modified": False, "etag_present": bool(state.get("etag"))}
    except HTTPError as exc:
        if exc.code == 304:
            body = state.get("feed_body")
            if not isinstance(body, str) or not body:
                raise RuntimeError("Jobbi returned 304 but no cached feed exists")
            payload = json.loads(body)
            return payload, {"http_status": 304, "not_modified": True, "etag_present": True}
        raise RuntimeError("Jobbi feed HTTP " + str(exc.code)) from None
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Jobbi feed connection failed: " + type(exc).__name__) from None

def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        try:
            return parsedate_to_datetime(str(value)).astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            return None

def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

def field(record, *keys):
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return None

def normalize(item):
    meta = item.get("_jobbi") if isinstance(item.get("_jobbi"), dict) else {}
    reward = meta.get("reward") if isinstance(meta.get("reward"), dict) else {}
    amount = number(reward.get("amount"))
    currency = str(reward.get("currency") or "").upper()
    source_raw = meta.get("source")
    source_meta = source_raw if isinstance(source_raw, dict) else {}
    source = field(source_meta, "key", "board", "name") or (source_raw if isinstance(source_raw, str) else None)
    expires = meta.get("expires")
    return {
        "id": str(item.get("id") or ""),
        "title": str(item.get("title") or ""),
        "summary": str(item.get("content_text") or item.get("summary") or ""),
        "original_url": item.get("url"),
        "date_published": item.get("date_published"),
        "date_modified": item.get("date_modified"),
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
        "lane": meta.get("lane"),
        "source_board": source,
        "reward_amount": str(amount) if amount is not None else None,
        "reward_currency": currency or None,
        "payment_rail": reward.get("rail"),
        "acceptance": meta.get("acceptance"),
        "acceptance_type": meta.get("acceptance_type"),
        "payment_state": meta.get("payment_state"),
        "payout_grade": str(meta.get("payout_grade") or "").upper(),
        "expires": expires,
        "claims_open": meta.get("claims_open") is True,
        "jobbi_first_seen": meta.get("first_seen"),
        "raw_metadata": meta
    }

def classify(item, now=None):
    now = now or datetime.now(timezone.utc)
    if not item.get("id") or not item.get("original_url"):
        return "EXCLUDED", "missing_stable_id_or_original_board_url"
    if item.get("lane") != "agent":
        return "EXCLUDED", "not_agent_lane"
    if item.get("claims_open") is not True:
        return "EXCLUDED", "claims_not_open"
    expiry = parse_datetime(item.get("expires"))
    if expiry and expiry <= now:
        return "EXCLUDED", "expired"
    text = " ".join([
        item.get("title") or "",
        item.get("summary") or "",
        " ".join(str(x) for x in item.get("tags") or [])
    ]).lower()
    for term in sorted(RISK_TERMS, key=len, reverse=True):
        if term in text:
            return "EXCLUDED", "restricted_or_non_autonomous_task:" + term
    currency = item.get("reward_currency")
    amount = number(item.get("reward_amount"))
    if currency not in CASH_CURRENCIES or amount is None:
        return "EXCLUDED", "non_cash_or_unpriced_reward"
    min_amount = Decimal("10") if currency == "USD" else Decimal("5")
    if amount < min_amount:
        return "EXCLUDED", "below_minimum_cash_reward"
    if item.get("payment_state") != "escrowed":
        if item.get("payment_state") == "promised":
            return "REVIEW_REQUIRED", "promised_payment_not_escrowed"
        return "BLOCKED", "payment_state_unknown_or_unverified"
    grade = item.get("payout_grade")
    if grade not in ("A-", "B", "B-", "C+", "C"):
        return "REVIEW_REQUIRED", "payout_evidence_grade_needs_manual_source_check"
    return "SOURCE_REVIEW_REQUIRED", "escrowed_agent_lane_cash_gig; verify origin board acceptance and operator payout eligibility"

def capability_score(item):
    text = " ".join([item.get("title") or "", item.get("summary") or "", " ".join(item.get("tags") or [])]).lower()
    skill_points = sum(points for term, points in TASK_TERMS.items() if term in text)
    grade_points = GRADE_SCORE.get(item.get("payout_grade"), 0)
    amount = number(item.get("reward_amount")) or Decimal(0)
    amount_points = min(25, int(amount / Decimal(20))) if item.get("reward_currency") in CASH_CURRENCIES else 0
    acceptance_points = 8 if item.get("acceptance_type") == "machine" else 3 if item.get("acceptance_type") == "human-review" else 0
    rail = str(item.get("payment_rail") or "").lower()
    rail_points = 4 if rail in ("stripe", "usdc-base", "onchain-gnosis") else 0
    return min(100, skill_points + int(grade_points * 0.35) + amount_points + acceptance_points + rail_points)

def run(payload, fetch_meta=None, now=None):
    now = now or datetime.now(timezone.utc)
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise RuntimeError("Jobbi JSON Feed has no items array")
    normalized = []
    seen = set()
    for raw in items:
        if not isinstance(raw, dict):
            continue
        item = normalize(raw)
        if not item["id"] or item["id"] in seen:
            continue
        seen.add(item["id"])
        item["decision"], item["reason"] = classify(item, now)
        item["priority_score"] = capability_score(item)
        normalized.append(item)
    normalized.sort(key=lambda x: (x["decision"] == "SOURCE_REVIEW_REQUIRED", x["priority_score"]), reverse=True)
    counts = {}
    for item in normalized:
        counts[item["decision"]] = counts.get(item["decision"], 0) + 1
    candidates = [x for x in normalized if x["decision"] == "SOURCE_REVIEW_REQUIRED"]
    return {
        "status": "ok",
        "feed_title": payload.get("title"),
        "generated_at_utc": now.isoformat(),
        "feed_item_count": len(items),
        "unique_agent_gigs": len(normalized),
        "decision_counts": counts,
        "source_review_candidates": len(candidates),
        "top_candidates": candidates[:25],
        "opportunities": normalized,
        "index_notice": "Jobbi is an index only. Verify every task on the original board; Jobbi does not hold funds, accept work, verify work, or pay.",
        "fetch": fetch_meta or {},
        "income_recognized": 0,
        "marketplace_writes": False
    }

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    payload, fetch_meta = fetch_feed()
    result = run(payload, fetch_meta)
    path = OUT / "jobbi-opportunities.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "feed_items": result["feed_item_count"],
        "candidates": result["source_review_candidates"],
        "decision_counts": result["decision_counts"],
        "not_modified": fetch_meta["not_modified"],
        "report": str(path)
    }, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
