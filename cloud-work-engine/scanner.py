#!/usr/bin/env python3
"""Read-only multi-marketplace opportunity scanner. Python standard library only."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import bounty_agent
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
BASEDAGENTS = os.getenv("BASEDAGENTS_API_BASE", "https://api.basedagents.ai")
TRYBOUNTY = os.getenv("TRYBOUNTY_API_BASE", "https://api.trybounty.ai")
TRYBOUNTY_API_KEY = os.getenv("BOUNTY_AGENT_API_KEY", "")

def get_json(url, attempts=3, extra_headers=None):
    last = None
    for n in range(attempts):
        try:
            req = Request(url, headers={**HEADERS, **(extra_headers or {})})
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
    budget = None
    if platform == "MoltJobs":
        task_id = first(row,"id","jobId","_id")
        reward = first(row,"budgetUsdc","reward","budget")
        currency = first(row,"currency","rewardCurrency") or ("USDC" if first(row,"budgetUsdc") is not None else None)
        filter_name = row.get("_molt_source_filter")
        explicit_funding = first(row,"escrowStatus","fundingStatus","paymentStatus")
        funding = str(explicit_funding).upper() if explicit_funding is not None else ("FUNDED_FILTER_MATCH_NOT_INDEPENDENT_PROOF" if filter_name == "funded_only" else "UNKNOWN")
        mode = first(row,"participationMode","mode","purpose")
        source = "https://moltjobs.io/open-jobs/" + str(task_id) if task_id else "https://moltjobs.io/open-jobs"
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
    elif platform == "Bounty":
        task_id = first(row,"_id","id","bounty_id")
        payout_cents = first(row,"payout_cents")
        budget_cents = first(row,"budget_cents")
        reward = str(Decimal(str(payout_cents)) / Decimal(100)) if payout_cents is not None else None
        budget = str(Decimal(str(budget_cents)) / Decimal(100)) if budget_cents is not None else None
        currency = first(row,"currency") or "USD"
        chain = "Stripe Connect"
        flow = first(row,"flow")
        funding = "FIXED_CLAIM_PAYOUT" if flow == "claim" and payout_cents is not None else "BID_PAYOUT_PENDING_OWNER_ACCEPTANCE"
        mode = flow
        source = "https://trybounty.ai"
        title = first(row,"title")
        desc = first(row,"description")
        status = first(row,"status")
        tags = row.get("tags") or ([first(row,"category")] if first(row,"category") else [])
        expiry = first(row,"expires_at")
        actor = "agent_operator"
    elif platform == "BasedAgents":
        task_id = first(row,"task_id","id")
        bounty = row.get("bounty") if isinstance(row.get("bounty"),dict) else {}
        reward = first(bounty,"amount_display")
        currency = first(bounty,"token")
        chain = first(bounty,"network")
        escrow = row.get("escrow") if isinstance(row.get("escrow"),dict) else {}
        funding = "ESCROW_FUNDED" if escrow.get("status") == "funded" and row.get("claimable") is True else ("ESCROW_NOT_READY" if bounty and escrow.get("status") != "funded" else "NO_BOUNTY")
        mode = "agent_task"
        source = "https://basedagents.ai/tasks/" + str(task_id) if task_id else "https://basedagents.ai/tasks"
        title = first(row,"title")
        desc = first(row,"description")
        status = first(row,"status")
        tags = row.get("required_capabilities") or []
        expiry = first(row,"expires_at")
        actor = first(row,"creator_kind")
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
        "budget_amount":budget,
        "reward_raw_base_units":str(first(row,"reward")) if platform == "Taskmarket" and first(row,"reward") is not None else None,
        "reward_currency":currency, "chain":chain, "funded_or_escrow_status":funding,
        "actor_type":actor, "task_mode":mode, "status":status, "deadline":expiry,
        "tags":tags if isinstance(tags,list) else [], "acceptance_criteria":first(row,"acceptanceCriteria","criteria") or first(row,"verification"),
        "source_url":source, "fetched_at":now, "settlement_terms":row.get("terms"), "computed_settlement_terms":row.get("_terms_response"), "detail_read_errors":row.get("_detail_read_errors",[]), "receipt_verification":row.get("_receipt_verification"), "pending_actions":row.get("pendingActions"), "awards":row.get("awards"), "raw":row,
        "write_actions_enabled":False
    }

def classify(platform, row):
    if platform == "Bounty":
        if row.get("test") is True:
            return "EXCLUDED", "test_bounty_no_money_moves"
        if str(first(row,"status") or "").lower() != "open":
            return "EXCLUDED", "bounty_not_open"
        flow = str(first(row,"flow") or "").lower()
        payout = first(row,"payout_cents")
        if flow == "claim" and payout is not None and int(payout) > 0:
            return "REVIEW_REQUIRED", "fixed_claim_payout_requires_terms_and_capability_review_before_claim"
        if flow == "bid" or payout is None:
            return "REVIEW_REQUIRED", "bid_flow_budget_is_pricing_signal_not_guaranteed_agent_income"
        return "REVIEW_REQUIRED", "unknown_bounty_flow_or_unconfirmed_payout"
    if platform == "BasedAgents":
        bounty = row.get("bounty") if isinstance(row.get("bounty"),dict) else None
        if str(first(row,"status") or "").lower() != "open":
            return "EXCLUDED", "task_not_open"
        if not bounty:
            return "EXCLUDED", "free_task_reputation_only_no_cash_reward"
        escrow = row.get("escrow") if isinstance(row.get("escrow"),dict) else {}
        if not escrow:
            return "BLOCKED", "sign_at_accept_bounty_not_prefunded_no_guaranteed_payment"
        if escrow.get("status") != "funded" or row.get("claimable") is not True:
            return "BLOCKED", "escrow_not_confirmed_funded_or_claimable"
        return "BLOCKED", "1_USDC_claim_bond_and_payout_wallet_required_not_authorized"
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
    rows, seen, page_count = [], set(), 0
    filters = (("all_open", None), ("funded_only", "true"))
    for filter_name, funded_value in filters:
        cursor = None
        for _ in range(20):
            params = {"status": "OPEN", "limit": "100"}
            if funded_value is not None:
                params["funded"] = funded_value
            if cursor:
                params["cursor"] = cursor
            payload = get_json(MOLT.rstrip("/") + "/jobs?" + urlencode(params))
            page_count += 1
            batch = extract_rows(payload, ("data",))
            for raw in batch:
                if not isinstance(raw, dict):
                    continue
                row = dict(raw)
                row["_molt_source_filter"] = filter_name
                ident = str(first(row, "id", "jobId", "_id") or "")
                if ident and ident not in seen:
                    seen.add(ident)
                    rows.append(row)
            meta = payload.get("meta") or payload.get("pagination") or {} if isinstance(payload, dict) else {}
            cursor = first(meta, "nextCursor", "next_cursor") or first(payload, "nextCursor", "next_cursor") if isinstance(payload, dict) else None
            if not cursor:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("MoltJobs pagination safety cap reached for " + filter_name)
    return rows, {"pages": page_count, "filters": ["all_open", "funded=true"], "deduplicated": True, "public_get_only": True}
def scan_dealwork():
    url=DEALWORK.rstrip("/")+"/jobs?"+urlencode({"per_page":20,"sort":"newest"})
    payload=get_json(url)
    rows=extract_rows(payload,("data",))
    meta=payload.get("meta",{}) if isinstance(payload,dict) else {}
    return rows, {"page":meta.get("page"),"per_page":meta.get("per_page"),"total":meta.get("total")}

def rpc_json(url, method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode("utf-8")
    req=Request(url,data=body,headers={**HEADERS,"Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=20) as res:
        payload=json.loads(res.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(str(payload["error"]))
    return payload.get("result")

def verify_taskmarket_receipt(row):
    tx=first(row,"escrowTxHash")
    chain=first(row,"chainId")
    if not tx or chain not in (8453,4217):
        return {"status":"UNKNOWN","reason":"missing_tx_hash_or_unsupported_chain"}
    rpc="https://mainnet.base.org" if int(chain)==8453 else "https://rpc.tempo.xyz"
    token="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" if int(chain)==8453 else "0x20c0000000000000000000006a37da5c996874be"
    diamond="0xDDc6cC3e4D11c1f3527B867C7DAD4ED9869C33f7" if int(chain)==8453 else "0xF4f4a00011B080EbC1E599A765D8bCE7557B97e7"
    receipt=rpc_json(rpc,"eth_getTransactionReceipt",[tx])
    if receipt is None:
        return {"status":"NOT_FOUND_OR_PENDING","rpc":rpc}
    if receipt.get("status")!="0x1":
        return {"status":"FAILED_RECEIPT","receipt_status":receipt.get("status"),"block_number":receipt.get("blockNumber"),"rpc":rpc}
    transfer_topic="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    token_transfers=[]
    for log in receipt.get("logs",[]):
        topics=log.get("topics") or []
        if str(log.get("address","")).lower()==token.lower() and len(topics)>=3 and str(topics[0]).lower()==transfer_topic:
            recipient="0x"+str(topics[2])[-40:]
            amount=int(log.get("data","0x0"),16)
            token_transfers.append({"to":recipient,"amount_base_units":str(amount),"to_taskmarket_diamond":recipient.lower()==diamond.lower()})
    deposited=sum(int(x["amount_base_units"]) for x in token_transfers if x["to_taskmarket_diamond"])
    reward=int(str(first(row,"reward") or "0"))
    return {"status":"SUCCESS_RECEIPT","block_number":receipt.get("blockNumber"),"tx_to":receipt.get("to"),
            "token_contract":token,"taskmarket_diamond":diamond,"matching_token_transfers":token_transfers,
            "token_transfer_to_diamond_base_units":str(deposited),"listed_reward_base_units":str(reward),
            "deposit_transfer_covers_listed_reward":deposited>=reward,"rpc":rpc}

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
        try:
            merged["_receipt_verification"]=verify_taskmarket_receipt(row)
        except Exception as exc:
            merged["_receipt_verification"]={"status":"ERROR","error":str(exc)}
        enriched.append(merged)
        time.sleep(0.25)
    return enriched, {"has_more":payload.get("hasMore") if isinstance(payload,dict) else None,
                  "next_cursor_present":bool(payload.get("nextCursor")) if isinstance(payload,dict) else False,
                  "details_attempted":len(enriched),"details_with_errors":sum(bool(x.get("_detail_read_errors")) for x in enriched)}


def scan_basedagents():
    url=BASEDAGENTS.rstrip("/")+"/v1/tasks?"+urlencode({"status":"open","limit":100,"offset":0})
    payload=get_json(url)
    rows=payload.get("tasks",[]) if isinstance(payload,dict) else []
    if not isinstance(rows,list):
        raise RuntimeError("BasedAgents response schema mismatch: tasks is not an array")
    return rows,{"status_filter":"open","limit":100,"offset":0,"has_more_unknown":len(rows)==100}

def scan_trybounty():
    if not TRYBOUNTY_API_KEY:
        return [], {"status":"needs_agent_api_key","endpoint":"/v1/agent/bounties?status=open","writes":False}
    rows, page_meta = bounty_agent.page_bounties("open")
    rows, detail_meta = bounty_agent.enrich_bounties(rows)
    return rows, {"status":"authenticated_read_only","count":len(rows),"pagination":page_meta,"details":detail_meta,"writes":False}

def main():
    now=datetime.now(timezone.utc).isoformat()
    sources={}
    normalized=[]
    for platform, fn in (("MoltJobs",scan_molt),("Dealwork",scan_dealwork),("Taskmarket",scan_taskmarket),("BasedAgents",scan_basedagents),("Bounty",scan_trybounty)):
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
        "BasedAgents bounty tasks require a 1 USDC claim bond per concurrent bounty claim and a matching payout wallet; this scanner never claims.",
        "Bounty discovery requires BOUNTY_AGENT_API_KEY; Stripe Connect payout onboarding is operator-controlled and never automated by this scanner.",
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
