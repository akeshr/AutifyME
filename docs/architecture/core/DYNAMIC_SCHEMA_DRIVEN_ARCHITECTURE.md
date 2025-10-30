# Dynamic Schema-Driven Architecture

**Date:** October 29, 2025
**Last Updated:** October 30, 2025
**Status:** ✅ Complete - Production Ready (Phase 2C+2D+2E)
**Replaces:** Static discriminated union pattern (Phase 2B)
**Related:**
- [SPECIALIST_BUILD_UP_PLAN.md](../workflows/SPECIALIST_BUILD_UP_PLAN.md) - Phase 2C+2D+2E Complete
- [EXECUTABLE_SCHEMA_COMPLETE.md](../tech/EXECUTABLE_SCHEMA_COMPLETE.md) - Implementation Details & Test Coverage

---

## Executive Summary

**Problem:** Current CRUD architecture hard-codes table names, operation types, and routing logic. Adding new tables/operations requires code deployment.

**Solution:** Schema-driven architecture where:
- Database schema is runtime metadata (not hard-coded)
- Specialist generates generic `OperationIntent` (not 7 hard-coded draft types)
- Single universal tool executes any operation against any table
- Business rules stored as metadata, executed dynamically
- LLM reasons about schema, plans operations autonomously

**Impact:**
- ✅ Add new tables → update schema metadata only (no code changes)
- ✅ New operations → LLM generates appropriate intent (no new draft types)
- ✅ Schema evolution → version-controlled, backward compatible
- ✅ Future-proof for 50+ tables, unlimited operation patterns

**Key Insight:** Modern LLMs can reason about database schemas dynamically. Don't hard-code what LLMs can infer.

---

## Current Architecture (Phase 2B - Static)

### Problems Identified

**Issue 1: Hard-Coded Draft Types**
```python
# 7 draft types enumerated
ProductArchitectureResponse = Union[
    ProductArchitectureDraft,
    VariantAdditionDraft,
    AxisAdditionDraft,
    FamilyUpdateDraft,
    ProductQueryDraft,
    ProductDeletionDraft,
    AmbiguousDraft,
]

# Adding "BundleCreation" operation → Need new draft type → Code deployment
```

**Issue 2: Hard-Coded Tools**
```python
# 6 specialized tools
create_product_family()
add_variant_values()
add_variant_axis()
update_product_fields()
query_product_data()
delete_product_data()

# Adding product_warranties table → Update 3+ tools → Code changes
```

**Issue 3: Hard-Coded Routing**
```python
# PM routing logic
match draft_type:
    case "variant_addition": await add_variant_values(...)
    case "axis_addition": await add_variant_axis(...)
    # New operation → Add new case → Code deployment
```

**Issue 4: Schema Knowledge in Code**
```python
# Table/column names hard-coded in tools
async def add_variant_values(...):
    result = await storage.query(
        "SELECT id FROM variant_axes WHERE name = ?"  # ← Hard-coded
    )
```

---

## New Architecture (Phase 2C - Dynamic)

### Core Principles

**Separate Invariants from Variants**

| Category | Examples | Storage |
|----------|----------|---------|
| **Invariants** (code) | CRUD semantics, transaction patterns, error handling | Python modules |
| **Variants** (data) | Table names, columns, relationships, business rules | Schema metadata |

**Leverage LLM Intelligence**
- LLM queries schema at runtime
- LLM generates execution plans dynamically
- LLM calculates impacts from structure
- No operation enumeration needed

---

## Architecture Components

### 1. Schema Metadata Layer

**Runtime Schema Definition (Data, Not Code)**

