"""Unit tests for schema registry models."""

import json
from pathlib import Path

import pytest

from autifyme_agents.schemas.registry import (
    BusinessRule,
    BusinessRuleTrigger,
    ColumnSchema,
    ColumnType,
    Relationship,
    RelationshipType,
    SchemaRegistry,
    SchemaValidator,
    TableSchema,
    ValidationResult,
)


# =============================================================================
# Test ColumnSchema
# =============================================================================


def test_column_schema_basic():
    """Test basic column schema creation."""
    col = ColumnSchema(
        name="id",
        type=ColumnType.UUID,
        nullable=False,
        primary_key=True
    )

    assert col.name == "id"
    assert col.type == ColumnType.UUID
    assert col.nullable is False
    assert col.primary_key is True


def test_column_schema_with_reference():
    """Test column schema with foreign key reference."""
    col = ColumnSchema(
        name="product_family_id",
        type=ColumnType.UUID,
        nullable=False,
        references="product_families.id"
    )

    assert col.references == "product_families.id"


# =============================================================================
# Test Relationship
# =============================================================================


def test_relationship_parent():
    """Test parent relationship definition."""
    rel = Relationship(
        type=RelationshipType.PARENT,
        target_table="product_families",
        foreign_key="product_family_id",
        cascade_delete=True
    )

    assert rel.type == RelationshipType.PARENT
    assert rel.target_table == "product_families"
    assert rel.foreign_key == "product_family_id"
    assert rel.cascade_delete is True


# =============================================================================
# Test BusinessRule
# =============================================================================


def test_business_rule_creation():
    """Test business rule metadata."""
    rule = BusinessRule(
        rule_type="generate_sku",
        trigger=BusinessRuleTrigger.AFTER_INSERT,
        handler="generate_sku_explosion_for_new_axis",
        parameters={"scope": "new_axis", "warn_threshold": 100}
    )

    assert rule.rule_type == "generate_sku"
    assert rule.trigger == BusinessRuleTrigger.AFTER_INSERT
    assert rule.handler == "generate_sku_explosion_for_new_axis"
    assert rule.parameters["warn_threshold"] == 100
    assert rule.enabled is True


# =============================================================================
# Test TableSchema
# =============================================================================


def test_table_schema_basic():
    """Test basic table schema creation."""
    table = TableSchema(
        name="product_families",
        columns={
            "id": ColumnSchema(
                name="id",
                type=ColumnType.UUID,
                nullable=False,
                primary_key=True
            ),
            "name": ColumnSchema(
                name="name",
                type=ColumnType.VARCHAR,
                max_length=255,
                nullable=False
            )
        },
        primary_key="id"
    )

    assert table.name == "product_families"
    assert len(table.columns) == 2
    assert table.primary_key == "id"


def test_table_schema_get_column():
    """Test getting column by name."""
    table = TableSchema(
        name="test",
        columns={
            "id": ColumnSchema(name="id", type=ColumnType.UUID, nullable=False),
            "name": ColumnSchema(name="name", type=ColumnType.VARCHAR, nullable=False)
        }
    )

    col = table.get_column("name")
    assert col.name == "name"
    assert col.type == ColumnType.VARCHAR

    with pytest.raises(ValueError, match="Column 'nonexistent' not found"):
        table.get_column("nonexistent")


def test_table_schema_get_foreign_keys():
    """Test extracting foreign key relationships."""
    table = TableSchema(
        name="variant_axes",
        columns={},
        relationships=[
            Relationship(
                type=RelationshipType.PARENT,
                target_table="product_families",
                foreign_key="product_family_id"
            )
        ]
    )

    fks = table.get_foreign_keys()
    assert "product_family_id" in fks
    assert fks["product_family_id"].target_table == "product_families"


def test_table_schema_get_required_columns():
    """Test extracting required columns."""
    table = TableSchema(
        name="test",
        columns={
            "id": ColumnSchema(
                name="id",
                type=ColumnType.UUID,
                nullable=False,
                primary_key=True
            ),
            "name": ColumnSchema(
                name="name",
                type=ColumnType.VARCHAR,
                nullable=False
            ),
            "description": ColumnSchema(
                name="description",
                type=ColumnType.TEXT,
                nullable=True
            ),
            "created_at": ColumnSchema(
                name="created_at",
                type=ColumnType.TIMESTAMPTZ,
                nullable=False,
                default="now()"
            )
        }
    )

    required = table.get_required_columns()
    assert "name" in required
    assert "id" not in required  # Primary key excluded
    assert "description" not in required  # Nullable
    assert "created_at" not in required  # Has default


