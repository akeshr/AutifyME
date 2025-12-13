# AutifyME: Autonomy Problems - Root Cause Analysis

**Created:** December 13, 2025
**Status:** ACTIVE - Fixing problems sequentially
**Framework:** [Architectural Vision](./ARCHITECTURAL_VISION.md) - Autonomy principles
**Purpose:** Identify and fix root autonomy violations blocking agent effectiveness

---

## The Three Root Problems

### Problem 1: PM Orchestration is Not Correct - [FIXED]

**Status:** FIXED (December 13, 2025)

**Vision Requirement:**
> "The PM is an intelligent multi-domain orchestrator that reasons dynamically about workflow coordination. **NO fixed workflows** - every request gets customized coordination."

**What Was Fixed:**

| Issue | Before | After |
|-------|--------|-------|
| Fixed Workflow | "Typical flow: Visual -> Catalog -> Product -> Execute" | Dynamic reasoning framework with 4 steps |
| Content Tools | PM had `inspect_schema`, `read_data`, `view_image` | PM has ONLY `download_media` |
| Team Descriptions | "Delegate when: [scenario]" | Domain expertise + capabilities + use cases |
| Examples | 1 example, 1 workflow path | 4 examples showing different workflow patterns |
| Principles | Buried, scattered | Clear reasoning framework + senior partner mindset |

**Files Changed:**
- `agents/src/autifyme_agents/prompts/project_manager.prompt` - Complete rewrite
- `agents/src/autifyme_agents/workflows/project_manager.py` - Removed content analysis tools

**Key Changes:**
1. **Identity Reframed:** "THINKING orchestrator, not DOING executor"
2. **Explicit Boundaries:** "You Do NOT: Analyze content, query catalog, view images"
3. **Reasoning Framework:** 4-step dynamic reasoning (What do I know? Context needed? Which experts? Adapt dynamically)
4. **4 Examples:** Unknown image, Clear instruction, Multi-domain, Information query
5. **Tool Removal:** Removed `inspect_schema`, `read_data`, `view_image` from PM
6. **Policy Layer (NEW):** Explicit goals in priority order (Accuracy > Completeness > Efficiency > Proactivity)
7. **Self-Verification (NEW):** Content/Quality/Accuracy checks before every response
8. **Domain-Based Delegation (NEW):** Team descriptions define DOMAINS not capabilities - "Delegate the PROBLEM, they decide HOW"

**AI Autonomy Alignment:**

| Principle | Implementation |
|-----------|----------------|
| SENSE | PM senses user intent + conversation context; delegates content sensing to analysts |
| THINK: Knowledge | Catalog summary + taxonomy tree injected at startup |
| THINK: Policy | Explicit goals section with priority order |
| THINK: Reasoning | 4-step dynamic reasoning framework |
| ACT | Delegate to experts, synthesize results |
| Self-Awareness | Self-verification checklist before every response |

**Validation:** Test with autonomous testing framework to verify dynamic reasoning behavior.

---

### Problem 2: Analysts and Specialists are Very Restricted - [FIXED]

**Status:** FIXED (December 13, 2025)

**Vision Requirement:**
> "Specialists are autonomous domain masters who explore possibilities... **Explorative Problem-Solving (Explore -> Reason -> Output) ALWAYS**... Autonomous regardless of analyst context."

**What Was Fixed:**

| Agent | Before | After |
|-------|--------|-------|
| **catalog_specialist** | "WITH enriched context from analysts", "You focus on EXECUTION" | Autonomy declaration, Explore->Reason->Output framework, Self-verification |
| **creative_specialist** | Good patterns but no policy layer | Autonomy declaration, Policy layer, Self-verification, Escalation |
| **catalog_analyst** | Good principles but no self-check | Autonomy declaration, Policy layer, Self-verification, Confidence calibration |
| **product_analyst** | Good principles but no structure | Autonomy declaration, Policy layer, Self-verification, Escalation |
| **visual_analyst** | OK but inconsistent with others | Autonomy declaration, Policy layer, Self-verification |

**Files Changed:**
- `agents/src/autifyme_agents/prompts/specialists/catalog_specialist_lean.prompt`
- `agents/src/autifyme_agents/prompts/specialists/creative_specialist_lean.prompt`
- `agents/src/autifyme_agents/prompts/analysts/catalog_analyst.prompt`
- `agents/src/autifyme_agents/prompts/analysts/product_analyst.prompt`
- `agents/src/autifyme_agents/prompts/analysts/visual_analyst.prompt`

