# CLAUDE.md

Project-specific guidance for AutifyME codebase. Communication style is defined in `.claude/output-styles/jarvis.md`. **[CRITICAL] DO NOT USE EMOJIS**.

---

## PART I: ARCHITECTURAL RULES

### Vision & North Star
- **2-Level Architecture:** PM → Specialists → Tools (direct specialist visibility enables dynamic planning)
- Deliver autonomous agentic organization with dynamic planning and adaptation
- **Domain-centric design:** Build reusable domain specialists, not workflow-specific agents
- PM composes specialists dynamically based on workflow needs
- Ask before building: "Which domains/workflows will reuse this specialist?"

### Design-First Process
- Create/update specs under `docs/architecture/` before implementation (user flow, agent interplay, components, schemas)
- Validate design preserves hierarchical data flow and context discipline
- Ensure specialists are domain experts, not workflow executors

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
- Design specialists/tools for single responsibility and reuse across workflows
- Use multimodal payloads, avoid brittle prompt hacks

### Autonomous Behavior Standards
- **Dynamic Planning:** Agents analyze context and plan adaptively, not follow rigid recipes
- **Graceful Adaptation:** Handle missing data, tool failures, and edge cases with fallback strategies
- **Self-Review:** Critique outputs before returning; iterate when confidence is low
- **Transparent Communication:** Flag limitations, assumptions, and data gaps clearly
- **Learning Orientation:** System should improve from past executions

### Prompt Engineering for Autonomy
- **Version prompts alongside code** - avoid hardcoded instructions in agent logic
- **Follow `PROMPT_ENGINEERING_STANDARDS.md`** - no Python code in prompts, use XML structure, canonical examples, right altitude for hierarchy level
- **Design for autonomy, not recipes:** Prompts should enable dynamic decision-making, not prescribe rigid execution sequences
- **PM prompts enable planning:** Analyze context first, then plan adaptively (not "Phase 1→2→3")
- **Specialist prompts enable adaptation:** Handle missing data, self-review outputs, iterate when confidence is low
- **Avoid hardcoded orchestration:** Let agents decide sequence based on available data and dependencies
- **Enable transparent failures:** Agents should flag limitations and adapt, not silently fail or rigidly error

### Documentation & Libraries
- Update architectural docs in lockstep with major decisions
- **Library verification priority**: (1) Official docs + source code, (2) Python REPL inspection (`uv run python -c`), (3) Local docs
- Always verify APIs with `inspect`/`dir` before depending on them
- Capture context-engineering strategies and extension points for reuse

### Documentation Strategy
- **[CRITICAL]Check first, then decide**: Review existing docs before creating new ones; update rather than duplicate
- **[CRITICAL]Create only when necessary**: Novel topics, complex specifications, long-term architectural impact
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

**Production**: `agents/src/autifyme_agents/` - Core, specialists, tools, workflows, entrypoints, integrations, schemas, prompts

**Testing**: `tests/` - tools/ (autonomous framework), unit, integration, cli (simulate.py, pm_chat.py), fixtures, synthesizer, archived/ (historical)

**Documentation**: `docs/architecture/` organized by concern (core/, workflows/, tech/, testing/), plus `historical/`, `deployment/`, `roadmap/`

### API Verification

Always verify library APIs with REPL before implementing (LangChain v1):
```bash
uv run python -c "from dotenv import load_dotenv; load_dotenv('.env'); # test code"
```

**Complete guide**: `docs/architecture/tech/UV_REPL_BEST_PRACTICES.md`

**Prerequisites**: Python 3.12+, `uv`, PostgreSQL

### Architectural Canon

**Navigation hub**: `docs/architecture/README.md` - All docs categorized by concern

### Common Gotchas

**LangChain v1**:
- Prerelease stack (`langchain==1.0.0`, `langgraph==1.0.0`, `deepagents==0.1.4`)
- APIs unstable; verify with `inspect`/`dir` before use

**Windows**:
- Use `.venv\Scripts\activate` (not `source`)
- Git line endings: LF (`.gitattributes`)

**Error Handling**:
- Tools must raise `ToolException` (prevents infinite loops)

### Quick Navigation

- **Project Status**: `README.md`
- **Architecture Docs**: `docs/architecture/README.md` (navigation hub)
- **LangSmith Traces**: https://smith.langchain.com
- Always use `safe_print` instead of `print`
- Always use testing framework for test scenarios