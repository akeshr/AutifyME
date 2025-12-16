# AutifyME Architectural Vision

**Date:** 2025-12-11
**Status:** REFINED - Sections 1 & 2 Complete
**Purpose:** North star for agent redesign and future development

**Note:** This vision has been refined through detailed discussion sessions. See [VISION_REFINEMENT_SESSION.md](./VISION_REFINEMENT_SESSION.md) for complete decision rationale and concrete examples.

---

## The Vision: Multi-Domain Autonomous Business Operating System

**AutifyME is not a cataloging system. It is a multi-domain autonomous business operating system.**

The system spans multiple operational domains:

- **Catalog Domain:** Product information management, inventory, pricing, manufacturing data
- **Creative Domain:** Image processing, visual asset generation, brand consistency
- **Operations Domain:** Quality control, damage detection, compliance checking, fulfillment workflows
- **Marketing Domain:** Campaign assets, product positioning, competitive analysis, content generation
- **Procurement Domain:** Supplier coordination, sourcing intelligence, cost analysis
- **Quality Domain:** Defect identification, standards compliance, testing protocols
- **Future Domains:** Customer service, analytics, forecasting, etc.

**Each domain has deep expertise. Each domain performs with utmost quality. Each domain explores possibilities autonomously.**

---

## PM Role: Dynamic Intelligent Orchestrator

The PM is NOT a simple router. The PM is an **intelligent multi-domain orchestrator** that reasons dynamically about workflow coordination.

### PM Responsibilities

1. **Analyze User Intent (NOT Content)**
   - Recognize high-level intent across domains (cataloging, creative, analysis)
   - Identify which domains are involved and cross-domain dependencies
   - Recognize multi-domain workflows vs single-domain tasks
   - **Does NOT analyze actual content** (no image analysis, product research, catalog queries)

2. **Dynamic Reasoning (NO Fixed Workflows)**
   - Reason about: What context is needed? Which subagents? What order?
   - Use analyst summaries to inform next steps dynamically
   - Adapt orchestration based on task complexity and findings
   - **No templates, no rigid workflows** - every request gets customized coordination

3. **Delegate with Context (NOT Instructions)**
   - Pass relevant context extraction (intent + media paths + entity references + workspace location)
   - Delegate with simple 1-2 liner descriptions
   - Provide paths to prior subagent findings for context handoffs
   - **Does NOT tell subagents what to do** - passes context, not directives

4. **Synthesize Multi-Domain Outputs**
   - Read all subagent outputs from filesystem
   - Synthesize coherent narrative connecting multi-domain findings
   - Present actionable summary with paths to detailed reports
   - **Does NOT re-analyze** - trusts subagent expertise

5. **Strategic Coordination**
   - Decide dynamically when to use analysts vs direct to specialists
   - Orchestrate sequentially when dependencies exist, parallel when independent
   - Maintain workflow state across domain boundaries
   - Escalate to user when ambiguity cannot be resolved autonomously

### PM is NOT

