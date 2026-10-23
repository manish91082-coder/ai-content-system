"""
Database Module — Supabase Integration
All data storage and retrieval operations.
Tables: topics, content_items, posts, analytics

Connection strategy (in order):
1. Supabase Python SDK (JWT key)
2. psycopg2 direct PostgreSQL (DATABASE_URL) — fallback
3. Mock mode — if all else fails
"""

import os
import json
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, date, timedelta
from loguru import logger

# Supabase REST API config (direct HTTP fallback)
# GitHub Secrets sometimes injects a BOM (\ufeff) — strip it always
def _clean_env(key: str, default: str = "") -> str:
    val = os.environ.get(key, default) or default
    return val.strip().lstrip('\ufeff').strip()

_SUPABASE_URL = _clean_env("SUPABASE_URL")
_SERVICE_KEY  = _clean_env("SUPABASE_SERVICE_KEY") or _clean_env("SUPABASE_KEY")
_SSL_CTX = ssl.create_default_context()

def _rest_request(method: str, table: str, data: dict = None, params: str = "") -> list:
    """Direct Supabase REST API call — no SDK needed"""
    base = _SUPABASE_URL.strip().rstrip('/')
    url = f"{base}/rest/v1/{table}{'?' + params if params else ''}"
    key = _SERVICE_KEY.strip()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, context=_SSL_CTX, timeout=15) as resp:
        content = resp.read()
        return json.loads(content) if content else []



