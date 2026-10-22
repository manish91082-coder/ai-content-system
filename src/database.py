"""
Database Module — Supabase Integration
All data storage and retrieval operations.
Tables: topics, content_items, posts, analytics
"""

import os
import json
from datetime import datetime, date, timedelta
from loguru import logger
from supabase import create_client, Client

class Database:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            logger.warning("Supabase credentials not found — using mock mode")
            self.client = None
            self._mock_data = {"topics": [], "content": [], "posts": []}
        else:
            self.client = create_client(url, key)
            logger.success("Supabase connected")

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
                logger.error(f"Save topic failed: {e}")
        else:
            self._mock_data["topics"].append(data)

    def get_recent_topics(self, days: int = 30) -> list:
        """Get topics used in the last N days"""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        if self.client:
            try:
                result = self.client.table("topics") \
                    .select("topic") \
                    .gte("date", cutoff) \
                    .execute()
                return [r["topic"] for r in result.data]
            except Exception as e:
                logger.error(f"Get topics failed: {e}")
                return []
        else:
            return [t["topic"] for t in self._mock_data["topics"]]

    def get_today_topics(self) -> list:
        """Get topics selected for today"""
        today = date.today().isoformat()
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
