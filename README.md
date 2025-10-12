# AutifyME - Agentic Business Operating System

**Status:** 🚧 MVP Development - WhatsApp Cataloging Active
**Last Updated:** October 8, 2025

---

## 🎯 Quick Links

| Document | Purpose |
|----------|---------|
| **[Architecture Docs](docs/architecture/README.md)** | Technical design & implementation |
| **[CLAUDE.md](CLAUDE.md)** | Development guidelines & standards |
| **[DeepAgents Fix](DEEPAGENTS_FIX.md)** | Library compatibility notes |
| **[Critical Bug Fix](CRITICAL_BUG_FIX.md)** | Recent HITL issue resolution |

---

## 📊 Current Status

### ✅ Completed:
- Refactored workflow orchestration (multi-channel ready)
- HITL approval flow with state persistence
- Error recovery and abandonment detection
- WhatsApp webhook with idempotency
- LangSmith observability integration

### 🚧 In Progress:
- WhatsApp cataloging workflow validation
- Unit test coverage for orchestration layer

---

## 🚀 Quick Start

### Prerequisites:
- Python 3.11+
- `uv` package manager
- Supabase account
- LangSmith account
- OpenAI API key

### Local Development Setup:
```bash
cd agents
uv venv
.venv\Scripts\activate  # Windows | source .venv/bin/activate on Unix
uv pip install -e ".[dev]"

# Configure .env with your API keys
# Run smoke test
uv run python test_cataloging_workflow_clean.py

# Start webhook server
uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload --port 8000
```

### 🚀 Production Deployment:
See **[Deployment Guide](docs/deployment/README.md)** for production deployment options with free tiers and HTTPS support.

**Quick Deploy Options:**
- **Railway** (Recommended): Automatic HTTPS, PostgreSQL included, **custom domains FREE**, $0/month free
- **Render**: 750 free hours/month, custom domains, $0/month free
- **Fly.io**: Global deployment, custom domains, $0/month free

All platforms support the included Docker configuration and GitHub Actions CI/CD pipeline.

### 🌐 Custom Domain Setup (Railway)
Railway provides **free custom domains** with automatic HTTPS:

1. Railway Dashboard → Your Project → Settings → Domains
2. Add your domain (e.g., `api.autifyme.com`)
3. Update DNS records as instructed
4. Railway issues SSL certificates automatically

**Benefits:** Professional URL, better for WhatsApp webhook, improved SEO.

See [CLAUDE.md](CLAUDE.md) for complete development reference.

---

## 🏗️ Architecture

```
Project Manager Agent (Orchestrator)
    ↓
Department Head Agents (Managers)
    ↓
Specialist Agents (Doers)
    ↓
Tools (Utilities)
```

**Pattern:** Hierarchical Agent Swarm + Hexagonal Architecture

**Key Principles:**
- Architecture-First Development
- LangChain v1 Best Practices
- Type Safety (Pydantic everywhere)
- Middleware for Cross-Cutting Concerns
- Generic-First Design (reusability)

---

## 📁 Project Structure

```
AutifyME/
├── agents/
│   ├── src/autifyme_agents/
│   │   ├── workflows/
│   │   │   ├── orchestration/      # Generic workflow coordination
│   │   │   └── channels/           # Channel-specific adapters
│   │   ├── entrypoints/            # API webhooks
│   │   ├── departments/            # Department head agents
│   │   ├── tools/                  # Reusable tool implementations
│   │   ├── integrations/           # External service clients
│   │   ├── schemas/                # Pydantic models
│   │   └── core/                   # Config, middleware, ports
│   └── scripts/                    # Utility scripts
├── docs/architecture/              # Technical specifications
├── CLAUDE.md                       # Development standards
└── DEEPAGENTS_FIX.md              # Library compatibility
```

---

## 🛠️ Tech Stack

- **Framework:** LangChain 1.0.0a12, LangGraph 1.0.0a4, DeepAgents 0.0.11
- **Observability:** LangSmith
- **Database:** Supabase + PostgreSQL (LangGraph checkpointer)
- **LLMs:** OpenAI (gpt-5-mini-2025-08-07)
- **Package Manager:** `uv`
- **Type Safety:** Pydantic v2

---

## 🎯 Next Steps

1. Validate refactored architecture in production (1-2 days)
2. Complete unit test coverage for orchestration layer
3. Add SMS/Telegram channel adapters (~150 lines each)
4. Remove deprecated `whatsapp_cataloging_runner.py` after validation

---

## 📚 Documentation

### Essential Reading:

1. **[CLAUDE.md](CLAUDE.md)** - Development standards, commands, architecture canon
2. **[Architecture Docs](docs/architecture/README.md)** - Complete technical specifications
3. **[DeepAgents Fix](DEEPAGENTS_FIX.md)** - Library compatibility notes
4. **[Critical Bug Fix](CRITICAL_BUG_FIX.md)** - Recent HITL issue resolution

---

## 🏗️ Architecture Principles

- **Hexagonal Architecture**: Core logic independent of external services
- **Single Responsibility**: Each component does one thing well
- **Strategy Pattern**: Channel behavior injected via protocol
- **Type Safety**: Pydantic models for all data transfer
- **Observability**: LangSmith tracing on all workflows

---

## 🤝 Contributing

See [CLAUDE.md](CLAUDE.md) for complete development guidelines:
- Architecture-first design process
- LangChain v1 patterns and verification
- Essential commands and workflows
- Common gotchas and solutions

