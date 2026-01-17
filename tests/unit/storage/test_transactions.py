"""Unit tests for transaction support in storage adapters.

Tests both FakeStorage and SupabaseStorageClient transaction implementations.
"""

import pytest

from tests.fixtures.fake_storage import FakeStorage


@pytest.mark.asyncio
class TestFakeStorageTransactions:
    """Test transaction support in FakeStorage."""

    @pytest.fixture
    def storage(self):
        """Create fresh FakeStorage instance."""
        return FakeStorage()

    async def test_transaction_commit_on_success(self, storage):
        """Successful operations should commit changes."""
        async with storage.transaction():
            family = await storage.insert_entity(
                "product_families", {"name": "Test Family", "company_id": "test-company"}
            )
            assert family["id"] is not None

        # Verify changes persisted
        families = await storage.query_entities("product_families", {})
        assert len(families) == 1
        assert families[0]["name"] == "Test Family"

    async def test_transaction_rollback_on_exception(self, storage):
        """Exception should rollback all operations."""
        with pytest.raises(ValueError):
            async with storage.transaction():
                await storage.insert_entity(
                    "product_families", {"name": "Family 1", "company_id": "test-company"}
                )
                await storage.insert_entity(
                    "product_families", {"name": "Family 2", "company_id": "test-company"}
                )
                raise ValueError("Intentional failure")

        # Verify nothing persisted
        families = await storage.query_entities("product_families", {})
        assert len(families) == 0

    async def test_transaction_rollback_partial_operations(self, storage):
        """Rollback should revert all operations, not just failed one."""
        # Pre-populate data
        existing = await storage.insert_entity(
            "product_families", {"name": "Existing Family", "company_id": "test-company"}
        )

        with pytest.raises(ValueError):
            async with storage.transaction():
                # Insert 2 new families
                await storage.insert_entity(
                    "product_families", {"name": "New Family 1", "company_id": "test-company"}
                )
                await storage.insert_entity(
                    "product_families", {"name": "New Family 2", "company_id": "test-company"}
                )
                raise ValueError("Fail after inserts")

        # Verify only existing data remains
        families = await storage.query_entities("product_families", {})
        assert len(families) == 1
        assert families[0]["id"] == existing["id"]

    async def test_transaction_with_batch_insert(self, storage):
        """Transaction should handle batch inserts."""
        async with storage.transaction():
            families = await storage.insert_entities(
                "product_families",
                [
                    {"name": "Family 1", "company_id": "test-company"},
                    {"name": "Family 2", "company_id": "test-company"},
                    {"name": "Family 3", "company_id": "test-company"},
                ],
            )
            assert len(families) == 3

        # Verify all persisted
        families = await storage.query_entities("product_families", {})
        assert len(families) == 3

    async def test_transaction_with_update(self, storage):
        """Transaction should handle updates."""
        family = await storage.insert_entity(
            "product_families", {"name": "Original", "company_id": "test-company"}
        )

        async with storage.transaction():
            count = await storage.update_entities(
                "product_families", {"id": family["id"]}, {"name": "Updated"}
            )
            assert count == 1

        # Verify update persisted
        families = await storage.query_entities("product_families", {"id": family["id"]})
        assert families[0]["name"] == "Updated"

    async def test_transaction_with_delete(self, storage):
        """Transaction should handle deletes."""
        family = await storage.insert_entity(
            "product_families", {"name": "To Delete", "company_id": "test-company"}
        )

        async with storage.transaction():
            count = await storage.delete_entities("product_families", {"id": family["id"]})
            assert count == 1

        # Verify delete persisted
        families = await storage.query_entities("product_families", {})
        assert len(families) == 0

    async def test_transaction_rollback_with_delete(self, storage):
        """Rollback should restore deleted entities."""
        family = await storage.insert_entity(
            "product_families", {"name": "To Delete", "company_id": "test-company"}
        )

        with pytest.raises(ValueError):
            async with storage.transaction():
                await storage.delete_entities("product_families", {"id": family["id"]})
                raise ValueError("Fail after delete")

        # Verify entity restored
        families = await storage.query_entities("product_families", {})
        assert len(families) == 1
        assert families[0]["id"] == family["id"]

    async def test_transaction_mixed_operations(self, storage):
        """Transaction should handle mixed insert/update/delete."""
        family1 = await storage.insert_entity(
            "product_families", {"name": "Family 1", "company_id": "test-company"}
        )

        async with storage.transaction():
            # Insert new
            family2 = await storage.insert_entity(
                "product_families", {"name": "Family 2", "company_id": "test-company"}
            )

            # Update existing
            await storage.update_entities(
                "product_families", {"id": family1["id"]}, {"name": "Updated Family 1"}
            )

            # Delete one
            await storage.delete_entities("product_families", {"id": family2["id"]})

        # Verify final state
        families = await storage.query_entities("product_families", {})
        assert len(families) == 1
        assert families[0]["name"] == "Updated Family 1"

    async def test_nested_transactions_not_supported(self, storage):
        """Nested transactions should work but share same snapshot."""
        async with storage.transaction():
            await storage.insert_entity(
                "product_families", {"name": "Family 1", "company_id": "test-company"}
            )

            # Inner transaction (shares outer snapshot)
            async with storage.transaction():
                await storage.insert_entity(
                    "product_families", {"name": "Family 2", "company_id": "test-company"}
                )

        # Both should persist
        families = await storage.query_entities("product_families", {})
        assert len(families) == 2


