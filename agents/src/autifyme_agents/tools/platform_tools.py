"""Platform-specific tools for media download and message handling.

These tools enable MessageIntentSpecialist to download media from various
messaging platforms without hardcoding platform logic in the Runner.

Storage Architecture:
    User-uploaded images are immediately persisted to Supabase Storage (inbox folder)
    to survive Vercel /tmp cleanup. The tool returns the Supabase public URL.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Protocol

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MediaDownloadResult(BaseModel):
    """Result of media download with both local and cloud paths."""

    local_path: str = Field(description="Local filesystem path (may be ephemeral)")
    storage_url: str | None = Field(
        default=None,
        description="Supabase public URL (persistent, preferred for references)"
    )
    storage_path: str | None = Field(
        default=None,
        description="Path within Supabase bucket (for move operations)"
    )
    mime_type: str = Field(description="MIME type of the media")
    size_bytes: int = Field(description="File size in bytes")


class MediaDownloader(Protocol):
    """Minimal interface for media download capability.

    Tools layer depends only on this protocol, not on full MessagingChannel.
    This preserves hexagonal architecture (core doesn't depend on adapters).
    """

    def download_media(self, media_id: str) -> Path | None:
        """Download media and return local path."""
        ...

    def download_media_with_bytes(self, media_id: str) -> tuple[Path, bytes, str]:
        """Download media and return path, bytes, and mime type."""
        ...


class StorageUploader(Protocol):
    """Minimal interface for storage upload capability."""

    async def upload_to_inbox(
        self,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Upload to inbox folder."""
        ...


def create_platform_media_tools(
    channel: MediaDownloader,
    storage: StorageUploader | None = None,
) -> list[Any]:
    """Create platform-specific media download tools.

    Args:
        channel: Object implementing MediaDownloader protocol (e.g., WhatsAppChannel)
        storage: Optional storage client for persisting to Supabase inbox

    Returns:
        List of platform-specific tools for media operations
    """
    platform_name = channel.__class__.__name__.replace("Channel", "").lower()

    @tool
    def download_media(
        media_id: str,
        thread_id: str | None = None,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        """Download media from the messaging platform and persist to Supabase.

        Downloads media and uploads to Supabase inbox for serverless persistence.
        Returns storage_url for all subsequent operations.

        Args:
            media_id: Platform-specific media identifier
            thread_id: Auto-injected from session context
            config: RunnableConfig (auto-injected by LangChain)

        Returns:
            Dict with storage_url, storage_path, mime_type, size_bytes

        Raises:
            Exception: If download or upload fails
        """
        # Inject thread_id from config if not explicitly provided
        if thread_id is None and config is not None:
            configurable = config.get("configurable", {})
            thread_id = configurable.get("thread_id")

        try:
            logger.info(
                f"Downloading media from {platform_name}",
                extra={"media_id": media_id, "platform": platform_name, "thread_id": thread_id}
            )

            # Download with bytes for storage upload
            if hasattr(channel, 'download_media_with_bytes'):
                media_path, media_bytes, mime_type = channel.download_media_with_bytes(media_id)
            else:
                downloaded_path = channel.download_media(media_id)
                if downloaded_path is None:
                    raise ValueError(f"Failed to download media: {media_id}")
                media_path = downloaded_path
                media_bytes = media_path.read_bytes()
                mime_type = "application/octet-stream"

            # Storage is required - fail if not configured
            if storage is None or thread_id is None:
                raise ValueError(
                    "Storage and thread_id required for media persistence. "
                    f"storage={storage is not None}, thread_id={thread_id}"
                )

            filename = Path(media_path).name

            # Upload to Supabase inbox
            try:
                asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        storage.upload_to_inbox(
                            file_bytes=media_bytes,
                            thread_id=thread_id,
                            filename=filename,
                            content_type=mime_type,
                        )
                    )
                    upload_result = future.result()
            except RuntimeError:
                upload_result = asyncio.run(
                    storage.upload_to_inbox(
                        file_bytes=media_bytes,
                        thread_id=thread_id,
                        filename=filename,
                        content_type=mime_type,
                    )
                )

            result = {
                "storage_url": upload_result["public_url"],
                "storage_path": upload_result["storage_path"],
                "mime_type": mime_type,
                "size_bytes": len(media_bytes),
            }

            logger.info(
                "Media persisted to inbox",
                extra={
                    "media_id": media_id,
                    "storage_url": result["storage_url"],
                    "thread_id": thread_id,
                }
            )
            return result

        except Exception as e:
            logger.exception(
                f"Failed to download media from {platform_name}",
                extra={"media_id": media_id, "error": str(e)}
            )
            raise

    # Set dynamic name and description based on platform
    download_media.name = f"download_{platform_name}_media"
    download_media.description = (
        f"Download media from {platform_name} and persist to Supabase inbox/. "
        f"Returns: storage_url (public URL for references), storage_path (bucket path), mime_type, size_bytes. "
        f"Use storage_url in all subsequent operations - images are already persistent."
    )

    return [download_media]
