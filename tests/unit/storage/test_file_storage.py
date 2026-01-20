"""Unit tests for file storage operations.

Tests FileStorageMixin implementation in both FakeStorage and SupabaseStorageClient.
Covers upload, delete, and URL generation for assets.
"""

import tempfile
from pathlib import Path

import pytest

from tests.fixtures.fake_storage import FakeStorage


@pytest.fixture
def storage():
    """Create fresh FakeStorage instance."""
    return FakeStorage()


@pytest.fixture
def temp_image_file():
    """Create a temporary test image file."""
    from PIL import Image

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create a simple 100x100 red image
        img = Image.new("RGB", (100, 100), color="red")
        img.save(f, format="PNG")
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_jpeg_file():
    """Create a temporary JPEG file."""
    from PIL import Image

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img = Image.new("RGB", (200, 150), color="blue")
        img.save(f, format="JPEG")
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_text_file():
    """Create a temporary text file."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("Test content for file upload")
        yield f.name
    Path(f.name).unlink(missing_ok=True)


# =============================================================================
# Upload Asset Tests
# =============================================================================


@pytest.mark.asyncio
class TestUploadAsset:
    """Test upload_asset method."""

    async def test_upload_png_file(self, storage, temp_image_file):
        """Test uploading PNG image file."""
        result = await storage.upload_asset(
            file_path=temp_image_file,
            bucket="assets",
            folder="products",
        )

        assert result["success"] is True
        assert result["bucket"] == "assets"
        assert result["storage_path"].startswith("products/")
        assert result["storage_path"].endswith(".png")
        assert result["content_type"] == "image/png"
        assert result["size_bytes"] > 0
        assert "public_url" in result

    async def test_upload_jpeg_file(self, storage, temp_jpeg_file):
        """Test uploading JPEG image file."""
        result = await storage.upload_asset(
            file_path=temp_jpeg_file,
            bucket="assets",
            folder="products",
        )

        assert result["success"] is True
        assert result["storage_path"].endswith(".jpg")
        assert result["content_type"] == "image/jpeg"

    async def test_upload_with_custom_bucket(self, storage, temp_image_file):
        """Test uploading to custom bucket."""
        result = await storage.upload_asset(
            file_path=temp_image_file,
            bucket="marketing",
            folder="campaigns",
        )

        assert result["bucket"] == "marketing"
        assert result["storage_path"].startswith("campaigns/")
        assert "marketing" in result["public_url"]

    async def test_upload_with_explicit_content_type(self, storage, temp_text_file):
        """Test uploading with explicit content type."""
        result = await storage.upload_asset(
            file_path=temp_text_file,
            bucket="assets",
            folder="documents",
            content_type="text/plain",
        )

        assert result["content_type"] == "text/plain"

    async def test_upload_generates_unique_paths(self, storage, temp_image_file):
        """Test that multiple uploads generate unique paths."""
        result1 = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )
        result2 = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )

        assert result1["storage_path"] != result2["storage_path"]
        assert result1["public_url"] != result2["public_url"]

    async def test_upload_nonexistent_file_raises_error(self, storage):
        """Test uploading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await storage.upload_asset(
                file_path="/nonexistent/path/image.png",
                bucket="assets",
                folder="products",
            )

    async def test_upload_stores_file_content(self, storage, temp_image_file):
        """Test that uploaded file content is stored."""
        result = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )

        # Verify in FakeStorage's internal storage
        bucket_key = f"{result['bucket']}/{result['storage_path']}"
        assert bucket_key in storage._file_storage
        assert storage._file_storage[bucket_key]["size_bytes"] == result["size_bytes"]

    async def test_upload_default_bucket_and_folder(self, storage, temp_image_file):
        """Test upload uses default bucket and folder."""
        result = await storage.upload_asset(file_path=temp_image_file)

        assert result["bucket"] == "assets"
        assert result["storage_path"].startswith("products/")


# =============================================================================
# Delete Asset Tests
# =============================================================================


@pytest.mark.asyncio
class TestDeleteAsset:
    """Test delete_asset method."""

    async def test_delete_existing_asset(self, storage, temp_image_file):
        """Test deleting an existing asset."""
        # First upload
        upload_result = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )

        # Then delete
        result = await storage.delete_asset(
            storage_path=upload_result["storage_path"], bucket="assets"
        )

        assert result is True

        # Verify removed from storage
        bucket_key = f"assets/{upload_result['storage_path']}"
        assert bucket_key not in storage._file_storage

    async def test_delete_nonexistent_asset_is_idempotent(self, storage):
        """Test deleting nonexistent asset returns True (idempotent)."""
        result = await storage.delete_asset(storage_path="nonexistent/path.png", bucket="assets")

        # Should return True (idempotent behavior)
        assert result is True

    async def test_delete_from_custom_bucket(self, storage, temp_image_file):
        """Test deleting from custom bucket."""
        # Upload to custom bucket
        upload_result = await storage.upload_asset(
            file_path=temp_image_file, bucket="marketing", folder="campaigns"
        )

        # Delete from same bucket
        result = await storage.delete_asset(
            storage_path=upload_result["storage_path"], bucket="marketing"
        )

        assert result is True

    async def test_delete_multiple_assets(self, storage, temp_image_file, temp_jpeg_file):
        """Test deleting multiple assets."""
        # Upload two files
        result1 = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )
        result2 = await storage.upload_asset(
            file_path=temp_jpeg_file, bucket="assets", folder="products"
        )

        # Delete both
        await storage.delete_asset(storage_path=result1["storage_path"], bucket="assets")
        await storage.delete_asset(storage_path=result2["storage_path"], bucket="assets")

        # Verify both removed
        assert f"assets/{result1['storage_path']}" not in storage._file_storage
        assert f"assets/{result2['storage_path']}" not in storage._file_storage


