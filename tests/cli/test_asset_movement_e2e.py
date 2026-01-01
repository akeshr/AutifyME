"""E2E REPL test for asset movement via write_data tool.

Tests the complete flow:
1. Upload test file to pending/{thread_id}/
2. Execute write_data with asset_uploads
3. Verify file moved to products/
4. Verify asset record created
5. Verify product_assets junction created

Run with: uv run python tests/cli/test_asset_movement_e2e.py
"""

import asyncio
import uuid
from datetime import datetime

# Load env before imports
from dotenv import load_dotenv

load_dotenv(".env")


async def test_move_asset_only():
    """Minimal test for move_asset function only."""
    from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

    print("\n" + "=" * 60)
    print("Minimal Test: move_asset function")
    print("=" * 60)

    storage = SupabaseStorageClient()

    # Create test file path
    test_id = uuid.uuid4().hex[:8]
    test_file = f"test_{test_id}.png"
    thread_id = f"test_thread_{test_id}"

    # Minimal valid PNG (1x1 pixel)
    minimal_png = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE,
        0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, 0x54,
        0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F, 0x00,
        0x05, 0xFE, 0x02, 0xFE, 0x00, 0x00, 0x00, 0x00,
        0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
    ])

    print(f"[1] Upload to pending/...")
    try:
        # Use upload_to_pending method
        upload_result = await storage.upload_to_pending(
            file_bytes=minimal_png,
            thread_id=thread_id,
            filename=test_file,
            content_type="image/png"
        )
        pending_path = upload_result.get("storage_path")
        print(f"    [OK] Uploaded: {pending_path}")
        print(f"    Public URL: {upload_result.get('public_url')}")
    except Exception as e:
        print(f"    [ERROR] {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"\n[2] Move to products/...")
    try:
        result = await storage.move_asset(
            source_path=pending_path,
            target_folder="products",
            bucket="assets"
        )
        print(f"    [OK] Moved!")
        print(f"    storage_path: {result.get('storage_path')}")
        print(f"    public_url: {result.get('public_url')}")
        print(f"    file_name: {result.get('file_name')}")
        print(f"    size_bytes: {result.get('size_bytes')}")

        # Cleanup
        print(f"\n[3] Cleanup...")
        await storage.delete_asset(
            storage_path=result['storage_path'],
            bucket="assets"
        )
        print(f"    [OK] Deleted: {result['storage_path']}")

    except Exception as e:
        print(f"    [ERROR] {e}")
        import traceback
        traceback.print_exc()

    print("\nTest complete.")


async def test_asset_movement_e2e():
    """Test complete asset movement flow via write_data tool."""
    from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient
    from autifyme_agents.schemas.write_intent import AssetUpload, Operation, WriteIntent
    from autifyme_agents.tools.data_engine._executor import MultiOperationExecutor

    print("=" * 60)
    print("E2E Test: Asset Movement via write_data")
    print("=" * 60)

    # Initialize storage
    storage = SupabaseStorageClient()
    print("[OK] Storage client initialized")

    # Test IDs
    test_id = uuid.uuid4().hex[:8]
    test_thread_id = f"test_thread_{test_id}"
    test_file_name = f"test_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    print(f"\n[1] Test Setup")
    print(f"    Thread ID: {test_thread_id}")
    print(f"    File name: {test_file_name}")

    # Minimal valid PNG (1x1 pixel)
    minimal_png = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE,
        0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, 0x54,
        0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F, 0x00,
        0x05, 0xFE, 0x02, 0xFE, 0x00, 0x00, 0x00, 0x00,
        0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
    ])

    # Phase 1: Upload test file to pending/
    print(f"\n[2] Uploading test file to pending/...")
    try:
        upload_result = await storage.upload_to_pending(
            file_bytes=minimal_png,
            thread_id=test_thread_id,
            filename=test_file_name,
            content_type="image/png"
        )
        pending_path = upload_result.get("storage_path")
        print(f"    [OK] File uploaded: {pending_path}")
        print(f"    Public URL: {upload_result.get('public_url')}")
    except Exception as e:
        print(f"    [ERROR] Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Phase 2: Test move_asset directly
    print(f"\n[3] Testing move_asset directly...")
    try:
        move_result = await storage.move_asset(
            source_path=pending_path,
            target_folder="products",
            bucket="assets"
        )
        print(f"    [OK] Asset moved successfully!")
        print(f"    New path: {move_result.get('storage_path')}")
        print(f"    Public URL: {move_result.get('public_url')}")
        print(f"    File name: {move_result.get('file_name')}")
        print(f"    Size: {move_result.get('size_bytes')} bytes")
        print(f"    Content type: {move_result.get('content_type')}")

        # Clean up moved file
        if move_result.get('storage_path'):
            print(f"\n    Cleaning up: {move_result['storage_path']}")
            await storage.delete_asset(
                storage_path=move_result['storage_path'],
                bucket="assets"
            )
            print(f"    [OK] Cleaned up test file")

    except FileNotFoundError as e:
        print(f"    [ERROR] Source file not found: {e}")
    except Exception as e:
        print(f"    [ERROR] Move failed: {e}")
        import traceback
        traceback.print_exc()

    # Phase 3: Full E2E test with WriteIntent
    print(f"\n[4] Full E2E: WriteIntent with asset_uploads...")

    # Re-upload test file for WriteIntent test
    test_file_name_2 = f"test_image2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    try:
        upload_result_2 = await storage.upload_to_pending(
            file_bytes=minimal_png,
            thread_id=test_thread_id,
            filename=test_file_name_2,
            content_type="image/png"
        )
        pending_path_2 = upload_result_2.get("storage_path")
        print(f"    [OK] Test file 2 uploaded: {pending_path_2}")
    except Exception as e:
        print(f"    [ERROR] Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Create WriteIntent with asset_uploads
    print(f"\n    Creating WriteIntent with asset movement...")

    # First, get a real product_id from the database
    product_result = await storage.query_entities(
        table="products",
        filters={"is_active": True},
        columns=["id", "name"],
        limit=1
    )

    if not product_result:
        print(f"    [SKIP] No active products found for junction test")
        print(f"    Testing asset creation only...")

        write_intent = WriteIntent(
            goal="Create test asset record from pending image",
            reasoning="E2E test: Moving image from pending to products and creating asset record",
            hitl_summary="Test asset creation. Reply *approve* to proceed or *reject* to cancel.",
            asset_uploads=[
                AssetUpload(
                    storage_path=pending_path_2,
                    returns="test_asset",
                    caption="E2E Test Image",
                    target_folder="products"
                )
            ],
            operations=[
                Operation(
                    action="create",
                    table="assets",
                    data={
                        "name": "E2E Test Asset",
                        "storage_url": "@test_asset.public_url",
                        "storage_provider": "SUPABASE",
                        "file_name": "@test_asset.file_name",
                        "file_size_bytes": "@test_asset.size_bytes",
                        "mime_type": "@test_asset.content_type",
                        "asset_type": "IMAGE",
                        "status": "ACTIVE",
                        "purpose": "PRODUCT",
                        "category": "HERO",
                        "is_ai_generated": False,
                        "caption": "@test_asset.caption"
                    },
                    returns="asset"
                )
            ],
            impact={
                "creates": {"assets": 1},
                "asset_uploads": 1,
                "warnings": ["E2E test - will be cleaned up"]
            }
        )
    else:
        product_id = product_result[0]["id"]
        product_name = product_result[0]["name"]
        print(f"    Found product: {product_name} ({product_id})")

        write_intent = WriteIntent(
            goal="Create test asset and link to product",
            reasoning="E2E test: Full asset movement flow with product_assets junction",
            hitl_summary=f"Creating test asset linked to {product_name}. Reply *approve* to proceed or *reject* to cancel.",
            asset_uploads=[
                AssetUpload(
                    storage_path=pending_path_2,
                    returns="test_asset",
                    caption="E2E Test Image",
                    target_folder="products"
                )
            ],
            operations=[
                Operation(
                    action="create",
                    table="assets",
                    data={
                        "name": "E2E Test Asset",
                        "storage_url": "@test_asset.public_url",
                        "storage_provider": "SUPABASE",
                        "file_name": "@test_asset.file_name",
                        "file_size_bytes": "@test_asset.size_bytes",
                        "mime_type": "@test_asset.content_type",
                        "asset_type": "IMAGE",
                        "status": "ACTIVE",
                        "purpose": "PRODUCT",
                        "category": "HERO",
                        "is_ai_generated": False,
                        "caption": "@test_asset.caption"
                    },
                    returns="asset"
                ),
                Operation(
                    action="create",
                    table="product_assets",
                    data={
                        "product_id": product_id,
                        "product_family_id": None,
                        "asset_id": "@asset.id",
                        "asset_role": "GALLERY",
                        "sort_order": 99,
                        "alt_text": "E2E Test Image"
                    },
                    dependencies=["asset"],
                    returns="product_asset"
                )
            ],
            impact={
                "creates": {"assets": 1, "product_assets": 1},
                "asset_uploads": 1,
                "warnings": ["E2E test - will be cleaned up"]
            }
        )

    # Execute WriteIntent
    print(f"\n    Executing WriteIntent...")
    executor = MultiOperationExecutor(storage)
    result = await executor.execute_intent(write_intent)

    if result.success:
        print(f"    [OK] WriteIntent executed successfully!")
        print(f"    Execution time: {result.execution_time_ms}ms")
        print(f"    Created entities: {result.created_entities}")
        print(f"    Uploaded assets: {result.uploaded_assets}")

        # Cleanup: Delete created records
        print(f"\n[5] Cleanup...")

        if "product_assets" in result.created_entities:
            for pa in result.created_entities["product_assets"]:
                try:
                    await storage.delete_entities(
                        table="product_assets",
                        filters={"id": pa["id"]},
                        soft_delete=False
                    )
                    print(f"    [OK] Deleted product_asset: {pa['id']}")
                except Exception as e:
                    print(f"    [WARN] Failed to delete product_asset: {e}")

        if "assets" in result.created_entities:
            for asset in result.created_entities["assets"]:
                try:
                    await storage.delete_entities(
                        table="assets",
                        filters={"id": asset["id"]},
                        soft_delete=False
                    )
                    print(f"    [OK] Deleted asset: {asset['id']}")
                except Exception as e:
                    print(f"    [WARN] Failed to delete asset: {e}")

        # Delete uploaded file from products/
        for asset_info in result.uploaded_assets:
            try:
                await storage.delete_asset(
                    storage_path=asset_info["storage_path"],
                    bucket=asset_info["bucket"]
                )
                print(f"    [OK] Deleted file: {asset_info['storage_path']}")
            except Exception as e:
                print(f"    [WARN] Failed to delete file: {e}")

    else:
        print(f"    [ERROR] WriteIntent failed!")
        print(f"    Error: {result.error_message}")
        print(f"    Rollback performed: {result.rollback_performed}")

    print(f"\n" + "=" * 60)
    print("E2E Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--minimal":
        asyncio.run(test_move_asset_only())
    else:
        asyncio.run(test_asset_movement_e2e())
