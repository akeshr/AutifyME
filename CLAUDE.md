# CLAUDE.md

Project-specific guidance for AutifyME codebase. Communication style is defined in `.claude/output-styles/jarvis.md`.

---

## PART I: ARCHITECTURAL RULES

### Vision & North Star
- Deliver full hierarchical agentic organization (PM → Departments → Specialists → Tools) from day one
- Sequence workflows pragmatically without architectural shortcuts
- Ensure components scale across departments and support future workflows
- Ask before building: "How will this serve another department?"

### Design-First Process
- Create/update specs under `docs/architecture/` before implementation (user flow, agent interplay, components, schemas)
- Align with architectural canon: `AGENTS_DESIGN.md`, `LANGCHAIN_V1_FEATURES.md`, workflow docs
- Validate design preserves hierarchical data flow and context discipline

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
- Default to LangChain v1 native patterns (`interrupt_before/after`, ToolStrategy, structured outputs)
- Use `create_agent`, maintain `{messages}`/`{agent_scratchpad}` contract
- Delegate cross-cutting concerns to middleware (tools stay focused, reusable, context-light)
- Design specialists/tools for single responsibility and cross-department reuse
- Keep department outputs structured and composable for DeepAgents orchestration
- Use multimodal payloads, avoid brittle prompt hacks

### Documentation & Libraries
- Version prompts alongside code; avoid hardcoded instructions
- Update architectural docs in lockstep with major decisions
- **Library verification priority**: (1) Official docs + source code, (2) Python REPL inspection (`uv run python -c`), (3) Local docs
- Always verify APIs with `inspect`/`dir` before depending on them
- Capture context-engineering strategies and extension points for reuse

### Quality Standards
- Treat testing, observability, recovery as foundational (not optional)
- Debug methodically: full traces, validate APIs, instrument thoughtfully, one variable at a time
- Keep HITL safeguards intact for production data protection

---

## PART II: DEVELOPMENT REFERENCE

### Essential Commands

**Setup:**
```bash
cd agents
uv venv
.venv\Scripts\activate  # Windows
uv pip install -e ".[dev]"
```

**Running:**
```bash
uv run python test_cataloging_workflow.py
uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload
pytest --cov=autifyme_agents
ruff check agents/src
```

**API Verification (CRITICAL - Use Extensively):**
Always verify library APIs with Python REPL before implementing. Use `uv run python -c "..."` to:
- Inspect available methods/signatures before using them
- Test Pydantic models and serialization
- Verify LangChain v1 alpha APIs (unstable, frequently change)
- Prototype patterns before committing to implementation
- Debug errors in isolation

Never rely on documentation alone for LangChain v1 alpha stack.

### Configuration

**Environment Variables** (`agents/src/autifyme_agents/core/config.py`):
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL` (PostgreSQL for LangGraph checkpointer)
- `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
- `OPENAI_API_KEY`, `LANGSMITH_API_KEY`

**Prerequisites**: Python 3.11+, `uv`, PostgreSQL

### Architectural Canon (Read Before Changes)

1. `docs/architecture/README.md` - Navigation hub
2. `docs/architecture/AGENTS_DESIGN.md` - Hierarchical model, context engineering
3. `docs/architecture/LANGCHAIN_V1_FEATURES.md` - Available v1 patterns
4. `docs/architecture/WHATSAPP_CATALOGING_WORKFLOW.md` - Current implementation
5. `docs/architecture/PROJECT_MANAGER_DESIGN.md` - Roadmap spec

### Common Gotchas

**LangChain v1 Alpha:**
- Prerelease stack (`langchain==1.0.0a10`, `langgraph==1.0.0a4`, `deepagents==0.0.11rc1`)
- APIs unstable; verify with `inspect`/`dir` before use

**Windows:**
- Use `.venv\Scripts\activate` (not `source`)
- Git line endings: LF (`.gitattributes`)

**Database:**
- LangGraph needs raw PostgreSQL string (`postgresql://...`)
- Supabase may need `?sslmode=require`

**Error Handling:**
- Tools must raise `ToolException` (prevents infinite loops)
- `handle_errors=True` for self-healing, `False` for fail-fast

**Context Management:**
- Never pass full conversation history to specialists
- Middleware injects context; tools stay context-light
- Use `{messages}` / `{agent_scratchpad}` contract

### Quick Navigation

- **Project Status**: `README.md`
- **Architecture**: `docs/architecture/`
- **LangSmith Traces**: https://smith.langchain.com
- **Roadmap**: `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
