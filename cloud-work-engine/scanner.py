#!/usr/bin/env python3
"""Read-only funded-job scanner for MoltJobs. Standard library only."""
import json, os, sys, time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
BASE = os.getenv("MOLTJOBS_API_BASE", "https://api.moltjobs.io/v1")
OUT = os.getenv("REPORT_DIR", "report")
os.makedirs(OUT, exist_ok=True)
def get_json(url, attempts=4):
    last = None
    for n in range(attempts):
        try:
            req = Request(url, headers={"Accept":"application/json","User-Agent":"NexusCloudWorkEngine/0.1"})
            with urlopen(req, timeout=25) as res: return json.loads(res.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
            last = str(e)
            if isinstance(e, HTTPError) and e.code not in (429,500,502,503,504): break
            time.sleep(min(2 ** n, 12))
    raise RuntimeError("GET failed after retries: " + str(last))
def unpack(payload):
    """Accept documented {data:[...]} envelopes and common cursor metadata layouts."""
    if isinstance(payload, list):
        return payload, None
    if not isinstance(payload, dict):
        return [], None

    data = payload.get("data")
    rows = None
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ("jobs", "items", "results"):
            if isinstance(data.get(key), list):
                rows = data[key]
                break

    if rows is None:
        for key in ("jobs", "items", "results"):
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break

    meta = payload.get("meta") or payload.get("pagination") or {}
    if not isinstance(meta, dict):
        meta = {}
    cursor = (
        payload.get("nextCursor") or payload.get("next_cursor")
        or meta.get("nextCursor") or meta.get("next_cursor")
        or (data.get("nextCursor") if isinstance(data, dict) else None)
        or (data.get("next_cursor") if isinstance(data, dict) else None)
    )
    return rows or [], cursor
def classify_job(job):
    """Exclude platform referral rewards from ordinary paid-task opportunities."""
    purpose = str(job.get("purpose") or "").upper()
    mode = str(job.get("participationMode") or "").upper()
    if purpose == "PLATFORM_REFERRAL" or mode == "AUTOMATIC_FORUM_REWARD":
        return False, "referral_or_forum_reward_not_a_normal_work_assignment"
    return True, "eligible_for_next_stage_review"

def main():
    all_rows, raw_pages, cursor, seen = [], [], None, set()
    for page in range(20):
        params = {"status":"OPEN","funded":"true","limit":"100"}
        if cursor: params["cursor"] = cursor
        payload = get_json(BASE.rstrip("/") + "/jobs?" + urlencode(params))
        raw_pages.append(payload)
        rows, next_cursor = unpack(payload)
        for row in rows:
            if isinstance(row, dict):
                jid = str(row.get("id") or row.get("jobId") or "")
                if jid and jid not in seen: seen.add(jid); all_rows.append(row)
        if not next_cursor: break
        cursor = next_cursor; time.sleep(3)
    else: raise RuntimeError("Pagination safety cap reached; report incomplete.")
    now = datetime.now(timezone.utc)
    eligible, excluded = [], []
    for job in all_rows:
        ok, reason = classify_job(job)
        if ok:
            eligible.append(job)
        else:
            excluded.append({"id":job.get("id"),"title":job.get("title"),"reason":reason})

    report = {
        "generated_at_utc":now.isoformat(),
        "source":BASE+"/jobs?status=OPEN&funded=true",
        "mode":"READ_ONLY",
        "funded_open_jobs_count":len(all_rows),
        "eligible_task_candidates_count":len(eligible),
        "excluded_by_policy_count":len(excluded),
        "jobs":all_rows,
        "eligible_task_candidates":eligible,
        "excluded_by_policy":excluded,
        "raw_pages":raw_pages,
        "notes":[
            "Funded listing is not a guarantee of bid acceptance or payout.",
            "Referral/forum reward campaigns are excluded from ordinary paid-task opportunities.",
            "Eligible candidates still require job-detail, task-permission, acceptance, and cost review.",
            "No bids, claims, submissions, wallet actions, or payments were performed."
        ]
    }
    path = os.path.join(OUT, "jobs-" + now.strftime("%Y%m%d-%H%M%S") + ".json")
    with open(path,"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({"status":"ok","funded_open_jobs_count":len(all_rows),"report":path}))
    print("ELIGIBLE_TASK_CANDIDATES:", len(eligible))
    print("EXCLUDED_BY_POLICY:", len(excluded))
    if not all_rows: print("RESULT: No funded open jobs returned by API filter in this scan.")
    elif not eligible: print("RESULT: Funded listings exist, but none passed the ordinary-work candidate filter.")
if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status":"error","error":str(exc)}),file=sys.stderr); sys.exit(1)
