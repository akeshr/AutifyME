# Architecture Documentation

## Core Documents

| Reference | Purpose |
| --- | --- |
| **[AGENTS_DESIGN.md](./AGENTS_DESIGN.md)** | Canonical agent hierarchy and context engineering patterns (timeless design blueprint). |
| **[PROMPT_ENGINEERING_STANDARDS.md](./PROMPT_ENGINEERING_STANDARDS.md)** | Production-grade prompt design standards for all agents (Anthropic/Claude best practices). |
| **[LANGCHAIN_V1_FEATURES.md](./LANGCHAIN_V1_FEATURES.md)** | Vendor feature reference with links to official resources; implementation status lives in roadmap docs. |
| **[TECH_STACK.md](./TECH_STACK.md)** | Technology choices organized by architecture layer. |
| **[PROJECT_MANAGER_DESIGN.md](./PROJECT_MANAGER_DESIGN.md)** | Roadmap specification for the Project Manager agent (explicitly marked future work). |
| **[WHATSAPP_CATALOGING_WORKFLOW.md](./WHATSAPP_CATALOGING_WORKFLOW.md)** | Workflow-specific design for the cataloging MVP. |

## Key Principles

- **Architecture-First:** Production-grade from day 1
- **LangChain v1 Native:** Use built-in patterns (HITL, error handling, structured outputs)
- **Hexagonal Architecture:** Core decoupled from external services
- **Context Engineering:** Minimize LLM context at every step

## ⚠️ Critical Gotchas

### LangGraph Interrupt Detection in Subgraphs

**If you're working with HITL/interrupts in subgraphs (DeepAgents, departments):**

❌ **DO NOT** use `checkpointer.get_tuple(config).checkpoint.get("__interrupt__")` - it doesn't work!

✅ **USE** `graph.get_state(config).interrupts` instead.

The Checkpoint dict has no `__interrupt__` field. You must use the StateSnapshot API via `get_state()`.

**Details:** See [LANGGRAPH_V1_FEATURES.md § Critical: Interrupt Detection in Subgraphs](./LANGGRAPH_V1_FEATURES.md#️-critical-interrupt-detection-in-subgraphs)

This gotcha cost us 3 days of debugging (Oct 2025). Learn from our pain.

## Quick Start

Before implementing any feature:
1. Check [LANGCHAIN_V1_FEATURES.md](./LANGCHAIN_V1_FEATURES.md) for native solutions before writing custom logic.
2. Review [AGENTS_DESIGN.md](./AGENTS_DESIGN.md) for hierarchy and context engineering rules.
3. **Writing prompts?** Follow [PROMPT_ENGINEERING_STANDARDS.md](./PROMPT_ENGINEERING_STANDARDS.md) - no code in prompts, right altitude, canonical examples.
4. For implementation sequencing or status, read `../roadmap/IMPLEMENTATION_ROADMAP.md`.
5. For pending departments or Project Manager details, consult [PROJECT_MANAGER_DESIGN.md](./PROJECT_MANAGER_DESIGN.md).
6. Follow Cursor rules in `../../.cursor/rules/`.
