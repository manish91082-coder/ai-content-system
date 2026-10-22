"""
Image Generator — Module 3b
Uses Pollinations.ai (FREE, no API key needed)
With HuggingFace Inference API as backup
Generates: Thumbnails, article images, social media visuals
"""

import os
import time
import requests
import urllib.parse
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from PIL import Image
import io

# Output directory
OUTPUT_DIR = Path("output/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# HuggingFace backup
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")

class ImageGenerator:
    def __init__(self):
        self.pollinations_base = "https://image.pollinations.ai/prompt"
        self.hf_base = "https://api-inference.huggingface.co/models"
        logger.success("Image Generator initialized (Pollinations.ai - FREE)")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=3, max=15))
    def generate_with_pollinations(self, prompt: str, 
                                    width: int = 1280, 
                                    height: int = 720,
                                    seed: int = None) -> bytes:
        """
        Generate image using Pollinations.ai (completely free, no key)
        Supports: FLUX, SDXL models
        """
        if not seed:
            seed = int(time.time())
        
        # Encode prompt
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"{self.pollinations_base}/{encoded_prompt}"
        
        params = {
            "width": width,
            "height": height,
            "seed": seed,
            "model": "flux",  # Best quality free model
            "nologo": "true",
            "enhance": "true"
        }
        
        logger.info(f"Generating image: {prompt[:60]}...")
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        logger.success(f"Image generated: {len(response.content)} bytes")
        return response.content

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=5, max=20))
    def generate_with_huggingface(self, prompt: str) -> bytes:
        """HuggingFace SDXL as backup"""
        if not HF_API_KEY:
            raise Exception("HuggingFace API key not available")
        
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        model = "stabilityai/stable-diffusion-xl-base-1.0"
        url = f"{self.hf_base}/{model}"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": "blurry, bad quality, watermark, text, logo",
                "num_inference_steps": 30,
                "guidance_scale": 7.5
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.content

    def generate(self, prompt: str, width: int = 1280, height: int = 720) -> bytes:
        """Generate image with automatic fallback"""
        try:
            return self.generate_with_pollinations(prompt, width, height)
        except Exception as e:
            logger.warning(f"Pollinations failed: {e}. Trying HuggingFace...")
            try:
                return self.generate_with_huggingface(prompt)
            except Exception as e2:
                logger.error(f"All image generators failed: {e2}")
                # Return a placeholder image
                return self._create_placeholder(prompt)

    def _create_placeholder(self, text: str) -> bytes:
        """Create a simple placeholder image using PIL"""
        img = Image.new('RGB', (1280, 720), color='#1a1a2e')
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()

    def generate_thumbnail(self, prompt: str, title: str, 
                           save_name: str) -> str:
        """Generate YouTube thumbnail (16:9)"""
        # Enhance prompt for thumbnail
        full_prompt = f"{prompt}, YouTube thumbnail style, vibrant colors, high contrast, professional quality, Indian audience, 4K"
        
        image_bytes = self.generate(full_prompt, width=1280, height=720)
        
        # Save file
        filepath = OUTPUT_DIR / f"{save_name}_thumbnail.jpg"
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        logger.success(f"Thumbnail saved: {filepath}")
        return str(filepath)

    def generate_portrait(self, prompt: str, save_name: str) -> str:
        """Generate portrait/vertical image (9:16 for Shorts/Reels)"""
        full_prompt = f"{prompt}, vertical format, mobile-optimized, vibrant, Indian style, professional"
        
        image_bytes = self.generate(full_prompt, width=720, height=1280)
        
        filepath = OUTPUT_DIR / f"{save_name}_portrait.jpg"
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        logger.success(f"Portrait image saved: {filepath}")
        return str(filepath)

    def generate_square(self, prompt: str, save_name: str) -> str:
        """Generate square image (1:1 for Instagram/Facebook)"""
        full_prompt = f"{prompt}, square format, Instagram post style, colorful, professional"
        
        image_bytes = self.generate(full_prompt, width=1080, height=1080)
        
        filepath = OUTPUT_DIR / f"{save_name}_square.jpg"
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        logger.success(f"Square image saved: {filepath}")
        return str(filepath)

    def generate_all_formats(self, prompt: str, save_name: str) -> dict:
        """Generate all required image formats for all platforms"""
        logger.info(f"Generating all image formats for: {save_name}")
        
        paths = {}
        
        # Thumbnail (YouTube)
        paths["thumbnail"] = self.generate_thumbnail(prompt, "", save_name)
        time.sleep(2)  # Respect rate limits
        
        # Portrait (Shorts/Reels)
        paths["portrait"] = self.generate_portrait(prompt, save_name)
        time.sleep(2)
        
        # Square (Instagram/Facebook)
        paths["square"] = self.generate_square(prompt, save_name)
        
        logger.success(f"All image formats generated: {list(paths.keys())}")
        return paths


if __name__ == "__main__":
    gen = ImageGenerator()
    test_prompt = "A professional Indian person looking at smartphone with AI hologram floating above, futuristic background, bright colors"
    paths = gen.generate_all_formats(test_prompt, "test_content_001")
    print("Generated images:", paths)
