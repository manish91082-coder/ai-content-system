#!/usr/bin/env python3
"""MoltJobs cash-task watchlist with escrow transition detection; no bids or claims."""
import glob
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPORT_DIR = Path(os.getenv("REPORT_DIR", "report"))
STATE_DIR = Path(os.getenv("NEXUS_STATE_DIR", ".nexus_state"))
STATE_FILE = STATE_DIR / "moltjobs_funding_state.json"
MIN_USDC = Decimal(os.getenv("MOLTJOBS_MIN_WATCH_USDC", "50"))
RISK_TERMS = (
    "investment advice", "portfolio recommendation", "wealth management advice",
    "buy or sell", "securities recommendation", "legal advice", "regulated financial advice",
    "guaranteed return", "stock picks"
)

def latest_scan():
    paths = sorted(glob.glob(str(REPORT_DIR / "opportunities-*.json")))
    if not paths:
        raise RuntimeError("No primary scanner opportunity report found")
    with open(paths[-1], encoding="utf-8") as handle:
        return json.load(handle), paths[-1]

def money(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

def evaluate(item):
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    title = str(item.get("title") or "")
    description = str(item.get("description") or "")
    text = (title + " " + description + " " + json.dumps(raw.get("inputData") or {}, ensure_ascii=False)).lower()
    task_id = str(item.get("task_id") or "")
    status = str(raw.get("status") or item.get("status") or "").lower()
    purpose = str(raw.get("purpose") or "").upper()
    mode = str(raw.get("participationMode") or "").upper()
    currency = str(raw.get("tokenSymbol") or item.get("reward_currency") or "").upper()
    amount = money(raw.get("budgetUsdc") or item.get("reward_amount"))
    funded = raw.get("funded") is True
    escrow_tx = raw.get("escrowTxHash")
    payment_status = str(raw.get("paymentStatus") or "").lower()
    criteria = raw.get("acceptanceCriteria") if isinstance(raw.get("acceptanceCriteria"), list) else []
    deadline = raw.get("deadlineAt") or item.get("deadline")
    reasons = []

    if status != "open":
        decision = "EXCLUDED_NOT_OPEN"
        reasons.append("source task is not currently open")
    elif purpose != "MARKETPLACE" or mode not in ("BID", "CLAIM"):
        decision = "EXCLUDED_NON_MARKETPLACE"
        reasons.append("not an independent marketplace assignment")
    elif any(term in text for term in RISK_TERMS):
        decision = "EXCLUDED_HIGH_RISK_DOMAIN"
        reasons.append("regulated financial/legal or guaranteed-return advice")
    elif currency != "USDC" or amount is None or amount < MIN_USDC:
        decision = "EXCLUDED_LOW_VALUE_OR_NON_CASH"
        reasons.append("below minimum value or payout token is not USDC")
    elif not funded or not escrow_tx:
        decision = "WATCH_ESCROW_PENDING"
        reasons.append("listed budget is not funded escrow; wait for explicit funded state and escrow transaction")
    else:
        decision = "FUNDED_REQUIRES_AGENT_ASSIGNMENT"
        reasons.append("escrow evidence is present; still requires authorized agent bid/claim acceptance")

    # Rank only for ordering a watchlist, never as a probability of acceptance.
    score = 0
    if decision in ("WATCH_ESCROW_PENDING", "FUNDED_REQUIRES_AGENT_ASSIGNMENT"):
        score += min(50, int(amount or 0) // 3)
        score += min(30, len(criteria) * 5)
        if any(term in text for term in ("landing page", "website", "responsive", "html")):
            score += 15
        if mode == "CLAIM":
            score += 5
    return {
        "task_id": task_id,
        "title": title,
        "url": item.get("source_url"),
        "mode": mode,
        "purpose": purpose,
        "status": status,
        "currency": currency,
        "listed_budget": str(amount) if amount is not None else None,
        "acceptance_criteria_count": len(criteria),
        "acceptance_criteria": criteria,
        "deadline_at": deadline,
        "created_at": raw.get("createdAt"),
        "updated_at": raw.get("updatedAt"),
        "funded": funded,
        "escrow_tx_hash": escrow_tx,
        "escrow_job_id": raw.get("escrowJobId"),
        "payment_status": payment_status or None,
        "poster": (raw.get("poster") or {}).get("displayName") if isinstance(raw.get("poster"), dict) else None,
        "decision": decision,
        "decision_reasons": reasons,
        "priority_score": score,
        "work_authorized": False,
        "bid_or_claim_sent": False,
        "income_recognized": "0"
    }

def build_watchlist(report):
    tasks = []
    for item in report.get("opportunities", []):
        if item.get("platform") != "MoltJobs":
            continue
        result = evaluate(item)
        if result["decision"] not in ("EXCLUDED_NOT_OPEN", "EXCLUDED_NON_MARKETPLACE", "EXCLUDED_HIGH_RISK_DOMAIN", "EXCLUDED_LOW_VALUE_OR_NON_CASH"):
            tasks.append(result)
    tasks.sort(key=lambda x: (x["decision"] == "FUNDED_REQUIRES_AGENT_ASSIGNMENT", x["priority_score"], float(x["listed_budget"] or 0)), reverse=True)
    return tasks

def detect_funding_transitions(tasks):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        previous = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            previous = {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        previous = {}
    current = {}
    transitions = []
    for task in tasks:
        ident = task["task_id"]
        if not ident:
            continue
        current[ident] = {
            "funded": task["funded"],
            "escrow_tx_hash": task["escrow_tx_hash"],
            "payment_status": task["payment_status"],
            "title": task["title"],
            "url": task["url"],
            "listed_budget": task["listed_budget"],
            "decision": task["decision"]
        }
        old = previous.get(ident, {})
        if task["funded"] and task["escrow_tx_hash"] and not (old.get("funded") and old.get("escrow_tx_hash")):
            transitions.append({
                "task_id": ident,
                "title": task["title"],
                "url": task["url"],
                "transition": "ESCROW_BECAME_FUNDED",
                "escrow_tx_hash": task["escrow_tx_hash"],
                "action": "reverify chain receipt and agent assignment terms"
            })
    STATE_FILE.write_text(json.dumps(current, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    return transitions

def main():
    report, source_path = latest_scan()
    tasks = build_watchlist(report)
    transitions = detect_funding_transitions(tasks)
    result = {
        "status": "ok",
        "source_report": source_path,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "watchlist_count": len(tasks),
        "funded_waiting_for_agent_assignment": sum(x["decision"] == "FUNDED_REQUIRES_AGENT_ASSIGNMENT" for x in tasks),
        "unfunded_budget_watch": sum(x["decision"] == "WATCH_ESCROW_PENDING" for x in tasks),
        "newly_funded_transitions": transitions,
        "watchlist": tasks,
        "policy": "A listed budget is not funded escrow. Funding transition still does not authorize a claim or count as income.",
        "marketplace_writes": False,
        "income_recognized": 0
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "moltjobs-watchlist.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "watchlist": len(tasks),
        "unfunded": result["unfunded_budget_watch"],
        "newly_funded": len(transitions),
        "report": str(path)
    }, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import sys
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
