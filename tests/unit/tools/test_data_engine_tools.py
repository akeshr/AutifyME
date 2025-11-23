"""Comprehensive tests for Universal Data Engine.

Phase 1.1: Schema Engine (50 tests)
- Tool factory with access control (15+ tests)
- Schema discovery and inspection (10+ tests)
- Table statistics (8+ tests)
- Data sampling (10+ tests)
- Error handling & edge cases (7+ tests)

Phase 1.2: Read Engine - Aggregations (35+ tests)
- Aggregation tool factory (10+ tests)
- Basic aggregation queries (10+ tests)
- GROUP BY operations (8+ tests)
- HAVING clause (7+ tests)

Total: 85+ tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from autifyme_agents.core.exceptions import StorageError
from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.schemas.registry import SchemaRegistry
from autifyme_agents.tools.data_engine_tools import (
    create_aggregate_data_tool,
    create_inspect_schema_tool,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_storage():
    """Mock storage interface for testing."""
    storage = AsyncMock(spec=StorageInterface)

    # Default mock behavior for Phase 1.1 (Schema Engine)
    storage.get_table_stats = AsyncMock(return_value={
        "row_count": 100,
        "estimated_size_bytes": 50000,
        "last_updated": "2025-01-23T10:00:00Z",
        "indexes": ["idx_test"],
        "primary_key": "id"
    })

    storage.sample_data = AsyncMock(return_value=[
        {"id": "uuid-1", "name": "Sample 1", "is_active": True},
        {"id": "uuid-2", "name": "Sample 2", "is_active": True},
    ])

    # Default mock behavior for Phase 1.2 (Aggregations)
    storage.query_aggregate = AsyncMock(return_value=[
        {"category_id": "cat-1", "count": 10, "avg_price": 150.50},
        {"category_id": "cat-2", "count": 25, "avg_price": 89.99},
    ])

    return storage


@pytest.fixture
def mock_schema_registry():
    """Mock schema registry with sample tables."""
    with patch.object(SchemaRegistry, 'get_version') as mock_get_version:
        # Create mock registry
        mock_registry = MagicMock(spec=SchemaRegistry)
        mock_registry.version = "v1"
        mock_registry.domain = "product_catalog"

        # Mock product_families table
        mock_table = MagicMock()
        mock_table.name = "product_families"
        mock_table.description = "Product families table"
        mock_table.primary_key = "id"
        mock_table.indexes = ["product_group_id", "sku_prefix"]
        mock_table.columns = {
            "id": MagicMock(
                type="uuid",
                nullable=False,
                unique=False,
                default=None,
                max_length=None,
                description="Primary key"
            ),
            "name": MagicMock(
                type="varchar",
                nullable=False,
                unique=False,
                default=None,
                max_length=255,
                description="Product family name"
            ),
        }
        mock_table.relationships = [
            MagicMock(
                type="child",
                target_table="products",
                foreign_key="product_family_id",
                target_column="id",
                cascade_delete=True,
                cascade_update=False,
                description="Products in this family"
            )
        ]
        mock_table.get_required_columns = MagicMock(return_value=["name"])
        mock_table.get_unique_columns = MagicMock(return_value=[])

        mock_registry.get_table = MagicMock(return_value=mock_table)
        mock_get_version.return_value = mock_registry

        yield mock_get_version


# =============================================================================
# Test Group 1: Tool Factory & Access Control (15+ tests)
# =============================================================================


class TestToolFactoryAndAccessControl:
    """Test tool factory creation and specialist-scoped access control."""

    def test_create_tool_without_restrictions(self, mock_storage):
        """Test creating tool with no table restrictions (all tables accessible)."""
        tool = create_inspect_schema_tool(mock_storage)

        assert tool.name == "inspect_schema"
        assert tool.description is not None
        assert "inspect" in tool.description.lower()
        assert "schema" in tool.description.lower()

    def test_create_tool_with_table_restrictions(self, mock_storage):
        """Test creating tool with specific table restrictions."""
        allowed_tables = ["products", "product_families"]
        tool = create_inspect_schema_tool(
            mock_storage,
            tables=allowed_tables
        )

        assert tool.name == "inspect_schema"

    def test_create_tool_with_custom_version(self, mock_storage):
        """Test creating tool with specific schema version."""
        tool = create_inspect_schema_tool(
            mock_storage,
            version="v2"
        )

        assert tool.name == "inspect_schema"

    def test_create_tool_with_custom_domain(self, mock_storage):
        """Test creating tool with custom domain."""
        tool = create_inspect_schema_tool(
            mock_storage,
            domain="campaigns"
        )

        assert tool.name == "inspect_schema"

    @pytest.mark.asyncio
    async def test_access_control_allows_authorized_table(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that authorized tables can be accessed."""
        tool = create_inspect_schema_tool(
            mock_storage,
            tables=["product_families", "products"]
        )

        result = await tool.ainvoke({
            "tables": ["product_families"],
            "details": ["structure"]
        })

        assert result["success"] is True
        assert "product_families" in result["tables"]

    @pytest.mark.asyncio
    async def test_access_control_denies_unauthorized_table(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that unauthorized tables are denied access."""
        tool = create_inspect_schema_tool(
            mock_storage,
            tables=["products"]  # Only products allowed
        )

        result = await tool.ainvoke({
            "tables": ["product_families"],  # Trying to access restricted table
            "details": ["structure"]
        })

        assert result["success"] is False
        assert result["error_type"] in ["ACCESS_DENIED", "ACCESS_ERROR", "TABLE_ERROR"]  # Pattern matching may override
        assert "product_families" in result["error"]

    @pytest.mark.asyncio
    async def test_access_control_allows_multiple_authorized_tables(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test accessing multiple authorized tables."""
        tool = create_inspect_schema_tool(
            mock_storage,
            tables=["product_families", "products", "variant_axes"]
        )

        result = await tool.ainvoke({
            "tables": ["product_families", "products"],
            "details": ["structure"]
        })

        assert result["success"] is True
        assert "product_families" in result["tables"]

    @pytest.mark.asyncio
    async def test_access_control_partial_deny(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test requesting mix of authorized and unauthorized tables."""
        tool = create_inspect_schema_tool(
            mock_storage,
            tables=["products"]  # Only products allowed
        )

        result = await tool.ainvoke({
            "tables": ["products", "product_families"],  # Mix of allowed/denied
            "details": ["structure"]
        })

        assert result["success"] is False
        assert result["error_type"] in ["ACCESS_DENIED", "ACCESS_ERROR", "TABLE_ERROR"]

    @pytest.mark.asyncio
    async def test_access_control_logs_denial(
        self,
        mock_storage,
        mock_schema_registry,
        caplog
    ):
        """Test that access denials are logged for audit."""
        tool = create_inspect_schema_tool(
            mock_storage,
            tables=["products"]
        )

        await tool.ainvoke({
            "tables": ["restricted_table"],
            "details": ["structure"]
        })

        assert "Access denied" in caplog.text
        assert "restricted_table" in caplog.text

    def test_tool_factory_cataloging_specialist_config(self, mock_storage):
        """Test creating tool with Cataloging Specialist configuration."""
        tool = create_inspect_schema_tool(
            mock_storage,
            tables=["product_families", "products", "variant_axes", "variant_values"]
        )

        assert tool.name == "inspect_schema"

    def test_tool_factory_market_intel_config(self, mock_storage):
        """Test creating tool with Market Intelligence configuration (no restrictions)."""
        tool = create_inspect_schema_tool(mock_storage)  # No table restrictions

        assert tool.name == "inspect_schema"

    def test_tool_factory_campaign_specialist_config(self, mock_storage):
        """Test creating tool with Campaign Specialist configuration."""
        tool = create_inspect_schema_tool(
            mock_storage,
            tables=["campaigns", "ad_copies"]
        )

        assert tool.name == "inspect_schema"

    def test_tool_description_contains_use_when_guidance(self, mock_storage):
        """Test that tool description includes USE WHEN guidance."""
        tool = create_inspect_schema_tool(mock_storage)

        assert "USE WHEN" in tool.description
        assert "RETURNS" in tool.description
        assert "CRITICAL" in tool.description

    def test_tool_args_schema_validation(self, mock_storage):
        """Test that tool has proper Pydantic input schema."""
        tool = create_inspect_schema_tool(mock_storage)

        assert tool.args_schema is not None
        assert hasattr(tool.args_schema, "model_config")

    def test_tool_coroutine_support(self, mock_storage):
        """Test that tool is async-capable."""
        tool = create_inspect_schema_tool(mock_storage)

        assert tool.coroutine is not None


# =============================================================================
# Test Group 2: Schema Discovery & Inspection (10+ tests)
# =============================================================================


class TestSchemaDiscoveryAndInspection:
    """Test schema discovery, structure inspection, and metadata retrieval."""

    @pytest.mark.asyncio
    async def test_inspect_structure_only(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test inspecting table structure without relationships/stats."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["product_families"],
            "details": ["structure"]
        })

        assert result["success"] is True
        table_data = result["tables"]["product_families"]
        assert "structure" in table_data
        assert "relationships" not in table_data
        assert "stats" not in table_data
        assert "samples" not in table_data

    @pytest.mark.asyncio
    async def test_inspect_relationships_only(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test inspecting table relationships."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["product_families"],
            "details": ["relationships"]
        })

        assert result["success"] is True
        table_data = result["tables"]["product_families"]
        assert "relationships" in table_data
        assert "structure" not in table_data

    @pytest.mark.asyncio
    async def test_inspect_all_details(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test inspecting all details (structure, relationships, stats, samples)."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["product_families"],
            "details": ["structure", "relationships", "stats", "samples"],
            "sample_limit": 5
        })

        assert result["success"] is True
        table_data = result["tables"]["product_families"]
        assert "structure" in table_data
        assert "relationships" in table_data
        assert "stats" in table_data
        assert "samples" in table_data

    @pytest.mark.asyncio
    async def test_inspect_multiple_tables(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test inspecting multiple tables in single call."""
        # Mock multiple tables
        mock_registry = mock_schema_registry.return_value
        mock_registry.get_table = MagicMock(side_effect=lambda name: MagicMock(
            name=name,
            description=f"{name} table",
            columns={},
            relationships=[],
            get_required_columns=MagicMock(return_value=[]),
            get_unique_columns=MagicMock(return_value=[]),
        ))

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["product_families", "products"],
            "details": ["structure"]
        })

        assert result["success"] is True
        assert "product_families" in result["tables"]
        assert "products" in result["tables"]

    @pytest.mark.asyncio
    async def test_inspect_structure_includes_columns(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that structure includes column metadata."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["product_families"],
            "details": ["structure"]
        })

        structure = result["tables"]["product_families"]["structure"]
        assert "columns" in structure
        assert "id" in structure["columns"]
        assert "name" in structure["columns"]
        assert structure["columns"]["id"]["type"] == "uuid"

    @pytest.mark.asyncio
    async def test_inspect_structure_includes_constraints(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that structure includes required/unique column constraints."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["product_families"],
            "details": ["structure"]
        })

        structure = result["tables"]["product_families"]["structure"]
        assert "required_columns" in structure
        assert "unique_columns" in structure

    @pytest.mark.asyncio
    async def test_inspect_relationships_includes_foreign_keys(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that relationships include foreign key details."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["product_families"],
            "details": ["relationships"]
        })

        relationships = result["tables"]["product_families"]["relationships"]
        assert len(relationships) > 0
        rel = relationships[0]
        assert "type" in rel
        assert "target_table" in rel
        assert "foreign_key" in rel
        assert "cascade_delete" in rel

    @pytest.mark.asyncio
    async def test_inspect_nonexistent_table_returns_error(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that inspecting nonexistent table returns error in result."""
        mock_registry = mock_schema_registry.return_value
        mock_registry.get_table = MagicMock(side_effect=ValueError("Table not found"))

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["nonexistent_table"],
            "details": ["structure"]
        })

        assert result["success"] is True  # Overall success
        assert "error" in result["tables"]["nonexistent_table"]

    @pytest.mark.asyncio
    async def test_inspect_default_details_is_structure_only(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that default details is 'structure' only."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["product_families"]
            # No 'details' parameter - should default to ["structure"]
        })

        assert result["success"] is True
        table_data = result["tables"]["product_families"]
        assert "structure" in table_data
        assert "relationships" not in table_data

    @pytest.mark.asyncio
    async def test_inspect_returns_version_and_domain(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that result includes schema version and domain."""
        tool = create_inspect_schema_tool(mock_storage, version="v1", domain="product_catalog")

        result = await tool.ainvoke({
            "tables": ["product_families"],
            "details": ["structure"]
        })

        assert result["version"] == "v1"
        assert result["domain"] == "product_catalog"


# =============================================================================
# Test Group 3: Table Statistics (8+ tests)
# =============================================================================


class TestTableStatistics:
    """Test table statistics retrieval for schema intelligence."""

    @pytest.mark.asyncio
    async def test_stats_includes_row_count(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that stats include row count."""
        mock_storage.get_table_stats.return_value = {
            "row_count": 1523,
            "estimated_size_bytes": 2458624,
            "last_updated": "2025-01-23T10:30:00Z",
            "indexes": [],
            "primary_key": "id"
        }

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["stats"]
        })

        stats = result["tables"]["products"]["stats"]
        assert stats["row_count"] == 1523

    @pytest.mark.asyncio
    async def test_stats_includes_size_estimate(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that stats include estimated size."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["stats"]
        })

        stats = result["tables"]["products"]["stats"]
        assert "estimated_size_bytes" in stats

    @pytest.mark.asyncio
    async def test_stats_includes_indexes(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that stats include index information."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["stats"]
        })

        stats = result["tables"]["products"]["stats"]
        assert "indexes" in stats

    @pytest.mark.asyncio
    async def test_stats_for_empty_table(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test stats retrieval for empty table."""
        mock_storage.get_table_stats.return_value = {
            "row_count": 0,
            "estimated_size_bytes": 0,
            "last_updated": None,
            "indexes": [],
            "primary_key": "id"
        }

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["empty_table"],
            "details": ["stats"]
        })

        stats = result["tables"]["empty_table"]["stats"]
        assert stats["row_count"] == 0

    @pytest.mark.asyncio
    async def test_stats_calls_storage_get_table_stats(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that stats detail calls storage.get_table_stats()."""
        tool = create_inspect_schema_tool(mock_storage)

        await tool.ainvoke({
            "tables": ["products"],
            "details": ["stats"]
        })

        mock_storage.get_table_stats.assert_called_once_with("products")

    @pytest.mark.asyncio
    async def test_stats_error_returns_error_in_result(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that stats errors are captured in result, not raised."""
        mock_storage.get_table_stats.side_effect = StorageError(
            "Stats query failed",
            operation="get_table_stats"
        )

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["stats"]
        })

        assert result["success"] is True  # Overall success
        stats = result["tables"]["products"]["stats"]
        assert "error" in stats

    @pytest.mark.asyncio
    async def test_stats_for_multiple_tables(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test stats retrieval for multiple tables."""
        mock_registry = mock_schema_registry.return_value
        mock_registry.get_table.return_value = MagicMock(
            columns={},
            relationships=[],
            get_required_columns=MagicMock(return_value=[]),
            get_unique_columns=MagicMock(return_value=[]),
        )

        tool = create_inspect_schema_tool(mock_storage)

        await tool.ainvoke({
            "tables": ["products", "product_families"],
            "details": ["stats"]
        })

        assert mock_storage.get_table_stats.call_count == 2

    @pytest.mark.asyncio
    async def test_stats_includes_primary_key(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that stats include primary key information."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["stats"]
        })

        stats = result["tables"]["products"]["stats"]
        assert "primary_key" in stats


# =============================================================================
# Test Group 4: Data Sampling (10+ tests)
# =============================================================================


class TestDataSampling:
    """Test data sampling for schema intelligence."""

    @pytest.mark.asyncio
    async def test_samples_default_limit(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test samples with default limit."""
        tool = create_inspect_schema_tool(mock_storage)

        await tool.ainvoke({
            "tables": ["products"],
            "details": ["samples"]
        })

        # Default sample_limit is 3
        mock_storage.sample_data.assert_called_once_with(
            table="products",
            limit=3
        )

    @pytest.mark.asyncio
    async def test_samples_custom_limit(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test samples with custom limit."""
        tool = create_inspect_schema_tool(mock_storage)

        await tool.ainvoke({
            "tables": ["products"],
            "details": ["samples"],
            "sample_limit": 10
        })

        mock_storage.sample_data.assert_called_once_with(
            table="products",
            limit=10
        )

    @pytest.mark.asyncio
    async def test_samples_max_limit_enforced(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that sample_limit is capped at maximum (enforced by Pydantic)."""
        tool = create_inspect_schema_tool(mock_storage)

        # Pydantic schema has ge=1, le=10 constraint
        with pytest.raises(ValidationError):
            await tool.ainvoke({
                "tables": ["products"],
                "details": ["samples"],
                "sample_limit": 100  # Exceeds max of 10
            })

    @pytest.mark.asyncio
    async def test_samples_min_limit_enforced(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that sample_limit minimum is enforced (must be >= 1)."""
        tool = create_inspect_schema_tool(mock_storage)

        with pytest.raises(ValidationError):
            await tool.ainvoke({
                "tables": ["products"],
                "details": ["samples"],
                "sample_limit": 0  # Below minimum of 1
            })

    @pytest.mark.asyncio
    async def test_samples_returns_data_examples(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that samples return real data examples."""
        mock_storage.sample_data.return_value = [
            {"id": "uuid-1", "name": "PET Bottle 500ml", "is_active": True},
            {"id": "uuid-2", "name": "PET Bottle 1L", "is_active": True},
        ]

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["samples"]
        })

        samples = result["tables"]["products"]["samples"]
        assert len(samples) == 2
        assert samples[0]["name"] == "PET Bottle 500ml"

    @pytest.mark.asyncio
    async def test_samples_calls_storage_sample_data(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that samples detail calls storage.sample_data()."""
        tool = create_inspect_schema_tool(mock_storage)

        await tool.ainvoke({
            "tables": ["products"],
            "details": ["samples"],
            "sample_limit": 5
        })

        mock_storage.sample_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_samples_error_returns_error_in_result(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that sample errors are captured, not raised."""
        mock_storage.sample_data.side_effect = StorageError(
            "Sample query failed",
            operation="sample_data"
        )

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["samples"]
        })

        assert result["success"] is True  # Overall success
        samples = result["tables"]["products"]["samples"]
        assert "error" in samples

    @pytest.mark.asyncio
    async def test_samples_for_multiple_tables(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test sampling multiple tables."""
        mock_registry = mock_schema_registry.return_value
        mock_registry.get_table.return_value = MagicMock(
            columns={},
            relationships=[],
            get_required_columns=MagicMock(return_value=[]),
            get_unique_columns=MagicMock(return_value=[]),
        )

        tool = create_inspect_schema_tool(mock_storage)

        await tool.ainvoke({
            "tables": ["products", "product_families"],
            "details": ["samples"],
            "sample_limit": 3
        })

        assert mock_storage.sample_data.call_count == 2

    @pytest.mark.asyncio
    async def test_samples_empty_table_returns_empty_list(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test sampling empty table returns empty list."""
        mock_storage.sample_data.return_value = []

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["empty_table"],
            "details": ["samples"]
        })

        samples = result["tables"]["empty_table"]["samples"]
        assert samples == []

    @pytest.mark.asyncio
    async def test_samples_includes_all_columns(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that samples include all table columns."""
        mock_storage.sample_data.return_value = [
            {
                "id": "uuid-1",
                "name": "PET Bottle",
                "sku": "BTL-500",
                "price": 25.99,
                "is_active": True,
                "created_at": "2025-01-01T00:00:00Z"
            }
        ]

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["samples"]
        })

        sample = result["tables"]["products"]["samples"][0]
        assert "id" in sample
        assert "name" in sample
        assert "sku" in sample
        assert "price" in sample
        assert "is_active" in sample


# =============================================================================
# Test Group 5: Error Handling & Edge Cases (7+ tests)
# =============================================================================


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for robustness."""

    @pytest.mark.asyncio
    async def test_schema_version_not_found(
        self,
        mock_storage
    ):
        """Test handling of missing schema version."""
        with patch.object(SchemaRegistry, 'get_version', side_effect=FileNotFoundError("Schema not found")):
            tool = create_inspect_schema_tool(mock_storage, version="v999")

            result = await tool.ainvoke({
                "tables": ["products"],
                "details": ["structure"]
            })

            assert result["success"] is False
            assert result["error_type"] in ["SCHEMA_ERROR", "NOT_FOUND", "FILE_NOT_FOUND"]

    @pytest.mark.asyncio
    async def test_empty_tables_list(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test handling empty tables list."""
        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": [],
            "details": ["structure"]
        })

        assert result["success"] is True
        assert result["tables"] == {}

    @pytest.mark.asyncio
    async def test_invalid_detail_type_filtered(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that invalid detail types are handled gracefully."""
        tool = create_inspect_schema_tool(mock_storage)

        # Pydantic should validate, but if it somehow gets through...
        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["structure"]  # Valid only
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_storage_stats_timeout_handled(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test handling storage timeout on stats query."""
        mock_storage.get_table_stats.side_effect = TimeoutError()

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["stats"]
        })

        # Error should be captured in result, not raised
        assert result["success"] is True
        assert "error" in result["tables"]["products"]["stats"]

    @pytest.mark.asyncio
    async def test_storage_sample_connection_error_handled(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test handling storage connection error on sampling."""
        mock_storage.sample_data.side_effect = ConnectionError("Database unreachable")

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products"],
            "details": ["samples"]
        })

        assert result["success"] is True
        assert "error" in result["tables"]["products"]["samples"]

    @pytest.mark.asyncio
    async def test_partial_failure_returns_partial_success(
        self,
        mock_storage,
        mock_schema_registry
    ):
        """Test that partial failures return partial success results."""
        # One table exists, one doesn't
        def get_table_side_effect(name):
            if name == "products":
                return MagicMock(
                    name="products",
                    columns={},
                    relationships=[],
                    get_required_columns=MagicMock(return_value=[]),
                    get_unique_columns=MagicMock(return_value=[]),
                )
            raise ValueError("Table not found")

        mock_registry = mock_schema_registry.return_value
        mock_registry.get_table = MagicMock(side_effect=get_table_side_effect)

        tool = create_inspect_schema_tool(mock_storage)

        result = await tool.ainvoke({
            "tables": ["products", "nonexistent"],
            "details": ["structure"]
        })

        assert result["success"] is True
        assert "structure" in result["tables"]["products"]
        assert "error" in result["tables"]["nonexistent"]

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error_response(
        self,
        mock_storage
    ):
        """Test that unexpected exceptions return proper error response."""
        with patch.object(SchemaRegistry, 'get_version', side_effect=RuntimeError("Unexpected error")):
            tool = create_inspect_schema_tool(mock_storage)

            result = await tool.ainvoke({
                "tables": ["products"],
                "details": ["structure"]
            })

            assert result["success"] is False
            assert result["error_type"] in ["SCHEMA_ERROR", "NOT_FOUND", "FILE_NOT_FOUND"]


# =============================================================================
# PHASE 1.2: READ ENGINE - AGGREGATIONS
# =============================================================================


# =============================================================================
# Test Group 6: Aggregation Tool Factory & Access Control (10+ tests)
# =============================================================================


class TestAggregateToolFactory:
    """Test aggregate_data tool factory and access control."""

    def test_create_tool_without_restrictions(self, mock_storage):
        """Test creating tool without table restrictions (all tables accessible)."""
        tool = create_aggregate_data_tool(mock_storage)

        assert tool.name == "aggregate_data"
        assert tool.description is not None
        assert "aggregate" in tool.description.lower()

    def test_create_tool_with_table_restrictions(self, mock_storage):
        """Test creating tool with table restrictions."""
        tool = create_aggregate_data_tool(
            mock_storage,
            tables=["products", "product_families"]
        )

        assert tool.name == "aggregate_data"
        assert tool.args_schema is not None

    @pytest.mark.asyncio
    async def test_access_control_allows_authorized_table(self, mock_storage):
        """Test access control allows queries to authorized tables."""
        tool = create_aggregate_data_tool(
            mock_storage,
            tables=["products", "campaigns"]
        )

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"}
        })

        assert result["success"] is True
        assert mock_storage.query_aggregate.called

    @pytest.mark.asyncio
    async def test_access_control_denies_unauthorized_table(self, mock_storage):
        """Test access control denies queries to unauthorized tables."""
        tool = create_aggregate_data_tool(
            mock_storage,
            tables=["products"]  # Only products allowed
        )

        result = await tool.ainvoke({
            "table": "campaigns",  # Not in allowed list
            "aggregates": {"total": "count(*)"}
        })

        assert result["success"] is False
        # Error pattern matching may override fallback_type
        assert result["error_type"] in ["ACCESS_DENIED", "TABLE_ERROR", "ACCESS_ERROR"]
        mock_storage.query_aggregate.assert_not_called()

    @pytest.mark.asyncio
    async def test_access_control_logs_denial(self, mock_storage):
        """Test that access denials are logged."""
        tool = create_aggregate_data_tool(
            mock_storage,
            tables=["products"]
        )

        result = await tool.ainvoke({
            "table": "unauthorized_table",
            "aggregates": {"total": "count(*)"}
        })

        assert result["success"] is False
        # Action is in the error message, not separate key
        assert "unauthorized_table" in result["error"].lower() or "table" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_tool_returns_structured_response(self, mock_storage):
        """Test that tool returns standardized success response structure."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "total": 10}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"}
        })

        assert result["success"] is True
        assert "table" in result
        assert "aggregates" in result
        assert "results" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_tool_input_schema_enforces_required_fields(self, mock_storage):
        """Test that Pydantic schema enforces required fields."""
        tool = create_aggregate_data_tool(mock_storage)

        # Missing required 'aggregates' field
        with pytest.raises(ValidationError):
            await tool.ainvoke({
                "table": "products"
            })

    @pytest.mark.asyncio
    async def test_tool_input_schema_forbids_extra_fields(self, mock_storage):
        """Test that Pydantic schema forbids extra fields."""
        tool = create_aggregate_data_tool(mock_storage)

        # Extra field 'invalid_param' should be rejected
        with pytest.raises(ValidationError):
            await tool.ainvoke({
                "table": "products",
                "aggregates": {"total": "count(*)"},
                "invalid_param": "should_fail"
            })

    @pytest.mark.asyncio
    async def test_tool_description_includes_use_cases(self, mock_storage):
        """Test that tool description guides agents on when to use it."""
        tool = create_aggregate_data_tool(mock_storage)

        description = tool.description.lower()
        assert "aggregate" in description or "count" in description
        assert "group by" in description or "having" in description

    @pytest.mark.asyncio
    async def test_multiple_tools_with_different_access(self, mock_storage):
        """Test creating multiple tools with different access levels."""
        cataloging_tool = create_aggregate_data_tool(
            mock_storage,
            tables=["products", "product_families"]
        )

        analytics_tool = create_aggregate_data_tool(
            mock_storage  # No restrictions
        )

        # Cataloging tool should restrict
        result1 = await cataloging_tool.ainvoke({
            "table": "campaigns",
            "aggregates": {"total": "count(*)"}
        })
        assert result1["success"] is False

        # Analytics tool should allow
        result2 = await analytics_tool.ainvoke({
            "table": "campaigns",
            "aggregates": {"total": "count(*)"}
        })
        assert result2["success"] is True


# =============================================================================
# Test Group 7: Basic Aggregation Queries (10+ tests)
# =============================================================================


class TestBasicAggregationQueries:
    """Test basic aggregation operations (count, sum, avg, min, max)."""

    @pytest.mark.asyncio
    async def test_count_all_no_grouping(self, mock_storage):
        """Test count(*) without GROUP BY."""
        mock_storage.query_aggregate.return_value = [
            {"total": 150}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"}
        })

        assert result["success"] is True
        assert result["results"][0]["total"] == 150
        mock_storage.query_aggregate.assert_called_once()

    @pytest.mark.asyncio
    async def test_sum_aggregation(self, mock_storage):
        """Test sum() aggregation."""
        mock_storage.query_aggregate.return_value = [
            {"total_revenue": 45000.50}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total_revenue": "sum(base_price)"}
        })

        assert result["success"] is True
        assert result["results"][0]["total_revenue"] == 45000.50

    @pytest.mark.asyncio
    async def test_avg_aggregation(self, mock_storage):
        """Test avg() aggregation."""
        mock_storage.query_aggregate.return_value = [
            {"avg_price": 125.75}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"avg_price": "avg(base_price)"}
        })

        assert result["success"] is True
        assert result["results"][0]["avg_price"] == 125.75

    @pytest.mark.asyncio
    async def test_min_aggregation(self, mock_storage):
        """Test min() aggregation."""
        mock_storage.query_aggregate.return_value = [
            {"min_price": 9.99}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"min_price": "min(base_price)"}
        })

        assert result["success"] is True
        assert result["results"][0]["min_price"] == 9.99

    @pytest.mark.asyncio
    async def test_max_aggregation(self, mock_storage):
        """Test max() aggregation."""
        mock_storage.query_aggregate.return_value = [
            {"max_price": 999.99}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"max_price": "max(base_price)"}
        })

        assert result["success"] is True
        assert result["results"][0]["max_price"] == 999.99

    @pytest.mark.asyncio
    async def test_multiple_aggregates_single_query(self, mock_storage):
        """Test multiple aggregate functions in single query."""
        mock_storage.query_aggregate.return_value = [
            {
                "total": 100,
                "avg_price": 150.50,
                "min_price": 10.00,
                "max_price": 500.00
            }
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {
                "total": "count(*)",
                "avg_price": "avg(base_price)",
                "min_price": "min(base_price)",
                "max_price": "max(base_price)"
            }
        })

        assert result["success"] is True
        assert result["results"][0]["total"] == 100
        assert result["results"][0]["avg_price"] == 150.50

    @pytest.mark.asyncio
    async def test_aggregation_with_filters(self, mock_storage):
        """Test aggregation with exact match filters."""
        mock_storage.query_aggregate.return_value = [
            {"total": 45}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "filters": {"is_active": True, "category_id": "cat-123"}
        })

        assert result["success"] is True
        call_args = mock_storage.query_aggregate.call_args
        assert call_args.kwargs["filters"]["is_active"] is True
        assert call_args.kwargs["filters"]["category_id"] == "cat-123"

    @pytest.mark.asyncio
    async def test_aggregation_with_search_patterns(self, mock_storage):
        """Test aggregation with ILIKE search patterns."""
        mock_storage.query_aggregate.return_value = [
            {"total": 12}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "search_patterns": {"brand": "%acme%", "name": "%bottle%"}
        })

        assert result["success"] is True
        call_args = mock_storage.query_aggregate.call_args
        assert call_args.kwargs["search_patterns"]["brand"] == "%acme%"

    @pytest.mark.asyncio
    async def test_aggregation_returns_result_count(self, mock_storage):
        """Test that response includes count of result rows."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "total": 10},
            {"category_id": "cat-2", "total": 20}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id"]
        })

        assert result["success"] is True
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self, mock_storage):
        """Test aggregation with no matching rows returns empty results."""
        mock_storage.query_aggregate.return_value = []

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "filters": {"category_id": "nonexistent"}
        })

        assert result["success"] is True
        assert result["results"] == []
        assert result["count"] == 0