- A passive message router
- A content analyzer (doesn't view images, research products, or query catalog)
- A domain expert itself (doesn't perform deep domain work)
- A micromanager (doesn't dictate how domain experts execute)
- A template follower (no fixed workflows)

---

## Analyst Role: Context Enrichment Layer

Analysts are **read-only exploration agents** that serve as PM's intelligence layer for detailed analysis. They provide triple value: context enrichment, execution separation, and cost optimization.

### Analyst Characteristics

1. **Read-Only Exploration**
   - Tools: view_image, read_data, research_product_tool, aggregate_data, extract_web_content_tool
   - **No execution capability** (no write_data, no create/update/delete)
   - Pure analysis without execution pressure or bias

2. **Context Enrichment for PM**
   - PM does NOT analyze content himself - delegates to analysts
   - Analysts explore comprehensively and return findings to PM
   - PM uses analyst summaries to reason about next steps dynamically
   - Enables PM's dynamic orchestration without content analysis

3. **Cost Optimization**
   - Use cheap models (Gemini 2.5 Flash ~$0.01/1K tokens for visual_analyst)
   - Bulk exploration before expensive specialist execution (Sonnet ~$3/1K tokens)
   - Significant savings when exploration >> execution

4. **Filesystem Communication Protocol**
   - Write detailed findings to workspace/thread_123/[domain]_[type].md
   - Return informative summary + file path to PM
   - PM uses summary for reasoning, specialists read full findings
   - Complete audit trail of analysis and decisions

### Analyst Types

- **visual_analyst**: Gemini 2.5 Flash, view_image, pure visual observation
- **product_analyst**: research_product_tool, market research, external intelligence
- **catalog_analyst**: read_data, aggregate_data, strategic catalog analysis

---

## Subagent Role: Explorative Domain Expert

Subagents are **NOT workflow executors following rigid recipes.** They are **autonomous domain masters** who explore possibilities, iterate for quality, and deliver portfolio-worthy outputs.

### Subagent Types

**Analysts (Read-Only):**
- visual_analyst, product_analyst, catalog_analyst
- Explore and analyze without execution
- Return findings to PM for orchestration

**Specialists (Execution):**
- catalog_specialist, creative_specialist
- Full toolset including write_data with HITL approval
- Explore AND execute with portfolio-worthy quality

### Specialist Characteristics

1. **Deep Domain Mastery**
   - Each specialist owns a domain with full tool access for that domain
   - Thinks in domain-specific vocabulary and patterns (e.g., "SKU architecture" for catalog, "light and composition" for creative)
   - Applies world-class judgment within domain boundaries
   - Knows industry standards, best practices, and quality thresholds for their domain

2. **Explorative Problem-Solving** (Explore → Reason → Output) **ALWAYS**
   - **FIRST: Explore comprehensively** - inspect schema, query data, research context, view images, validate prerequisites across ALL relevant areas
   - **THEN: Reason deeply** - synthesize analyst findings (if provided), apply own domain expertise, identify gaps, evaluate options
   - **FINALLY: Output intelligently** - execute with complete validated information, verify outputs, write to filesystem
   - **Autonomous regardless of analyst context** - analyst findings are supplementary, not directive
   - Specialists ALWAYS explore to validate current state and apply domain expertise

3. **Quality-First Execution**
   - Every output is portfolio-worthy, immediately publishable
   - Self-verification before returning results (e.g., view_image after image_studio, read_data to check duplicates)
   - Bounded iteration with clear quality thresholds and escalation protocols
   - Fills every relevant field, uses all available context, maximizes catalog/asset quality

4. **Intelligent Communication**
   - Returns domain intelligence shaped by explorative discovery (not rigid schemas)
   - Write detailed results to workspace/thread_123/[domain]_results.md
   - Return informative summary + file path to PM
   - Flags gaps, uncertainties, and recommendations clearly
   - Escalates to PM when hitting domain boundaries or unresolvable blockers

### Subagents are NOT

- Passive executors waiting for PM to provide everything
- Limited to narrow, scripted workflows
- Allowed to skip exploration when given analyst context
- Allowed to produce mediocre outputs ("good enough" is not acceptable)

---

## Communication Protocol

The system uses a consistent communication pattern across all PM-subagent interactions:

### Standard Interaction Flow

```
1. PM → Subagent: Simple 1-2 liner delegation
   Example: "Do detailed visual analysis, write findings to workspace, return summary + file path"

2. Subagent → Explores: Uses all relevant tools comprehensively
   - Analysts: view_image, read_data, research_product_tool, aggregate_data
   - Specialists: All analyst tools PLUS inspect_schema, write_data (with HITL)

3. Subagent → Filesystem: Writes detailed findings
   - workspace/thread_123/visual_analysis.md
   - workspace/thread_123/product_research.md
   - workspace/thread_123/catalog_results.md
   - Complete analysis with all context for traceability

4. Subagent → PM: Returns concise package
   - Informative summary (key insights for PM's next decision)
   - File path (for specialist access and user traceability)

5. PM → Reasons: Uses summary to decide next step dynamically
   - What did I learn? What's still needed?
   - Which subagent next? What context should I provide?

6. PM → User: Synthesizes all outputs
   - Reads all subagent outputs from filesystem
   - Creates coherent narrative connecting findings
   - Provides actionable summary + paths to detailed reports
```

### Key Protocol Characteristics

- **Lightweight delegation**: PM provides context, not instructions (1-2 liner)
- **Rich exploration**: Subagents use full tool access autonomously
- **Persistent findings**: Filesystem as source of truth for full workflow lifecycle
- **Concise coordination**: Summaries enable PM reasoning without reading full documents
- **Traceable decisions**: Complete audit trail via filesystem outputs
- **Dynamic orchestration**: PM reasons about next step based on findings, not templates

### File Naming Convention

```
workspace/thread_123/
├── visual_analysis.md      # visual_analyst output
├── catalog_analysis.md     # catalog_analyst output
├── product_research.md     # product_analyst output
├── creative_output.md      # creative_specialist output
└── catalog_results.md      # catalog_specialist output
```

---

## Architectural Decisions

### Decision 1: PM Intelligence Level → Dynamic Intelligent Orchestrator

**PM analyzes intent + domain dependencies, but does NOT analyze content.**

PM is an intelligent coordinator that:
- Recognizes high-level intent and identifies involved domains
- Reasons dynamically about optimal subagent sequencing (NO fixed workflows)
- Delegates to analysts for detailed content analysis (visual, product, catalog)
- Uses analyst summaries to inform next steps dynamically
- Synthesizes all subagent outputs into coherent user-facing narrative

**What PM Does:**
- ✅ Recognizes "this needs catalog + creative domains"
- ✅ Identifies "creative depends on catalog context first"
- ✅ Reasons: "What context needed? Which subagents? What order?"
- ✅ Uses analyst summaries to decide next step

**What PM Does NOT Do:**
- ❌ Analyze image content, research products, or query catalog state
- ❌ Follow fixed workflow templates
- ❌ Tell subagents what to do (passes context, not instructions)

---

### Decision 2: Analyst Role → Triple Purpose (Context Enrichment + Read-Only + Cost Optimization)

**Analysts are PM's intelligence layer for detailed content analysis.**

Analysts serve three complementary purposes:
1. **Context Enrichment**: PM delegates detailed analysis to analysts, who explore and return findings
2. **Read-Only Separation**: Analysts NEVER execute (no write_data), creating clean exploration vs execution boundary
3. **Cost Optimization**: Use cheap models (Gemini Flash) for bulk exploration before expensive specialist execution (Sonnet)

**Dynamic Usage Pattern:**
- PM decides dynamically when to use analysts vs direct to specialists
- Exploration-heavy tasks → use analysts for cheap context gathering
- Simple execution tasks → go direct to specialists
- PM reasons about cost/benefit, not fixed workflows

**Communication Protocol:**
- Analysts write detailed findings to filesystem (workspace/thread_123/*.md)
- Return informative summary + file path to PM
- PM uses summary for reasoning, specialists read full findings

---

### Decision 3: Specialist Autonomy → Autonomous Regardless (Explore → Reason → Output ALWAYS)

**Specialists ALWAYS explore comprehensively, regardless of analyst context provided.**

Specialists are fully autonomous domain experts:
- Always follow Explore → Reason → Output pattern
- Validate analyst findings through own exploration
- Apply domain expertise that analysts lack
- Verify current state before execution (data/schema may have changed)
- **Analyst context is supplementary, not directive**

**Why Specialists Don't Just Trust Analyst Context:**
- Domain expertise: Specialists have deep knowledge analysts lack
- Execution responsibility: Must validate before write operations
- Context staleness: State may have changed between analyst and specialist execution
- Different tools: Specialists have execution capabilities analysts don't

**Escalation Protocol:**
- Escalate to PM when hitting domain boundaries
- Escalate when multiple iterations don't meet quality threshold
- Escalate when ambiguous requirements require business judgment
- Escalate when tool failures or missing prerequisites block progress

---

### Decision 4: Multi-Domain Coordination → Dynamic Sequential Orchestration

**PM orchestrates sequentially when dependencies exist, parallel when independent.**

PM determines optimal execution pattern based on task analysis:
- **Sequential** when dependencies exist (Domain B needs Domain A's output)
- **Parallel** when domains work independently (no dependencies)
- **Dynamically chained** based on intermediate results (PM reasons after each step)

**PM's Dynamic Coordination:**
- PM recognizes cross-domain dependencies from intent analysis
- PM sequences subagents based on dependencies
- PM uses filesystem for domain-to-domain context handoffs
- PM maintains workflow state and synthesizes final outputs

**NOT** parallel-first (risk: duplication/conflicts) or sequential-pipeline (risk: inefficiency).

---

## Core Design Principles

### P1: Intelligence-First Design

- Trust LLM reasoning over rigid control
- Give agents problems + context, not step-by-step recipes
- Rich context enables autonomy
- Design for reasoning, not automation

### P2: Clear Boundaries Through Purpose

- Each agent/tool answers: "What problem do I solve?"
- Overlap is acceptable when domains naturally intersect
- Boundaries = domain coherence, not artificial separation

### P3: Explorative Over Prescriptive

- Agents explore first (schema, data, context, images, prerequisites)
- Then reason (analyze, synthesize, evaluate, decide)
- Then output (findings shaped by discovery, not templates)
- No rigid Pydantic schemas enforcing output structure

### P4: Context Flow Is Explicit

- What context does PM pass to domain experts?
- What context do tools need to succeed?
- What context do tools return that agents can use?
- Prevent duplicate work through intelligent context passing

### P5: Verification Over Hope

- Agents verify before acting (duplicates, schema, prerequisites)
- Specialists verify outputs (view_image after image_studio)
- Multi-step validation gates prevent cascading failures

### P6: Fail-Fast with Actionable Errors

- Tools validate inputs and return structured errors
- Error messages guide agents to correct action
- Agents can recover without PM intervention

### P7: Prompt-Based Guidance, Not Code Enforcement

- Guide behavior through rich, well-structured prompts
- Avoid over-engineering and rigid scaffolding
- Let agents reason about goals and adapt dynamically
- Use filesystem tool for larger outputs (DeepAgents default)

---

## Design Philosophy

**From the user (life-critical stakes):**

> "I want the PM to orchestrate intelligently and I want the subagents to be explorative and know their domain and perform with utmost quality based on what is required."

**Key Insights:**

- Modern LLMs are highly capable (200K+ context, strong reasoning, autonomous problem-solving)
- Intelligence-first design means trusting agents to explore and decide
- Minimal scaffolding beats rigid orchestration
- Context enables autonomy better than step-by-step control
- Design for reasoning agents, not automated workflows

**Zero Tolerance:**

- Architectural compromise for shortcuts
- "Good enough" quality from domain experts
- Passive execution without exploration
- Rigid schemas limiting explorative discovery

---

## Success Criteria

**PM Success:**
- Correctly analyzes multi-domain user intents
- Routes to appropriate domains with complete context
- Synthesizes coherent results from multiple domain experts
- Handles complex workflows without user micromanagement

**Subagent Success:**
- Explores comprehensively before executing
- Delivers portfolio-worthy, immediately publishable outputs
- Escalates intelligently when hitting limits
- Uses all available context and tools autonomously

**System Success:**
- No repeated behavioral anti-patterns from prior iterations
- Clean separation of concerns (PM orchestrates, domains execute)
- Efficient multi-domain coordination (no duplication, context loss)
- Quality outputs that reflect deep domain expertise

---

## What This Means for Redesign

**Tool Descriptions:**
- PURPOSE / USE WHEN / DON'T USE / RETURNS / NEEDS format
- Decision guides, not feature lists
- Signal overlap explicitly ("Also consider X if...")

**Specialist Descriptions:**
- Domain ownership statement
- "DELEGATE WHEN:" with concrete scenarios
- "DOES NOT:" to clarify boundaries
- "REQUIRES:" for prerequisites

**Agent Prompts:**
- Identity: domain expert voice (photographer, architect, analyst)
- Capabilities: tool inventory with when/why
- Principles: decision-making heuristics (Explore → Reason → Output)
- Examples: canonical scenarios showing reasoning process

**NO MORE:**
- Pydantic model enforcement for explorative outputs
- Conflicting autonomy vs dependency signals
- Vague "enriched context" without specification
- Unbounded iteration or verification without escalation protocols
- PM doing specialist work or specialists being passive

---

## References

- **Vision Refinement Sessions:** [VISION_REFINEMENT_SESSION.md](./VISION_REFINEMENT_SESSION.md) - Complete decision rationale with concrete examples
- **Diagnostic Analysis:** [AGENT_TOOL_REDESIGN.md](./AGENT_TOOL_REDESIGN.md) - Root cause analysis of behavioral issues
- **Domain Design Guidelines:** [DOMAIN_DESIGN_GUIDELINES.md](./core/DOMAIN_DESIGN_GUIDELINES.md)
- **Project Instructions:** [CLAUDE.md](../../CLAUDE.md)
