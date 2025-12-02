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
        """Download media from the messaging platform and persist to cloud storage.

        Downloads media from the platform, optionally uploads to Supabase inbox
        for persistence across serverless invocations. Returns both local path
        (for immediate use) and cloud URL (for persistent references).

        thread_id is automatically injected from RunnableConfig if not provided.
        This enables automatic cloud storage persistence without requiring the
        LLM to explicitly pass thread_id.

        Args:
            media_id: Platform-specific media identifier
            thread_id: Conversation thread ID for organizing uploads (e.g., "whatsapp:123:919...")
                      Auto-injected from RunnableConfig if not provided.
            config: RunnableConfig (auto-injected by LangChain runtime)

        Returns:
            Dict with:
                - local_path: Local filesystem path (ephemeral on serverless)
                - storage_url: Supabase public URL (persistent, use this for references)
                - storage_path: Path within bucket (for move operations)
                - mime_type: MIME type of the media
                - size_bytes: File size in bytes

        Raises:
            Exception: If media download fails
        """
        # Inject thread_id from config if not explicitly provided
        if thread_id is None and config is not None:
            configurable = config.get("configurable", {})
            thread_id = configurable.get("thread_id")
            if thread_id:
                logger.debug(
                    "Injected thread_id from RunnableConfig",
                    extra={"thread_id": thread_id}
                )

        try:
            logger.info(
                f"Downloading media from {platform_name}",
                extra={"media_id": media_id, "platform": platform_name, "thread_id": thread_id}
            )

            # Download with bytes for storage upload
            if hasattr(channel, 'download_media_with_bytes'):
                media_path, media_bytes, mime_type = channel.download_media_with_bytes(media_id)
            else:
                # Fallback for channels without bytes support
                downloaded_path = channel.download_media(media_id)
                if downloaded_path is None:
                    raise ValueError(f"Failed to download media: {media_id}")
                media_path = downloaded_path
                media_bytes = media_path.read_bytes()
                mime_type = "application/octet-stream"

            result: dict[str, Any] = {
                "storage_url": None,  # Primary - use this for references
                "storage_path": None,  # Path within bucket
                "local_path": str(media_path),  # Fallback only - ephemeral on serverless
                "mime_type": mime_type,
                "size_bytes": len(media_bytes),
            }

            # Upload to Supabase inbox if storage is available and thread_id provided
            if storage is not None and thread_id is not None:
                filename = Path(media_path).name
                try:
                    # Run async upload in sync context
                    try:
                        asyncio.get_running_loop()  # Check if loop exists (raises RuntimeError if not)
                        # Already in async context - use thread pool
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
                        # No running loop - safe to use asyncio.run
                        upload_result = asyncio.run(
                            storage.upload_to_inbox(
                                file_bytes=media_bytes,
                                thread_id=thread_id,
                                filename=filename,
                                content_type=mime_type,
                            )
                        )

                    result["storage_url"] = upload_result["public_url"]
                    result["storage_path"] = upload_result["storage_path"]

                    logger.info(
                        "Media persisted to inbox",
                        extra={
                            "media_id": media_id,
                            "storage_url": result["storage_url"],
                            "thread_id": thread_id,
                        }
                    )
                except Exception as upload_error:
                    # Log but don't fail - local path still usable for same-request
                    logger.warning(
                        f"Failed to persist media to inbox (local path still available): {upload_error}",
                        extra={"media_id": media_id, "thread_id": thread_id}
                    )

            logger.info(
                "Media downloaded successfully",
                extra={
                    "media_id": media_id,
                    "local_path": result["local_path"],
                    "storage_url": result["storage_url"],
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
        f"Download media from {platform_name} and persist to Supabase inbox. "
        f"Returns storage_url (persistent, USE THIS) and local_path (ephemeral fallback). "
        f"CRITICAL: Always use storage_url for image references - local_path is deleted on serverless."
    )

    return [download_media]