```python
class TableSchema(BaseModel):
    """Runtime table metadata."""
    name: str
    columns: dict[str, ColumnSchema]
    primary_key: str
    relationships: list[Relationship]
    business_rules: list[BusinessRule]

class Relationship(BaseModel):
    """Table relationship metadata."""
    type: Literal["parent", "child", "many_to_many"]
    target_table: str
    foreign_key: str
    cascade_delete: bool
    cascade_update: bool

class BusinessRule(BaseModel):
    """Executable business logic metadata."""
    rule_type: str  # "generate_sku", "validate_price", "calculate_total"
    trigger: str  # "before_insert", "after_insert", "before_update"
    handler: str  # Python function name
    parameters: dict[str, Any]

class SchemaRegistry:
    """Version-controlled schema registry."""
    version: str
    tables: dict[str, TableSchema]

    @classmethod
    def get_version(cls, version: str = "latest") -> "SchemaRegistry":
        """Load schema by version."""

    def evolve(
        self,
        add_tables: list[TableSchema] = [],
        migrations: list[Migration] = []
    ) -> "SchemaRegistry":
        """Create new schema version."""
```

**Example Schema Definition:**

```python
# Version-controlled in: agents/src/autifyme_agents/schemas/registry/product_catalog_v1.json

{
    "version": "v1",
    "tables": {
        "product_families": {
            "name": "product_families",
            "columns": {...},
            "relationships": [],
            "business_rules": []
        },
        "variant_axes": {
            "name": "variant_axes",
            "relationships": [
                {
                    "type": "parent",
                    "target_table": "product_families",
                    "foreign_key": "product_family_id",
                    "cascade_delete": true
                }
            ],
            "business_rules": [
                {
                    "rule_type": "generate_entities",
                    "trigger": "after_insert",
                    "handler": "generate_sku_explosion",
                    "parameters": {"scope": "new_axis"}
                }
            ]
        }
    }
}
```

---

### 2. Generic Intent Model (Replaces 7 Draft Types)

**Single Universal Intent**

```python
class OperationIntent(BaseModel):
    """Universal operation specification - works for ANY table/operation."""

    # Operation classification
    intent_type: Literal["create", "read", "update", "delete"]

    # What's changing (schema-agnostic)
    change_spec: ChangeSpecification

    # Human context (for HITL presentation)
    user_request_summary: str
    reasoning: str

    # Impact analysis (calculated by specialist from schema + data)
    impact_analysis: ImpactAnalysis

    # LLM-generated execution plan
    execution_plan: ExecutionPlan


class ChangeSpecification(BaseModel):
    """Generic change specification."""

    domain: str  # "product_catalog", "marketing_content", "inventory"
    operations: list[Operation]  # Multiple tables can be affected


class Operation(BaseModel):
    """Single table operation."""

    op_type: Literal["insert", "update", "delete", "query"]
    table: str  # Validated against schema at runtime

    # For INSERT
    new_entities: list[dict[str, Any]] | None = None

    # For UPDATE
    target_filter: dict[str, Any] | None = None
    field_updates: dict[str, Any] | None = None

    # For DELETE
    delete_filter: dict[str, Any] | None = None
    soft_delete: bool = True

    # For READ
    query_filter: dict[str, Any] | None = None
    include_relations: list[str] = []

    # Dependency ordering (for multi-table atomicity)
    depends_on: list[int] = []  # Operation indices


class ImpactAnalysis(BaseModel):
    """Dynamic impact calculation."""

    affected_tables: dict[str, int]  # table → row_count
    new_entities_count: dict[str, int]
    updated_entities_count: dict[str, int]
    deleted_entities_count: dict[str, int]

    business_impact_summary: str
    warnings: list[str]
    examples: list[str]


class ExecutionPlan(BaseModel):
    """Multi-step execution plan with dependencies."""

    steps: list[ExecutionStep]
    estimated_duration_ms: int
    requires_approval: bool = True


class ExecutionStep(BaseModel):
    """Atomic execution step."""

    step_number: int
    description: str  # Human-readable
    operation: Operation
    rollback_on_failure: bool = True
```

---

### 3. Universal CRUD Tool (Single Tool for Everything)

**Replaces 6 Specialized Tools**

