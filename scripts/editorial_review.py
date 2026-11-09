#!/usr/bin/env python3
"""Prepare and record human editorial decisions through a restricted Supabase RPC."""
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from editorial_qa import content_review_hash  # noqa: E402


def _config():
    base = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if not base or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required.")
    if key.startswith("sb_publishable_") or key.startswith("sb_anon_"):
        raise RuntimeError("A server-side service key is required; publishable/anon keys are rejected.")
    return base, key


def _request(method, path, payload=None):
    base, key = _config()
    url = f"{base}/rest/v1/{path}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else []
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"Supabase request failed (HTTP {exc.code}): {detail}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Supabase connection failed: {exc.reason}") from None


def _load_item(content_id):
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", content_id):
        raise RuntimeError("content_id must be a UUID.")
    query = urllib.parse.urlencode({
        "select": "id,title,script,metadata,status",
        "id": f"eq.{content_id}",
        "limit": "1",
    })
    rows = _request("GET", f"content_items?{query}")
    if not rows:
        raise RuntimeError("Content item not found or not accessible.")
    item = rows[0]
    metadata = item.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    if not isinstance(metadata, dict):
        raise RuntimeError("Content metadata is not a JSON object.")
    item["metadata"] = metadata
    item["computed_review_hash"] = content_review_hash(
        item.get("title"), item.get("script"), metadata
    )
    return item


def _write_summary(markdown):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(markdown + "\n")
    print(markdown)


def prepare(content_id):
    item = _load_item(content_id)
    if item.get("status") != "pending_editorial_review":
        raise RuntimeError(f"Item is not pending review (status={item.get('status')}).")
    metadata = item["metadata"]
    sources = metadata.get("sources") or []
    source_lines = "\n".join(
        f"- [{source.get('title') or source.get('url')}]({source.get('url')})"
        for source in sources if isinstance(source, dict) and source.get("url")
    ) or "- No source links stored."
    body = f"""# Editorial review package

- Content ID: `{item['id']}`
- Current status: `{item['status']}`
- Review fingerprint: `{item['computed_review_hash']}`
- Evidence status: `{metadata.get('evidence_status', 'not recorded')}`

## Title
{item.get('title') or '(empty)'}

## Description
{metadata.get('description') or '(empty)'}

## Script
{item.get('script') or '(empty)'}

## Hashtags
{' '.join(metadata.get('hashtags') or [])}

## Thumbnail prompt
{metadata.get('thumbnail_prompt') or '(empty)'}

## Source references
{source_lines}

**Review rule:** inspect the actual text and sources above. If any text, source, or metadata changes, prepare again. Use the fingerprint exactly as shown when recording the decision. This workflow records an editorial decision only; it does not publish content.
"""
    _write_summary(body)


def decide(content_id, decision, actor, expected_hash):
    allowed = {
        value.strip().casefold()
        for value in os.environ.get("EDITORIAL_APPROVER_LOGINS", "").split(",")
        if value.strip()
    }
    if not allowed:
        raise RuntimeError("EDITORIAL_APPROVER_LOGINS repository variable is not configured.")
    if not actor or actor.casefold() not in allowed:
        raise RuntimeError("The authenticated GitHub actor is not in EDITORIAL_APPROVER_LOGINS.")
    if decision not in {"approve", "reject"}:
        raise RuntimeError("Decision must be approve or reject.")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash or ""):
        raise RuntimeError("Provide the 64-character fingerprint from the prepared review.")
    item = _load_item(content_id)
    if item.get("status") != "pending_editorial_review":
        raise RuntimeError(f"Item is not pending review (status={item.get('status')}).")
    if item["computed_review_hash"] != expected_hash:
        raise RuntimeError("Fingerprint mismatch: content changed after review. Prepare again.")
    result = _request("POST", "rpc/editorial_review_decide", {
        "p_content_id": content_id,
        "p_decision": decision,
        "p_reviewer_login": actor,
        "p_expected_content_hash": expected_hash,
    })
    _write_summary(
        "# Editorial decision recorded\n\n"
        f"- Content ID: `{content_id}`\n"
        f"- Decision: **{decision.upper()}**\n"
        f"- Authenticated GitHub actor: `{actor}`\n"
        f"- RPC result: `{json.dumps(result, ensure_ascii=False)}`\n\n"
        "**This is not a publishing event.** Publishing remains separately disabled."
    )


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: editorial_review.py prepare <content_id> | decide <content_id> <approve|reject> <github_actor> <expected_hash>")
    mode, content_id = sys.argv[1:3]
    if mode == "prepare" and len(sys.argv) == 3:
        prepare(content_id)
    elif mode == "decide" and len(sys.argv) == 6:
        decide(content_id, sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        raise SystemExit("Invalid arguments.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
