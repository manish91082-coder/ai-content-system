#!/usr/bin/env python3
"""Read-only discovery for PACT AI Market public bounties and services."""
import json, os, sys, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE=os.getenv("PACT_MARKET_API_BASE","https://app.pactcore.ai").rstrip("/")
OUT=Path(os.getenv("REPORT_DIR","report"))
HEADERS={"Accept":"application/json","User-Agent":"NexusCloudWorkEngine/1.0"}

CODING={"code","coding","software","developer","backend","frontend","api","bug","automation","python","javascript","typescript","rust","go","database","devops","testing","rate-limiter","rate limit"}
RESEARCH={"research","analysis","data","report","documentation","technical writing","audit","translation","localization","architecture","scaling plan"}
BLOCKED={"buy me a cup of coffee","purchase","buy ","in-person","in person","visit","physical delivery","schoolwork","homework","essay","write my assignment","medical diagnosis","legal advice","investment advice","trading","gambling","adult","weapon","credential","private key","native japanese translator","native speaker required"}

def get_json(path,query=None,retries=3):
    url=BASE+path
    if query: url+="?"+urlencode(query)
    last=None
    for attempt in range(retries):
        req=Request(url,headers=HEADERS)
        try:
            with urlopen(req,timeout=30) as response:
                payload=json.loads(response.read().decode("utf-8"))
                if not isinstance(payload,dict): raise RuntimeError("PACT response must be an object")
                return payload,{"http_status":response.status,"url":url}
        except HTTPError as exc:
            if exc.code==429 and attempt+1<retries:
                try: wait=max(1,min(int(exc.headers.get("Retry-After","5")),60))
                except ValueError: wait=5
                time.sleep(wait); last="HTTP 429"; continue
            if exc.code>=500 and attempt+1<retries:
                time.sleep(2**attempt); last="HTTP "+str(exc.code); continue
            raise RuntimeError("PACT public API HTTP "+str(exc.code)) from None
        except (URLError,TimeoutError,json.JSONDecodeError) as exc:
            last=type(exc).__name__
            if attempt+1<retries: time.sleep(2**attempt)
    raise RuntimeError("PACT API failed: "+str(last))

def minor_to_usdt(value):
    if value is None: return None
    try: return str(Decimal(str(value))/Decimal(1_000_000))
    except (InvalidOperation,ValueError,TypeError): return None

def get_rows(payload):
    rows=payload.get("items")
    if not isinstance(rows,list): raise RuntimeError("PACT response schema mismatch: items array required")
    return rows

def fetch_bounty_detail(row):
    ident=str(row.get("id") or "")
    if not ident: return row,{"status":"missing_id"}
    try:
        payload,meta=get_json("/api/market/bounties/"+ident)
        detail=payload.get("bounty") if isinstance(payload.get("bounty"),dict) else payload.get("item") if isinstance(payload.get("item"),dict) else payload
        merged=dict(row)
        if isinstance(detail,dict): merged.update(detail)
        merged["_detail_read_status"]="ok"
        merged["_detail_read_url"]=meta.get("url")
        return merged,{"status":"ok","url":meta.get("url")}
    except Exception as exc:
        result=dict(row)
        result["_detail_read_status"]="error"
        result["_detail_read_error"]=type(exc).__name__+":"+str(exc)[:200]
        return result,{"status":"error","reason":result["_detail_read_error"]}

def normalize(row,kind):
    if not isinstance(row,dict): return None
    author=row.get("author") if isinstance(row.get("author"),dict) else {}
    amount=minor_to_usdt(row.get("priceAmount"))
    tags=row.get("tags") if isinstance(row.get("tags"),list) else []
    return {
        "platform":"PACT AI Market",
        "listing_type":kind,
        "id":str(row.get("id") or ""),
        "title":str(row.get("title") or ""),
        "description":str(row.get("description") or ""),
        "acceptance_criteria":row.get("acceptanceCriteria"),
        "detail_read_status":row.get("_detail_read_status","not_attempted"),
        "detail_read_error":row.get("_detail_read_error"),
        "tags":[str(x) for x in tags],
        "price_amount_minor":str(row.get("priceAmount")) if row.get("priceAmount") is not None else None,
        "price_amount_usdt":amount,
        "price_unit":row.get("priceUnit"),
        "currency":row.get("priceCurrency") or "USDT",
        "author_type":author.get("type"),
        "author_handle":author.get("handle"),
        "author_rating_x100":author.get("rating"),
        "author_review_count":author.get("reviewCount"),
        "status":row.get("status") or "open",
        "status_source":"PUBLIC_OPEN_FEED_DEFAULT" if row.get("status") is None else "API_FIELD",
        "created_at":row.get("createdAt"),
        "source_url":BASE+"/market/bounties" if kind=="bounty" else BASE+"/market/services",
        "payment_state":"NOT_DISCLOSED_ON_PUBLIC_LISTING",
        "escrow_status":"NOT_FUNDED_OR_UNVERIFIED",
        "writes_enabled":False
    }

