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

---

## Specialist Description Pattern

**PM routes based on description. For 50+ specialists, descriptions must be unambiguous.**

**Structure:** `[Domain ownership]. [Key capabilities]. [What it returns to PM].`

| Quality | Example | Problem |
|---------|---------|---------|
| Bad | "Handles images" | Too vague |
| Bad | "Does product stuff" | Overlaps multiple domains |
| Good | "Owns visual asset creation. Has image_studio, view_image. Returns asset IDs and storage paths." | Clear domain, tools, output |

**Test:** If PM could confuse this specialist with another, description is too vague.

---

## Scoping Patterns

### Read-Only (Analyst)

```python
return {
    "name": "market_intelligence_specialist",
    "tools": [
        create_read_data_tool(storage),  # Full read
        create_aggregate_data_tool(storage),
    ],
    # No interrupt_on - read operations don't need HITL
}
```

### Write-Capable (Editor)

```python
return {
    "name": "content_specialist",
    "tools": [
        create_read_data_tool(storage, tables=["content"]),
        create_write_data_tool(storage, tables=["content"]),
    ],
    "interrupt_on": ["write_data"],  # HITL for writes
}
```

### External API

```python
return {
    "name": "platform_specialist",
    "tools": [
        facebook_api_tool,
        create_read_data_tool(storage, tables=["campaigns"]),
    ],
    "interrupt_on": ["publish_to_facebook"],  # HITL for external
}
```

---

## Registration with PM

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
    }
```

---

## Domain Coherence Check

**Before creating/extending a specialist, answer these:**

| Question | If YES | If NO |
|----------|--------|-------|
| Shares vocabulary with existing specialist? | Consider extending | New specialist |
| Examples compose naturally? | Extend | New (permutation explosion) |
| Same human expert would handle both? | Keep together | Split |
| Adding this creates O(2^n) examples? | Split out | Safe to extend |

**Full framework:** See CLAUDE.md "Agent Granularity Principle"

---

## Design Checklist

**Before implementing:**

- [ ] Domain coherence check passed
- [ ] Single domain ownership clear
- [ ] Tool scoping defined (minimum necessary tables/APIs)
- [ ] HITL boundary identified (write/external actions?)

**Implementation:**

- [ ] Factory function returns SubAgent spec dict
- [ ] Prompt file created (use `prompt-engineering` skill)
- [ ] Tools scoped to domain tables only
- [ ] Description enables correct PM routing
- [ ] Registered in PM's subagents list

---

## Reference

- **Specialists:** `agents/src/autifyme_agents/specialists/`
- **Prompts:** `agents/src/autifyme_agents/prompts/specialists/`
- **Prompt structure:** See `prompt-engineering` skill
- **Tool creation:** See `tool-development` skill
