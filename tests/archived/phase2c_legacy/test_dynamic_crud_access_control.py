"""
Unit tests for dynamic CRUD access control.

Tests the operation-scoped tool factory and dynamic schema generation.
Verifies that LLMs see correct JSON schemas for different operation types.
"""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from autifyme_agents.tools.universal_crud_tool import (
    _create_operation_input_schema,
    _generate_tool_description,
    _generate_tool_name,
    create_database_tool,
)

# =============================================================================
# Dynamic Schema Generation Tests
# =============================================================================


class TestSchemaGeneration:
    """Test dynamic Pydantic schema generation for different operations."""

    def test_read_only_schema_fields(self):
        """Read-only schema should have query_filter, not change_spec."""
        read_schema = _create_operation_input_schema(["read"])

        # Verify field presence
        assert "user_request_summary" in read_schema.model_fields
        assert "reasoning" in read_schema.model_fields
        assert "intent_type" in read_schema.model_fields
        assert "query_filter" in read_schema.model_fields
        assert "execution_plan" in read_schema.model_fields
        assert "specialist_name" in read_schema.model_fields
        assert "schema_version" in read_schema.model_fields

        # Verify mutation fields absent
        assert "change_spec" not in read_schema.model_fields
        assert "impact_analysis" not in read_schema.model_fields

    def test_full_crud_schema_fields(self):
        """Full CRUD schema should have change_spec and impact_analysis."""
        crud_schema = _create_operation_input_schema(["create", "read", "update", "delete"])

        # Verify all fields present
        assert "user_request_summary" in crud_schema.model_fields
        assert "reasoning" in crud_schema.model_fields
        assert "intent_type" in crud_schema.model_fields
        assert "change_spec" in crud_schema.model_fields
        assert "impact_analysis" in crud_schema.model_fields
        assert "execution_plan" in crud_schema.model_fields
        assert "specialist_name" in crud_schema.model_fields
        assert "schema_version" in crud_schema.model_fields

        # Verify read-only field absent
        assert "query_filter" not in crud_schema.model_fields

    def test_mixed_operations_schema(self):
        """Mixed operations schema should have mutation fields."""
        mixed_schema = _create_operation_input_schema(["read", "update"])

        # Should have mutation fields (for update)
        assert "change_spec" in mixed_schema.model_fields
        assert "impact_analysis" in mixed_schema.model_fields
        assert "execution_plan" in mixed_schema.model_fields

        # Should not have read-only simplified structure
        assert "query_filter" not in mixed_schema.model_fields

    def test_schema_names(self):
        """Schema class names should be descriptive."""
        read_schema = _create_operation_input_schema(["read"])
        assert read_schema.__name__ == "ReadOperationInput"

        crud_schema = _create_operation_input_schema(["create", "read", "update", "delete"])
        assert crud_schema.__name__ == "FullCrudOperationInput"

        update_schema = _create_operation_input_schema(["update"])
        assert update_schema.__name__ == "UpdateOperationInput"

    def test_schema_config(self):
        """Schemas should have extra='forbid' config."""
        read_schema = _create_operation_input_schema(["read"])

        # Verify config
        assert read_schema.model_config.get("extra") == "forbid"

    def test_read_schema_field_descriptions(self):
        """Read-only schema should have operation-specific descriptions."""
        read_schema = _create_operation_input_schema(["read"])

        # Check intent_type description mentions read-only
        intent_desc = read_schema.model_fields["intent_type"].description
        assert "read" in intent_desc.lower()

        # Check execution_plan description mentions read-only
        plan_desc = read_schema.model_fields["execution_plan"].description
        assert "read-only" in plan_desc.lower() or "query" in plan_desc.lower()

    def test_crud_schema_field_descriptions(self):
        """CRUD schema should have mutation-aware descriptions."""
        crud_schema = _create_operation_input_schema(["create", "read", "update", "delete"])

        # Check intent_type description lists all operations
        intent_desc = crud_schema.model_fields["intent_type"].description
        assert "create" in intent_desc.lower()
        assert "read" in intent_desc.lower()
        assert "update" in intent_desc.lower()
        assert "delete" in intent_desc.lower()

        # Check impact_analysis description mentions HITL
        impact_desc = crud_schema.model_fields["impact_analysis"].description
        assert "HITL" in impact_desc or "approval" in impact_desc.lower()

    def test_schema_required_fields(self):
        """Verify required vs optional fields."""
        read_schema = _create_operation_input_schema(["read"])

        # Required fields
        required_fields = [
            name for name, field in read_schema.model_fields.items() if field.is_required()
        ]
        assert "user_request_summary" in required_fields
        assert "reasoning" in required_fields
        assert "intent_type" in required_fields
        assert "execution_plan" in required_fields

        # Optional fields with sensible defaults
        optional_fields = [
            name for name, field in read_schema.model_fields.items() if not field.is_required()
        ]
        assert "query_filter" in optional_fields  # Has default={}
        assert "specialist_name" in optional_fields  # Has default=None
        assert "schema_version" in optional_fields  # Has default="v1"

    def test_schema_instantiation(self):
        """Schemas should be instantiable with correct parameters."""
        read_schema = _create_operation_input_schema(["read"])

        # Valid instantiation
        instance = read_schema(
            user_request_summary="Find all products",
            reasoning="User wants to browse",
            intent_type="read",
            execution_plan={"steps": []},
        )
        assert instance.user_request_summary == "Find all products"
        assert instance.query_filter == {}  # Default value
        assert instance.schema_version == "v1"  # Default value

    def test_schema_validation_rejects_extra_fields(self):
        """Schema should reject unexpected fields (extra='forbid')."""
        read_schema = _create_operation_input_schema(["read"])

        with pytest.raises(ValidationError) as exc_info:
            read_schema(
                user_request_summary="Test",
                reasoning="Test",
                intent_type="read",
                execution_plan={"steps": []},
                invalid_field="should fail",  # Extra field
            )

        assert "invalid_field" in str(exc_info.value)

    def test_json_schema_output(self):
        """JSON Schema output should only include defined fields."""
        read_schema = _create_operation_input_schema(["read"])

        json_schema = read_schema.model_json_schema()

        # Verify properties match model fields
        assert set(json_schema["properties"].keys()) == set(read_schema.model_fields.keys())

        # Verify additionalProperties is false
        assert not json_schema.get("additionalProperties")

        # Verify query_filter has default
        assert json_schema["properties"]["query_filter"].get("default") == {}