# =============================================================================
# Test SchemaRegistry
# =============================================================================


def test_schema_registry_basic():
    """Test basic schema registry creation."""
    registry = SchemaRegistry(
        version="v1",
        domain="product_catalog",
        tables={
            "product_families": TableSchema(
                name="product_families",
                columns={
                    "id": ColumnSchema(name="id", type=ColumnType.UUID, nullable=False)
                }
            )
        }
    )

    assert registry.version == "v1"
    assert registry.domain == "product_catalog"
    assert "product_families" in registry.tables


def test_schema_registry_get_table():
    """Test getting table by name."""
    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={
            "test_table": TableSchema(name="test_table", columns={})
        }
    )

    table = registry.get_table("test_table")
    assert table.name == "test_table"

    with pytest.raises(ValueError, match="Table 'nonexistent' not found"):
        registry.get_table("nonexistent")


def test_schema_registry_get_table_names():
    """Test getting all table names."""
    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={
            "table1": TableSchema(name="table1", columns={}),
            "table2": TableSchema(name="table2", columns={})
        }
    )

    names = registry.get_table_names()
    assert len(names) == 2
    assert "table1" in names
    assert "table2" in names


def test_schema_registry_validate_table_exists():
    """Test table existence validation."""
    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={
            "existing": TableSchema(name="existing", columns={})
        }
    )

    assert registry.validate_table_exists("existing") is True
    assert registry.validate_table_exists("nonexistent") is False


def test_schema_registry_to_dict():
    """Test serialization to dictionary."""
    registry = SchemaRegistry(
        version="v1",
        domain="test",
        description="Test schema",
        tables={}
    )

    data = registry.to_dict()
    assert data["version"] == "v1"
    assert data["domain"] == "test"
    assert data["description"] == "Test schema"
    assert isinstance(data["tables"], dict)


def test_schema_registry_to_json():
    """Test serialization to JSON."""
    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={}
    )

    json_str = registry.to_json()
    data = json.loads(json_str)
    assert data["version"] == "v1"
    assert data["domain"] == "test"


def test_schema_registry_from_dict():
    """Test deserialization from dictionary."""
    data = {
        "version": "v1",
        "domain": "test",
        "tables": {
            "test_table": {
                "name": "test_table",
                "columns": {}
            }
        }
    }

    registry = SchemaRegistry.from_dict(data)
    assert registry.version == "v1"
    assert registry.domain == "test"
    assert "test_table" in registry.tables


def test_schema_registry_from_json():
    """Test deserialization from JSON."""
    json_str = """
    {
        "version": "v1",
        "domain": "test",
        "tables": {
            "test_table": {
                "name": "test_table",
                "columns": {}
            }
        }
    }
    """

    registry = SchemaRegistry.from_json(json_str)
    assert registry.version == "v1"
    assert registry.domain == "test"


def test_schema_registry_save_and_load(tmp_path):
    """Test saving to and loading from file."""
    schema_file = tmp_path / "test_schema.json"

    # Create and save
    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={}
    )
    registry.save_to_file(schema_file)

    # Load
    loaded_registry = SchemaRegistry.load_from_file(schema_file)
    assert loaded_registry.version == "v1"
    assert loaded_registry.domain == "test"


def test_schema_registry_evolve():
    """Test schema evolution."""
    v1 = SchemaRegistry(
        version="v1",
        domain="test",
        tables={
            "table1": TableSchema(name="table1", columns={})
        }
    )

    # Evolve to v2 - add table, remove table, update table
    v2 = v1.evolve(
        new_version="v2",
        add_tables=[TableSchema(name="table2", columns={})],
        remove_tables=["table1"],
        description="Added table2, removed table1"
    )

    assert v2.version == "v2"
    assert "table2" in v2.tables
    assert "table1" not in v2.tables
    assert "Added table2" in v2.description


# =============================================================================
# Test SchemaValidator
# =============================================================================


def test_validation_result_basic():
    """Test validation result creation."""
    result = ValidationResult(valid=True)
    assert result.valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 0


def test_validation_result_add_error():
    """Test adding validation error."""
    result = ValidationResult(valid=True)
    result.add_error("Test error")

    assert result.valid is False
    assert len(result.errors) == 1
    assert result.errors[0] == "Test error"