class Database:
    def __init__(self):
        self.client = None
        self.use_rest = False
        self._mock_data = {"topics": [], "content": [], "posts": []}

        url = _clean_env("SUPABASE_URL")
        key = _clean_env("SUPABASE_SERVICE_KEY") or _clean_env("SUPABASE_KEY")

        if not url or not key:
            logger.warning("Supabase credentials not found — using mock mode")
            return

        if key.startswith("sb_publishable_") or key.startswith("sb_secret_"):
            logger.warning("New-format Supabase key detected — switching to REST API mode")
            self.use_rest = True
            logger.success("Supabase REST API mode active")
            return

        # Try 1: Supabase Python SDK
        try:
            from supabase import create_client
            self.client = create_client(url, key)
            logger.success("Supabase SDK connected")
            return
        except Exception as e:
            logger.warning(f"Supabase SDK failed: {e} — trying REST API fallback")

        # Try 2: Direct REST API (always works if URL + key are valid)
        try:
            clean_url = url.strip().rstrip('/')
            clean_key = key.strip()
            test_url = f"{clean_url}/rest/v1/topics?limit=1"
            req_headers = {"apikey": clean_key, "Authorization": f"Bearer {clean_key}"}
            req = urllib.request.Request(test_url, headers=req_headers)
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=10) as resp:
                resp.read()
            self.use_rest = True
            logger.success("Supabase REST API fallback connected")
            return
        except Exception as e:
            logger.warning(f"REST API also failed: {e} — using mock mode")


    # ─────────────────────────────────────────
    #  TOPICS
    # ─────────────────────────────────────────
    def save_topic(self, topic: str, source: str, category: str, score: float, date: str):
        """Save a research topic"""
        data = {
            "topic": topic,
            "source": source,
            "category": category,
            "score": score,
            "date": date,
            "created_at": datetime.utcnow().isoformat()
        }
        if self.client:
            try:
                self.client.table("topics").insert(data).execute()
            except Exception as e:
                logger.error(f"Save topic failed (SDK): {e}")
        elif self.use_rest:
            try:
                _rest_request("POST", "topics", data)
                logger.success(f"Topic saved via REST: {topic[:40]}")
            except Exception as e:
                logger.error(f"Save topic failed (REST): {e}")
        else:
            self._mock_data["topics"].append(data)

    def get_recent_topics(self, days: int = 30) -> list:
        """Get topics used in the last N days"""
        from datetime import date as _date
        cutoff = (_date.today() - timedelta(days=days)).isoformat()
        if self.client:
            try:
                result = self.client.table("topics").select("topic").gte("date", cutoff).execute()
                return [r["topic"] for r in result.data]
            except Exception as e:
                logger.error(f"Get topics failed: {e}")
                return []
        elif self.use_rest:
            try:
                rows = _rest_request("GET", "topics", params=f"select=topic&date=gte.{cutoff}")
                return [r["topic"] for r in rows]
            except Exception:
                return []
        else:
            return [t["topic"] for t in self._mock_data["topics"]]

    def get_today_topics(self) -> list:
        """Get topics selected for today"""
        from datetime import date as _date
        today = _date.today().isoformat()
        if self.client:
            try:
                result = self.client.table("topics") \
                    .select("*") \
                    .eq("date", today) \
                    .execute()
                return result.data
            except Exception as e:
                logger.error(f"Get today topics failed: {e}")
                return []
        else:
            return [t for t in self._mock_data["topics"] 
                    if t.get("date") == today]

    # ─────────────────────────────────────────
    #  CONTENT
    # ─────────────────────────────────────────
    def save_content(self, topic_id: str, content_type: str, 
                     title: str, script: str, metadata: dict) -> str:
        """Save generated content"""
        data = {
            "topic_id": topic_id,
            "content_type": content_type,
            "title": title,
            "script": script,
            "metadata": json.dumps(metadata),
            "status": "generated",
            "created_at": datetime.utcnow().isoformat()
        }
        if self.client:
            try:
                result = self.client.table("content_items") \
                    .insert(data).execute()
                return result.data[0]["id"]
            except Exception as e:
                logger.error(f"Save content failed: {e}")
                return "mock_id"
        else:
            import uuid
            content_id = str(uuid.uuid4())
            data["id"] = content_id
            self._mock_data["content"].append(data)
            return content_id

    def update_content_status(self, content_id: str, status: str, 
                               file_paths: dict = None):
        """Update content status (generated/published/failed)"""
        data = {"status": status, "updated_at": datetime.utcnow().isoformat()}
        if file_paths:
            data["file_paths"] = json.dumps(file_paths)
        
        if self.client:
            try:
                self.client.table("content_items") \
                    .update(data).eq("id", content_id).execute()
            except Exception as e:
                logger.error(f"Update content failed: {e}")

    def get_pending_content(self) -> list:
        """Get content ready for publishing"""
        if self.client:
            try:
                result = self.client.table("content_items") \
                    .select("*") \
                    .eq("status", "ready_to_publish") \
                    .execute()
                return result.data
            except Exception as e:
                logger.error(f"Get pending content failed: {e}")
                return []
        return []

    # ─────────────────────────────────────────
    #  POSTS
    # ─────────────────────────────────────────
    def save_post(self, content_id: str, platform: str, 
                  post_url: str, post_id: str, status: str):
        """Record a published post"""
        data = {
            "content_id": content_id,
            "platform": platform,
            "post_url": post_url,
            "post_id": post_id,
            "status": status,
            "published_at": datetime.utcnow().isoformat()
        }
        if self.client:
            try:
                self.client.table("posts").insert(data).execute()
            except Exception as e:
                logger.error(f"Save post failed: {e}")
        else:
            self._mock_data["posts"].append(data)

    # ─────────────────────────────────────────
    #  ANALYTICS
    # ─────────────────────────────────────────
    def get_daily_stats(self, date_str: str = None) -> dict:
        """Get statistics for a given date"""
        if not date_str:
            date_str = date.today().isoformat()
        
        if self.client:
            try:
                posts = self.client.table("posts") \
                    .select("*") \
                    .gte("published_at", f"{date_str}T00:00:00") \
                    .lte("published_at", f"{date_str}T23:59:59") \
                    .execute()
                
                return {
                    "date": date_str,
                    "total_posts": len(posts.data),
                    "platforms": list(set(p["platform"] for p in posts.data)),
                    "successful": sum(1 for p in posts.data if p["status"] == "success"),
                    "failed": sum(1 for p in posts.data if p["status"] == "failed")
                }
            except Exception as e:
                logger.error(f"Get stats failed: {e}")
        
        return {"date": date_str, "total_posts": 0, "platforms": [], 
                "successful": 0, "failed": 0}
