# CLAUDE.md

Project-specific guidance for AutifyME codebase. Communication style is defined in `.claude/output-styles/jarvis.md`. **CRITICAL** DO NOT USE EMOJIS.

---

## PART I: ARCHITECTURAL RULES

### Vision & North Star
- Deliver full hierarchical agentic organization (PM → Departments → Specialists → Tools) from day one
- Sequence workflows pragmatically without architectural shortcuts
- Ensure components scale across departments and support future workflows
- Ask before building: "How will this serve another department?"

### Design-First Process
- Create/update specs under `docs/architecture/` before implementation (user flow, agent interplay, components, schemas)
- Align with architectural canon (see below)
- Validate design preserves hierarchical data flow and context discipline

### Deep Research & Architectural Analysis
- **Think exhaustively for critical decisions**: Enumerate all permutation combinations, edge cases, platform-specific behaviors
- **Verify before assuming**: Use REPL extensively to test library capabilities; inspect code to validate assumptions
- **Challenge and iterate**: When user pushes back, dig deeper with code inspection, API verification, alternative approaches
- **Document complex findings**: Create architectural analysis docs for multi-platform support, complex workflows, cross-cutting concerns

### Core Engineering Standards
- **Production-grade from start**: resilience, observability, recovery, verification baked in
- **Hexagonal Architecture**: core logic depends only on ports; adapters at edges
- **Type Safety**: Pydantic models and structured outputs for all data transfer
- **Separation of Concerns**: strict top-down data flow per hierarchical swarm model

### Operating Model
- **Single-tenant managed service**: load company context once, inject via middleware
- **Storage adapters**: single source for persistent context; no adapter leakage to core
- **State persistence**: persist agent state, approvals, workflow checkpoints for restart recovery
- **Context flow**: map how context ascends/descends hierarchy for PM traceability

### Engineering Priorities
- Resolve blockers before feature work (error handling, persistence, verification never deferred)
- Surface deviations immediately with business justification
- Keep architectural debt visible

### LangChain & Agent Patterns
- Default to LangChain v1 native patterns (structured outputs, ToolStrategy, middleware-based HITL)
- Use `create_agent` for specialists, `create_deep_agent` for orchestrators, maintain `{messages}`/`{agent_scratchpad}` contract
- HITL via DeepAgents `tool_configs` + HumanInTheLoopMiddleware (not interrupt_before/after)
- Delegate cross-cutting concerns to middleware (tools stay focused, reusable, context-light)
- Design specialists/tools for single responsibility and cross-department reuse
- Keep department outputs structured and composable for DeepAgents orchestration
- Use multimodal payloads, avoid brittle prompt hacks

### Documentation & Libraries
- Version prompts alongside code; avoid hardcoded instructions
- **Prompt Engineering**: Follow `PROMPT_ENGINEERING_STANDARDS.md` - no Python code in prompts, use XML structure, canonical examples, right altitude for hierarchy level
- Update architectural docs in lockstep with major decisions
- **Library verification priority**: (1) Official docs + source code, (2) Python REPL inspection (`uv run python -c`), (3) Local docs
- Always verify APIs with `inspect`/`dir` before depending on them
- Capture context-engineering strategies and extension points for reuse

### Documentation Strategy
- **Check first, then decide**: Review existing docs before creating new ones; update rather than duplicate
- **Create only when necessary**: Novel topics, complex specifications, long-term architectural impact
- **Make scannable**: Date/status header, executive summary, tables/schemas/examples, implementation checklists
- **Connect the dots**: Link related docs, mark open questions, align with architectural canon

### Quality Standards
- Treat testing, observability, recovery as foundational (not optional)
- Debug methodically: full traces, validate APIs, instrument thoughtfully, one variable at a time
- Keep HITL safeguards intact for production data protection

---

## PART II: DEVELOPMENT REFERENCE

### Essential Commands

**Setup:**
```bash
uv venv
.venv\Scripts\activate  # Windows
uv pip install -e ".[dev]"
```

**Running (from root directory):**
```bash
uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload
uv run pytest tests/ --cov=autifyme_agents
uv run ruff check .
uv run mypy .
```

### Repository Structure

**Production**: `agents/src/autifyme_agents/` - Core, departments, specialists, tools, workflows, entrypoints, integrations, schemas, prompts

**Testing**: `tests/` - unit, integration, e2e, cli (testing tools), scripts, scenarios, fixtures

