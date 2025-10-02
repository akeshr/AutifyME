# Implementation Roadmap (LangChain v1 Stack)

This roadmap captures the concrete engineering work that follows from the features available in our installed stack (LangChain `1.0.0a10`, LangGraph `1.0.0a4`, DeepAgents `0.0.11rc1`). It complements the architecture references by focusing on *what we need to build next*.

---

## 1. Middleware Adoption for Cataloging Workflow
- Add `HumanInTheLoopMiddleware` with tool-specific interrupt config for `save_product` (approve / edit / reject flows).
- Introduce `SummarizationMiddleware` to keep conversation history compact while preserving tool-call pairs.
- Enable `AnthropicPromptCachingMiddleware` (and provider equivalents) to reduce prompt cost when models support caching.

## 2. Tool & Dependency Injection Refactor
- Replace global storage client (`_storage_client`) with ToolNode injection using `InjectedState` / `InjectedStore`.
- Ensure tools return LangGraph `Command` objects when they mutate state (align with ToolNode patterns).
- Define typed tool error handling (custom handlers or `@retry` policies) consistent with ToolNode semantics.

## 3. Checkpointing & Runtime Enhancements
- Finalize PostgresSaver migrations on Supabase (matching `langgraph.checkpoint.postgres` schema).
- Leverage `Runtime` context to pass company/user metadata instead of embedding it in prompts.
- Document resume/replay flow using `Command`/`Send` structures for cataloging approvals.

## 4. DeepAgents Preparation for Project Manager
- Prototype `PlanningMiddleware`, `FilesystemMiddleware`, and `SubAgentMiddleware` in a small playground to validate plan tracking and sub-agent invocation.
- Define PM-level structured outputs (e.g., `ProjectPlan`, `DepartmentResult`) using `ToolStrategy` or `ProviderStrategy`.
- Plan HITL configuration via `tool_configs` for high-risk actions (publish, invoice, etc.).

## 5. Testing & Observability Upgrades
- Wire LangSmith trace metadata using ToolNode configs and middleware (workflow, department, specialist tags).
- Add assertions around structured outputs in workflow scripts (moving toward automated tests).
- Document SSE/stream handling for providers (OpenAI/Anthropic) to support future UI integrations.

---

**Next Step:** Prioritize sections 1–2 to solidify the cataloging workflow, then iterate toward sections 3–4 as we prepare the Project Manager agent. Sections 5 runs in parallel to preserve observability and testability as we refactor.
