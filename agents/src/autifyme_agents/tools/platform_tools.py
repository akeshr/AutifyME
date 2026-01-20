"""Platform-specific tools for media download.

Downloads media from messaging platforms and persists to Supabase Storage.
Returns user-friendly paths (no thread_id visible to LLM).

Path Format:
- LLM sees: "inbox/photo.jpg"
- Internal: "inbox/{thread_id}/photo.jpg"
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Protocol

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.execution_context import get_thread_id, to_user_path

logger = logging.getLogger(__name__)


class MediaDownloader(Protocol):
    """Minimal interface for media download capability."""

    def download_media(self, media_id: str) -> Path | None:
        """Download media and return local path."""
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


class DownloadMediaInput(BaseModel):
    """Input schema for download_media tool."""

    media_id: str = Field(description="Platform-specific media identifier")


def create_platform_media_tools(
    channel: MediaDownloader,
    storage: StorageUploader | None = None,
) -> list[Any]:
    """Create platform-specific media download tools.

    Args:
        channel: Object implementing MediaDownloader protocol
        storage: Storage client for persisting to Supabase inbox

    Returns:
        List of platform-specific tools
    """
    platform_name = channel.__class__.__name__.replace("Channel", "").lower()

    def _download_media_impl(media_id: str) -> dict[str, Any] | list[dict[str, Any]]:
        """Download media and persist to Supabase inbox.

        Returns user-friendly path (no thread_id visible).
        """
        thread_id = get_thread_id()

        try:
            logger.info(
                f"Downloading media from {platform_name}",
                extra={"media_id": media_id, "thread_id": thread_id},
            )

            # Download with bytes for storage upload
            if hasattr(channel, "download_media_with_bytes"):
                media_path, media_bytes, mime_type = channel.download_media_with_bytes(media_id)
            else:
                downloaded_path = channel.download_media(media_id)
                if downloaded_path is None:
                    raise ValueError(f"Failed to download media: {media_id}")
                media_path = downloaded_path
                media_bytes = media_path.read_bytes()
                mime_type = "application/octet-stream"

            # Storage required
            if storage is None or thread_id is None:
                raise ValueError(
                    f"Storage and thread_id required. "
                    f"storage={storage is not None}, thread_id={thread_id}"
                )

            filename = Path(media_path).name

            # Upload to Supabase
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
                        ),
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

            # Convert to user path (strip thread_id)
            storage_path = upload_result["storage_path"]
            user_path = to_user_path(storage_path)

            logger.info(
                "Media persisted to inbox",
                extra={"user_path": user_path, "internal_path": storage_path},
            )

            # Return multimodal content if image, otherwise dict
            if mime_type.startswith("image/"):
                from autifyme_agents.tools.view_image import _load_image_as_data_uri

                try:
                    data_uri, img_metadata = _load_image_as_data_uri(storage_path)
                    return [
                        {
                            "type": "text",
                            "text": (
                                f"Downloaded image to storage.\n"
                                f"storage_path: {user_path}\n"
                                f"mime_type: {mime_type}\n"
                                f"size_bytes: {len(media_bytes)}\n"
                                f"dimensions: {img_metadata['original_size']}"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                    ]
                except Exception as e:
                    logger.warning(f"Failed to load image for preview: {e}")
                    # Fall through to dict return

            return {
                "storage_path": user_path,
                "mime_type": mime_type,
                "size_bytes": len(media_bytes),
            }

        except Exception:
            logger.exception(f"Failed to download media from {platform_name}")
            raise

    download_tool = StructuredTool.from_function(
        func=_download_media_impl,
        name=f"download_{platform_name}_media",
        description=(
            f"Download media from {platform_name} and persist to storage. "
            f"RETURNS: {{storage_path, mime_type, size_bytes}}. "
            f"Use storage_path (e.g., 'inbox/photo.jpg') in view_image, image_studio, write_data."
        ),
        args_schema=DownloadMediaInput,
        return_direct=False,
    )

    return [download_tool]
