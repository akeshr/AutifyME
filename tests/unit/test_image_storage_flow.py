"""Tests for image storage flow - inbox, pending, and move operations.

Tests the serverless-compatible image persistence architecture:
- WhatsApp images -> inbox/{thread_id}/ (immediate, no HITL)
- AI-generated images -> pending/{thread_id}/ (awaiting HITL)
- On approval: pending/ -> products/ (move operation)
"""


import pytest

from tests.fixtures.fake_storage import FakeStorage

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def storage() -> FakeStorage:
    """Create fresh FakeStorage instance."""
    return FakeStorage()


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Create sample PNG image bytes."""
    # Minimal valid PNG: 1x1 transparent pixel
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82
    ])


@pytest.fixture
def thread_id() -> str:
    """Sample thread ID in WhatsApp format."""
    return "whatsapp:123456789:919876543210"


# =============================================================================
# Upload to Inbox Tests (WhatsApp images)
# =============================================================================


class TestUploadToInbox:
    """Tests for upload_to_inbox - WhatsApp user-uploaded images."""

    @pytest.mark.asyncio
    async def test_upload_to_inbox_success(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test successful upload to inbox folder."""
        result = await storage.upload_to_inbox(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="20251202_143022_mediaid.png",
            content_type="image/png",
        )

        assert result["success"] is True
        assert "inbox/" in result["storage_path"]
        assert "whatsapp_123456789_919876543210" in result["storage_path"]
        assert result["bucket"] == "assets"
        assert result["public_url"].startswith("https://")
        assert result["size_bytes"] == len(sample_image_bytes)
        assert result["content_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_upload_to_inbox_sanitizes_thread_id(
        self, storage: FakeStorage, sample_image_bytes: bytes
    ):
        """Test that thread_id colons are replaced with underscores."""
        result = await storage.upload_to_inbox(
            file_bytes=sample_image_bytes,
            thread_id="whatsapp:123:456",
            filename="test.png",
            content_type="image/png",
        )

        # Colons should be replaced with underscores
        assert "whatsapp_123_456" in result["storage_path"]
        assert ":" not in result["storage_path"]

    @pytest.mark.asyncio
    async def test_upload_to_inbox_stores_content(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test that file content is actually stored."""
        await storage.upload_to_inbox(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="test.png",
            content_type="image/png",
        )

        # Verify content is in storage
        assert hasattr(storage, "_file_storage")
        stored_keys = list(storage._file_storage.keys())
        assert len(stored_keys) == 1
        assert storage._file_storage[stored_keys[0]]["content"] == sample_image_bytes


# =============================================================================
# Upload to Pending Tests (AI-generated images)
# =============================================================================


class TestUploadToPending:
    """Tests for upload_to_pending - AI-generated images awaiting HITL."""

    @pytest.mark.asyncio
    async def test_upload_to_pending_success(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test successful upload to pending folder."""
        result = await storage.upload_to_pending(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="20251202_generate_abc123.png",
            content_type="image/png",
        )

        assert result["success"] is True
        assert "pending/" in result["storage_path"]
        assert "whatsapp_123456789_919876543210" in result["storage_path"]
        assert result["bucket"] == "assets"
        assert result["public_url"].startswith("https://")

    @pytest.mark.asyncio
    async def test_upload_to_pending_different_from_inbox(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test that pending uses different folder than inbox."""
        inbox_result = await storage.upload_to_inbox(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="inbox_file.png",
            content_type="image/png",
        )

        pending_result = await storage.upload_to_pending(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="pending_file.png",
            content_type="image/png",
        )

        assert "inbox/" in inbox_result["storage_path"]
        assert "pending/" in pending_result["storage_path"]
        assert inbox_result["storage_path"] != pending_result["storage_path"]


# =============================================================================
# Move Asset Tests (pending -> products on approval)
# =============================================================================


class TestMoveAsset:
    """Tests for move_asset - moving approved images to products folder."""

    @pytest.mark.asyncio
    async def test_move_asset_success(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test successful move from pending to products."""
        # First upload to pending
        upload_result = await storage.upload_to_pending(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="20251202_generate_abc123.png",
            content_type="image/png",
        )

        # Then move to products
        move_result = await storage.move_asset(
            source_path=upload_result["storage_path"],
            target_folder="products",
            bucket="assets",
        )

        assert move_result["success"] is True
        assert "products/" in move_result["storage_path"]
        assert "pending/" not in move_result["storage_path"]
        assert move_result["size_bytes"] == len(sample_image_bytes)

    @pytest.mark.asyncio
    async def test_move_asset_deletes_source(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test that move deletes source file."""
        # Upload to pending
        upload_result = await storage.upload_to_pending(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="to_move.png",
            content_type="image/png",
        )

        source_key = f"assets/{upload_result['storage_path']}"
        assert source_key in storage._file_storage

        # Move to products
        move_result = await storage.move_asset(
            source_path=upload_result["storage_path"],
            target_folder="products",
        )

        # Source should be deleted
        assert source_key not in storage._file_storage

        # Target should exist
        target_key = f"assets/{move_result['storage_path']}"
        assert target_key in storage._file_storage

    @pytest.mark.asyncio
    async def test_move_asset_not_found_raises(self, storage: FakeStorage):
        """Test that moving non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await storage.move_asset(
                source_path="pending/nonexistent/file.png",
                target_folder="products",
            )

    @pytest.mark.asyncio
    async def test_move_asset_preserves_content(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test that move preserves file content."""
        # Upload to pending
        upload_result = await storage.upload_to_pending(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="content_test.png",
            content_type="image/png",
        )

        # Move to products
        move_result = await storage.move_asset(
            source_path=upload_result["storage_path"],
            target_folder="products",
        )

        # Verify content is preserved
        target_key = f"assets/{move_result['storage_path']}"
        assert storage._file_storage[target_key]["content"] == sample_image_bytes


# =============================================================================
# AssetUpload Schema Tests
# =============================================================================


class TestAssetUploadSchema:
    """Tests for AssetUpload schema validation."""

    def test_asset_upload_with_storage_path(self):
        """Test AssetUpload with storage_path (preferred)."""
        from autifyme_agents.schemas.write_intent import AssetUpload

        upload = AssetUpload(
            storage_path="pending/whatsapp_123_456/image.png",
            returns="product_image",
            caption="Product photo",
            target_folder="products",
        )

        assert upload.storage_path == "pending/whatsapp_123_456/image.png"
        assert upload.temp_path is None
        assert upload.target_folder == "products"

    def test_asset_upload_with_temp_path(self):
        """Test AssetUpload with temp_path (legacy)."""
        from autifyme_agents.schemas.write_intent import AssetUpload

        upload = AssetUpload(
            temp_path="/tmp/media_downloads/image.png",
            returns="product_image",
            caption="Product photo",
        )

        assert upload.temp_path == "/tmp/media_downloads/image.png"
        assert upload.storage_path is None
        assert upload.folder == "products"

    def test_asset_upload_requires_one_path(self):
        """Test that AssetUpload requires either temp_path or storage_path."""
        from autifyme_agents.schemas.write_intent import AssetUpload

        with pytest.raises(ValueError, match="Either temp_path or storage_path"):
            AssetUpload(
                returns="product_image",
                caption="Product photo",
            )

    def test_asset_upload_rejects_both_paths(self):
        """Test that AssetUpload rejects both temp_path and storage_path."""
        from autifyme_agents.schemas.write_intent import AssetUpload

        with pytest.raises(ValueError, match="Cannot provide both"):
            AssetUpload(
                temp_path="/tmp/image.png",
                storage_path="pending/thread/image.png",
                returns="product_image",
            )


# =============================================================================
# WriteIntent Executor Move Operation Tests
# =============================================================================


class TestExecutorMoveOperation:
    """Tests for WriteIntent executor handling storage_path moves."""

    @pytest.mark.asyncio
    async def test_executor_moves_storage_path(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test executor moves from storage_path instead of uploading."""
        from autifyme_agents.schemas.write_intent import AssetUpload, Operation, WriteIntent
        from autifyme_agents.tools.data_engine._executor import MultiOperationExecutor

        # First upload to pending (simulating Image Studio)
        pending_result = await storage.upload_to_pending(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="generated.png",
            content_type="image/png",
        )

        # Create WriteIntent with storage_path
        intent = WriteIntent(
            goal="Create asset record for generated image",
            reasoning="Moving approved image to products and creating record",
            asset_uploads=[
                AssetUpload(
                    storage_path=pending_result["storage_path"],
                    returns="img",
                    caption="Generated product image",
                    target_folder="products",
                )
            ],
            operations=[
                Operation(
                    action="create",
                    table="assets",
                    data={
                        "file_url": "@img.public_url",
                        "file_type": "@img.content_type",
                        "file_size": "@img.size_bytes",
                    },
                    returns="asset",
                )
            ],
            impact={"creates": {"assets": 1}},
        )

        # Execute
        executor = MultiOperationExecutor(storage)
        result = await executor.execute_intent(intent)

        assert result.success is True
        assert len(result.uploaded_assets) == 1

        # Verify move happened (products/ not pending/)
        assert "products/" in result.uploaded_assets[0]["storage_path"]
        assert "pending/" not in result.uploaded_assets[0]["storage_path"]

        # Verify DB record created with resolved URL
        assert len(result.created_entities.get("assets", [])) == 1
        asset_record = result.created_entities["assets"][0]
        assert "products/" in asset_record["file_url"]


# =============================================================================
# End-to-End Flow Tests
# =============================================================================


class TestEndToEndImageFlow:
    """End-to-end tests for complete image handling flows."""

    @pytest.mark.asyncio
    async def test_whatsapp_image_to_product_flow(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test complete flow: WhatsApp image -> inbox -> product record."""
        from autifyme_agents.schemas.write_intent import Operation, WriteIntent
        from autifyme_agents.tools.data_engine._executor import MultiOperationExecutor

        # Step 1: WhatsApp image uploaded to inbox
        inbox_result = await storage.upload_to_inbox(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="user_product.png",
            content_type="image/png",
        )

        # Step 2: Catalog specialist creates asset record
        # (User images don't need move - they're already "approved" by user sending them)
        intent = WriteIntent(
            goal="Create asset from user-uploaded image",
            reasoning="User sent product image via WhatsApp",
            asset_uploads=[],  # No upload needed - already in inbox
            operations=[
                Operation(
                    action="create",
                    table="assets",
                    data={
                        "file_url": inbox_result["public_url"],
                        "file_type": inbox_result["content_type"],
                        "file_size": inbox_result["size_bytes"],
                        "source": "whatsapp_upload",
                    },
                    returns="asset",
                )
            ],
            impact={"creates": {"assets": 1}},
        )

        executor = MultiOperationExecutor(storage)
        result = await executor.execute_intent(intent)

        assert result.success is True
        assert len(result.created_entities.get("assets", [])) == 1
        assert "inbox/" in result.created_entities["assets"][0]["file_url"]

    @pytest.mark.asyncio
    async def test_ai_generated_image_approval_flow(
        self, storage: FakeStorage, sample_image_bytes: bytes, thread_id: str
    ):
        """Test complete flow: AI generates -> pending -> HITL approve -> products."""
        from autifyme_agents.schemas.write_intent import AssetUpload, Operation, WriteIntent
        from autifyme_agents.tools.data_engine._executor import MultiOperationExecutor

        # Step 1: Image Studio generates image -> pending (simulated)
        pending_result = await storage.upload_to_pending(
            file_bytes=sample_image_bytes,
            thread_id=thread_id,
            filename="lifestyle_shot.png",
            content_type="image/png",
        )

        # Verify it's in pending
        assert "pending/" in pending_result["storage_path"]

        # Step 2: HITL approval -> Creative specialist calls write_data
        intent = WriteIntent(
            goal="Approve and store AI-generated lifestyle shot",
            reasoning="User approved the generated image",
            asset_uploads=[
                AssetUpload(
                    storage_path=pending_result["storage_path"],
                    returns="lifestyle_img",
                    caption="AI-generated lifestyle shot",
                    target_folder="products",
                )
            ],
            operations=[
                Operation(
                    action="create",
                    table="assets",
                    data={
                        "file_url": "@lifestyle_img.public_url",
                        "file_type": "@lifestyle_img.content_type",
                        "file_size": "@lifestyle_img.size_bytes",
                        "source": "ai_generated",
                    },
                    returns="asset",
                )
            ],
            impact={"creates": {"assets": 1}},
        )

        executor = MultiOperationExecutor(storage)
        result = await executor.execute_intent(intent)

        assert result.success is True

        # Verify image moved to products
        assert "products/" in result.uploaded_assets[0]["storage_path"]

        # Verify pending source is gone
        source_key = f"assets/{pending_result['storage_path']}"
        assert source_key not in storage._file_storage

        # Verify DB record points to products URL
        asset_record = result.created_entities["assets"][0]
        assert "products/" in asset_record["file_url"]
        assert "pending/" not in asset_record["file_url"]
