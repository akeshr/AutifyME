---
name: specialist-creation
description: Create domain specialists for AutifyME using SubAgent pattern with scoped tools and prompts. Use when adding new specialists to the PM's delegation options.
---

# Specialist Creation Guide

## Architecture Context

**2-Level Hierarchy:** PM -> Specialists -> Tools

- PM orchestrates across domains, delegates to specialists
- Specialists are domain experts with scoped tool access
- Tools are ATOMIC operations (see `tool-development` skill)

---

## Specialist Factory Pattern

```python
"""[Domain] specialist - [one-line purpose].

Factory function returns SubAgent spec for PM's subagents list.
"""

from typing import Any

from autifyme_agents.core.ports import StorageInterface
from autifyme_agents.core.prompt_loader import load_prompt
from autifyme_agents.tools.data_engine import (
    create_inspect_schema_tool,
    create_read_data_tool,
)


def create_[domain]_specialist(storage: StorageInterface) -> dict[str, Any]:
    """Create [domain] specialist SubAgent spec.

    Args:
        storage: Storage adapter for database operations

    Returns:
        SubAgent spec with [description of tools and capabilities].
    """
    system_prompt = load_prompt("specialists/[domain]_specialist.prompt")

    description = (
        "[What this specialist does]. "
        "[What tools it has access to]. "
        "[What it returns to PM]."
    )

    # Scoped table access (domain-specific)
    allowed_tables = [
        "table1",
        "table2",
    ]

    return {
        "name": "[domain]_specialist",
        "description": description,
        "tools": [
            # Domain-specific tools
            create_read_data_tool(storage, tables=allowed_tables),
            create_inspect_schema_tool(storage, tables=allowed_tables),
        ],
        "system_prompt": system_prompt,
        # "interrupt_on": ["save_tool"],  # Only if specialist has HITL tools
    }
```

---

## SubAgent Spec Structure

```python
{
    "name": str,           # Unique identifier (snake_case)
    "description": str,    # PM uses this to decide when to delegate
    "tools": list[Tool],   # Scoped tool instances
    "system_prompt": str,  # Loaded from .prompt file
    "interrupt_on": list,  # Optional: tools requiring HITL approval
}
```

**Key Points:**
- `description` guides PM's delegation decision
- `tools` are scoped (e.g., limited tables, read-only access)
- `interrupt_on` only for specialists with write/modify tools

---

## Prompt File Structure

Location: `agents/src/autifyme_agents/prompts/specialists/[domain]_specialist.prompt`

```xml
<background_information>
You [one-line role description].

**Your Tools:**
- tool_name: Purpose and when to use
- another_tool: Purpose

**Your Role:**
- [Responsibility 1]
- [Responsibility 2]
- [What you return to PM]

**Context:**
Company brand voice and target audience are provided via middleware.
</background_information>

<instructions>
**Workflow:**
1. [First step - usually check existing data]
2. [Analysis step]
3. [Synthesis step]
4. [Return to PM]

**Key Principles:**
- [Principle 1]
- [Principle 2]
- [Anti-hallucination rule]
</instructions>

<examples>
<example>
PM: "[Example input from PM]"

Actions:
1. [Tool call 1] -> [Result]
2. [Tool call 2] -> [Result]
3. Return: "[Structured output to PM]"
</example>
</examples>
```

---

## Scoping Patterns

### Read-Only Specialist (Analyst Role)

```python
return {
    "name": "market_intelligence_specialist",
    "tools": [
        create_read_data_tool(storage),  # Full read access
        create_aggregate_data_tool(storage),
        web_search_tool,
    ],
    # No interrupt_on - no HITL needed for read operations
}
```

### Write-Capable Specialist (Editor Role)

```python
return {
    "name": "content_specialist",
    "tools": [
        create_read_data_tool(storage, tables=["content", "templates"]),
        create_write_data_tool(storage, tables=["content"]),  # Scoped write
    ],
    "interrupt_on": ["write_data"],  # HITL for writes
}
```

### External API Specialist

```python
return {
    "name": "platform_specialist",
    "tools": [
        facebook_api_tool,
        create_read_data_tool(storage, tables=["campaigns"]),
    ],
    "interrupt_on": ["publish_to_facebook"],  # HITL for external actions
}
```

---

## Registration with PM

Add to PM's subagents list in `project_manager.py`:

```python
from autifyme_agents.specialists import (
    create_cataloging_specialist,
    create_[domain]_specialist,  # New specialist
)

def create_project_manager(storage: StorageInterface):
    return {
        "subagents": [
            create_cataloging_specialist(storage),
            create_[domain]_specialist(storage),  # Add here
        ],
        # ... rest of PM config
    }
```

---

## Design Checklist

Before implementing:

- [ ] **Domain clarity:** What single domain does this specialist own?
- [ ] **Reusability:** Will multiple workflows use this specialist?
- [ ] **Tool scoping:** What tables/APIs does it need? Minimum necessary.
- [ ] **HITL boundary:** Does it write/modify data? External actions?

Implementation:

- [ ] Factory function returns SubAgent spec dict
- [ ] Prompt file uses XML structure (see `prompt-engineering` skill)
- [ ] Tools scoped to domain tables only
- [ ] Description helps PM delegate correctly
- [ ] Registered in PM's subagents list

---

## Reference Implementations

- **Cataloging:** `specialists/cataloging_specialist.py` - Image analysis + read-only
- **Market Intelligence:** `specialists/market_intelligence_specialist.py` - Analytics + web search
- **Content SEO:** `specialists/content_seo_specialist.py` - Content generation

Prompts: `agents/src/autifyme_agents/prompts/specialists/`
