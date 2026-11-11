#!/usr/bin/env python3
"""Read-only PACT AI Market agent/order/wallet reconciliation."""
import json,os,sys,time
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen

BASE=os.getenv("PACT_MARKET_API_BASE","https://app.pactcore.ai").rstrip("/")
KEY=os.getenv("PACT_AGENT_API_KEY","")
REPORT=Path(os.getenv("REPORT_DIR","report"))
HEADERS={"Accept":"application/json","User-Agent":"NexusCloudWorkEngine/1.0"}

def api_get(path,retries=3):
    if not KEY: raise RuntimeError("PACT_AGENT_API_KEY is not configured")
    url=BASE+path
    last=None
    for attempt in range(retries):
        req=Request(url,headers={**HEADERS,"Authorization":"Bearer "+KEY})
        try:
            with urlopen(req,timeout=30) as response:
                data=json.loads(response.read().decode("utf-8"))
                if not isinstance(data,dict): raise RuntimeError("PACT response schema mismatch")
                return data
        except HTTPError as exc:
            if exc.code==429 and attempt+1<retries:
                try: wait=max(1,min(int(exc.headers.get("Retry-After","5")),60))
                except ValueError: wait=5
                time.sleep(wait);last="HTTP 429";continue
            if exc.code>=500 and attempt+1<retries:
                time.sleep(2**attempt);last="HTTP "+str(exc.code);continue
            raise RuntimeError("PACT API HTTP "+str(exc.code)) from None
        except (URLError,TimeoutError,json.JSONDecodeError) as exc:
            last=type(exc).__name__
            if attempt+1<retries: time.sleep(2**attempt)
    raise RuntimeError("PACT API failed: "+str(last))

def get_profile():
    return api_get("/api/agents/me")

def get_orders(role="seller",limit=100):
    return api_get("/api/market/orders?"+urlencode({"role":role,"limit":min(100,max(1,int(limit)))}))

def get_order(order_id):
    return api_get("/api/market/orders/"+str(order_id))

def get_wallet():
    return api_get("/api/market/wallet")

def amount(value):
    try:return Decimal(str(value))/Decimal(1_000_000)
    except (InvalidOperation,ValueError,TypeError):return None

def reconcile(profile,orders_payload,wallet_payload,details=None):
    agent=(profile.get("agent") or {}) if isinstance(profile,dict) else {}
    agent_id=agent.get("id")
    items=orders_payload.get("items",[]) if isinstance(orders_payload,dict) else []
    entries=wallet_payload.get("entries",[]) if isinstance(wallet_payload,dict) else []
    details=details or {}
    results=[]
    for raw in items:
        if not isinstance(raw,dict):continue
        order_id=str(raw.get("id") or "")
        detail=details.get(order_id,{})
        order=detail.get("order") if isinstance(detail.get("order"),dict) else raw
        events=detail.get("events") if isinstance(detail.get("events"),list) else []
        seller_id=order.get("sellerId")
        is_our_order=bool(agent_id and seller_id==agent_id)
        relevant=[e for e in entries if isinstance(e,dict) and str(e.get("orderId") or "")==order_id]
        releases=[e for e in relevant if e.get("kind")=="escrow_release"]
        refunds=[e for e in relevant if e.get("kind")=="escrow_refund"]
        release_total=sum((amount(e.get("amount")) or Decimal(0) for e in releases),Decimal(0))
        results.append({
            "order_id":order_id,
            "title":order.get("title"),
            "description":order.get("description"),
            "acceptance_criteria":order.get("acceptanceCriteria"),
            "updated_at":order.get("updatedAt"),
            "stage":order.get("stage"),
            "role_from_api":detail.get("role"),
            "is_our_seller_order":is_our_order,
            "seller_id":seller_id,
            "amount_usdt":str(amount(order.get("amount"))) if amount(order.get("amount")) is not None else None,
            "events":[{"kind":e.get("kind"),"from":e.get("fromStage"),"to":e.get("toStage"),"created_at":e.get("createdAt")} for e in events],
            "escrow_release_ledger_entries":len(releases),
            "released_to_platform_wallet_usdt":str(release_total),
            "refund_ledger_entries":len(refunds),
            "funds_reconciled_to_platform_wallet":bool(is_our_order and order.get("stage")=="COMPLETED" and releases and release_total>0),
            "external_withdrawal_status":"NOT_EXPOSED_BY_WALLET_READ_ENDPOINT",
            "recognized_external_income": "0"
        })
    wallet=wallet_payload.get("wallet",{}) if isinstance(wallet_payload,dict) else {}
    return {
        "status":"ok",
        "agent":{"id":agent_id,"handle":agent.get("handle"),"display_name":agent.get("displayName"),"type":agent.get("type")},
        "orders_seen":len(results),
        "seller_orders":[x for x in results if x["is_our_seller_order"]],
        "wallet":{
            "currency":wallet.get("currency"),
            "available_usdt":str(amount(wallet.get("available"))) if amount(wallet.get("available")) is not None else None,
            "escrowed_usdt":str(amount(wallet.get("escrowed"))) if amount(wallet.get("escrowed")) is not None else None,
            "total_usdt":str(amount(wallet.get("total"))) if amount(wallet.get("total")) is not None else None,
            "recent_ledger_entries":len(entries)
        },
        "financial_policy":{
            "escrow_release_is_platform_wallet_credit_not_external_bank_receipt":True,
            "external_withdrawal_requires_separate_confirmation":True,
            "recognized_external_income":"0",
            "reason":"PACT wallet read API shows platform ledger balance. Withdrawal request is pending operator approval; no external funds movement is proven."
        },
        "marketplace_writes":False
    }

def main():
    REPORT.mkdir(parents=True,exist_ok=True)
    if not KEY:
        result={"status":"needs_pact_agent_api_key","orders_seen":0,"marketplace_writes":False}
    else:
        profile=get_profile()
        orders=get_orders("seller",100)
        wallet=get_wallet()
        details={}
        for row in orders.get("items",[]) if isinstance(orders.get("items"),list) else []:
            oid=row.get("id") if isinstance(row,dict) else None
            if oid:
                try:details[str(oid)]=get_order(oid)
                except Exception as exc:details[str(oid)]={"detail_error":type(exc).__name__+":"+str(exc)[:200]}
        result=reconcile(profile,orders,wallet,details)
        result["order_detail_errors"]=sum(1 for x in details.values() if x.get("detail_error"))
    path=REPORT/"pact-agent-orders.json"
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":result["status"],"orders_seen":result.get("orders_seen",0),"seller_orders":len(result.get("seller_orders",[])),"recognized_external_income":"0","report":str(path)}))

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print(json.dumps({"status":"error","reason":type(exc).__name__+":"+str(exc)[:400]}),file=sys.stderr)
        raise SystemExit(1)
