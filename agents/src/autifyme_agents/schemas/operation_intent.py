"""Generic operation intent models for dynamic database operations.

Single OperationIntent replaces all hard-coded draft types (ProductArchitectureDraft,
VariantAdditionDraft, etc.). Supports ANY operation on ANY table through schema-driven execution.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# Helper Models for Type Safety
# =============================================================================


class FieldValue(BaseModel):
    """Strongly-typed field-value pair for database operations.

    Provides type safety while supporting all database field types.
    """

    field: str = Field(..., description="Field/column name")
    value: str | int | float | bool | None = Field(..., description="Field value (NULL supported)")


class EntityRef(BaseModel):
    """Named entity reference for cross-operation dependencies.

    Enables semantic references like $ref:prod_500ml_clear instead of $step_0.
    """

    name: str = Field(..., description="Semantic reference name (e.g., 'prod_500ml_clear')")
    entity_index: int = Field(..., description="Index in new_entities array (0-based)")


class TableCount(BaseModel):
    """Table with row count for impact tracking."""

    table: str = Field(..., description="Table name")
    count: int = Field(..., description="Row count")


class CreatedEntity(BaseModel):
    """Track created entity with generated ID and semantic name."""

    entity_id: str = Field(..., description="Generated entity ID (UUID)")
    entity_name: str | None = Field(None, description="Semantic name if using entity_refs")
    table: str = Field(..., description="Table name where entity was created")
    step_number: int = Field(..., description="Execution step that created this entity")


class UpdatedEntity(BaseModel):
    """Track updated entity with modified fields."""

    entity_id: str = Field(..., description="Entity ID that was updated")
    table: str = Field(..., description="Table name")
    updated_fields: list[str] = Field(..., description="List of field names that were updated")


class DeletedEntity(BaseModel):
    """Track deleted entity."""

    entity_id: str = Field(..., description="Entity ID that was deleted")
    table: str = Field(..., description="Table name")
    soft_delete: bool = Field(..., description="Whether it was soft-deleted (inactive) or hard-deleted")


# =============================================================================
# Operation Models
# =============================================================================


class Operation(BaseModel):
    """Single table operation specification for schema-driven database operations.

    Supports INSERT, UPDATE, DELETE, and QUERY operations with dynamic filters,
    cross-operation references, and foreign key dependency tracking.

    Examples:
        INSERT with cross-operation references:
            Operation(
                op_type="insert",
                table="product_families",
                new_entities=[
                    {"name": "PET Bottles", "sku_prefix": "BOTTLE-PET", "base_price": 25.0},
                    {"name": "HDPE Containers", "sku_prefix": "CONT-HDPE", "base_price": 30.0}
                ],
                entity_refs={"pet_bottles_family": 0, "hdpe_containers_family": 1},
                description="Create product families for packaging catalog"
            )

        UPDATE with complex filter:
            Operation(
                op_type="update",
                table="products",
                target_filter={"family_id": "550e8400-e29b-41d4-a716-446655440000", "is_active": True},
                field_updates={"base_price": 32.0, "price_updated_at": "2025-01-15T10:30:00Z"},
                description="Increase base price for all active PET Bottles variants"
            )

        DELETE with soft_delete:
            Operation(
                op_type="delete",
                table="variant_values",
                delete_filter={"axis_id": "660e8400-e29b-41d4-a716-446655440000"},
                soft_delete=True,  # Mark inactive instead of permanent delete
                description="Retire all size variants for discontinued axis"
            )

        QUERY with relations:
            Operation(
                op_type="query",
                table="product_families",
                query_filter={"is_active": True, "category": "packaging"},
                include_relations=["products(*)", "variant_axes(*)", "variant_values(*)"],
                description="Fetch complete packaging catalog with all variants"
            )
    """

    op_type: Literal["insert", "update", "delete", "query"] = Field(
        ...,
        description=(
            "Operation type. Options: "
            "'insert' (create new records), "
            "'update' (modify existing records), "
            "'delete' (remove/soft-delete records), "
            "'query' (read records with optional relations)"
        )
    )
    table: str = Field(
        ...,
        description=(
            "Target table name (e.g., 'product_families', 'products', 'variant_values'). "
            "Must exist in database schema. Validated at execution time."
        )
    )

    # For INSERT operations
    new_entities: list[dict[str, Any]] | None = Field(
        None,
        description=(
            "Entities to insert (INSERT operations only). List of dicts with column:value pairs. "
            "Example: [{'name': 'PET Bottles', 'sku_prefix': 'BOTTLE-PET', 'base_price': 25.0}, "
            "{'name': 'HDPE Containers', 'sku_prefix': 'CONT-HDPE', 'base_price': 30.0}]. "
            "Foreign keys can use $ref:name syntax to reference entities created in previous operations. "
            "Generated IDs (UUID, auto-increment) are returned in ExecutionResult.created_ids."
        )
    )

    # Named entity references for cross-operation dependencies
    entity_refs: dict[str, int] | None = Field(
        None,
        description=(
            "Map of semantic names to entity indices in new_entities array (INSERT operations with cross-references). "
            "Example: {'pet_bottles_family': 0, 'hdpe_containers_family': 1} maps human-readable names to array indices. "
            "Dependent operations can reference these using $ref:pet_bottles_family syntax in foreign key fields. "
            "This enables readable, maintainable cross-operation references instead of numeric step indices."
        )
    )

    # For UPDATE operations
    target_filter: dict[str, Any] | None = Field(
        None,
        description=(
            "Filter to identify records to update (UPDATE operations only). Dict with column:value conditions. "
            "Simple: {'id': '550e8400-e29b-41d4-a716-446655440000'} (single record by UUID). "
            "Complex: {'family_id': 'uuid-123', 'is_active': True, 'price': {'$gt': 50.0}} (multiple records matching criteria). "
            "Supports operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $not_in for advanced filtering. "
            "Missing filter updates ALL records (dangerous - requires explicit confirmation)."
        )
    )
    field_updates: dict[str, Any] | None = Field(
        None,
        description=(
            "Fields to update with new values (UPDATE operations only). Dict with column:value pairs. "
            "Example: {'base_price': 32.0, 'price_updated_at': '2025-01-15T10:30:00Z', 'is_featured': True}. "
            "Only specified fields are modified; other columns remain unchanged. "
            "Null values: Use None to clear a field. "
            "JSON fields: Pass nested dicts (e.g., {'metadata': {'source': 'bulk_import', 'verified': True}})."
        )
    )

    # For DELETE operations
    delete_filter: dict[str, Any] | None = Field(
        None,
        description=(
            "Filter to identify records to delete (DELETE operations only). Dict with column:value conditions. "
            "Simple: {'id': ['uuid-1', 'uuid-2', 'uuid-3']} (delete specific records by UUID list). "
            "Complex: {'family_id': 'uuid-123', 'is_active': False} (delete all inactive variants in family). "
            "Missing filter deletes ALL records (DESTRUCTIVE - requires explicit confirmation). "
            "Supports same operators as target_filter ($eq, $ne, $gt, $gte, $lt, $lte, $in, $not_in)."
        )
    )
    soft_delete: bool = Field(
        default=True,
        description=(
            "Soft delete vs permanent delete (DELETE operations only). "
            "True: Set is_active=False (recommended - preserves data for audit/recovery). "
            "False: Permanently remove from database (DESTRUCTIVE - cannot undo). "
            "Soft delete is default for safety. Only use permanent delete for test data or explicit user request."
        )
    )

    # For READ operations
    query_filter: dict[str, Any] | None = Field(
        None,
        description=(
            "Filter for query (QUERY operations only). Dict with column:value conditions. "
            "Simple: {'is_active': True} (fetch all active records). "
            "Complex: {'category': 'packaging', 'base_price': {'$gte': 20.0, '$lte': 50.0}, 'name': {'$like': '%Bottle%'}} "
            "(fetch packaging products priced ₹20-50 with 'Bottle' in name). "
            "Empty/None: Fetch all records (use with caution on large tables). "
            "Supports operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $not_in, $like, $ilike for flexible querying."
        )
    )
    include_relations: list[str] = Field(
        default_factory=list,
        description=(
            "Related tables to include via foreign keys (QUERY operations only). List of relation paths. "
            "Simple: ['products', 'variant_axes'] (include direct foreign key relations). "
            "Nested: ['products(*)', 'products.variant_values(*)', 'variant_axes.variant_values(*)'] "
            "(fetch products with their variant values, and axes with their variant values). "
            "Wildcard (*): Select all columns from related table. "
            "Specific columns: ['products(id,name,sku)', 'variant_axes(id,axis_name)'] (optimize query size)."
        )
    )

    # Dependency ordering
    depends_on: list[int] = Field(
        default_factory=list,
        description=(
            "Indices of operations that must complete before this operation (0-based array indices). "
            "Example: Operation 2 creates products referencing family created in Operation 0 → depends_on=[0]. "
            "Execution engine uses topological sorting to ensure dependency order. "
            "Circular dependencies are detected and rejected. "
            "Empty list: No dependencies, can execute first (or in parallel if supported)."
        )
    )

    # Execution metadata
    description: str | None = Field(
        None,
        description=(
            "Human-readable operation description for logging and HITL presentation. "
            "Example: 'Create PET Bottles family with 6 size variants (500ml to 5L)'. "
            "Helps users understand what each operation does during approval workflow."
        )
    )


class ChangeSpecification(BaseModel):
    """Specification of what's changing across tables.

    Groups related operations into a single atomic transaction across multiple tables.
    Operations are executed in dependency order (topologically sorted).

    Examples:
        Single-table operation:
            ChangeSpecification(
                domain="product_catalog",
                operations=[
                    Operation(
                        op_type="update",
                        table="product_families",
                        target_filter={"id": "550e8400-e29b-41d4-a716-446655440000"},
                        field_updates={"base_price": 30.0},
                        description="Update PET Bottles family base price"
                    )
                ]
            )

        Multi-table product family creation:
            ChangeSpecification(
                domain="product_catalog",
                operations=[
                    Operation(
                        op_type="insert",
                        table="product_families",
                        new_entities=[{"name": "PET Bottles", "sku_prefix": "BOTTLE-PET"}],
                        entity_refs={"pet_family": 0},
                        description="Create PET Bottles family"
                    ),
                    Operation(
                        op_type="insert",
                        table="variant_axes",
                        new_entities=[
                            {"axis_name": "Size", "family_id": "$ref:pet_family"}
                        ],
                        entity_refs={"size_axis": 0},
                        depends_on=[0],  # Wait for family creation
                        description="Create Size axis for PET family"
                    ),
                    Operation(
                        op_type="insert",
                        table="variant_values",
                        new_entities=[
                            {"value_name": "500ml", "axis_id": "$ref:size_axis"},
                            {"value_name": "1L", "axis_id": "$ref:size_axis"}
                        ],
                        depends_on=[1],  # Wait for axis creation
                        description="Create size variants"
                    )
                ]
            )
    """

    domain: str = Field(
        default="product_catalog",
        description=(
            "Domain name for logical grouping and context. Options: "
            "'product_catalog' (families, products, variants), "
            "'marketing_content' (campaigns, assets, segments), "
            "'sales_orders' (orders, line items, payments). "
            "Helps specialists and PM organize operations by business domain."
        )
    )
    operations: list[Operation] = Field(
        ...,
        description=(
            "List of operations to execute atomically across tables. "
            "Operations are executed in dependency order (topological sort respects depends_on fields). "
            "Example: [create family, create axis, create values] → dependency chain ensures correct execution order. "
            "All operations succeed or all rollback (transaction semantics). "
            "Empty list is invalid - must have at least one operation."
        )
    )


# =============================================================================
# Impact Analysis
# =============================================================================


class ImpactAnalysis(BaseModel):
    """Dynamic impact calculation from schema + current data.

    Calculated by specialist after analyzing database schema and current data state.
    Used for HITL presentation to help users understand what will change.

    Examples:
        Simple product family creation:
            ImpactAnalysis(
                affected_tables=[
                    TableCount(table="product_families", count=1),
                    TableCount(table="variant_axes", count=2),
                    TableCount(table="variant_values", count=12)
                ],
                new_entities_count=[
                    TableCount(table="product_families", count=1),
                    TableCount(table="variant_axes", count=2),
                    TableCount(table="variant_values", count=12)
                ],
                business_impact_summary="Will create 1 new product family (PET Bottles) with 2 variant axes (Size, Color) and 12 variant values (6 sizes × 2 colors = 12 SKU combinations)",
                examples=[
                    "BOTTLE-PET-500ML-CLEAR",
                    "BOTTLE-PET-1L-CLEAR",
                    "BOTTLE-PET-2L-AMBER"
                ],
                warnings=[
                    "SKU count will increase by 12 (current: 45 → new: 57)",
                    "Base price ₹25/unit is 15% below current family average (₹29.50)"
                ],
                is_destructive=False,
                requires_approval=True
            )

        Bulk price update with risk:
            ImpactAnalysis(
                affected_tables=[TableCount(table="products", count=156)],
                updated_entities_count=[TableCount(table="products", count=156)],
                business_impact_summary="Will increase base price by 20% for all PET Bottles variants (156 SKUs affected)",
                warnings=[
                    "CRITICAL: Price increase affects 156 active SKUs across 12 families",
                    "Average price change: ₹25.00 → ₹30.00 (+20%)",
                    "3 products will exceed ₹100/unit threshold (may require manager approval)",
                    "Price history will be preserved in audit log"
                ],
                examples=[
                    "BOTTLE-PET-500ML-CLEAR: ₹22.50 → ₹27.00",
                    "BOTTLE-PET-2L-AMBER: ₹45.00 → ₹54.00",
                    "BOTTLE-PET-5L-CLEAR: ₹85.00 → ₹102.00 (⚠️ exceeds threshold)"
                ],
                is_destructive=False,
                requires_approval=True
            )

        Destructive deletion:
            ImpactAnalysis(
                affected_tables=[
                    TableCount(table="variant_values", count=24),
                    TableCount(table="products", count=48)
                ],
                deleted_entities_count=[
                    TableCount(table="variant_values", count=24),
                    TableCount(table="products", count=48)
                ],
                business_impact_summary="Will soft-delete 24 discontinued color variants, marking 48 dependent products as inactive",
                warnings=[
                    "DESTRUCTIVE: 48 products will be marked inactive (soft delete)",
                    "Cascade effect: Deleting 24 variant values affects 48 products",
                    "Order history preserved (soft delete maintains referential integrity)",
                    "Can be reversed by setting is_active=True"
                ],
                examples=[
                    "Color variant 'Neon Green' → inactive (8 products affected)",
                    "Color variant 'Metallic Gold' → inactive (12 products affected)"
                ],
                is_destructive=True,
                requires_approval=True
            )
    """

    # Quantitative impact (strongly typed for better validation)
    affected_tables: list[TableCount] = Field(
        default_factory=list,
        description=(
            "All tables affected by this operation with row counts. "
            "Includes tables directly modified plus cascade effects (e.g., deleting axis affects dependent products). "
            "Example: [TableCount(table='product_families', count=1), TableCount(table='variant_axes', count=2)]. "
            "Used to show user full scope of changes across normalized schema."
        )
    )
    new_entities_count: list[TableCount] = Field(
        default_factory=list,
        description=(
            "New rows to be inserted per table (INSERT operations only). "
            "Example: Creating 1 family with 2 axes and 12 values → "
            "[TableCount(table='product_families', count=1), TableCount(table='variant_axes', count=2), "
            "TableCount(table='variant_values', count=12)]. "
            "Empty for UPDATE/DELETE/QUERY operations."
        )
    )
    updated_entities_count: list[TableCount] = Field(
        default_factory=list,
        description=(
            "Rows to be updated per table (UPDATE operations only). "
            "Example: Bulk price update across 156 SKUs → [TableCount(table='products', count=156)]. "
            "Count calculated by running target_filter against current database state. "
            "Empty for INSERT/DELETE/QUERY operations."
        )
    )
    deleted_entities_count: list[TableCount] = Field(
        default_factory=list,
        description=(
            "Rows to be deleted per table (DELETE operations only). "
            "Includes both soft deletes (is_active=False) and hard deletes (permanent removal). "
            "Example: Deleting 24 variant values + 48 dependent products → "
            "[TableCount(table='variant_values', count=24), TableCount(table='products', count=48)]. "
            "Empty for INSERT/UPDATE/QUERY operations."
        )
    )

    # Business-level impact (for HITL presentation)
    business_impact_summary: str = Field(
        ...,
        description=(
            "Human-readable summary of business impact for user approval. "
            "Should quantify changes and explain business consequences. "
            "Good: 'Will create 1 new product family (PET Bottles) with 2 variant axes (Size, Color) and 12 variant values (6 sizes × 2 colors = 12 SKU combinations)'. "
            "Bad: 'Will insert records'. "
            "Include: entity counts, affected SKUs, price changes, cascade effects, business context."
        )
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Business warnings and risk flags for user attention. "
            "Examples: "
            "'CRITICAL: Price increase affects 156 active SKUs across 12 families', "
            "'SKU count will triple from 45 to 135 (storage cost +₹2400/month)', "
            "'Base price ₹150/unit exceeds 10x current average (₹12/unit)', "
            "'DESTRUCTIVE: Permanent delete cannot be undone (consider soft delete)', "
            "'3 products will exceed ₹100/unit approval threshold'. "
            "Use 'CRITICAL' or 'DESTRUCTIVE' prefixes for high-risk operations. "
            "Empty list if no warnings."
        )
    )
    examples: list[str] = Field(
        default_factory=list,
        description=(
            "Representative examples of affected entities (SKUs, products, campaigns). "
            "Helps users visualize concrete impact. "
            "Examples: "
            "['BOTTLE-PET-500ML-CLEAR', 'BOTTLE-PET-1L-AMBER', 'BOTTLE-PET-2L-CLEAR'] (SKU creation), "
            "['PET Bottles family: ₹22.50 → ₹27.00', 'HDPE Containers family: ₹30.00 → ₹36.00'] (price updates), "
            "['Summer Campaign 2025: +₹50,000 budget', 'Winter Promo: +3 new segments'] (campaign changes). "
            "Include 3-5 diverse examples showing range of changes. "
            "Empty list if operation is abstract (e.g., schema migration)."
        )
    )

    # Risk assessment
    is_destructive: bool = Field(
        default=False,
        description=(
            "Operation includes DELETE operations (soft or hard delete). "
            "True: Requires extra user confirmation, audit logging, rollback plan. "
            "False: Standard approval workflow. "
            "Even soft deletes are marked destructive (data becomes inactive/hidden)."
        )
    )
    requires_approval: bool = Field(
        default=True,
        description=(
            "Should user approve before execution (HITL gate). "
            "True (default): All production operations require explicit approval. "
            "False: Auto-execute (ONLY for read-only queries or test environments). "
            "Override to False for query operations that don't modify data."
        )
    )


# =============================================================================
# Execution Plan
# =============================================================================


class ExecutionStep(BaseModel):
    """Single atomic execution step in multi-step execution plan.

    Each step references an operation from ChangeSpecification.operations[].
    Steps are executed sequentially in step_number order (topologically sorted by dependencies).

    Examples:
        Step 1 - Create family:
            ExecutionStep(
                step_number=1,
                description="Create PET Bottles product family",
                operation_index=0,  # References operations[0]
                rollback_on_failure=True
            )

        Step 2 - Create axis (depends on Step 1):
            ExecutionStep(
                step_number=2,
                description="Create Size variant axis for PET family",
                operation_index=1,  # References operations[1] which has depends_on=[0]
                rollback_on_failure=True
            )

        Step 3 - Bulk update (no rollback):
            ExecutionStep(
                step_number=3,
                description="Update base prices for 156 PET Bottles SKUs",
                operation_index=2,
                rollback_on_failure=False  # Price updates logged but not rolled back
            )
    """

    step_number: int = Field(
        ...,
        description=(
            "Step sequence number (1-indexed) defining execution order. "
            "Steps execute sequentially: 1 → 2 → 3 → ... → N. "
            "Topological sort ensures dependencies execute before dependents. "
            "Example: Step 1 creates family, Step 2 creates axis (depends_on=[0]), Step 3 creates values (depends_on=[1])."
        )
    )
    description: str = Field(
        ...,
        description=(
            "Human-readable step description for logging and HITL presentation. "
            "Should explain WHAT this step does and WHY. "
            "Good: 'Create Size variant axis for PET Bottles family (enables 500ml-5L range)'. "
            "Bad: 'Insert into variant_axes'. "
            "Used in approval UI and execution logs to help users understand workflow progression."
        )
    )

    operation_index: int = Field(
        ...,
        description=(
            "Index into change_spec.operations[] array (0-based) to execute for this step. "
            "Avoids duplicating operation data in execution plan. "
            "Example: operation_index=0 → execute operations[0], operation_index=1 → execute operations[1]. "
            "Must be valid index: 0 <= operation_index < len(operations)."
        )
    )

    rollback_on_failure: bool = Field(
        default=True,
        description=(
            "Should all previous steps be rolled back if this step fails? "
            "True (default): Full transaction semantics - all-or-nothing execution. "
            "False: Allow partial success (e.g., bulk updates where some rows can fail independently). "
            "Use False carefully - can leave database in inconsistent state. "
            "Typical use case: Non-critical updates that don't break referential integrity."
        )
    )


class ExecutionPlan(BaseModel):
    """Multi-step execution plan with dependency tracking and time estimation.

    Orchestrates sequential execution of operations respecting dependencies.
    Generated by specialist LLM after analyzing operation complexity and dependencies.

    Examples:
        Simple single-table update:
            ExecutionPlan(
                steps=[
                    ExecutionStep(
                        step_number=1,
                        description="Update base price for PET Bottles family",
                        operation_index=0
                    )
                ],
                estimated_duration_ms=50,
                requires_approval=True
            )

        Complex multi-table family creation:
            ExecutionPlan(
                steps=[
                    ExecutionStep(
                        step_number=1,
                        description="Create PET Bottles product family",
                        operation_index=0
                    ),
                    ExecutionStep(
                        step_number=2,
                        description="Create Size variant axis (depends on family)",
                        operation_index=1
                    ),
                    ExecutionStep(
                        step_number=3,
                        description="Create Color variant axis (depends on family)",
                        operation_index=2
                    ),
                    ExecutionStep(
                        step_number=4,
                        description="Create 6 size variant values (500ml-5L)",
                        operation_index=3
                    ),
                    ExecutionStep(
                        step_number=5,
                        description="Create 2 color variant values (Clear, Amber)",
                        operation_index=4
                    ),
                    ExecutionStep(
                        step_number=6,
                        description="Generate 12 product SKU combinations (6×2)",
                        operation_index=5
                    )
                ],
                estimated_duration_ms=450,  # ~75ms per step
                requires_approval=True
            )

        Read-only query (auto-execute):
            ExecutionPlan(
                steps=[
                    ExecutionStep(
                        step_number=1,
                        description="Query all active PET Bottles SKUs with pricing",
                        operation_index=0
                    )
                ],
                estimated_duration_ms=100,
                requires_approval=False  # Read-only, safe to auto-execute
            )
    """

    steps: list[ExecutionStep] = Field(
        ...,
        description=(
            "Ordered execution steps (topologically sorted by dependencies). "
            "Each step references an operation via operation_index. "
            "Steps execute sequentially: step_number 1 → 2 → 3 → ... → N. "
            "Dependency resolution: Operations with depends_on=[0] execute after operations[0] completes. "
            "Example: [create family (step 1), create axis (step 2, depends_on=[0]), create values (step 3, depends_on=[1])]. "
            "Empty list invalid - must have at least one step."
        )
    )
    estimated_duration_ms: int = Field(
        default=150,
        description=(
            "Estimated total execution time in milliseconds. "
            "Used for user expectations and timeout configuration. "
            "Rough guidelines: "
            "Simple INSERT/UPDATE: 50-100ms, "
            "Complex multi-table family creation: 300-500ms, "
            "Bulk updates (100+ rows): 500-2000ms, "
            "Large queries with relations: 200-800ms. "
            "Actual time varies by database load and network latency."
        )
    )
    requires_approval: bool = Field(
        default=True,
        description=(
            "Must user approve before execution (HITL gate)? "
            "True (default): Present ImpactAnalysis to user, wait for approval, then execute. "
            "False: Auto-execute without approval (ONLY for read-only queries or test environments). "
            "Safety: Always True for INSERT/UPDATE/DELETE in production. "
            "Set False for QUERY operations that don't modify data."
        )
    )

    def get_steps_in_order(self) -> list[ExecutionStep]:
        """Get steps sorted by dependencies (topological order).

        Returns:
            List of ExecutionStep sorted by step_number (1, 2, 3, ...).
            Already topologically sorted - dependencies guaranteed to execute before dependents.
        """
        # Simple implementation: already ordered by depends_on during plan creation
        return sorted(self.steps, key=lambda s: s.step_number)


# =============================================================================
# Operation Intent (Single Universal Model)
# =============================================================================


class OperationIntent(BaseModel):
    """Universal operation specification - replaces ALL hard-coded draft types.

    Single model handles any database operation across any domain:
    - Product catalog: Full family creation, variant addition, axis addition, field updates, queries, deletions
    - Marketing: Campaign creation, content updates, segment management
    - Sales: Order creation, inventory updates, pricing changes
    - Future domains: No code changes needed!

    Generated by domain specialists (ProductSpecialist, MarketingSpecialist, etc.) after analyzing user intent.
    Consumed by UniversalCRUDTool for schema-driven execution.

    Complete Workflow Example - Create PET Bottles Family:
        User: "Create a new product family for PET bottles with sizes 500ml, 1L, 2L and colors Clear, Amber"

        Specialist generates:
        OperationIntent(
            intent_type="create",

            change_spec=ChangeSpecification(
                domain="product_catalog",
                operations=[
                    Operation(
                        op_type="insert",
                        table="product_families",
                        new_entities=[{
                            "name": "PET Bottles",
                            "sku_prefix": "BOTTLE-PET",
                            "base_price": 25.0,
                            "description": "Polyethylene Terephthalate bottles for beverages"
                        }],
                        entity_refs={"pet_family": 0},
                        description="Create PET Bottles product family"
                    ),
                    Operation(
                        op_type="insert",
                        table="variant_axes",
                        new_entities=[
                            {"axis_name": "Size", "family_id": "$ref:pet_family"},
                            {"axis_name": "Color", "family_id": "$ref:pet_family"}
                        ],
                        entity_refs={"size_axis": 0, "color_axis": 1},
                        depends_on=[0],
                        description="Create Size and Color variant axes"
                    ),
                    Operation(
                        op_type="insert",
                        table="variant_values",
                        new_entities=[
                            {"value_name": "500ml", "axis_id": "$ref:size_axis"},
                            {"value_name": "1L", "axis_id": "$ref:size_axis"},
                            {"value_name": "2L", "axis_id": "$ref:size_axis"},
                            {"value_name": "Clear", "axis_id": "$ref:color_axis"},
                            {"value_name": "Amber", "axis_id": "$ref:color_axis"}
                        ],
                        depends_on=[1],
                        description="Create 3 size values + 2 color values"
                    )
                ]
            ),

            user_request_summary="Create PET Bottles family with 3 sizes (500ml, 1L, 2L) and 2 colors (Clear, Amber)",

            reasoning=(
                "User wants to create a complete product family structure. "
                "Classified as 'create' intent requiring 3 tables: product_families, variant_axes, variant_values. "
                "Dependencies: axes depend on family ID, values depend on axis IDs. "
                "Will generate 6 SKU combinations (3 sizes × 2 colors)."
            ),

            impact_analysis=ImpactAnalysis(
                affected_tables=[
                    TableCount(table="product_families", count=1),
                    TableCount(table="variant_axes", count=2),
                    TableCount(table="variant_values", count=5),
                    TableCount(table="products", count=6)  # Generated SKUs
                ],
                new_entities_count=[
                    TableCount(table="product_families", count=1),
                    TableCount(table="variant_axes", count=2),
                    TableCount(table="variant_values", count=5),
                    TableCount(table="products", count=6)
                ],
                business_impact_summary=(
                    "Will create 1 new product family (PET Bottles) with 2 variant axes "
                    "(Size, Color) and 5 variant values, generating 6 SKU combinations"
                ),
                examples=[
                    "BOTTLE-PET-500ML-CLEAR",
                    "BOTTLE-PET-1L-CLEAR",
                    "BOTTLE-PET-2L-AMBER"
                ],
                warnings=[
                    "SKU count will increase by 6 (current: 45 → new: 51)",
                    "Base price ₹25/unit is 15% below current family average (₹29.50)"
                ],
                is_destructive=False,
                requires_approval=True
            ),

            execution_plan=ExecutionPlan(
                steps=[
                    ExecutionStep(step_number=1, description="Create PET Bottles family", operation_index=0),
                    ExecutionStep(step_number=2, description="Create Size and Color axes", operation_index=1),
                    ExecutionStep(step_number=3, description="Create 5 variant values", operation_index=2)
                ],
                estimated_duration_ms=250,
                requires_approval=True
            ),

            specialist_name="ProductSpecialist",
            schema_version="v1"
        )

        Execution flow:
        1. PM presents impact_analysis to user via HITL
        2. User approves
        3. UniversalCRUDTool executes 3 steps sequentially
        4. Returns ExecutionResult with created_ids for all entities
    """

    # Operation classification
    intent_type: Literal["create", "read", "update", "delete"] = Field(
        ...,
        description=(
            "High-level intent classification for routing and validation. Options: "
            "'create' (INSERT new entities across 1+ tables), "
            "'read' (QUERY existing data with optional relations), "
            "'update' (UPDATE existing entities with field changes), "
            "'delete' (DELETE/soft-delete entities). "
            "Used by PM to understand operation type at a glance."
        )
    )

    # What's changing (schema-agnostic)
    change_spec: ChangeSpecification = Field(
        ...,
        description=(
            "Complete specification of what tables/operations are involved. "
            "Contains list of Operation objects defining exact database changes. "
            "Schema-agnostic design enables operations on ANY table without code changes. "
            "See ChangeSpecification examples for single-table and multi-table patterns."
        )
    )

    # Human context (for HITL presentation)
    user_request_summary: str = Field(
        ...,
        description=(
            "Plain-language summary of user's original request for HITL presentation. "
            "Should match user's vocabulary and intent. "
            "Good: 'Create PET Bottles family with 3 sizes (500ml, 1L, 2L) and 2 colors (Clear, Amber)'. "
            "Bad: 'Insert into product_families, variant_axes, variant_values'. "
            "Used in approval UI to confirm specialist understood user correctly."
        )
    )
    reasoning: str = Field(
        ...,
        description=(
            "Specialist's reasoning for this operation classification and structure. "
            "Explains WHY specialist chose this approach (transparency for debugging/auditing). "
            "Should cover: intent classification rationale, table dependencies, SKU count logic, warnings. "
            "Example: 'User wants complete family structure. Classified as create intent requiring "
            "3 tables with dependencies: axes depend on family ID, values depend on axis IDs. "
            "Will generate 6 SKU combinations (3 sizes × 2 colors).'"
        )
    )

    # Impact analysis (calculated by specialist from schema + data)
    impact_analysis: ImpactAnalysis = Field(
        ...,
        description=(
            "Business impact assessment calculated from database schema + current data state. "
            "Specialist analyzes: row counts, cascade effects, price changes, warnings, examples. "
            "Used for HITL presentation - helps user understand consequences before approval. "
            "See ImpactAnalysis examples for creation, update, and deletion scenarios."
        )
    )

    # LLM-generated execution plan
    execution_plan: ExecutionPlan = Field(
        ...,
        description=(
            "Multi-step execution plan with dependency ordering and time estimates. "
            "Specialist generates steps respecting operation dependencies (topological sort). "
            "Includes rollback behavior, estimated duration, approval requirements. "
            "See ExecutionPlan examples for simple updates and complex multi-table workflows."
        )
    )

    # Metadata
    specialist_name: str | None = Field(
        None,
        description=(
            "Name of specialist that generated this intent (e.g., 'ProductSpecialist', 'MarketingSpecialist'). "
            "Used for logging, debugging, and tracing which specialist handled user request. "
            "Optional but recommended for production systems."
        )
    )
    schema_version: str = Field(
        default="v1",
        description=(
            "Schema version used for planning (enables schema evolution). "
            "Current version: 'v1'. "
            "Future versions (v2, v3) can add fields while maintaining backward compatibility. "
            "Execution layer checks version to apply correct validation/migration logic."
        )
    )


# =============================================================================
# Execution Result
# =============================================================================


class ExecutionResult(BaseModel):
    """Result of executing an OperationIntent (strongly typed for validation).

    Returned by UniversalCRUDTool after executing all steps in ExecutionPlan.
    Tracks created/updated/deleted entities, execution time, errors, and rollback status.

    Examples:
        Successful product family creation:
            ExecutionResult(
                success=True,
                affected_entities=[
                    TableCount(table="product_families", count=1),
                    TableCount(table="variant_axes", count=2),
                    TableCount(table="variant_values", count=5)
                ],
                created_ids=[
                    CreatedEntity(
                        entity_id="550e8400-e29b-41d4-a716-446655440000",
                        entity_name="pet_family",
                        table="product_families",
                        step_number=1
                    ),
                    CreatedEntity(
                        entity_id="660e8400-e29b-41d4-a716-446655440000",
                        entity_name="size_axis",
                        table="variant_axes",
                        step_number=2
                    ),
                    CreatedEntity(
                        entity_id="660e8401-e29b-41d4-a716-446655440000",
                        entity_name="color_axis",
                        table="variant_axes",
                        step_number=2
                    )
                    # ... 5 more CreatedEntity for variant_values
                ],
                execution_time_ms=247,
                steps_completed=3,
                steps_total=3
            )

        Successful bulk price update:
            ExecutionResult(
                success=True,
                affected_entities=[TableCount(table="products", count=156)],
                updated_entities=[
                    UpdatedEntity(
                        entity_id="770e8400-e29b-41d4-a716-446655440000",
                        table="products",
                        updated_fields=["base_price", "price_updated_at"]
                    )
                    # ... 155 more UpdatedEntity records
                ],
                execution_time_ms=1843,
                steps_completed=1,
                steps_total=1
            )

        Failed execution with rollback:
            ExecutionResult(
                success=False,
                affected_entities=[
                    TableCount(table="product_families", count=1),
                    TableCount(table="variant_axes", count=2)
                ],
                created_ids=[
                    CreatedEntity(
                        entity_id="550e8400-e29b-41d4-a716-446655440000",
                        entity_name="pet_family",
                        table="product_families",
                        step_number=1
                    )
                    # Step 1 succeeded, step 2 succeeded, step 3 failed
                ],
                execution_time_ms=158,
                steps_completed=2,
                steps_total=3,
                error_message="Foreign key constraint violation: axis_id does not exist in variant_axes table",
                error_step=3,
                rollback_performed=True
            )
    """

    success: bool = Field(
        ...,
        description=(
            "Execution succeeded (all steps completed without errors). "
            "True: All operations executed successfully, database committed. "
            "False: One or more steps failed, check error_message and error_step for details. "
            "If rollback_performed=True, database state unchanged (transaction rolled back)."
        )
    )

    # Entity tracking (strongly typed models)
    affected_entities: list[TableCount] = Field(
        default_factory=list,
        description=(
            "All tables affected with final row counts (after execution). "
            "Example: [TableCount(table='product_families', count=1), TableCount(table='variant_axes', count=2)]. "
            "Includes tables from all completed steps (even if later steps failed). "
            "Used to show user what actually changed in database."
        )
    )
    created_ids: list[CreatedEntity] = Field(
        default_factory=list,
        description=(
            "List of created entities with generated IDs and semantic names (INSERT operations). "
            "Each CreatedEntity tracks: entity_id (UUID), entity_name (from entity_refs), table, step_number. "
            "Example: CreatedEntity(entity_id='550e8400...', entity_name='pet_family', table='product_families', step_number=1). "
            "Used to reference new entities in subsequent operations or UI feedback. "
            "Empty for UPDATE/DELETE/QUERY operations."
        )
    )
    updated_entities: list[UpdatedEntity] = Field(
        default_factory=list,
        description=(
            "List of updated entities with modified fields (UPDATE operations). "
            "Each UpdatedEntity tracks: entity_id, table, updated_fields (list of field names). "
            "Example: UpdatedEntity(entity_id='770e8400...', table='products', updated_fields=['base_price', 'updated_at']). "
            "Used for audit logging and UI feedback showing what changed. "
            "Empty for INSERT/DELETE/QUERY operations."
        )
    )
    deleted_entities: list[DeletedEntity] = Field(
        default_factory=list,
        description=(
            "List of deleted entities (DELETE operations, soft or hard). "
            "Each DeletedEntity tracks: entity_id, table, soft_delete (True=inactive, False=permanent). "
            "Example: DeletedEntity(entity_id='880e8400...', table='variant_values', soft_delete=True). "
            "Used for audit logging and potential recovery (soft deletes can be reversed). "
            "Empty for INSERT/UPDATE/QUERY operations."
        )
    )

    # Execution metadata
    execution_time_ms: int = Field(
        default=0,
        description=(
            "Actual execution time in milliseconds (total for all steps). "
            "Includes: operation execution, database commits, entity tracking, rollback (if any). "
            "Compare to execution_plan.estimated_duration_ms for performance monitoring. "
            "Example: 247ms for 3-step family creation, 1843ms for 156-row bulk update."
        )
    )
    steps_completed: int = Field(
        default=0,
        description=(
            "Number of steps successfully completed before success/failure. "
            "Success case: steps_completed == steps_total. "
            "Failure case: steps_completed < steps_total (indicates which step failed). "
            "Example: steps_completed=2, steps_total=3 → step 3 failed after steps 1-2 succeeded."
        )
    )
    steps_total: int = Field(
        default=0,
        description=(
            "Total number of steps in execution plan. "
            "Should match len(execution_plan.steps). "
            "Used with steps_completed to show progress percentage: (steps_completed / steps_total) * 100."
        )
    )

    # Error handling
    error_message: str | None = Field(
        None,
        description=(
            "Error message if execution failed (None if success=True). "
            "Contains detailed error information for debugging and user feedback. "
            "Examples: "
            "'Foreign key constraint violation: family_id does not exist in product_families', "
            "'Unique constraint violation: SKU BOTTLE-PET-500ML-CLEAR already exists', "
            "'Permission denied: user lacks INSERT permission on variant_axes table'. "
            "Should be user-friendly but technically accurate."
        )
    )
    error_step: int | None = Field(
        None,
        description=(
            "Step number that failed (None if success=True). "
            "1-indexed to match ExecutionStep.step_number. "
            "Example: error_step=3 → third step failed (operations[2] in change_spec). "
            "Used to identify exactly which operation caused failure for debugging."
        )
    )
    rollback_performed: bool = Field(
        default=False,
        description=(
            "Was database transaction rolled back after failure? "
            "True: All changes undone, database state unchanged (if ExecutionStep.rollback_on_failure=True). "
            "False: Partial changes committed (if rollback_on_failure=False or commit already happened). "
            "Safety: True is default for atomicity, False only for non-critical operations."
        )
    )


# =============================================================================
# Helper Functions
# =============================================================================


def create_simple_intent(
    intent_type: Literal["create", "read", "update", "delete"],
    table: str,
    entities: list[dict[str, Any]] | None = None,
    summary: str = "Operation",
) -> OperationIntent:
    """Helper to create simple single-table OperationIntent.

    Convenience function for testing or simple operations that don't require
    complex multi-table dependencies, impact analysis, or custom execution plans.

    Args:
        intent_type: Operation type - 'create', 'read', 'update', or 'delete'
        table: Target table name (e.g., 'product_families', 'variant_axes')
        entities: List of entities to insert (CREATE only, optional for others)
        summary: Human-readable operation summary (defaults to "Operation")

    Returns:
        Minimal OperationIntent with single operation and basic impact analysis.

    Examples:
        Create 2 product families:
            intent = create_simple_intent(
                intent_type="create",
                table="product_families",
                entities=[
                    {"name": "PET Bottles", "sku_prefix": "BOTTLE-PET", "base_price": 25.0},
                    {"name": "HDPE Containers", "sku_prefix": "CONT-HDPE", "base_price": 30.0}
                ],
                summary="Create 2 new product families"
            )

        Query all active families:
            intent = create_simple_intent(
                intent_type="read",
                table="product_families",
                summary="Fetch all active product families"
            )

        Update family base price:
            intent = create_simple_intent(
                intent_type="update",
                table="product_families",
                summary="Update PET Bottles base price to ₹30"
            )

    Note:
        For complex multi-table operations with dependencies, construct OperationIntent manually
        instead of using this helper. This function is optimized for simple single-table use cases.
    """
    # Map intent_type to op_type (create→insert, read→query, update→update, delete→delete)
    op_type_map = {"create": "insert", "read": "query", "update": "update", "delete": "delete"}
    operation = Operation(
        op_type=op_type_map.get(intent_type, intent_type),  # type: ignore[arg-type]
        table=table,
        new_entities=entities if intent_type == "create" else None,
        description=f"{intent_type.upper()} on {table}",
    )

    entity_count = len(entities or [])
    return OperationIntent(
        intent_type=intent_type,
        change_spec=ChangeSpecification(operations=[operation]),
        user_request_summary=summary,
        reasoning=f"Simple {intent_type} operation on {table} table with {entity_count} entities",
        impact_analysis=ImpactAnalysis(
            business_impact_summary=f"Will {intent_type} {entity_count} entities in {table}",
            affected_tables=[TableCount(table=table, count=entity_count)] if entity_count > 0 else [],
        ),
        execution_plan=ExecutionPlan(
            steps=[
                ExecutionStep(
                    step_number=1,
                    description=f"{intent_type.upper()} {entity_count} entities in {table}",
                    operation_index=0,  # Reference first (and only) operation
                )
            ],
            estimated_duration_ms=50 + (entity_count * 10),  # 50ms base + 10ms per entity
            requires_approval=(intent_type != "read"),  # Auto-approve read-only queries
        ),
    )
