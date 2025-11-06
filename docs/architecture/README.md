# Architecture Documentation

**Navigation hub for AutifyME architectural docs.** Organized by concern for scannable access.

---

## Core Architecture (`core/`)

Timeless design blueprints and implementation ground truth.

| Document | Purpose |
| --- | --- |
| **[DOMAIN_DESIGN_GUIDELINES.md](./core/DOMAIN_DESIGN_GUIDELINES.md)** | **[CRITICAL]** Architectural standards for designing new domains and workflows - MUST reference when building new workflows |
| **[AGENTS_DESIGN.md](./core/AGENTS_DESIGN.md)** | Canonical agent hierarchy and context engineering patterns (design blueprint) |
| **[ACTUAL_IMPLEMENTATION_ARCHITECTURE.md](./core/ACTUAL_IMPLEMENTATION_ARCHITECTURE.md)** | ✅ **Ground truth** - as-built implementation verified from code |
| **[PROJECT_MANAGER_DESIGN.md](./core/PROJECT_MANAGER_DESIGN.md)** | PM agent role, intent classification, delegation patterns |
| **[DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md](./core/DYNAMIC_SCHEMA_DRIVEN_ARCHITECTURE.md)** | 🔄 **Dynamic CRUD** - Schema-driven architecture for future-proof database operations (replaces static patterns) |
| **[WORKFLOW_DESIGN_STRATEGY.md](./core/WORKFLOW_DESIGN_STRATEGY.md)** | Workflow orchestration patterns and sequencing strategies |
| **[ARCHITECTURE_IMPROVEMENTS.md](./core/ARCHITECTURE_IMPROVEMENTS.md)** | Evolution and design decision history |

---

## Architectural Analysis & Vision

High-level architectural reviews and alignment with vision.

| Document | Purpose |
| --- | --- |
| **[COMPREHENSIVE_ARCHITECTURAL_REVIEW.md](./COMPREHENSIVE_ARCHITECTURAL_REVIEW.md)** | Complete architecture analysis against vision goals (updated Oct 25) |

---

## Workflows & Implementation (`workflows/`)

Workflow-specific designs and orchestration patterns.

| Document | Purpose |
| --- | --- |
| **[WHATSAPP_CATALOGING_WORKFLOW.md](./workflows/WHATSAPP_CATALOGING_WORKFLOW.md)** | Current cataloging implementation (end-to-end) |
| **[PRODUCT_ONBOARDING_COMPLETE_DESIGN.md](./workflows/PRODUCT_ONBOARDING_COMPLETE_DESIGN.md)** | Product onboarding workflow - 5 specialists, 4 HITL points, complete spec |
| **[WEBHOOK_IDEMPOTENCY_DEEP_DIVE.md](./workflows/WEBHOOK_IDEMPOTENCY_DEEP_DIVE.md)** | Webhook idempotency and deduplication patterns |

---

## Operational & Debugging (`workflows/`)

Monitoring, debugging, and operational patterns.

| Document | Purpose |
| --- | --- |
| **[MONITORING_QUERIES.md](./workflows/MONITORING_QUERIES.md)** | Database queries for monitoring and debugging |
| **[TRACE_CORRELATION.md](./workflows/TRACE_CORRELATION.md)** | Trace debugging patterns and correlation strategies |
| **[BUG3_ROOT_CAUSE_ANALYSIS.md](./workflows/BUG3_ROOT_CAUSE_ANALYSIS.md)** | Bug fix post-mortem (cataloging workflow) |

---

## Technical Debt & Refactoring (`workflows/`)

Active refactoring plans and technical debt tracking.

| Document | Purpose |
| --- | --- |
| **[RUNNER_V2_REFACTORING_PLAN.md](./workflows/RUNNER_V2_REFACTORING_PLAN.md)** | ⚙️ In Progress - Runner refactoring to separate concerns |

---

## Technology & Patterns (`tech/`)

Library patterns, prompt engineering, and development practices.

