# Tech Stack Reference

**Created:** September 29, 2025
**Last Updated:** November 25, 2025

---

## Core Framework

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| Agent Builder | `langchain` | >=1.1.0 | Agent construction, tools, structured outputs |
| Orchestration | `langgraph` | >=1.0.4 | State machines, checkpointing, workflow graphs |
| Advanced Agents | `deepagents` | >=0.2.8 | SubAgent pattern, PM orchestration |
| Checkpointing | `langgraph-checkpoint-postgres` | >=3.0.1 | PostgreSQL state persistence |

---

## LLM Providers

| Provider | Package | Primary Use |
|----------|---------|-------------|
| **Google AI** | `langchain-google-genai>=3.2.0` | Primary - gemini-2.5-flash for PM and specialists |
| OpenAI | `langchain-openai>=1.1.0` | Fallback, image analysis |
| Anthropic | `langchain-anthropic>=1.2.0` | Fallback |

**Default Model:** `gemini-2.5-flash` (PM: temp=0.5, Specialists: temp=0.3)

---

## Data & Storage

| Component | Technology | Purpose |
|-----------|------------|---------|
| Database | Supabase (PostgreSQL) | Single-tenant data + checkpoints |
| Client | `supabase` | Python client for CRUD operations |
| Postgres Driver | `psycopg[binary]` | >=3.2.10 | LangGraph checkpointer requirement |

---

## Research & Tools

| Component | Package | Purpose |
|-----------|---------|---------|
| Web Search | `langchain-tavily` | >=0.2.11 | Product research, competitive analysis |
| Image Processing | `pillow` | >=10.0.0 | Vision API optimization (resize to 2048px) |

---

## Webhook Stack

| Component | Package | Purpose |
|-----------|---------|---------|
| API Framework | `fastapi` | >=0.118.0 | WhatsApp webhook endpoints |
| Server | `uvicorn` | >=0.37.0 | ASGI server |

---

## Observability

| Component | Technology | Purpose |
|-----------|------------|---------|
| Tracing | LangSmith | Trace analysis, debugging, prompt iteration |

---

## Development

| Component | Technology | Purpose |
|-----------|------------|---------|
| Python | 3.12+ | Required version |
| Package Manager | `uv` | Fast dependency management |
| Linting | `ruff` | >=0.5.0 | Code quality, import sorting |
| Type Checking | `mypy` | >=1.10.0 | Strict mode, Pydantic plugin |
| Testing | `pytest` | >=8.0.0 | Unit + integration tests |

---

## Key Dependencies (pyproject.toml)

```toml
# Core
langchain>=1.1.0
langgraph>=1.0.4
deepagents>=0.2.8

# LLM Providers
langchain-google-genai>=3.2.0
langchain-openai>=1.1.0
langchain-anthropic>=1.2.0

# Research
langchain-tavily>=0.2.13

# Data
supabase>=2.24.0
psycopg[binary]>=3.2.13
pydantic>=2.12.5

# Webhook
fastapi>=0.123.0
uvicorn>=0.38.0

# Utilities
pillow>=12.0.0
tenacity>=9.1.2
python-dotenv>=1.2.1
```

---

## Architecture Notes

- **Hexagonal Architecture:** Core depends only on ports; adapters at edges
- **Type Safety:** 100% mypy strict compliance, zero `type: ignore`
- **Single Tenant:** One company context per deployment
- **Intelligence-First:** Trust LLM reasoning, minimal scaffolding