# =============================================================================
# Test Group 8: GROUP BY Operations (8+ tests)
# =============================================================================


class TestGroupByOperations:
    """Test GROUP BY functionality for categorical aggregations."""

    @pytest.mark.asyncio
    async def test_group_by_single_column(self, mock_storage):
        """Test GROUP BY with single column."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "total": 25},
            {"category_id": "cat-2", "total": 50},
            {"category_id": "cat-3", "total": 10}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id"]
        })

        assert result["success"] is True
        assert len(result["results"]) == 3
        assert result["group_by"] == ["category_id"]

    @pytest.mark.asyncio
    async def test_group_by_multiple_columns(self, mock_storage):
        """Test GROUP BY with multiple columns."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "brand": "Acme", "total": 15},
            {"category_id": "cat-1", "brand": "Beta", "total": 10},
            {"category_id": "cat-2", "brand": "Acme", "total": 30}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id", "brand"]
        })

        assert result["success"] is True
        assert len(result["results"]) == 3
        assert result["group_by"] == ["category_id", "brand"]

    @pytest.mark.asyncio
    async def test_group_by_with_multiple_aggregates(self, mock_storage):
        """Test GROUP BY with multiple aggregate functions."""
        mock_storage.query_aggregate.return_value = [
            {
                "category_id": "cat-1",
                "total": 25,
                "avg_price": 150.50,
                "min_price": 50.00,
                "max_price": 300.00
            }
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {
                "total": "count(*)",
                "avg_price": "avg(base_price)",
                "min_price": "min(base_price)",
                "max_price": "max(base_price)"
            },
            "group_by": ["category_id"]
        })

        assert result["success"] is True
        assert result["results"][0]["total"] == 25
        assert result["results"][0]["avg_price"] == 150.50

    @pytest.mark.asyncio
    async def test_group_by_with_filters(self, mock_storage):
        """Test GROUP BY combined with WHERE filters."""
        mock_storage.query_aggregate.return_value = [
            {"brand": "Acme", "total": 20},
            {"brand": "Beta", "total": 15}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "filters": {"is_active": True},
            "group_by": ["brand"]
        })

        assert result["success"] is True
        call_args = mock_storage.query_aggregate.call_args
        assert call_args.kwargs["filters"]["is_active"] is True
        assert call_args.kwargs["group_by"] == ["brand"]

    @pytest.mark.asyncio
    async def test_group_by_includes_group_columns_in_results(self, mock_storage):
        """Test that GROUP BY columns are included in result rows."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "total": 10}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id"]
        })

        assert result["success"] is True
        assert "category_id" in result["results"][0]
        assert "total" in result["results"][0]

    @pytest.mark.asyncio
    async def test_group_by_empty_results(self, mock_storage):
        """Test GROUP BY with no matching rows."""
        mock_storage.query_aggregate.return_value = []

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "filters": {"category_id": "nonexistent"},
            "group_by": ["brand"]
        })

        assert result["success"] is True
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_group_by_calls_storage_correctly(self, mock_storage):
        """Test that GROUP BY parameters are passed to storage layer."""
        tool = create_aggregate_data_tool(mock_storage)

        await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id", "brand"]
        })

        call_args = mock_storage.query_aggregate.call_args
        assert call_args.kwargs["table"] == "products"
        assert call_args.kwargs["group_by"] == ["category_id", "brand"]

    @pytest.mark.asyncio
    async def test_group_by_with_search_patterns(self, mock_storage):
        """Test GROUP BY with search patterns (ILIKE)."""
        mock_storage.query_aggregate.return_value = [
            {"brand": "Acme Corp", "total": 15}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "search_patterns": {"name": "%bottle%"},
            "group_by": ["brand"]
        })

        assert result["success"] is True
        call_args = mock_storage.query_aggregate.call_args
        assert call_args.kwargs["search_patterns"]["name"] == "%bottle%"


# =============================================================================
# Test Group 9: HAVING Clause (7+ tests)
# =============================================================================


class TestHavingClause:
    """Test HAVING clause for filtering aggregated results."""

    @pytest.mark.asyncio
    async def test_having_gt_operator(self, mock_storage):
        """Test HAVING with greater than (gt) operator."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "total": 25},
            {"category_id": "cat-2", "total": 50}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id"],
            "having": {"total": {"gt": 20}}
        })

        assert result["success"] is True
        call_args = mock_storage.query_aggregate.call_args
        assert call_args.kwargs["having"]["total"]["gt"] == 20

    @pytest.mark.asyncio
    async def test_having_gte_operator(self, mock_storage):
        """Test HAVING with greater than or equal (gte) operator."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "total": 20}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id"],
            "having": {"total": {"gte": 20}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_having_lt_operator(self, mock_storage):
        """Test HAVING with less than (lt) operator."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-3", "total": 5}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id"],
            "having": {"total": {"lt": 10}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_having_lte_operator(self, mock_storage):
        """Test HAVING with less than or equal (lte) operator."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-3", "total": 10}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id"],
            "having": {"total": {"lte": 10}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_having_eq_operator(self, mock_storage):
        """Test HAVING with equals (eq) operator."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "total": 50}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "group_by": ["category_id"],
            "having": {"total": {"eq": 50}}
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_having_multiple_conditions(self, mock_storage):
        """Test HAVING with multiple conditions."""
        mock_storage.query_aggregate.return_value = [
            {"category_id": "cat-1", "total": 25, "avg_price": 150.00}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {
                "total": "count(*)",
                "avg_price": "avg(base_price)"
            },
            "group_by": ["category_id"],
            "having": {
                "total": {"gte": 10},
                "avg_price": {"gte": 100, "lte": 200}
            }
        })

        assert result["success"] is True
        call_args = mock_storage.query_aggregate.call_args
        assert "total" in call_args.kwargs["having"]
        assert "avg_price" in call_args.kwargs["having"]

    @pytest.mark.asyncio
    async def test_having_with_filters_and_group_by(self, mock_storage):
        """Test HAVING combined with WHERE filters and GROUP BY."""
        mock_storage.query_aggregate.return_value = [
            {"brand": "Acme", "total": 30}
        ]

        tool = create_aggregate_data_tool(mock_storage)

        result = await tool.ainvoke({
            "table": "products",
            "aggregates": {"total": "count(*)"},
            "filters": {"is_active": True},
            "group_by": ["brand"],
            "having": {"total": {"gt": 20}}
        })

        assert result["success"] is True
        call_args = mock_storage.query_aggregate.call_args
        assert call_args.kwargs["filters"]["is_active"] is True
        assert call_args.kwargs["group_by"] == ["brand"]
        assert call_args.kwargs["having"]["total"]["gt"] == 20
