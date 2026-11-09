"""
Telegram Bot — Daily Reports & Notifications
Sends automated daily summary to your Telegram
"""

import os
import json
import requests
from html import escape
from datetime import date, datetime
from loguru import logger

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

        if self.token and self.chat_id:
            logger.success("Telegram Bot initialized")
        else:
            logger.warning("Telegram credentials not set")

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send text message"""
        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured, skipping message")
            return False

        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": parse_mode
                },
                timeout=15
            )
            data = response.json()
            if data.get("ok"):
                logger.success("Telegram message sent")
                return True
            logger.error(f"Telegram error: {data}")
            return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    @staticmethod
    def format_publish_results(publish_results: dict) -> str:
        """
        Format both supported result shapes:
        1) {topic: {platform: {success, url/error}}}
        2) {topic: {error: {success, error}}}
        Never assume nested values are strings.
        """
        lines = []
        if not isinstance(publish_results, dict):
            return "  ⚠️ Invalid publish-results payload\n"

        for topic, topic_result in publish_results.items():
            topic_label = escape(str(topic)[:50])
            if not isinstance(topic_result, dict):
                lines.append(f"  ⚠️ {topic_label}: Invalid result payload\n")
                continue

            # Backward-compatible flat platform result.
            if "success" in topic_result or "error" in topic_result:
                platform_items = [("result", topic_result)]
            else:
                platform_items = list(topic_result.items())

            for platform, outcome in platform_items:
                platform_label = escape(str(platform).upper()[:24])
                if not isinstance(outcome, dict):
                    lines.append(
                        f"  ⚠️ {topic_label} / {platform_label}: Invalid result payload\n"
                    )
                    continue

                if outcome.get("success") is True:
                    destination = outcome.get("url") or outcome.get("post_id") or "Posted"
                    lines.append(
                        f"  ✅ {topic_label} / {platform_label}: {escape(str(destination)[:180])}\n"
                    )
                    continue

                error_value = outcome.get("error", "Not published")
                if isinstance(error_value, dict):
                    error_value = error_value.get("error", "Processing failed")
                error_text = escape(str(error_value)[:120])
                lines.append(
                    f"  ❌ {topic_label} / {platform_label}: {error_text}\n"
                )

        return "".join(lines) if lines else "  No publishing attempts recorded.\n"

    def send_daily_report(self, research_topics: list,
                          publish_results: dict,
                          stats: dict = None) -> bool:
        """Send formatted daily report without assuming nested result types."""
        today = date.today().strftime("%d %B %Y")
        now = datetime.now().strftime("%I:%M %p IST")

        topic_lines = []
        for index, item in enumerate((research_topics or [])[:5], 1):
            if isinstance(item, dict):
                title = item.get("topic", "N/A")
            else:
                title = item
            topic_lines.append(f"  {index}. {escape(str(title)[:120])}")
        topics_text = "\n".join(topic_lines) or "  No topics recorded."

        platforms_text = self.format_publish_results(publish_results)

        message = f"""🤖 <b>AI Content System — Daily Report</b>
📅 {today} | ⏰ {now}

━━━━━━━━━━━━━━━━━━━━
📊 <b>TODAY'S TOPICS RESEARCHED:</b>
{topics_text}

━━━━━━━━━━━━━━━━━━━━
📤 <b>PUBLISHING RESULTS:</b>
{platforms_text}
━━━━━━━━━━━━━━━━━━━━

<i>— Your AI Content System</i>"""

        return self.send_message(message)

    def send_error_alert(self, error_module: str, error_message: str) -> bool:
        """Send error alert"""
        message = f"""⚠️ <b>AI System Alert</b>

❌ Module: {escape(str(error_module)[:100])}
📝 Error: {escape(str(error_message)[:200])}
⏰ Time: {datetime.now().strftime("%H:%M IST")}

Check GitHub Actions logs for details.
🔗 https://github.com/manish91082-coder/ai-content-system/actions"""
        return self.send_message(message)

    def send_startup_message(self) -> bool:
        """Send startup notification"""
        message = """🚀 <b>AI Content System Started</b>

🔍 Research and content-generation pipeline started.
📤 Publishing is separately gated by TEST_MODE and PUBLISH_ENABLED."""
        return self.send_message(message)

    def send_simple(self, text: str) -> bool:
        """Quick simple message"""
        return self.send_message(text)


if __name__ == "__main__":
    bot = TelegramBot()
    bot.send_simple("AI Content System test message")