**Documentation**: `docs/architecture/` organized by concern (core/, workflows/, tech/, testing/), plus `historical/`, `deployment/`, `roadmap/`

**Database**: `database/migrations/` - SQL migration files

**Critical**: CLI tools (pm_chat, simulate) are in `tests/cli/`, NOT in agents package. They're test infrastructure.

### Local Testing

**Philosophy**: Iterate locally first (terminal) → Automated scenarios → Production (WhatsApp)

**CLI Tools** (all in `tests/cli/`):
```bash
# Fastest: Direct PM testing
uv run python tests/cli/pm_chat.py --interactive

# Full workflow with HITL
uv run python tests/cli/simulate.py "Catalog these sneakers"

# Multi-turn scenarios
uv run python tests/cli/conversation.py --scenario greeting_to_cataloging
```

**Complete guide**: `docs/architecture/testing/LOCAL_TESTING_STRATEGY.md`

### Autonomous Testing Framework

**Claude as Testing Orchestrator**: Claude can autonomously test, analyze, and improve the agentic system using a comprehensive testing framework.

**Capabilities**:
- Execute workflows with HITL simulation
- Analyze LangSmith traces hierarchically (25x token reduction)
- Validate database state via Supabase MCP
- Identify issues in code, prompts, architecture
- Generate and validate improvements iteratively
- Run continuous improvement loops

**Framework includes 23 tools across 5 categories**: Execution, Analysis (3 levels), Improvement, Helpers, Database validation

**Complete framework**: `docs/architecture/testing/AUTONOMOUS_TESTING_FRAMEWORK.md`
**Quick reference**: `docs/architecture/testing/QUICK_REFERENCE.md`

### API Verification

Always verify library APIs with REPL before implementing (LangChain v1 alpha is unstable):
```bash
uv run python -c "from dotenv import load_dotenv; load_dotenv('.env'); # test code"
```

**Complete guide**: `docs/architecture/tech/UV_REPL_BEST_PRACTICES.md`

### Configuration

**Environment Variables** (`agents/src/autifyme_agents/core/config.py`):
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL` (PostgreSQL for LangGraph checkpointer)
- `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
- `OPENAI_API_KEY`, `LANGSMITH_API_KEY`

**Prerequisites**: Python 3.11+, `uv`, PostgreSQL

### Architectural Canon

**Navigation hub**: `docs/architecture/README.md` - All docs categorized by concern

**Must-read before changes**:
- `core/AGENTS_DESIGN.md` - Hierarchical model, context engineering
- `core/ACTUAL_IMPLEMENTATION_ARCHITECTURE.md` - **[GROUND TRUTH]** As-built implementation
- `tech/PROMPT_ENGINEERING_STANDARDS.md` - **[CRITICAL]** Prompt design standards
- `tech/LANGCHAIN_V1_FEATURES.md` - LangChain v1 native patterns
- `workflows/WHATSAPP_CATALOGING_WORKFLOW.md` - Current implementation

**Autonomous testing framework** (for Claude to test/analyze/improve system):
- `testing/AUTONOMOUS_TESTING_FRAMEWORK.md` - **[PRIMARY]** Complete framework
- `testing/QUICK_REFERENCE.md` - Cheat sheet for quick access

**Complete index with 30+ docs**: See `docs/architecture/README.md`

### Common Gotchas

**LangChain v1 Alpha**:
- Prerelease stack (`langchain==1.0.0a12`, `langgraph==1.0.0a4`, `deepagents==0.0.11`)
- APIs unstable; verify with `inspect`/`dir` before use

**Windows**:
- Use `.venv\Scripts\activate` (not `source`)
- Git line endings: LF (`.gitattributes`)

**Database**:
- LangGraph needs raw PostgreSQL string (`postgresql://...`)
- Supabase may need `?sslmode=require`

**Error Handling**:
- Tools must raise `ToolException` (prevents infinite loops)
- `handle_errors=True` for self-healing, `False` for fail-fast

**Context Management**:
- Never pass full conversation history to specialists
- Middleware injects context; tools stay context-light
- Use `{messages}` / `{agent_scratchpad}` contract

### Quick Navigation

- **Project Status**: `README.md`
- **Architecture Docs**: `docs/architecture/README.md` (navigation hub)
- **LangSmith Traces**: https://smith.langchain.com
- **Roadmap**: `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
- Always use safe_print instaed of print