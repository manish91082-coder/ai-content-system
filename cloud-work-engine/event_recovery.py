#!/usr/bin/env python3
"""Durable, read-only Bounty event-feed recovery with cursor persistence."""
import json, os, sys, tempfile, time
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bounty_agent

STATE_DIR = Path(os.getenv("NEXUS_STATE_DIR", ".nexus_state"))
STATE_FILE = STATE_DIR / "bounty_events.json"
REPORT_DIR = Path(os.getenv("REPORT_DIR", "report"))
EVENT_ACTIONS = {
    "bounty.available": "refresh_current_bounty_terms",
    "bounty.updated": "refresh_current_bounty_terms",
    "discussion.user_replied": "review_owner_reply",
    "bounty.claimed": "verify_agent_assignment",
    "work.message.created": "read_private_work_thread",
    "submission.verification_failed": "prepare_revision",
    "submission.review_opened": "await_owner_review",
    "submission.accepted": "settlement_pending",
    "work.completed": "reconcile_settlement",
    "work.ended": "close_work_context"
}
SAFE_DATA_KEYS = {"bounty_id","bounty_version","agent_id","message_id","claim_id","submission_id","reason","status"}

def load_state():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"cursor": None, "events": {}}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"cursor": None, "events": {}}

def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="bounty-events-", suffix=".json", dir=str(STATE_DIR))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, STATE_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

def sanitize_event(event):
    event_type = str(event.get("type") or "unknown")
    subject = event.get("subject") if isinstance(event.get("subject"), dict) else {}
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    safe_data = {key: data[key] for key in SAFE_DATA_KEYS if key in data}
    return {
        "id": str(event.get("id") or ""),
        "type": event_type,
        "version": event.get("version"),
        "occurred_at": event.get("occurredAt"),
        "agent_id": event.get("agentId"),
        "subject_type": subject.get("type"),
        "subject_id": subject.get("id"),
        "data": safe_data,
        "action": EVENT_ACTIONS.get(event_type, "review_unknown_event"),
        "processing_state": "pending"
    }

def fetch_page(cursor=None, limit=100):
    query = {"limit": str(limit)}
    if cursor:
        query["cursor"] = cursor
    return bounty_agent.request_json("/v1/agent/events?" + urlencode(query))

def recover_events(max_pages=100):
    if not bounty_agent.API_KEY:
        return {"status": "needs_agent_api_key", "new_events": 0, "pending_events": 0, "writes_enabled": False}
    state = load_state()
    if not isinstance(state.get("events"), dict):
        state["events"] = {}
    cursor = state.get("cursor")
    pages = added = 0
    cursor_reset = False
    for _ in range(max_pages):
        try:
            payload = fetch_page(cursor)
        except RuntimeError as exc:
            if cursor and "HTTP 400" in str(exc) and not cursor_reset:
                cursor = None
                cursor_reset = True
                continue
            raise
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise RuntimeError("Bounty event-feed schema mismatch")
        for raw in payload["events"]:
            if not isinstance(raw, dict):
                continue
            event = sanitize_event(raw)
            event_id = event["id"]
            if event_id and event_id not in state["events"]:
                state["events"][event_id] = event
                added += 1
        next_cursor = payload.get("next_cursor")
        has_more = payload.get("has_more") is True
        if has_more and (not next_cursor or next_cursor == cursor):
            raise RuntimeError("Bounty event feed returned an invalid or repeated cursor")
        state["cursor"] = next_cursor or cursor
        state["last_sync_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        # Persist new events and cursor atomically before requesting another page.
        save_state(state)
        pages += 1
        cursor = state["cursor"]
        if not has_more:
            break
    else:
        raise RuntimeError("Bounty event pagination safety cap reached")
    if len(state["events"]) > 5000:
        ordered = sorted(state["events"].items(), key=lambda item: str(item[1].get("occurred_at") or ""))
        state["events"] = dict(ordered[-5000:])
        save_state(state)
    pending = sum(1 for event in state["events"].values() if event.get("processing_state") == "pending")
    report = {"status": "ok", "pages_read": pages, "new_events": added,
              "pending_events": pending, "cursor_reset": cursor_reset,
              "event_types": {}, "writes_enabled": False}
    for event in state["events"].values():
        key = event.get("type") or "unknown"
        report["event_types"][key] = report["event_types"].get(key, 0) + 1
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "bounty-events.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report

if __name__ == "__main__":
    try:
        recover_events()
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
