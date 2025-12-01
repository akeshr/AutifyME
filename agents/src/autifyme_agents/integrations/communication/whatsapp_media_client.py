"""WhatsApp media client for downloading attachments."""

from __future__ import annotations

import logging
import platform
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from autifyme_agents.core.config import settings

# Use platform-appropriate temp directory for media downloads
# Serverless (Linux): /tmp/media_downloads
# Windows: %TEMP%\media_downloads
# macOS: /tmp/media_downloads
if platform.system() == "Windows":
    MEDIA_DIR = Path(tempfile.gettempdir()) / "media_downloads"
else:
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
        media_url: str = data["url"]
        logger.info(
            "Resolved media",
            extra={"media_id": media_id, "media_url": media_url, "mime_type": data.get("mime_type")},
        )
        return media_url

    def download_media(self, media_id: str) -> tuple[Path, bytes, str]:
        """Download media from WhatsApp and return Path, bytes, and MIME type.

        Returns tuple of (path, bytes, mime_type) to support both:
        - Serverless: use bytes directly (no /tmp persistence issues)
        - Local: use path for debugging

        On serverless platforms like Vercel, /tmp is ephemeral and unreliable.
        Always use the returned bytes for production code.
        """
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

        content_bytes = response.content
        mime_type = response.headers.get("Content-Type", "application/octet-stream")

        # Create meaningful filename with timestamp and media_id
        suffix = self._derive_suffix(mime_type)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{media_id}{suffix}"
        media_path = MEDIA_DIR / filename

        # Write to /tmp for local debugging (optional, may fail on serverless)
        try:
            media_path.write_bytes(content_bytes)
            logger.info("Downloaded media to %s (ephemeral on serverless)", media_path)
        except Exception as e:
            logger.warning(f"Could not write to {media_path}: {e}. Using bytes only.")

        return media_path, content_bytes, mime_type

    def upload_media(self, file_path: str, mime_type: str | None = None) -> str:
        """Upload local media file to WhatsApp and return media_id.

        WhatsApp Cloud API requires media to be uploaded before sending.
        The returned media_id can be used with send_image().

        Args:
            file_path: Local path to the media file
            mime_type: Optional MIME type (auto-detected from extension if not provided)

        Returns:
            WhatsApp media_id for the uploaded file

        Raises:
            FileNotFoundError: If file doesn't exist
            httpx.HTTPStatusError: If upload fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")

        # Auto-detect MIME type from extension
        if not mime_type:
            mime_type = self._derive_mime_type(path.suffix.lower())

        logger.info(
            "Uploading media to WhatsApp",
            extra={"file_path": file_path, "mime_type": mime_type, "size_bytes": path.stat().st_size}
        )

        # WhatsApp media upload endpoint
        upload_url = f"https://graph.facebook.com/{self.api_version}/{settings.WHATSAPP_PHONE_NUMBER_ID}/media"

        with open(path, "rb") as f:
            files = {
                "file": (path.name, f, mime_type),
            }
            data = {
                "messaging_product": "whatsapp",
                "type": mime_type,
            }

            response = httpx.post(
                upload_url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                files=files,
                data=data,
                timeout=60.0,  # Longer timeout for uploads
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error(
                "Failed to upload media to WhatsApp",
                extra={"status": response.status_code, "file_path": file_path, "response": response.text}
            )
            raise

        result: dict[str, Any] = response.json()
        media_id: str = result["id"]

        logger.info(
            "Media uploaded to WhatsApp",
            extra={"file_path": file_path, "media_id": media_id}
        )

        return media_id

    @staticmethod
    def _derive_mime_type(extension: str) -> str:
        """Derive MIME type from file extension."""
        ext_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".mp4": "video/mp4",
            ".pdf": "application/pdf",
        }
        return ext_map.get(extension, "application/octet-stream")

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
