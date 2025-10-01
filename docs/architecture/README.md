# Architecture Documentation

## Core Documents

1. **[AGENTS_DESIGN.md](./AGENTS_DESIGN.md)** - Agent hierarchy and patterns
2. **[LANGCHAIN_V1_FEATURES.md](./LANGCHAIN_V1_FEATURES.md)** - LangChain v1 reference
3. **[TECH_STACK.md](./TECH_STACK.md)** - Technology choices
4. **[PROJECT_MANAGER_DESIGN.md](./PROJECT_MANAGER_DESIGN.md)** - PM agent spec
5. **[WHATSAPP_CATALOGING_WORKFLOW.md](./WHATSAPP_CATALOGING_WORKFLOW.md)** - First workflow

## Key Principles

- **Architecture-First:** Production-grade from day 1
- **LangChain v1 Native:** Use built-in patterns (HITL, error handling, structured outputs)
- **Hexagonal Architecture:** Core decoupled from external services
- **Context Engineering:** Minimize LLM context at every step

## Quick Start

Before implementing any feature:
1. Check [LANGCHAIN_V1_FEATURES.md](./LANGCHAIN_V1_FEATURES.md) for native solutions
2. Review [AGENTS_DESIGN.md](./AGENTS_DESIGN.md) for patterns
3. Follow Cursor rules in `../../.cursor/rules/`
