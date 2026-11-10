#!/usr/bin/env python3
"""Public GET-only reality check for newly discovered AI-agent marketplaces."""
import json, os, sys, time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pathlib import Path

OUT = Path(os.getenv("REPORT_DIR", "report"))
TIMEOUT = 20
SOURCES = {
    "AgentSouk": {
        "model": "agent_to_agent_wallet_to_wallet",
        "policy": "No custody; buyer pays seller directly in USDC on Base. No escrow protection.",
        "urls": [
            "https://api.agentsouk.dev/v1/opportunities",
            "https://api.agentsouk.dev/v1/demand",
            "https://api.agentsouk.dev/v1/listings?limit=25",
            "https://api.agentsouk.dev/v1/commitments",
            "https://api.agentsouk.dev/v1/payments"
        ]
    },
    "WorkPNP": {
        "model": "agent_to_agent_usdc_escrow",
        "policy": "10% worker fee; registration owner must verify email and X; payout wallet required.",
        "urls": [
            "https://workpnp.com/jobs",
            "https://workpnp.com/api/v1/jobs?status=open&limit=25"
        ]
    },
    "BountyBoardXYZ": {
        "model": "solana_escrow_devnet",
        "policy": "Documentation states currently Solana Devnet only; do not recognize test SOL as cash.",
        "urls": [
            "https://bountyboard.xyz/api/tasks?status=open",
            "https://bountyboard.xyz/api/stats"
        ]
    },
    "Atelier": {
        "model": "ai_service_seller_marketplace",
        "policy": "Agent seller retains 90%; requires owner proof, public HTTP service endpoint and on-chain payout wallet.",
        "urls": [
            "https://api.useatelier.ai/api/platform-stats",
            "https://api.useatelier.ai/api/agents?limit=20"
        ]
    },
    "TaskForce": {
        "model": "agent_task_marketplace_usdc",
        "policy": "Agent API key required for task reads; registration creates API key and Solana wallet; withdrawals need native gas.",
        "urls": [
            "https://task-force.app/api/agent/tasks?limit=20"
        ]
    }
}

def request(url):
    req = Request(url, headers={"Accept":"application/json, text/html;q=0.9", "User-Agent":"NexusCloudWorkEngine/1.0"})
    try:
        with urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read(1_500_001)
            truncated = len(raw) > 1_500_000
            raw = raw[:1_500_000]
            text = raw.decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")
            parsed = None
            if "json" in content_type.lower() or text.lstrip().startswith(("{","[")):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    pass
            return {
                "http_status": response.status,
                "content_type": content_type,
                "content_length_sample": len(raw),
                "truncated": truncated,
                "payload": parsed,
                "text_sample": None if parsed is not None else text[:2500]
            }
    except HTTPError as exc:
        body = exc.read(1200).decode("utf-8", errors="replace")
        return {"http_status": exc.code, "content_type": exc.headers.get("Content-Type", ""), "error_sample": body[:1200]}
    except (URLError, TimeoutError) as exc:
        return {"http_status": None, "error": type(exc).__name__}

def rows_from(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("tasks","jobs","bounties","opportunities","listings","agents","items","data","results"):
            child = value.get(key)
            if isinstance(child, list):
                return child
            if isinstance(child, dict):
                nested = rows_from(child)
                if nested:
                    return nested
    return []

def safe_item(row):
    if not isinstance(row, dict):
        return {"type": type(row).__name__}
    return {
        "id": row.get("id") or row.get("_id") or row.get("task_id") or row.get("slug"),
        "title": row.get("title") or row.get("name"),
        "status": row.get("status"),
        "flow": row.get("flow"),
        "reward": row.get("reward") or row.get("payout") or row.get("amount") or row.get("budget") or row.get("payout_cents"),
        "currency": row.get("currency") or row.get("token") or row.get("rewardCurrency"),
        "escrow": row.get("escrow") or row.get("payment_state") or row.get("funding_status"),
        "url": row.get("url") or row.get("task_url")
    }

def summarize(response):
    payload = response.get("payload")
    if payload is None:
        text = response.get("text_sample") or ""
        return {
            "row_count": None,
            "rows_sample": [],
            "top_level_keys": [],
            "text_sample": text[:1200] if text else None
        }
    rows = rows_from(payload)
    return {
        "row_count": len(rows) if rows else (0 if isinstance(payload, (dict,list)) else None),
        "rows_sample": [safe_item(row) for row in rows[:12]],
        "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
        "summary_fields": {k: payload.get(k) for k in ("success","total","count","totalTasks","activeAgents","totalEscrowed","tasksCompleted","message") if isinstance(payload,dict) and k in payload}
    }

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {}
    for name, spec in SOURCES.items():
        endpoints = []
        for url in spec["urls"]:
            result = request(url)
            endpoints.append({
                "url": url,
                "http_status": result.get("http_status"),
                "content_type": result.get("content_type"),
                "error": result.get("error"),
                "summary": summarize(result)
            })
        sources[name] = {
            "operating_model": spec["model"],
            "policy_note": spec["policy"],
            "endpoints": endpoints
        }
        time.sleep(0.15)
    report = {
        "status": "ok",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "PUBLIC_GET_ONLY",
        "source_count": len(sources),
        "sources": sources,
        "safety": {
            "registration": False,
            "API_key_generation": False,
            "wallet_creation_or_binding": False,
            "bids": False,
            "claims": False,
            "messages": False,
            "submissions": False,
            "payments": False
        },
        "economic_rule": "Treat all listings and advertised rewards as zero income until origin-board terms and actual payout are independently verified."
    }
    path = OUT / "marketplace-reality-check.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status":"ok","source_count":len(sources),"endpoint_count":sum(len(x["endpoints"]) for x in sources.values()),"report":str(path)}))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status":"error","error":str(exc)}), file=sys.stderr)
        raise SystemExit(1)
