"""Schema metadata models for dynamic database operations.

Defines runtime schema representations that enable schema-driven CRUD operations
without hard-coding table names, columns, or relationships.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Column Metadata
# =============================================================================


class ColumnType(str, Enum):
    """Supported PostgreSQL column types."""

    UUID = "uuid"
    VARCHAR = "varchar"
    TEXT = "text"
    INTEGER = "integer"
    BIGINT = "bigint"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    TIMESTAMPTZ = "timestamptz"
    DATE = "date"
    JSON = "json"
    JSONB = "jsonb"
    ARRAY = "array"


class ColumnSchema(BaseModel):
    """Column metadata for runtime validation."""

    name: str = Field(..., description="Column name")
    type: ColumnType = Field(..., description="Column data type")
    nullable: bool = Field(default=True, description="Can be NULL")
    primary_key: bool = Field(default=False, description="Is primary key")
    unique: bool = Field(default=False, description="Has UNIQUE constraint")
    default: Any | None = Field(None, description="Default value")
    max_length: int | None = Field(None, description="For VARCHAR - max length")
    references: str | None = Field(
        None, description="Foreign key reference (format: table.column)"
    )
    description: str | None = Field(None, description="Column description")


# =============================================================================
# Relationship Metadata
# =============================================================================


class RelationshipType(str, Enum):
    """Relationship types between tables."""

    PARENT = "parent"  # This table references parent (foreign key)
    CHILD = "child"  # Parent table references this table
    MANY_TO_MANY = "many_to_many"  # Junction table relationship


class Relationship(BaseModel):
    """Table relationship metadata."""

    type: RelationshipType = Field(..., description="Relationship type")
    target_table: str = Field(..., description="Target table name")
    foreign_key: str = Field(..., description="Foreign key column name in this table")
    target_column: str = Field(
        default="id", description="Referenced column in target table"
    )
    cascade_delete: bool = Field(
        default=False, description="CASCADE on DELETE if true"
    )
    cascade_update: bool = Field(
        default=False, description="CASCADE on UPDATE if true"
    )
    description: str | None = Field(None, description="Relationship description")


# =============================================================================
# Business Rule Metadata
# =============================================================================


class BusinessRuleTrigger(str, Enum):
    """When business rule should execute."""

    BEFORE_INSERT = "before_insert"
    AFTER_INSERT = "after_insert"
    BEFORE_UPDATE = "before_update"
    AFTER_UPDATE = "after_update"
    BEFORE_DELETE = "before_delete"
    AFTER_DELETE = "after_delete"


class BusinessRule(BaseModel):
    """Executable business logic metadata."""

    rule_type: str = Field(
        ...,
        description="Rule type (e.g., 'generate_sku', 'validate_price', 'calculate_total')",
    )
    trigger: BusinessRuleTrigger = Field(..., description="When to execute rule")
    handler: str = Field(
        ..., description="Python function name in BusinessRuleHandlers"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Handler-specific parameters"
    )
    description: str | None = Field(None, description="Rule description")
    enabled: bool = Field(default=True, description="Rule is active")


# =============================================================================
# Table Metadata
# =============================================================================


class TableSchema(BaseModel):
    """Complete table metadata for runtime operations."""

    name: str = Field(..., description="Table name")
    description: str | None = Field(None, description="Table description")
    columns: dict[str, ColumnSchema] = Field(
        ..., description="Map of column_name -> ColumnSchema"
    )
    primary_key: str = Field(default="id", description="Primary key column name")
    relationships: list[Relationship] = Field(
        default_factory=list, description="Foreign key relationships"
    )
    business_rules: list[BusinessRule] = Field(
        default_factory=list, description="Business logic rules"
    )
    indexes: list[str] = Field(
        default_factory=list, description="Indexed column names (for query optimization)"
    )

    def get_column(self, name: str) -> ColumnSchema:
        """Get column schema by name."""
        if name not in self.columns:
            raise ValueError(f"Column '{name}' not found in table '{self.name}'")
        return self.columns[name]

    def get_foreign_keys(self) -> dict[str, Relationship]:
        """Get all foreign key relationships."""
        return {rel.foreign_key: rel for rel in self.relationships if rel.type == RelationshipType.PARENT}

    def get_required_columns(self) -> list[str]:
        """Get columns that cannot be NULL and have no default."""
        return [
            name
            for name, col in self.columns.items()
            if not col.nullable and col.default is None and not col.primary_key
        ]


# =============================================================================
# Schema Registry
# =============================================================================


class SchemaRegistry(BaseModel):
    """Version-controlled schema registry."""

    version: str = Field(..., description="Schema version (e.g., 'v1', 'v2')")
    domain: str = Field(..., description="Domain name (e.g., 'product_catalog')")
    description: str | None = Field(None, description="Schema description")
    tables: dict[str, TableSchema] = Field(
        ..., description="Map of table_name -> TableSchema"
    )

    def get_table(self, name: str) -> TableSchema:
        """Get table schema by name."""
        if name not in self.tables:
            raise ValueError(
                f"Table '{name}' not found in schema {self.domain}:{self.version}"
            )
        return self.tables[name]

    def get_table_names(self) -> list[str]:
        """Get all table names in this schema."""
        return list(self.tables.keys())

    def validate_table_exists(self, name: str) -> bool:
        """Check if table exists in schema."""
        return name in self.tables

    def to_dict(self) -> dict[str, Any]:
        """Serialize schema to dictionary."""
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Serialize schema to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, file_path: Path | str) -> None:
        """Save schema to JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SchemaRegistry":
        """Load schema from dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "SchemaRegistry":
        """Load schema from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def load_from_file(cls, file_path: Path | str) -> "SchemaRegistry":
        """Load schema from JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")
        return cls.from_json(path.read_text())

    @classmethod
    def get_version(cls, version: str = "latest", domain: str = "product_catalog") -> "SchemaRegistry":
        """
        Load schema by version from registry.

        Args:
            version: Schema version ('latest', 'v1', 'v2', etc.)
            domain: Domain name (default: 'product_catalog')

        Returns:
            SchemaRegistry instance

        Raises:
            FileNotFoundError: If schema version not found
        """
        # Get schema directory
        schema_dir = Path(__file__).parent / "versions" / domain

        if version == "latest":
            # Find latest version
            version_files = sorted(schema_dir.glob("v*.json"), reverse=True)
            if not version_files:
                raise FileNotFoundError(
                    f"No schema versions found for domain '{domain}'"
                )
            schema_file = version_files[0]
        else:
            # Load specific version
            schema_file = schema_dir / f"{version}.json"

        return cls.load_from_file(schema_file)

    def evolve(
        self,
        new_version: str,
        add_tables: list[TableSchema] | None = None,
        remove_tables: list[str] | None = None,
        update_tables: dict[str, TableSchema] | None = None,
        description: str | None = None,
    ) -> "SchemaRegistry":
        """
        Create new schema version with changes.

        Args:
            new_version: New version identifier
            add_tables: Tables to add
            remove_tables: Table names to remove
            update_tables: Tables to update (replaces existing)
            description: Description of changes

        Returns:
            New SchemaRegistry with changes applied
        """
        new_tables = self.tables.copy()

        # Remove tables
        if remove_tables:
            for table_name in remove_tables:
                new_tables.pop(table_name, None)

        # Update existing tables
        if update_tables:
            for table_name, table_schema in update_tables.items():
                new_tables[table_name] = table_schema

        # Add new tables
        if add_tables:
            for table_schema in add_tables:
                new_tables[table_schema.name] = table_schema

        return SchemaRegistry(
            version=new_version,
            domain=self.domain,
            description=description or f"Evolved from {self.version}",
            tables=new_tables,
        )


# =============================================================================
# Schema Validator
# =============================================================================


class ValidationResult(BaseModel):
    """Result of schema validation."""

    valid: bool = Field(..., description="Validation passed")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")

    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)


class SchemaValidator:
    """Validates operations against schema metadata."""

    def __init__(self, schema: SchemaRegistry):
        """Initialize validator with schema."""
        self.schema = schema

    def validate_table_exists(self, table_name: str) -> ValidationResult:
        """Validate table exists in schema."""
        result = ValidationResult(valid=True)

        if not self.schema.validate_table_exists(table_name):
            result.add_error(f"Table '{table_name}' not found in schema")

        return result

    def validate_entity(
        self, table_name: str, entity: dict[str, Any]
    ) -> ValidationResult:
        """Validate entity against table schema."""
        result = ValidationResult(valid=True)

        # Check table exists
        table_result = self.validate_table_exists(table_name)
        if not table_result.valid:
            return table_result

        table = self.schema.get_table(table_name)

        # Check required columns
        required = table.get_required_columns()
        missing = [col for col in required if col not in entity]
        if missing:
            result.add_error(
                f"Missing required columns for table '{table_name}': {missing}"
            )

        # Check unknown columns
        valid_columns = set(table.columns.keys())
        provided_columns = set(entity.keys())
        unknown = provided_columns - valid_columns
        if unknown:
            result.add_warning(
                f"Unknown columns for table '{table_name}': {list(unknown)}"
            )

        # Validate column types (basic)
        for col_name, value in entity.items():
            if col_name in table.columns:
                col = table.columns[col_name]
                if value is None and not col.nullable:
                    result.add_error(
                        f"Column '{col_name}' cannot be NULL in table '{table_name}'"
                    )

        return result

    def validate_operation(
        self, operation: dict[str, Any]
    ) -> ValidationResult:
        """Validate operation against schema."""
        result = ValidationResult(valid=True)

        table_name = operation.get("table")
        if not table_name:
            result.add_error("Operation missing 'table' field")
            return result

        # Validate table exists
        table_result = self.validate_table_exists(table_name)
        if not table_result.valid:
            result.errors.extend(table_result.errors)
            return result

        # Validate entities if present
        new_entities = operation.get("new_entities") or []
        for i, entity in enumerate(new_entities):
            entity_result = self.validate_entity(table_name, entity)
            if not entity_result.valid:
                for error in entity_result.errors:
                    result.add_error(f"Entity {i}: {error}")

        return result