# =============================================================================
# Get Public URL Tests
# =============================================================================


class TestGetAssetPublicUrl:
    """Test get_asset_public_url method."""

    def test_get_public_url_format(self, storage):
        """Test public URL format."""
        url = storage.get_asset_public_url(
            storage_path="products/20251130_abc123.png", bucket="assets"
        )

        assert "assets" in url
        assert "products/20251130_abc123.png" in url

    def test_get_public_url_custom_bucket(self, storage):
        """Test public URL with custom bucket."""
        url = storage.get_asset_public_url(storage_path="campaigns/banner.jpg", bucket="marketing")

        assert "marketing" in url
        assert "campaigns/banner.jpg" in url

    def test_get_public_url_default_bucket(self, storage):
        """Test public URL with default bucket."""
        url = storage.get_asset_public_url(storage_path="products/image.png")

        assert "assets" in url
        assert "products/image.png" in url

    async def test_public_url_matches_upload_result(self, storage, temp_image_file):
        """Test that get_asset_public_url matches upload result URL."""
        upload_result = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )

        generated_url = storage.get_asset_public_url(
            storage_path=upload_result["storage_path"], bucket="assets"
        )

        assert generated_url == upload_result["public_url"]


# =============================================================================
# Integration Scenarios
# =============================================================================


@pytest.mark.asyncio
class TestFileStorageIntegration:
    """Test file storage in realistic scenarios."""

    async def test_upload_delete_cycle(self, storage, temp_image_file):
        """Test complete upload-delete lifecycle."""
        # Upload
        upload_result = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )
        assert upload_result["success"] is True

        # Verify exists
        bucket_key = f"assets/{upload_result['storage_path']}"
        assert bucket_key in storage._file_storage

        # Delete
        delete_result = await storage.delete_asset(
            storage_path=upload_result["storage_path"], bucket="assets"
        )
        assert delete_result is True

        # Verify removed
        assert bucket_key not in storage._file_storage

    async def test_multiple_folder_uploads(self, storage, temp_image_file):
        """Test uploading to multiple folders."""
        folders = ["products", "variants", "marketing", "thumbnails"]
        results = []

        for folder in folders:
            result = await storage.upload_asset(
                file_path=temp_image_file, bucket="assets", folder=folder
            )
            results.append(result)

        # Verify all uploaded to correct folders
        for i, folder in enumerate(folders):
            assert results[i]["storage_path"].startswith(f"{folder}/")

    async def test_storage_isolation_between_buckets(
        self, storage, temp_image_file, temp_jpeg_file
    ):
        """Test that buckets are isolated."""
        # Upload to different buckets
        result1 = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )
        result2 = await storage.upload_asset(
            file_path=temp_jpeg_file, bucket="marketing", folder="products"
        )

        # Delete from assets bucket only
        await storage.delete_asset(storage_path=result1["storage_path"], bucket="assets")

        # Verify assets file deleted, marketing file still exists
        assert f"assets/{result1['storage_path']}" not in storage._file_storage
        assert f"marketing/{result2['storage_path']}" in storage._file_storage

    async def test_transaction_does_not_affect_file_storage(self, storage, temp_image_file):
        """Test that file uploads are outside transaction scope."""
        # Upload file
        upload_result = await storage.upload_asset(
            file_path=temp_image_file, bucket="assets", folder="products"
        )

        # Start transaction and create data
        async with storage.transaction():
            await storage.insert_entity("products", {"name": "Test Product", "sku": "TEST-001"})

        # File should still exist (not affected by transaction)
        bucket_key = f"assets/{upload_result['storage_path']}"
        assert bucket_key in storage._file_storage

    async def test_file_storage_with_various_extensions(self, storage):
        """Test file storage with various file extensions."""
        # Create temp files with different extensions
        extensions = [".png", ".jpg", ".webp", ".pdf", ".json"]

        for ext in extensions:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(b"test content")
                temp_path = f.name

            try:
                result = await storage.upload_asset(
                    file_path=temp_path, bucket="assets", folder="mixed"
                )
                assert result["storage_path"].endswith(ext)
            finally:
                Path(temp_path).unlink(missing_ok=True)
