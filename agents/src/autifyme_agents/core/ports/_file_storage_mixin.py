"""File storage mixin for asset upload/download operations.

Handles file storage operations separate from database CRUD.
Used for persisting images, documents, and other binary assets.

Storage Structure:
    assets/
        inbox/{thread_id}/      - User-uploaded images (WhatsApp) - no HITL
        pending/{thread_id}/    - AI-generated awaiting approval
        products/               - Approved permanent images
"""

from abc import ABC, abstractmethod
from typing import Any


class FileStorageMixin(ABC):
    """Abstract interface for file/asset storage operations.

    Implementations handle:
    - Uploading files to persistent storage (e.g., Supabase Storage, S3)
    - Moving files between folders (pending -> products)
    - Deleting files from storage
    - Generating public URLs for stored assets

    Storage Zones:
    - inbox/{thread_id}/: User-uploaded images from WhatsApp (immediate, no HITL)
    - pending/{thread_id}/: AI-generated images awaiting HITL approval
    - products/: Approved permanent product images

    Used by:
    - WhatsApp channel: Upload user images to inbox/
    - Image Studio: Upload generated images to pending/
    - WriteIntent executor: Move from pending/ to products/ on approval
    - HITL middleware: Delete from pending/ on rejection
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
    async def upload_to_inbox(
        self,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Upload user-provided media to inbox folder.

        Used by WhatsApp channel for immediate persistence of user-uploaded images.
        No HITL required - user provided the image.

        Storage path: inbox/{thread_id}/{filename}

        Args:
            file_bytes: Raw file content
            thread_id: Conversation thread ID (e.g., "whatsapp:123:919...")
            filename: Original or generated filename with extension
            content_type: MIME type (e.g., "image/jpeg")
            bucket: Storage bucket name (default: "assets")

        Returns:
            Dict with:
                - success: bool
                - storage_path: Path within bucket (e.g., "inbox/whatsapp_123_919/file.jpg")
                - bucket: Bucket name
                - public_url: Public URL for the asset
                - size_bytes: File size
                - content_type: MIME type

        Raises:
            StorageError: On upload failure
        """
        pass

    @abstractmethod
    async def upload_to_pending(
        self,
        file_bytes: bytes,
        thread_id: str,
        filename: str,
        content_type: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Upload AI-generated media to pending folder.

        Used by Image Studio for generated/edited images awaiting HITL approval.
        Images in pending/ are moved to products/ on approval or deleted on rejection.

        Storage path: pending/{thread_id}/{filename}

        Args:
            file_bytes: Raw file content
            thread_id: Conversation thread ID (e.g., "whatsapp:123:919...")
            filename: Generated filename with extension
            content_type: MIME type (e.g., "image/png")
            bucket: Storage bucket name (default: "assets")

        Returns:
            Dict with:
                - success: bool
                - storage_path: Path within bucket (e.g., "pending/whatsapp_123_919/file.png")
                - bucket: Bucket name
                - public_url: Public URL for the asset
                - size_bytes: File size
                - content_type: MIME type

        Raises:
            StorageError: On upload failure
        """
        pass

    @abstractmethod
    async def move_asset(
        self,
        source_path: str,
        target_folder: str,
        bucket: str = "assets",
    ) -> dict[str, Any]:
        """Move asset from one folder to another within same bucket.

        Used by WriteIntent executor to move approved images:
        - pending/{thread_id}/file.png -> products/file.png

        Args:
            source_path: Current path within bucket (e.g., "pending/thread/file.png")
            target_folder: Target folder (e.g., "products")
            bucket: Storage bucket name (default: "assets")

        Returns:
            Dict with:
                - success: bool
                - storage_path: New path within bucket
                - bucket: Bucket name
                - public_url: New public URL
                - size_bytes: File size
                - content_type: MIME type

        Raises:
            StorageError: On move failure
            FileNotFoundError: If source doesn't exist
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
