"""
Main Orchestrator — Daily Content Pipeline
This is the MASTER script that GitHub Actions runs daily.

Flow:
1. Research → Find trending topics
2. Generate → Create all content (text + images + voice + video)
3. Publish → Post to all platforms
4. Report → Send Telegram summary
"""

import os
import sys
import json
import time
from datetime import datetime
from loguru import logger
from pathlib import Path

# Import all modules
from research_engine import ResearchEngine
from content_generator import ContentGenerator
from image_generator import ImageGenerator
from voice_generator import VoiceGenerator
from video_creator import VideoCreator
from publisher import Publisher
from telegram_bot import TelegramBot
from database import Database

# Setup logging
Path("logs").mkdir(exist_ok=True)
logger.add("logs/main_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days")

def run_daily_pipeline():
    """Main daily automation pipeline"""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("AI CONTENT SYSTEM — DAILY PIPELINE STARTED")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info("=" * 60)
    
    # Initialize all modules
    db = Database()
    telegram = TelegramBot()
    
    # Send startup notification
    telegram.send_startup_message()
    
    all_publish_results = {}
    all_topics = []
    
    try:
        # ─────────────────────────────────────────
        # STEP 1: RESEARCH
        # ─────────────────────────────────────────
        logger.info("\n📍 STEP 1: Research")
        research = ResearchEngine()
        topics = research.run()
        all_topics = topics
        
        if not topics:
            logger.error("No topics found! Using fallback.")
            topics = [{"topic": "AI से पैसे कमाएं 2025 में", "category": "technology"}]
        
        logger.success(f"Research complete: {len(topics)} topics")
        
        # Process each topic (up to 3 per day to stay in free limits)
        content_gen = ContentGenerator()
        image_gen = ImageGenerator()
        voice_gen = VoiceGenerator()
        video_creator = VideoCreator()
        publisher = Publisher()
        
        for i, topic_data in enumerate(topics[:3]):  # Max 3 per day
            topic_name = topic_data.get("topic", "")
            safe_name = f"content_{datetime.now().strftime('%Y%m%d')}_{i+1:02d}"
            
            logger.info(f"\n📍 Processing topic {i+1}/3: {topic_name}")
            
            try:
                # ─────────────────────────────────────────
                # STEP 2: GENERATE CONTENT
                # ─────────────────────────────────────────
                logger.info("STEP 2a: Generating text content...")
                content_package = content_gen.generate_full_content_package(
                    topic_data, "youtube_short"
                )
                
                # Save to DB
                content_id = db.save_content(
                    topic_id=topic_data.get("id", safe_name),
                    content_type="youtube_short",
                    title=content_package["title"],
                    script=content_package["script"],
                    metadata=content_package.get("metadata", {})
                )
                
                logger.info("STEP 2b: Generating images...")
                image_paths = image_gen.generate_all_formats(
                    prompt=content_package["thumbnail_prompt"],
                    save_name=safe_name
                )
                
                logger.info("STEP 2c: Generating voice...")
                audio_path = voice_gen.generate(
                    script=content_package["script"],
                    save_name=safe_name
                )
                
                if audio_path:
                    logger.info("STEP 2d: Creating videos...")
                    video_paths = video_creator.create_all_formats(
                        images=image_paths,
                        audio_path=audio_path,
                        title=content_package["title"],
                        save_name=safe_name
                    )
                else:
                    logger.warning("Voice generation failed, skipping video")
                    video_paths = {}
                
                # Update DB status
                db.update_content_status(
                    content_id, "ready_to_publish",
                    {"images": image_paths, "videos": video_paths}
                )
                
                # ─────────────────────────────────────────
                # STEP 3: PUBLISH
                # ─────────────────────────────────────────
                logger.info("STEP 3: Publishing to all platforms...")
                
                if video_paths:
                    publish_results = publisher.publish_all(
                        content_package=content_package,
                        video_paths=video_paths,
                        image_paths=image_paths
                    )
                    all_publish_results[topic_name[:30]] = publish_results
                    
                    # Log published posts to DB
                    for platform, result in publish_results.items():
                        db.save_post(
                            content_id=content_id,
                            platform=platform,
                            post_url=result.get("url", ""),
                            post_id=result.get("post_id", ""),
                            status="success" if result.get("success") else "failed"
                        )
                else:
                    logger.warning(f"No video created for: {topic_name}")
                    all_publish_results[topic_name[:30]] = {
                        "skipped": {"success": False, "error": "No video created"}
                    }
                
                # Rate limiting between topics
                logger.info("Waiting 30s before next topic...")
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Topic processing failed: {topic_name} — {e}")
                telegram.send_error_alert("content_pipeline", str(e))
                all_publish_results[topic_name[:30]] = {
                    "error": {"success": False, "error": str(e)}
                }
                continue
        
        # ─────────────────────────────────────────
        # STEP 4: DAILY REPORT
        # ─────────────────────────────────────────
        logger.info("\n📍 STEP 4: Sending daily report...")
        
        stats = db.get_daily_stats()
        telegram.send_daily_report(
            research_topics=all_topics,
            publish_results=all_publish_results,
            stats=stats
        )
        
        duration = time.time() - start_time
        logger.success(f"\n{'='*60}")
        logger.success(f"PIPELINE COMPLETE in {duration/60:.1f} minutes")
        logger.success(f"Topics processed: {min(len(topics), 3)}")
        logger.success(f"Platforms published: {len(all_publish_results)}")
        logger.success(f"{'='*60}")
        
        return True
        
    except Exception as e:
        logger.error(f"PIPELINE FAILED: {e}")
        telegram.send_error_alert("main_pipeline", str(e))
        return False


if __name__ == "__main__":
    success = run_daily_pipeline()
    sys.exit(0 if success else 1)
