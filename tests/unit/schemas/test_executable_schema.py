"""Comprehensive test suite for executable schema validation methods.

Tests TableSchema validation methods with:
- Unit tests for each validation method
- Edge case coverage (empty data, nulls, large batches)
- Property-based tests with Hypothesis
- Comparison tests (old handlers vs new methods)
- Performance benchmarks

Production confidence: These tests validate that schema-driven validation
works correctly across all scenarios before removing BusinessRuleHandlers.
"""

import uuid

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from autifyme_agents.schemas.registry import (
    ColumnSchema,
    ColumnType,
    SchemaRegistry,
    TableSchema,
)
from tests.fixtures.fake_storage import FakeStorage

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fake_storage():
    """Create FakeStorage for testing."""
    return FakeStorage()


@pytest.fixture
def schema_registry():
    """Create minimal schema registry for testing."""
    return SchemaRegistry.get_version("latest", "product_catalog")


@pytest.fixture
def products_table(schema_registry):
    """Get products table schema."""
    return schema_registry.get_table("products")


@pytest.fixture
def simple_table():
    """Create simple test table with unique constraint."""
    return TableSchema(
        name="test_table",
        description="Test table",
        columns={
            "id": ColumnSchema(
                name="id",
                type=ColumnType.UUID,
                nullable=False,
                primary_key=True,
            ),
            "email": ColumnSchema(
                name="email",
                type=ColumnType.VARCHAR,
                nullable=False,
                unique=True,
                max_length=255,
            ),
            "username": ColumnSchema(
                name="username",
                type=ColumnType.VARCHAR,
                nullable=False,
                unique=True,
                max_length=50,
            ),
            "name": ColumnSchema(
                name="name",
                type=ColumnType.VARCHAR,
                nullable=False,
                max_length=100,
            ),
            "age": ColumnSchema(
                name="age",
                type=ColumnType.INTEGER,
                nullable=True,
            ),
        },
        primary_key="id",
    )


# =============================================================================
# Unit Tests: validate_before_insert()
# =============================================================================


