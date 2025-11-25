**Architecture**
- entrypoints/whatsapp_webhook.py handles FastAPI intake, persists idempotency via storage.check_and_mark_message_processed, and fires BackgroundTasks; mirror this pattern when onboarding new channels.
- workflows/orchestration/runner.py acts as blind executor with OutcomeTrackingMiddleware and blank-response retries; keep core logic here agnostic and push domain logic into handlers.
- workflows/project_manager.py builds the DeepAgents PM, loading PMBaseContext via middleware/context_middleware.py and attaching SubAgents from specialists/product_architecture_specialist.py et al.
- Maintain hexagonal boundaries: core/ports.py defines contracts, integrations/storage/{storage_factory.py,supabase_client.py,postgres_saver_factory.py} supply adapters and must be the only Supabase/Postgres touchpoints.

**HITL Flow**
- approval_analyzer.py plus prompts/approval_analyzer.prompt turn user replies into BatchApprovalResponse; never parse approval text manually.
- ApprovalCoordinator with workflows/handlers/cataloging_handler.py formats approval batches (including OperationIntent summaries) and routes send_approval_request/send_text through channel adapters.
- workflows/interrupt_unpacker.py normalizes LangGraph interrupt payloads (DeepAgents batch, legacy lists, single dicts); extend here whenever a new tool produces novel interrupt shapes.
- Async checkpointer comes from integrations/storage/postgres_saver_factory.py using DATABASE_URL; ensure migrations run via get_async_checkpointer(setup=True) before relying on resume flows.

**Data & Tools**
- tools/universal_crud_tool.py is the canonical persistence surface: specialists emit OperationIntent schemas, and the tool enforces dependency ordering, transactions, and validation.
- Schema discovery flows through schemas/registry.py and tools/schema_tools.get_product_schema; use them before inventing bespoke SQL.
- SupabaseStorageClient in integrations/storage/supabase_client.py handles HTTP/1.1 sessions, numeric normalization, idempotency RPC, and async clients per event loop; reuse instead of raw supabase.* calls.
- middleware/context_middleware.py loads catalog/taxonomy summaries with graceful degradation; PM prompts assume these summaries exist even when counts are zero.

**Specialists & Prompts**
- specialists/*.py follow create_*_specialist factories using langchain.agents.create_agent; mirror product_architecture_specialist.py when adding domains.
- Load prompts from prompts/** via core/prompt_loader.py, and conform to docs/architecture/tech/PROMPT_ENGINEERING_STANDARDS.md for XML framing and version control.
- Honor .cursor/rules/08-langchain-agent-creation.mdc: prompts expect {messages} and {agent_scratchpad}, and agents invoke via ainvoke({"messages": [...]}) config.
- Keep tool HITL policies inside specialist tool_configs (see specialists/product_architecture_specialist.py) so runner stays generic.

**Developer Setup**
- Bootstrap in agents/: uv venv; .venv\Scripts\activate; uv pip install -e ".[dev]" (pyproject requires Python 3.12+).
- .env must include SUPABASE_URL, SUPABASE_ANON_KEY or SERVICE_ROLE_KEY, DATABASE_URL (LangGraph checkpointer), WhatsApp credentials, and optional Tavily/LangSmith keys per core/config.py.
- Local webhook: uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload --port 8000; structured logging configured by core/logging_config.py.
- Use uv run python -m autifyme_agents.cli.simulate ... or tests/cli/pm_chat.py for manual exercises to keep dependencies consistent.

**Testing & QA**
- Run suites with uv run pytest tests --cov=autifyme_agents; per-scope commands live in tests/README.md (unit, integration, synthesizer).
- Autonomous testing framework sits in tests/tools/ (execute_scenario, get_trace_overview, get_run_details, get_run_messages, list_recent_tests); expect workflow-tester agents to call these.
- database/test_full_flow.py exercises cataloging permutations and verifies workflow_outcomes via Postgres; run via uv run python database/test_full_flow.py.
- Static quality gates: uv run ruff check . (line 100) and uv run mypy . (strict with pydantic plugin) must be clean before merges.

**Observability & Analytics**
- OutcomeTrackingMiddleware + outcome_tracker.py create WorkflowOutcome records and correlate LangSmith traces (tracking_id = run_id); never bypass when invoking PM.
- workflows/outcome_tracker.py persists to storage.save_workflow_outcome and handles similarity hashes; respect this when altering result schemas.
- LangSmith usage is automatic once LANGCHAIN_API_KEY and LANGCHAIN_PROJECT are set; inspect traces by thread/trace ids emitted in logging.
- logs/ and agents/logs/ capture structured JSON when file logging enabled; keep log_extra payloads small to avoid Pydantic errors.

**Reference Docs**
- docs/architecture/README.md links to DOMAIN_DESIGN_GUIDELINES, AGENTS_DESIGN, and LANGCHAIN_V1_FEATURES; review before architectural changes.
- CLAUDE.md codifies ULTRATHINK, hierarchy principles, and command canon; align commits with that doc.
- tests/README.md, docs/architecture/testing/AUTONOMOUS_TESTING_FRAMEWORK.md, and .cursor/rules/* cover testing methodology and debugging expectations.
- Optional capabilities live under extensions/ (browser_automation_specialist, google_computer_use); install extras only when feature flagged.
