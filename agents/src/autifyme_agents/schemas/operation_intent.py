"""Generic operation intent models for dynamic database operations.

Single OperationIntent replaces all hard-coded draft types (ProductArchitectureDraft,
VariantAdditionDraft, etc.). Supports ANY operation on ANY table through schema-driven execution.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Operation Models
# =============================================================================


class Operation(BaseModel):
    """Single table operation specification."""

    op_type: Literal["insert", "update", "delete", "query"] = Field(
        ..., description="Operation type"
    )
    table: str = Field(..., description="Target table name (validated against schema)")

    # For INSERT operations
    new_entities: list[dict[str, Any]] | None = Field(
        None, description="Entities to insert (list of column:value dicts)"
    )

    # For UPDATE operations
    target_filter: dict[str, Any] | None = Field(
        None, description="Filter to identify records to update (e.g., {'id': 'uuid-123'})"
    )
    field_updates: dict[str, Any] | None = Field(
        None, description="Fields to update (column:value pairs)"
    )

    # For DELETE operations
    delete_filter: dict[str, Any] | None = Field(
        None, description="Filter to identify records to delete"
    )
    soft_delete: bool = Field(
        default=True, description="Mark as inactive vs permanent delete"
    )

    # For READ operations
    query_filter: dict[str, Any] | None = Field(
        None, description="Filter for query (e.g., {'family_id': 'uuid-123'})"
    )
    include_relations: list[str] = Field(
        default_factory=list,
        description="Related tables to include (e.g., ['variant_axes', 'products'])"
    )

    # Dependency ordering
    depends_on: list[int] = Field(
        default_factory=list,
        description="Indices of operations that must complete first (for foreign keys)"
    )

    # Execution metadata
    description: str | None = Field(None, description="Human-readable operation description")


class ChangeSpecification(BaseModel):
    """Specification of what's changing across tables."""

    domain: str = Field(
        default="product_catalog",
        description="Domain name (e.g., 'product_catalog', 'marketing_content')"
    )
    operations: list[Operation] = Field(
        ..., description="List of operations to execute (in dependency order)"
    )


# =============================================================================
# Impact Analysis
# =============================================================================


class ImpactAnalysis(BaseModel):
    """Dynamic impact calculation from schema + current data."""

    # Quantitative impact
    affected_tables: dict[str, int] = Field(
        default_factory=dict,
        description="Map of table_name -> affected_row_count"
    )
    new_entities_count: dict[str, int] = Field(
        default_factory=dict,
        description="Map of table_name -> new_row_count (for INSERTs)"
    )
    updated_entities_count: dict[str, int] = Field(
        default_factory=dict,
        description="Map of table_name -> updated_row_count (for UPDATEs)"
    )
    deleted_entities_count: dict[str, int] = Field(
        default_factory=dict,
        description="Map of table_name -> deleted_row_count (for DELETEs)"
    )

    # Business-level impact (for HITL presentation)
    business_impact_summary: str = Field(
        ..., description="Human-readable summary (e.g., 'Will create 3 new SKUs')"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings (e.g., 'SKU count will triple', 'Price exceeds 10x base')"
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Example entities (e.g., ['BOTTLE-BLK-2L', 'BOTTLE-WHT-2L'])"
    )

    # Risk assessment
    is_destructive: bool = Field(
        default=False, description="Operation includes DELETE operations"
    )
    requires_approval: bool = Field(
        default=True, description="Should user approve before execution"
    )


# =============================================================================
# Execution Plan
# =============================================================================


class ExecutionStep(BaseModel):
    """Single atomic execution step."""

    step_number: int = Field(..., description="Step sequence number (1-indexed)")
    description: str = Field(..., description="Human-readable step description")
    operation: Operation = Field(..., description="Operation to execute")
    rollback_on_failure: bool = Field(
        default=True, description="Rollback all previous steps if this fails"
    )