@pytest.mark.asyncio
class TestSupabaseTransactionOperationTracking:
    """Test operation tracking in SupabaseTransaction (unit tests without Supabase)."""

    async def test_insert_tracks_operation(self):
        """Insert should track operation for rollback."""
        from autifyme_agents.integrations.storage.supabase_client import (
            SupabaseStorageClient,
        )

        storage = SupabaseStorageClient()
        storage._current_transaction = type("MockTx", (), {"operations": []})()

        # Mock the async client and response
        class MockResponse:
            data = [{"id": "test-id", "name": "Test"}]

        class MockTable:
            def insert(self, data):
                return self

            async def execute(self):
                return MockResponse()

        class MockClient:
            def table(self, name):
                return MockTable()

        async def mock_ensure_client():
            return MockClient()

        storage._ensure_async_client = mock_ensure_client

        # Execute insert
        await storage.insert_entity("test_table", {"name": "Test"})

        # Verify operation tracked
        assert len(storage._current_transaction.operations) == 1
        op = storage._current_transaction.operations[0]
        assert op["type"] == "insert"
        assert op["table"] == "test_table"
        assert op["ids"] == ["test-id"]

    async def test_batch_insert_tracks_all_ids(self):
        """Batch insert should track all entity IDs."""
        from autifyme_agents.integrations.storage.supabase_client import (
            SupabaseStorageClient,
        )

        storage = SupabaseStorageClient()
        storage._current_transaction = type("MockTx", (), {"operations": []})()

        # Mock batch insert response
        class MockResponse:
            data = [
                {"id": "id-1", "name": "Test 1"},
                {"id": "id-2", "name": "Test 2"},
                {"id": "id-3", "name": "Test 3"},
            ]

        class MockTable:
            def insert(self, data):
                return self

            async def execute(self):
                return MockResponse()

        class MockClient:
            def table(self, name):
                return MockTable()

        async def mock_ensure_client():
            return MockClient()

        storage._ensure_async_client = mock_ensure_client

        # Execute batch insert
        await storage.insert_entities(
            "test_table", [{"name": "Test 1"}, {"name": "Test 2"}, {"name": "Test 3"}]
        )

        # Verify operation tracked
        assert len(storage._current_transaction.operations) == 1
        op = storage._current_transaction.operations[0]
        assert op["type"] == "insert"
        assert op["ids"] == ["id-1", "id-2", "id-3"]

    async def test_update_tracks_operation(self):
        """Update should track operation (limited rollback)."""
        from autifyme_agents.integrations.storage.supabase_client import (
            SupabaseStorageClient,
        )

        storage = SupabaseStorageClient()
        storage._current_transaction = type("MockTx", (), {"operations": []})()

        # Mock update response
        class MockResponse:
            data = [{"id": "id-1"}, {"id": "id-2"}]

        class MockQuery:
            def __init__(self):
                pass

            def eq(self, key, value):
                return self

            async def execute(self):
                return MockResponse()

        class MockTable:
            def update(self, data):
                return MockQuery()

        class MockClient:
            def table(self, name):
                return MockTable()

        async def mock_ensure_client():
            return MockClient()

        storage._ensure_async_client = mock_ensure_client

        # Execute update
        await storage.update_entities("test_table", {"status": "active"}, {"is_published": True})

        # Verify operation tracked
        assert len(storage._current_transaction.operations) == 1
        op = storage._current_transaction.operations[0]
        assert op["type"] == "update"
        assert op["table"] == "test_table"
        assert op["count"] == 2

    async def test_delete_with_in_operator(self):
        """Delete should support 'in' operator for batch rollback."""
        from autifyme_agents.integrations.storage.supabase_client import (
            SupabaseStorageClient,
        )

        storage = SupabaseStorageClient()

        # Mock delete with in_ operator
        class MockResponse:
            data = [{"id": "id-1"}, {"id": "id-2"}]

        class MockQuery:
            def __init__(self):
                self.in_called = False

            def in_(self, column, values):
                self.in_called = True
                assert column == "id"
                assert values == ["id-1", "id-2"]
                return self

            async def execute(self):
                return MockResponse()

        class MockTable:
            def delete(self):
                return MockQuery()

            def update(self, updates):
                # Soft delete calls update() internally
                return MockQuery()

        class MockClient:
            def table(self, name):
                return MockTable()

        async def mock_ensure_client():
            return MockClient()

        storage._ensure_async_client = mock_ensure_client

        # Execute delete with in operator
        count = await storage.delete_entities("test_table", {"id": {"in": ["id-1", "id-2"]}})

        assert count == 2


