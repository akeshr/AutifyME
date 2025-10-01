# AutifyME - Agentic Business Operating System

**Status:** 🚧 Foundation Layer - 40% Complete (Grade: B-)  
**Last Updated:** October 1, 2025

---

## 🎯 Quick Links

| Document | Purpose |
|----------|---------|
| **[Implementation Status](IMPLEMENTATION_STATUS.md)** | Current state, progress, blockers |
| **[Deep Code Analysis](DEEP_CODE_ANALYSIS.md)** | Architectural audit & fixes |
| **[Architecture Review](docs/architecture/ARCHITECTURE_REVIEW.md)** | Implementation roadmap |
| **[Whitepaper](docs/whitepaper.md)** | Product vision |
| **[Architecture Docs](docs/architecture/README.md)** | Full technical design |

---

## 📊 Current Status

### ✅ Working:
- Hexagonal Architecture (Grade: A)
- Type Safety with Pydantic (Grade: A)
- Middleware System (Grade: A-)
- LangSmith Integration (Grade: B+)
- Basic Cataloging Workflow (E2E working)

### ❌ Critical Blockers (P0):
1. **No Error Handling** - Missing ToolStrategy/ToolException (2-3 days)
2. **No State Persistence** - Missing PostgresSaver checkpointing (1 day)
3. **No Testing Framework** - No unit/integration tests (2-3 days)

**Timeline to Production:** 5-6 days

---

## 🚀 Quick Start

### Prerequisites:
- Python 3.11+
- `uv` package manager
- Supabase account
- LangSmith account
- OpenAI API key

### Setup:
```bash
# 1. Clone and navigate
cd AutifyME/agents

# 2. Create virtual environment
uv venv

# 3. Activate environment
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate

# 4. Install dependencies
uv pip install -e .

# 5. Configure environment
cp .env.example .env
# Edit .env with your keys

# 6. Run test workflow
uv run python test_cataloging_workflow.py
```

See [LangSmith Setup](docs/setup/LANGSMITH_SETUP.md) for detailed configuration.

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
├── agents/                    # Python agentic service
│   ├── src/autifyme_agents/
│   │   ├── core/             # Factories, middleware, config
│   │   ├── integrations/     # External service adapters
│   │   ├── tools/            # Agent-accessible operations
│   │   ├── specialists/      # Single-task agents
│   │   ├── departments/      # Multi-specialist orchestrators
│   │   ├── schemas/          # Pydantic models
│   │   └── prompts/          # Version-controlled prompts
│   └── test_cataloging_workflow.py
├── docs/
│   ├── architecture/         # Technical design docs
│   ├── setup/               # Configuration guides
│   └── whitepaper.md        # Product vision
├── .cursor/rules/           # 11 development guardrails
├── IMPLEMENTATION_STATUS.md # Current state tracker
└── DEEP_CODE_ANALYSIS.md   # Architectural audit
```

---

## 🛠️ Tech Stack

- **Agentic Framework:** LangChain v1 (latest), LangGraph v1
- **Observability:** LangSmith
- **Database:** Supabase (PostgreSQL)
- **LLMs:** OpenAI (gpt-4o), Anthropic (Claude)
- **Package Manager:** `uv`
- **Type Safety:** Pydantic
- **Testing:** pytest (to be set up)

---

## 🎯 Next Steps

### This Week (P0):
1. Implement error handling (2-3 days)
2. Add checkpointing (1 day)
3. Set up testing framework (2-3 days)

### Following Week:
4. Structured logging (1 day)
5. Database migrations (0.5 days)
6. Memory management (1 day)

---

## 📚 Documentation

### Reading Order:

**New to the project?**
1. This README (you are here)
2. [Implementation Status](IMPLEMENTATION_STATUS.md) - Current state
3. [Architecture Overview](docs/architecture/README.md) - Navigate all architecture docs

**Setting up?**
1. [LangSmith Setup](docs/setup/LANGSMITH_SETUP.md) - Configuration guide
2. Run `test_cataloging_workflow.py` - Verify it works

**Contributing?**
1. Review all [Cursor Rules](.cursor/rules/) - 11 guardrails
2. [LangChain v1 Features](docs/architecture/LANGCHAIN_V1_FEATURES.md) - What's available
3. [Lessons Learned](docs/architecture/LESSONS_LEARNED_OCT_2025.md) - Common pitfalls

**Technical review?**
1. [Deep Code Analysis](DEEP_CODE_ANALYSIS.md) - Audit results
2. [Architecture Review](docs/architecture/ARCHITECTURE_REVIEW.md) - Roadmap

---

## 🔒 Cursor Rules (Guardrails)

11 active rules enforcing:
- Architecture-First Philosophy
- LangChain v1 Best Practices
- Hexagonal Architecture
- Type Safety
- Middleware Patterns
- Context Engineering
- Debugging Methodology

See `.cursor/rules/` for details.

---

## 🤝 Contributing

**Development Philosophy:**
1. **Architecture-First:** No shortcuts, production-grade from day 1
2. **Design-First:** Document in markdown before coding
3. **Generic-First:** Build for the system, not just one workflow
4. **Explain the Why:** All decisions must be justified

---

## 📊 Progress Tracking

- **Foundation:** 40% (5/10 production criteria met)
- **Grade:** B- (improved from C-)
- **Deployment Ready:** No (3 P0 blockers)

See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for detailed tracking.

---

## 📄 License

[To be determined]

---

**Built with ❤️ for Indian small businesses**