**Key Changes Applied to ALL Agents:**

1. **Autonomy Declaration in Identity:**
   ```xml
   **Your Autonomy:**
   - You EXPLORE first, regardless of what context PM provides
   - Analyst findings are SUPPLEMENTARY - validate through your own exploration
   - You decide HOW to accomplish the goal PM delegates
   - You are a domain MASTER, not a passive executor
   ```

2. **Policy Layer with Goals:**
   ```xml
   <policy>
   ## Your Goals (Priority Order)
   1. **ACCURACY** - ...
   2. **COMPLETENESS** - ...
   3. **STRATEGIC VALUE** - ...
   4. **EFFICIENCY** - ...
   </policy>
   ```

3. **Self-Verification Section:**
   ```xml
   <self_verification>
   ## Before [Action] - Self-Check
   - Exploration complete?
   - Quality criteria met?
   - Confidence calibration?
   </self_verification>
   ```

4. **Escalation Protocol (Specialists):**
   ```xml
   <escalation>
   ## When to Escalate to PM
   - Ambiguous requirements
   - Domain boundary crossed
   - Conflicting information
   </escalation>
   ```

5. **Explore -> Reason -> Output Framework (Catalog Specialist):**
   ```xml
   <exploration_framework>
   ## EXPLORE -> REASON -> OUTPUT (Mandatory)
   ### Step 1: EXPLORE (Always First)
   ### Step 2: REASON (Synthesize All Information)
   ### Step 3: OUTPUT (Execute with Confidence)
   </exploration_framework>
   ```

**AI Autonomy Alignment:**

| Principle | Implementation |
|-----------|----------------|
| SENSE | Each agent senses via their domain tools (view_image, read_data, research) |
| THINK: Knowledge | Tools provide knowledge access (schema, catalog, web research) |
| THINK: Policy | Explicit policy layer with prioritized goals |
| THINK: Reasoning | Self-verification before output |
| ACT | Domain-specific actions (write_data, image_studio, etc.) |
| Self-Awareness | Confidence calibration, escalation when uncertain |

**Validation:** Test with autonomous testing framework to verify exploration-first behavior.

---

### Problem 3: Agents Don't Know How to Use Tools Powerfully and Efficiently

**Vision Requirement:**
> "Tool descriptions: PURPOSE / USE WHEN / DON'T USE / RETURNS / NEEDS format. Decision guides, not feature lists. Signal overlap explicitly."

**Current Implementation:**

```python
# read_data tool, filters parameter:
filters: dict[str, Any] | None = Field(
    None,
    description=(
        "[EXACT MATCH] Equality / IN matching (no wildcards). "
        "Use when you have exact values (IDs, booleans, enums/status codes). "
        "Examples: {'is_active': True}, {'category_id': 'cat-123'}"
    )
)

# search_patterns parameter:
search_patterns: dict[str, str] | None = Field(
    None,
    description=(
        "[FUZZY MATCH] Case-insensitive ILIKE pattern matching. "
        "Use for searching text fields (names, descriptions, codes). "
        "Examples: {'name': '%search%'}"
    )
)
```

**Violations:**

**3A. Syntax Documentation, Not Decision Guidance**

- Describes WHAT parameters do (exact match, fuzzy match)
- Describes HOW to use syntax (%, ILIKE, examples)
- Does NOT describe WHEN to use each approach
- Does NOT describe WHICH scenarios fit which parameter

**3B. No "DON'T USE" Guidance**

- Doesn't say when NOT to use filters vs search_patterns
- Doesn't warn about common mistakes (e.g., using % in filters)
- Agents must infer from examples, not explicit decision logic

**3C. No Overlap Signaling**

- read_data has filters + search_patterns (complementary, not alternatives)
- But no guidance: "Use both together when..."
- No cross-tool overlap signaling (read_data vs aggregate_data vs inspect_schema)

**3D. Feature List, Not Decision Framework**

- Tool descriptions are 200-400 lines (good length)
- But structured as parameter reference, not decision tree
- Agents see: "Here's what this tool CAN do"
- Should see: "Here's WHEN to use this tool, and HOW to decide which parameters"

**Manifestation:**

- Agents use tools inefficiently (missing powerful parameters)
- Agents make mistakes (% in filters instead of search_patterns)
- Agents don't know which tool for which scenario
- Agents don't combine tools powerfully (batch reads, joins, aggregations)

