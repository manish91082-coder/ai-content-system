"""
Telegram Bot — Daily Reports & Notifications
Sends automated daily summary to your Telegram
"""

import os
import json
import requests
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
            else:
                logger.error(f"Telegram error: {data}")
                return False
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    def send_daily_report(self, research_topics: list, 
                           publish_results: dict,
                           stats: dict = None) -> bool:
        """Send formatted daily report"""
        today = date.today().strftime("%d %B %Y")
        now = datetime.now().strftime("%I:%M %p IST")
        
        # Topics summary
        topics_text = "\n".join([
            f"  {i+1}. {t.get('topic', 'N/A')[:50]}"
            for i, t in enumerate(research_topics[:5])
        ])
        
        # Platform results
        platforms_text = ""
        for platform, result in publish_results.items():
            if result.get("success"):
                url = result.get("url", result.get("post_id", "Posted"))
                platforms_text += f"  ✅ {platform.upper()}: {url}\n"
            else:
                error = result.get("error", "Unknown error")[:50]
                platforms_text += f"  ❌ {platform.upper()}: {error}\n"
        
        # Build message
        message = f"""🤖 <b>AI Content System — Daily Report</b>
📅 {today} | ⏰ {now}

━━━━━━━━━━━━━━━━━━━━
📊 <b>TODAY'S TOPICS RESEARCHED:</b>
{topics_text}

━━━━━━━━━━━━━━━━━━━━
📤 <b>PUBLISHED TO:</b>
{platforms_text}
━━━━━━━━━━━━━━━━━━━━

✅ System running automatically!
🔄 Next run: Tomorrow 9:00 AM IST

<i>— Your AI Content System</i>"""
        
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
        message = """🚀 <b>AI Content System Started!</b>

⚡ GitHub Actions workflow triggered
🔍 Starting research...
📝 Will generate content...
📤 Will auto-publish...

You'll receive the results soon!"""
        
        return self.send_message(message)

    def send_simple(self, text: str) -> bool:
        """Quick simple message"""
        return self.send_message(text)


if __name__ == "__main__":
    bot = TelegramBot()
    bot.send_simple("✅ AI Content System is working! Test message.")
