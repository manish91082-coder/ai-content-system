"""
Content Generator — Module 3a
Uses Gemini 3.5 Flash-Lite (primary) + Groq GPT-OSS 120B (backup)
Generates Hindi content: titles, scripts, descriptions, hashtags
"""

import os
import json
import time
import random
from loguru import logger
from google import genai
from groq import Groq
from editorial_qa import build_editorial_context, build_source_metadata

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GROQ_MODEL_ID = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

CONTENT_TYPES = {
    "youtube_short": {
        "duration": "60 seconds",
        "script_length": "150-200 words",
        "format": "hook + main points + CTA",
        "ratio": "9:16"
    },
    "youtube_long": {
        "duration": "8-12 minutes",
        "script_length": "1200-1800 words",
        "format": "intro + 5 main points + conclusion + CTA",
        "ratio": "16:9"
    },
    "instagram_reel": {
        "duration": "30-60 seconds",
        "script_length": "80-120 words",
        "format": "hook + value + hashtags",
        "ratio": "9:16"
    },
    "facebook_post": {
        "duration": "N/A",
        "script_length": "200-400 words",
        "format": "engaging post + questions + hashtags",
        "ratio": "1:1"
    }
}

# Writing styles vary presentation; never attempt to evade platform detection.
WRITING_STYLES = [
    "conversational_storytelling",
    "practical_tips_list",
    "question_and_answer",
    "first_person_explainer",
    "news_style"
]

class ContentGenerator:
    def __init__(self):
        self.gemini_client = None
        self.groq_client = None
        self._last_provider = None
        self._setup_gemini()
        self._setup_groq()

    def _setup_gemini(self):
        """Initialize the maintained Google GenAI SDK client."""
        if not GEMINI_API_KEY:
            logger.warning("Gemini API key not found")
            return
        try:
            self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            logger.success(f"Gemini client initialized (model={GEMINI_MODEL_ID})")
        except Exception as e:
            logger.error(f"Gemini client initialization failed ({type(e).__name__}): {self._redact_error(e, GEMINI_API_KEY)}")

    def _setup_groq(self):
        """Initialize Groq client."""
        if not GROQ_API_KEY:
            logger.warning("Groq API key not found")
            return
        try:
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            logger.success(f"Groq client initialized (model={GROQ_MODEL_ID})")
        except Exception as e:
            logger.error(f"Groq client initialization failed ({type(e).__name__}): {self._redact_error(e, GROQ_API_KEY)}")

    @staticmethod
    def _redact_error(error: Exception, secret: str = None) -> str:
        message = str(error)
        if secret:
            message = message.replace(secret, "[REDACTED]")
        return message[:500]

    @staticmethod
    def _is_permanent_provider_error(error: Exception) -> bool:
        """Disable a provider for this process after auth or model-not-found errors."""
        status = getattr(error, "status_code", None) or getattr(error, "code", None)
        if status in (401, 403, 404):
            return True
        message = str(error).lower()
        return status == 400 and (
            "model not found" in message
            or "unsupported model" in message
            or "model does not exist" in message
        )

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini using the maintained Google GenAI SDK."""
        response = self.gemini_client.models.generate_content(
            model=GEMINI_MODEL_ID,
            contents=prompt
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty text response")
        return response.text.strip()

    def _call_groq(self, prompt: str) -> str:
        """Call a currently listed Groq free-plan model as backup."""
        completion = self.groq_client.chat.completions.create(
            model=GROQ_MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=2000
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty text response")
        return content.strip()

    def _call_ai(self, prompt: str) -> str:
        """Call Gemini first, then Groq; preserve actionable error classes."""
        errors = []
        if self.gemini_client:
            try:
                result = self._call_gemini(prompt)
                self._last_provider = f"Gemini:{GEMINI_MODEL_ID}"
                logger.debug(f"Used {self._last_provider}")
                return result
            except Exception as e:
                summary = self._redact_error(e, GEMINI_API_KEY)
                errors.append(f"Gemini {type(e).__name__}: {summary}")
                if self._is_permanent_provider_error(e):
                    self.gemini_client = None
                    logger.warning("Gemini disabled for the remainder of this run after a permanent authentication/model error.")
                logger.warning(f"Gemini failed ({type(e).__name__}): {summary}. Trying Groq fallback.")

        if self.groq_client:
            try:
                result = self._call_groq(prompt)
                self._last_provider = f"Groq:{GROQ_MODEL_ID}"
                logger.debug(f"Used {self._last_provider}")
                return result
            except Exception as e:
                summary = self._redact_error(e, GROQ_API_KEY)
                errors.append(f"Groq {type(e).__name__}: {summary}")
                if self._is_permanent_provider_error(e):
                    self.groq_client = None
                    logger.error("Groq disabled for the remainder of this run after a permanent authentication/model error.")
                logger.error(f"Groq failed ({type(e).__name__}): {summary}")

        if not errors:
            raise RuntimeError("No AI provider configured. Add valid provider keys as GitHub Actions secrets.")
        raise RuntimeError("All configured AI providers failed. " + " | ".join(errors))

    def generate_title(self, topic: str, content_type: str) -> str:
        """Generate catchy Hindi title"""
        style = random.choice(WRITING_STYLES)
        prompt = f"""
