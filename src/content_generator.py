"""
Content Generator — Module 3a
Uses Gemini 2.0 Flash (primary) + Groq Llama 3.1 (backup)
Generates Hindi content: titles, scripts, descriptions, hashtags
"""

import os
import json
import time
import random
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import google.generativeai as genai
from groq import Groq

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

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

# Anti-AI-detection: randomize writing style
WRITING_STYLES = [
    "conversational_storytelling",
    "practical_tips_list",
    "question_and_answer",
    "personal_experience",
    "news_style"
]

class ContentGenerator:
    def __init__(self):
        self._setup_gemini()
        self._setup_groq()

    def _setup_gemini(self):
        """Initialize Gemini client"""
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
            logger.success("Gemini initialized")
        else:
            self.gemini_model = None
            logger.warning("Gemini API key not found")

    def _setup_groq(self):
        """Initialize Groq client"""
        if GROQ_API_KEY:
            self.groq_client = Groq(api_key=GROQ_API_KEY)
            logger.success("Groq initialized")
        else:
            self.groq_client = None
            logger.warning("Groq API key not found")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API"""
        response = self.gemini_model.generate_content(prompt)
        return response.text.strip()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_groq(self, prompt: str) -> str:
        """Call Groq API (backup)"""
        completion = self.groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=2000
        )
        return completion.choices[0].message.content.strip()

    def _call_ai(self, prompt: str) -> str:
        """Call AI with Gemini first, Groq as fallback"""
        if self.gemini_model:
            try:
                result = self._call_gemini(prompt)
                logger.debug("Used: Gemini")
                return result
            except Exception as e:
                logger.warning(f"Gemini failed: {e}. Trying Groq...")
        
        if self.groq_client:
            try:
                result = self._call_groq(prompt)
                logger.debug("Used: Groq (backup)")
                return result
            except Exception as e:
                logger.error(f"Both AI APIs failed: {e}")
        
        raise Exception("All AI APIs failed")

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

    def generate_script(self, topic: str, title: str, content_type: str) -> str:
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
        
        script = self.generate_script(topic, title, content_type)
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
                "ai_model": "gemini-2.0-flash or groq-llama-3.1"
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