```python
@tool("execute_database_operation")
async def execute_database_operation(
    intent: dict,  # OperationIntent serialized
    schema_version: str = "v1",
) -> ExecutionResult:
    """
    Universal database operation executor.

    Schema-driven, validates against runtime metadata.
    Handles ANY table, ANY operation, with ZERO code changes.

    Examples:
    - Create product family → operations on 9 tables
    - Add variant value → variant_values + products tables
    - Add warranty → product_warranties table (future)
    - Create bundle → product_bundles + bundle_items (future)

    Args:
        intent: OperationIntent with execution plan
        schema_version: Schema version to validate against

    Returns:
        ExecutionResult with affected entities and created IDs
    """

    # Parse and validate
    operation_intent = OperationIntent(**intent)

    # Load schema
    schema = SchemaRegistry.get_version(schema_version)

    # Validate against schema
    validator = SchemaValidator(schema)
    validation_result = validator.validate(operation_intent.change_spec)

    if not validation_result.valid:
        raise ToolException(f"Invalid operation: {validation_result.errors}")

    # Execute with dependency resolution
    executor = OperationExecutor(storage, schema)

    try:
        result = await executor.execute_plan(
            plan=operation_intent.execution_plan,
            rollback_on_error=True,
        )

        return ExecutionResult(
            success=True,
            affected_entities=result.affected_entities,
            created_ids=result.created_ids,
            execution_time_ms=result.execution_time_ms,
        )

    except Exception as e:
        logger.error("Operation execution failed", exc_info=True)
        raise ToolException(f"Execution failed: {str(e)}") from e
```

---

### 4. Schema-Aware Operation Executor

**Core Execution Engine**

```python
class OperationExecutor:
    """Executes operations with dynamic schema awareness."""

    def __init__(self, storage: StorageInterface, schema: SchemaRegistry):
        self.storage = storage
        self.schema = schema

    async def execute_plan(
        self, plan: ExecutionPlan, rollback_on_error: bool = True
    ) -> ExecutionResult:
        """Execute multi-step plan with dependency resolution."""

        completed_steps = []
        created_ids = {}

        try:
            # Topological sort by dependencies
            sorted_steps = self._resolve_dependencies(plan.steps)

            for step in sorted_steps:
                # Execute operation
                result = await self._execute_operation(
                    step.operation,
                    created_ids  # Context for reference resolution
                )
                completed_steps.append((step, result))

                # Store IDs for dependent operations
                if step.operation.op_type == "insert" and result.get("ids"):
                    created_ids[step.step_number] = result["ids"]

                # Trigger business rules
                await self._trigger_business_rules(
                    step.operation, result, trigger="after"
                )

            return ExecutionResult(
                success=True,
                affected_entities=self._count_affected(completed_steps),
                created_ids=created_ids,
            )

        except Exception as e:
            if rollback_on_error:
                await self._rollback(completed_steps)
            raise

    async def _execute_operation(
        self, operation: Operation, context: dict
    ) -> dict:
        """Execute single operation with schema validation."""

        # Get table schema dynamically
        table_schema = self.schema.get_table(operation.table)

        # Route to appropriate handler
        handlers = {
            "insert": self._execute_insert,
            "update": self._execute_update,
            "delete": self._execute_delete,
            "query": self._execute_query,
        }

        handler = handlers[operation.op_type]
        return await handler(operation, table_schema, context)

    async def _execute_insert(
        self, operation: Operation, schema: TableSchema, context: dict
    ) -> dict:
        """Generic insert with relationship resolution."""

        created_ids = []

        for entity in operation.new_entities:
            # Resolve foreign key references dynamically
            # Example: {"product_family_id": "$step_1.family_id"}
            #       → {"product_family_id": "uuid-123"}
            resolved_entity = self._resolve_references(entity, schema, context)

            # Validate against schema
            validated = self._validate_entity(resolved_entity, schema)

            # Insert
            result = await self.storage.insert(operation.table, validated)
            created_ids.append(result["id"])

        return {"ids": created_ids, "count": len(created_ids)}

    def _resolve_references(
        self, entity: dict, schema: TableSchema, context: dict
    ) -> dict:
        """
        Resolve foreign key references from execution context.

        Enables multi-step operations with dependencies:
        Step 1: INSERT variant_axis → returns axis_id
        Step 2: INSERT variant_values with {"variant_axis_id": "$step_1.axis_id"}
        """
        resolved = entity.copy()

        for key, value in entity.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to previous step's result
                step_ref, field_ref = value[1:].split(".")
                step_num = int(step_ref.replace("step_", ""))
                resolved[key] = context[step_num][field_ref]

        return resolved

    async def _trigger_business_rules(
        self, operation: Operation, result: dict, trigger: str
    ) -> None:
        """Execute business rules (e.g., SKU generation, price calculations)."""

        table_schema = self.schema.get_table(operation.table)

        for rule in table_schema.business_rules:
            if rule.trigger == f"{trigger}_{operation.op_type}":
                # Execute handler dynamically
                handler = BusinessRuleHandlers.get(rule.handler)
                await handler(
                    storage=self.storage,
                    operation=operation,
                    result=result,
                    parameters=rule.parameters,
                    schema=self.schema,
                )
```