# =============================================================================
# Tool Description Generation Tests
# =============================================================================


class TestDescriptionGeneration:
    """Test tool description generation for different operation types."""

    def test_read_only_description(self):
        """Read-only description should emphasize query operations."""
        desc = _generate_tool_description(["read"])

        assert "read-only" in desc.lower() or "query" in desc.lower()
        assert "without modifications" in desc.lower() or "no mutations" in desc.lower()

    def test_full_crud_description(self):
        """Full CRUD description should mention all operations."""
        desc = _generate_tool_description(["create", "read", "update", "delete"])

        assert "full crud" in desc.lower() or "all operations" in desc.lower()
        assert "create" in desc.lower()
        assert "read" in desc.lower()
        assert "update" in desc.lower()
        assert "delete" in desc.lower()

    def test_mixed_operations_description(self):
        """Mixed operations should list specific operations."""
        desc = _generate_tool_description(["read", "update"])

        assert "read" in desc.lower()
        assert "update" in desc.lower()
        # Should not claim full CRUD
        assert "delete" not in desc.lower()

    def test_description_with_table_scope(self):
        """Description should mention table restrictions."""
        desc = _generate_tool_description(["read"], tables=["categories", "products"])

        assert "categories" in desc.lower()
        assert "products" in desc.lower()
        assert "scoped" in desc.lower()

    def test_description_with_many_tables(self):
        """Description should summarize when many tables."""
        tables = [f"table_{i}" for i in range(10)]
        desc = _generate_tool_description(["read"], tables=tables)

        # Should mention count, not list all
        assert "10" in desc or "specific tables" in desc.lower()

    def test_description_without_table_scope(self):
        """Description should indicate all tables accessible."""
        desc = _generate_tool_description(["read"], tables=None)

        assert "all tables" in desc.lower() or "all schema" in desc.lower()

    def test_description_includes_capabilities(self):
        """Description should mention core capabilities."""
        desc = _generate_tool_description(["read"])

        assert "schema-driven" in desc.lower() or "schema" in desc.lower()
        assert "transaction" in desc.lower() or "atomic" in desc.lower()


