#!/usr/bin/env python3
"""Verify Jobbi shortlist records against original GitHub issues and recent comments."""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

REPORT_DIR = Path(os.getenv("REPORT_DIR", "report"))
INPUT = REPORT_DIR / "jobbi-opportunities.json"
OUTPUT = REPORT_DIR / "jobbi-source-verification.json"
STATE_FILE = Path(os.getenv("NEXUS_STATE_DIR", ".nexus_state")) / "jobbi_source_verified.json"
CACHE_HOURS = int(os.getenv("JOBBI_SOURCE_CACHE_HOURS", "24"))
TOKEN = os.getenv("GITHUB_TOKEN", "")
MAX_CHECKS = int(os.getenv("JOBBI_SOURCE_CHECK_LIMIT", "30"))
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "NexusCloudWorkEngine/1.0",
    "X-GitHub-Api-Version": "2022-11-28"
}
NO_PAY_PATTERNS = [
    r"stopped the bounty program",
    r"payouts? won't work",
    r"no longer (?:pay|paying|accept(?:ing)? bounty)",
    r"do not expect (?:a )?payout",
    r"not accept(?:ing)? (?:any )?bounty claims",
    r"bounty program (?:is )?(?:ended|stopped|closed)",
    r"reward (?:has been )?(?:withdrawn|cancelled|canceled)",
    r"bounty (?:is )?(?:withdrawn|cancelled|canceled|no longer available)"
]
COMPETITION_PATTERNS = [
    r"(?im)^\s*/(?:attempt|claim)\s+#?\d+",
    r"\bsubmitted (?:a )?(?:pr|pull request)\b",
    r"\bpr\s*#\d+\b",
    r"github\.com/[^\s)]+/pull/\d+"
]
BLOCK_LABELS = ("core team only", "on hold", "wontfix", "not planned", "no bounty")