---

### 5. Specialist Integration (Schema-Aware Planning)

**Specialist Tool: Query Schema**

```python
@tool("get_product_schema")
async def get_product_schema(version: str = "latest") -> dict:
    """
    Retrieve product catalog schema.

    Returns:
        Complete schema with tables, relationships, business rules.
        Specialist uses this to plan operations dynamically.
    """
    schema = SchemaRegistry.get_version(version)
    return schema.to_dict()
```

**Specialist Prompt Enhancement:**

```markdown
## Schema-Driven Operation Planning

You have access to the complete product catalog schema via `get_product_schema` tool.

### Planning Process

**For ANY user request:**

1. **Query Schema** (if not cached):
   - Get current table structure
   - Understand relationships
   - Review business rules

2. **Analyze Request**:
   - Determine affected tables
   - Identify operation types (insert/update/delete/query)
   - Calculate dependencies (parent tables first)

3. **Generate OperationIntent**:
   - Classify intent_type (create/read/update/delete)
   - Build operations list with dependencies
   - Calculate impact analysis from schema + current data
   - Create human-readable execution plan

### Examples

**Example 1: "Add 2L capacity"**

1. Query schema → see variant_axes, variant_values, products tables
2. Query current family → get existing structure
3. Generate:
```json
{
  "intent_type": "create",
  "change_spec": {
    "domain": "product_catalog",
    "operations": [
      {
        "op_type": "insert",
        "table": "variant_values",
        "new_entities": [
          {"value": "2L", "sku_code": "2L", "variant_axis_id": "$existing.capacity_axis_id"}
        ]
      },
      {
        "op_type": "insert",
        "table": "products",
        "new_entities": [
          {"sku": "BOTTLE-BLK-2L", "variant_values": ["BLK", "2L"]},
          {"sku": "BOTTLE-WHT-2L", "variant_values": ["WHT", "2L"]}
        ],
        "depends_on": [0]
      }
    ]
  },
  "impact_analysis": {
    "new_entities_count": {"variant_values": 1, "products": 2},
    "business_impact_summary": "Will create 2 new SKUs for the 2L capacity",
    "examples": ["BOTTLE-BLK-2L", "BOTTLE-WHT-2L"]
  }
}
```

**Example 2: "Add product warranty feature" (future table)**

Schema now includes `product_warranties` table → Specialist automatically:
1. Sees new table in schema
2. Generates appropriate operations
3. No code changes needed
```

---

### 6. PM Workflow (Simplified)

**Generic Intent Handling (No Hard-Coded Routing)**

