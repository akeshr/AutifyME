# Dynamic CRUD Access Control

**Date:** January 6, 2025
**Status:** 🔄 Design - Ready for Implementation
**Related:**
- [DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md](../core/DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md) - Base CRUD architecture
- [DOMAIN_DESIGN_GUIDELINES.md](../core/DOMAIN_DESIGN_GUIDELINES.md) - Specialist design patterns
- [ACTUAL_IMPLEMENTATION_ARCHITECTURE.md](../core/ACTUAL_IMPLEMENTATION_ARCHITECTURE.md) - Tool configuration patterns

---

## Executive Summary

**Problem:** Current universal CRUD tool exposes ALL operations (create/read/update/delete) to ALL agents, regardless of their domain responsibilities. LLMs see full operation set in JSON Schema, causing confusion and wasted reasoning tokens.

**Solution:** Dynamic tool factory that creates operation-scoped CRUD tools with:
- **Dynamic Pydantic schemas** - Only relevant fields for allowed operations
- **Context-aware descriptions** - Same field gets different guidance per operation type
- **Table-level access control** - Optional restriction to specific tables
- **Clean LLM interface** - JSON Schema shows only what agent can use

**Impact:**
- ✅ Market Intelligence: Read-only tool (no mutation fields in schema)
- ✅ Product Architecture: Full CRUD tool (all operations)
- ✅ Taxonomy Specialist: Read/write specific tables only
- ✅ Campaign Optimizer: Read + update campaigns (no create/delete)

**Key Insight:** LLMs read JSON Schema to decide which tool to use. Dynamic Pydantic models = dynamic JSON Schema = clearer agent capabilities.

---

## ULTRATHINK: First Principles Analysis

### The Real Problem

**Not just:** "Prevent unauthorized access"
**Actually:** "LLMs waste tokens reasoning about operations they shouldn't consider"

**Why it matters:**
1. OpenAI function calling sends FULL JSON Schema to LLM, not just description
2. Current schema has 8 fields including `impact_analysis`, `change_spec`, `delete_filter`
3. Read-only agents see mutation fields they'll never use
4. LLMs attempt operations outside their domain, fail at execution time

### What We Actually Control

| Layer | What We Control | How It Affects LLM |
|-------|----------------|-------------------|
| **Tool Name** | String identifier | Tool selection in multi-tool scenarios |
| **Tool Description** | Natural language summary | Primary tool selection signal |
| **Input Schema** | Pydantic BaseModel → JSON Schema | ✅ **CRITICAL** - LLM sees full field list + descriptions |
| **Implementation** | Python validation + execution | Runtime validation (after LLM choice) |

**Critical Insight:** We must control the INPUT SCHEMA to properly guide LLM behavior.

### Semantic Analysis by Operation

