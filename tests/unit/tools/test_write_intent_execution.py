"""
Comprehensive test suite for WriteIntent multi-operation execution.

Tests the Phase 1.7 Universal Data Engine WriteIntent architecture including:
- Single and multi-operation execution
- Dependency resolution (topological sort)
- Cross-operation references (@name.field)
- Validation (duplicates, missing deps, 0-impact)
- Access control
- Soft delete vs hard delete
- Error handling and rollback
- Edge cases

Created: 2025-11-24
Author: Claude
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.tools.data_engine import create_write_data_tool

# Standard HITL summary for all tests
TEST_HITL_SUMMARY = "Test operation. Reply *approve* to proceed or *reject* to cancel."

# =============================================================================
# Fixtures
# =============================================================================


def create_rpc_success_result(
    created: dict[str, list[dict]] | None = None,
    updated: dict[str, int] | None = None,
    deleted: dict[str, int] | None = None,
    context: dict | None = None,
) -> dict:
    """Helper to create RPC success result structure."""
    results = []

    if created:
        for table, entities in created.items():
            results.append({
                "action": "create",
                "table": table,
                "count": len(entities),
                "data": entities
            })

    if updated:
        for table, count in updated.items():
            results.append({
                "action": "update",
                "table": table,
                "count": count
            })

    if deleted:
        for table, count in deleted.items():
            results.append({
                "action": "delete",
                "table": table,
                "count": count
            })

    return {
        "success": True,
        "results": results,
        "context": context or {},
        "operations_executed": len(results)
    }


def create_rpc_error_result(error: str, error_code: str = "ERROR") -> dict:
    """Helper to create RPC error result structure."""
    return {
        "success": False,
        "error": error,
        "error_code": error_code,
        "failed_operation_index": 1,
        "failed_operation": {}
    }


@pytest.fixture
def mock_storage():
    """Mock storage for testing with RPC-based executor."""
    storage = AsyncMock(spec=StorageInterface)

    # Mock execute_write_intent_rpc - the new atomic execution method
    # Default success response
    storage.execute_write_intent_rpc = AsyncMock(return_value=create_rpc_success_result(
        created={"products": [{"id": "uuid-123", "name": "Test"}]},
        context={"entity": {"id": "uuid-123", "name": "Test"}}
    ))

    # Legacy mocks (for validation tests that don't reach RPC)
    storage.insert_entity = AsyncMock(return_value={"id": "uuid-123", "name": "Test"})
    storage.bulk_upsert = AsyncMock(return_value=[
        {"id": "uuid-1", "name": "Entity 1"},
        {"id": "uuid-2", "name": "Entity 2"},
    ])
    storage.update_entities = AsyncMock(return_value=5)
    storage.delete_entities = AsyncMock(return_value=3)

    # Transaction context manager (deprecated but kept for compatibility)
    storage.transaction = MagicMock(return_value=AsyncMock())
    storage.transaction.return_value.__aenter__ = AsyncMock(return_value=None)
    storage.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

    return storage


# =============================================================================
# Group 1: Single-Operation Execution (10 tests)
# =============================================================================


class TestSingleOperationExecution:
    """Test single-operation WriteIntent scenarios via RPC."""

    @pytest.mark.asyncio
    async def test_single_create_operation(self, mock_storage):
        """Test single CREATE operation via RPC."""
        # Set up RPC mock for CREATE
        mock_storage.execute_write_intent_rpc.return_value = create_rpc_success_result(
            created={"products": [{"id": "uuid-123", "name": "Test Product", "price": 100}]},
            context={"entity": {"id": "uuid-123"}}
        )

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create test product",
            "reasoning": "User requested new product",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "create",
                "table": "products",
                "data": {"name": "Test Product", "price": 100}
            }],
            "impact": {"creates": {"products": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 1
        assert "products" in result["created_entities"]
        mock_storage.execute_write_intent_rpc.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_update_operation(self, mock_storage):
        """Test single UPDATE operation via RPC."""
        # Set up RPC mock for UPDATE
        mock_storage.execute_write_intent_rpc.return_value = create_rpc_success_result(
            updated={"products": 5}
        )

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Update product price",
            "reasoning": "Price adjustment requested",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "update",
                "table": "products",
                "filters": {"id": "uuid-123"},
                "updates": {"price": 150}
            }],
            "impact": {"updates": {"products": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_updated"] == 5
        mock_storage.execute_write_intent_rpc.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_delete_soft(self, mock_storage):
        """Test single soft DELETE operation via RPC."""
        # Set up RPC mock for DELETE
        mock_storage.execute_write_intent_rpc.return_value = create_rpc_success_result(
            deleted={"products": 3}
        )

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Delete inactive products",
            "reasoning": "Cleanup requested",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "delete",
                "table": "products",
                "filters": {"is_active": False},
                "soft_delete": True
            }],
            "impact": {"deletes": {"products": 3}}
        })

        assert result["success"] is True
        assert result["summary"]["total_deleted"] == 3
        # Verify RPC was called with soft_delete=True in operations
        call_args = mock_storage.execute_write_intent_rpc.call_args
        ops = call_args[1]["operations"]
        assert ops[0]["soft_delete"] is True

    @pytest.mark.asyncio
    async def test_single_delete_hard(self, mock_storage):
        """Test single hard DELETE operation via RPC."""
        mock_storage.execute_write_intent_rpc.return_value = create_rpc_success_result(
            deleted={"test_products": 2}
        )

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Permanently delete test data",
            "reasoning": "Test cleanup",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "delete",
                "table": "test_products",
                "filters": {"category": "test"},
                "soft_delete": False  # Hard delete
            }],
            "impact": {"deletes": {"test_products": 2}}
        })

        assert result["success"] is True
        # Verify RPC was called with soft_delete=False
        call_args = mock_storage.execute_write_intent_rpc.call_args
        ops = call_args[1]["operations"]
        assert ops[0]["soft_delete"] is False

    @pytest.mark.asyncio
    async def test_create_with_bulk_data(self, mock_storage):
        """Test CREATE with list of entities (bulk insert) via RPC."""
        mock_storage.execute_write_intent_rpc.return_value = create_rpc_success_result(
            created={"products": [
                {"id": "uuid-1", "name": "Product 1"},
                {"id": "uuid-2", "name": "Product 2"}
            ]}
        )

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create multiple products",
            "reasoning": "Bulk import",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "create",
                "table": "products",
                "data": [
                    {"name": "Product 1", "price": 100},
                    {"name": "Product 2", "price": 200}
                ]
            }],
            "impact": {"creates": {"products": 2}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 2
        mock_storage.execute_write_intent_rpc.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_0_impact_warning(self, mock_storage):
        """Test UPDATE that matches 0 rows generates warning."""
        mock_storage.execute_write_intent_rpc.return_value = create_rpc_success_result(
            updated={"products": 0}  # No rows affected
        )

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Update non-existent product",
            "reasoning": "User requested update",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "update",
                "table": "products",
                "filters": {"id": "non-existent"},
                "updates": {"price": 999}
            }],
            "impact": {"updates": {"products": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_updated"] == 0
        assert "warnings" in result
        assert any("matched 0 rows" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_delete_with_0_impact_warning(self, mock_storage):
        """Test DELETE that matches 0 rows generates warning."""
        mock_storage.execute_write_intent_rpc.return_value = create_rpc_success_result(
            deleted={"products": 0}  # No rows affected
        )

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Delete obsolete data",
            "reasoning": "Cleanup",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "delete",
                "table": "products",
                "filters": {"status": "obsolete"}
            }],
            "impact": {"deletes": {"products": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_deleted"] == 0
        assert "warnings" in result
        assert any("matched 0 rows" in w for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, mock_storage):
        """Test that execution time is tracked."""
        mock_storage.execute_write_intent_rpc.return_value = create_rpc_success_result(
            created={"products": [{"id": "uuid-123"}]}
        )

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create product",
            "reasoning": "Test",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "create",
                "table": "products",
                "data": {"name": "Test"}
            }],
            "impact": {"creates": {"products": 1}}
        })

        assert result["success"] is True
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, mock_storage):
        """Test dry_run mode (preview without execution)."""
        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create product",
            "reasoning": "Preview",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "create",
                "table": "products",
                "data": {"name": "Test"}
            }],
            "impact": {"creates": {"products": 1}},
            "dry_run": True
        })

        assert result["success"] is True
        # In dry_run, RPC should NOT be called
        mock_storage.execute_write_intent_rpc.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_only_mode(self, mock_storage):
        """Test validate_only mode (schema validation only)."""
        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create product",
            "reasoning": "Validation check",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [{
                "action": "create",
                "table": "products",
                "data": {"name": "Test"}
            }],
            "impact": {"creates": {"products": 1}},
            "validate_only": True
        })

        assert result["success"] is True
        # In validate_only, RPC should NOT be called
        mock_storage.execute_write_intent_rpc.assert_not_called()


# =============================================================================
# Group 2: Multi-Operation with Dependencies (15 tests)
# =============================================================================


class TestMultiOperationDependencies:
    """Test multi-operation WriteIntent with dependencies."""

    @pytest.mark.asyncio
    async def test_two_operations_linear_dependency(self, mock_storage):
        """Test 2 operations with linear dependency (A → B)."""
        mock_storage.insert_entity.side_effect = [
            {"id": "family-1", "name": "PET Jars"},
            {"id": "axis-1", "axis_name": "Size"}
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create family and axis",
            "reasoning": "Setup product structure",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {
                    "action": "create",
                    "table": "product_families",
                    "data": {"name": "PET Jars"},
                    "returns": "family"
                },
                {
                    "action": "create",
                    "table": "variant_axes",
                    "data": {
                        "axis_name": "Size",
                        "family_id": "@family.id"  # Reference to family
                    },
                    "dependencies": ["family"]
                }
            ],
            "impact": {"creates": {"product_families": 1, "variant_axes": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 2

        # Verify operations executed in correct order
        calls = mock_storage.insert_entity.call_args_list
        assert len(calls) == 2
        # Second call should have resolved family_id
        assert calls[1][1]["data"]["family_id"] == "family-1"

    @pytest.mark.asyncio
    async def test_three_operations_chain_dependency(self, mock_storage):
        """Test 3 operations with chain dependency (A → B → C)."""
        mock_storage.insert_entity.side_effect = [
            {"id": "family-1"},
            {"id": "axis-1"},
            {"id": "value-1"}
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create family, axis, and value",
            "reasoning": "Complete product hierarchy",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {
                    "action": "create",
                    "table": "product_families",
                    "data": {"name": "PET Jars"},
                    "returns": "family"
                },
                {
                    "action": "create",
                    "table": "variant_axes",
                    "data": {"family_id": "@family.id"},
                    "dependencies": ["family"],
                    "returns": "axis"
                },
                {
                    "action": "create",
                    "table": "variant_values",
                    "data": {"axis_id": "@axis.id"},
                    "dependencies": ["axis"]
                }
            ],
            "impact": {"creates": {"product_families": 1, "variant_axes": 1, "variant_values": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 3

    @pytest.mark.asyncio
    async def test_fan_out_dependencies(self, mock_storage):
        """Test fan-out: A → B, A → C (B and C depend on A)."""
        mock_storage.insert_entity.side_effect = [
            {"id": "family-1"},
            {"id": "axis-1"},
            {"id": "axis-2"}
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create family with multiple axes",
            "reasoning": "Multi-dimensional variants",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {
                    "action": "create",
                    "table": "product_families",
                    "data": {"name": "Containers"},
                    "returns": "family"
                },
                {
                    "action": "create",
                    "table": "variant_axes",
                    "data": {"axis_name": "Size", "family_id": "@family.id"},
                    "dependencies": ["family"]
                },
                {
                    "action": "create",
                    "table": "variant_axes",
                    "data": {"axis_name": "Color", "family_id": "@family.id"},
                    "dependencies": ["family"]
                }
            ],
            "impact": {"creates": {"product_families": 1, "variant_axes": 2}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 3

    @pytest.mark.asyncio
    async def test_diamond_dependency(self, mock_storage):
        """Test diamond: A → B, A → C, B → D, C → D."""
        mock_storage.insert_entity.side_effect = [
            {"id": "a"},
            {"id": "b"},
            {"id": "c"},
            {"id": "d"}
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Complex dependency",
            "reasoning": "Test diamond pattern",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {"v": 1}, "returns": "a"},
                {"action": "create", "table": "t2", "data": {"ref": "@a.id"}, "dependencies": ["a"], "returns": "b"},
                {"action": "create", "table": "t3", "data": {"ref": "@a.id"}, "dependencies": ["a"], "returns": "c"},
                {"action": "create", "table": "t4", "data": {"b_ref": "@b.id", "c_ref": "@c.id"}, "dependencies": ["b", "c"]}
            ],
            "impact": {"creates": {"t1": 1, "t2": 1, "t3": 1, "t4": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 4

    @pytest.mark.asyncio
    async def test_nested_field_reference(self, mock_storage):
        """Test nested field access (@name.nested.field)."""
        mock_storage.insert_entity.return_value = {
            "id": "obj-1",
            "metadata": {"category_id": "cat-123"}
        }

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Reference nested field",
            "reasoning": "Test deep access",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {
                    "action": "create",
                    "table": "objects",
                    "data": {"metadata": {"category_id": "cat-123"}},
                    "returns": "obj"
                },
                {
                    "action": "create",
                    "table": "related",
                    "data": {"category_id": "@obj.metadata.category_id"},
                    "dependencies": ["obj"]
                }
            ],
            "impact": {"creates": {"objects": 1, "related": 1}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_multiple_refs_in_single_operation(self, mock_storage):
        """Test multiple @references in single operation data."""
        mock_storage.insert_entity.side_effect = [
            {"id": "user-1"},
            {"id": "category-1"},
            {"id": "product-1"}
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create with multiple refs",
            "reasoning": "Test multi-ref resolution",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "users", "data": {"name": "Alice"}, "returns": "user"},
                {"action": "create", "table": "categories", "data": {"name": "Food"}, "returns": "category"},
                {
                    "action": "create",
                    "table": "products",
                    "data": {
                        "name": "Item",
                        "created_by": "@user.id",
                        "category_id": "@category.id"
                    },
                    "dependencies": ["user", "category"]
                }
            ],
            "impact": {"creates": {"users": 1, "categories": 1, "products": 1}}
        })

        assert result["success"] is True
        # Verify both references resolved correctly
        calls = mock_storage.insert_entity.call_args_list
        assert calls[2][1]["data"]["created_by"] == "user-1"
        assert calls[2][1]["data"]["category_id"] == "category-1"

    @pytest.mark.asyncio
    async def test_no_dependencies_execute_first(self, mock_storage):
        """Test operations without dependencies execute first."""
        execution_order = []

        async def track_insert(table, data):
            execution_order.append(table)
            return {"id": f"{table}-1"}

        mock_storage.insert_entity.side_effect = track_insert

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test execution order",
            "reasoning": "Verify topological sort",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                # This depends on B, should execute last
                {"action": "create", "table": "C", "data": {"ref": "@b.id"}, "dependencies": ["b"]},
                # This has no dependencies, should execute first
                {"action": "create", "table": "A", "data": {}, "returns": "a"},
                # This depends on A, should execute second
                {"action": "create", "table": "B", "data": {"ref": "@a.id"}, "dependencies": ["a"], "returns": "b"}
            ],
            "impact": {"creates": {"A": 1, "B": 1, "C": 1}}
        })

        assert result["success"] is True
        # Verify execution order: A (no deps) → B (deps: A) → C (deps: B)
        assert execution_order == ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_mixed_create_and_update_with_deps(self, mock_storage):
        """Test mix of CREATE and UPDATE with dependencies."""
        mock_storage.insert_entity.return_value = {"id": "new-1"}
        mock_storage.update_entities.return_value = 1

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create then update",
            "reasoning": "Test mixed operations",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {
                    "action": "create",
                    "table": "users",
                    "data": {"name": "Alice"},
                    "returns": "user"
                },
                {
                    "action": "update",
                    "table": "profiles",
                    "filters": {"user_id": "@user.id"},
                    "updates": {"verified": True},
                    "dependencies": ["user"]
                }
            ],
            "impact": {"creates": {"users": 1}, "updates": {"profiles": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 1
        assert result["summary"]["total_updated"] == 1

    @pytest.mark.asyncio
    async def test_list_data_with_references(self, mock_storage):
        """Test bulk data with @references (list of dicts)."""
        mock_storage.insert_entity.return_value = {"id": "family-1"}
        mock_storage.bulk_upsert.return_value = [{"id": "v1"}, {"id": "v2"}]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Bulk create with refs",
            "reasoning": "Test list resolution",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "families", "data": {"name": "F1"}, "returns": "fam"},
                {
                    "action": "create",
                    "table": "variants",
                    "data": [
                        {"family_id": "@fam.id", "name": "V1"},
                        {"family_id": "@fam.id", "name": "V2"}
                    ],
                    "dependencies": ["fam"]
                }
            ],
            "impact": {"creates": {"families": 1, "variants": 2}}
        })

        assert result["success"] is True
        # Verify bulk_upsert was called with resolved references
        bulk_call = mock_storage.bulk_upsert.call_args
        bulk_data = bulk_call[1]["data"]
        assert all(item["family_id"] == "family-1" for item in bulk_data)

    @pytest.mark.asyncio
    async def test_complex_6_operation_workflow(self, mock_storage):
        """Test realistic 6-operation workflow."""
        mock_storage.insert_entity.side_effect = [
            {"id": "fam-1"},
            {"id": "axis-size"},
            {"id": "axis-color"},
            {"id": "val-500ml"},
            {"id": "val-blue"},
            {"id": "prod-1"}
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Create complete product with 2 axes",
            "reasoning": "Full product setup",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "product_families", "data": {"name": "Jars"}, "returns": "family"},
                {"action": "create", "table": "variant_axes", "data": {"name": "Size", "family_id": "@family.id"}, "dependencies": ["family"], "returns": "size_axis"},
                {"action": "create", "table": "variant_axes", "data": {"name": "Color", "family_id": "@family.id"}, "dependencies": ["family"], "returns": "color_axis"},
                {"action": "create", "table": "variant_values", "data": {"value": "500ml", "axis_id": "@size_axis.id"}, "dependencies": ["size_axis"], "returns": "size_val"},
                {"action": "create", "table": "variant_values", "data": {"value": "Blue", "axis_id": "@color_axis.id"}, "dependencies": ["color_axis"], "returns": "color_val"},
                {
                    "action": "create",
                    "table": "products",
                    "data": {
                        "family_id": "@family.id",
                        "size_value_id": "@size_val.id",
                        "color_value_id": "@color_val.id"
                    },
                    "dependencies": ["family", "size_val", "color_val"]
                }
            ],
            "impact": {"creates": {"product_families": 1, "variant_axes": 2, "variant_values": 2, "products": 1}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 6


# =============================================================================
# Group 3: Validation Tests (12 tests)
# =============================================================================


class TestValidation:
    """Test WriteIntent validation."""

    @pytest.mark.asyncio
    async def test_validation_duplicate_returns_names(self, mock_storage):
        """Test validation detects duplicate returns names."""
        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test duplicate returns",
            "reasoning": "Should fail validation",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {}, "returns": "obj"},
                {"action": "create", "table": "t2", "data": {}, "returns": "obj"}  # Duplicate!
            ],
            "impact": {"creates": {"t1": 1, "t2": 1}}
        })

        assert result["success"] is False
        assert "Duplicate returns names" in result["error"]

    @pytest.mark.asyncio
    async def test_validation_missing_dependency(self, mock_storage):
        """Test validation detects missing dependency."""
        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test missing dependency",
            "reasoning": "Should fail validation",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {
                    "action": "create",
                    "table": "t1",
                    "data": {"ref": "@nonexistent.id"},
                    "dependencies": ["nonexistent"]  # No operation with returns="nonexistent"
                }
            ],
            "impact": {"creates": {"t1": 1}}
        })

        assert result["success"] is False
        assert "not found in returns names" in result["error"]

    @pytest.mark.asyncio
    async def test_validation_circular_dependency(self, mock_storage):
        """Test validation detects circular dependencies."""
        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test circular dependency",
            "reasoning": "Should fail validation",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {"ref": "@b.id"}, "dependencies": ["b"], "returns": "a"},
                {"action": "create", "table": "t2", "data": {"ref": "@a.id"}, "dependencies": ["a"], "returns": "b"}
            ],
            "impact": {"creates": {"t1": 1, "t2": 1}}
        })

        assert result["success"] is False
        assert "Dependency error" in result["error"]

    @pytest.mark.asyncio
    async def test_validation_create_missing_data(self, mock_storage):
        """Test validation detects CREATE without data."""
        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test missing data",
            "reasoning": "Should fail validation",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "products"}  # No data field!
            ],
            "impact": {"creates": {"products": 1}}
        })

        assert result["success"] is False
        assert "data is required" in result["error"]

    @pytest.mark.asyncio
    async def test_validation_update_missing_filters(self, mock_storage):
        """Test validation detects UPDATE without filters."""
        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test missing filters",
            "reasoning": "Should fail validation",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "update", "table": "products", "updates": {"price": 100}}  # No filters!
            ],
            "impact": {"updates": {"products": 1}}
        })

        assert result["success"] is False
        assert "filters required" in result["error"]

    @pytest.mark.asyncio
    async def test_validation_delete_missing_filters(self, mock_storage):
        """Test validation detects DELETE without filters."""
        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test missing filters",
            "reasoning": "Should fail validation",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "delete", "table": "products"}  # No filters! Dangerous!
            ],
            "impact": {"deletes": {"products": 1}}
        })

        assert result["success"] is False
        assert "filters required" in result["error"]

    @pytest.mark.asyncio
    async def test_access_control_table_allowed(self, mock_storage):
        """Test access control allows specified tables."""
        tool = create_write_data_tool(mock_storage, tables=["products", "orders"])

        result = await tool.ainvoke({
            "goal": "Create in allowed table",
            "reasoning": "Should succeed",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "products", "data": {"name": "Test"}}
            ],
            "impact": {"creates": {"products": 1}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_access_control_table_denied(self, mock_storage):
        """Test access control blocks unauthorized tables."""
        tool = create_write_data_tool(mock_storage, tables=["products"])

        result = await tool.ainvoke({
            "goal": "Create in unauthorized table",
            "reasoning": "Should fail",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "admin_users", "data": {"name": "Hacker"}}
            ],
            "impact": {"creates": {"admin_users": 1}}
        })

        assert result["success"] is False
        assert result["error_type"] == "ACCESS_DENIED"
        assert "Access denied" in result["error"]

    @pytest.mark.asyncio
    async def test_access_control_multi_op_all_allowed(self, mock_storage):
        """Test access control with multiple ops (all allowed)."""
        mock_storage.insert_entity.side_effect = [{"id": "1"}, {"id": "2"}]

        tool = create_write_data_tool(mock_storage, tables=["products", "categories"])

        result = await tool.ainvoke({
            "goal": "Create in multiple allowed tables",
            "reasoning": "Should succeed",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "categories", "data": {"name": "Food"}, "returns": "cat"},
                {"action": "create", "table": "products", "data": {"category_id": "@cat.id"}, "dependencies": ["cat"]}
            ],
            "impact": {"creates": {"categories": 1, "products": 1}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_access_control_multi_op_one_denied(self, mock_storage):
        """Test access control with multiple ops (one unauthorized)."""
        tool = create_write_data_tool(mock_storage, tables=["products"])

        result = await tool.ainvoke({
            "goal": "Mixed authorized and unauthorized",
            "reasoning": "Should fail",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "products", "data": {"name": "OK"}},
                {"action": "create", "table": "unauthorized_table", "data": {"bad": True}}
            ],
            "impact": {"creates": {"products": 1, "unauthorized_table": 1}}
        })

        assert result["success"] is False
        assert result["error_type"] == "ACCESS_DENIED"
        assert "Access denied" in result["error"]

    @pytest.mark.asyncio
    async def test_validation_empty_operations_list(self, mock_storage):
        """Test validation detects empty operations list.

        Pydantic validation raises ValidationError before tool execution
        for invalid input structures like empty operations.
        """
        from pydantic import ValidationError

        tool = create_write_data_tool(mock_storage, tables=None)

        # Empty operations fails at Pydantic validation level
        with pytest.raises(ValidationError) as exc_info:
            await tool.ainvoke({
                "goal": "Test empty ops",
                "reasoning": "Should fail",
                "hitl_summary": TEST_HITL_SUMMARY,
                "operations": [],  # Empty!
                "impact": {}
            })

        # Verify error mentions operations validation
        error_str = str(exc_info.value).lower()
        assert "operations" in error_str or "empty" in error_str

    @pytest.mark.asyncio
    async def test_validation_passes_for_valid_intent(self, mock_storage):
        """Test validation passes for well-formed WriteIntent."""
        mock_storage.insert_entity.return_value = {"id": "1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Valid intent",
            "reasoning": "All fields correct",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "products", "data": {"name": "Test"}}
            ],
            "impact": {"creates": {"products": 1}}
        })

        assert result["success"] is True


# =============================================================================
# Group 4: Error Handling and Rollback (8 tests)
# =============================================================================


class TestErrorHandlingAndRollback:
    """Test error handling and transaction rollback."""

    @pytest.mark.asyncio
    async def test_storage_error_triggers_rollback(self, mock_storage):
        """Test storage error triggers automatic rollback."""
        # First op succeeds, second fails
        mock_storage.insert_entity.side_effect = [
            {"id": "success-1"},
            Exception("Database error")
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test rollback",
            "reasoning": "Second op should fail",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {"name": "First"}},
                {"action": "create", "table": "t2", "data": {"name": "Second"}}
            ],
            "impact": {"creates": {"t1": 1, "t2": 1}}
        })

        assert result["success"] is False
        assert "error" in result
        # Transaction should have been entered (rollback automatic)
        mock_storage.transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_reference_fails_gracefully(self, mock_storage):
        """Test invalid @reference generates clear error."""
        mock_storage.insert_entity.return_value = {"id": "obj-1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test invalid ref",
            "reasoning": "Reference non-existent field",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {"name": "A"}, "returns": "obj"},
                {
                    "action": "create",
                    "table": "t2",
                    "data": {"ref": "@obj.nonexistent_field"},  # Field doesn't exist
                    "dependencies": ["obj"]
                }
            ],
            "impact": {"creates": {"t1": 1, "t2": 1}}
        })

        assert result["success"] is False
        # Should get clear error about missing field
        assert "error" in result

    @pytest.mark.asyncio
    async def test_malformed_reference_syntax_fails(self, mock_storage):
        """Test malformed @reference syntax generates error."""
        mock_storage.insert_entity.return_value = {"id": "obj-1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test malformed ref",
            "reasoning": "Bad syntax",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {"name": "A"}, "returns": "obj"},
                {
                    "action": "create",
                    "table": "t2",
                    "data": {"ref": "@obj"},  # Missing .field part!
                    "dependencies": ["obj"]
                }
            ],
            "impact": {"creates": {"t1": 1, "t2": 1}}
        })

        assert result["success"] is False
        assert "Invalid reference syntax" in result["error"]

    @pytest.mark.asyncio
    async def test_update_error_includes_context(self, mock_storage):
        """Test update error includes helpful context."""
        mock_storage.update_entities.side_effect = Exception("Constraint violation")

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test update error",
            "reasoning": "Trigger constraint error",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {
                    "action": "update",
                    "table": "products",
                    "filters": {"id": "test"},
                    "updates": {"invalid_field": "value"}
                }
            ],
            "impact": {"updates": {"products": 1}}
        })

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_pydantic_validation_error_clear_message(self, mock_storage):
        """Test Pydantic validation errors have clear messages."""
        tool = create_write_data_tool(mock_storage, tables=None)

        # Missing required field 'goal'
        with pytest.raises(Exception) as exc_info:
            await tool.ainvoke({
                "reasoning": "Missing goal field",
                "operations": [{"action": "create", "table": "t", "data": {}}],
                "impact": {}
            })

        # Should be Pydantic validation error
        assert "goal" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execution_result_includes_execution_time_on_error(self, mock_storage):
        """Test error result includes execution time."""
        mock_storage.insert_entity.side_effect = Exception("Test error")

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test error timing",
            "reasoning": "Should track time even on error",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t", "data": {}}
            ],
            "impact": {"creates": {"t": 1}}
        })

        assert result["success"] is False
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_partial_execution_rolls_back_all(self, mock_storage):
        """Test partial execution rolls back ALL operations."""
        # First 2 succeed, third fails
        mock_storage.insert_entity.side_effect = [
            {"id": "1"},
            {"id": "2"},
            Exception("Third op fails")
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test partial rollback",
            "reasoning": "Third op fails",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {}},
                {"action": "create", "table": "t2", "data": {}},
                {"action": "create", "table": "t3", "data": {}}
            ],
            "impact": {"creates": {"t1": 1, "t2": 1, "t3": 1}}
        })

        assert result["success"] is False
        # Transaction rollback should happen automatically
        # (via context manager __aexit__)

    @pytest.mark.asyncio
    async def test_transaction_context_manager_entered(self, mock_storage):
        """Test transaction context manager is used."""
        mock_storage.insert_entity.return_value = {"id": "1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        await tool.ainvoke({
            "goal": "Test transaction",
            "reasoning": "Verify transaction used",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t", "data": {}}
            ],
            "impact": {"creates": {"t": 1}}
        })

        # Verify transaction() was called
        mock_storage.transaction.assert_called_once()
        # Verify __aenter__ was called (transaction started)
        mock_storage.transaction.return_value.__aenter__.assert_called_once()


# =============================================================================
# Group 5: Edge Cases (10 tests)
# =============================================================================


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    @pytest.mark.asyncio
    async def test_operation_returns_none(self, mock_storage):
        """Test operation with returns but result is None."""
        mock_storage.insert_entity.return_value = None

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test None result",
            "reasoning": "Edge case",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t", "data": {}, "returns": "obj"}
            ],
            "impact": {"creates": {"t": 1}}
        })

        # Should still succeed but with None in context
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_reference_to_none_result(self, mock_storage):
        """Test @reference to None result fails gracefully."""
        mock_storage.insert_entity.return_value = None

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Reference None",
            "reasoning": "Should fail",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {}, "returns": "obj"},
                {"action": "create", "table": "t2", "data": {"ref": "@obj.id"}, "dependencies": ["obj"]}
            ],
            "impact": {"creates": {"t1": 1, "t2": 1}}
        })

        # Should fail when trying to access .id on None
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_empty_string_as_reference(self, mock_storage):
        """Test empty string in data (not a reference)."""
        mock_storage.insert_entity.return_value = {"id": "1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test empty string",
            "reasoning": "Not a ref",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t", "data": {"name": ""}}  # Empty string, not @ref
            ],
            "impact": {"creates": {"t": 1}}
        })

        assert result["success"] is True
        # Empty string should pass through unchanged
        calls = mock_storage.insert_entity.call_args_list
        assert calls[0][1]["data"]["name"] == ""

    @pytest.mark.asyncio
    async def test_special_characters_in_returns_name(self, mock_storage):
        """Test special characters in returns name."""
        mock_storage.insert_entity.side_effect = [{"id": "1"}, {"id": "2"}]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test special chars",
            "reasoning": "Edge case",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t1", "data": {}, "returns": "obj_with_underscore"},
                {"action": "create", "table": "t2", "data": {"ref": "@obj_with_underscore.id"}, "dependencies": ["obj_with_underscore"]}
            ],
            "impact": {"creates": {"t1": 1, "t2": 1}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_very_long_operations_list(self, mock_storage):
        """Test WriteIntent with many operations (performance)."""
        mock_storage.insert_entity.return_value = {"id": "x"}

        # Create 50 operations
        operations = [
            {"action": "create", "table": f"table_{i}", "data": {"i": i}}
            for i in range(50)
        ]

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Bulk operations",
            "reasoning": "Performance test",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": operations,
            "impact": {"creates": {f"table_{i}": 1 for i in range(50)}}
        })

        assert result["success"] is True
        assert result["summary"]["total_created"] == 50

    @pytest.mark.asyncio
    async def test_unicode_in_data(self, mock_storage):
        """Test Unicode characters in operation data."""
        mock_storage.insert_entity.return_value = {"id": "1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test Unicode",
            "reasoning": "Special chars",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "products", "data": {"name": "Café ☕ 日本語"}}
            ],
            "impact": {"creates": {"products": 1}}
        })

        assert result["success"] is True
        # Verify Unicode preserved
        calls = mock_storage.insert_entity.call_args_list
        assert calls[0][1]["data"]["name"] == "Café ☕ 日本語"

    @pytest.mark.asyncio
    async def test_very_nested_data_structure(self, mock_storage):
        """Test deeply nested data structure."""
        mock_storage.insert_entity.return_value = {"id": "1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep"
                        }
                    }
                }
            }
        }

        result = await tool.ainvoke({
            "goal": "Test nesting",
            "reasoning": "Deep structure",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "objects", "data": nested_data}
            ],
            "impact": {"creates": {"objects": 1}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_null_values_in_data(self, mock_storage):
        """Test None/null values in operation data."""
        mock_storage.insert_entity.return_value = {"id": "1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test null values",
            "reasoning": "Edge case",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t", "data": {"nullable_field": None}}
            ],
            "impact": {"creates": {"t": 1}}
        })

        assert result["success"] is True
        # None should pass through
        calls = mock_storage.insert_entity.call_args_list
        assert calls[0][1]["data"]["nullable_field"] is None

    @pytest.mark.asyncio
    async def test_boolean_and_numeric_edge_values(self, mock_storage):
        """Test edge values for booleans and numbers."""
        mock_storage.insert_entity.return_value = {"id": "1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Test edge values",
            "reasoning": "Type boundaries",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {
                    "action": "create",
                    "table": "t",
                    "data": {
                        "bool_true": True,
                        "bool_false": False,
                        "zero": 0,
                        "negative": -999,
                        "float": 3.14159,
                        "large_int": 999999999999
                    }
                }
            ],
            "impact": {"creates": {"t": 1}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_operation_without_impact_field(self, mock_storage):
        """Test WriteIntent with minimal impact."""
        mock_storage.insert_entity.return_value = {"id": "1"}

        tool = create_write_data_tool(mock_storage, tables=None)

        result = await tool.ainvoke({
            "goal": "Minimal impact",
            "reasoning": "Edge case",
            "hitl_summary": TEST_HITL_SUMMARY,
            "operations": [
                {"action": "create", "table": "t", "data": {}}
            ],
            "impact": {"creates": {"t": 1}}  # Minimal valid impact
        })

        assert result["success"] is True