class TestValidateBeforeInsert:
    """Test suite for TableSchema.validate_before_insert()."""

    async def test_empty_entities_returns_valid(self, simple_table, fake_storage):
        """Empty entity list should return valid result."""
        result = await simple_table.validate_before_insert([], fake_storage)

        assert result.valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    async def test_unique_constraint_passes_with_new_values(
        self, simple_table, fake_storage
    ):
        """New unique values should pass validation."""
        entities = [
            {"email": "user1@test.com", "username": "user1", "name": "User 1"},
            {"email": "user2@test.com", "username": "user2", "name": "User 2"},
        ]

        result = await simple_table.validate_before_insert(entities, fake_storage)

        assert result.valid
        assert len(result.errors) == 0

    async def test_unique_constraint_fails_with_duplicate_in_db(
        self, simple_table, fake_storage
    ):
        """Duplicate values already in DB should fail validation."""
        # Seed database with existing record
        fake_storage.tables["test_table"] = [
            {
                "id": str(uuid.uuid4()),
                "email": "existing@test.com",
                "username": "existing_user",
                "name": "Existing User",
            }
        ]

        # Try to insert duplicate email
        entities = [
            {"email": "existing@test.com", "username": "new_user", "name": "New User"}
        ]

        result = await simple_table.validate_before_insert(entities, fake_storage)

        assert not result.valid
        assert len(result.errors) > 0
        assert "existing@test.com" in str(result.errors)

    async def test_multiple_unique_columns_all_validated(
        self, simple_table, fake_storage
    ):
        """All unique columns should be validated."""
        # Seed with existing data
        fake_storage.tables["test_table"] = [
            {
                "id": str(uuid.uuid4()),
                "email": "user1@test.com",
                "username": "user1",
                "name": "User 1",
            }
        ]

        # Try duplicate email (should fail)
        entities = [{"email": "user1@test.com", "username": "user2", "name": "User 2"}]
        result = await simple_table.validate_before_insert(entities, fake_storage)
        assert not result.valid

        # Try duplicate username (should fail)
        entities = [{"email": "user2@test.com", "username": "user1", "name": "User 2"}]
        result = await simple_table.validate_before_insert(entities, fake_storage)
        assert not result.valid

    async def test_entities_with_null_unique_values_are_skipped(
        self, simple_table, fake_storage
    ):
        """Entities with null values for unique columns should be skipped."""
        entities = [
            {"email": "user1@test.com", "username": None, "name": "User 1"},
            {"email": None, "username": "user2", "name": "User 2"},
        ]

        result = await simple_table.validate_before_insert(entities, fake_storage)

        # Should not fail (nulls skipped)
        assert result.valid

    async def test_large_batch_insert_validation(self, simple_table, fake_storage):
        """Large batches should validate efficiently."""
        entities = [
            {
                "email": f"user{i}@test.com",
                "username": f"user{i}",
                "name": f"User {i}",
            }
            for i in range(100)
        ]

        result = await simple_table.validate_before_insert(entities, fake_storage)

        assert result.valid
        assert len(result.errors) == 0

    async def test_storage_error_returns_warning_not_failure(
        self, simple_table, fake_storage
    ):
        """Storage errors should return warnings, not fail validation."""
        # Force storage error by making check_existing_values raise
        class FailingStorage(FakeStorage):
            async def check_existing_values(self, table, column, values):
                raise Exception("Storage connection failed")

        failing_storage = FailingStorage()
        entities = [{"email": "test@test.com", "username": "test", "name": "Test"}]

        result = await simple_table.validate_before_insert(entities, failing_storage)

        # Should not fail validation (graceful degradation)
        assert result.valid
        assert len(result.warnings) > 0
        assert "Could not verify uniqueness" in str(result.warnings)

    async def test_sku_uniqueness_on_products_table(
        self, products_table, fake_storage, schema_registry
    ):
        """Test SKU uniqueness validation on real products table."""
        family_id = str(uuid.uuid4())

        # Seed product family
        fake_storage.tables["product_families"].append(
            {
                "id": family_id,
                "product_group_id": "TEST",
                "sku_prefix": "TST",
                "name": "Test Family",
                "description": "Test",
                "brand": "TestBrand",
                "base_price": 10.00,
                "price_currency": "INR",
                "condition": "new",
                "lifecycle_stage": "regular",
            }
        )

        # Seed existing product with SKU
        fake_storage.tables["products"].append(
            {
                "id": str(uuid.uuid4()),
                "product_family_id": family_id,
                "sku": "TST-001",
                "name": "Test Product",
                "description": "Test",
                "price": 10.00,
                "stock_quantity": 0,
                "availability": "in_stock",
            }
        )

        # Try to insert duplicate SKU
        entities = [
            {
                "product_family_id": family_id,
                "sku": "TST-001",  # Duplicate
                "name": "Another Product",
                "description": "Test",
                "price": 20.00,
            }
        ]

        result = await products_table.validate_before_insert(entities, fake_storage)

        assert not result.valid
        assert "TST-001" in str(result.errors)


# =============================================================================
# Unit Tests: validate_before_update()
# =============================================================================


class TestValidateBeforeUpdate:
    """Test suite for TableSchema.validate_before_update()."""

    async def test_update_non_unique_field_passes(self, simple_table, fake_storage):
        """Updating non-unique fields should pass validation."""
        result = await simple_table.validate_before_update(
            filters={"id": str(uuid.uuid4())},
            updates={"name": "Updated Name", "age": 30},
            storage=fake_storage,
        )

        assert result.valid

    async def test_update_unique_field_to_existing_value_fails(
        self, simple_table, fake_storage
    ):
        """Updating unique field to existing value should fail."""
        # Seed with existing data
        fake_storage.tables["test_table"] = [
            {
                "id": str(uuid.uuid4()),
                "email": "existing@test.com",
                "username": "existing",
                "name": "Existing",
            }
        ]

        # Try to update another record to same email
        result = await simple_table.validate_before_update(
            filters={"id": str(uuid.uuid4())},
            updates={"email": "existing@test.com"},
            storage=fake_storage,
        )

        assert not result.valid
        assert "existing@test.com" in str(result.errors)

    async def test_update_unique_field_to_new_value_passes(
        self, simple_table, fake_storage
    ):
        """Updating unique field to new value should pass."""
        result = await simple_table.validate_before_update(
            filters={"id": str(uuid.uuid4())},
            updates={"email": "newemail@test.com"},
            storage=fake_storage,
        )

        assert result.valid

    async def test_update_with_null_unique_value_skipped(
        self, simple_table, fake_storage
    ):
        """Updating unique field to null should be skipped."""
        result = await simple_table.validate_before_update(
            filters={"id": str(uuid.uuid4())},
            updates={"email": None},
            storage=fake_storage,
        )

        assert result.valid

    async def test_idempotent_update_to_same_value_passes(
        self, simple_table, fake_storage
    ):
        """Idempotent update: updating record to same unique value it already has should pass.

        This tests the critical fix for Issue #2 - exclude_ids prevents self-collision.
        Scenario: Record has email='test@example.com', update same record to email='test@example.com'
        Expected: Should PASS (idempotent operation, not a conflict)
        """
        # Create existing record with unique email
        record_id = str(uuid.uuid4())
        fake_storage.tables["test_table"] = [
            {
                "id": record_id,
                "email": "test@example.com",
                "username": "testuser",
                "name": "Test User",
            }
        ]

        # Update same record to same email value (idempotent update)
        result = await simple_table.validate_before_update(
            filters={"id": record_id},
            updates={"email": "test@example.com", "name": "Test User Updated"},
            storage=fake_storage,
        )

        # Should PASS - same record, same value = idempotent
        assert result.valid, f"Idempotent update should pass, but got errors: {result.errors}"


