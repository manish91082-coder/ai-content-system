#!/usr/bin/env python3
"""Read-only multi-marketplace opportunity scanner. Python standard library only."""
import json, os, sys, time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

OUT = os.getenv("REPORT_DIR", "report")
os.makedirs(OUT, exist_ok=True)
HEADERS = {"Accept":"application/json","User-Agent":"NexusCloudWorkEngine/0.2"}
MOLT = os.getenv("MOLTJOBS_API_BASE", "https://api.moltjobs.io/v1")
DEALWORK = os.getenv("DEALWORK_API_BASE", "https://api.dealwork.ai/api/v1")
TASKMARKET = os.getenv("TASKMARKET_API_BASE", "https://api.taskmarket.dev")

def get_json(url, attempts=3):
    last = None
    for n in range(attempts):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=20) as res:
                return json.loads(res.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = str(exc)
            if isinstance(exc, HTTPError) and exc.code not in (429,500,502,503,504):
                break
            if n + 1 < attempts:
                time.sleep(min(2 ** n, 5))
    raise RuntimeError("GET failed: " + str(last))

def first(obj, *keys):
    for key in keys:
        value = obj.get(key) if isinstance(obj, dict) else None
        if value is not None and value != "":
            return value
    return None

def extract_rows(payload, preferred=()):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in preferred + ("data","tasks","jobs","items","results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for nested in preferred + ("tasks","jobs","items","results"):
                if isinstance(value.get(nested), list):
                    return value[nested]
    return []

def decimal_base_units(value, decimals=6):
    if value is None:
        return None
    try:
        return str(Decimal(str(value)) / (Decimal(10) ** decimals))
    except (InvalidOperation, ValueError, TypeError):
        return None

def normalize(platform, row, now):
    if not isinstance(row, dict):
        return None
    if platform == "MoltJobs":
        task_id = first(row,"id","jobId")
        reward = first(row,"budgetUsdc","reward","budget")
        currency = first(row,"currency","rewardCurrency") or ("USDC" if first(row,"budgetUsdc") is not None else None)
        funding = "FUNDED_FILTER_RETURNED" if row.get("_funded_filter") else "UNKNOWN"
        mode = first(row,"participationMode","mode","purpose")
        source = "https://moltjobs.io/open-jobs"
        title = first(row,"title","name")
        desc = first(row,"description","details")
        chain = first(row,"chain","network")
        status = first(row,"status")
        tags = row.get("tags") or []
        expiry = first(row,"deadline","expiresAt","expiryTime")
        actor = first(row,"requesterActorType","posterType")
    elif platform == "Dealwork":
        task_id = first(row,"id","jobId")
        reward = first(row,"fixedPrice","budgetMax","reward","budget","amount","price","maxBudget")
        currency = first(row,"currency","token","paymentToken") or ("USD" if first(row,"fixedPrice","budgetMax","budgetMin") is not None else None)
        funding = "FUNDED_FLAG_TRUE" if row.get("posterFunded") is True else ("UNFUNDED_FLAG_FALSE" if row.get("posterFunded") is False else ("CONFIRMED_ESCROW_FIELD" if str(first(row,"escrowStatus","escrow_status") or "").lower() in ("locked","funded","escrowed") or row.get("escrowLocked") is True else "UNKNOWN"))
        mode = first(row,"jobMode","type","mode","jobType")
        source = first(row,"url","webUrl","jobUrl") or ("https://api.dealwork.ai/jobs/" + str(task_id) if task_id else "https://api.dealwork.ai/")
        title = first(row,"title","name")
        desc = first(row,"description","details")
        chain = first(row,"chain","network")
        status = first(row,"status")
        tags = row.get("tags") or []
        expiry = first(row,"deadline","expiresAt","dueDate")
        actor = first(row,"requesterActorType","posterType")
    else:
        task_id = first(row,"id","taskId")
        raw_reward = first(row,"reward")
        reward = decimal_base_units(raw_reward, 6)
        chain_id = first(row,"chainId")
        chain = {"8453":"Base","4217":"Tempo",8453:"Base",4217:"Tempo"}.get(chain_id, str(chain_id) if chain_id is not None else None)
        currency = "USDC" if str(chain_id) == "8453" else ("OUSD" if str(chain_id) == "4217" else None)
        funding = "ESCROW_TX_REFERENCE_PRESENT" if first(row,"escrowTxHash") else "UNKNOWN"
        mode = first(row,"mode")
        source = "https://api.taskmarket.dev/"
        title = first(row,"title") or (str(first(row,"description") or "")[:100])
        desc = first(row,"description")
        status = first(row,"status")
        tags = row.get("tags") or []
        expiry = first(row,"expiryTime")
        actor = first(row,"requesterActorType")
    return {
        "platform":platform, "task_id":str(task_id) if task_id is not None else None,
        "title":title, "description":desc, "reward_amount":reward,
        "reward_raw_base_units":str(first(row,"reward")) if platform == "Taskmarket" and first(row,"reward") is not None else None,
        "reward_currency":currency, "chain":chain, "funded_or_escrow_status":funding,
        "actor_type":actor, "task_mode":mode, "status":status, "deadline":expiry,
        "tags":tags if isinstance(tags,list) else [], "acceptance_criteria":first(row,"acceptanceCriteria","criteria"),
        "source_url":source, "fetched_at":now, "raw":row,
        "write_actions_enabled":False
    }

def classify(platform, row):
    if platform == "MoltJobs":
        purpose = str(first(row,"purpose") or "").upper()
        mode = str(first(row,"participationMode") or "").upper()
        if purpose == "PLATFORM_REFERRAL" or mode == "AUTOMATIC_FORUM_REWARD":
            return "EXCLUDED", "referral_or_forum_reward_not_a_normal_work_assignment"
        return "REVIEW_REQUIRED", "requires_detail_funding_permissions_and_payout_review"
    if platform == "Dealwork":
        if str(first(row,"status") or "").lower() not in ("posted","open","active","published","available","bidding"):
            return "EXCLUDED", "job_not_in_open_status"
        if row.get("posterFunded") is False or str(first(row,"claimBlockedReason") or "").lower() in ("underfunded","poster_unfunded"):
            return "BLOCKED", "poster_funding_not_locked"
        if str(first(row,"eligibleWorkerTypes") or "").lower() == "human_only":
            return "EXCLUDED", "human_only_worker_restriction"
        return "REVIEW_REQUIRED", "funding_and_ai_permission_not_yet_proven"
    status = str(first(row,"status") or "").lower()
    if status != "open":
        return "EXCLUDED", "task_not_open"
    if not first(row,"escrowTxHash"):
        return "BLOCKED", "escrow_transaction_reference_missing"
    return "REVIEW_REQUIRED", "escrow_reference_present_but_onchain_and_task_terms_need_verification"

def scan_molt():
    rows, cursor, seen, pages = [], None, set(), []
    for _ in range(20):
        params={"status":"OPEN","funded":"true","limit":"100"}
        if cursor: params["cursor"]=cursor
        payload=get_json(MOLT.rstrip("/")+"/jobs?"+urlencode(params))
        pages.append(payload)
        batch=extract_rows(payload,("data",))
        for row in batch:
            if isinstance(row,dict):
                row=dict(row); row["_funded_filter"]=True
                ident=str(first(row,"id","jobId") or "")
                if not ident or ident not in seen:
                    rows.append(row)
                    if ident: seen.add(ident)
        meta=payload.get("meta") or payload.get("pagination") or {} if isinstance(payload,dict) else {}
        cursor=first(payload,"nextCursor","next_cursor") or first(meta,"nextCursor","next_cursor")
        if not cursor: break
        time.sleep(2)
    else:
        raise RuntimeError("MoltJobs pagination safety cap reached")
    return rows, {"pages":len(pages),"funded_filter":"true"}

def scan_dealwork():
    url=DEALWORK.rstrip("/")+"/jobs?"+urlencode({"per_page":20,"sort":"newest"})
    payload=get_json(url)
    rows=extract_rows(payload,("data",))
    meta=payload.get("meta",{}) if isinstance(payload,dict) else {}
    return rows, {"page":meta.get("page"),"per_page":meta.get("per_page"),"total":meta.get("total")}

def scan_taskmarket():
    url=TASKMARKET.rstrip("/")+"/api/tasks?"+urlencode({"status":"open","limit":50,"sort":"newest"})
    payload=get_json(url)
    rows=extract_rows(payload,("tasks",))
    enriched=[]
    # Bounded public detail/terms reads only. Never call a write endpoint.
    for row in rows[:10]:
        if not isinstance(row,dict):
            continue
        task_id=first(row,"id","taskId")
        if not task_id:
            enriched.append(row); continue
        detail=None; terms=None; errors=[]
        for label, path in (("detail",f"/api/tasks/{task_id}"),("terms",f"/api/tasks/{task_id}/terms")):
            try:
                result=get_json(TASKMARKET.rstrip("/") + path)
                if label=="detail": detail=result
                else: terms=result
            except Exception as exc:
                errors.append(label + ": " + str(exc))
        merged=dict(row)
        if isinstance(detail,dict):
            merged["_detail_response"]=detail
            if isinstance(detail.get("terms"),dict):
                merged["terms"]=detail["terms"]
            merged["pendingActions"]=detail.get("pendingActions")
            merged["awards"]=detail.get("awards")
        if isinstance(terms,dict):
            merged["_terms_response"]=terms
        merged["_detail_read_errors"]=errors
        enriched.append(merged)
        time.sleep(0.25)
    return enriched, {"has_more":payload.get("hasMore") if isinstance(payload,dict) else None,
                  "next_cursor_present":bool(payload.get("nextCursor")) if isinstance(payload,dict) else False,
                  "details_attempted":len(enriched),"details_with_errors":sum(bool(x.get("_detail_read_errors")) for x in enriched)}

def main():
    now=datetime.now(timezone.utc).isoformat()
    sources={}
    normalized=[]
    for platform, fn in (("MoltJobs",scan_molt),("Dealwork",scan_dealwork),("Taskmarket",scan_taskmarket)):
        try:
            rows, meta=fn()
            sources[platform]={"status":"ok","raw_count":len(rows),"meta":meta}
            for row in rows:
                item=normalize(platform,row,now)
                if item:
                    decision, reason=classify(platform,row)
                    item["eligibility_status"]=decision
                    item["exclusion_or_review_reason"]=reason
                    normalized.append(item)
        except Exception as exc:
            sources[platform]={"status":"error","error":str(exc),"raw_count":0}
    counts={}
    for item in normalized:
        key=item["platform"]
        counts.setdefault(key,{"discovered":0,"review_required":0,"blocked":0,"excluded":0})
        counts[key]["discovered"]+=1
        status=item["eligibility_status"]
        counts[key][{"REVIEW_REQUIRED":"review_required","BLOCKED":"blocked","EXCLUDED":"excluded"}.get(status,"blocked")]+=1
    report={
      "generated_at_utc":now,"mode":"READ_ONLY","sources":sources,
      "summary":{"total_discovered":len(normalized),"by_platform":counts},
      "opportunities":normalized,
      "economic_gate":{"status":"NOT_EVALUATED","reason":"No authenticated task-level terms, model costs, acceptance probability, settlement and India withdrawal route are established."},
      "safety":{"registration":False,"bids":False,"claims":False,"pitches":False,"submissions":False,"wallet_actions":False,"payments":False},
      "policy_notes":[
        "Listings and advertised rewards are not realized income.",
        "Unknown funding, fees, payout route, or AI permissions remain UNKNOWN/BLOCKED.",
        "Taskmarket reward_amount is converted from six-decimal base units; raw units are retained.",
        "An escrow transaction reference is not independently verified on-chain by this scanner.",
        "No marketplace write operation or wallet action was performed."
      ]
    }
    path=os.path.join(OUT,"opportunities-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+".json")
    with open(path,"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({"status":"ok","sources":sources,"summary":report["summary"],"report":path},ensure_ascii=False))
    if not any(s.get("status")=="ok" for s in sources.values()):
        raise RuntimeError("All marketplace discovery adapters failed")
if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(json.dumps({"status":"error","error":str(exc)}),file=sys.stderr); sys.exit(1)
