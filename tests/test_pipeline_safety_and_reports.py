import sys
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline_safety import publishing_is_enabled
from telegram_bot import TelegramBot
from publisher import Publisher
from content_generator import ContentGenerator
from editorial_qa import topic_is_generation_eligible, build_editorial_context, build_source_metadata, editorial_package_approved


class PublishingSafetyTests(unittest.TestCase):
    def test_missing_flags_block_publishing(self):
        self.assertFalse(publishing_is_enabled({}))

    def test_test_mode_always_blocks(self):
        self.assertFalse(publishing_is_enabled({
            "PUBLISH_ENABLED": "true", "TEST_MODE": "true"
        }))

    def test_explicit_enable_and_non_test_mode_allow(self):
        self.assertTrue(publishing_is_enabled({
            "PUBLISH_ENABLED": "true", "TEST_MODE": "false"
        }))

    def test_missing_enable_flag_blocks(self):
        self.assertFalse(publishing_is_enabled({"TEST_MODE": "false"}))

    def test_malformed_enable_value_blocks(self):
        self.assertFalse(publishing_is_enabled({
            "PUBLISH_ENABLED": "sometimes", "TEST_MODE": "false"
        }))

    def test_permanent_auth_errors_trip_provider_circuit_breaker(self):
        class AuthError(Exception):
            code = 401
        self.assertTrue(ContentGenerator._is_permanent_provider_error(AuthError("unauthorized")))

    def test_rate_limit_is_not_permanent_provider_error(self):
        class RateLimitError(Exception):
            status_code = 429
        self.assertFalse(ContentGenerator._is_permanent_provider_error(RateLimitError("rate limited")))

    def test_gemini_auth_failure_falls_back_and_is_skipped_afterward(self):
        class AuthError(Exception):
            code = 401
        generator = object.__new__(ContentGenerator)
        generator.gemini_client = object()
        generator.groq_client = object()
        generator._last_provider = None
        calls = {"gemini": 0, "groq": 0}
        def fail_gemini(prompt):
            calls["gemini"] += 1
            raise AuthError("invalid key")
        def use_groq(prompt):
            calls["groq"] += 1
            return "fallback response"
        generator._call_gemini = fail_gemini
        generator._call_groq = use_groq
        self.assertEqual(generator._call_ai("prompt"), "fallback response")
        self.assertIsNone(generator.gemini_client)
        self.assertEqual(generator._call_ai("second prompt"), "fallback response")
        self.assertEqual(calls, {"gemini": 1, "groq": 2})

    def test_publisher_itself_blocks_live_calls_by_default(self):
        publisher = object.__new__(Publisher)
        result = publisher.publish_all({}, {}, {})
        self.assertFalse(result["publishing"]["success"])
        self.assertIn("PUBLISH_ENABLED", result["publishing"]["error"])


class EditorialEvidenceTests(unittest.TestCase):
    def test_news_without_source_is_blocked(self):
        self.assertFalse(topic_is_generation_eligible({
            "topic": "Breaking headline", "category": "news", "source": "rss"
        }))

    def test_news_with_url_but_short_excerpt_is_blocked(self):
        self.assertFalse(topic_is_generation_eligible({
            "topic": "Breaking headline", "category": "news",
            "source_url": "https://example.org/story",
            "source_summary": "Too short"
        }))

    def test_news_with_url_and_useful_excerpt_is_eligible(self):
        self.assertTrue(topic_is_generation_eligible({
            "topic": "Breaking headline", "category": "news",
            "source_url": "https://example.org/story",
            "source_title": "Original report",
            "source_summary": "A sufficiently detailed source excerpt. " * 5
        }))

    def test_trending_without_source_is_blocked(self):
        self.assertFalse(topic_is_generation_eligible({
            "topic": "Trending phrase", "category": "trending"
        }))

    def test_evergreen_without_source_is_limited_to_general_education(self):
        topic = {"topic": "Basic computer concepts", "category": "technology"}
        self.assertTrue(topic_is_generation_eligible(topic))
        instructions = build_editorial_context(topic)
        self.assertIn("NO SOURCE EXCERPT", instructions)
        self.assertIn("Do not state current events", instructions)

    def test_source_metadata_marks_not_independently_verified(self):
        topic = {
            "topic": "Story", "category": "news",
            "source_url": "https://example.org/story",
            "source_title": "Report",
            "source_summary": "Evidence excerpt " * 15
        }
        metadata = build_source_metadata(topic)
        self.assertEqual(metadata["evidence_status"],
                         "source_excerpt_supplied_not_independently_verified")
        self.assertEqual(metadata["sources"][0]["url"], "https://example.org/story")

    def test_editorial_approval_requires_human_identity_and_timestamp(self):
        self.assertFalse(editorial_package_approved({
            "metadata": {"editorial_approved": True}
        }))
        self.assertTrue(editorial_package_approved({
            "metadata": {
                "editorial_approved": True,
                "approved_by": "human-reviewer",
                "approved_at": "2026-11-09T12:00:00Z"
            }
        }))

    def test_publisher_blocks_even_when_live_gate_is_open_without_editorial_approval(self):
        publisher = object.__new__(Publisher)
        package = {
            "title": "Test", "description": "Test", "metadata": {
                "editorial_status": "pending_review",
                "editorial_approved": False
            }
        }
        with unittest.mock.patch.dict(os.environ, {
            "PUBLISH_ENABLED": "true", "TEST_MODE": "false"
        }, clear=False):
            result = publisher.publish_all(package, {}, {})
        self.assertFalse(result["editorial_approval"]["success"])
        self.assertEqual(result["editorial_approval"]["status"], "pending_review")


class TelegramReportTests(unittest.TestCase):
    def setUp(self):
        self.bot = object.__new__(TelegramBot)

    def test_nested_topic_platform_results(self):
        report = self.bot._format_publish_results({
            "A topic": {
                "youtube": {"success": True, "url": "https://example.test/post"},
                "instagram": {"success": False, "error": "Not authorized"}
            }
        })
        self.assertIn("YOUTUBE", report)
        self.assertIn("https://example.test/post", report)
        self.assertIn("Not authorized", report)

    def test_nested_error_dictionary_does_not_crash(self):
        report = self.bot._format_publish_results({
            "A topic": {"error": {"success": False, "error": "AI unavailable"}}
        })
        self.assertIn("AI unavailable", report)

    def test_html_is_escaped(self):
        report = self.bot._format_publish_results({
            "<script>": {"youtube": {"success": False, "error": "<bad>"}}
        })
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)

    def test_invalid_payload_is_handled(self):
        self.assertIn("No publishing", self.bot._format_publish_results(None))


if __name__ == "__main__":
    unittest.main()