@pytest.mark.asyncio
class TestComplexTransactionScenarios:
    """Test complex, production-realistic transaction scenarios."""

    @pytest.fixture
    def storage(self):
        """Create fresh FakeStorage instance."""
        return FakeStorage()

    async def test_foreign_key_dependencies_in_transaction(self, storage):
        """Transaction with foreign key dependencies should maintain integrity."""
        async with storage.transaction():
            # Create parent
            family = await storage.insert_entity(
                "product_families", {"name": "Electronics", "company_id": "test-company"}
            )

            # Create children referencing parent
            axes = await storage.insert_entities(
                "variant_axes",
                [
                    {"name": "Color", "product_family_id": family["id"]},
                    {"name": "Size", "product_family_id": family["id"]},
                ],
            )

            # Create grandchildren referencing children
            values = await storage.insert_entities(
                "axis_values",
                [
                    {"value": "Red", "variant_axis_id": axes[0]["id"]},
                    {"value": "Blue", "variant_axis_id": axes[0]["id"]},
                    {"value": "Small", "variant_axis_id": axes[1]["id"]},
                    {"value": "Large", "variant_axis_id": axes[1]["id"]},
                ],
            )

        # Verify entire hierarchy persisted
        families = await storage.query_entities("product_families", {})
        axes = await storage.query_entities("variant_axes", {})
        values = await storage.query_entities("axis_values", {})

        assert len(families) == 1
        assert len(axes) == 2
        assert len(values) == 4
        assert all(v["variant_axis_id"] in [a["id"] for a in axes] for v in values)

    async def test_foreign_key_rollback_maintains_integrity(self, storage):
        """Rollback should not leave orphaned foreign key references."""
        with pytest.raises(ValueError):
            async with storage.transaction():
                family = await storage.insert_entity(
                    "product_families", {"name": "Electronics", "company_id": "test-company"}
                )

                axes = await storage.insert_entities(
                    "variant_axes",
                    [
                        {"name": "Color", "product_family_id": family["id"]},
                        {"name": "Size", "product_family_id": family["id"]},
                    ],
                )

                values = await storage.insert_entities(
                    "axis_values",
                    [
                        {"value": "Red", "variant_axis_id": axes[0]["id"]},
                        {"value": "Blue", "variant_axis_id": axes[0]["id"]},
                    ],
                )

                raise ValueError("Rollback entire hierarchy")

        # Verify nothing persisted - no orphans
        families = await storage.query_entities("product_families", {})
        axes = await storage.query_entities("variant_axes", {})
        values = await storage.query_entities("axis_values", {})

        assert len(families) == 0
        assert len(axes) == 0
        assert len(values) == 0

    async def test_production_workflow_create_product_family(self, storage):
        """Real production workflow: Create family → axes → values → products atomically."""
        async with storage.transaction():
            # 1. Create product family
            family = await storage.insert_entity(
                "product_families",
                {
                    "name": "T-Shirts",
                    "company_id": "test-company",
                    "description": "Cotton t-shirts",
                },
            )

            # 2. Create variant axes
            axes = await storage.insert_entities(
                "variant_axes",
                [
                    {"name": "Color", "product_family_id": family["id"]},
                    {"name": "Size", "product_family_id": family["id"]},
                ],
            )

            # 3. Create axis values
            await storage.insert_entities(
                "axis_values",
                [
                    {"value": "Red", "variant_axis_id": axes[0]["id"]},
                    {"value": "Blue", "variant_axis_id": axes[0]["id"]},
                    {"value": "Green", "variant_axis_id": axes[0]["id"]},
                ],
            )

            await storage.insert_entities(
                "axis_values",
                [
                    {"value": "S", "variant_axis_id": axes[1]["id"]},
                    {"value": "M", "variant_axis_id": axes[1]["id"]},
                    {"value": "L", "variant_axis_id": axes[1]["id"]},
                ],
            )

            # 4. Create products (would normally be variants, simplified here)
            await storage.insert_entities(
                "products",
                [
                    {
                        "sku": "TSHIRT-RED-S",
                        "name": "Red T-Shirt Small",
                        "product_family_id": family["id"],
                        "company_id": "test-company",
                    },
                    {
                        "sku": "TSHIRT-BLUE-M",
                        "name": "Blue T-Shirt Medium",
                        "product_family_id": family["id"],
                        "company_id": "test-company",
                    },
                ],
            )

        # Verify entire product catalog created atomically
        assert len(await storage.query_entities("product_families", {})) == 1
        assert len(await storage.query_entities("variant_axes", {})) == 2
        assert len(await storage.query_entities("axis_values", {})) == 6
        assert len(await storage.query_entities("products", {})) == 2

    async def test_large_scale_transaction_performance(self, storage):
        """Transaction should handle large number of operations efficiently."""
        async with storage.transaction():
            # Insert 100 families
            families = await storage.insert_entities(
                "product_families",
                [{"name": f"Family {i}", "company_id": "test-company"} for i in range(100)],
            )

            # Insert 500 axes (5 per family)
            all_axes = []
            for family in families:
                axes = await storage.insert_entities(
                    "variant_axes",
                    [{"name": f"Axis {j}", "product_family_id": family["id"]} for j in range(5)],
                )
                all_axes.extend(axes)

        # Verify all persisted
        assert len(await storage.query_entities("product_families", {})) == 100
        assert len(await storage.query_entities("variant_axes", {})) == 500

    async def test_large_scale_rollback_performance(self, storage):
        """Rollback should handle large number of operations efficiently."""
        with pytest.raises(ValueError):
            async with storage.transaction():
                # Insert 50 families
                families = await storage.insert_entities(
                    "product_families",
                    [{"name": f"Family {i}", "company_id": "test-company"} for i in range(50)],
                )

                # Insert 250 axes
                for family in families:
                    await storage.insert_entities(
                        "variant_axes",
                        [
                            {"name": f"Axis {j}", "product_family_id": family["id"]}
                            for j in range(5)
                        ],
                    )

                raise ValueError("Rollback 300 operations")

        # Verify complete rollback
        assert len(await storage.query_entities("product_families", {})) == 0
        assert len(await storage.query_entities("variant_axes", {})) == 0

    async def test_transaction_with_validation_failure(self, storage):
        """Validation failure mid-transaction should rollback all operations."""
        from autifyme_agents.schemas.registry import SchemaRegistry

        schema = SchemaRegistry.get_version("v1", domain="product_catalog")

        # Pre-populate duplicate SKU
        await storage.insert_entity(
            "products",
            {
                "sku": "EXISTING-SKU",
                "name": "Existing Product",
                "company_id": "test-company",
            },
        )

        # Attempt transaction with validation failure
        with pytest.raises(ValueError):
            async with storage.transaction():
                # Insert family
                await storage.insert_entity(
                    "product_families", {"name": "Test Family", "company_id": "test-company"}
                )

                # Attempt to insert product with duplicate SKU (should fail validation)
                products_table = schema.get_table("products")
                validation = await products_table.validate_before_insert(
                    [{"sku": "EXISTING-SKU", "company_id": "test-company"}], storage
                )

                if not validation.valid:
                    raise ValueError(f"Validation failed: {validation.errors}")

        # Verify rollback - family not persisted due to validation failure
        families = await storage.query_entities("product_families", {})
        # Only the pre-existing product remains
        products = await storage.query_entities("products", {})
        assert len(families) == 0
        assert len(products) == 1
        assert products[0]["sku"] == "EXISTING-SKU"

    async def test_empty_transaction(self, storage):
        """Empty transaction should succeed without side effects."""
        async with storage.transaction():
            pass  # No operations

        # Should complete successfully
        assert True

    async def test_single_operation_transaction(self, storage):
        """Transaction with single operation should work correctly."""
        async with storage.transaction():
            await storage.insert_entity(
                "product_families", {"name": "Single", "company_id": "test-company"}
            )

        families = await storage.query_entities("product_families", {})
        assert len(families) == 1

    async def test_transaction_rollback_preserves_existing_data(self, storage):
        """Rollback should not affect data created before transaction."""
        # Create data before transaction
        existing_family = await storage.insert_entity(
            "product_families", {"name": "Existing", "company_id": "test-company"}
        )

        # Transaction that fails
        with pytest.raises(ValueError):
            async with storage.transaction():
                await storage.insert_entity(
                    "product_families", {"name": "New", "company_id": "test-company"}
                )
                raise ValueError("Rollback")

        # Verify existing data preserved, new data rolled back
        families = await storage.query_entities("product_families", {})
        assert len(families) == 1
        assert families[0]["id"] == existing_family["id"]
        assert families[0]["name"] == "Existing"

    async def test_sequential_transactions_isolated(self, storage):
        """Sequential transactions should be properly isolated."""
        # Transaction 1
        async with storage.transaction():
            await storage.insert_entity(
                "product_families", {"name": "Family 1", "company_id": "test-company"}
            )

        # Transaction 2 (independent)
        async with storage.transaction():
            await storage.insert_entity(
                "product_families", {"name": "Family 2", "company_id": "test-company"}
            )

        # Both should succeed independently
        families = await storage.query_entities("product_families", {})
        assert len(families) == 2

    async def test_transaction_with_update_then_delete(self, storage):
        """Transaction with update followed by delete should work correctly."""
        family = await storage.insert_entity(
            "product_families", {"name": "To Delete", "company_id": "test-company"}
        )

        async with storage.transaction():
            # Update
            await storage.update_entities(
                "product_families", {"id": family["id"]}, {"name": "Updated"}
            )

            # Then delete
            await storage.delete_entities("product_families", {"id": family["id"]})

        # Should be deleted
        families = await storage.query_entities("product_families", {})
        assert len(families) == 0

    async def test_transaction_rollback_with_update_then_delete(self, storage):
        """Rollback should restore entity that was updated then deleted."""
        family = await storage.insert_entity(
            "product_families", {"name": "Original", "company_id": "test-company"}
        )

        with pytest.raises(ValueError):
            async with storage.transaction():
                # Update
                await storage.update_entities(
                    "product_families", {"id": family["id"]}, {"name": "Updated"}
                )

                # Delete
                await storage.delete_entities("product_families", {"id": family["id"]})

                raise ValueError("Rollback")

        # Should be restored to original state
        families = await storage.query_entities("product_families", {})
        assert len(families) == 1
        assert families[0]["name"] == "Original"

    async def test_cascade_delete_within_transaction(self, storage):
        """Transaction should handle cascade delete operations correctly."""
        async with storage.transaction():
            # Create hierarchy
            family = await storage.insert_entity(
                "product_families", {"name": "Electronics", "company_id": "test-company"}
            )

            axes = await storage.insert_entities(
                "variant_axes",
                [
                    {"name": "Color", "product_family_id": family["id"]},
                    {"name": "Size", "product_family_id": family["id"]},
                ],
            )

            values = await storage.insert_entities(
                "axis_values",
                [
                    {"value": "Red", "variant_axis_id": axes[0]["id"]},
                    {"value": "Blue", "variant_axis_id": axes[0]["id"]},
                ],
            )

            # Delete parent (simulating cascade - manual for FakeStorage)
            await storage.delete_entities("axis_values", {"variant_axis_id": axes[0]["id"]})
            await storage.delete_entities("variant_axes", {"id": axes[0]["id"]})

        # Verify cascade completed correctly
        axes = await storage.query_entities("variant_axes", {})
        values = await storage.query_entities("axis_values", {})
        assert len(axes) == 1  # Only Color axis deleted
        assert len(values) == 0  # Both color values deleted

    async def test_multiple_updates_same_entity(self, storage):
        """Transaction with multiple updates to same entity should apply all."""
        family = await storage.insert_entity(
            "product_families", {"name": "Original", "company_id": "test-company"}
        )

        async with storage.transaction():
            # Update 1
            await storage.update_entities(
                "product_families", {"id": family["id"]}, {"name": "Update 1"}
            )

            # Update 2
            await storage.update_entities(
                "product_families", {"id": family["id"]}, {"name": "Update 2"}
            )

            # Update 3
            await storage.update_entities(
                "product_families", {"id": family["id"]}, {"name": "Final"}
            )

        # Should have final update
        families = await storage.query_entities("product_families", {"id": family["id"]})
        assert families[0]["name"] == "Final"