# =============================================================================
# Tool Name Generation Tests
# =============================================================================


class TestNameGeneration:
    """Test tool name generation with optional suffix."""

    def test_default_name(self):
        """Default name should be execute_database_operation."""
        name = _generate_tool_name()
        assert name == "execute_database_operation"

    def test_name_with_suffix(self):
        """Name with suffix should append suffix."""
        name = _generate_tool_name("read_only")
        assert name == "execute_database_operation_read_only"

        name = _generate_tool_name("products")
        assert name == "execute_database_operation_products"

    def test_name_empty_suffix(self):
        """Empty suffix should return base name."""
        name = _generate_tool_name("")
        assert name == "execute_database_operation"


# =============================================================================
# Tool Factory Tests
# =============================================================================


class TestToolFactory:
    """Test create_database_tool factory function."""

    def test_factory_creates_tool(self):
        """Factory should create StructuredTool instance."""
        mock_storage = Mock()
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read"],
        )

        assert tool is not None
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "args_schema")

    def test_factory_read_only_tool(self):
        """Read-only tool should have correct schema."""
        mock_storage = Mock()
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read"],
        )

        # Check schema - now uses single operation_intent parameter
        assert "operation_intent" in tool.args_schema.model_fields
        assert len(tool.args_schema.model_fields) == 1  # Only one parameter

        # Check description
        assert "read" in tool.description.lower()

    def test_factory_full_crud_tool(self):
        """Full CRUD tool should have complete schema."""
        mock_storage = Mock()
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["create", "read", "update", "delete"],
        )

        # Check schema - now uses single operation_intent parameter
        assert "operation_intent" in tool.args_schema.model_fields
        assert len(tool.args_schema.model_fields) == 1  # Only one parameter

        # Check description
        assert "crud" in tool.description.lower() or "create" in tool.description.lower()

    def test_factory_with_tool_name_suffix(self):
        """Tool with suffix should have suffixed name."""
        mock_storage = Mock()
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read"],
            tool_name_suffix="products",
        )

        assert tool.name == "execute_database_operation_products"

    def test_factory_with_table_scope(self):
        """Tool with table scope should mention tables in description."""
        mock_storage = Mock()
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read"],
            tables=["categories", "products"],
        )

        assert "categories" in tool.description.lower()
        assert "products" in tool.description.lower()

    def test_factory_validates_empty_operations(self):
        """Factory should reject empty operations list."""
        mock_storage = Mock()
        with pytest.raises(ValueError) as exc_info:
            create_database_tool(
                storage=mock_storage,
                allowed_operations=[],
            )

        assert "cannot be empty" in str(exc_info.value)

    def test_factory_validates_invalid_operations(self):
        """Factory should reject invalid operation names."""
        mock_storage = Mock()
        with pytest.raises(ValueError) as exc_info:
            create_database_tool(
                storage=mock_storage,
                allowed_operations=["read", "invalid_op"],
            )

        assert "invalid" in str(exc_info.value).lower()
        assert "invalid_op" in str(exc_info.value)

    def test_factory_accepts_valid_operations(self):
        """Factory should accept all valid operation combinations."""
        mock_storage = Mock()
        valid_combinations = [
            ["read"],
            ["create"],
            ["update"],
            ["delete"],
            ["read", "create"],
            ["read", "update"],
            ["read", "delete"],
            ["create", "update"],
            ["read", "create", "update"],
            ["create", "read", "update", "delete"],
        ]

        for ops in valid_combinations:
            tool = create_database_tool(
                storage=mock_storage,
                allowed_operations=ops,
            )
            assert tool is not None

    def test_factory_closure_captures_operations(self):
        """Factory closure should capture allowed operations."""
        mock_storage = Mock()
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read"],
        )

        # Tool schema should use single operation_intent parameter
        assert tool.args_schema.__name__ == "OperationIntentInput"
        assert "operation_intent" in tool.args_schema.model_fields

    def test_factory_different_instances_independent(self):
        """Different factory calls should create independent tools."""
        mock_storage = Mock()
        read_tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read"],
        )
        crud_tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["create", "read", "update", "delete"],
        )

        # Both should use single operation_intent parameter
        assert "operation_intent" in read_tool.args_schema.model_fields
        assert "operation_intent" in crud_tool.args_schema.model_fields
        # Schema instances should be different (but both named OperationIntentInput)
        assert read_tool.args_schema.__name__ == "OperationIntentInput"
        assert crud_tool.args_schema.__name__ == "OperationIntentInput"


