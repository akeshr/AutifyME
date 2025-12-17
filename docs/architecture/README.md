# Architecture Documentation

**Navigation hub for AutifyME architectural docs.** Organized by concern for scannable access.

---

## Core Architecture (`core/`)

Timeless design blueprints and implementation ground truth.

| Document | Purpose |
| --- | --- |
| **[DOMAIN_REASONING.md](./core/DOMAIN_REASONING.md)** | **[CANONICAL]** Domain reasoning framework - protocols, architecture, implementation |
| **[PM_INTELLIGENCE_ROADMAP.md](./core/PM_INTELLIGENCE_ROADMAP.md)** | **[ROADMAP]** Future PM capabilities - reference resolution, intent inference |
| **[DOMAIN_DESIGN_GUIDELINES.md](./core/DOMAIN_DESIGN_GUIDELINES.md)** | **[CRITICAL]** Architectural standards for designing new domains and workflows |
| **[AGENTS_DESIGN.md](./core/AGENTS_DESIGN.md)** | **[CANONICAL]** Agent hierarchy, context engineering, specialist patterns |
| **[ACTUAL_IMPLEMENTATION_ARCHITECTURE.md](./core/ACTUAL_IMPLEMENTATION_ARCHITECTURE.md)** | **[GROUND TRUTH]** As-built implementation verified from code |
| **[UNIVERSAL_DATA_ENGINE_DESIGN.md](./core/UNIVERSAL_DATA_ENGINE_DESIGN.md)** | Three-engine model (Schema/Read/Write) - partially implemented |
| **[WORKFLOW_DESIGN_STRATEGY.md](./core/WORKFLOW_DESIGN_STRATEGY.md)** | Workflow orchestration patterns and sequencing strategies |
| **[DATABASE_SCHEMA_DESIGN.md](./core/DATABASE_SCHEMA_DESIGN.md)** | Database schema and table relationships |
| **[BROWSER_AUTOMATION_SPECIALIST_DESIGN.md](./core/BROWSER_AUTOMATION_SPECIALIST_DESIGN.md)** | Browser automation specialist design (future) |
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
| **[UNIVERSAL_DATA_ENGINE_EXECUTION_PLAN.md](./workflows/UNIVERSAL_DATA_ENGINE_EXECUTION_PLAN.md)** | 🚀 **[NEW]** Phased execution plan for Universal Data Engine (4 phases, 9-13 weeks, 791+ tests) |
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

---

## Tools Design (`tools/`)

Detailed design documents for powerful, atomic tools.

| Document | Purpose |
| --- | --- |
| **[IMAGE_STUDIO_TOOL.md](./tools/IMAGE_STUDIO_TOOL.md)** | Unified image tool - analyze, generate, enhance, compose with self-review pattern |

---

## Technology & Patterns (`tech/`)

Library patterns, prompt engineering, and development practices.

| Document | Purpose |
| --- | --- |
| **[TECH_STACK.md](./tech/TECH_STACK.md)** | Technology choices organized by architecture layer |
| **[PROMPT_ENGINEERING_STANDARDS.md](./tech/PROMPT_ENGINEERING_STANDARDS.md)** | **[CRITICAL]** Prompt design standards (Anthropic best practices) |
| **[LANGCHAIN_V1_FEATURES.md](./tech/LANGCHAIN_V1_FEATURES.md)** | LangChain v1 native patterns (HITL, error handling, structured outputs) |
| **[LANGGRAPH_V1_FEATURES.md](./tech/LANGGRAPH_V1_FEATURES.md)** | LangGraph orchestration patterns and gotchas |
| **[LANGSMITH_FEATURES.md](./tech/LANGSMITH_FEATURES.md)** | LangSmith tracing and debugging |
| **[GOOGLE_AI_MULTIMODAL_INTEGRATION.md](./tech/GOOGLE_AI_MULTIMODAL_INTEGRATION.md)** | Google AI infrastructure - Gemini 2.5, multimodal capabilities |
| **[GOOGLE_COMPUTER_USE_GUIDE.md](./tech/GOOGLE_COMPUTER_USE_GUIDE.md)** | Browser automation with Gemini Computer Use |
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
| **[WORKFLOW_EVALUATION_FRAMEWORK.md](./testing/WORKFLOW_EVALUATION_FRAMEWORK.md)** | **[NEW]** World-class framework for AI agents to evaluate and improve any agentic workflow |
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

1. Review **[AGENTS_DESIGN.md](./core/AGENTS_DESIGN.md)** for hierarchy and specialist patterns
2. Check **[DOMAIN_DESIGN_GUIDELINES.md](./core/DOMAIN_DESIGN_GUIDELINES.md)** for architectural standards
3. **Writing prompts?** Follow **[PROMPT_ENGINEERING_STANDARDS.md](./tech/PROMPT_ENGINEERING_STANDARDS.md)**
4. **Adding domain expertise?** Use **[DOMAIN_REASONING.md](./core/DOMAIN_REASONING.md)** to encode as executable protocols
5. Check **[LANGCHAIN_V1_FEATURES.md](./tech/LANGCHAIN_V1_FEATURES.md)** for native solutions
6. Follow Cursor rules in `../../.cursor/rules/`

---

## Historical Archive

Archived docs moved to `../historical/` (kept for reference, not active navigation):

- `historical/bug-fixes/BUG_FIXES_CHANGELOG.md` - Consolidated bug fix changelog
- `historical/migrations/v1-upgrade/V1_MIGRATION_COMPLETE.md` - LangChain v1 migration summary
- `historical/research/deepagents/DEEPAGENTS_LIBRARY_LIMITATIONS.md` - Known library limitations
- `historical/research/` - Research docs (marketing analysis, platform APIs, middleware investigation)