def gh_get(url, retries=3):
    last = None
    for attempt in range(retries):
        headers = dict(HEADERS)
        if TOKEN:
            headers["Authorization"] = "Bearer " + TOKEN
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body), dict(response.headers)
        except HTTPError as exc:
            if exc.code == 429 or (exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0"):
                if attempt + 1 < retries:
                    reset = exc.headers.get("X-RateLimit-Reset")
                    wait = 5
                    if reset:
                        try:
                            wait = max(1, min(int(reset) - int(time.time()) + 1, 30))
                        except ValueError:
                            pass
                    time.sleep(wait)
                    last = "rate_limited"
                    continue
            if exc.code >= 500 and attempt + 1 < retries:
                time.sleep(2 ** attempt)
                last = "http_" + str(exc.code)
                continue
            raise RuntimeError("GitHub returned HTTP " + str(exc.code)) from None
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = type(exc).__name__
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError("GitHub request failed: " + str(last))

def parse_issue_url(url):
    try:
        parsed = urlparse(str(url))
        host = parsed.netloc.lower()
        parts = [x for x in parsed.path.split('/') if x]
        if host in ('oss.issuehunt.io', 'www.oss.issuehunt.io'):
            if len(parts) >= 5 and parts[0] == 'r' and parts[3] in ('issues', 'pull'):
                owner, repository, kind, number = parts[1:5]
                if number.isdigit():
                    return owner + '/' + repository, int(number), kind
            return None
        if host not in ('github.com', 'www.github.com'):
            return None
        if len(parts) < 4 or parts[2] not in ('issues', 'pull'):
            return None
        owner, repository, kind, number = parts[:4]
        if not number.isdigit():
            return None
        return owner + '/' + repository, int(number), kind
    except Exception:
        return None

def candidate_order(item):
    grade = item.get("payout_grade")
    grade_rank = {"A-": 5, "B": 4, "B-": 3}.get(grade, 0)
    try:
        amount = float(item.get("reward_amount") or 0)
    except (TypeError, ValueError):
        amount = 0
    currency = item.get("reward_currency")
    if currency not in ("USD", "USDC", "USDT"):
        amount = 0
    return (grade_rank, float(item.get("priority_score") or 0), amount)

def is_cashworthy(item):
    currency = item.get("reward_currency")
    try:
        amount = float(item.get("reward_amount"))
    except (TypeError, ValueError):
        return False
    threshold = 25 if currency == "USD" else 10 if currency in ("USDC", "USDT") else float("inf")
    return amount >= threshold and item.get("payment_state") == "escrowed" and item.get("claims_open") is True and item.get("lane") == "agent" and item.get("payout_grade") in ("A-", "B", "B-", "C+", "C")

def classify_source(item, issue, comments):
    if not isinstance(issue, dict):
        return "SOURCE_VERIFICATION_INCOMPLETE", "original_board_issue_unavailable"
    if issue.get("state") != "open":
        return "EXCLUDED_SOURCE_CLOSED", "original_issue_not_open"
    if issue.get("locked") is True:
        return "EXCLUDED_SOURCE_LOCKED", "original_issue_discussion_locked"
    labels = [str(x.get("name") or "").strip().lower() for x in issue.get("labels", []) if isinstance(x, dict)]
    if any(any(term in label for term in BLOCK_LABELS) for label in labels):
        return "EXCLUDED_SOURCE_RESTRICTED", "issue_label_blocks_external_bounty_work"
    if issue.get("assignee") or issue.get("assignees"):
        return "EXCLUDED_SOURCE_ASSIGNED", "original_issue_has_assignee"
    if issue.get("pull_request"):
        return "EXCLUDED_SOURCE_IS_PR", "original_url_points_to_pull_request"
    all_comments = comments if isinstance(comments, list) else []
    recent = all_comments[:40] if len(all_comments) > 40 else all_comments
    texts = [str(c.get("body") or "") for c in recent if isinstance(c, dict)]
    for body in texts:
        for pattern in NO_PAY_PATTERNS:
            if re.search(pattern, body, flags=re.IGNORECASE):
                return "EXCLUDED_PAYOUT_WITHDRAWN", "maintainer_comment_indicates_bounty_or_payment_withdrawn"
    claim_hits, pr_hits = 0, 0
    for body in texts:
        if any(re.search(pattern, body, flags=re.IGNORECASE) for pattern in COMPETITION_PATTERNS[:1]):
            claim_hits += 1
        if any(re.search(pattern, body, flags=re.IGNORECASE) for pattern in COMPETITION_PATTERNS[1:]):
            pr_hits += 1
    if claim_hits or pr_hits:
        return "EXCLUDED_COMPETITION", "existing_attempts_or_pull_requests_detected"
    bounty_labels = [label for label in labels if "bounty" in label or "$" in label]
    issue_updated = issue.get("updated_at")
    board = str(item.get("source_board") or "").lower()
    meta = item.get("raw_metadata") if isinstance(item.get("raw_metadata"), dict) else {}
    extra = meta.get("extra") if isinstance(meta.get("extra"), dict) else {}
    funded_at = parse_cache_time(extra.get("funded_at"))
    if board == "issuehunt" and not bounty_labels:
        funded_age = (datetime.now(timezone.utc) - funded_at).days if funded_at else None
        try:
            last_activity = datetime.fromisoformat(str(issue_updated).replace("Z", "+00:00")).astimezone(timezone.utc)
            issue_age = (datetime.now(timezone.utc) - last_activity).days
        except (ValueError, TypeError):
            issue_age = None
        if (funded_age is None or funded_age > 365) and (issue_age is None or issue_age > 180):
            return "EXCLUDED_STALE_UNCONFIRMED_FUNDING", "IssueHunt funding is old and original issue has no bounty label or recent activity"
        return "SOURCE_REVIEW_REQUIRED", "no_bounty_label_on_issue; confirm original board reward terms"
        
    try:
        updated = datetime.fromisoformat(str(issue_updated).replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - updated).days > 180:
            return "SOURCE_REVIEW_REQUIRED", "original_issue_stale_over_180_days; confirm still actionable"
    except (ValueError, TypeError):
        pass
    return "CANDIDATE_NEEDS_OPERATOR_GATE", "issue_open_unassigned_no_recent_attempt_or_pr_in_reviewed_comments; operator gate required for board claim and payout terms"

def verify_one(item):
    parsed = parse_issue_url(item.get("original_url"))
    if not parsed:
        return {**item, "source_decision": "SOURCE_VERIFICATION_UNSUPPORTED", "source_reason": "non_github_origin_requires_board_specific_adapter"}
    repository, number, kind = parsed
    issue_url = "https://api.github.com/repos/" + repository + "/issues/" + str(number)
    comments_url = issue_url + "/comments?per_page=100&sort=created&direction=desc"
    try:
        issue, _ = gh_get(issue_url)
        comments, _ = gh_get(comments_url)
        if not isinstance(comments, list):
            raise RuntimeError("GitHub comments response schema mismatch")
        decision, reason = classify_source(item, issue, comments)
        return {
            "id": item.get("id"), "title": item.get("title"),
            "source_board": item.get("source_board"),
            "original_url": item.get("original_url"),
            "reward_amount": item.get("reward_amount"),
            "reward_currency": item.get("reward_currency"),
            "payout_grade": item.get("payout_grade"),
            "payment_state": item.get("payment_state"),
            "acceptance": item.get("acceptance"),
            "issue_state": issue.get("state"),
            "issue_locked": issue.get("locked"),
            "issue_updated_at": issue.get("updated_at"),
            "issue_labels": [x.get("name") for x in issue.get("labels", []) if isinstance(x, dict)],
            "issue_assignee_count": len(issue.get("assignees") or []),
            "issue_comments_count": issue.get("comments"),
            "comments_checked": len(comments),
            "source_decision": decision,
            "source_reason": reason,
            "checked_at_utc": datetime.now(timezone.utc).isoformat()
        }
    except Exception as exc:
        return {
            "id": item.get("id"), "title": item.get("title"),
            "source_board": item.get("source_board"),
            "original_url": item.get("original_url"),
            "source_decision": "SOURCE_VERIFICATION_INCOMPLETE",
            "source_reason": str(exc),
            "checked_at_utc": datetime.now(timezone.utc).isoformat()
        }

def parse_cache_time(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None

def load_cache():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

def save_cache(cache):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(cache, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")

def item_signature(item):
    payload = {key: item.get(key) for key in ("title", "summary", "original_url", "reward_amount", "reward_currency", "payment_state", "payout_grade", "claims_open")}
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)

def main():
    if not INPUT.exists():
        raise RuntimeError("Jobbi feed report missing")
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    rows = [x for x in source.get("opportunities", []) if is_cashworthy(x)]
    rows.sort(key=candidate_order, reverse=True)
    cache = load_cache()
    now = datetime.now(timezone.utc)
    selected = []
    cached_skipped = 0
    for item in rows:
        key = str(item.get("id") or "")
        signature = item_signature(item)
        cached = cache.get(key) if key else None
        checked = parse_cache_time(cached.get("checked_at_utc")) if isinstance(cached, dict) else None
        reusable = (
            isinstance(cached, dict)
            and cached.get("signature") == signature
            and checked is not None
            and (now - checked) < timedelta(hours=CACHE_HOURS)
            and cached.get("result", {}).get("source_decision") != "SOURCE_VERIFICATION_INCOMPLETE"
        )
        if reusable:
            cached_skipped += 1
            continue
        selected.append(item)
        if len(selected) >= MAX_CHECKS:
            break
    results = []
    for item in selected:
        result = verify_one(item)
        results.append(result)
        key = str(item.get("id") or "")
        if key:
            cache[key] = {"signature": item_signature(item), "checked_at_utc": now.isoformat(), "result": result}
        save_cache(cache)
    counts = {}
    for row in results:
        key = row["source_decision"]
        counts[key] = counts.get(key, 0) + 1
    eligible = [x for x in results if x["source_decision"] == "CANDIDATE_NEEDS_OPERATOR_GATE"]
    report = {
        "status": "ok",
        "jobbi_feed_candidates": len(rows),
        "source_checks_attempted": len(results),
        "cached_results_skipped": cached_skipped,
        "verification_cache_size": len(cache),
        "source_decision_counts": counts,
        "operator_gate_candidates": eligible,
        "results": results,
        "policy": "No account, claim, bid, PR, message, or submission is performed. A source-level candidate still requires operator authorization and a manual payout/terms check.",
        "github_api_auth_configured": bool(TOKEN),
        "income_recognized": 0
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "jobbi_candidates": len(rows),
        "source_checks": len(results),
        "cached_skipped": cached_skipped,
        "source_decisions": counts,
        "operator_gate_candidates": len(eligible),
        "report": str(OUTPUT)
    }, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
