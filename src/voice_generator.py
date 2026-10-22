"""
Voice Generator — Module 3c
Uses Azure Speech API (FREE: 500K chars/month)
With Sarvam AI as backup (India-specific, FREE tier)
Generates: Hindi voice-over for videos
"""

import os
import time
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

OUTPUT_DIR = Path("output/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AZURE_KEY = os.environ.get("AZURE_SPEECH_KEY")
AZURE_REGION = os.environ.get("AZURE_SPEECH_REGION", "centralindia")
SARVAM_KEY = os.environ.get("SARVAM_API_KEY", "")

# Azure Hindi Voices (best quality)
HINDI_VOICES = [
    "hi-IN-SwaraNeural",    # Female, natural
    "hi-IN-MadhurNeural",   # Male, professional
    "hi-IN-AaravNeural",    # Male, young
]

class VoiceGenerator:
    def __init__(self):
        self._setup_azure()
        logger.success("Voice Generator initialized")

    def _setup_azure(self):
        """Initialize Azure Speech SDK"""
        if not AZURE_KEY:
            logger.warning("Azure Speech key not found — will use text-to-speech API directly")
            self.azure_available = False
            return
        
        try:
            import azure.cognitiveservices.speech as speechsdk
            self.speech_config = speechsdk.SpeechConfig(
                subscription=AZURE_KEY,
                region=AZURE_REGION
            )
            self.speechsdk = speechsdk
            self.azure_available = True
            logger.success(f"Azure Speech configured: {AZURE_REGION}")
        except ImportError:
            logger.warning("Azure Speech SDK not installed, using REST API fallback")
            self.azure_available = False

    def _clean_script_for_voice(self, script: str) -> str:
        """Clean script markers for TTS"""
        replacements = [
            ("[PAUSE]", "..."),
            ("[EMPHASIS]", ""),
            ("[BREAK]", "।"),
        ]
        # Remove image cues
        import re
        script = re.sub(r'\[IMAGE:.*?\]', '', script)
        script = re.sub(r'\[.*?\]', '', script)
        
        for old, new in replacements:
            script = script.replace(old, new)
        
        return script.strip()

    def _add_ssml_markup(self, text: str, voice: str) -> str:
        """Add SSML markup for natural speech"""
        # Add pauses at sentence boundaries
        text = text.replace('।', '। <break time="500ms"/>')
        text = text.replace('!', '! <break time="300ms"/>')
        text = text.replace('?', '? <break time="400ms"/>')
        
        ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="hi-IN">
  <voice name="{voice}">
    <prosody rate="0.95" pitch="+2%">
      {text}
    </prosody>
  </voice>
</speak>"""
        return ssml

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=15))
    def generate_with_azure_sdk(self, text: str, voice: str, 
                                  output_file: str) -> bool:
        """Generate voice using Azure Speech SDK"""
        import azure.cognitiveservices.speech as speechsdk
        
        self.speech_config.speech_synthesis_voice_name = voice
        
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Use SSML for better quality
        ssml = self._add_ssml_markup(text, voice)
        result = synthesizer.speak_ssml_async(ssml).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.success(f"Azure voice generated: {output_file}")
            return True
        else:
            logger.error(f"Azure speech failed: {result.reason}")
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=15))
    def generate_with_azure_rest(self, text: str, voice: str, 
                                   output_file: str) -> bool:
        """Generate voice using Azure REST API (no SDK needed)"""
        import requests
        
        token_url = f"https://{AZURE_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        headers = {"Ocp-Apim-Subscription-Key": AZURE_KEY}
        token_response = requests.post(token_url, headers=headers, timeout=10)
        access_token = token_response.text
        
        ssml = self._add_ssml_markup(text, voice)
        tts_url = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3",
            "User-Agent": "AIContentSystem"
        }
        
        response = requests.post(tts_url, headers=headers, data=ssml.encode('utf-8'), timeout=60)
        
        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            logger.success(f"Azure REST voice generated: {output_file}")
            return True
        else:
            logger.error(f"Azure REST failed: {response.status_code}")
            return False

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=5, max=20))
    def generate_with_sarvam(self, text: str, output_file: str) -> bool:
        """Generate voice using Sarvam AI (Indian voices, free tier)"""
        if not SARVAM_KEY:
            raise Exception("Sarvam API key not available")
        
        import requests
        
        url = "https://api.sarvam.ai/text-to-speech"
        headers = {
            "api-subscription-key": SARVAM_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": [text[:500]],  # Sarvam has char limits
            "target_language_code": "hi-IN",
            "speaker": "meera",  # Natural Hindi female voice
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 22050,
            "enable_preprocessing": True,
            "model": "bulbul:v1"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            import base64
            audio_data = base64.b64decode(data["audios"][0])
            with open(output_file, 'wb') as f:
                f.write(audio_data)
            logger.success(f"Sarvam voice generated: {output_file}")
            return True
        return False

    def generate(self, script: str, save_name: str, 
                 voice_index: int = 0) -> str:
        """Generate voice-over for script"""
        
        # Clean script for TTS
        clean_text = self._clean_script_for_voice(script)
        voice = HINDI_VOICES[voice_index % len(HINDI_VOICES)]
        output_file = str(OUTPUT_DIR / f"{save_name}_voice.mp3")
        
        logger.info(f"Generating voice: {voice}")
        logger.info(f"Text length: {len(clean_text)} chars")
        
        # Try Azure SDK first
        if self.azure_available:
            try:
                success = self.generate_with_azure_sdk(clean_text, voice, output_file)
                if success:
                    return output_file
            except Exception as e:
                logger.warning(f"Azure SDK failed: {e}")
        
        # Try Azure REST API
        if AZURE_KEY:
            try:
                success = self.generate_with_azure_rest(clean_text, voice, output_file)
                if success:
                    return output_file
            except Exception as e:
                logger.warning(f"Azure REST failed: {e}")
        
        # Try Sarvam
        try:
            success = self.generate_with_sarvam(clean_text[:500], output_file)
            if success:
                return output_file
        except Exception as e:
            logger.warning(f"Sarvam failed: {e}")
        
        logger.error("All voice generators failed")
        return None

    def split_long_script(self, script: str, max_chars: int = 1000) -> list:
        """Split long scripts for TTS (Azure has limits per request)"""
        sentences = script.replace('।', '।|').replace('.', '.|').split('|')
        chunks = []
        current = ""
        
        for sentence in sentences:
            if len(current) + len(sentence) < max_chars:
                current += sentence
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence
        
        if current:
            chunks.append(current.strip())
        
        return chunks


if __name__ == "__main__":
    gen = VoiceGenerator()
    test_script = """
    नमस्ते दोस्तों! आज हम बात करने वाले हैं AI से पैसे कमाने के बारे में।
    अगर आपके पास smartphone है, तो आप घर बैठे हर महीने हजारों रुपये कमा सकते हैं।
    चलिए शुरू करते हैं!
    """
    result = gen.generate(test_script, "test_voice_001")
    print(f"Voice file: {result}")
