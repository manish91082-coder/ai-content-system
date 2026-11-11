#!/usr/bin/env python3
"""Export only funded/hired work to a secret-free local coder bundle."""
import json,os
from pathlib import Path
REPORT=Path(os.getenv("REPORT_DIR","report"))

def export_bundle(source,pact_source=None):
 selected=[]; skipped=[]
 for item in source.get("active_work",[]) if isinstance(source,dict) else []:
  if not isinstance(item,dict): continue
  tid=item.get("task_id")
  if item.get("test_bounty"): skipped.append({"task_id":tid,"reason":"test_bounty"}); continue
  if item.get("status")!="claimed" or item.get("claim_status")!="active": skipped.append({"task_id":tid,"reason":"not_active_hired_claim"}); continue
  if item.get("detail_error"): skipped.append({"task_id":tid,"reason":"detail_not_verified"}); continue
  if item.get("attachments"): skipped.append({"task_id":tid,"reason":"attachments_not_ingested"}); continue
  if not tid or not item.get("description"): skipped.append({"task_id":tid,"reason":"incomplete_task_brief"}); continue
  selected.append({"source_platform":"Bounty","task_id":str(tid),"title":item.get("title"),"description":item.get("description"),"verification":item.get("verification"),"category":item.get("category"),"tags":item.get("tags") or [],"payout_amount":item.get("payout_amount"),"currency":item.get("currency"),"version":str(item.get("version") or ""),"claim_id":str(item.get("claim_id") or ""),"order_id":None,"order_stage":"CLAIMED"})
 for item in pact_source.get("seller_orders",[]) if isinstance(pact_source,dict) else []:
  if not isinstance(item,dict): continue
  oid=str(item.get("order_id") or "")
  stage=str(item.get("stage") or "")
  if not item.get("is_our_seller_order"): skipped.append({"task_id":oid,"reason":"not_our_seller_order"}); continue
  if stage not in ("ESCROWED","DELIVERING"): skipped.append({"task_id":oid,"reason":"buyer_escrow_not_funded_or_order_not_active","stage":stage}); continue
  if not item.get("title") or not item.get("description"): skipped.append({"task_id":oid,"reason":"incomplete_pact_order_brief"}); continue
  selected.append({
   "source_platform":"PACT AI Market","task_id":"pact-"+oid,"order_id":oid,"order_stage":stage,
   "title":item.get("title"),"description":item.get("description"),
   "verification":item.get("acceptance_criteria"),"category":"software_or_research",
   "tags":[],"payout_amount":item.get("amount_usdt"),"currency":"USDT",
   "version":str(item.get("updated_at") or item.get("stage") or ""),
   "claim_id":None
  })
 return {"status":"ready" if selected else "idle","tasks":selected,"skipped":skipped,"secrets_included":False}

def main():
 src=REPORT/"bounty-opportunities.json"
 pact=REPORT/"pact-agent-orders.json"
 if not src.exists(): raise RuntimeError("Bounty report missing")
 bounties=json.loads(src.read_text(encoding="utf-8"))
 pact_data=json.loads(pact.read_text(encoding="utf-8")) if pact.exists() else {}
 result=export_bundle(bounties,pact_data)
 REPORT.mkdir(parents=True,exist_ok=True)
 (REPORT/"active-work-bundle.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 out=os.getenv("GITHUB_OUTPUT")
 if out:
  with open(out,"a",encoding="utf-8") as f: f.write("active_work="+("true" if result["tasks"] else "false")+"\n")
 print(json.dumps({"status":result["status"],"active_tasks":len(result["tasks"]),"pact_tasks":sum(x["source_platform"]=="PACT AI Market" for x in result["tasks"]),"skipped":len(result["skipped"]),"secrets_included":False}))
if __name__=="__main__": main()
