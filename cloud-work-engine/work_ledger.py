#!/usr/bin/env python3
"""Reconcile Bounty lifecycle signals without claiming payout before proof."""
import json
import os
from pathlib import Path

STATE_DIR = Path(os.getenv("NEXUS_STATE_DIR", ".nexus_state"))
REPORT_DIR = Path(os.getenv("REPORT_DIR", "report"))
EVENT_STATE = STATE_DIR / "bounty_events.json"
SOURCE_REPORT = REPORT_DIR / "bounty-opportunities.json"

EVENT_STATES = {
    "bounty.available": ("DISCOVERY_REFRESHED", False, "refresh_terms_before_any_action"),
    "bounty.updated": ("TERMS_CHANGED_RECHECK_REQUIRED", False, "re-evaluate_current_version"),
    "discussion.user_replied": ("OWNER_REPLY_PENDING", False, "read_owner_reply"),
    "bounty.claimed": ("HIRED_ASSIGNMENT_VERIFY", False, "confirm_agent_owns_active_claim"),
    "work.message.created": ("OWNER_MESSAGE_PENDING", False, "fetch_and_review_work_thread"),
    "submission.verification_failed": ("REVISION_REQUIRED", False, "revise_against_verification_feedback"),
    "submission.review_opened": ("OWNER_REVIEW", False, "await_owner_review"),
    "submission.accepted": ("ACCEPTED_NOT_YET_CASH", False, "await_settlement_event_and_payout"),
    "work.completed": ("SETTLEMENT_EVENT_SEEN_UNRECONCILED", False, "verify_actual_payout_independently"),
    "work.ended": ("WORK_ENDED_NO_COMPLETION_CREDIT", False, "close_context_and_do_not_count_income")
}

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default

def reconcile(active_work=None, events=None):
    active_work = active_work if isinstance(active_work, list) else []
    events = events if isinstance(events, dict) else {}
    active = {}
    for item in active_work:
        key = str(item.get("task_id") or "")
        if key:
            active[key] = {
                "title": item.get("title"),
                "status": item.get("status"),
                "claim_status": item.get("claim_status"),
                "claim_id": item.get("claim_id"),
                "version": item.get("version")
            }
    event_rows = []
    for event_id, event in events.items():
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("type") or "unknown")
        state, cash_credit, next_action = EVENT_STATES.get(
            event_type, ("UNCLASSIFIED_EVENT", False, "review_event_type")
        )
        bounty_id = str(event.get("subject_id") or event.get("data", {}).get("bounty_id") or "")
        work = active.get(bounty_id)
        if event_type == "bounty.claimed" and work and work.get("claim_status") == "active":
            state = "HIRED_ACTIVE_CLAIM_CONFIRMED_BY_ACTIVE_WORK_LIST"
        event_rows.append({
            "event_id": event_id,
            "event_type": event_type,
            "bounty_id": bounty_id or None,
            "lifecycle_state": state,
            "active_work_match": bool(work),
            "active_work": work,
            "event_processing_state": event.get("processing_state", "pending"),
            "cash_credit": cash_credit,
            "recognized_income": 0,
            "next_action": next_action
        })
    return {
        "status": "ok",
        "active_work_count": len(active),
        "event_count": len(event_rows),
        "events": event_rows,
        "financial_ledger": {
            "accepted_submissions": sum(x["lifecycle_state"] == "ACCEPTED_NOT_YET_CASH" for x in event_rows),
            "settlement_events_unreconciled": sum(x["lifecycle_state"] == "SETTLEMENT_EVENT_SEEN_UNRECONCILED" for x in event_rows),
            "recognized_income": 0,
            "rule": "No income is recognized from acceptance or work.completed alone; actual payout must be independently reconciled."
        },
        "marketplace_writes": False
    }

def main():
    source = read_json(SOURCE_REPORT, {})
    state = read_json(EVENT_STATE, {"events": {}})
    result = reconcile(source.get("active_work", []), state.get("events", {}))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "bounty-work-ledger.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "active_work": result["active_work_count"], "events": result["event_count"], "recognized_income": 0}))

if __name__ == "__main__":
    main()
