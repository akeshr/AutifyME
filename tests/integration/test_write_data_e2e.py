"""End-to-end tests for write_data tool with asset uploads.

Tests the complete workflow:
1. Tool invocation with WriteIntent parameters
2. Asset upload via storage
3. Reference resolution (@name.public_url)
4. Database operations in transaction
5. Rollback on failure

Uses FakeStorage to test without external dependencies.
"""

import tempfile
from pathlib import Path

import pytest

from autifyme_agents.tools.data_engine import create_write_data_tool
from tests.fixtures.fake_storage import FakeStorage


@pytest.fixture
def storage():
    """Create fresh FakeStorage instance."""
    return FakeStorage()


@pytest.fixture
def write_tool(storage):
    """Create write_data tool with FakeStorage."""
    return create_write_data_tool(storage=storage, tables=None)


@pytest.fixture
def temp_image_file():
    """Create a temporary test image file."""
    from PIL import Image

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (100, 100), color="red")
        img.save(f, format="PNG")
        yield f.name
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


# =============================================================================
# Basic Write Operations E2E
# =============================================================================


@pytest.mark.asyncio
class TestWriteDataBasicE2E:
    """E2E tests for basic write operations without assets."""

    async def test_create_single_entity(self, write_tool, storage):
        """Test creating a single entity through write_data tool."""
        result = await write_tool.ainvoke({
            "goal": "Create a new product family",
            "reasoning": "User requested new product family for PET bottles",
            "operations": [
                {
                    "action": "create",
                    "table": "product_families",
                    "data": {
                        "name": "PET Bottles",
                        "slug": "pet-bottles",
                        "description": "Polyethylene terephthalate bottles",
                    },
                    "returns": "family",
                }
            ],
            "impact": {"creates": {"product_families": 1}},
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 1

        # Verify in storage
        families = await storage.query_entities("product_families", {})
        assert len(families) == 1
        assert families[0]["name"] == "PET Bottles"

    async def test_create_with_dependencies(self, write_tool, storage):
        """Test creating entities with dependencies."""
        result = await write_tool.ainvoke({
            "goal": "Create product family with variant axis",
            "reasoning": "Testing dependency resolution",
            "operations": [
                {
                    "action": "create",
                    "table": "product_families",
                    "data": {"name": "Glass Jars", "slug": "glass-jars"},
                    "returns": "family",
                },
                {
                    "action": "create",
                    "table": "variant_axes",
                    "data": {
                        "name": "Size",
                        "product_family_id": "@family.id",
                        "display_order": 1,
                    },
                    "dependencies": ["family"],
                    "returns": "size_axis",
                },
            ],
            "impact": {"creates": {"product_families": 1, "variant_axes": 1}},
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 2

        # Verify dependency was resolved
        axes = await storage.query_entities("variant_axes", {})
        assert len(axes) == 1
        families = await storage.query_entities("product_families", {})
        assert axes[0]["product_family_id"] == families[0]["id"]

    async def test_update_operation(self, write_tool, storage):
        """Test updating entities through write_data tool."""
        # Pre-create entity
        await storage.insert_entity(
            "products",
            {"name": "Old Name", "sku_code": "UPD-001", "price": 10.00},
        )

        result = await write_tool.ainvoke({
            "goal": "Update product name and price",
            "reasoning": "User requested name change",
            "operations": [
                {
                    "action": "update",
                    "table": "products",
                    "filters": {"sku_code": "UPD-001"},
                    "updates": {"name": "New Name", "price": 15.00},
                }
            ],
            "impact": {"updates": {"products": 1}},
        })

        assert result["success"] is True
        assert result["summary"]["total_updated"] == 1

        # Verify update
        products = await storage.query_entities("products", {"sku_code": "UPD-001"})
        assert products[0]["name"] == "New Name"
        assert products[0]["price"] == 15.00

    async def test_delete_operation_soft(self, write_tool, storage):
        """Test soft delete through write_data tool."""
        # Pre-create entity
        await storage.insert_entity(
            "products",
            {"name": "To Delete", "sku_code": "DEL-001", "is_active": True},
        )

        result = await write_tool.ainvoke({
            "goal": "Soft delete product",
            "reasoning": "Product discontinued",
            "operations": [
                {
                    "action": "delete",
                    "table": "products",
                    "filters": {"sku_code": "DEL-001"},
                    "soft_delete": True,
                }
            ],
            "impact": {"deletes": {"products": 1}},
        })

        assert result["success"] is True
        assert result["summary"]["total_deleted"] == 1

        # Verify soft delete (is_active=False)
        products = await storage.query_entities(
            "products", {"sku_code": "DEL-001", "is_active": False}
        )
        assert len(products) == 1
        assert products[0]["is_active"] is False

    async def test_dry_run_mode(self, write_tool, storage):
        """Test dry run does not modify data."""
        result = await write_tool.ainvoke({
            "goal": "Create product (dry run)",
            "reasoning": "Testing dry run",
            "operations": [
                {
                    "action": "create",
                    "table": "products",
                    "data": {"name": "Dry Run Product", "sku_code": "DRY-001"},
                }
            ],
            "impact": {"creates": {"products": 1}},
            "dry_run": True,
        })

        assert result["success"] is True

        # Verify no data was created
        products = await storage.query_entities("products", {"sku_code": "DRY-001"})
        assert len(products) == 0


# =============================================================================
# Asset Upload E2E Tests
# =============================================================================


@pytest.mark.asyncio
class TestWriteDataAssetUploadsE2E:
    """E2E tests for write operations with asset uploads."""

    async def test_create_product_with_image(
        self, write_tool, storage, temp_image_file
    ):
        """Test creating product with uploaded image."""
        result = await write_tool.ainvoke({
            "goal": "Create product with image",
            "reasoning": "New product with product photo",
            "asset_uploads": [
                {
                    "temp_path": temp_image_file,
                    "returns": "product_image",
                    "bucket": "assets",
                    "folder": "products",
                }
            ],
            "operations": [
                {
                    "action": "create",
                    "table": "products",
                    "data": {
                        "name": "Product with Image",
                        "sku_code": "IMG-001",
                        "image_url": "@product_image.public_url",
                    },
                    "returns": "product",
                }
            ],
            "impact": {"creates": {"products": 1}, "asset_uploads": 1},
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 1
        assert result["summary"]["assets_uploaded"] == 1

        # Verify product has image URL
        products = await storage.query_entities("products", {"sku_code": "IMG-001"})
        assert len(products) == 1
        assert products[0]["image_url"].startswith("https://")
        assert "products/" in products[0]["image_url"]

    async def test_create_with_multiple_images(
        self, write_tool, storage, temp_image_file, temp_jpeg_file
    ):
        """Test creating entity with multiple uploaded images."""
        result = await write_tool.ainvoke({
            "goal": "Create product with main and thumbnail images",
            "reasoning": "Product with multiple image variants",
            "asset_uploads": [
                {
                    "temp_path": temp_image_file,
                    "returns": "main_image",
                    "folder": "products",
                },
                {
                    "temp_path": temp_jpeg_file,
                    "returns": "thumbnail",
                    "folder": "thumbnails",
                },
            ],
            "operations": [
                {
                    "action": "create",
                    "table": "products",
                    "data": {
                        "name": "Multi-Image Product",
                        "sku_code": "MULTI-IMG-001",
                        "main_image_url": "@main_image.public_url",
                        "thumbnail_url": "@thumbnail.public_url",
                    },
                    "returns": "product",
                }
            ],
            "impact": {"creates": {"products": 1}, "asset_uploads": 2},
        })

        assert result["success"] is True
        assert result["summary"]["assets_uploaded"] == 2

        # Verify both URLs are different and in correct folders
        products = await storage.query_entities(
            "products", {"sku_code": "MULTI-IMG-001"}
        )
        assert "products/" in products[0]["main_image_url"]
        assert "thumbnails/" in products[0]["thumbnail_url"]
        assert products[0]["main_image_url"] != products[0]["thumbnail_url"]

    async def test_asset_metadata_reference(
        self, write_tool, storage, temp_image_file
    ):
        """Test referencing asset metadata (size, content_type)."""
        result = await write_tool.ainvoke({
            "goal": "Create asset record with full metadata",
            "reasoning": "Store image with metadata",
            "asset_uploads": [
                {
                    "temp_path": temp_image_file,
                    "returns": "uploaded_file",
                }
            ],
            "operations": [
                {
                    "action": "create",
                    "table": "product_images",
                    "data": {
                        "url": "@uploaded_file.public_url",
                        "storage_path": "@uploaded_file.storage_path",
                        "size_bytes": "@uploaded_file.size_bytes",
                        "content_type": "@uploaded_file.content_type",
                    },
                    "returns": "image_record",
                }
            ],
            "impact": {"creates": {"product_images": 1}, "asset_uploads": 1},
        })

        assert result["success"] is True

        # Verify all metadata was resolved
        images = await storage.query_entities("product_images", {})
        assert len(images) == 1
        assert images[0]["url"].startswith("https://")
        assert images[0]["storage_path"].startswith("products/")
        assert images[0]["size_bytes"] > 0
        assert images[0]["content_type"] == "image/png"

    async def test_asset_with_dependent_operations(
        self, write_tool, storage, temp_image_file
    ):
        """Test asset upload with chained dependent operations."""
        result = await write_tool.ainvoke({
            "goal": "Create product family with image and variant",
            "reasoning": "Full product setup with image",
            "asset_uploads": [
                {
                    "temp_path": temp_image_file,
                    "returns": "family_image",
                    "folder": "families",
                }
            ],
            "operations": [
                {
                    "action": "create",
                    "table": "product_families",
                    "data": {
                        "name": "Imaged Family",
                        "slug": "imaged-family",
                        "image_url": "@family_image.public_url",
                    },
                    "returns": "family",
                },
                {
                    "action": "create",
                    "table": "variant_axes",
                    "data": {
                        "name": "Color",
                        "product_family_id": "@family.id",
                    },
                    "dependencies": ["family"],
                    "returns": "color_axis",
                },
            ],
            "impact": {
                "creates": {"product_families": 1, "variant_axes": 1},
                "asset_uploads": 1,
            },
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 2
        assert result["summary"]["assets_uploaded"] == 1

        # Verify chain: asset -> family -> axis
        families = await storage.query_entities("product_families", {})
        axes = await storage.query_entities("variant_axes", {})

        assert families[0]["image_url"].startswith("https://")
        assert axes[0]["product_family_id"] == families[0]["id"]


# =============================================================================
# Error Handling E2E Tests
# =============================================================================


@pytest.mark.asyncio
class TestWriteDataErrorHandlingE2E:
    """E2E tests for error handling scenarios."""

    async def test_missing_asset_file_fails(self, write_tool, storage):
        """Test that missing asset file causes failure."""
        result = await write_tool.ainvoke({
            "goal": "Create with missing file",
            "reasoning": "Testing error handling",
            "asset_uploads": [
                {
                    "temp_path": "/nonexistent/path/image.png",
                    "returns": "missing_image",
                }
            ],
            "operations": [
                {
                    "action": "create",
                    "table": "products",
                    "data": {"name": "Test", "sku_code": "ERR-001"},
                }
            ],
            "impact": {"creates": {"products": 1}, "asset_uploads": 1},
        })

        assert result["success"] is False

        # Verify no data was created (rolled back)
        products = await storage.query_entities("products", {"sku_code": "ERR-001"})
        assert len(products) == 0

    async def test_validation_error_fails(self, write_tool, storage):
        """Test validation errors are caught."""
        result = await write_tool.ainvoke({
            "goal": "Create with missing required data",
            "reasoning": "Testing validation",
            "operations": [
                {
                    "action": "create",
                    "table": "products",
                    "data": None,  # Missing required data for create
                }
            ],
            "impact": {"creates": {"products": 1}},
        })

        assert result["success"] is False

    async def test_circular_dependency_fails(self, write_tool, storage):
        """Test circular dependencies are detected."""
        result = await write_tool.ainvoke({
            "goal": "Create with circular deps",
            "reasoning": "Testing circular detection",
            "operations": [
                {
                    "action": "create",
                    "table": "products",
                    "data": {"name": "A", "ref": "@op_b.id"},
                    "dependencies": ["op_b"],
                    "returns": "op_a",
                },
                {
                    "action": "create",
                    "table": "products",
                    "data": {"name": "B", "ref": "@op_a.id"},
                    "dependencies": ["op_a"],
                    "returns": "op_b",
                },
            ],
            "impact": {"creates": {"products": 2}},
        })

        assert result["success"] is False


# =============================================================================
# Complex Workflow E2E Tests
# =============================================================================


@pytest.mark.asyncio
class TestComplexWorkflowE2E:
    """E2E tests for complex multi-operation workflows."""

    async def test_full_product_catalog_creation(
        self, write_tool, storage, temp_image_file
    ):
        """Test creating full product catalog entry with all related entities."""
        result = await write_tool.ainvoke({
            "goal": "Create complete product catalog entry",
            "reasoning": "Full product setup: family -> axes -> values -> product -> image",
            "asset_uploads": [
                {
                    "temp_path": temp_image_file,
                    "returns": "product_photo",
                    "folder": "products",
                }
            ],
            "operations": [
                # 1. Create product family
                {
                    "action": "create",
                    "table": "product_families",
                    "data": {
                        "name": "Premium Bottles",
                        "slug": "premium-bottles",
                        "description": "High-end bottle collection",
                    },
                    "returns": "family",
                },
                # 2. Create Size variant axis
                {
                    "action": "create",
                    "table": "variant_axes",
                    "data": {
                        "name": "Size",
                        "product_family_id": "@family.id",
                        "display_order": 1,
                    },
                    "dependencies": ["family"],
                    "returns": "size_axis",
                },
                # 3. Create Color variant axis
                {
                    "action": "create",
                    "table": "variant_axes",
                    "data": {
                        "name": "Color",
                        "product_family_id": "@family.id",
                        "display_order": 2,
                    },
                    "dependencies": ["family"],
                    "returns": "color_axis",
                },
                # 4. Create size values
                {
                    "action": "create",
                    "table": "variant_values",
                    "data": [
                        {"variant_axis_id": "@size_axis.id", "value": "500ml"},
                        {"variant_axis_id": "@size_axis.id", "value": "1L"},
                    ],
                    "dependencies": ["size_axis"],
                },
                # 5. Create color values
                {
                    "action": "create",
                    "table": "variant_values",
                    "data": [
                        {"variant_axis_id": "@color_axis.id", "value": "Clear"},
                        {"variant_axis_id": "@color_axis.id", "value": "Blue"},
                    ],
                    "dependencies": ["color_axis"],
                },
                # 6. Create product with image
                {
                    "action": "create",
                    "table": "products",
                    "data": {
                        "name": "Premium Bottle 500ml Clear",
                        "sku_code": "PB-500-CLR",
                        "product_family_id": "@family.id",
                        "image_url": "@product_photo.public_url",
                        "price": 29.99,
                    },
                    "dependencies": ["family"],
                    "returns": "product",
                },
            ],
            "impact": {
                "creates": {
                    "product_families": 1,
                    "variant_axes": 2,
                    "variant_values": 4,
                    "products": 1,
                },
                "asset_uploads": 1,
            },
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 8  # 1+2+4+1
        assert result["summary"]["assets_uploaded"] == 1

        # Verify all entities created correctly
        families = await storage.query_entities("product_families", {})
        assert len(families) == 1
        assert families[0]["name"] == "Premium Bottles"

        axes = await storage.query_entities("variant_axes", {})
        assert len(axes) == 2

        values = await storage.query_entities("variant_values", {})
        assert len(values) == 4

        products = await storage.query_entities("products", {})
        assert len(products) == 1
        assert products[0]["image_url"].startswith("https://")
        assert products[0]["product_family_id"] == families[0]["id"]

    async def test_bulk_product_creation(self, write_tool, storage):
        """Test bulk creating multiple products."""
        result = await write_tool.ainvoke({
            "goal": "Bulk create product variants",
            "reasoning": "Creating multiple SKU variants at once",
            "operations": [
                {
                    "action": "create",
                    "table": "products",
                    "data": [
                        {"name": "Variant A", "sku_code": "BULK-A", "price": 10.00},
                        {"name": "Variant B", "sku_code": "BULK-B", "price": 12.00},
                        {"name": "Variant C", "sku_code": "BULK-C", "price": 14.00},
                        {"name": "Variant D", "sku_code": "BULK-D", "price": 16.00},
                        {"name": "Variant E", "sku_code": "BULK-E", "price": 18.00},
                    ],
                }
            ],
            "impact": {"creates": {"products": 5}},
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 5

        # Verify all products created
        products = await storage.query_entities("products", {})
        assert len(products) == 5
        skus = {p["sku_code"] for p in products}
        assert skus == {"BULK-A", "BULK-B", "BULK-C", "BULK-D", "BULK-E"}

    async def test_mixed_operations_workflow(self, write_tool, storage):
        """Test workflow with create, update, and delete operations."""
        # Pre-create some data
        await storage.insert_entity(
            "products",
            {
                "name": "Old Product",
                "sku_code": "MIX-OLD",
                "price": 5.00,
                "is_active": True,
            },
        )
        await storage.insert_entity(
            "products",
            {"name": "To Delete", "sku_code": "MIX-DEL", "is_active": True},
        )

        result = await write_tool.ainvoke({
            "goal": "Mixed operations: create, update, delete",
            "reasoning": "Comprehensive catalog update",
            "operations": [
                # Create new product
                {
                    "action": "create",
                    "table": "products",
                    "data": {
                        "name": "New Product",
                        "sku_code": "MIX-NEW",
                        "price": 20.00,
                    },
                },
                # Update existing product
                {
                    "action": "update",
                    "table": "products",
                    "filters": {"sku_code": "MIX-OLD"},
                    "updates": {"price": 7.50, "name": "Updated Product"},
                },
                # Delete product
                {
                    "action": "delete",
                    "table": "products",
                    "filters": {"sku_code": "MIX-DEL"},
                    "soft_delete": True,
                },
            ],
            "impact": {
                "creates": {"products": 1},
                "updates": {"products": 1},
                "deletes": {"products": 1},
            },
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 1
        assert result["summary"]["total_updated"] == 1
        assert result["summary"]["total_deleted"] == 1

        # Verify results
        new_product = await storage.query_entities(
            "products", {"sku_code": "MIX-NEW"}
        )
        assert len(new_product) == 1

        updated = await storage.query_entities("products", {"sku_code": "MIX-OLD"})
        assert updated[0]["price"] == 7.50

        deleted = await storage.query_entities(
            "products", {"sku_code": "MIX-DEL", "is_active": False}
        )
        assert len(deleted) == 1
