"""
Voice Generator — Module 3c
PRIMARY:  gTTS (Google Text-to-Speech) — FREE, no API key, Hindi support
FALLBACK: pyttsx3 (offline TTS)
NO AZURE / NO PAID API NEEDED!
"""

import os
import re
import time
from pathlib import Path
from loguru import logger

OUTPUT_DIR = Path("output/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class VoiceGenerator:
    def __init__(self):
        self._check_dependencies()
        logger.success("Voice Generator initialized — gTTS (FREE Google TTS)")

    def _check_dependencies(self):
        """Auto-install gTTS if not present"""
        try:
            from gtts import gTTS
            self.gtts_available = True
            logger.success("gTTS available")
        except ImportError:
            logger.info("Installing gTTS...")
            import subprocess, sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gTTS", "-q"])
            try:
                from gtts import gTTS
                self.gtts_available = True
                logger.success("gTTS installed")
            except:
                self.gtts_available = False

        try:
            import pyttsx3
            self.pyttsx3_available = True
        except ImportError:
            try:
                import subprocess, sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyttsx3", "-q"])
                import pyttsx3
                self.pyttsx3_available = True
            except:
                self.pyttsx3_available = False

    def _clean_script_for_voice(self, script: str) -> str:
        """Clean script markers for TTS"""
        script = re.sub(r'\[IMAGE:.*?\]', '', script)
        script = re.sub(r'\[SCENE:.*?\]', '', script)
        script = re.sub(r'\[.*?\]', '', script)
        script = script.replace("[PAUSE]", "...")
        script = script.replace("[EMPHASIS]", "")
        script = script.replace("[BREAK]", "।")
        script = re.sub(r'\s+', ' ', script).strip()
        return script

    def _split_text(self, text: str, max_chars: int = 500) -> list:
        """Split long text into chunks (gTTS works best under 500 chars per call)"""
        if len(text) <= max_chars:
            return [text]

        sentences = re.split(r'([।\.!\?])', text)
        chunks = []
        current = ""

        i = 0
        while i < len(sentences):
            part = sentences[i]
            if i + 1 < len(sentences) and sentences[i + 1] in '।.!?':
                part += sentences[i + 1]
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

    def generate_with_gtts(self, text: str, output_file: str) -> bool:
        """Generate Hindi voice using gTTS (Google TTS) — FREE"""
        try:
            from gtts import gTTS
            import subprocess

            chunks = self._split_text(text, max_chars=500)

            if len(chunks) == 1:
                tts = gTTS(text=text, lang='hi', slow=False)
                tts.save(output_file)
            else:
                # Generate chunks and merge
                chunk_files = []
                for i, chunk in enumerate(chunks):
                    chunk_file = output_file.replace(".mp3", f"_part{i}.mp3")
                    tts = gTTS(text=chunk, lang='hi', slow=False)
                    tts.save(chunk_file)
                    chunk_files.append(chunk_file)
                    time.sleep(0.3)  # Polite delay

                # Merge with ffmpeg if available
                merged = False
                try:
                    file_list = output_file.replace(".mp3", "_list.txt")
                    with open(file_list, 'w') as f:
                        for cf in chunk_files:
                            f.write(f"file '{Path(cf).absolute()}'\n")

                    result = subprocess.run(
                        ["ffmpeg", "-f", "concat", "-safe", "0",
                         "-i", file_list, "-c", "copy", output_file, "-y"],
                        capture_output=True, timeout=60
                    )
                    merged = result.returncode == 0
                    try:
                        os.remove(file_list)
                    except:
                        pass
                except Exception:
                    pass

                if not merged and chunk_files:
                    # No ffmpeg — just use first chunk
                    import shutil
                    shutil.copy(chunk_files[0], output_file)

                # Cleanup
                for cf in chunk_files:
                    try:
                        os.remove(cf)
                    except:
                        pass

            if Path(output_file).exists() and Path(output_file).stat().st_size > 500:
                logger.success(f"gTTS voice generated: {output_file}")
                return True
            return False

        except Exception as e:
            logger.warning(f"gTTS failed: {e}")
            return False

    def generate_with_pyttsx3(self, text: str, output_file: str) -> bool:
        """Offline fallback using pyttsx3"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.setProperty('volume', 0.9)

            # Try to find Hindi voice
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'hindi' in voice.name.lower() or 'hi' in voice.id.lower():
                    engine.setProperty('voice', voice.id)
                    break

            # pyttsx3 saves to wav, convert if ffmpeg available
            wav_file = output_file.replace('.mp3', '.wav')
            engine.save_to_file(text[:2000], wav_file)
            engine.runAndWait()

            if Path(wav_file).exists():
                try:
                    import subprocess
                    subprocess.run(
                        ["ffmpeg", "-i", wav_file, output_file, "-y"],
                        capture_output=True, timeout=30
                    )
                    os.remove(wav_file)
                except:
                    # Use wav as-is, rename to mp3
                    import shutil
                    shutil.move(wav_file, output_file)

                logger.success(f"pyttsx3 voice generated: {output_file}")
                return True
            return False

        except Exception as e:
            logger.warning(f"pyttsx3 failed: {e}")
            return False

    def generate(self, script: str, save_name: str, voice_index: int = 0) -> str:
        """Main function — generate Hindi voice-over for script"""
        clean_text = self._clean_script_for_voice(script)
        output_file = str(OUTPUT_DIR / f"{save_name}_voice.mp3")

        logger.info(f"Generating voice for: {save_name}")
        logger.info(f"Text length: {len(clean_text)} chars")

        # Method 1: gTTS (Google TTS — primary, FREE)
        if self.gtts_available:
            success = self.generate_with_gtts(clean_text, output_file)
            if success:
                return output_file

        # Method 2: pyttsx3 (offline fallback)
        if self.pyttsx3_available:
            logger.info("Falling back to pyttsx3 (offline)...")
            success = self.generate_with_pyttsx3(clean_text, output_file)
            if success:
                return output_file

        logger.error("All TTS methods failed — no voice file generated")
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
