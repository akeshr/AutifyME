# Architecture Documentation

**Navigation hub for AutifyME architectural docs.** Organized by concern for scannable access.

---

## Core Architecture (`core/`)

Timeless design blueprints and implementation ground truth.

| Document | Purpose |
| --- | --- |
| **[AGENTS_DESIGN.md](./core/AGENTS_DESIGN.md)** | Canonical agent hierarchy and context engineering patterns (design blueprint) |
| **[ACTUAL_IMPLEMENTATION_ARCHITECTURE.md](./core/ACTUAL_IMPLEMENTATION_ARCHITECTURE.md)** | ✅ **Ground truth** - as-built implementation verified from code |
| **[PROJECT_MANAGER_DESIGN.md](./core/PROJECT_MANAGER_DESIGN.md)** | PM agent role, intent classification, delegation patterns |
| **[ARCHITECTURE_IMPROVEMENTS.md](./core/ARCHITECTURE_IMPROVEMENTS.md)** | Evolution and design decision history |

---

## Workflows & Implementation (`workflows/`)

Workflow-specific designs and orchestration patterns.

| Document | Purpose |
| --- | --- |
| **[WHATSAPP_CATALOGING_WORKFLOW.md](./workflows/WHATSAPP_CATALOGING_WORKFLOW.md)** | Current cataloging implementation (end-to-end) |
| **[WEBHOOK_IDEMPOTENCY_DEEP_DIVE.md](./workflows/WEBHOOK_IDEMPOTENCY_DEEP_DIVE.md)** | Webhook idempotency and deduplication patterns |
| **[MONITORING_QUERIES.md](./workflows/MONITORING_QUERIES.md)** | Database queries for monitoring and debugging |

---

## Technology & Patterns (`tech/`)

Library patterns, prompt engineering, and development practices.

| Document | Purpose |
| --- | --- |
| **[TECH_STACK.md](./tech/TECH_STACK.md)** | Technology choices organized by architecture layer |
| **[LANGCHAIN_V1_FEATURES.md](./tech/LANGCHAIN_V1_FEATURES.md)** | LangChain v1 native patterns (HITL, error handling, structured outputs) |
| **[LANGGRAPH_V1_FEATURES.md](./tech/LANGGRAPH_V1_FEATURES.md)** | LangGraph orchestration patterns and gotchas |
| **[LANGSMITH_FEATURES.md](./tech/LANGSMITH_FEATURES.md)** | LangSmith tracing and debugging |
| **[PROMPT_ENGINEERING_STANDARDS.md](./tech/PROMPT_ENGINEERING_STANDARDS.md)** | **[CRITICAL]** Prompt design standards (Anthropic best practices) |
| **[LIBRARY_NATIVE_PATTERNS.md](./tech/LIBRARY_NATIVE_PATTERNS.md)** | Prefer library-native solutions over custom code |
| **[UV_REPL_BEST_PRACTICES.md](./tech/UV_REPL_BEST_PRACTICES.md)** | API verification workflow using Python REPL |

---

## Testing & Development (`testing/`)

Testing strategy, CLI tools, and development workflows.

| Document | Purpose |
| --- | --- |
| **[LOCAL_TESTING_STRATEGY.md](./testing/LOCAL_TESTING_STRATEGY.md)** | Testing philosophy and CLI tools guide (canonical) |
| **[COMPREHENSIVE_CLI_TESTING_DESIGN.md](./testing/COMPREHENSIVE_CLI_TESTING_DESIGN.md)** | CLI testing framework design for future enhancements |

---

## Key Principles

- **Architecture-First:** Production-grade from day 1
- **LangChain v1 Native:** Use built-in patterns (HITL, error handling, structured outputs)
- **Hexagonal Architecture:** Core decoupled from external services
- **Context Engineering:** Minimize LLM context at every step

---

## ⚠️ Critical Gotchas

### LangGraph Interrupt Detection in Subgraphs

**If you're working with HITL/interrupts in subgraphs (DeepAgents, departments):**

❌ **DO NOT** use `checkpointer.get_tuple(config).checkpoint.get("__interrupt__")` - it doesn't work!

✅ **USE** `graph.get_state(config).interrupts` instead.

The Checkpoint dict has no `__interrupt__` field. You must use the StateSnapshot API via `get_state()`.

**Details:** See [LANGGRAPH_V1_FEATURES.md § Critical: Interrupt Detection in Subgraphs](./tech/LANGGRAPH_V1_FEATURES.md#️-critical-interrupt-detection-in-subgraphs)

This gotcha cost us 3 days of debugging (Oct 2025). Learn from our pain.

---

## Quick Start

Before implementing any feature:

1. Check **[LANGCHAIN_V1_FEATURES.md](./tech/LANGCHAIN_V1_FEATURES.md)** for native solutions
2. Review **[AGENTS_DESIGN.md](./core/AGENTS_DESIGN.md)** for hierarchy and context engineering
3. **Writing prompts?** Follow **[PROMPT_ENGINEERING_STANDARDS.md](./tech/PROMPT_ENGINEERING_STANDARDS.md)**
4. For implementation sequencing, read `../roadmap/IMPLEMENTATION_ROADMAP.md`
5. For pending departments or PM details, consult **[PROJECT_MANAGER_DESIGN.md](./core/PROJECT_MANAGER_DESIGN.md)**
6. Follow Cursor rules in `../../.cursor/rules/`

---

## Historical Archive

Old debugging sessions, bug fixes, and refactor docs moved to `../historical/`:
- `historical/bug-fixes/` - Bug fix summaries and post-mortems
- `historical/refactors/` - Refactoring session notes and implementation summaries
- `historical/debug-sessions/` - Debugging analyses and audits
- `historical/design-specs/` - Unimplemented design specifications

These are kept for reference but don't clutter active navigation.
