"""
Publisher — Module 5
Posts content to all platforms automatically:
- YouTube (Shorts + Long)
- Instagram (Reels + Posts)
- Facebook (Posts + Reels)
- Telegram (Notification)
"""

import os
import json
import time
import requests
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from database import Database

# Platform credentials from environment
YT_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
YT_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

FB_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN")
FB_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID")
IG_USER_ID = os.environ.get("INSTAGRAM_USER_ID")

GDRIVE_CREDS = os.environ.get("GDRIVE_CREDENTIALS")

class Publisher:
    def __init__(self):
        self.db = Database()
        self._yt_access_token = None
        logger.success("Publisher initialized")

    # ─────────────────────────────────────────
    #  GOOGLE DRIVE (File Storage)
    # ─────────────────────────────────────────
    def upload_to_gdrive(self, file_path: str, folder_id: str = None) -> str:
        """Upload file to Google Drive, return public URL"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            import json as json_mod
            
            if not GDRIVE_CREDS:
                logger.warning("Google Drive credentials not found")
                return None
            
            creds_data = json_mod.loads(GDRIVE_CREDS)
            creds = Credentials.from_authorized_user_info(creds_data)
            service = build('drive', 'v3', credentials=creds)
            
            file_metadata = {'name': Path(file_path).name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, resumable=True)
            file = service.files().create(
                body=file_metadata, media_body=media, fields='id'
            ).execute()
            
            # Make public
            service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            url = f"https://drive.google.com/uc?id={file['id']}"
            logger.success(f"Uploaded to Drive: {url}")
            return url
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
            return None

    # ─────────────────────────────────────────
    #  YOUTUBE
    # ─────────────────────────────────────────
    def _get_youtube_token(self) -> str:
        """Get YouTube access token from refresh token"""
        if self._yt_access_token:
            return self._yt_access_token
        
        if not YT_REFRESH_TOKEN:
            return None
        
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": YT_CLIENT_ID,
                    "client_secret": YT_CLIENT_SECRET,
                    "refresh_token": YT_REFRESH_TOKEN,
                    "grant_type": "refresh_token"
                },
                timeout=10
            )
            data = response.json()
            self._yt_access_token = data.get("access_token")
            logger.success("YouTube token obtained")
            return self._yt_access_token
        except Exception as e:
            logger.error(f"YouTube token failed: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def upload_youtube(self, video_path: str, title: str, description: str,
                       tags: list, category_id: str = "22",
                       privacy: str = "public", is_short: bool = False) -> dict:
        """Upload video to YouTube"""
        
        token = self._get_youtube_token()
        if not token:
            return {"success": False, "error": "No YouTube token"}
        
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.oauth2.credentials import Credentials
            
            creds = Credentials(token=token)
            youtube = build('youtube', 'v3', credentials=creds)
            
            # Add #Shorts to title for YouTube Shorts
            if is_short and "#Shorts" not in title:
                title = title[:90] + " #Shorts"
            
            body = {
                'snippet': {
                    'title': title[:100],
                    'description': description[:5000],
                    'tags': tags[:15],
                    'categoryId': category_id,
                    'defaultLanguage': 'hi'
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            media = MediaFileUpload(
                video_path,
                mimetype='video/mp4',
                resumable=True,
                chunksize=1024*1024*5  # 5MB chunks
            )
            
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"YouTube upload: {int(status.progress() * 100)}%")
            
            video_id = response.get("id")
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            logger.success(f"YouTube uploaded: {video_url}")
            return {"success": True, "video_id": video_id, "url": video_url}
            
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────
    #  INSTAGRAM
    # ─────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def post_instagram_reel(self, video_url: str, caption: str) -> dict:
        """Post video as Instagram Reel using Graph API"""
        if not FB_ACCESS_TOKEN or not IG_USER_ID:
            return {"success": False, "error": "Instagram credentials not set"}
        
        try:
            # Step 1: Create media container
            create_url = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media"
            payload = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption[:2200],
                "access_token": FB_ACCESS_TOKEN
            }
            
            response = requests.post(create_url, data=payload, timeout=60)
            data = response.json()
            
            if "error" in data:
                return {"success": False, "error": data["error"]["message"]}
            
            container_id = data["id"]
            
            # Step 2: Wait for processing
            logger.info("Waiting for Instagram video processing...")
            for _ in range(12):  # Wait up to 2 minutes
                time.sleep(10)
                status_url = f"https://graph.facebook.com/v18.0/{container_id}"
                status_resp = requests.get(
                    status_url,
                    params={"fields": "status_code", "access_token": FB_ACCESS_TOKEN}
                )
                status = status_resp.json().get("status_code")
                logger.info(f"IG status: {status}")
                if status == "FINISHED":
                    break
                elif status == "ERROR":
                    return {"success": False, "error": "Instagram processing failed"}
            
            # Step 3: Publish
            publish_url = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media_publish"
            pub_resp = requests.post(publish_url, data={
                "creation_id": container_id,
                "access_token": FB_ACCESS_TOKEN
            }, timeout=30)
            
            pub_data = pub_resp.json()
            if "id" in pub_data:
                post_url = f"https://www.instagram.com/p/{pub_data['id']}"
                logger.success(f"Instagram posted: {post_url}")
                return {"success": True, "post_id": pub_data["id"], "url": post_url}
            
            return {"success": False, "error": str(pub_data)}
            
        except Exception as e:
            logger.error(f"Instagram post failed: {e}")
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────
    #  FACEBOOK
    # ─────────────────────────────────────────
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
    def post_facebook(self, message: str, video_url: str = None) -> dict:
        """Post to Facebook Page"""
        if not FB_ACCESS_TOKEN or not FB_PAGE_ID:
            return {"success": False, "error": "Facebook credentials not set"}
        
        try:
            if video_url:
                # Video post
                url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/videos"
                payload = {
                    "file_url": video_url,
                    "description": message[:63000],
                    "access_token": FB_ACCESS_TOKEN
                }
            else:
                # Text/link post
                url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
                payload = {
                    "message": message[:63000],
                    "access_token": FB_ACCESS_TOKEN
                }
            
            response = requests.post(url, data=payload, timeout=60)
            data = response.json()
            
            if "id" in data:
                logger.success(f"Facebook posted: {data['id']}")
                return {"success": True, "post_id": data["id"]}
            else:
                return {"success": False, "error": str(data)}
        except Exception as e:
            logger.error(f"Facebook post failed: {e}")
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────
    #  MAIN PUBLISH WORKFLOW
    # ─────────────────────────────────────────
    def publish_all(self, content_package: dict, video_paths: dict,
                    image_paths: dict) -> dict:
        """Publish content to all platforms"""
        results = {}
        title = content_package["title"]
        description = content_package["description"]
        hashtags = content_package.get("hashtags", [])
        caption = f"{description[:1800]}\n\n{' '.join(hashtags[:20])}"
        
        logger.info(f"Publishing: {title}")
        
        # Upload videos to Google Drive first (for URL-based publishing)
        drive_urls = {}
        for fmt, path in video_paths.items():
            if path and os.path.exists(path):
                url = self.upload_to_gdrive(path)
                if url:
                    drive_urls[fmt] = url
        
        # 1. YouTube Short
        if "short" in video_paths and video_paths["short"]:
            yt_result = self.upload_youtube(
                video_path=video_paths["short"],
                title=title,
                description=description,
                tags=[h.replace('#', '') for h in hashtags],
                is_short=True
            )
            results["youtube_short"] = yt_result
            time.sleep(5)
        
        # 2. YouTube Long
        if "long" in video_paths and video_paths["long"]:
            yt_long = self.upload_youtube(
                video_path=video_paths["long"],
                title=title,
                description=description,
                tags=[h.replace('#', '') for h in hashtags],
                is_short=False
            )
            results["youtube_long"] = yt_long
            time.sleep(5)
        
        # 3. Instagram Reel
        if "short" in drive_urls:
            ig_result = self.post_instagram_reel(
                video_url=drive_urls["short"],
                caption=caption
            )
            results["instagram"] = ig_result
            time.sleep(5)
        
        # 4. Facebook
        fb_message = f"{title}\n\n{description[:500]}\n\n{' '.join(hashtags[:10])}"
        fb_result = self.post_facebook(
            message=fb_message,
            video_url=drive_urls.get("short")
        )
        results["facebook"] = fb_result
        
        # Log results
        successful = sum(1 for r in results.values() if r.get("success"))
        total = len(results)
        logger.success(f"Publishing complete: {successful}/{total} platforms successful")
        
        return results


if __name__ == "__main__":
    pub = Publisher()
    print("Publisher initialized successfully")
    print("Ready to publish to: YouTube, Instagram, Facebook")