class ExecutionPlan(BaseModel):
    """Multi-step execution plan with dependencies."""

    steps: list[ExecutionStep] = Field(..., description="Ordered execution steps")
    estimated_duration_ms: int = Field(
        default=150, description="Estimated execution time in milliseconds"
    )
    requires_approval: bool = Field(
        default=True, description="User must approve before execution"
    )

    def get_steps_in_order(self) -> list[ExecutionStep]:
        """Get steps sorted by dependencies (topological order)."""
        # Simple implementation: already ordered by depends_on
        return sorted(self.steps, key=lambda s: s.step_number)


# =============================================================================
# Operation Intent (Single Universal Model)
# =============================================================================


class OperationIntent(BaseModel):
    """
    Universal operation specification - replaces ALL hard-coded draft types.

    This single model handles:
    - Full family creation (ProductArchitectureDraft)
    - Variant value addition (VariantAdditionDraft)
    - Axis addition (AxisAdditionDraft)
    - Field updates (FamilyUpdateDraft)
    - Queries (ProductQueryDraft)
    - Deletions (ProductDeletionDraft)
    - Future operations (no code changes needed!)
    """

    # Operation classification
    intent_type: Literal["create", "read", "update", "delete"] = Field(
        ..., description="High-level intent classification"
    )

    # What's changing (schema-agnostic)
    change_spec: ChangeSpecification = Field(
        ..., description="Specification of table operations"
    )

    # Human context (for HITL presentation)
    user_request_summary: str = Field(
        ..., description="Summary of user's original request"
    )
    reasoning: str = Field(
        ..., description="Why specialist classified this way (for transparency)"
    )

    # Impact analysis (calculated by specialist from schema + data)
    impact_analysis: ImpactAnalysis = Field(
        ..., description="Impact assessment for HITL"
    )

    # LLM-generated execution plan
    execution_plan: ExecutionPlan = Field(
        ..., description="Multi-step execution plan with dependencies"
    )

    # Metadata
    specialist_name: str | None = Field(
        None, description="Which specialist generated this intent"
    )
    schema_version: str = Field(
        default="v1", description="Schema version used for planning"
    )


# =============================================================================
# Execution Result
# =============================================================================


class ExecutionResult(BaseModel):
    """Result of executing an OperationIntent."""

    success: bool = Field(..., description="Execution succeeded")

    # Entity tracking
    affected_entities: dict[str, int] = Field(
        default_factory=dict,
        description="Map of table_name -> affected_row_count"
    )
    created_ids: dict[int, dict[str, Any]] = Field(
        default_factory=dict,
        description="Map of step_number -> {field_name: generated_id} (for foreign keys)"
    )

    # Execution metadata
    execution_time_ms: int = Field(default=0, description="Actual execution time")
    steps_completed: int = Field(default=0, description="Number of steps completed")
    steps_total: int = Field(default=0, description="Total number of steps")

    # Error handling
    error_message: str | None = Field(None, description="Error message if failed")
    error_step: int | None = Field(None, description="Step number that failed")
    rollback_performed: bool = Field(default=False, description="Rollback executed")


# =============================================================================
# Helper Functions
# =============================================================================


def create_simple_intent(
    intent_type: Literal["create", "read", "update", "delete"],
    table: str,
    entities: list[dict[str, Any]] | None = None,
    summary: str = "Operation",
) -> OperationIntent:
    """
    Helper to create simple single-table OperationIntent.

    For testing or simple operations.
    """
    operation = Operation(
        op_type="insert" if intent_type == "create" else intent_type,
        table=table,
        new_entities=entities if intent_type == "create" else None,
        description=f"{intent_type.upper()} on {table}",
    )

    return OperationIntent(
        intent_type=intent_type,
        change_spec=ChangeSpecification(operations=[operation]),
        user_request_summary=summary,
        reasoning=f"Simple {intent_type} operation on {table}",
        impact_analysis=ImpactAnalysis(
            business_impact_summary=f"Will {intent_type} {len(entities or [])} entities in {table}",
        ),
        execution_plan=ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_number=1,
                    description=f"{intent_type.upper()} {table}",
                    operation=operation,
                )
            ]
        ),
    )
