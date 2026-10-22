"""
Research Engine — Module 1
Finds trending Hindi topics from multiple sources:
- Google Trends (pytrends)
- RSS Feeds (Hindi news sites)
- YouTube Trending
- Fallback: Pre-defined evergreen topics
"""

import os
import json
import random
import time
import feedparser
import requests
from datetime import datetime, date
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from pytrends.request import TrendReq
from database import Database

# Configure logging
logger.add("logs/research_engine.log", rotation="1 day", retention="7 days")

# Hindi RSS News Feeds (verified working)
HINDI_RSS_FEEDS = [
    "https://feeds.feedburner.com/ndtvkhabar",
    "https://www.bhaskar.com/rss/tech.xml",
    "https://www.amarujala.com/rss/breaking-news.xml",
    "https://www.jagran.com/rss/technology.xml",
    "https://navbharattimes.indiatimes.com/rssfeedstopstories.cms",
]

# Evergreen Hindi content categories (fallback)
EVERGREEN_TOPICS = {
    "technology": [
        "AI क्या है और कैसे काम करता है",
        "ChatGPT से पैसे कैसे कमाएं",
        "फ्री में वेबसाइट कैसे बनाएं",
        "Canva से professional design कैसे बनाएं",
        "YouTube से पैसे कमाने के तरीके",
        "Android फोन की hidden settings",
        "WhatsApp के secret features",
        "Instagram पर followers कैसे बढ़ाएं",
        "Online पैसे कमाने के सच्चे तरीके",
        "Freelancing शुरू कैसे करें",
    ],
    "finance": [
        "Mutual Fund में invest कैसे करें",
        "Share market basics in Hindi",
        "SIP क्या है और कैसे शुरू करें",
        "EPF पैसे कैसे निकालें",
        "Income Tax return कैसे भरें",
        "Gold vs Silver investment",
        "Credit Card smartly use करने के tips",
        "Emergency fund कैसे बनाएं",
        "Passive income sources India में",
        "PPF account benefits",
    ],
    "lifestyle": [
        "सुबह की routine जो जीवन बदल दे",
        "घर पर yoga कैसे करें",
        "Healthy खाने के आसान tips",
        "Memory power कैसे बढ़ाएं",
        "English बोलना कैसे सीखें",
        "Time management tips in Hindi",
        "Motivation कैसे बनाए रखें",
        "Stress free कैसे रहें",
        "Study करने का सही तरीका",
        "Digital detox कैसे करें",
    ],
    "india_trending": [
        "Digital India scheme benefits",
        "PM Mudra Loan कैसे मिलेगा",
        "Aadhaar card update कैसे करें",
        "UPI payment problems solve",
        "Government jobs की तैयारी",
        "UPSC preparation tips",
        "Make in India opportunities",
        "Indian startup success stories",
    ]
}

