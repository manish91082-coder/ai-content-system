"""
Video Creator — Module 3d
Uses FFmpeg (pre-installed in GitHub Actions) + MoviePy
Creates: YouTube Shorts, Long videos, Reels
Assembles: Images + Voice + Background music
"""

import os
import subprocess
import json
import time
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

OUTPUT_DIR = Path("output/videos")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Background music URL (royalty-free)
BG_MUSIC_URL = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

class VideoCreator:
    def __init__(self):
        self._check_ffmpeg()
        logger.success("Video Creator initialized")

    def _check_ffmpeg(self):
        """Verify FFmpeg is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.success("FFmpeg available")
                self.ffmpeg_available = True
            else:
                self.ffmpeg_available = False
        except FileNotFoundError:
            logger.error("FFmpeg not found!")
            self.ffmpeg_available = False

    def _run_ffmpeg(self, args: list, description: str = "") -> bool:
        """Run FFmpeg command"""
        cmd = ["ffmpeg", "-y"] + args  # -y = overwrite output
        logger.info(f"FFmpeg: {description}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )
        
        if result.returncode == 0:
            logger.success(f"FFmpeg success: {description}")
            return True
        else:
            logger.error(f"FFmpeg failed: {result.stderr[-500:]}")
            return False

    def download_bg_music(self) -> str:
        """Download background music"""
        import requests
        music_file = str(TEMP_DIR / "bg_music.mp3")
        
        if os.path.exists(music_file):
            return music_file
        
        try:
            response = requests.get(BG_MUSIC_URL, timeout=30)
            with open(music_file, 'wb') as f:
                f.write(response.content)
            logger.success("Background music downloaded")
            return music_file
        except Exception as e:
            logger.warning(f"BG music download failed: {e}")
            return None

    def create_image_slideshow(self, image_paths: list, 
                                duration_per_image: float,
                                output_path: str,
                                resolution: str = "1280x720") -> bool:
        """Create a slideshow video from images"""
        if not image_paths:
            logger.error("No images provided")
            return False
        
        # Create file list for FFmpeg
        list_file = str(TEMP_DIR / "image_list.txt")
        with open(list_file, 'w') as f:
            for img_path in image_paths:
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {duration_per_image}\n")
        
        args = [
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-vf", f"scale={resolution},fps=30",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path
        ]
        
        return self._run_ffmpeg(args, "Creating image slideshow")

    def add_audio_to_video(self, video_path: str, audio_path: str, 
                            output_path: str, bg_music_path: str = None) -> bool:
        """Add voice-over (and optional background music) to video"""
        if bg_music_path and os.path.exists(bg_music_path):
            # Mix voice + bg music
            args = [
                "-i", video_path,
                "-i", audio_path,
                "-i", bg_music_path,
                "-filter_complex",
                "[1:a]volume=1.0[voice];[2:a]volume=0.1,aloop=loop=-1:size=44100[music];[voice][music]amix=inputs=2:duration=first[out]",
                "-map", "0:v",
                "-map", "[out]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]
        else:
            # Just voice
            args = [
                "-i", video_path,
                "-i", audio_path,
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]
        
        return self._run_ffmpeg(args, "Adding audio to video")

    def add_text_overlay(self, video_path: str, title: str, 
                          output_path: str) -> bool:
        """Add title text overlay on video"""
        # Escape special characters for FFmpeg
        safe_title = title.replace("'", "\\'").replace(":", "\\:")
        
        args = [
            "-i", video_path,
            "-vf",
            f"drawtext=text='{safe_title}':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y=h-th-50",
            "-codec:a", "copy",
            output_path
        ]
        
        return self._run_ffmpeg(args, "Adding text overlay")

    def create_short_video(self, image_path: str, audio_path: str,
                            title: str, save_name: str) -> str:
        """Create a YouTube Short / Instagram Reel (60s, 9:16)"""
        logger.info(f"Creating short video: {save_name}")
        
        temp_video = str(TEMP_DIR / f"{save_name}_temp.mp4")
        final_video = str(OUTPUT_DIR / f"{save_name}_short.mp4")
        
        # Step 1: Image to video (portrait, 720x1280)
        args = [
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,fps=30",
            "-shortest",
            temp_video
        ]
        
        if not self._run_ffmpeg(args, "Image to video"):
            return None
        
        # Step 2: Add text overlay
        if not self.add_text_overlay(temp_video, title[:40], final_video):
            # If text overlay fails, use temp video
            import shutil
            shutil.copy(temp_video, final_video)
        
        logger.success(f"Short video created: {final_video}")
        return final_video

    def create_long_video(self, image_paths: list, audio_path: str,
                           title: str, save_name: str) -> str:
        """Create a YouTube long-form video (8-12 min, 16:9)"""
        logger.info(f"Creating long video: {save_name}")
        
        temp_slideshow = str(TEMP_DIR / f"{save_name}_slideshow.mp4")
        temp_with_audio = str(TEMP_DIR / f"{save_name}_audio.mp4")
        final_video = str(OUTPUT_DIR / f"{save_name}_long.mp4")
        
        # Calculate duration per image
        total_images = max(len(image_paths), 1)
        duration_per = 30  # 30 seconds per image for long video
        
        # Create slideshow
        if not self.create_image_slideshow(
            image_paths, duration_per, temp_slideshow, "1280x720"
        ):
            return None
        
        # Add audio
        bg_music = self.download_bg_music()
        if not self.add_audio_to_video(temp_slideshow, audio_path, 
                                         temp_with_audio, bg_music):
            return None
        
        # Add text overlay
        if not self.add_text_overlay(temp_with_audio, title[:50], final_video):
            import shutil
            shutil.copy(temp_with_audio, final_video)
        
        logger.success(f"Long video created: {final_video}")
        return final_video

    def create_all_formats(self, images: dict, audio_path: str,
                            title: str, save_name: str) -> dict:
        """Create all video formats for all platforms"""
        results = {}
        
        # Short (YouTube Shorts / Reels)
        portrait_img = images.get("portrait", images.get("thumbnail"))
        if portrait_img and audio_path:
            short_path = self.create_short_video(
                portrait_img, audio_path, title, save_name
            )
            if short_path:
                results["short"] = short_path
        
        # Long form (YouTube)
        thumbnail = images.get("thumbnail", portrait_img)
        if thumbnail and audio_path:
            long_path = self.create_long_video(
                [thumbnail] * 5,  # Use same image multiple times
                audio_path, title, save_name
            )
            if long_path:
                results["long"] = long_path
        
        logger.success(f"Video formats created: {list(results.keys())}")
        return results


if __name__ == "__main__":
    creator = VideoCreator()
    # Test would require actual image and audio files
    print("Video Creator initialized successfully")
    print(f"FFmpeg available: {creator.ffmpeg_available}")
