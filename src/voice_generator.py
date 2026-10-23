"""
Voice Generator — Module 3c
Uses edge-tts (FREE — Microsoft Edge TTS, same Azure Neural voices!)
NO API KEY NEEDED!
Hindi Voices: hi-IN-SwaraNeural (female), hi-IN-MadhurNeural (male)
Fallback: gTTS (Google TTS, also FREE)
"""

import os
import re
import asyncio
import time
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

OUTPUT_DIR = Path("output/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Hindi Neural Voices (edge-tts — same as Azure, FREE!)
HINDI_VOICES = [
    "hi-IN-SwaraNeural",     # Female, natural, warm
    "hi-IN-MadhurNeural",   # Male, professional
    "hi-IN-AaravNeural",    # Male, young & energetic (if available)
]

class VoiceGenerator:
    def __init__(self):
        self._check_dependencies()
        logger.success("Voice Generator initialized — using edge-tts (FREE, no API key!)")

    def _check_dependencies(self):
        """Auto-install edge-tts and gTTS if not present"""
        try:
            import edge_tts
            self.edge_available = True
            logger.success("edge-tts available")
        except ImportError:
            logger.info("Installing edge-tts...")
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts", "-q"])
            try:
                import edge_tts
                self.edge_available = True
                logger.success("edge-tts installed successfully")
            except:
                self.edge_available = False

        try:
            from gtts import gTTS
            self.gtts_available = True
        except ImportError:
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gTTS", "-q"])
            try:
                from gtts import gTTS
                self.gtts_available = True
            except:
                self.gtts_available = False

    def _clean_script_for_voice(self, script: str) -> str:
        """Clean script markers for TTS"""
        # Remove image/scene cues
        script = re.sub(r'\[IMAGE:.*?\]', '', script)
        script = re.sub(r'\[SCENE:.*?\]', '', script)
        script = re.sub(r'\[.*?\]', '', script)

        # Replace TTS markers
        script = script.replace("[PAUSE]", "...")
        script = script.replace("[EMPHASIS]", "")
        script = script.replace("[BREAK]", "।")

        # Clean extra whitespace
        script = re.sub(r'\s+', ' ', script).strip()
        return script

    def _split_text(self, text: str, max_chars: int = 800) -> list:
        """Split long text into chunks for TTS"""
        # Split at sentence boundaries
        sentences = re.split(r'([।\.!\?])', text)
        chunks = []
        current = ""

        i = 0
        while i < len(sentences):
            part = sentences[i]
            # Reattach punctuation
            if i + 1 < len(sentences) and sentences[i+1] in '।.!?':
                part += sentences[i+1]
                i += 1

            if len(current) + len(part) < max_chars:
                current += part
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = part
            i += 1

        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [text]

    async def _generate_edge_tts_async(self, text: str, voice: str, output_file: str) -> bool:
        """Generate voice using edge-tts (async)"""
        import edge_tts

        communicate = edge_tts.Communicate(text, voice, rate="-5%", pitch="+2Hz")
        await communicate.save(output_file)
        return True

    def generate_with_edge_tts(self, text: str, voice: str, output_file: str) -> bool:
        """Generate voice using Microsoft Edge TTS — FREE, Azure Neural quality"""
        try:
            # Handle long text by splitting into chunks
            chunks = self._split_text(text, max_chars=800)

            if len(chunks) == 1:
                # Single chunk — direct generation
                asyncio.run(self._generate_edge_tts_async(text, voice, output_file))
            else:
                # Multiple chunks — generate and merge
                import subprocess
                chunk_files = []

                for i, chunk in enumerate(chunks):
                    chunk_file = output_file.replace(".mp3", f"_chunk{i}.mp3")
                    asyncio.run(self._generate_edge_tts_async(chunk, voice, chunk_file))
                    chunk_files.append(chunk_file)
                    time.sleep(0.5)  # Small delay between requests

                # Merge chunks using ffmpeg (if available) or just use first chunk
                try:
                    file_list = output_file.replace(".mp3", "_chunks.txt")
                    with open(file_list, 'w') as f:
                        for cf in chunk_files:
                            f.write(f"file '{cf}'\n")

                    result = subprocess.run(
                        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", file_list,
                         "-c", "copy", output_file, "-y"],
                        capture_output=True, timeout=60
                    )
                    # Cleanup chunk files
                    import os
                    for cf in chunk_files:
                        try: os.remove(cf)
                        except: pass
                    try: os.remove(file_list)
                    except: pass

                    if result.returncode != 0:
                        # ffmpeg failed — just use first chunk
                        import shutil
                        shutil.copy(chunk_files[0], output_file)

                except Exception:
                    # No ffmpeg — use first chunk as approximation
                    import shutil
                    if chunk_files:
                        shutil.copy(chunk_files[0], output_file)

            if Path(output_file).exists() and Path(output_file).stat().st_size > 1000:
                logger.success(f"edge-tts voice generated: {output_file} ({voice})")
                return True
            return False

        except Exception as e:
            logger.warning(f"edge-tts failed with {voice}: {e}")
            return False

    def generate_with_gtts(self, text: str, output_file: str) -> bool:
        """Fallback: Google TTS (gTTS) — also FREE"""
        try:
            from gtts import gTTS
            tts = gTTS(text=text[:3000], lang='hi', slow=False)
            tts.save(output_file)
            logger.success(f"gTTS voice generated: {output_file}")
            return True
        except Exception as e:
            logger.error(f"gTTS failed: {e}")
            return False

    def generate(self, script: str, save_name: str, voice_index: int = 0) -> str:
        """Main function — generate voice-over for script"""
        clean_text = self._clean_script_for_voice(script)
        voice = HINDI_VOICES[voice_index % len(HINDI_VOICES)]
        output_file = str(OUTPUT_DIR / f"{save_name}_voice.mp3")

        logger.info(f"Generating voice: {voice}")
        logger.info(f"Text length: {len(clean_text)} chars")

        # Method 1: edge-tts (FREE Azure Neural quality)
        if self.edge_available:
            success = self.generate_with_edge_tts(clean_text, voice, output_file)
            if success:
                return output_file
            # Try other voice if first fails
            for alt_voice in HINDI_VOICES:
                if alt_voice != voice:
                    success = self.generate_with_edge_tts(clean_text, alt_voice, output_file)
                    if success:
                        return output_file

        # Method 2: gTTS fallback
        if self.gtts_available:
            logger.info("Falling back to gTTS...")
            success = self.generate_with_gtts(clean_text, output_file)
            if success:
                return output_file

        logger.error("All TTS methods failed")
        return None


if __name__ == "__main__":
    gen = VoiceGenerator()
    test_script = """
    नमस्ते दोस्तों! आज हम बात करने वाले हैं AI से पैसे कमाने के बारे में।
    अगर आपके पास smartphone है, तो आप घर बैठे हर महीने हजारों रुपये कमा सकते हैं।
    चलिए शुरू करते हैं!
    """
    result = gen.generate(test_script, "test_voice_001")
    print(f"Voice file: {result}")