**READ operations need:**
- `user_request_summary`, `reasoning` (context)
- `intent_type` (must be "read")
- `query_filter` (WHERE conditions)
- `execution_plan` (multi-step queries)
- **DO NOT NEED:** `impact_analysis` (reads don't impact data), `change_spec` (no mutations)

**CREATE/UPDATE/DELETE operations need:**
- `user_request_summary`, `reasoning` (context)
- `intent_type` (create/update/delete)
- `change_spec` (what to mutate)
- `impact_analysis` (REQUIRED for HITL approval)
- `execution_plan` (multi-step mutations with dependencies)

**Current Problem:** Unified schema forces read-only tools to carry unused mutation fields.

**ULTRATHINK Solution:** Different Pydantic schemas for different operation types.

---

## Current Architecture

### Static Unified Schema

```python
class ExecuteDatabaseOperationInput(BaseModel):
    """One schema for all operations."""
    model_config = {"extra": "forbid"}

    intent_type: str = Field(
        ...,
        description="High-level intent (create/read/update/delete)"
    )
    change_spec: dict[str, Any] = Field(
        ...,
        description="Specification of table operations"
    )
    user_request_summary: str = Field(...)
    reasoning: str = Field(...)
    impact_analysis: dict[str, Any] = Field(
        ...,
        description="Impact assessment for HITL"
    )
    execution_plan: dict[str, Any] = Field(...)
    specialist_name: str | None = Field(default=None)
    schema_version: str = Field(default="v1")
```

### Problems

**Issue 1: Semantic Mismatch**
- Read-only agents must provide `impact_analysis` field (no semantic meaning for reads)
- Field marked required, but read operations ignore it

**Issue 2: LLM Confusion**
- JSON Schema shows all 8 fields to all agents
- Market Intelligence specialist sees `change_spec`, `impact_analysis` (shouldn't mutate)
- Descriptions generic, don't reflect operation-specific semantics

**Issue 3: No Table-Level Control**
- All agents see all tables in schema
- Taxonomy specialist can theoretically query campaign data
- No explicit boundary enforcement

**Issue 4: Tool Discovery Overhead**
- Single tool name: `execute_database_operation`
- LLM must read full description + schema to understand capabilities
- Multi-tool scenarios: unclear which tool for which operation

---

## Solution Architecture

### Dynamic Tool Factory Pattern

**Core Principle:** Generate operation-specific Pydantic schemas at agent creation time.

```python
def create_database_tool(
    storage: StorageInterface,
    operations: list[Literal["read", "create", "update", "delete"]],
    tables: list[str] | None = None,
    tool_name_suffix: str | None = None,
) -> BaseTool:
    """
    Create operation-scoped database tool with dynamic schema.

    Args:
        storage: Storage interface for database operations
        operations: Allowed operations for this tool instance
        tables: Optional whitelist of accessible tables
        tool_name_suffix: Optional suffix for tool name

    Returns:
        StructuredTool with operation-specific schema

    Examples:
        # Read-only for market intelligence
        read_tool = create_database_tool(storage, operations=["read"])

        # Full CRUD for product architecture
        crud_tool = create_database_tool(
            storage,
            operations=["create", "read", "update", "delete"]
        )

        # Table-scoped for taxonomy specialist
        taxonomy_tool = create_database_tool(
            storage,
            operations=["read", "create", "update"],
            tables=["categories", "category_product_mappings"]
        )
    """
```

### Dynamic Schema Generation

**Function:** `_create_operation_input_schema(operations: list[str]) -> type[BaseModel]`

Uses `pydantic.create_model()` to dynamically generate schema classes:

```python
from pydantic import Field, create_model, ConfigDict

def _create_operation_input_schema(operations: list[str]) -> type[BaseModel]:
    """Generate Pydantic schema for specific operations."""

    # Common fields for all operations
    fields = {
        'user_request_summary': (
            str,
            Field(..., description='Summary of user original request')
        ),
        'reasoning': (
            str,
            Field(..., description='Why specialist classified this way')
        ),
    }

    # intent_type with operation-specific description
    allowed_ops = ', '.join(operations)
    fields['intent_type'] = (
        str,
        Field(
            ...,
            description=f'Intent type. Allowed: {allowed_ops}'
        )
    )

    # Operation-specific fields
    if 'read' in operations and len(operations) == 1:
        # Read-only: simplified query structure
        fields['query_filter'] = (
            dict[str, Any],
            Field(
                default={},
                description='Filter conditions for query. '
                'E.g., {"id": "123"} or {"category": "electronics"}'
            )
        )
    else:
        # Mutations need full spec
        fields['change_spec'] = (
            dict[str, Any],
            Field(
                ...,
                description='Specification of table operations. '
                'Contains operations array with insert/update/delete specs.'
            )
        )
        fields['impact_analysis'] = (
            dict[str, Any],
            Field(
                ...,
                description='REQUIRED for HITL approval. '
                'Specifies new/updated/deleted entity counts per table.'
            )
        )

    fields['execution_plan'] = (
        dict[str, Any],
        Field(
            ...,
            description='Multi-step execution plan with dependencies'
        )
    )

    fields['specialist_name'] = (
        str | None,
        Field(
            default=None,
            description='Which specialist generated this intent'
        )
    )

    fields['schema_version'] = (
        str,
        Field(
            default='v1',
            description='Schema version to validate against'
        )
    )

    # Create model with config
    model_name = f"{''.join([op.title() for op in operations])}OperationInput"
    return create_model(
        model_name,
        __config__=ConfigDict(extra='forbid'),
        **fields
    )
```

### Schema Variations

**Read-Only Schema (`operations=["read"]`):**

```python
class ReadOperationInput(BaseModel):
    model_config = {"extra": "forbid"}

    user_request_summary: str
    reasoning: str
    intent_type: str  # Description: "Must be 'read'"
    query_filter: dict[str, Any] = {}  # NEW: Simplified for reads
    execution_plan: dict[str, Any]
    specialist_name: str | None = None
    schema_version: str = "v1"

    # NO impact_analysis - reads don't need HITL approval
    # NO change_spec - reads don't mutate data
```

**Full CRUD Schema (`operations=["create", "read", "update", "delete"]`):**

```python
class CreateReadUpdateDeleteOperationInput(BaseModel):
    model_config = {"extra": "forbid"}

    user_request_summary: str
    reasoning: str
    intent_type: str  # Description: "Allowed: create, read, update, delete"
    change_spec: dict[str, Any]  # Full mutation specification
    impact_analysis: dict[str, Any]  # REQUIRED for HITL
    execution_plan: dict[str, Any]
    specialist_name: str | None = None
    schema_version: str = "v1"
```

**Mixed Operations (`operations=["read", "update"]`):**

```python
class ReadUpdateOperationInput(BaseModel):
    model_config = {"extra": "forbid"}

    user_request_summary: str
    reasoning: str
    intent_type: str  # Description: "Allowed: read, update"
    change_spec: dict[str, Any]  # For updates
    impact_analysis: dict[str, Any]  # For update HITL
    execution_plan: dict[str, Any]
    specialist_name: str | None = None
    schema_version: str = "v1"
```

### Tool Naming Strategy

**Default:** `execute_database_operation`

**With suffix:** `execute_database_operation_{suffix}`

Examples:
- `execute_database_operation` (no suffix, full CRUD)
- `execute_database_operation_read_only` (read-only variant)
- `execute_database_operation_products` (product domain scoped)
- `execute_database_operation_campaigns` (campaign domain scoped)

**Rationale:** Consistent naming helps LLMs recognize tool family while suffixes differentiate variants.

### Tool Description Generation

**Function:** `_generate_tool_description(operations: list[str], tables: list[str] | None) -> str`

```python
def _generate_tool_description(
    operations: list[str],
    tables: list[str] | None
) -> str:
    """Generate operation-specific tool description."""

    # Operation description
    if operations == ["read"]:
        op_desc = "Read-only database access. Query entities without modifications."
    elif set(operations) == {"create", "read", "update", "delete"}:
        op_desc = "Full CRUD database access. Create, read, update, and delete entities."
    elif "read" in operations and "update" in operations:
        op_desc = "Database query and update access. Read existing data and modify entities."
    else:
        op_list = ', '.join(operations)
        op_desc = f"Database operations: {op_list}."

    # Table scope
    if tables:
        table_list = ', '.join(tables)
        scope_desc = f" Scoped to tables: {table_list}."
    else:
        scope_desc = " Works across all schema tables."

    # Core capabilities
    capabilities = (
        " Schema-driven execution with dependency resolution, "
        "foreign key reference resolution, and atomic transactions."
    )

    return op_desc + scope_desc + capabilities
```

**Examples:**

```
Read-only database access. Query entities without modifications.
Works across all schema tables. Schema-driven execution with
dependency resolution, foreign key reference resolution, and
atomic transactions.

---

Full CRUD database access. Create, read, update, and delete entities.
Works across all schema tables. Schema-driven execution with
dependency resolution, foreign key reference resolution, and
atomic transactions.

---

Database query and update access. Read existing data and modify entities.
Scoped to tables: campaigns, ad_copies. Schema-driven execution with
dependency resolution, foreign key reference resolution, and
atomic transactions.
```

### Runtime Validation

**Two-layer validation:**

1. **Schema validation** (Pydantic) - Ensures correct structure, required fields
2. **Operation validation** (Runtime) - Ensures `intent_type` matches allowed operations

```python
async def _execute_database_operation_impl(
    # ... parameters from dynamic schema
) -> dict[str, Any]:
    """Implementation shared by all tool variants."""

    # Validate operation is allowed
    if intent_type not in allowed_operations:
        raise ToolException(
            f"Operation '{intent_type}' not allowed for this tool. "
            f"Allowed: {', '.join(allowed_operations)}"
        )

    # Validate table access if restricted
    if allowed_tables is not None:
        for operation in change_spec.operations:
            if operation.table not in allowed_tables:
                raise ToolException(
                    f"Table '{operation.table}' not accessible. "
                    f"Allowed: {', '.join(allowed_tables)}"
                )

    # Proceed with execution (existing universal_crud_tool logic)
    # ...
```

---

## Technical Verification (REPL)

**Verified via Python REPL** (`uv run python -c`):

### Test 1: Dynamic Pydantic Models Work

```python
from pydantic import Field, create_model, ConfigDict

DynamicModel = create_model(
    'ReadOnlyInput',
    user_request=(str, Field(..., description='What user wants')),
    query_filter=(dict, Field(default={}, description='Filter conditions')),
    __config__=ConfigDict(extra='forbid')
)

# ✓ Model created successfully
# ✓ Fields: ['user_request', 'query_filter']
# ✓ Config: {'extra': 'forbid'}
```

### Test 2: StructuredTool Accepts Dynamic Models

```python
from langchain_core.tools import StructuredTool

async def sample_impl(user_request: str, query_filter: dict = {}) -> dict:
    return {'success': True}

tool = StructuredTool.from_function(
    coroutine=sample_impl,
    name='dynamic_tool',
    description='A tool with dynamic schema',
    args_schema=DynamicModel  # <-- Dynamic model
)

# ✓ Tool created: dynamic_tool
# ✓ Args schema: ReadOnlyInput
# ✓ Schema is dynamic model: True
```

### Test 3: JSON Schema Output (What LLM Sees)

```python
import json
schema = DynamicModel.model_json_schema()
print(json.dumps(schema, indent=2))

# Output:
{
  "properties": {
    "user_request": {
      "description": "What user wants",
      "title": "User Request",
      "type": "string"
    },
    "query_filter": {
      "additionalProperties": true,
      "default": {},
      "description": "Filter conditions",
      "title": "Query Filter",
      "type": "object"
    }
  },
  "required": ["user_request"],
  "additionalProperties": false,  # <-- From ConfigDict(extra='forbid')
  "title": "ReadOnlyInput",
  "type": "object"
}

# ✓ Clean JSON Schema with only defined fields
# ✓ additionalProperties: false from config
# ✓ Field descriptions preserved
```

### Test 4: Context-Aware Field Descriptions

```python
# Same field, different descriptions per operation
read_schema = create_custom_schema('read')
create_schema = create_custom_schema('create')

read_schema.model_fields['intent_type'].description
# "Query intent. Must be 'read'. Read-only tool..."

create_schema.model_fields['intent_type'].description
# "Mutation intent. Must be 'create'. Creates new entities..."

# ✓ Same field name, different semantic guidance
# ✓ LLM sees operation-appropriate description
```

**Conclusion:** Pydantic `create_model()` fully supports our architecture requirements.

---

## Agent Configuration Examples

### Market Intelligence Specialist (Read-Only)

```python
from autifyme_agents.tools.universal_crud_tool import create_database_tool

def create_market_intelligence_specialist(storage: StorageInterface) -> dict:
    """Read-only specialist for market research."""

    tools = [
        create_database_tool(
            storage,
            operations=["read"],
            tool_name_suffix="read_only"
        ),
        # ... other read-only tools
    ]

    return {
        "name": "market_intelligence_specialist",
        "description": "Market research and competitive analysis specialist",
        "tools": tools,
        "system_prompt": load_prompt("specialists/market_intelligence.prompt")
    }
```

**Generated Tool:**
- Name: `execute_database_operation_read_only`
- Schema: 6 fields (no `change_spec`, no `impact_analysis`)
- Description: "Read-only database access..."

### Product Architecture Specialist (Full CRUD)

```python
def create_product_architecture_specialist(storage: StorageInterface) -> dict:
    """Full CRUD specialist for product catalog."""

    tools = [
        create_database_tool(
            storage,
            operations=["create", "read", "update", "delete"],
            tables=[
                "product_families",
                "products",
                "variant_axes",
                "variant_values",
                "product_components",
                "product_bundles",
                "component_relationships",
                "bundle_items",
                "bundle_variant_configs"
            ]
        ),
        # ... schema query tools
    ]

    return {
        "name": "product_architecture_specialist",
        "description": "Product structure and variant management specialist",
        "tools": tools,
        "system_prompt": load_prompt("specialists/product_architecture.prompt")
    }
```

**Generated Tool:**
- Name: `execute_database_operation`
- Schema: 8 fields (full CRUD schema)
- Description: "Full CRUD database access..."

### Taxonomy Specialist (Domain-Scoped)

```python
def create_taxonomy_specialist(storage: StorageInterface) -> dict:
    """Category management specialist with scoped access."""

    tools = [
        create_database_tool(
            storage,
            operations=["read", "create", "update"],
            tables=["categories", "category_product_mappings"],
            tool_name_suffix="taxonomy"
        ),
        # ... taxonomy-specific tools
    ]

    return {
        "name": "taxonomy_specialist",
        "description": "Product categorization and taxonomy specialist",
        "tools": tools,
        "system_prompt": load_prompt("specialists/taxonomy.prompt")
    }
```

**Generated Tool:**
- Name: `execute_database_operation_taxonomy`
- Schema: 8 fields (has mutations, scoped to 2 tables)
- Description: "Database query and update access. Scoped to tables: categories, category_product_mappings..."

### Campaign Optimization Specialist (Read + Update)

```python
def create_campaign_optimization_specialist(storage: StorageInterface) -> dict:
    """Campaign performance tuning specialist."""

    tools = [
        create_database_tool(
            storage,
            operations=["read", "update"],
            tables=["campaigns", "ad_copies", "campaign_performance"],
            tool_name_suffix="campaigns"
        ),
        # ... analytics tools
    ]

    return {
        "name": "campaign_optimization_specialist",
        "description": "Campaign performance analysis and optimization",
        "tools": tools,
        "system_prompt": load_prompt("specialists/campaign_optimization.prompt")
    }
```

**Generated Tool:**
- Name: `execute_database_operation_campaigns`
- Schema: 8 fields (mutations allowed, no create/delete)
- Description: "Database query and update access. Scoped to tables: campaigns, ad_copies, campaign_performance..."

---

## Implementation Strategy

### Phase 1: Factory Function (Core)

**File:** `agents/src/autifyme_agents/tools/universal_crud_tool.py`

**Changes:**

1. Add dynamic schema generator: `_create_operation_input_schema(operations)`
2. Add description generator: `_generate_tool_description(operations, tables)`
3. Add tool name generator: `_generate_tool_name(suffix)`
4. Refactor implementation to closure: `_execute_database_operation_impl` captures `allowed_operations`, `allowed_tables`
5. Create factory: `create_database_tool(storage, operations, tables, suffix)`

**Keep existing:** `create_execute_database_operation_tool()` as wrapper for backward compatibility.

### Phase 2: Specialist Updates

**Files:** `agents/src/autifyme_agents/specialists/*.py`

**Changes:**

1. **Product Architecture Specialist:** Use `create_database_tool(storage, ["create", "read", "update", "delete"])`
2. **Market Intelligence Specialist:** (Future) Use `create_database_tool(storage, ["read"])`
3. **Taxonomy Specialist:** (Future) Use `create_database_tool(storage, ["read", "create", "update"], tables=[...])`

### Phase 3: Testing

**File:** `tests/unit/test_dynamic_crud_access_control.py`

**Coverage:**

1. Schema generation for all operation combinations
2. StructuredTool creation with dynamic schemas
3. JSON Schema output validation
4. Runtime operation validation
5. Runtime table access validation
6. Field presence/absence verification
7. Backward compatibility with existing tools

### Phase 4: Documentation

**Files:**

1. Update `DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md` - Add section on access control
2. Update specialist prompts - Mention operation scope in tool descriptions
3. Add migration guide for future specialists

---

## Implementation Checklist

### Core Implementation

- [ ] Implement `_create_operation_input_schema(operations)` in `universal_crud_tool.py`
- [ ] Implement `_generate_tool_description(operations, tables)` in `universal_crud_tool.py`
- [ ] Implement `_generate_tool_name(suffix)` in `universal_crud_tool.py`
- [ ] Refactor `_execute_database_operation_impl` to closure capturing access control params
- [ ] Implement `create_database_tool(storage, operations, tables, suffix)` factory
- [ ] Add runtime operation validation (check `intent_type` against allowed)
- [ ] Add runtime table validation (check `operation.table` against allowed)
- [ ] Keep `create_execute_database_operation_tool()` for backward compatibility

### Specialist Updates

- [ ] Update `product_architecture_specialist.py` to use new factory
- [ ] Test product architecture specialist with full CRUD access
- [ ] Verify backward compatibility (existing workflows continue working)

### Testing

- [ ] Unit tests: Schema generation for read-only operations
- [ ] Unit tests: Schema generation for full CRUD operations
- [ ] Unit tests: Schema generation for mixed operations
- [ ] Unit tests: Tool description generation
- [ ] Unit tests: Tool name generation
- [ ] Unit tests: Runtime operation validation
- [ ] Unit tests: Runtime table validation
- [ ] Unit tests: JSON Schema output verification
- [ ] Integration tests: Product architecture specialist E2E
- [ ] Integration tests: Verify LLM receives correct JSON Schema

### Documentation

- [ ] Update `DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md` with access control section
- [ ] Update `DOMAIN_DESIGN_GUIDELINES.md` with tool configuration examples
- [ ] Add inline documentation in `universal_crud_tool.py`
- [ ] Update specialist prompts with operation scope awareness

### Verification

- [ ] REPL verification: Dynamic Pydantic models work
- [ ] REPL verification: StructuredTool integration works
- [ ] REPL verification: JSON Schema output correct
- [ ] Code review: Hexagonal architecture preserved
- [ ] Code review: Type safety maintained
- [ ] Code review: Error messages actionable for LLMs

---

## Benefits Summary

### For LLMs

**Clarity:**
- JSON Schema shows only relevant fields for agent's role
- Field descriptions contextual to operation type
- No confusion about mutations for read-only agents

**Efficiency:**
- Fewer fields = smaller token usage
- Clearer capabilities = faster tool selection
- Operation validation upfront (schema level, not runtime)

### For Architecture

**Separation of Concerns:**
- Access control at tool boundary (hexagonal architecture)
- Core executor remains operation-agnostic
- Configuration at specialist creation time

**Extensibility:**
- New operation combinations without code changes
- New specialists configure via factory parameters
- Table-level access control for domain boundaries

**Type Safety:**
- Pydantic validates structure at schema level
- Operation-specific schemas enforce semantic correctness
- `model_config = {"extra": "forbid"}` prevents schema drift

### For Specialists

**Clear Boundaries:**
- Each specialist gets exactly what it needs
- Tool names reflect capabilities
- Descriptions match actual permissions

**Domain Focus:**
- Market Intelligence: Read-only across all tables
- Product Architecture: Full CRUD on product domain
- Taxonomy: Read/write categories only
- Campaign Optimizer: Read + update campaigns

---

## Open Questions

### 1. Should we support blacklist mode for tables?

**Current:** Whitelist only (`tables=["categories", "products"]`)
**Alternative:** Blacklist (`exclude_tables=["sensitive_data"]`)

**Recommendation:** Start with whitelist only. Blacklist adds complexity without clear use case.

### 2. How granular for input schema filtering?

**Current:** Include/exclude entire fields (`change_spec`, `impact_analysis`)
**Alternative:** Filter nested fields within `change_spec`

**Recommendation:** Field-level only. Nested filtering violates separation of concerns.

### 3. Should tool names be suffix-based or operation-based?

**Suffix-based:** `execute_database_operation_products`
**Operation-based:** `execute_database_operation_read_only`

**Recommendation:** Support both via `tool_name_suffix` parameter. Let specialist designers choose.

### 4. Should we cache generated schema classes?

**Concern:** Generating new Pydantic class on every specialist creation
**Alternative:** Cache by operation signature

**Recommendation:** Start without caching. Profile if needed. Schema generation is fast.

---

## References

### Internal Documentation

- [DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md](../core/DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md) - Base CRUD architecture
- [DOMAIN_DESIGN_GUIDELINES.md](../core/DOMAIN_DESIGN_GUIDELINES.md) - Specialist patterns
- [ACTUAL_IMPLEMENTATION_ARCHITECTURE.md](../core/ACTUAL_IMPLEMENTATION_ARCHITECTURE.md) - Current tool setup
- [PROMPT_ENGINEERING_STANDARDS.md](./PROMPT_ENGINEERING_STANDARDS.md) - Tool description patterns

### External References

- [Pydantic create_model() docs](https://docs.pydantic.dev/latest/api/main/#pydantic.create_model)
- [LangChain StructuredTool docs](https://python.langchain.com/docs/modules/agents/tools/custom_tools/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling) - JSON Schema format

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2025-01-06 | Initial design | Architecture Team |
