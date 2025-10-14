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
- Default to LangChain v1 native patterns (`interrupt_before/after`, ToolStrategy, structured outputs)
- Use `create_agent`, maintain `{messages}`/`{agent_scratchpad}` contract
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
uv run pytest agents/tests/ --cov=autifyme_agents
uv run ruff check .
uv run mypy .
```

**Local Testing (CRITICAL - Use Extensively):**
Always test locally before WhatsApp. CLI tools available for terminal-based testing without external dependencies.

**Testing Philosophy**:
- **Iterate locally first**: Test changes in terminal where you have access, not on WhatsApp
- **Layer your testing**: Quick PM tests → Full workflow → Automated scenarios → Production
- **Test with real media**: Use local files (images, videos, voice, documents) to simulate realistic flows
- **Validate end-to-end**: After REPL prototyping, run full workflow to catch integration issues

**Available Tools**:
- `pm_chat` - Direct PM invocation for rapid prompt/logic iteration (interactive mode recommended)
- `simulate` - Full workflow simulation with HITL support

See `docs/architecture/LOCAL_TESTING_STRATEGY.md` for commands and usage patterns.

**API Verification (CRITICAL - Use Extensively):**
Always verify library APIs with Python REPL before implementing.

**Correct Pattern (from root directory):**
```bash
# uv auto-detects agents/pyproject.toml
uv run python -c "
from dotenv import load_dotenv
load_dotenv('.env')
# ... your test code
"

# With automatic .env loading
uv run --env-file .env python -c "
# ... your test code (env already loaded)
"
```

**Use Cases:**
- Inspect available methods/signatures before using them
- Test Pydantic models and serialization
- Verify LangChain v1 alpha APIs (unstable, frequently change)
- Prototype patterns before committing to implementation
- Debug errors in isolation with real API keys

**Important:** Always run from project root - `uv` auto-detects the project.

**See:** `docs/architecture/UV_REPL_BEST_PRACTICES.md` for complete guide.

Never rely on documentation alone for LangChain v1 alpha stack.

### Configuration

**Environment Variables** (`agents/src/autifyme_agents/core/config.py`):
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL` (PostgreSQL for LangGraph checkpointer)
- `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
- `OPENAI_API_KEY`, `LANGSMITH_API_KEY`

**Prerequisites**: Python 3.11+, `uv`, PostgreSQL

### Architectural Canon (Read Before Changes)

**Core Architecture:**
1. `docs/architecture/README.md` - Navigation hub
2. `docs/architecture/AGENTS_DESIGN.md` - Hierarchical model, context engineering
3. `docs/architecture/ACTUAL_IMPLEMENTATION_ARCHITECTURE.md` - **[GROUND TRUTH]** As-built implementation verified from code
4. `docs/architecture/PROMPT_ENGINEERING_STANDARDS.md` - **[CRITICAL]** Prompt design standards (no code, right altitude, examples)
5. `docs/architecture/PROJECT_MANAGER_DESIGN.md` - PM role, intent classification, delegation

**Technology & Patterns:**
6. `docs/architecture/TECH_STACK.md` - Technology decisions
7. `docs/architecture/LANGCHAIN_V1_FEATURES.md` - LangChain v1 patterns
8. `docs/architecture/LANGGRAPH_V1_FEATURES.md` - LangGraph orchestration
9. `docs/architecture/UV_REPL_BEST_PRACTICES.md` - API verification workflow

**Workflows & Implementation:**
10. `docs/architecture/WHATSAPP_CATALOGING_WORKFLOW.md` - Current cataloging implementation
11. `docs/architecture/PM_INTENT_ANALYSIS_AND_MESSAGE_HANDLING.md` - Multi-platform message handling
12. `docs/architecture/LOCAL_TESTING_STRATEGY.md` - Testing philosophy and CLI tools
13. `docs/architecture/WORKFLOW_ORCHESTRATION_REFACTOR.md` - Runner architecture

**See `docs/architecture/README.md` for complete index and context.**

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