**Root Cause:** Tool descriptions are API reference docs, not agent decision guides.

**Autonomy Impact:** **HIGH** - Agents have power tools but use them like manual screwdrivers.

---

## Detailed Problem Breakdown

### Problem 1: PM Orchestration - Specific Issues

| Issue | Current State | Vision Requirement | Impact |
|-------|---------------|-------------------|--------|
| **Fixed Workflow Pattern** | "Typical flow: Visual → Catalog → Research → Execute" | "NO fixed workflows - dynamic reasoning" | PM defaults to pattern instead of adapting |
| **Limited Example Coverage** | One scenario (unmarked image) | Multiple scenarios showing workflow variation | PM doesn't learn how to vary orchestration |
| **PM Does Content Analysis** | PM has `read_data`, `view_image` tools | "PM does NOT analyze content - delegates to analysts" | PM may query catalog directly instead of delegating |
| **Static Delegation Logic** | "Delegate when: [scenario list]" | "PM reasons: What context needed? Which subagents? What order?" | PM follows rules instead of reasoning |
| **No Dynamic Adaptation Examples** | Example shows single-path reasoning | "Use analyst summaries to inform next steps dynamically" | PM doesn't learn to adapt based on findings |

**Evidence from PM Prompt:**

- Line 76: "Typical flow" is a fixed workflow
- Line 44-49: PM has `inspect_schema` and `read_data` for "your orchestration decisions" - contradicts "PM does NOT analyze content"
- Line 96-142: Example shows one scenario, one workflow path
- Line 23-38: Team descriptions are "Delegate when: [scenario]" - rule-based, not reasoning-based

**What's Missing:**

- Multiple example scenarios showing DIFFERENT workflows
- Explicit reasoning: "How do I decide which subagents for THIS request?"
- Dynamic adaptation: "Analyst found X, now I reason Y leads to Z"
- Cost/benefit reasoning: "Direct to specialist vs analyst first - when each?"

---

### Problem 2: Specialist Restriction - Specific Issues

**Status:** ADDRESSED - See "Problem 2: Analysts and Specialists are Very Restricted - [FIXED]" above for details.

---

### Problem 3: Tool Usage Inefficiency - Specific Issues

| Issue | Current State | Vision Requirement | Impact |
|-------|---------------|-------------------|--------|
| **Syntax Docs, Not Decisions** | "filters: Equality matching. search_patterns: ILIKE" | "PURPOSE / USE WHEN / DON'T USE" | Agents don't know WHEN to use each |
| **No Decision Framework** | Parameter descriptions explain HOW | "Decision guides, not feature lists" | Agents see API, not decision logic |
| **Missing USE WHEN** | Examples show syntax, not scenarios | "When to use X vs Y" | Agents guess instead of decide |
| **Missing DON'T USE** | No anti-patterns or warnings | "When NOT to use this tool" | Agents make avoidable mistakes |
| **No Overlap Signaling** | Each tool described in isolation | "Signal overlap explicitly (Also consider...)" | Agents don't know tool combinations |
| **No Power User Guidance** | Basic examples only | "How to use this tool POWERFULLY" | Agents underutilize capabilities |

**Evidence from read_data Tool:**

- Line 31-41: `filters` parameter - describes WHAT (exact match), not WHEN
- Line 44-53: `search_patterns` - describes SYNTAX (%, ILIKE), not USE CASES
- Line 55-77: `relations` - syntax examples, but no "USE WHEN you need related data for X scenario"
- No "DON'T USE filters for text search - use search_patterns"
- No "Combine filters + search_patterns when you need exact category AND fuzzy name match"
- No "Consider aggregate_data instead when you need counts/sums"

**What's Missing (Per Tool):**

- **PURPOSE:** "This tool is for [primary use case]. It excels at [strength]."
- **USE WHEN:** "Use this when [scenario 1], [scenario 2], [scenario 3]"
- **DON'T USE:** "Don't use this when [anti-pattern]. Instead, use [alternative]."
- **RETURNS:** "You'll get [structure]. Use [field] for [next step]."
- **NEEDS:** "Before calling, you need [prerequisite]. Get it via [other tool]."
- **ALSO CONSIDER:** "For [related scenario], consider [other tool]."

---

## Impact on Agent Autonomy

### Autonomy Spectrum

