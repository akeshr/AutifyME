---
applyTo: '**'
---
# CLAUDE Canon Instructions

## Output Discipline
- ASCII only; never use emojis or fancy glyphs.
- Default to Jarvis output style from `.claude/output-styles/jarvis.md` for tone and formatting.

## Architecture & Vision
- Preserve the 2-level swarm: Project Manager → Specialists → Tools; PM plans dynamically and specialists stay domain-centric for reuse.
- Build intelligence-first: supply goals + rich context, keep scaffolding light, and avoid over-orchestrating when an LLM can reason autonomously.
- Enforce ULTRATHINK: design from first principles, refactor ruthlessly before layering features, and refuse architectural compromises even if legacy code suggests otherwise.
- Maintain Hexagonal boundaries: core logic talks only to ports; adapters (storage, channels, integrations) isolate persistence and external services.
- Persist state (workflows, approvals, checkpoints) to guarantee restart/recovery; storage adapters must remain the single source of truth.

## Engineering Process
- Design before build: update specs under `docs/architecture/` capturing flows, contexts, schemas, and PM↔specialist interactions.
- Research exhaustively: verify APIs in REPL/inspect, enumerate edge cases, and document findings for multi-platform or cross-cutting concerns.
- Treat resilience, observability, and verification as baseline requirements, not polish.
- Question reuse: before creating a specialist, answer which workflows/domains will share it.

## Standards for Agents & Tools
- Specialists built with `langchain.agents.create_agent`; orchestrators via DeepAgents with `{messages}`/`{agent_scratchpad}` contract intact.
- Keep HITL in tool_configs + middleware; do not bake HITL into runner logic.
- Specialists/tools follow single responsibility, structured outputs (Pydantic), multimodal support, and must raise `ToolException` on recoverable failures.
- Agents must self-plan, adapt to missing data, self-review outputs, and surface limitations explicitly.

## Prompt & Context Governance
- Version prompts alongside code (under `prompts/`); follow `PROMPT_ENGINEERING_STANDARDS.md` for XML framing and autonomy-focused guidance.
- PM prompts prioritize situational analysis + adaptive planning; specialist prompts emphasize adaptation, transparent failure, and iterative improvement.
- Load context via middleware (e.g., `context_middleware.py`) so PM and specialists share the same canonical summaries.

## Documentation Expectations
- Check existing docs before authoring new ones; extend rather than duplicate unless topic is novel/complex.
- New docs must be scannable (date/status, executive summary, tables/examples) and link to related canon.
- Capture architecture decisions, test strategies, and investigative findings contemporaneously with code changes.

## Quality & Testing
- Run `uv run pytest tests --cov=autifyme_agents`, `uv run ruff check .`, and `uv run mypy .` before merges; treat failures as blockers.
- Debug methodically with full traces/logs, validating assumptions one variable at a time.
- Keep HITL safeguards intact for production safety.

## Operational Commands
- Setup: `uv venv`, `.venv\Scripts\activate`, `uv pip install -e ".[dev]"`.
- Runtime: `uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload`.
- API verification: `uv run python -c "from dotenv import load_dotenv; load_dotenv('.env'); # test code"` as scratch REPL.

Adhere to this canon on every change; when trade-offs arise, escalate with explicit architectural justification before deviating.
