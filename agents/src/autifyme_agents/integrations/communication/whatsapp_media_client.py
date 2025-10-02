"""WhatsApp media client for downloading attachments."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

import httpx

from autifyme_agents.core.config import settings


logger = logging.getLogger(__name__)


class WhatsAppMediaClient:
    """Handles fetching media URLs and downloading content to temp files."""

    def __init__(self, *, access_token: str | None = None, api_version: str | None = None) -> None:
        self.access_token = access_token or settings.WHATSAPP_ACCESS_TOKEN
        self.api_version = api_version or settings.WHATSAPP_API_VERSION
        if not self.access_token:
            raise ValueError("WhatsApp access token not configured")

    def get_media_url(self, media_id: str) -> str:
        url = f"https://graph.facebook.com/{self.api_version}/{media_id}"
        response = httpx.get(url, headers={"Authorization": f"Bearer {self.access_token}"}, timeout=10.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data["url"]

    def download_media(self, media_id: str) -> Path:
        media_url = self.get_media_url(media_id)
        response = httpx.get(media_url, headers={"Authorization": f"Bearer {self.access_token}"}, timeout=30.0)
        response.raise_for_status()

        suffix = self._derive_suffix(response.headers.get("Content-Type"))
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(response.content)
        temp_file.flush()
        temp_file.close()
        logger.debug("Downloaded media %s to %s", media_id, temp_file.name)
        return Path(temp_file.name)

    @staticmethod
    def _derive_suffix(content_type: str | None) -> str:
        if not content_type:
            return ""
        if content_type == "image/jpeg":
            return ".jpg"
        if content_type == "image/png":
            return ".png"
        return ""
