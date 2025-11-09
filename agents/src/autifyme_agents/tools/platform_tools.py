"""Platform-specific tools for media download and message handling.

These tools enable MessageIntentSpecialist to download media from various
messaging platforms without hardcoding platform logic in the Runner.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from langchain.tools import tool

logger = logging.getLogger(__name__)


class MediaDownloader(Protocol):
    """Minimal interface for media download capability.

    Tools layer depends only on this protocol, not on full MessagingChannel.
    This preserves hexagonal architecture (core doesn't depend on adapters).
    """

    def download_media(self, media_id: str) -> Path | None:
        """Download media and return local path."""
        ...


def create_platform_media_tools(channel: MediaDownloader) -> list[Any]:
    """Create platform-specific media download tools.

    Args:
        channel: Object implementing MediaDownloader protocol (e.g., WhatsAppChannel)

    Returns:
        List of platform-specific tools for media operations
    """
    platform_name = channel.__class__.__name__.replace("Channel", "").lower()

    @tool
    def download_media(media_id: str) -> str:
        """Download media from the messaging platform.

        Args:
            media_id: Platform-specific media identifier

        Returns:
            Local filesystem path to downloaded media file

        Raises:
            Exception: If media download fails
        """
        try:
            logger.info(
                f"Downloading media from {platform_name}",
                extra={"media_id": media_id, "platform": platform_name}
            )
            media_path = channel.download_media(media_id)
            logger.info(
                "Media downloaded successfully",
                extra={"media_id": media_id, "local_path": str(media_path)}
            )
            return str(media_path)
        except Exception as e:
            logger.exception(
                f"Failed to download media from {platform_name}",
                extra={"media_id": media_id, "error": str(e)}
            )
            raise

    # Set dynamic name and description based on platform
    download_media.name = f"download_{platform_name}_media"
    download_media.description = (
        f"Download media (image, video, audio, document) from {platform_name}. "
        f"Takes the media_id from the raw message and returns the local file path. "
        f"Use this when user sends media attachments that need to be analyzed."
    )

    return [download_media]
