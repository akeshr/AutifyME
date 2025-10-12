"""Platform-specific tools for media download and message handling.

These tools enable MessageIntentSpecialist to download media from various
messaging platforms without hardcoding platform logic in the Runner.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain.tools import tool

if TYPE_CHECKING:
    from autifyme_agents.workflows.channels.protocol import MessagingChannel

logger = logging.getLogger(__name__)


def create_platform_media_tools(channel: MessagingChannel) -> list:
    """Create platform-specific media download tools.

    Args:
        channel: The messaging channel adapter (WhatsApp, Telegram, etc.)

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