class ResearchEngine:
    def __init__(self):
        self.db = Database()
        self.today = date.today().isoformat()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_google_trends(self) -> list:
        """Fetch trending searches from Google Trends India"""
        try:
            logger.info("Fetching Google Trends India...")
            pytrends = TrendReq(hl='hi', tz=330)  # IST timezone
            
            # Get daily trending searches for India
            trending_df = pytrends.trending_searches(pn='india')
            trends = trending_df[0].tolist()[:20]
            
            logger.success(f"Found {len(trends)} Google Trends topics")
            return trends
        except Exception as e:
            logger.warning(f"Google Trends failed: {e}. Using fallback.")
            return []

    def get_rss_topics(self) -> list:
        """Fetch latest topics from Hindi RSS feeds"""
        topics = []
        for feed_url in HINDI_RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    title = entry.get('title', '').strip()
                    if title and len(title) > 10:
                        topics.append(title)
                logger.info(f"RSS: Got {len(feed.entries)} articles from {feed_url}")
            except Exception as e:
                logger.warning(f"RSS feed failed ({feed_url}): {e}")
                continue
        
        logger.success(f"Total RSS topics: {len(topics)}")
        return topics[:20]

    def get_youtube_trending(self) -> list:
        """Get YouTube trending topics without API key using RSS"""
        try:
            # YouTube trending via RSS (India)
            url = "https://www.youtube.com/feeds/videos.xml?chart=mostpopular&regionCode=IN&hl=hi"
            feed = feedparser.parse(url)
            topics = [entry.title for entry in feed.entries[:10]]
            logger.success(f"YouTube trending: {len(topics)} topics")
            return topics
        except Exception as e:
            logger.warning(f"YouTube trending failed: {e}")
            return []

    def get_evergreen_topic(self) -> dict:
        """Get a random evergreen topic (fallback)"""
        category = random.choice(list(EVERGREEN_TOPICS.keys()))
        topics = EVERGREEN_TOPICS[category]
        topic = random.choice(topics)
        return {"topic": topic, "category": category, "source": "evergreen"}

    def score_topic(self, topic: str, source: str) -> float:
        """Score a topic based on relevance and freshness"""
        score = 0.0
        
        # Source scoring
        source_scores = {
            "google_trends": 1.0,
            "youtube": 0.9,
            "rss": 0.8,
            "evergreen": 0.5
        }
        score += source_scores.get(source, 0.5)
        
        # Hindi content boost
        hindi_chars = sum(1 for c in topic if '\u0900' <= c <= '\u097F')
        if hindi_chars > 3:
            score += 0.3
        
        # Length preference (not too short, not too long)
        if 20 < len(topic) < 100:
            score += 0.2
        
        return round(score, 2)

    def is_duplicate(self, topic: str) -> bool:
        """Check if this topic was used recently (last 30 days)"""
        try:
            recent = self.db.get_recent_topics(days=30)
            topic_lower = topic.lower()
            for r in recent:
                if topic_lower in r.lower() or r.lower() in topic_lower:
                    return True
            return False
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")
            return False

    def select_best_topics(self, all_topics: list, count: int = 5) -> list:
        """Select top N unique topics for today"""
        scored = []
        
        for item in all_topics:
            topic = item.get("topic", "")
            source = item.get("source", "unknown")
            
            if not topic or len(topic) < 5:
                continue
            
            if self.is_duplicate(topic):
                logger.debug(f"Skipping duplicate: {topic}")
                continue
            
            score = self.score_topic(topic, source)
            scored.append({
                "topic": topic,
                "source": source,
                "score": score,
                "category": item.get("category", "general")
            })
        
        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        # Remove near-duplicates
        selected = []
        for item in scored:
            is_dup = False
            for sel in selected:
                # Simple overlap check
                words1 = set(item["topic"].lower().split())
                words2 = set(sel["topic"].lower().split())
                overlap = len(words1 & words2) / max(len(words1), len(words2), 1)
                if overlap > 0.5:
                    is_dup = True
                    break
            if not is_dup:
                selected.append(item)
            
            if len(selected) >= count:
                break
        
        return selected

    def run(self) -> list:
        """Main research function — returns today's content topics"""
        logger.info(f"=== Research Engine Started: {self.today} ===")
        
        all_topics = []
        
        # 1. Google Trends
        trends = self.get_google_trends()
        for t in trends:
            all_topics.append({"topic": t, "source": "google_trends", "category": "trending"})
        
        # 2. RSS Feeds
        rss_topics = self.get_rss_topics()
        for t in rss_topics:
            all_topics.append({"topic": t, "source": "rss", "category": "news"})
        
        # 3. YouTube Trending
        yt_topics = self.get_youtube_trending()
        for t in yt_topics:
            all_topics.append({"topic": t, "source": "youtube", "category": "trending"})
        
        # 4. Add some evergreen topics as fillers
        for _ in range(5):
            all_topics.append(self.get_evergreen_topic())
        
        logger.info(f"Total raw topics: {len(all_topics)}")
        
        # Select best 5 topics for today
        selected = self.select_best_topics(all_topics, count=5)
        
        # If still not enough, add evergreen
        while len(selected) < 5:
            ev = self.get_evergreen_topic()
            selected.append(ev)
        
        # Save to database
        try:
            for topic_data in selected:
                self.db.save_topic(
                    topic=topic_data["topic"],
                    source=topic_data["source"],
                    category=topic_data["category"],
                    score=topic_data.get("score", 0.5),
                    date=self.today
                )
            logger.success(f"Saved {len(selected)} topics to database")
        except Exception as e:
            logger.error(f"DB save failed: {e}")
        
        # Output summary
        logger.success(f"=== Research Complete: {len(selected)} topics selected ===")
        for i, t in enumerate(selected, 1):
            logger.info(f"  {i}. [{t['source']}] {t['topic']}")
        
        return selected


if __name__ == "__main__":
    engine = ResearchEngine()
    topics = engine.run()
    print(json.dumps(topics, ensure_ascii=False, indent=2))