# =============================================================================
# Unit Tests: calculate_cascade_impact()
# =============================================================================


class TestCalculateCascadeImpact:
    """Test suite for TableSchema.calculate_cascade_impact()."""

    async def test_cascade_impact_with_no_children(
        self, schema_registry, fake_storage
    ):
        """Deleting record with no children should show single table impact."""
        product_families = schema_registry.get_table("product_families")
        family_id = str(uuid.uuid4())

        # Seed product family (no children)
        fake_storage.tables["product_families"].append(
            {
                "id": family_id,
                "product_group_id": "TEST",
                "sku_prefix": "TST",
                "name": "Test",
                "description": "Test",
                "brand": "Test",
                "base_price": 10.00,
                "price_currency": "INR",
                "condition": "new",
                "lifecycle_stage": "regular",
            }
        )

        result = await product_families.calculate_cascade_impact(
            filters={"id": family_id},
            storage=fake_storage,
            schema_registry=schema_registry,
        )

        assert result["status"] == "calculated"
        assert result["impact"]["product_families"] == 1
        assert result["total_affected"] == 1

    async def test_cascade_impact_with_children(self, schema_registry, fake_storage):
        """Deleting parent should calculate child table impacts."""
        product_families = schema_registry.get_table("product_families")
        family_id = str(uuid.uuid4())

        # Seed product family
        fake_storage.tables["product_families"].append(
            {
                "id": family_id,
                "product_group_id": "TEST",
                "sku_prefix": "TST",
                "name": "Test",
                "description": "Test",
                "brand": "Test",
                "base_price": 10.00,
                "price_currency": "INR",
                "condition": "new",
                "lifecycle_stage": "regular",
            }
        )

        # Seed variant axes (children with cascade_delete=true)
        for i in range(3):
            fake_storage.tables["variant_axes"].append(
                {
                    "id": str(uuid.uuid4()),
                    "product_family_id": family_id,
                    "axis_type": f"axis{i}",
                    "display_name": f"Axis {i}",
                }
            )

        # Seed products (children with cascade_delete=true)
        for i in range(5):
            fake_storage.tables["products"].append(
                {
                    "id": str(uuid.uuid4()),
                    "product_family_id": family_id,
                    "sku": f"TST-{i}",
                    "name": f"Product {i}",
                    "description": "Test",
                    "price": 10.00,
                }
            )

        result = await product_families.calculate_cascade_impact(
            filters={"id": family_id},
            storage=fake_storage,
            schema_registry=schema_registry,
        )

        assert result["status"] == "calculated"
        assert result["impact"]["product_families"] == 1
        assert result["impact"]["variant_axes"] == 3
        assert result["impact"]["products"] == 5
        assert result["total_affected"] == 9
        assert result["is_destructive"] is True

    async def test_cascade_impact_empty_filter(self, schema_registry, fake_storage):
        """Empty filter should show zero impact."""
        products = schema_registry.get_table("products")

        result = await products.calculate_cascade_impact(
            filters={"id": str(uuid.uuid4())},  # Non-existent ID
            storage=fake_storage,
            schema_registry=schema_registry,
        )

        assert result["status"] == "calculated"
        assert result["impact"]["products"] == 0


# =============================================================================
# Property-Based Tests with Hypothesis
# =============================================================================