```
LOW AUTONOMY                                  HIGH AUTONOMY
│                                                          │
│  Workflow Executor                Intelligent Reasoner  │
│  (follows templates)              (adapts dynamically)  │
│                                                          │
│  [Current PM] ─────────────────────────► [Vision PM]   │
│                                                          │
│  Passive Executor                 Explorative Expert    │
│  (waits for context)              (explores first)      │
│                                                          │
│  [Current Specialist] ──────────────► [Vision Spec]    │
│                                                          │
│  API User                         Power User            │
│  (basic syntax)                   (decision mastery)    │
│                                                          │
│  [Current Tool Usage] ──────────────► [Vision Usage]   │
```

### Current vs Vision Autonomy

| Agent/Layer | Current Autonomy | Vision Autonomy | Gap |
|-------------|------------------|-----------------|-----|
| **PM** | 4/10 - Follows "typical flow", has content analysis tools | 9/10 - Dynamic reasoning, delegates all content analysis | **CRITICAL** |
| **Specialists** | 5/10 - Depends on analyst context, exploration not emphasized | 9/10 - Autonomous exploration ALWAYS, analyst context supplementary | **CRITICAL** |
| **Tool Usage** | 6/10 - Agents know syntax, miss power features | 9/10 - Agents use tools as decision frameworks | **HIGH** |

**Combined System Autonomy:** 5/10 (Current) → 9/10 (Vision)

---

## Why These Problems Are ROOT CAUSES

**Not Surface Issues:**

- These aren't "agent makes mistakes sometimes"
- These are **architectural design flaws** in how agents are guided

**Cascade Effects:**

- Problem 1 (PM fixed workflows) → PM doesn't adapt → wrong specialists called → poor outcomes
- Problem 2 (Specialist dependency) → Specialists wait for context → slow execution → missed exploration
- Problem 3 (Tool inefficiency) → Agents underutilize tools → repetitive queries → expensive, slow workflows

**Prevent True Autonomy:**

- Agents can't reason intelligently if given templates
- Agents can't explore effectively if framed as executors
- Agents can't use tools powerfully if given syntax docs instead of decision guides

**Must Fix Before Feedback Loops:**

- Adding RLHF to current system = learning to follow templates better
- Adding RAG to current system = retrieving more fixed workflows
- Fixing autonomy FIRST → then learning amplifies good behavior

---

## Priority Ranking (Based on Autonomy Impact)

### P0: CRITICAL - Breaks Autonomous Reasoning

1. **Problem 1: PM Fixed Workflows** - [FIXED]
   - Impact: PM becomes template follower, not intelligent orchestrator
   - Blocks: Dynamic multi-domain coordination
   - Fix Effort: Medium (prompt rewrite + multiple examples)

2. **Problem 2: Specialist Dependency** - [FIXED]
   - Impact: Specialists become passive executors, not explorative experts
   - Blocks: Autonomous exploration and domain mastery
   - Fix Effort: Medium (prompt restructure + autonomy emphasis)

### P1: HIGH - Reduces Effectiveness

3. **Problem 3: Tool Usage Inefficiency** - [PENDING]
   - Impact: Agents underutilize powerful tools, make avoidable mistakes
   - Blocks: Efficient workflows, power user capabilities
   - Fix Effort: High (redesign all tool descriptions to decision guide format)

---

## Next Steps

**Progress:**

1. **Fix Problem 1 (PM Orchestration)** - [COMPLETED] Dynamic reasoning enabled
2. **Fix Problem 2 (Specialist Autonomy)** - [COMPLETED] Explorative mastery enabled
3. **Fix Problem 3 (Tool Guidance)** - [NEXT] Enable power usage

**Remaining Work:**

- **Problem 3:** Redesign tool descriptions from API reference to decision guides
  - Add PURPOSE / USE WHEN / DON'T USE / RETURNS / NEEDS format
  - Signal tool overlap explicitly
  - Include power user guidance

**Validation:**

- Test each fix with autonomous testing framework
- Verify agents demonstrate reasoning, exploration, decision-making
- Measure workflow variety (not all following same pattern)

---

## References

- **Vision:** [ARCHITECTURAL_VISION.md](./ARCHITECTURAL_VISION.md) - Autonomy principles
- **Current Implementation:** Codebase exploration (6 parallel agents)
- **Autonomy Framework:** [AI_AGENT_ANATOMY.md](./core/AI_AGENT_ANATOMY.md) - Think layer (reasoning)