def test_validation_result_add_warning():
    """Test adding validation warning."""
    result = ValidationResult(valid=True)
    result.add_warning("Test warning")

    assert result.valid is True
    assert len(result.warnings) == 1
    assert result.warnings[0] == "Test warning"


def test_schema_validator_validate_table_exists():
    """Test table existence validation."""
    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={
            "existing": TableSchema(name="existing", columns={})
        }
    )

    validator = SchemaValidator(registry)

    result = validator.validate_table_exists("existing")
    assert result.valid is True

    result = validator.validate_table_exists("nonexistent")
    assert result.valid is False
    assert len(result.errors) == 1


def test_schema_validator_validate_entity_missing_required():
    """Test entity validation with missing required columns."""
    table = TableSchema(
        name="test",
        columns={
            "id": ColumnSchema(
                name="id",
                type=ColumnType.UUID,
                nullable=False,
                primary_key=True
            ),
            "name": ColumnSchema(
                name="name",
                type=ColumnType.VARCHAR,
                nullable=False
            )
        }
    )

    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={"test": table}
    )

    validator = SchemaValidator(registry)

    # Missing required 'name' column
    entity = {"id": "123"}
    result = validator.validate_entity("test", entity)

    assert result.valid is False
    assert len(result.errors) > 0
    assert "name" in result.errors[0]


def test_schema_validator_validate_entity_unknown_columns():
    """Test entity validation with unknown columns."""
    table = TableSchema(
        name="test",
        columns={
            "id": ColumnSchema(name="id", type=ColumnType.UUID, nullable=False)
        }
    )

    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={"test": table}
    )

    validator = SchemaValidator(registry)

    # Unknown column 'unknown'
    entity = {"id": "123", "unknown": "value"}
    result = validator.validate_entity("test", entity)

    assert result.valid is True  # Valid but with warnings
    assert len(result.warnings) > 0
    assert "unknown" in result.warnings[0]


def test_schema_validator_validate_entity_null_violation():
    """Test entity validation with NULL constraint violation."""
    table = TableSchema(
        name="test",
        columns={
            "name": ColumnSchema(name="name", type=ColumnType.VARCHAR, nullable=False)
        }
    )

    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={"test": table}
    )

    validator = SchemaValidator(registry)

    # NULL value for non-nullable column
    entity = {"name": None}
    result = validator.validate_entity("test", entity)

    assert result.valid is False
    assert len(result.errors) > 0


def test_schema_validator_validate_operation():
    """Test operation validation."""
    table = TableSchema(
        name="test",
        columns={
            "name": ColumnSchema(name="name", type=ColumnType.VARCHAR, nullable=False)
        }
    )

    registry = SchemaRegistry(
        version="v1",
        domain="test",
        tables={"test": table}
    )

    validator = SchemaValidator(registry)

    # Valid operation
    operation = {
        "table": "test",
        "op_type": "insert",
        "new_entities": [{"name": "value"}]
    }
    result = validator.validate_operation(operation)
    assert result.valid is True

    # Invalid operation - missing table
    operation = {"op_type": "insert"}
    result = validator.validate_operation(operation)
    assert result.valid is False


# =============================================================================
# Integration Test - Load Product Catalog Schema
# =============================================================================


def test_load_product_catalog_v1():
    """Test loading actual product catalog v1 schema."""
    # This tests the real schema file exists and is valid
    schema_path = Path(__file__).parent.parent.parent.parent / \
                  "agents/src/autifyme_agents/schemas/registry/versions/product_catalog/v1.json"

    if not schema_path.exists():
        pytest.skip("Product catalog v1 schema not found")

    registry = SchemaRegistry.load_from_file(schema_path)

    assert registry.version == "v1"
    assert registry.domain == "product_catalog"

    # Verify all 9 tables exist
    expected_tables = [
        "product_families",
        "variant_axes",
        "variant_values",
        "products",
        "product_variant_values",
        "product_family_industries",
        "customer_segments",
        "product_images",
        "marketing_content"
    ]

    for table_name in expected_tables:
        assert table_name in registry.tables, f"Table '{table_name}' not found"

    # Verify product_families has expected columns
    product_families = registry.get_table("product_families")
    assert "id" in product_families.columns
    assert "name" in product_families.columns
    assert "base_price" in product_families.columns

    # Verify variant_axes has foreign key to product_families
    variant_axes = registry.get_table("variant_axes")
    fks = variant_axes.get_foreign_keys()
    assert "product_family_id" in fks
    assert fks["product_family_id"].target_table == "product_families"
