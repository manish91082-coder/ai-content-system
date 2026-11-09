import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline_safety import publishing_is_enabled
from telegram_bot import TelegramBot
from publisher import Publisher


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

    def test_publisher_itself_blocks_live_calls_by_default(self):
        publisher = object.__new__(Publisher)
        result = publisher.publish_all({}, {}, {})
        self.assertFalse(result["publishing"]["success"])
        self.assertIn("PUBLISH_ENABLED", result["publishing"]["error"])


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
