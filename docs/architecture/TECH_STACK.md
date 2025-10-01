# Tech Stack

## Core Framework
- **LangChain v1** + **LangGraph v1** (v0.2.60+)
- Native HITL, error handling, structured outputs, checkpointing
- See [LANGCHAIN_V1_FEATURES.md](./LANGCHAIN_V1_FEATURES.md) for details

## Database & Storage
- **Supabase** (Postgres + Auth + Storage + Realtime)
- Direct Postgres connection for LangGraph checkpointing

## Observability
- **LangSmith** - Purpose-built for LLM/agent tracing
- Essential for debugging multi-agent workflows

## Development Tools
- **uv** - Fast Python package manager
- **Python 3.11+** - Required for async context propagation

## Architecture Patterns
- **Hexagonal Architecture** - Core decoupled from integrations
- **Dependency Injection** - Storage/LLM providers injected
- **LCEL** - LangChain Expression Language for composability
