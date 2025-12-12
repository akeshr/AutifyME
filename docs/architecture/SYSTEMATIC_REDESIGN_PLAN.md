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

## Layer 0: Operating Contracts + Validation Gates (Make the vision executable)

The bottom-up prompt-first layering is correct, but it currently lacks a small set of **shared invariants** that prevent the exact anti-patterns documented in `AGENT_TOOL_REDESIGN.md` (role ambiguity, redundant work, inconsistent delegation/context, fragile multi-step coordination).

This is intentionally NOT a fixed workflow system. It’s a minimal set of contracts so dynamic orchestration stays stable.

### 0.1 Role Boundary Decision (PM vs Analysts vs Specialists)

**Goal:** eliminate PM role ambiguity (orchestrator vs executor) and stop redundant work.

- **PM MUST NOT analyze content.** No image viewing, no catalog queries, no product research.
- **PM SHOULD do only coordination primitives:**
  - Download/normalize attachments
  - Create/choose `workspace/thread_<id>/` directory
  - Read subagent outputs from filesystem
  - Decide sequencing / parallelism / escalation

**Implication:** if PM currently has tools like `view_image`, `read_data`, `inspect_schema`, treat them as legacy and (a) remove from PM prompt/tooling, or (b) explicitly forbid using them in the PM prompt.

### 0.2 Context Packet Contract (PM → Subagent)

**Problem:** “delegate with context (not instructions)” is right but underspecified, causing under/over-context and inconsistent handoffs.

Define a minimal, consistent context packet (even if it’s just prompt text) that always includes:
- `thread_dir`: path like `workspace/thread_123/`
- `user_intent`: 1-2 lines, intent only (no analysis)
- `inputs`: media paths, entity refs, record IDs, workspace location
- `constraints`: quality bar, deadlines, budget/latency limits if any
- `prior_findings`: file paths the subagent should read (if present)
- `deliverable`: exact output file name + summary expectation

### 0.3 Output Contract (Subagent → PM)

Keep your filesystem protocol, but add two invariants:
- Every subagent returns (a) **1-paragraph summary** and (b) **a single primary file path**.
- Every output file starts with a tiny header: `Date/Inputs/Assumptions/Confidence/Next actions`.

This makes PM synthesis reliable without PM re-analysis.

### 0.4 Dynamic Orchestration Guardrails (Anti-chaos, not workflows)

Add prompt-level rules (applies to PM and specialists):
- **Attempt budget:** max N retries / alternative strategies before escalation.
- **Ambiguity policy:** if >1 plausible interpretation affects data writes, escalate with options.
- **Conflict policy:** if two domain outputs disagree, either (a) route to a reviewer agent, or (b) ask user (never silently pick).

### 0.5 Validation Gates (How you prove the redesign works)

Add explicit gates so you don’t “feel” autonomy—you measure it:
- **Routing gate:** correct domain selection on a fixed scenario set
- **Redundancy gate:** no duplicate image viewing / duplicate catalog queries when analyst context exists
- **Resilience gate:** tool failures trigger fallbacks + structured escalation, not workflow death
- **HITL gate:** writes always route through approval analyzer flow (no ad-hoc parsing)

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
