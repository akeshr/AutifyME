"""WhatsApp media client for downloading attachments."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from autifyme_agents.core.config import settings
# Use /tmp for media downloads on serverless platforms
MEDIA_DIR = Path("/tmp/media_downloads")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


logger = logging.getLogger(__name__)


class WhatsAppMediaClient:
    """Handles fetching media URLs and downloading content to persistent media directory.

    Downloaded media is stored in media_downloads/ (next to logs/) with meaningful
    filenames: {timestamp}_{media_id}.{ext}

    Supports: images, audio/voice, videos, documents
    """

    def __init__(self, *, access_token: str | None = None, api_version: str | None = None) -> None:
        self.access_token = access_token or settings.WHATSAPP_ACCESS_TOKEN
        self.api_version = api_version or settings.WHATSAPP_API_VERSION
        if not self.access_token:
            raise ValueError("WhatsApp access token not configured")
        self._auth_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def get_media_url(self, media_id: str) -> str:
        url = f"https://graph.facebook.com/{self.api_version}/{media_id}"
        logger.info("Fetching media metadata", extra={"media_id": media_id, "url": url})
        response = httpx.get(url, headers=self._auth_headers, timeout=10.0)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:  # noqa: BLE001
            logger.error(
                "Failed to fetch media metadata",
                extra={"status": response.status_code, "media_id": media_id, "url": url},
            )
            raise
        data: dict[str, Any] = response.json()
        media_url = data["url"]
        logger.info(
            "Resolved media",
            extra={"media_id": media_id, "media_url": media_url, "mime_type": data.get("mime_type")},
        )
        return media_url

    def download_media(self, media_id: str) -> Path:
        media_url = self.get_media_url(media_id)
        logger.info(
            "Downloading media content",
            extra={"media_id": media_id, "media_url": media_url},
        )
        response = httpx.get(media_url, headers=self._auth_headers, timeout=30.0)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:  # noqa: BLE001
            logger.error(
                "Failed to download media",
                extra={"status": response.status_code, "media_id": media_id, "media_url": media_url},
            )
            raise

        # Create meaningful filename with timestamp and media_id
        suffix = self._derive_suffix(response.headers.get("Content-Type"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{media_id}{suffix}"
        media_path = MEDIA_DIR / filename

        # Write media to persistent location next to logs
        media_path.write_bytes(response.content)
        logger.info("Downloaded media to %s", media_path)
        return media_path

    @staticmethod
    def _derive_suffix(content_type: str | None) -> str:
        """Derive file extension from MIME type."""
        if not content_type:
            return ""

        # Map MIME types to extensions
        mime_map = {
            # Images
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            # Audio/Voice
            "audio/ogg": ".ogg",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/wav": ".wav",
            "audio/aac": ".aac",
            # Video
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "video/webm": ".webm",
            "video/x-matroska": ".mkv",
            # Documents
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.ms-excel": ".xls",
            "text/csv": ".csv",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/msword": ".doc",
            "text/plain": ".txt",
        }

        return mime_map.get(content_type, "")