| Document | Purpose |
| --- | --- |
| **[TECH_STACK.md](./tech/TECH_STACK.md)** | Technology choices organized by architecture layer |
| **[EXECUTABLE_SCHEMA_COMPLETE.md](./tech/EXECUTABLE_SCHEMA_COMPLETE.md)** | ✅ **Phase 2D+2E Complete** - Executable schema + transaction support (76 tests, production-ready) |
| **[DYNAMIC_CRUD_ACCESS_CONTROL.md](./tech/DYNAMIC_CRUD_ACCESS_CONTROL.md)** | ✅ **Implemented** - Operation-scoped CRUD tools with dynamic Pydantic schemas (39 tests) |
| **[LANGCHAIN_V1_FEATURES.md](./tech/LANGCHAIN_V1_FEATURES.md)** | LangChain v1 native patterns (HITL, error handling, structured outputs) |
| **[LANGGRAPH_V1_FEATURES.md](./tech/LANGGRAPH_V1_FEATURES.md)** | LangGraph orchestration patterns and gotchas |
| **[LANGSMITH_FEATURES.md](./tech/LANGSMITH_FEATURES.md)** | LangSmith tracing and debugging |
| **[GOOGLE_AI_MULTIMODAL_INTEGRATION.md](./tech/GOOGLE_AI_MULTIMODAL_INTEGRATION.md)** | ✅ Complete Google AI infrastructure - Gemini 2.5, image gen (Nano Banana), TTS, video (Veo 3.1), live audio, browser automation |
| **[GOOGLE_COMPUTER_USE_GUIDE.md](./tech/GOOGLE_COMPUTER_USE_GUIDE.md)** | Browser automation with Gemini Computer Use (optional extension) |
| **[PROMPT_OPTIMIZATION_TOOLS_ANALYSIS.md](./tech/PROMPT_OPTIMIZATION_TOOLS_ANALYSIS.md)** | Research on prompt optimization tools (Vertex AI, DSPy, cross-provider) |
| **[PROMPT_ENGINEERING_STANDARDS.md](./tech/PROMPT_ENGINEERING_STANDARDS.md)** | **[CRITICAL]** Prompt design standards (Anthropic best practices) |
| **[LIBRARY_NATIVE_PATTERNS.md](./tech/LIBRARY_NATIVE_PATTERNS.md)** | Prefer library-native solutions over custom code |
| **[UV_REPL_BEST_PRACTICES.md](./tech/UV_REPL_BEST_PRACTICES.md)** | API verification workflow using Python REPL |

---

## Deployment & Operations (`../deployment/`)

Operational guides for production runtime and maintenance.

| Document | Purpose |
| --- | --- |
| **[DATABASE_MAINTENANCE.md](../deployment/DATABASE_MAINTENANCE.md)** | Database health monitoring, cleanup scheduling, backup strategy, index maintenance, troubleshooting |

---

## Testing & Development (`testing/`)

Testing strategy, CLI tools, and autonomous testing framework.

### Manual Testing & CLI Tools

| Document | Purpose |
| --- | --- |
| **[LOCAL_TESTING_STRATEGY.md](./testing/LOCAL_TESTING_STRATEGY.md)** | Testing philosophy and CLI tools guide (canonical) |

### Autonomous Testing Framework (Claude-Orchestrated)

Framework for Claude to test, analyze, and improve the agentic system through hierarchical trace analysis. Claude uses 5 observation tools to gather information, then applies existing tools (Edit/Write/MCP) to fix issues.

**Core Philosophy**: Tools provide visibility, Claude provides intelligence.

| Document | Purpose |
| --- | --- |
| **[AUTONOMOUS_TESTING_FRAMEWORK.md](./testing/AUTONOMOUS_TESTING_FRAMEWORK.md)** | **[PRIMARY]** Complete framework - Claude as orchestrator, 5 essential tools, workflows |
| **[TOOL_SPECIFICATIONS.md](./testing/TOOL_SPECIFICATIONS.md)** | Complete API reference for 5 observation tools |
| **[HIERARCHICAL_TRACE_ANALYSIS.md](./testing/HIERARCHICAL_TRACE_ANALYSIS.md)** | 3-level lazy-loading trace analysis strategy (25x token reduction) |
| **[QUICK_REFERENCE.md](./testing/QUICK_REFERENCE.md)** | Cheat sheet - common commands, decision trees, token budgets |

---

## Key Principles

- **Architecture-First:** Production-grade from day 1
- **LangChain v1 Native:** Use built-in patterns (HITL, error handling, structured outputs)
- **Hexagonal Architecture:** Core decoupled from external services
- **Context Engineering:** Minimize LLM context at every step

---

## ⚠️ Critical Gotchas

### LangGraph Interrupt Detection in Subgraphs

**If you're working with HITL/interrupts in subgraphs (DeepAgents, specialists):**

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
5. For specialist or PM details, consult **[PROJECT_MANAGER_DESIGN.md](./core/PROJECT_MANAGER_DESIGN.md)**
6. Follow Cursor rules in `../../.cursor/rules/`

---

## Historical Archive

Old debugging sessions, bug fixes, refactor docs, research, and planning artifacts moved to `../historical/`:
- `historical/bug-fixes/` - Bug fix summaries and post-mortems
- `historical/refactors/` - Refactoring session notes and implementation summaries
- `historical/debug-sessions/` - Debugging analyses and audits
- `historical/design-specs/` - Unimplemented design specifications and rejected alternatives
  - `design-specs/product-onboarding-alternatives/` - Rejected product onboarding designs
  - `design-specs/hitl-patterns/` - HITL implementation proposals (not yet implemented)
- `historical/research/` - Pre-implementation research and investigation
  - `research/deepagents/` - DeepAgents library research (Oct 2025)
- `historical/migrations/` - Completed migration documentation
  - `migrations/v1-upgrade/` - LangChain v1 alpha → v1 stable migration (Oct 2025)
- `historical/planning/` - Time-bound implementation plans (now historical)

These are kept for reference but don't clutter active navigation.
