# Tech Stack Reference

| Layer | Technology | Notes |
| --- | --- | --- |
| **Agents & Workflow** | LangChain v1 (`langchain`, `langchain-core`) | Production agent builder (`create_agent`) backed by LangGraph. |
|  | LangGraph v1 (`langgraph`, `langgraph.checkpoint.postgres`) | State machines, runtime context, checkpointing. |
|  | DeepAgents (`deepagents`) | Planning-oriented middleware for future Project Manager agent. |
| **Observability** | LangSmith | Tracing, evaluation, prompt management. |
| **LLM Providers** | OpenAI (`langchain-openai`) | gpt-5-nano-2025-08-07 models with structured output support. |
|  | Anthropic (`langchain-anthropic`) | Claude models with prompt caching middleware. |
| **Data & Storage** | Supabase (PostgreSQL) | Single-tenant database hosting checkpoints and business data. |
|  | PostgresSaver | LangGraph checkpoint implementation aligned with Supabase. |
| **Runtime Tooling** | uv | Fast Python package manager. |
|  | Python 3.11 | Required for LangChain v1 stack. |
| **Testing & Evaluation** | Script-based workflow runs (`agents/test_cataloging_workflow.py`) | Manual validation while automated testing framework is deferred per stakeholder directive. |
