#!/usr/bin/env python3
"""Export only already-hired, attachment-free Bounty tasks to a secret-free job."""
import json,os
from pathlib import Path
REPORT=Path(os.getenv("REPORT_DIR","report"))
def export_bundle(source):
 selected=[]; skipped=[]
 for item in source.get("active_work",[]) if isinstance(source,dict) else []:
  if not isinstance(item,dict): continue
  tid=item.get("task_id")
  if item.get("test_bounty"): skipped.append({"task_id":tid,"reason":"test_bounty"}); continue
  if item.get("status")!="claimed" or item.get("claim_status")!="active": skipped.append({"task_id":tid,"reason":"not_active_hired_claim"}); continue
  if item.get("detail_error"): skipped.append({"task_id":tid,"reason":"detail_not_verified"}); continue
  if item.get("attachments"): skipped.append({"task_id":tid,"reason":"attachments_not_ingested"}); continue
  if not tid or not item.get("description"): skipped.append({"task_id":tid,"reason":"incomplete_task_brief"}); continue
  selected.append({k:item.get(k) for k in ("task_id","title","description","verification","category","tags","payout_amount","currency","version","claim_id")})
 return {"status":"ready" if selected else "idle","tasks":selected,"skipped":skipped,"secrets_included":False}
def main():
 src=REPORT/"bounty-opportunities.json"
 if not src.exists(): raise RuntimeError("Bounty report missing")
 result=export_bundle(json.loads(src.read_text(encoding="utf-8")))
 REPORT.mkdir(parents=True,exist_ok=True)
 (REPORT/"active-work-bundle.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 out=os.getenv("GITHUB_OUTPUT")
 if out:
  with open(out,"a",encoding="utf-8") as f: f.write("active_work="+("true" if result["tasks"] else "false")+"\n")
 print(json.dumps({"status":result["status"],"active_tasks":len(result["tasks"]),"skipped":len(result["skipped"]),"secrets_included":False}))
if __name__=="__main__": main()
