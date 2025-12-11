# Systematic Redesign Plan - Bottom-Up Approach

**Date:** 2025-12-11
**Status:** IN PROGRESS
**Approach:** Bottom-up like building a house - foundation to roof

---

## Architecture Layers

```
Layer 4: PM Prompt
         ↑ (Orchestration - brings all layers together)

Layer 3: Agent Prompts (Analysts + Specialists)
         ↑ (Identity, reasoning, execution patterns)

Layer 2: Specialist Descriptions
         ↑ (Who uses what tools and why)

Layer 1: Tool Descriptions ← START HERE
         (Atomic capabilities - the foundation)
```

---

## Layer 1: Tool Descriptions (Foundation)

**Format:** PURPOSE / USE WHEN / DON'T USE / RETURNS / NEEDS

**Order:** Logical dependency chain (discover → read → analyze → execute)

### Read/Discovery Tools (Build foundation for exploration)

1. **inspect_schema** - Schema discovery (most foundational - discover structure first)
2. **read_data** - Database queries (query discovered structure)
3. **view_image** - Visual observation (parallel to read_data)
4. **aggregate_data** - Analytical queries (builds on read_data)

### Research Tools (External exploration)

5. **research_product_tool** - External product research
6. **extract_web_content_tool** - Web content extraction

### Execution Tools (Build on discovered/analyzed foundation)

7. **write_data** - Database writes (HITL) - writes to discovered/validated structure
8. **image_studio** - Image generation

---

## Layer 2: Specialist Descriptions (Framework)

**Format:** Domain ownership + DELEGATE WHEN + DOES NOT + REQUIRES

**Order:** Analysts first (read-only), then Specialists (execution)

### Analysts (Read-Only)

1. **visual_analyst** - Uses: view_image
2. **product_analyst** - Uses: research_product_tool, extract_web_content_tool
3. **catalog_analyst** - Uses: read_data, aggregate_data

### Specialists (Execution)

4. **catalog_specialist** - Uses: All read tools + inspect_schema + write_data
5. **creative_specialist** - Uses: All read tools + view_image + image_studio + write_data

---

## Layer 3: Agent Prompts (Structure)

**Format:** Identity + Capabilities + Principles + Examples

**Order:** Same as Layer 2 (Analysts → Specialists)

1. visual_analyst.prompt
2. product_analyst.prompt
3. catalog_analyst.prompt
4. catalog_specialist.prompt
5. creative_specialist.prompt

---

## Layer 4: PM Prompt (Roof)

**Format:** Identity + Subagent Roster + Dynamic Reasoning + Communication Protocol + Examples

**Components:**
- PM identity (Dynamic Intelligent Orchestrator)
- Complete subagent roster with descriptions
- Dynamic reasoning pattern (no fixed workflows)
- Delegation protocol (1-2 liner + context passing)
- Filesystem protocol
- Multi-domain coordination examples

---

## Dependencies

**Layer 2 depends on Layer 1:**
- Can't write specialist descriptions without knowing exact tool capabilities
- Tool PURPOSE/USE WHEN guides DELEGATE WHEN decisions

**Layer 3 depends on Layers 1 & 2:**
- Agent prompts reference tool capabilities from Layer 1
- Agent prompts embody domain ownership from Layer 2

**Layer 4 depends on all layers:**
- PM prompt includes complete subagent roster (Layer 2)
- PM prompt references tool ecosystem (Layer 1)
- PM prompt shows delegation patterns that agents will understand (Layer 3)

---

## Current Status

- ✅ Vision finalized (ARCHITECTURAL_VISION.md)
- ✅ Refinement sessions complete (VISION_REFINEMENT_SESSION.md)
- ✅ Layer 1: Tool Descriptions (COMPLETE - 68% compression, 912 lines → 289 lines)
  - ✅ All 8 tools optimized (inspect_schema, read_data, view_image, aggregate_data, research_product_tool, extract_web_content_tool, write_data, image_studio)
- ⏳ Layer 2: Specialist Descriptions (NEXT)
- ⏳ Layer 3: Agent Prompts
- ⏳ Layer 4: PM Prompt

---

## References

- **Architectural Vision:** [ARCHITECTURAL_VISION.md](./ARCHITECTURAL_VISION.md)
- **Vision Refinement:** [VISION_REFINEMENT_SESSION.md](./VISION_REFINEMENT_SESSION.md)
- **Diagnostic Analysis:** [AGENT_TOOL_REDESIGN.md](./AGENT_TOOL_REDESIGN.md)