```python
# PM receives OperationIntent (single type, not 7!)
specialist_result: OperationIntent = await delegate_to_specialist(...)

# Present impact analysis (generic template)
await present_for_approval(
    f"""
    {specialist_result.user_request_summary}

    IMPACT:
    {specialist_result.impact_analysis.business_impact_summary}

    CHANGES:
    {format_impact_table(specialist_result.impact_analysis)}

    WARNINGS:
    {format_warnings(specialist_result.impact_analysis.warnings)}

    EXAMPLES:
    {format_examples(specialist_result.impact_analysis.examples)}

    REASONING:
    {specialist_result.reasoning}

    Approve?
    """
)

# Execute (single universal tool)
result = await execute_database_operation(
    intent=specialist_result.model_dump(),
    schema_version="v1",
)
```

**PM Responsibilities:**
- ✅ Generic HITL presentation
- ✅ Single tool invocation
- ✅ Error handling

**PM Does NOT:**
- ❌ Hard-code operation types
- ❌ Route based on draft_type
- ❌ Know table names
- ❌ Convert data formats

---

## Future-Proofing Examples

### Scenario 1: Add Product Warranties Table

**Current System (Static):**
```python
# Required changes:
1. Add WarrantyDraft type → code change
2. Update ProductArchitectureResponse union → code change
3. Add create_warranty tool → code change
4. Update PM routing → code change
5. Deploy all changes

Total: 4 files changed, deployment required
```

**New System (Dynamic):**
```python
# Required changes:
1. Update schema metadata:
   PRODUCT_SCHEMA_V2 = PRODUCT_SCHEMA_V1.evolve(
       add_tables=[
           TableSchema(
               name="product_warranties",
               columns={...},
               relationships=[...]
           )
       ]
   )

2. That's it! No code deployment.

# Specialist automatically:
- Sees new table via get_product_schema()
- Generates appropriate OperationIntent
- Tool validates against new schema
- Tool executes insert/update/delete

Total: 1 JSON file changed, no code deployment
```

---

### Scenario 2: New Operation Type (Bundle Creation)

**Current System (Static):**
```python
# Required changes:
1. Add BundleCreationDraft type → code change
2. Update union → code change
3. Add create_bundle tool → code change
4. Update PM routing → code change
5. Update specialist prompt → prompt change
6. Deploy

Total: 5 changes, deployment required
```

**New System (Dynamic):**
```python
# Required changes:
NONE!

# Specialist generates:
OperationIntent(
    intent_type="create",
    change_spec=ChangeSpecification(
        operations=[
            Operation(
                op_type="insert",
                table="product_bundles",
                new_entities=[{...}]
            ),
            Operation(
                op_type="insert",
                table="bundle_items",
                new_entities=[{...}],
                depends_on=[0]
            )
        ]
    )
)

# Tool executes it (validates against schema, creates entities)

Total: 0 changes, works immediately
```

---

### Scenario 3: Add Price Validation Rule

**Current System (Static):**
```python
# Required changes:
1. Update update_product_fields tool with validation logic
2. Hard-code max_price check
3. Deploy

Total: 1 tool modified, deployment required
```

**New System (Dynamic):**
```python
# Required changes:
1. Add business rule to schema:
   PRODUCT_SCHEMA.tables["products"].business_rules.append(
       BusinessRule(
           rule_type="validation",
           trigger="before_insert",
           handler="validate_price_range",
           parameters={"max_multiplier": 10}
       )
   )

2. Implement reusable handler (one-time):
   class BusinessRuleHandlers:
       @staticmethod
       async def validate_price_range(operation, parameters, **kwargs):
           # Validation logic
           pass

Total: Schema metadata update + reusable handler (used for all price validations)
```

---

## Benefits Summary

### Compared to Static Architecture