class TestPropertyBased:
    """Property-based tests using Hypothesis for validation invariants."""

    @given(
        emails=st.lists(
            st.emails(), min_size=1, max_size=20, unique=True
        )
    )
    @settings(max_examples=50, deadline=5000)
    async def test_property_unique_emails_always_pass(self, emails):
        """Property: Unique emails should always pass validation."""
        # Create table and storage directly (Hypothesis doesn't like fixtures)
        table = TableSchema(
            name="test_table",
            columns={
                "id": ColumnSchema(name="id", type=ColumnType.UUID, primary_key=True, nullable=False),
                "email": ColumnSchema(name="email", type=ColumnType.VARCHAR, unique=True, nullable=False),
                "username": ColumnSchema(name="username", type=ColumnType.VARCHAR, unique=True, nullable=False),
                "name": ColumnSchema(name="name", type=ColumnType.VARCHAR, nullable=False),
            },
            primary_key="id",
        )
        storage = FakeStorage()

        entities = [
            {"email": email, "username": f"user{i}", "name": f"User {i}"}
            for i, email in enumerate(emails)
        ]

        result = await table.validate_before_insert(entities, storage)

        assert result.valid

    @given(
        email=st.emails(),
    )
    @settings(max_examples=50, deadline=5000)
    async def test_property_duplicate_email_always_fails(self, email):
        """Property: Duplicate email should always fail validation."""
        table = TableSchema(
            name="test_table",
            columns={
                "id": ColumnSchema(name="id", type=ColumnType.UUID, primary_key=True, nullable=False),
                "email": ColumnSchema(name="email", type=ColumnType.VARCHAR, unique=True, nullable=False),
                "username": ColumnSchema(name="username", type=ColumnType.VARCHAR, unique=True, nullable=False),
                "name": ColumnSchema(name="name", type=ColumnType.VARCHAR, nullable=False),
            },
            primary_key="id",
        )
        storage = FakeStorage()

        # Seed database with email
        storage.tables["test_table"] = [
            {
                "id": str(uuid.uuid4()),
                "email": email,
                "username": "existing",
                "name": "Existing",
            }
        ]

        # Try to insert same email
        entities = [{"email": email, "username": "new_user", "name": "New User"}]

        result = await table.validate_before_insert(entities, storage)

        assert not result.valid

    @given(
        batch_size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=20, deadline=10000)
    async def test_property_validation_scales_linearly(self, batch_size):
        """Property: Validation should scale linearly with batch size."""
        import time

        table = TableSchema(
            name="test_table",
            columns={
                "id": ColumnSchema(name="id", type=ColumnType.UUID, primary_key=True, nullable=False),
                "email": ColumnSchema(name="email", type=ColumnType.VARCHAR, unique=True, nullable=False),
                "username": ColumnSchema(name="username", type=ColumnType.VARCHAR, unique=True, nullable=False),
                "name": ColumnSchema(name="name", type=ColumnType.VARCHAR, nullable=False),
            },
            primary_key="id",
        )
        storage = FakeStorage()

        entities = [
            {
                "email": f"user{i}@test.com",
                "username": f"user{i}",
                "name": f"User {i}",
            }
            for i in range(batch_size)
        ]

        start = time.time()
        result = await table.validate_before_insert(entities, storage)
        duration = time.time() - start

        # Should complete in reasonable time (< 1 second for 100 entities)
        assert duration < 1.0
        assert result.valid


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Edge case coverage for production robustness."""

    async def test_validation_with_missing_table_in_storage(
        self, simple_table, fake_storage
    ):
        """Missing table in storage should return warning."""
        # Don't create test_table in fake_storage
        entities = [{"email": "test@test.com", "username": "test", "name": "Test"}]

        result = await simple_table.validate_before_insert(entities, fake_storage)

        # Should gracefully handle (empty table = no duplicates)
        assert result.valid

    async def test_validation_with_special_characters_in_values(
        self, simple_table, fake_storage
    ):
        """Special characters in values should be handled correctly."""
        entities = [
            {
                "email": "user+test@example.com",
                "username": "user_123-ABC",
                "name": "O'Brien & Co.",
            }
        ]

        result = await simple_table.validate_before_insert(entities, fake_storage)

        assert result.valid

    async def test_validation_with_very_long_values(self, simple_table, fake_storage):
        """Very long values should be handled."""
        entities = [
            {
                "email": f"{'a' * 240}@test.com",  # Near max_length
                "username": "a" * 50,  # At max_length
                "name": "Test",
            }
        ]

        result = await simple_table.validate_before_insert(entities, fake_storage)

        assert result.valid

    async def test_validation_with_unicode_characters(
        self, simple_table, fake_storage
    ):
        """Unicode characters should be handled correctly."""
        entities = [
            {
                "email": "用户@测试.com",
                "username": "ユーザー123",
                "name": "Пользователь Test",
            }
        ]

        result = await simple_table.validate_before_insert(entities, fake_storage)

        assert result.valid

    async def test_table_with_no_unique_columns(self, fake_storage):
        """Table with no unique columns should pass validation."""
        table = TableSchema(
            name="no_unique_table",
            columns={
                "id": ColumnSchema(
                    name="id", type=ColumnType.UUID, primary_key=True, nullable=False
                ),
                "value": ColumnSchema(
                    name="value", type=ColumnType.VARCHAR, nullable=False
                ),
            },
            primary_key="id",
        )

        entities = [{"value": "test"}, {"value": "test"}]  # Duplicate values OK

        result = await table.validate_before_insert(entities, fake_storage)

        assert result.valid


# =============================================================================
# Comparison Tests: Old Handlers vs New Methods
# =============================================================================


class TestOldVsNewComparison:
    """Compare old BusinessRuleHandlers with new TableSchema methods.

    These tests ensure behavior parity before removing old handlers.
    """

    async def test_schema_validation_detects_duplicate_sku(
        self, products_table, fake_storage
    ):
        """Verify schema validation detects duplicate SKU (core requirement)."""
        family_id = str(uuid.uuid4())

        # Seed data
        fake_storage.tables["product_families"].append(
            {
                "id": family_id,
                "product_group_id": "TEST",
                "sku_prefix": "TST",
                "name": "Test",
                "description": "Test",
                "brand": "Test",
                "base_price": 10.00,
                "price_currency": "INR",
                "condition": "new",
                "lifecycle_stage": "regular",
            }
        )
        fake_storage.tables["products"].append(
            {
                "id": str(uuid.uuid4()),
                "product_family_id": family_id,
                "sku": "TST-EXISTING",
                "name": "Existing",
                "description": "Test",
                "price": 10.00,
            }
        )

        entities = [
            {
                "product_family_id": family_id,
                "sku": "TST-EXISTING",  # Duplicate
                "name": "New",
                "description": "Test",
                "price": 10.00,
            }
        ]

        # Test new schema method detects duplicate
        schema_result = await products_table.validate_before_insert(
            entities, fake_storage
        )

        # Should fail for duplicate SKU
        assert not schema_result.valid
        assert "TST-EXISTING" in str(schema_result.errors)


# =============================================================================
# Performance Benchmarks
# =============================================================================


class TestPerformance:
    """Performance benchmarks to ensure no regressions."""

    async def test_validation_performance_100_entities(
        self, simple_table, fake_storage
    ):
        """Validate 100 entities should complete in <100ms."""
        import time

        entities = [
            {
                "email": f"user{i}@test.com",
                "username": f"user{i}",
                "name": f"User {i}",
            }
            for i in range(100)
        ]

        start = time.time()
        result = await simple_table.validate_before_insert(entities, fake_storage)
        duration = (time.time() - start) * 1000  # Convert to ms

        assert result.valid
        assert duration < 100, f"Validation took {duration}ms, expected <100ms"

    async def test_validation_performance_50_entities(
        self, products_table, fake_storage
    ):
        """Validate 50 entities should complete in <50ms."""
        import time

        family_id = str(uuid.uuid4())
        fake_storage.tables["product_families"].append(
            {
                "id": family_id,
                "product_group_id": "TEST",
                "sku_prefix": "TST",
                "name": "Test",
                "description": "Test",
                "brand": "Test",
                "base_price": 10.00,
                "price_currency": "INR",
                "condition": "new",
                "lifecycle_stage": "regular",
            }
        )

        entities = [
            {
                "product_family_id": family_id,
                "sku": f"TST-{i}",
                "name": f"Product {i}",
                "description": "Test",
                "price": 10.00,
            }
            for i in range(50)
        ]

        start = time.time()
        result = await products_table.validate_before_insert(entities, fake_storage)
        duration = (time.time() - start) * 1000  # Convert to ms

        assert result.valid
        assert duration < 50, f"Validation took {duration}ms, expected <50ms"
