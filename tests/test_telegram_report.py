import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from telegram_bot import TelegramBot


class TelegramReportFormattingTests(unittest.TestCase):
    def test_nested_topic_platform_results(self):
        results = {
            "Topic Alpha": {
                "youtube_short": {"success": True, "url": "https://example.com/post"},
                "facebook": {"success": False, "error": "No token"}
            }
        }
        rendered = TelegramBot.format_publish_results(results)
        self.assertIn("YOUTUBE_SHORT", rendered)
        self.assertIn("https://example.com/post", rendered)
        self.assertIn("No token", rendered)

    def test_nested_processing_error_dictionary_does_not_slice_dict(self):
        results = {
            "Topic Beta": {
                "processing": {"success": False, "error": "Model unavailable"}
            }
        }
        rendered = TelegramBot.format_publish_results(results)
        self.assertIn("Model unavailable", rendered)

    def test_invalid_nested_payload_is_handled(self):
        rendered = TelegramBot.format_publish_results({"Topic": None})
        self.assertIn("Invalid result payload", rendered)

    def test_empty_results_are_readable(self):
        self.assertIn("No publishing attempts", TelegramBot.format_publish_results({}))


if __name__ == "__main__":
    unittest.main()
