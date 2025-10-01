# AutifyME Architecture Documentation

**Last Updated:** Oct 1, 2025

This directory contains the complete architectural documentation for the AutifyME Agentic Business Operating System.

---

## 📚 Core Documents (Read in Order)

### 1. **[Whitepaper](../whitepaper.md)** - Vision & Product Strategy
Start here for the big picture: vision, product model, and roadmap.

### 2. **[Tech Stack](./TECH_STACK.md)** - Technology Choices
Our technology decisions with reasoning: LangChain v1, Supabase, LangSmith, etc.

### 3. **[LangChain v1 Features](./LANGCHAIN_V1_FEATURES.md)** - Framework Reference
Comprehensive guide to LangChain/LangGraph v1 features we're leveraging. **Review before implementation.**

### 4. **[Agents Design](./AGENTS_DESIGN.md)** - Agent Architecture
The hierarchical agent system: Project Manager → Department → Specialist → Tools.

### 5. **[Project Manager Design](./PROJECT_MANAGER_DESIGN.md)** - PM Implementation
Detailed implementation guide for the Project Manager Agent using `deepagents`.

### 6. **[Project Structure](./PROJECT_STRUCTURE.md)** - Folder Organization
Hexagonal architecture: core, integrations, tools, workflows, schemas.

### 7. **[Architecture Review](./ARCHITECTURE_REVIEW.md)** - Roadmap & Plan
Architecture validation, implementation roadmap, and success criteria.

---

## 🎯 Workflow-Specific Docs

### [WhatsApp Cataloging](./WHATSAPP_CATALOGING_WORKFLOW.md)
Design for the first feature: WhatsApp-based product cataloging for Indian SMEs.

---

## 📖 Reading Guide by Role

### **For Architects/Tech Leads:**
1. [Whitepaper](../whitepaper.md) → [Tech Stack](./TECH_STACK.md) → [Agents Design](./AGENTS_DESIGN.md) → [Architecture Review](./ARCHITECTURE_REVIEW.md)

### **For New Developers:**
1. [LangChain v1 Features](./LANGCHAIN_V1_FEATURES.md) - Understand framework capabilities
2. [Project Structure](./PROJECT_STRUCTURE.md) - Navigate the codebase
3. [Agents Design](./AGENTS_DESIGN.md) - Understand architecture
4. [Lessons Learned](./LESSONS_LEARNED_OCT_2025.md) - Avoid common mistakes

### **For Implementation:**
1. [WhatsApp Cataloging](./WHATSAPP_CATALOGING_WORKFLOW.md) - First workflow design
2. [Project Manager Design](./PROJECT_MANAGER_DESIGN.md) - PM agent implementation
3. Review [Cursor Rules](../../.cursor/rules/) - Follow all 11 guardrails

### **For Code Review:**
1. [Architecture Review](./ARCHITECTURE_REVIEW.md) - Validation checklist
2. [LangChain v1 Features](./LANGCHAIN_V1_FEATURES.md) - Verify v1 patterns used
3. Check compliance with [Cursor Rules](../../.cursor/rules/)

---

## 🔑 Key Principles

1. **Architecture-First:** Build complete production-grade infrastructure from day 1
2. **v1 Native:** Leverage LangChain v1's built-in patterns (HITL, error handling, structured outputs)
3. **Hexagonal Architecture:** Core logic decoupled from external services
4. **Single-Tenant:** Each customer gets isolated instance (for now)
5. **Design-First:** Document workflows in markdown before coding

---

## 🚀 Quick Start

**Before building any feature:**
1. ✅ Review [LangChain v1 Features](./LANGCHAIN_V1_FEATURES.md) for latest capabilities
2. ✅ Check if framework-native solution exists (prefer over custom)
3. ✅ Use v1 patterns: `interrupt_before`, `ToolStrategy`, `.with_structured_output()`

---

## 📝 Document Status

| Document | Status | Last Updated | Purpose |
|----------|--------|--------------|---------|
| [Tech Stack](./TECH_STACK.md) | ✅ Current | Oct 1, 2025 | Technology choices |
| [LangChain v1 Features](./LANGCHAIN_V1_FEATURES.md) | ✅ Current | Oct 1, 2025 | v1 reference guide |
| [Agents Design](./AGENTS_DESIGN.md) | ✅ Current | Sep 30, 2025 | Agent architecture |
| [Project Manager](./PROJECT_MANAGER_DESIGN.md) | ✅ Current | Sep 30, 2025 | PM implementation |
| [Project Structure](./PROJECT_STRUCTURE.md) | ✅ Current | Sep 30, 2025 | Folder structure |
| [Architecture Review](./ARCHITECTURE_REVIEW.md) | ✅ Current | Sep 30, 2025 | Roadmap & validation |
| [WhatsApp Cataloging](./WHATSAPP_CATALOGING_WORKFLOW.md) | ✅ Current | Sep 30, 2025 | First workflow |

---

## 📝 Documentation Maintenance

### When to Update:
- **After implementing a feature:** Update relevant architecture doc + mark complete in `../../IMPLEMENTATION_STATUS.md`
- **After architecture decision:** Update relevant doc + create new Cursor Rule if needed
- **After finding a bug:** Add to [Lessons Learned](./LESSONS_LEARNED_OCT_2025.md) if valuable

### Guidelines:
- ✅ **Update once:** Change info in one place only (single source of truth)
- ✅ **Link, don't duplicate:** Reference other docs instead of copying
- ✅ **Keep dates current:** Update "Last Updated" when changing
- ❌ **Don't create summaries:** Update existing docs instead of new summary files

---

**Need help?** Start with the [Architecture Review](./ARCHITECTURE_REVIEW.md) for the implementation roadmap.

