---
name: tool-development
description: Build ATOMIC tools using StructuredTool with Pydantic schemas. Use when creating new tools, refactoring existing tools, or reviewing tool implementations for AutifyME agents.
---

# Tool Development Standards

## Core Principles

**ATOMIC Tools:** Each tool does ONE thing powerfully and completely.
- No partial operations or multi-step orchestration within tools
- Rich, structured return values that enable agent reasoning
- Tools communicate only through defined inputs/outputs

**Always StructuredTool:** All tools must use `StructuredTool.from_function()` with Pydantic schemas.

---

## Tool Template

```python
"""[Tool Name] - One-line purpose description.

[Expanded explanation of what this tool does and when agents should use it.]
"""

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from autifyme_agents.core.tool_error_handler import (
    build_agent_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)


class MyToolInput(BaseModel):
    """Input schema for my_tool."""

    model_config = {"extra": "forbid"}  # Strict validation

    required_field: str = Field(
        ...,  # Required
        description="Clear description of what this field is for"
    )
    optional_field: str | None = Field(
        None,
        description="Description with examples when helpful"
    )


def create_my_tool(dependency: SomeDependency) -> StructuredTool:
    """
    Create my_tool for [specific purpose].

    Args:
        dependency: [What this dependency provides]

    Returns:
        StructuredTool configured for [operation type]
    """

    async def _my_tool_impl(
        required_field: str,
        optional_field: str | None = None,
    ) -> dict[str, Any]:
        """
        [Detailed docstring for agent understanding]

        USE WHEN:
        - [Scenario 1]
        - [Scenario 2]

        NOT FOR:
        - [Anti-pattern 1]
        - [Anti-pattern 2]

        Returns:
            Structured dict with success status and data
        """
        try:
            # Implementation
            result = await dependency.do_something(required_field)

            logger.info(
                f"Operation completed",
                extra={"field": required_field, "result_count": len(result)}
            )

            return build_success_response({
                "data": result,
                "count": len(result),
            })

        except Exception as e:
            logger.error(
                f"Operation failed",
                exc_info=True,
                extra={"field": required_field}
            )
            return build_agent_error_response(
                exception=e,
                context={"field": required_field},
                fallback_type="OPERATION_ERROR",
                fallback_action="Describe what agent should try next"
            )

    return StructuredTool.from_function(
        func=_my_tool_impl,
        name="my_tool",
        description=(
            "One-line description. "
            "USE WHEN: [trigger conditions]. "
            "RETURNS: [what agent gets back]. "
            "NOT FOR: [anti-patterns]."
        ),
        args_schema=MyToolInput,
        coroutine=_my_tool_impl,
    )
```

---

## Error Handling Pattern

Tools NEVER raise exceptions. Always return structured dicts:

```python
# Success response
return build_success_response({
    "data": results,
    "count": len(results),
    "metadata": {"key": "value"}
})
# Returns: {"success": True, "data": [...], "count": 5, ...}

# Error response
return build_agent_error_response(
    exception=e,
    context={"table": table, "operation": "query"},
    fallback_type="QUERY_ERROR",
    fallback_action="Verify table name. Check schema with inspect_schema tool."
)
# Returns: {"success": False, "error": "QUERY_ERROR: ...", "error_type": "QUERY_ERROR", ...}
```

**Error types** (from `core.tool_error_handler`):
- `ACCESS_DENIED` - Permission issues
- `TABLE_ERROR`, `INVALID_COLUMN`, `INVALID_RELATION` - Schema issues
- `CONSTRAINT_VIOLATION`, `MISSING_REFERENCE` - Data integrity
- `CONNECTION_ERROR`, `RATE_LIMIT_ERROR` - Network/API issues
- `NOT_FOUND`, `INVALID_INPUT`, `INVALID_FILE` - Input issues

---

## Input Schema Best Practices

```python
class ReadDataInput(BaseModel):
    """Input schema with comprehensive field documentation."""

    model_config = {"extra": "forbid"}  # Reject unknown fields

    # Required field with validation
    table: str = Field(
        ...,
        description="Table name (e.g., 'products', 'categories')"
    )

    # Optional with clear purpose
    filters: dict[str, Any] | None = Field(
        None,
        description=(
            "[EXACT MATCH] Case-sensitive. Use for IDs, booleans. "
            "Examples: {'is_active': True}, {'id': 'uuid-123'}"
        )
    )

    # Bounded optional
    limit: int | None = Field(
        None,
        description="Maximum rows (pagination)",
        gt=0,
        le=1000
    )
```

---

## Tool Description Pattern

```python
description=(
    "Unified read operations: query, search, batch fetch, pagination. "
    "USE WHEN: Fetching records, searching data, loading relations. "
    "RETURNS: Records with metadata and pagination info. "
    "NOT FOR: Aggregations (use aggregate_data) or writes (use write_data)."
)
```

**Format:** `[What it does]. USE WHEN: [triggers]. RETURNS: [output]. NOT FOR: [anti-patterns].`

---

## Docstring Pattern (Agent-Facing)

```python
async def _read_data_impl(...) -> dict[str, Any]:
    """
    Unified read operation for all query patterns.

    USE WHEN:
    - Fetching individual records or lists
    - Searching with filters or patterns
    - Loading related data (joins)

    NOT FOR:
    - Aggregations with GROUP BY (use aggregate_data)
    - Writing/updating data (use write_data)

    CRITICAL: filters vs search_patterns
    =====================================

    filters = EXACT MATCH (case-sensitive)
    - Use for: IDs, booleans, enums, foreign keys
    - Examples: {'is_active': True}, {'id': 'uuid-123'}

    search_patterns = FUZZY MATCH (case-insensitive ILIKE)
    - Use for: Names, descriptions, any text search
    - Examples: {'name': '%jar%'}, {'sku': '%500ML%'}

    Examples:
        # Simple query
        read_data(table="products", filters={"is_active": True})

        # Complex with relations
        read_data(
            table="products",
            search_patterns={"name": "%bottle%"},
            relations=["product_family(name)"],
            limit=50
        )
    """
```

---

## Factory Pattern for Access Control

```python
def create_read_data_tool(
    storage: StorageInterface,
    tables: list[str] | None = None,  # Access control
) -> StructuredTool:
    """
    Create read_data tool with optional table restrictions.

    Args:
        storage: Storage interface
        tables: Allowed tables (None = unrestricted)

    Examples:
        # Cataloging Specialist - restricted
        tool = create_read_data_tool(storage, tables=["products", "categories"])

        # Market Intelligence - full access
        tool = create_read_data_tool(storage)
    """
    allowed_tables = tables

    async def _impl(...):
        # Access control check
        if allowed_tables and table not in allowed_tables:
            return build_agent_error_response(
                exception=PermissionError(f"Access denied: {table}"),
                context={"table": table},
                fallback_action=f"Available tables: {allowed_tables}"
            )
        # ... rest of implementation
```

---

## Validation Checklist

Before committing a tool:

- [ ] Uses `StructuredTool.from_function()` with Pydantic `args_schema`
- [ ] Does ONE thing completely (ATOMIC)
- [ ] Never raises exceptions - uses `build_agent_error_response()`
- [ ] Returns structured dict with `success` flag
- [ ] Field descriptions include examples
- [ ] Tool description has USE WHEN / RETURNS / NOT FOR
- [ ] Docstring explains agent decision logic
- [ ] Logging with structured `extra` data
- [ ] Factory pattern if access control needed

---

## Reference Implementation

See `agents/src/autifyme_agents/tools/data_engine/read_data.py` for canonical example.
