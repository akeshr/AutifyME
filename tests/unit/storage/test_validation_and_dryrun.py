"""
Comprehensive test suite for Phase 1.5: Dry-Run & Validation Operations.

Tests cover:
- validate_entity_data() - Schema validation without execution
- check_constraint_violations() - Pre-flight constraint checking
- preview_write_impact() - Dry-run impact analysis

Test structure:
- Group 1: validate_entity_data - Basic Validation (18 tests)
- Group 2: check_constraint_violations - Constraint Checking (17 tests)
- Group 3: preview_write_impact - Impact Analysis (15 tests)

Total: 50 tests
"""

from unittest.mock import MagicMock, patch

import pytest

from autifyme_agents.integrations.storage.supabase_client import (
    SupabaseStorageClient,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase async client for testing."""
    with patch(
        "autifyme_agents.integrations.storage.supabase_client.create_async_client"
    ) as mock_create:
        mock_client = MagicMock()

        # create_async_client is async
        async def mock_create_client(*args, **kwargs):
            return mock_client

        mock_create.side_effect = mock_create_client

        # Mock table() chain
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        # Default successful response
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.count = 0

        # Make execute() async
        async def mock_execute():
            return mock_response

        mock_table.execute = mock_execute

        # Mock query chain methods (all return mock_table for chaining)
        mock_table.select.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.neq.return_value = mock_table
        mock_table.ilike.return_value = mock_table  # For query_advanced

        # Mock .not_ property for check_existing_values with exclude_ids
        mock_not = MagicMock()
        mock_not.in_.return_value = mock_table
        mock_table.not_ = mock_not

        yield mock_client, mock_create, mock_table, mock_response


# ============================================================================
# Group 1: validate_entity_data - Basic Validation (18 tests)
# ============================================================================


class TestValidateEntityData:
    """Test schema validation without execution."""

    @pytest.mark.asyncio
    async def test_validate_valid_single_entity(self, mock_supabase_client):
        """Test validation passes for valid single entity."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products", {"sku_code": "SKU-001", "name": "Product A"}, operation="insert"
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["entity_count"] == 1

    @pytest.mark.asyncio
    async def test_validate_missing_required_field(self, mock_supabase_client):
        """Test validation fails when required field is missing."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"sku_code": "SKU-001"},  # Missing 'name'
            operation="insert",
        )

        assert result["valid"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["field"] == "name"
        assert "required" in result["errors"][0]["error"].lower()

    @pytest.mark.asyncio
    async def test_validate_empty_required_field(self, mock_supabase_client):
        """Test validation fails when required field is empty string."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"sku_code": "", "name": "Product A"},  # Empty sku_code
            operation="insert",
        )

        assert result["valid"] is False
        assert any(e["field"] == "sku_code" for e in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_null_required_field(self, mock_supabase_client):
        """Test validation fails when required field is None."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products", {"sku_code": None, "name": "Product A"}, operation="insert"
        )

        assert result["valid"] is False
        assert any(e["field"] == "sku_code" for e in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_batch_of_entities(self, mock_supabase_client):
        """Test validation of multiple entities."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            [
                {"sku_code": "SKU-001", "name": "Product A"},
                {"sku_code": "SKU-002", "name": "Product B"},
                {"sku_code": "SKU-003", "name": "Product C"},
            ],
            operation="insert",
        )

        assert result["valid"] is True
        assert result["entity_count"] == 3

    @pytest.mark.asyncio
    async def test_validate_batch_with_errors(self, mock_supabase_client):
        """Test validation identifies errors in batch."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            [
                {"sku_code": "SKU-001", "name": "Product A"},  # Valid
                {"sku_code": "SKU-002"},  # Missing name
                {"name": "Product C"},  # Missing sku_code
            ],
            operation="insert",
        )

        assert result["valid"] is False
        assert len(result["errors"]) == 2
        assert result["entity_count"] == 3

    @pytest.mark.asyncio
    async def test_validate_invalid_price_type(self, mock_supabase_client):
        """Test validation fails for non-numeric price."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"sku_code": "SKU-001", "name": "Product A", "base_price": "invalid"},
            operation="insert",
        )

        assert result["valid"] is False
        assert any(
            e["field"] == "base_price" and "number" in e["error"].lower() for e in result["errors"]
        )

    @pytest.mark.asyncio
    async def test_validate_negative_price_warning(self, mock_supabase_client):
        """Test validation generates warning for negative price."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"sku_code": "SKU-001", "name": "Product A", "base_price": -10.0},
            operation="insert",
        )

        assert result["valid"] is True  # Warning, not error
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["field"] == "base_price"
        assert "negative" in result["warnings"][0]["warning"].lower()

    @pytest.mark.asyncio
    async def test_validate_long_string_warning(self, mock_supabase_client):
        """Test validation warns for very long strings."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        long_description = "A" * 1500

        result = await storage.validate_entity_data(
            "products",
            {"sku_code": "SKU-001", "name": "Product A", "description": long_description},
            operation="insert",
        )

        assert result["valid"] is True
        assert len(result["warnings"]) == 1
        assert "1500" in result["warnings"][0]["warning"]

    @pytest.mark.asyncio
    async def test_validate_update_operation_no_required_fields(self, mock_supabase_client):
        """Test update operation doesn't require all fields."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"base_price": 150.0},  # Only updating price, no sku/name required
            operation="update",
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_validate_upsert_operation(self, mock_supabase_client):
        """Test upsert operation validation."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"base_price": 100.0},  # Partial data ok for upsert
            operation="upsert",
        )

        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_product_families_table(self, mock_supabase_client):
        """Test validation for product_families table."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        # Missing required fields
        result = await storage.validate_entity_data(
            "product_families",
            {"name": "Family A"},  # Missing sku_prefix
            operation="insert",
        )

        assert result["valid"] is False
        assert any(e["field"] == "sku_prefix" for e in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_categories_table(self, mock_supabase_client):
        """Test validation for categories table."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "categories",
            {},  # Missing required 'name'
            operation="insert",
        )

        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_validate_unknown_table(self, mock_supabase_client):
        """Test validation for unknown table (no specific rules)."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "unknown_table", {"any_field": "any_value"}, operation="insert"
        )

        # Should pass as there are no specific validation rules
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_zero_price_valid(self, mock_supabase_client):
        """Test zero price is valid (not negative)."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"sku_code": "SKU-001", "name": "Product A", "base_price": 0},
            operation="insert",
        )

        assert result["valid"] is True
        assert len(result["warnings"]) == 0

    @pytest.mark.asyncio
    async def test_validate_positive_price_valid(self, mock_supabase_client):
        """Test positive price is valid."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"sku_code": "SKU-001", "name": "Product A", "base_price": 99.99},
            operation="insert",
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 0

    @pytest.mark.asyncio
    async def test_validate_multiple_errors_per_entity(self, mock_supabase_client):
        """Test validation captures multiple errors per entity."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            {"base_price": "not-a-number"},  # Missing sku_code, name, invalid price
            operation="insert",
        )

        assert result["valid"] is False
        assert len(result["errors"]) >= 3  # Multiple errors

    @pytest.mark.asyncio
    async def test_validate_entity_index_in_batch_errors(self, mock_supabase_client):
        """Test errors include entity_index for batch validation."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.validate_entity_data(
            "products",
            [
                {"sku_code": "SKU-001", "name": "Product A"},
                {"sku_code": "SKU-002"},  # Error at index 1
                {"sku_code": "SKU-003", "name": "Product C"},
            ],
            operation="insert",
        )

        assert result["valid"] is False
        error_indices = [e["entity_index"] for e in result["errors"]]
        assert 1 in error_indices


# ============================================================================
# Group 2: check_constraint_violations - Constraint Checking (17 tests)
# ============================================================================


class TestCheckConstraintViolations:
    """Test pre-flight constraint checking."""

    @pytest.mark.asyncio
    async def test_check_no_violations(self, mock_supabase_client):
        """Test constraint check passes when no violations."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Mock check_existing_values to return empty (no conflicts)
        mock_response.data = []

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products", {"sku_code": "SKU-NEW", "name": "New Product"}, operation="insert"
        )

        assert result["safe_to_proceed"] is True
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_check_uniqueness_violation(self, mock_supabase_client):
        """Test constraint check detects uniqueness violation."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Mock check_existing_values to return existing SKU
        mock_response.data = [{"sku_code": "SKU-001"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products", {"sku_code": "SKU-001", "name": "Product A"}, operation="insert"
        )

        assert result["safe_to_proceed"] is False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["type"] == "uniqueness"
        assert result["violations"][0]["field"] == "sku_code"

    @pytest.mark.asyncio
    async def test_check_upsert_skips_uniqueness(self, mock_supabase_client):
        """Test upsert operation skips uniqueness checks."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products", {"sku_code": "SKU-001", "name": "Product A"}, operation="upsert"
        )

        # Upsert handles conflicts, so should be safe
        assert result["safe_to_proceed"] is True

    @pytest.mark.asyncio
    async def test_check_with_exclude_ids(self, mock_supabase_client):
        """Test constraint check excludes specified IDs."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Mock returns empty because entity with this ID is excluded
        mock_response.data = []

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products",
            {"sku_code": "SKU-001"},
            operation="update",
            exclude_ids=["uuid-123"],  # Exclude self from check
        )

        assert result["safe_to_proceed"] is True

    @pytest.mark.asyncio
    async def test_check_batch_violations(self, mock_supabase_client):
        """Test constraint check for batch operations."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Mock existing SKU
        mock_response.data = [{"sku_code": "SKU-001"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products",
            [
                {"sku_code": "SKU-001", "name": "Product A"},  # Conflict
                {"sku_code": "SKU-002", "name": "Product B"},  # OK
            ],
            operation="insert",
        )

        assert result["safe_to_proceed"] is False
        assert any(v["value"] == "SKU-001" for v in result["violations"])

    @pytest.mark.asyncio
    async def test_check_duplicate_within_batch(self, mock_supabase_client):
        """Test detection of duplicates within the batch itself."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        mock_response.data = []  # No existing conflicts

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products",
            [
                {"sku_code": "SKU-001", "name": "Product A"},
                {"sku_code": "SKU-001", "name": "Product A Duplicate"},
                {"sku_code": "SKU-002", "name": "Product B"},
            ],
            operation="insert",
        )

        assert result["safe_to_proceed"] is False
        assert any(
            v["type"] == "duplicate_in_batch" and v["value"] == "SKU-001"
            for v in result["violations"]
        )

    @pytest.mark.asyncio
    async def test_check_large_batch_warning(self, mock_supabase_client):
        """Test warning generated for large batches."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        mock_response.data = []

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        # Create batch of 150 entities
        batch_data = [{"sku_code": f"SKU-{i:03d}", "name": f"Product {i}"} for i in range(150)]

        result = await storage.check_constraint_violations(
            "products", batch_data, operation="insert"
        )

        assert result["safe_to_proceed"] is True  # No violations
        assert len(result["warnings"]) >= 1
        assert any(w["type"] == "performance" for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_check_product_families_uniqueness(self, mock_supabase_client):
        """Test uniqueness check for product_families table."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        mock_response.data = [{"sku_prefix": "PRE"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "product_families", {"sku_prefix": "PRE", "name": "Family A"}, operation="insert"
        )

        assert result["safe_to_proceed"] is False
        assert any(v["field"] == "sku_prefix" for v in result["violations"])

    @pytest.mark.asyncio
    async def test_check_categories_slug_uniqueness(self, mock_supabase_client):
        """Test uniqueness check for categories slug."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        mock_response.data = [{"slug": "bottles"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "categories", {"slug": "bottles", "name": "Bottles"}, operation="insert"
        )

        assert result["safe_to_proceed"] is False

    @pytest.mark.asyncio
    async def test_check_variant_axes_uniqueness(self, mock_supabase_client):
        """Test uniqueness check for variant_axes."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        mock_response.data = [{"axis_name": "size"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "variant_axes", {"axis_name": "size"}, operation="insert"
        )

        assert result["safe_to_proceed"] is False

    @pytest.mark.asyncio
    async def test_check_unknown_table_no_constraints(self, mock_supabase_client):
        """Test constraint check for unknown table (no unique fields)."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "unknown_table", {"any_field": "any_value"}, operation="insert"
        )

        # No constraints to check
        assert result["safe_to_proceed"] is True
        assert len(result["checked_constraints"]) == 0

    @pytest.mark.asyncio
    async def test_check_null_unique_field_skipped(self, mock_supabase_client):
        """Test null values in unique fields are skipped."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        mock_response.data = []

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products", {"sku_code": None, "name": "Product"}, operation="insert"
        )

        # Null unique field not checked
        assert result["safe_to_proceed"] is True

    @pytest.mark.asyncio
    async def test_check_multiple_unique_fields(self, mock_supabase_client):
        """Test checking multiple unique fields in single table."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # For products table, only sku_code is unique
        mock_response.data = [{"sku_code": "SKU-001"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products", {"sku_code": "SKU-001", "name": "Product"}, operation="insert"
        )

        assert result["safe_to_proceed"] is False
        assert len(result["checked_constraints"]) >= 1

    @pytest.mark.asyncio
    async def test_check_batch_with_mixed_violations(self, mock_supabase_client):
        """Test batch with both existing and within-batch duplicates."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # SKU-001 exists in database
        mock_response.data = [{"sku_code": "SKU-001"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products",
            [
                {"sku_code": "SKU-001"},  # Exists in DB
                {"sku_code": "SKU-002"},  # New
                {"sku_code": "SKU-002"},  # Duplicate within batch
            ],
            operation="insert",
        )

        assert result["safe_to_proceed"] is False
        # Should have both uniqueness and duplicate_in_batch violations
        violation_types = {v["type"] for v in result["violations"]}
        assert "uniqueness" in violation_types
        assert "duplicate_in_batch" in violation_types

    @pytest.mark.asyncio
    async def test_check_constraint_violations_tracked(self, mock_supabase_client):
        """Test checked_constraints list is populated."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        mock_response.data = []

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products", {"sku_code": "SKU-NEW"}, operation="insert"
        )

        assert len(result["checked_constraints"]) > 0
        assert "sku_code_unique" in result["checked_constraints"]

    @pytest.mark.asyncio
    async def test_check_update_operation_constraint_check(self, mock_supabase_client):
        """Test update operation still checks constraints."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        mock_response.data = [{"sku_code": "SKU-EXISTING"}]

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.check_constraint_violations(
            "products", {"sku_code": "SKU-EXISTING"}, operation="update"
        )

        assert result["safe_to_proceed"] is False


# ============================================================================
# Group 3: preview_write_impact - Impact Analysis (15 tests)
# ============================================================================


class TestPreviewWriteImpact:
    """Test dry-run impact analysis."""

    @pytest.mark.asyncio
    async def test_preview_update_impact_basic(self, mock_supabase_client):
        """Test basic update impact preview."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        # Setup count and query responses
        count_response = MagicMock()
        count_response.count = 10

        sample_response = MagicMock()
        sample_response.data = [
            {"id": f"id{i}", "sku_code": f"SKU-{i:03d}", "name": f"Product {i}"}
            for i in range(1, 6)
        ]

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return count_response  # Test connection
            elif call_count == 2:
                return count_response  # Count query
            else:
                return sample_response  # Sample query

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"is_active": False}, operation="update"
        )

        assert result["affected_count"] == 10
        assert len(result["sample_entities"]) == 5
        assert result["estimated_duration_ms"] >= 20  # 10 entities * 2ms
        assert result["safe_to_proceed"] is True

    @pytest.mark.asyncio
    async def test_preview_no_filters_unsafe(self, mock_supabase_client):
        """Test preview warns when no filters (affects all entities)."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 1000

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return MagicMock(data=[])

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products",
            filters=None,  # No filters!
            operation="delete",
        )

        assert result["safe_to_proceed"] is False
        assert any(w["type"] == "no_filters" for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_preview_empty_filters_unsafe(self, mock_supabase_client):
        """Test preview warns for empty filter dict."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 500

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return MagicMock(data=[])

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products",
            filters={},  # Empty dict
            operation="delete",
        )

        assert result["safe_to_proceed"] is False
        assert any(w["type"] == "no_filters" for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_preview_large_batch_warning(self, mock_supabase_client):
        """Test preview warns for large batch (>100 entities)."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 250

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return MagicMock(data=[])

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"is_active": False}, operation="update"
        )

        assert any(w["type"] == "large_batch" for w in result["warnings"])
        assert "250" in result["warnings"][0]["message"]

    @pytest.mark.asyncio
    async def test_preview_no_entities_affected(self, mock_supabase_client):
        """Test preview when no entities match filters."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 0

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            return count_response

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"sku_code": "NON-EXISTENT"}, operation="delete"
        )

        assert result["affected_count"] == 0
        assert len(result["sample_entities"]) == 0
        assert any(w["type"] == "no_effect" for w in result["warnings"])

    @pytest.mark.asyncio
    async def test_preview_delete_operation(self, mock_supabase_client):
        """Test preview for delete operation."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 5

        sample_response = MagicMock()
        sample_response.data = [{"id": f"id{i}"} for i in range(1, 6)]

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return sample_response

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"is_active": False}, operation="delete"
        )

        assert result["affected_count"] == 5
        assert len(result["sample_entities"]) == 5

    @pytest.mark.asyncio
    async def test_preview_custom_sample_size(self, mock_supabase_client):
        """Test preview with custom sample size."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 100

        sample_response = MagicMock()
        sample_response.data = [{"id": f"id{i}"} for i in range(1, 11)]

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return sample_response

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"category": "bottles"}, operation="update", sample_size=10
        )

        assert len(result["sample_entities"]) == 10

    @pytest.mark.asyncio
    async def test_preview_estimated_duration_scales(self, mock_supabase_client):
        """Test estimated duration scales with affected count."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 500

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return MagicMock(data=[])

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"is_active": True}, operation="update"
        )

        # 500 entities * 2ms = 1000ms
        assert result["estimated_duration_ms"] >= 1000

    @pytest.mark.asyncio
    async def test_preview_minimum_duration(self, mock_supabase_client):
        """Test minimum estimated duration for small operations."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 1

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return MagicMock(data=[{"id": "id1"}])

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"id": "specific-id"}, operation="update"
        )

        # Minimum duration is 10ms
        assert result["estimated_duration_ms"] >= 10

    @pytest.mark.asyncio
    async def test_preview_safe_to_proceed_logic(self, mock_supabase_client):
        """Test safe_to_proceed is True for filtered operations."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 50

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return MagicMock(data=[])

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"category": "test"}, operation="update"
        )

        assert result["safe_to_proceed"] is True

    @pytest.mark.asyncio
    async def test_preview_sample_entities_structure(self, mock_supabase_client):
        """Test sample entities have expected structure."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 10

        sample_response = MagicMock()
        sample_response.data = [
            {"id": "id1", "sku_code": "SKU-001", "name": "Product 1", "price": 100},
            {"id": "id2", "sku_code": "SKU-002", "name": "Product 2", "price": 200},
        ]

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return sample_response

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"category": "test"}, operation="update", sample_size=2
        )

        assert len(result["sample_entities"]) == 2
        assert result["sample_entities"][0]["id"] == "id1"
        assert result["sample_entities"][0]["sku_code"] == "SKU-001"

    @pytest.mark.asyncio
    async def test_preview_multiple_warnings(self, mock_supabase_client):
        """Test preview can generate multiple warnings."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 200

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return MagicMock(data=[])

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products",
            filters={},  # Empty filters
            operation="delete",
        )

        # Should have both no_filters and large_batch warnings
        warning_types = {w["type"] for w in result["warnings"]}
        assert "no_filters" in warning_types
        assert "large_batch" in warning_types

    @pytest.mark.asyncio
    async def test_preview_exact_sample_limit(self, mock_supabase_client):
        """Test preview respects exact sample size limit."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 50

        # Return more than requested, but query should limit
        sample_response = MagicMock()
        sample_response.data = [{"id": f"id{i}"} for i in range(1, 4)]

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return sample_response

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"category": "test"}, operation="update", sample_size=3
        )

        assert len(result["sample_entities"]) == 3

    @pytest.mark.asyncio
    async def test_preview_result_structure_complete(self, mock_supabase_client):
        """Test preview result has all expected fields."""
        mock_client, mock_create, mock_table, mock_response = mock_supabase_client

        count_response = MagicMock()
        count_response.count = 25

        sample_response = MagicMock()
        sample_response.data = [{"id": "id1"}]

        call_count = 0

        async def mock_multi_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return count_response
            return sample_response

        mock_table.execute = mock_multi_execute
        mock_table.count.return_value = mock_table

        storage = SupabaseStorageClient(
            supabase_url="https://test.supabase.co", service_key="test-key"
        )

        result = await storage.preview_write_impact(
            "products", filters={"category": "test"}, operation="update"
        )

        # Verify all expected fields present
        assert "affected_count" in result
        assert "sample_entities" in result
        assert "estimated_duration_ms" in result
        assert "warnings" in result
        assert "safe_to_proceed" in result