def classify(item):
    if not item.get("id") or item.get("status")!="open":
        return "EXCLUDED","missing_id_or_not_open"
    if item.get("listing_type")!="bounty":
        return "SERVICE_SIDE_NOT_REVENUE","service_is_supply_listing_not_buyer_demand"
    if item.get("detail_read_status")=="error":
        return "REVIEW_REQUIRED","original_bounty_detail_unavailable"
    text=" ".join([item.get("title") or "",item.get("description") or "",item.get("acceptance_criteria") or ""," ".join(item.get("tags") or [])]).lower()
    for term in sorted(BLOCKED,key=len,reverse=True):
        if term in text:
            return "EXCLUDED","non_autonomous_or_restricted_requirement:"+term
    amount=Decimal(item["price_amount_usdt"]) if item.get("price_amount_usdt") else Decimal(0)
    if amount<=0: return "EXCLUDED","zero_or_invalid_payout"
    unit=item.get("price_unit")
    if unit=="negotiable":
        return "REVIEW_REQUIRED","negotiable_price_requires_buyer_quote_and_escrow_funding"
    if unit not in ("fixed","per_item","per_hour"):
        return "REVIEW_REQUIRED","price_unit_unknown"
    tags={x.lower() for x in item.get("tags",[])}
    skill_text=text
    if any(x in skill_text for x in CODING):
        category="CODING"
    elif any(x in skill_text for x in RESEARCH):
        category="RESEARCH_OR_CONTENT"
    else:
        return "REVIEW_REQUIRED","capability_match_not_established"
    if amount<Decimal("5"):
        return "LOW_VALUE_EXCLUDE","payout_below_minimum_work_value"
    if "ticket history" in text or "existing ticket history" in text:
        return "REVIEW_REQUIRED","requires_private_customer_ticket_data_not_yet_ingested"
    if "500 ui screenshots" in text or "screenshots for taxonomy" in text:
        return "REVIEW_REQUIRED","requires_buyer_image_dataset_not_yet_available"
    return "ESCROW_GATE_REQUIRED",category+": buyer funding must be verified before work starts"

def run_scan():
    bounties,bmeta=get_json("/api/public/bounties",{"limit":100,"sort":"newest"})
    services,smeta=get_json("/api/public/services",{"limit":100,"sort":"newest"})
    items=[]
    seen=set()
    detail_reads=[]
    for kind,payload in (("bounty",bounties),("service",services)):
        for row in get_rows(payload):
            if kind=="bounty":
                row,detail_meta=fetch_bounty_detail(row)
                detail_reads.append({"id":str(row.get("id") or ""),"status":detail_meta.get("status"),"reason":detail_meta.get("reason")})
            item=normalize(row,kind)
            if not item or not item["id"]: continue
            key=(kind,item["id"])
            if key in seen: continue
            seen.add(key)
            item["decision"],item["reason"]=classify(item)
            items.append(item)
    counts={}
    for item in items: counts[item["decision"]]=counts.get(item["decision"],0)+1
    candidates=[x for x in items if x["decision"]=="ESCROW_GATE_REQUIRED"]
    return {
        "status":"ok",
        "generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "platform":"PACT AI Market",
        "bounty_count":sum(x["listing_type"]=="bounty" for x in items),
        "service_count":sum(x["listing_type"]=="service" for x in items),
        "decision_counts":counts,
        "bounty_detail_reads":detail_reads,
        "bounty_details_ok":sum(x.get("status")=="ok" for x in detail_reads),
        "bounty_details_failed":sum(x.get("status")=="error" for x in detail_reads),
        "escrow_gate_candidates":len(candidates),
        "candidates":candidates,
        "listings":items,
        "economics":{
            "asset":"USDT",
            "amount_encoding":"six-decimal minor-unit string",
            "public_listing_is_not_escrow":True,
            "negotiation_is_not_acceptance_or_payment":True,
            "work_may_start_only_after_order_stage_ESCROWED":True,
            "income_recognized":"0 until seller payout is actually reconciled"
        },
        "sources":{"bounties":bmeta,"services":smeta},
        "marketplace_writes":False
    }

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    result=run_scan()
    path=OUT/"pact-market-opportunities.json"
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":result["status"],"bounties":result["bounty_count"],"services":result["service_count"],"decisions":result["decision_counts"],"escrow_gate_candidates":result["escrow_gate_candidates"],"report":str(path)},ensure_ascii=False))

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(json.dumps({"status":"error","reason":type(exc).__name__+":"+str(exc)[:400]}),file=sys.stderr)
        raise SystemExit(1)
