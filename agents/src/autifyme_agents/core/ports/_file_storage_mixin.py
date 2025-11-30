"""File storage mixin for asset upload/download operations.

Handles file storage operations separate from database CRUD.
Used for persisting images, documents, and other binary assets.
"""

from abc import ABC, abstractmethod
from typing import Any


class FileStorageMixin(ABC):
    """Abstract interface for file/asset storage operations.

    Implementations handle:
    - Uploading files to persistent storage (e.g., Supabase Storage, S3)
    - Deleting files from storage
    - Generating public URLs for stored assets

    Used by:
    - HITL middleware: Upload assets after approval
    - Cleanup flows: Delete rejected/expired assets
    """

    @abstractmethod
    async def upload_asset(
        self,
        file_path: str,
        bucket: str = "assets",
        folder: str = "products",
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload file to persistent storage.

        Used for persisting processed images after HITL approval.
        Generates unique storage path: bucket/folder/timestamp_uuid.ext

        Args:
            file_path: Local file path to upload
            bucket: Storage bucket name (default: "assets")
            folder: Folder within bucket (default: "products")
            content_type: MIME type (auto-detected if None)

        Returns:
            Dict with:
                - success: bool
                - storage_path: Path within bucket
                - bucket: Bucket name
                - public_url: Public URL for the asset
                - size_bytes: File size
                - content_type: MIME type

        Raises:
            StorageError: On upload failure
            FileNotFoundError: If local file doesn't exist
        """
        pass

    @abstractmethod
    async def delete_asset(
        self,
        storage_path: str,
        bucket: str = "assets",
    ) -> bool:
        """Delete file from persistent storage.

        Used for cleanup on HITL rejection or error recovery.

        Args:
            storage_path: Path within bucket (e.g., "products/20251130_abc123.png")
            bucket: Storage bucket name (default: "assets")

        Returns:
            True if deleted successfully

        Raises:
            StorageError: On delete failure
        """
        pass

    @abstractmethod
    def get_asset_public_url(
        self,
        storage_path: str,
        bucket: str = "assets",
    ) -> str:
        """Get public URL for stored asset.

        Args:
            storage_path: Path within bucket
            bucket: Storage bucket name

        Returns:
            Public URL for the asset
        """
        pass