| Aspect | Static (Phase 2B) | Dynamic (Phase 2C) |
|--------|------------------|-------------------|
| **Draft Types** | 7 hard-coded | 1 generic (OperationIntent) |
| **Tools** | 6 specialized | 1 universal |
| **Schema Knowledge** | Hard-coded in tools | Runtime metadata |
| **New Tables** | Update 3+ tools + drafts | Update schema JSON only |
| **New Operations** | Add draft + tool + routing | LLM generates intent |
| **Business Rules** | Hard-coded in tools | Metadata-driven, reusable |
| **PM Routing** | match/case on 7 types | Generic presentation |
| **LLM Utilization** | Low (recipe following) | High (schema reasoning) |
| **Future-Proof** | ❌ Requires code changes | ✅ Metadata-only updates |
| **Complexity** | Medium (7 types × 6 tools) | Low (1 type × 1 tool) |

---

## Implementation Plan

See [SPECIALIST_BUILD_UP_PLAN.md - Phase 2C](../workflows/SPECIALIST_BUILD_UP_PLAN.md#phase-2c-dynamic-schema-driven-crud-8-10-hours) for detailed implementation checklist.

### High-Level Phases

**Phase 1: Schema Metadata Layer** (3 hours)
- Define schema models (TableSchema, Relationship, BusinessRule)
- Extract product catalog schema as JSON
- Implement SchemaRegistry with versioning
- Unit tests for schema loading/validation

**Phase 2: Universal Tool** (3 hours)
- Implement execute_database_operation tool
- Build OperationExecutor with dependency resolution
- Implement reference resolution ($step_N.field syntax)
- Business rule trigger system

**Phase 3: Intent Models** (1 hour)
- Define OperationIntent, ChangeSpecification, Operation models
- Replace 7 draft types with single Intent
- Update response_format

**Phase 4: Specialist Integration** (2 hours)
- Add get_product_schema tool
- Update specialist prompt with schema-driven planning
- Remove hard-coded operation classification
- Teach impact calculation from schema

**Phase 5: PM Simplification** (1 hour)
- Remove hard-coded routing (7 case statements)
- Generic HITL presentation template
- Single tool invocation pattern

**Phase 6: Testing** (2 hours)
- Unit tests for OperationExecutor
- E2E tests for all 7 current operations
- Future-proofing test (add fake table, verify works)
- Performance benchmarks

**Phase 7: Migration** (1 hour)
- Migrate existing 9 tables to schema metadata
- Migrate business rules (SKU generation)
- Backward compatibility verification
- Documentation updates

---

## Success Metrics

**After Implementation:**

1. ✅ **Zero Code Deployment for New Tables**
   - Add `product_warranties` table via schema metadata
   - Specialist automatically handles warranty CRUD
   - Tool validates and executes

2. ✅ **Zero Code Deployment for New Operations**
   - User requests bundle creation
   - Specialist generates OperationIntent
   - Tool executes without code changes

3. ✅ **Schema Evolution**
   - v1 → v2 schema migration
   - Both versions supported simultaneously
   - Backward compatibility maintained

4. ✅ **LLM Reasoning Quality**
   - Specialist calculates impact from schema
   - Dependency ordering correct (90%+ accuracy)
   - Examples generated correctly

5. ✅ **Performance**
   - No regression in execution time
   - Schema metadata cached efficiently
   - Tool execution < 2x current latency

---

## Risk Mitigation

### Risk 1: LLM Generates Invalid Operations

**Mitigation:**
- Schema validation before execution (fail fast)
- Dry-run mode for testing
- LLM self-review prompt ("validate your plan against schema")

### Risk 2: Complex Multi-Table Operations

**Mitigation:**
- Dependency resolution algorithm (topological sort)
- Rollback on failure (all-or-nothing atomicity)
- Execution plan debugging (log each step)

### Risk 3: Business Rule Complexity

**Mitigation:**
- Start with simple rules (SKU generation)
- Reusable handler library
- Fallback to specialist for complex calculations

### Risk 4: Schema Versioning Conflicts

**Mitigation:**
- Explicit version parameter in tool calls
- Schema evolution with migrations
- Version compatibility matrix

---

## Related Documentation

- [SPECIALIST_BUILD_UP_PLAN.md](../workflows/SPECIALIST_BUILD_UP_PLAN.md) - Phase 2C implementation
- [PRODUCT_SPECIALIST_CRUD_IMPLEMENTATION.md](../PRODUCT_SPECIALIST_CRUD_IMPLEMENTATION.md) - Current static implementation (Phase 2B)
- [PROMPT_ENGINEERING_STANDARDS.md](../tech/PROMPT_ENGINEERING_STANDARDS.md) - Prompt design for schema reasoning

---

## Appendix: Code Examples

### Example: Schema Metadata Definition

```json
{
  "version": "v1",
  "domain": "product_catalog",
  "tables": {
    "variant_axes": {
      "name": "variant_axes",
      "columns": {
        "id": {"type": "uuid", "primary_key": true},
        "product_family_id": {"type": "uuid", "nullable": false},
        "name": {"type": "varchar", "max_length": 100},
        "display_label": {"type": "varchar", "max_length": 200},
        "sort_order": {"type": "integer", "default": 0}
      },
      "relationships": [
        {
          "type": "parent",
          "target_table": "product_families",
          "foreign_key": "product_family_id",
          "cascade_delete": true
        }
      ],
      "business_rules": [
        {
          "rule_type": "generate_entities",
          "trigger": "after_insert",
          "handler": "generate_sku_explosion_for_new_axis",
          "parameters": {
            "scope": "new_axis",
            "warn_threshold": 100
          }
        }
      ]
    }
  }
}
```

### Example: Specialist-Generated Intent

```python
# User: "Add 2L capacity to water bottle family"

# Specialist generates:
OperationIntent(
    intent_type="create",
    change_spec=ChangeSpecification(
        domain="product_catalog",
        operations=[
            Operation(
                op_type="insert",
                table="variant_values",
                new_entities=[
                    {
                        "variant_axis_id": "$query.capacity_axis_id",
                        "value": "2L",
                        "sku_code": "2L",
                        "display_label": "2 Liter",
                        "price_adjustment": 5.00,
                        "sort_order": 3
                    }
                ]
            ),
            Operation(
                op_type="insert",
                table="products",
                new_entities=[
                    {
                        "product_family_id": "$query.family_id",
                        "sku": "BOTTLE-BLK-2L",
                        "name": "Water Bottle - Black - 2L",
                        "price": 30.00,
                        "variant_values": ["BLK", "2L"]
                    },
                    {
                        "product_family_id": "$query.family_id",
                        "sku": "BOTTLE-WHT-2L",
                        "name": "Water Bottle - White - 2L",
                        "price": 30.00,
                        "variant_values": ["WHT", "2L"]
                    }
                ],
                depends_on=[0]  # Wait for variant_value insert
            )
        ]
    ),
    user_request_summary="Add 2L capacity to Water Bottle family",
    reasoning="User wants to add new capacity variant. Existing family has Color axis (Black, White). Adding 2L value requires 2 new SKUs (2L × 2 colors).",
    impact_analysis=ImpactAnalysis(
        affected_tables={"variant_values": 1, "products": 2},
        new_entities_count={"variant_values": 1, "products": 2},
        business_impact_summary="Will create 2 new SKUs for 2L capacity",
        warnings=[],
        examples=["BOTTLE-BLK-2L", "BOTTLE-WHT-2L"]
    ),
    execution_plan=ExecutionPlan(
        steps=[
            ExecutionStep(
                step_number=1,
                description="Insert 2L variant value into Capacity axis",
                operation=operations[0]
            ),
            ExecutionStep(
                step_number=2,
                description="Generate 2 new SKUs for 2L × existing colors",
                operation=operations[1]
            )
        ],
        estimated_duration_ms=150,
        requires_approval=True
    )
)
```

---

**End of Document**