# =============================================================================
# JSON Schema Output Tests (What LLMs See)
# =============================================================================


class TestJSONSchemaForLLMs:
    """Test that JSON Schema output is correct for LLM function calling."""

    def test_read_only_json_schema(self):
        """Read-only JSON Schema should only show query fields."""
        read_schema = _create_operation_input_schema(["read"])
        json_schema = read_schema.model_json_schema()

        # Check properties
        properties = json_schema["properties"]
        assert "query_filter" in properties
        assert "change_spec" not in properties
        assert "impact_analysis" not in properties

        # Check required fields
        required = json_schema.get("required", [])
        assert "user_request_summary" in required
        assert "reasoning" in required
        assert "intent_type" in required
        assert "execution_plan" in required

        # Check additionalProperties
        assert not json_schema.get("additionalProperties")

    def test_crud_json_schema(self):
        """CRUD JSON Schema should show mutation fields."""
        crud_schema = _create_operation_input_schema(["create", "read", "update", "delete"])
        json_schema = crud_schema.model_json_schema()

        # Check properties
        properties = json_schema["properties"]
        assert "change_spec" in properties
        assert "impact_analysis" in properties
        assert "query_filter" not in properties

        # Check required fields
        required = json_schema.get("required", [])
        assert "user_request_summary" in required
        assert "reasoning" in required
        assert "intent_type" in required
        assert "change_spec" in required
        assert "impact_analysis" in required
        assert "execution_plan" in required

    def test_field_descriptions_in_json_schema(self):
        """JSON Schema should include field descriptions."""
        read_schema = _create_operation_input_schema(["read"])
        json_schema = read_schema.model_json_schema()

        # Check descriptions present
        assert "description" in json_schema["properties"]["intent_type"]
        assert "description" in json_schema["properties"]["query_filter"]
        assert "description" in json_schema["properties"]["execution_plan"]

    def test_json_schema_structure(self):
        """JSON Schema should have standard OpenAI structure."""
        read_schema = _create_operation_input_schema(["read"])
        json_schema = read_schema.model_json_schema()

        # Check standard fields
        assert "type" in json_schema
        assert json_schema["type"] == "object"
        assert "properties" in json_schema
        assert "required" in json_schema
        assert "title" in json_schema


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for complete access control flow."""

    # Uses mock_storage fixture from conftest.py

    def test_read_only_specialist_pattern(self):
        """Test read-only specialist configuration pattern."""
        mock_storage = Mock()
        # Market Intelligence specialist pattern
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read"],
            tool_name_suffix="read_only",
        )

        assert tool.name == "execute_database_operation_read_only"
        assert "read" in tool.description.lower()
        assert "operation_intent" in tool.args_schema.model_fields
        # Tool now accepts single operation_intent parameter

    def test_full_crud_specialist_pattern(self):
        """Test full CRUD specialist configuration pattern."""
        mock_storage = Mock()
        # Product Architecture specialist pattern
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["create", "read", "update", "delete"],
        )

        assert tool.name == "execute_database_operation"
        assert "operation_intent" in tool.args_schema.model_fields
        # Tool now accepts single operation_intent parameter

    def test_domain_scoped_specialist_pattern(self):
        """Test domain-scoped specialist configuration pattern."""
        mock_storage = Mock()
        # Taxonomy specialist pattern
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read", "create", "update"],
            tables=["categories", "category_product_mappings"],
            tool_name_suffix="taxonomy",
        )

        assert tool.name == "execute_database_operation_taxonomy"
        assert "categories" in tool.description.lower()
        assert "operation_intent" in tool.args_schema.model_fields

    def test_mixed_operations_specialist_pattern(self):
        """Test mixed operations specialist configuration pattern."""
        mock_storage = Mock()
        # Campaign Optimization specialist pattern
        tool = create_database_tool(
            storage=mock_storage,
            allowed_operations=["read", "update"],
            tables=["campaigns", "ad_copies"],
            tool_name_suffix="campaigns",
        )

        assert tool.name == "execute_database_operation_campaigns"
        assert "campaigns" in tool.description.lower()
        assert "operation_intent" in tool.args_schema.model_fields
