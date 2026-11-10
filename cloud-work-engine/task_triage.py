#!/usr/bin/env python3
"""Deterministic opportunity triage. No marketplace writes and no paid inference."""
import json
import os
from pathlib import Path

REPORT_DIR = Path(os.getenv("REPORT_DIR", "report"))
ALLOWED = {"software", "coding", "development", "data", "research", "writing", "content", "automation", "analysis", "translation", "design", "documentation"}
BLOCKED = {"medical", "healthcare diagnosis", "legal advice", "investment advice", "financial advice", "trading", "gambling", "adult", "surveillance", "credential theft", "malware", "exploit", "weapon"}
NEEDS_EXTERNAL = {"account login", "personal account", "identity verification", "purchase required", "buy product", "install app", "phone call", "in-person", "physical delivery", "paid subscription", "private customer data"}

def classify(item):
    text = " ".join(str(item.get(k) or "") for k in ("title", "description", "verification", "category", "tags")).lower()
    if item.get("test_bounty"):
        return "EXCLUDED", "test_bounty_no_money_moves"
    if item.get("status") != "open":
        return "EXCLUDED", "not_open"
    if any(term in text for term in BLOCKED):
        return "EXCLUDED", "high_risk_or_restricted_domain"
    if any(term in text for term in NEEDS_EXTERNAL):
        return "REVIEW_REQUIRED", "external_dependency_or_sensitive_data"
    flow = item.get("flow")
    payout = item.get("payout_cents")
    budget = item.get("budget_cents")
    if flow == "claim" and isinstance(payout, int) and payout > 0:
        fixed = True
    elif flow == "bid":
        fixed = False
    else:
        return "REVIEW_REQUIRED", "unknown_payout_flow"
    category = str(item.get("category") or "").lower()
    tag_match = any(t in text for t in ALLOWED)
    if category not in ALLOWED and not tag_match:
        return "REVIEW_REQUIRED", "capability_category_not_yet_supported"
    if not fixed and not (isinstance(budget, int) and budget >= 500):
        return "REVIEW_REQUIRED", "bid_budget_missing_or_below_platform_minimum"
    return "CANDIDATE_REQUIRES_ECONOMIC_QA", "fixed_payout" if fixed else "bid_budget_is_only_a_pricing_signal"

def main():
    path = REPORT_DIR / "bounty-opportunities.json"
    if not path.exists():
        result = {"status": "no_input", "candidates": []}
    else:
        source = json.loads(path.read_text(encoding="utf-8"))
        candidates = []
        for item in source.get("opportunities", []):
            decision, reason = classify(item)
            candidates.append({
                "task_id": item.get("task_id"),
                "title": item.get("title"),
                "flow": item.get("flow"),
                "payout_amount": item.get("payout_amount"),
                "budget_amount": item.get("budget_amount"),
                "currency": item.get("currency"),
                "decision": decision,
                "reason": reason,
                "next_stage": "independent_acceptance_criteria_and_cost_estimate" if decision == "CANDIDATE_REQUIRES_ECONOMIC_QA" else "none"
            })
        result = {"status": source.get("status"), "candidate_count": sum(x["decision"] == "CANDIDATE_REQUIRES_ECONOMIC_QA" for x in candidates), "items": candidates, "marketplace_writes": False}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = REPORT_DIR / "bounty-triage.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "candidate_count": result.get("candidate_count", 0), "report": str(output)}))

if __name__ == "__main__":
    main()