Create a catchy, engaging Hindi YouTube title for the topic: "{topic}"

Rules:
- Language: Hindi (Devanagari script, can mix some English words like "AI", "Free", numbers)
- Length: 50-70 characters maximum
- Style: {style}
- Add emotional words: जरूर देखें, सच्चाई, पूरी जानकारी, etc.
- No clickbait lies, must be honest
- Content type: {content_type}

Return ONLY the title, nothing else.
"""
        title = self._call_ai(prompt)
        # Clean up any extra formatting
        title = title.strip('"\'`').strip()
        logger.info(f"Generated title: {title}")
        return title

    def generate_script(self, topic: str, title: str, content_type: str, topic_data: dict = None) -> str:
        """Generate full Hindi script"""
        config = CONTENT_TYPES.get(content_type, CONTENT_TYPES["youtube_short"])
        style = random.choice(WRITING_STYLES)
        
        prompt = f"""
Write a complete Hindi script for a {content_type} video.

Topic: {topic}
Title: {title}
Duration: {config['duration']}
Word count: {config['script_length']}
Format: {config['format']}
Writing style: {style}

Editorial evidence instructions:
{build_editorial_context(topic_data or {"topic": topic, "category": "general"})}

Requirements:
- Pure Hindi with Devanagari script (English technical words allowed)
- Natural, conversational tone — not like AI, like a real person talking
- Start with a strong hook in first 3 seconds
- Provide genuine value and accurate information
- End with clear call-to-action (like, subscribe, comment)
- Add [PAUSE] markers where speaker should pause
- Add [EMPHASIS] for important words
- Mark image cues with [IMAGE: description]

Script:
"""
        script = self._call_ai(prompt)
        logger.success(f"Script generated: {len(script)} chars")
        return script

    def generate_description(self, topic: str, title: str, 
                              content_type: str) -> str:
        """Generate YouTube/platform description"""
        prompt = f"""
Write an SEO-optimized Hindi description for a {content_type} about "{topic}".
Title: {title}

Include:
- First 2 lines: most important keywords (shown in search)
- Main description in Hindi (200-300 words)
- Chapters/timestamps if long video
- 3-5 relevant links (describe as [LINK: description])
- Social media handles: @AIContentHindi
- Call to action: Like + Subscribe करें
- 5-10 Hindi hashtags at the end

Return formatted description ready to paste in YouTube.
"""
        return self._call_ai(prompt)

    def generate_hashtags(self, topic: str, platform: str) -> list:
        """Generate platform-specific hashtags"""
        count_map = {
            "youtube": 5,
            "instagram": 25,
            "facebook": 10
        }
        count = count_map.get(platform, 10)
        
        prompt = f"""
Generate {count} hashtags for "{topic}" for {platform}.
Mix Hindi and English hashtags.
Format: Return ONLY hashtags separated by spaces, like: #hindi #viral #tech

Hashtags:
"""
        result = self._call_ai(prompt)
        hashtags = [h.strip() for h in result.split() if h.startswith('#')]
        return hashtags[:count]

    def generate_thumbnail_prompt(self, topic: str, title: str) -> str:
        """Generate image prompt for thumbnail"""
        prompt = f"""
Create a detailed image generation prompt for a YouTube thumbnail.
Topic: {topic}
Title: {title}

The thumbnail should:
- Be eye-catching and colorful
- Show the main concept visually
- Have space for text overlay
- Be appropriate for Indian audience
- Professional quality

Return ONLY the image prompt, no explanation.
Example format: "A professional Indian person looking amazed at a glowing smartphone screen showing money symbols, bright orange and blue gradient background, high quality, 4K"
"""
        return self._call_ai(prompt)

    def generate_full_content_package(self, topic_data: dict, 
                                       content_type: str = "youtube_short") -> dict:
        """Generate complete content package for a topic"""
        topic = topic_data.get("topic", "")
        category = topic_data.get("category", "general")
        
        logger.info(f"Generating content package for: {topic}")
        logger.info(f"Type: {content_type}")
        
        # Generate all content pieces
        title = self.generate_title(topic, content_type)
        time.sleep(1)  # Rate limiting
        
        script = self.generate_script(topic, title, content_type, topic_data=topic_data)
        time.sleep(1)
        
        description = self.generate_description(topic, title, content_type)
        time.sleep(1)
        
        hashtags = self.generate_hashtags(topic, "youtube")
        time.sleep(0.5)
        
        thumbnail_prompt = self.generate_thumbnail_prompt(topic, title)
        
        package = {
            "topic": topic,
            "category": category,
            "content_type": content_type,
            "title": title,
            "script": script,
            "description": description,
            "hashtags": hashtags,
            "thumbnail_prompt": thumbnail_prompt,
            "metadata": {
                "word_count": len(script.split()),
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "ai_model": self._last_provider or "provider_not_recorded",
                **build_source_metadata(topic_data)
            }
        }
        
        logger.success(f"Content package complete for: {topic}")
        return package


if __name__ == "__main__":
    # Test the content generator
    generator = ContentGenerator()
    test_topic = {
        "topic": "ChatGPT से पैसे कैसे कमाएं",
        "category": "technology",
        "source": "evergreen"
    }
    result = generator.generate_full_content_package(test_topic, "youtube_short")
    print(json.dumps(result, ensure_ascii=False, indent=2))
