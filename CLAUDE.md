# CLAUDE.md

Project-specific guidance for AutifyME codebase. Communication style is defined in `.claude/output-styles/jarvis.md`. **[CRITICAL] DO NOT USE EMOJIS, ALWAYS USE ASCII COMPLAINT CHARACTERS**.

---

## PART I: ARCHITECTURAL RULES

### Vision & North Star
- **2-Level Architecture:** PM → Specialists → Tools (direct specialist visibility enables dynamic planning)
- Deliver autonomous agentic organization with dynamic planning and adaptation
- **Domain-centric design:** Build reusable domain specialists, not workflow-specific agents
- PM composes specialists dynamically based on workflow needs
- Ask before building: "Which domains/workflows will reuse this specialist?"

### **[CRITICAL] Agent Granularity Principle: Domain Coherence**

**The right agent size is determined by domain coherence, not arbitrary count.**

| Keep Together | Split Apart |
|---------------|-------------|
| Shared vocabulary/reasoning patterns | Different mental models |
| Examples for A help illustrate B | O(2^n) example permutations |
| Human expert would naturally do both | Distinct expertise domains |

**Key Insight:** 50+ agents in catalog is fine - only 10-15 active per workflow. PM routing is O(1) lookup.

**Test:** If adding responsibility D requires examples for A+D, B+D, C+D combinations, split by domain boundary.

**Full framework:** See `specialist-creation` skill for Domain Coherence Assessment.

### **[CRITICAL] Intelligence-First Design Principle**
Modern LLMs are highly capable: massive context windows (200K+ tokens), strong reasoning, autonomous problem-solving. This fundamentally shapes our architecture:

- **Trust intelligence over control:** Give agents problems + rich context, not step-by-step recipes
- **Minimal scaffolding:** Avoid over-engineering; let agents reason about goals and adapt dynamically
- **Context enables autonomy:** Rich, well-structured context beats rigid orchestration
- **Design for reasoning, not automation:** Agents should analyze situations and decide, not follow scripts

**[CRITICAL] The Domain Grounding Reality:**
LLMs are general-purpose - they DON'T know your tools, business rules, or domain expectations. Canonical examples (2-4 complex, pattern-illustrative) bridge this gap. Use `agent-improvement` skill to diagnose and fix underperforming agents.

### **[CRITICAL] ULTRATHINK: First-Principles Engineering - Clean Slate, Not Frankenstein**

Every change—whether design, architecture, or code—must meet this standard:

- **Analyze deeply before proposing:** Research all viable options, explore the problem space, verify assumptions with REPL/docs/code inspection—never jump to implementation
- **Present options, recommend best:** Surface trade-offs honestly, then give a clear recommendation with conviction and rationale
- **Clean slate, not Frankenstein patches:** Design the ideal solution from first principles—never layer band-aids on broken foundations
- **Zero tolerance for patchwork:** No shortcuts, no workarounds, no "we'll fix it later"—if it's worth doing, it's worth doing right
- **From-scratch mindset:** Approach every change as if building fresh—question existing patterns, refactor fearlessly, eliminate technical debt
- **Fix the foundation first:** If existing code violates principles, refactor to the right architecture before adding features
- **Unconstrained design:** Ignore legacy limitations, existing patterns, or "how it's done now"—design the ideal solution first, then implement it

**ULTRATHINK means:** Before every implementation, pause and ask: "If I were designing this from scratch with everything I know now, would I build it this way?" If not, refactor to the right architecture first. The right architecture justifies any necessary refactoring—never compromise with Frankenstein patches.

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
- Use `create_agent` for specialists, `create_deep_agent` for orchestrators
- HITL via DeepAgents `tool_configs` + HumanInTheLoopMiddleware
- Delegate cross-cutting concerns to middleware

### Tool Development Standards
- **[CRITICAL] ATOMIC + StructuredTool:** One thing powerfully, Pydantic schemas, structured returns

### **[CRITICAL] Proactive Skill Usage**
Invoke project skills automatically at the start of relevant work - do not wait to be told:

- **`agent-improvement`**: Diagnosing underperforming agents, adding examples, domain grounding
- **`prompt-engineering`**: Creating, refactoring, or reviewing PM/specialist prompts
- **`specialist-creation`**: Adding new specialists or modifying specialist architecture
- **`tool-development`**: Building new tools, refactoring existing tools, reviewing tool implementations
- **`autonomous-testing`**: Testing workflows, validating PM behavior, post-implementation verification

### Autonomous Behavior Standards
- **Dynamic Planning:** Agents analyze context and plan adaptively, not follow rigid recipes
- **Suggestive Agents:** Agents come to the user with details, options, and recommendations - not wait passively for everything to be specified
- **Graceful Adaptation:** Handle missing data, tool failures, and edge cases with fallback strategies
- **Self-Review:** Critique outputs before returning; iterate when confidence is low
- **Transparent Communication:** Flag limitations, assumptions, and data gaps clearly
- **Learning Orientation:** System should improve from past executions

### Prompt Engineering for Autonomy
- **Version prompts alongside code** - no hardcoded instructions in agent logic
- **XML structure, right altitude, canonical examples** - no Python code in prompts

### Documentation Strategy
- **[CRITICAL] Check first, update rather than duplicate**: Review existing docs before creating new ones
- **Create only when necessary**: Novel topics, complex specifications, long-term architectural impact
- **Make scannable**: Date/status header, executive summary, tables/schemas/examples
- Update architectural docs in lockstep with major decisions

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

### Common Gotchas

**LangChain v1 Stack**:
- Stable releases: `langchain>=1.1.0`, `langgraph>=1.0.4`, `deepagents>=0.2.8`

**Windows**:
- Use `.venv\Scripts\activate` (not `source`)
- Git line endings: LF (`.gitattributes`)

**Error Handling**:
- Tools NEVER raise exceptions - return structured dicts with `{"success": bool, "error": ...}`
- Use `build_agent_error_response()` from `core.tool_error_handler` for consistent error handling
- Error responses include actionable guidance enabling agents to reason and retry intelligently

**Console Output**:
- Always use `safe_print` instead of `print` for CLI/test output

**Testing**:
- Always use the autonomous testing framework for test scenarios (not manual scripts)

### Quick Navigation

- **Project Status**: `README.md`
- **Architecture Docs**: `docs/architecture/README.md` (navigation hub)
- **LangSmith Traces**: https://smith.langchain.com