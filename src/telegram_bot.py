"""
Telegram Bot — Daily Reports & Notifications
Sends automated daily summary to your Telegram
"""

import os
import json
import requests
from datetime import date, datetime
from html import escape
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
            else:
                logger.error(f"Telegram error: {data}")
                return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    @staticmethod
    def _format_publish_results(publish_results: dict) -> str:
        """Format both legacy flat and current topic -> platform -> result reports."""
        lines = []
        if not isinstance(publish_results, dict):
            return "  No publishing result data available.\n"

        for topic, platform_results in publish_results.items():
            topic_label = escape(str(topic)[:60])
            if not isinstance(platform_results, dict):
                lines.append(f"  • {topic_label}: invalid result format")
                continue

            # Support a flat result as well as the nested topic/platform structure.
            if "success" in platform_results or "error" in platform_results:
                platform_results = {"status": platform_results}

            for platform, result in platform_results.items():
                platform_label = escape(str(platform).upper()[:30])
                if isinstance(result, dict):
                    if result.get("success") is True:
                        destination = result.get("url") or result.get("post_id") or "Published (no URL returned)"
                        lines.append(f"  ✅ {topic_label} | {platform_label}: {escape(str(destination)[:180])}")
                    else:
                        error = result.get("error") or result.get("message") or "Not published / status unavailable"
                        lines.append(f"  ⏸ {topic_label} | {platform_label}: {escape(str(error)[:180])}")
                else:
                    lines.append(f"  ⏸ {topic_label} | {platform_label}: {escape(str(result)[:180])}")

        return "\n".join(lines) if lines else "  No publishing attempts recorded.\n"

    def send_daily_report(self, research_topics: list,
                           publish_results: dict,
                           stats: dict = None) -> bool:
        """Send formatted daily report without assuming nested values are strings."""
        today = date.today().strftime("%d %B %Y")
        now = datetime.now().strftime("%I:%M %p")

        topic_lines = []
        for i, item in enumerate((research_topics or [])[:5]):
            if isinstance(item, dict):
                label = item.get("topic", "N/A")
            else:
                label = str(item)
            topic_lines.append(f"  {i + 1}. {escape(str(label)[:160])}")
        topics_text = "\n".join(topic_lines) or "  No topics researched."

        platforms_text = self._format_publish_results(publish_results)
        message = f"""🤖 <b>AI Content System — Daily Report</b>
📅 {today} | ⏰ {now}

━━━━━━━━━━━━━━━━━━━━
📊 <b>TOPICS RESEARCHED:</b>
{topics_text}

━━━━━━━━━━━━━━━━━━━━
📤 <b>PUBLISHING RESULTS:</b>
{platforms_text}
━━━━━━━━━━━━━━━━━━━━

ℹ️ Report reflects recorded pipeline results. A generated asset is not counted as a published post.

<i>— AI Content System</i>"""

        return self.send_message(message)

    def send_error_alert(self, error_module: str, error_message: str) -> bool:
        """Send error alert"""
        message = f"""⚠️ <b>AI System Alert</b>

❌ Module: {error_module}
📝 Error: {error_message[:200]}
⏰ Time: {datetime.now().strftime("%H:%M IST")}

Check GitHub Actions logs for details.
🔗 https://github.com/manish91082-coder/ai-content-system/actions"""
        
        return self.send_message(message)

    def send_startup_message(self) -> bool:
        """Send startup notification"""
        message = """🚀 <b>AI Content System Started</b>

⚡ GitHub Actions workflow triggered
🔍 Research stage starting
📝 Content generation will be attempted
🛡️ Publishing is controlled by the explicit safety gate

A generated asset is not a published post. The daily report will show the recorded result."""
        
        return self.send_message(message)

    def send_simple(self, text: str) -> bool:
        """Quick simple message"""
        return self.send_message(text)


if __name__ == "__main__":
    bot = TelegramBot()
    bot.send_simple("✅ AI Content System is working! Test message.")
