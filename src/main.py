"""
Main Orchestrator — Daily Content Pipeline.

Research and media generation can run without enabling social publishing.
Publishing is fail-closed: TEST_MODE must be OFF and PUBLISH_ENABLED must be ON.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from research_engine import ResearchEngine
from content_generator import ContentGenerator
from image_generator import ImageGenerator
from voice_generator import VoiceGenerator
from video_creator import VideoCreator
from publisher import Publisher
from telegram_bot import TelegramBot
from database import Database
from publish_guard import publishing_allowed

Path("logs").mkdir(exist_ok=True)
logger.add("logs/main_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days")


def run_daily_pipeline():
    """Run research, content generation, media creation and guarded publishing."""
    start_time = time.time()
    test_mode = os.environ.get("TEST_MODE", "")
    publish_enabled = os.environ.get("PUBLISH_ENABLED", "")
    can_publish = publishing_allowed(test_mode, publish_enabled)

    logger.info("=" * 60)
    logger.info("AI CONTENT SYSTEM — DAILY PIPELINE STARTED")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    logger.info(f"TEST_MODE enabled: {str(test_mode).lower() in {'1', 'true', 'yes', 'on'}}")
    logger.info(f"Publishing authorized: {can_publish}")
    logger.info("=" * 60)

    db = Database()
    telegram = TelegramBot()
    telegram.send_startup_message()

    all_publish_results = {}
    all_topics = []

    try:
        logger.info("\\n📍 STEP 1: Research")
        research = ResearchEngine()
        topics = research.run()
        all_topics = topics

        if not topics:
            logger.error("No topics found. No fabricated fallback topic will be published.")
            topics = []

        logger.success(f"Research complete: {len(topics)} topics")

        if not topics:
            telegram.send_daily_report(all_topics, all_publish_results, db.get_daily_stats())
            return True

        content_gen = ContentGenerator()
        image_gen = ImageGenerator()
        voice_gen = VoiceGenerator()
        video_creator = VideoCreator()
        publisher = Publisher()

        for index, topic_data in enumerate(topics[:3]):
            topic_name = str(topic_data.get("topic", "Untitled topic"))
            safe_name = f"content_{datetime.now().strftime('%Y%m%d')}_{index + 1:02d}"
            logger.info(f"\\n📍 Processing topic {index + 1}/3: {topic_name}")

            try:
                logger.info("STEP 2a: Generating text content...")
                content_package = content_gen.generate_full_content_package(
                    topic_data, "youtube_short"
                )

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
                    logger.warning("Voice generation failed; skipping video creation.")
                    video_paths = {}

                db.update_content_status(
                    content_id,
                    "ready_to_publish" if video_paths else "generated",
                    {"images": image_paths, "videos": video_paths}
                )

                if video_paths and can_publish:
                    logger.info("STEP 3: Publishing explicitly authorized content...")
                    publish_results = publisher.publish_all(
                        content_package=content_package,
                        video_paths=video_paths,
                        image_paths=image_paths
                    )
                    all_publish_results[topic_name[:30]] = publish_results

                    for platform, result in publish_results.items():
                        if isinstance(result, dict):
                            db.save_post(
                                content_id=content_id,
                                platform=platform,
                                post_url=result.get("url", ""),
                                post_id=result.get("post_id", ""),
                                status="success" if result.get("success") else "failed"
                            )
                elif video_paths:
                    reason = (
                        "TEST_MODE is enabled"
                        if str(test_mode).strip().lower() in {"1", "true", "yes", "on"}
                        else "PUBLISH_ENABLED is not explicitly true"
                    )
                    logger.warning(f"Publishing blocked: {reason}")
                    all_publish_results[topic_name[:30]] = {
                        "publishing": {"success": False, "error": f"Blocked safely: {reason}"}
                    }
                else:
                    logger.warning(f"No video created for: {topic_name}")
                    all_publish_results[topic_name[:30]] = {
                        "media": {"success": False, "error": "No video created"}
                    }

                if index < min(len(topics), 3) - 1:
                    logger.info("Waiting 30 seconds before next topic...")
                    time.sleep(30)

            except Exception as error:
                logger.exception(f"Topic processing failed: {topic_name}")
                telegram.send_error_alert("content_pipeline", str(error))
                all_publish_results[topic_name[:30]] = {
                    "processing": {"success": False, "error": str(error)}
                }
                continue

        logger.info("\\n📍 STEP 4: Sending daily report...")
        stats = db.get_daily_stats()
        telegram.send_daily_report(
            research_topics=all_topics,
            publish_results=all_publish_results,
            stats=stats
        )

        duration = time.time() - start_time
        logger.success(f"PIPELINE FINISHED in {duration / 60:.1f} minutes")
        logger.success(f"Topics processed: {min(len(topics), 3)}")
        logger.success(f"Publishing authorized: {can_publish}")
        return True

    except Exception as error:
        logger.exception(f"PIPELINE FAILED: {error}")
        telegram.send_error_alert("main_pipeline", str(error))
        return False


if __name__ == "__main__":
    sys.exit(0 if run_daily_pipeline() else 1)
