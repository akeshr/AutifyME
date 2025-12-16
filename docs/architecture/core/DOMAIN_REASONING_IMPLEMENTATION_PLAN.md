# Domain Reasoning Protocols - Implementation Plan

**Created:** December 16, 2025
**Status:** ACTIVE - Phase 1 Ready to Start
**Framework:** [DOMAIN_REASONING_PROTOCOLS.md](./DOMAIN_REASONING_PROTOCOLS.md)
**Purpose:** Staged implementation plan with progress tracking and decision log

---

## Executive Summary

Transform agents from "pattern-copying generalists" to "structured domain reasoners grounded in real data" through Domain-Specific Reasoning Protocols.

**Core Mechanism:** Protocols force TOOL CALLS that ground reasoning in real data - agents can't fake query results.

**Delivery Mechanism:** `load_protocol` tool + `ProtocolInjectionMiddleware` (wrap_model_call):

1. Agent calls `load_protocol(["family_fit", "pricing"])` - accepts list for batch loading
2. Tool returns protocol CONTENT directly (identified by tool name, no markers)
3. Middleware's `wrap_model_call` scans ToolMessages where `msg.name == 'load_protocol'`
4. Middleware deduplicates by protocol name, injects into system prompt via `request.override()`
5. Agent sees protocol as INSTRUCTIONS (semantically correct placement)

**Key Design Decisions (REPL Verified):**

- **Message-history based:** Config doesn't persist across tool calls; ToolMessages do
- **Tool name identification:** No markers - middleware checks `msg.name == 'load_protocol'`
- **Batch loading:** Single tool call for multiple protocols prevents parallel call issues
- **Deduplication:** Middleware tracks protocol names, injects each only once
- **Unified mechanism:** All agents (PM, specialists, analysts) use same pattern
- **Agent autonomy:** Agent decides what protocols to load based on protocol index
- **Automatic lifecycle:** Fresh messages per SubAgent = isolation; new conversation = fresh start
- **Token efficiency:** Lean base prompts (~1,500 tokens) + dynamic loading

---

## Implementation Phases Overview

| Phase | Focus | Duration | Key Deliverables |
|-------|-------|----------|------------------|
| **Phase 1** | Foundation (Catalog) | 1 week | Protocol structure, loader, business context |
| **Phase 2** | Protocol Execution | 1 week | Core protocols, confidence scoring, HITL |
| **Phase 3** | Token Optimization | 3-4 days | Tiered protocols, PM selection, budgets |
| **Phase 4** | Multi-Domain | 2 weeks | Marketing, Operations, generic patterns |

---

## Current Architecture Analysis

### What We Have (DeepAgents + LangChain v1)

```python
# PM Creation (project_manager.py)
create_deep_agent(
    tools=pm_tools,
    system_prompt=instructions,              # Static prompt
    model=llm,
    subagents=subagents,                     # SubAgent dicts
    middleware=pm_middleware,                 # ContextEditingMiddleware
    response_format=ToolStrategy(PMOutput),   # Structured output
    interrupt_on={},
    checkpointer=checkpointer,               # State persistence
    store=store,                             # LangGraph store
    context_schema=CompanyContext,           # Stateful context
)

# Specialist Creation (catalog_specialist.py)
spec = {
    "name": "catalog_specialist",
    "description": description,
    "tools": tools,
    "system_prompt": system_prompt,          # Static prompt from file
    "middleware": [MultimodalInjectionMiddleware()],
    "interrupt_on": {"write_data": True},
}
```

### Capabilities to Leverage

| Capability | Current Use | Protocol Use |
|------------|-------------|--------------|
| `AgentMiddleware.wrap_model_call` | Model interception | Scan ToolMessages, inject protocols via `request.override()` |
| `ModelRequest.state["messages"]` | Message history | Source for finding load_protocol ToolMessages |
| `ToolMessage.name` | Tool identification | Check `msg.name == 'load_protocol'` (no markers) |
| `request.override(system_message=...)` | Immutable update | Inject protocol content into system prompt |
| `@tool` decorator | Domain tools | `load_protocol` tool accepting list of names |
| `ToolStrategy` | PMOutput schema | Confidence-enhanced output |
| SubAgent statelessness | Fresh per invocation | Natural protocol lifecycle cleanup |

---

## Phase 1: Foundation (Catalog Domain)

**Goal:** Establish protocol infrastructure and embed business context.

### 1.1 Protocol File Structure

```text
agents/src/autifyme_agents/
├── prompts/
│   ├── protocols/                         # NEW: Protocol files (per-agent)
│   │   ├── pm/                            # PM orchestration protocols
│   │   │   ├── intent_understanding.protocol
│   │   │   ├── domain_discovery.protocol
│   │   │   ├── multi_domain_planning.protocol
│   │   │   └── batch_processing.protocol
│   │   ├── catalog_specialist/            # Catalog domain decisions
│   │   │   ├── business_context.protocol
│   │   │   ├── family_fit.protocol
│   │   │   ├── pricing.protocol
│   │   │   ├── duplicate_prevention.protocol
│   │   │   ├── cold_start.protocol
│   │   │   └── new_entity.protocol
│   │   ├── catalog_analyst/               # Catalog exploration
│   │   │   ├── catalog_exploration.protocol
│   │   │   └── family_analysis.protocol
│   │   └── shared/                        # Cross-agent protocols
│   │       ├── tool_mastery/
│   │       │   ├── read_data.protocol
│   │       │   ├── write_data.protocol
│   │       │   └── aggregate_data.protocol
│   │       └── generic_patterns/
│   │           ├── fit_assessment.protocol
│   │           └── value_discovery.protocol
│   ├── specialists/
│   │   └── catalog_specialist_lean.prompt  # Updated with protocol index
│   └── project_manager.prompt              # Updated with protocol index
├── tools/
│   └── protocol_tools.py              # NEW: load_protocol tool factory
└── middleware/
    └── protocol_injection.py          # NEW: ProtocolInjectionMiddleware
```

**Resolution Order:** Agent-specific (`protocols/{agent_type}/`) first, then shared (`protocols/shared/`).

**Status:** [ ] Not Started

### 1.2 Protocol Loading Tool Implementation

```python
# agents/src/autifyme_agents/tools/protocol_tools.py

from functools import lru_cache
from pathlib import Path
from langchain_core.tools import tool

PROTOCOL_BASE_PATH = Path(__file__).parent.parent / "prompts" / "protocols"


@lru_cache(maxsize=64)
def _load_protocol_content(agent_type: str, name: str) -> str:
    """Load protocol content from filesystem with caching.

    Resolution order:
    1. Agent-specific: protocols/{agent_type}/{name}.protocol
    2. Shared: protocols/shared/{name}.protocol
    """
    agent_path = PROTOCOL_BASE_PATH / agent_type / f"{name}.protocol"
    if agent_path.exists():
        return agent_path.read_text(encoding="utf-8")

    shared_path = PROTOCOL_BASE_PATH / "shared" / f"{name}.protocol"
    if shared_path.exists():
        return shared_path.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Protocol '{name}' not found for {agent_type}")


def create_load_protocol_tool(agent_type: str):
    """Create load_protocol tool configured for specific agent type.

    The tool returns protocol CONTENT directly. Middleware identifies it by
    checking ToolMessage.name == 'load_protocol' (no markers needed).

    Args:
        agent_type: Agent identifier (pm, catalog_specialist, etc.)

    Returns:
        Configured load_protocol tool
    """

    @tool
    def load_protocol(names: list[str]) -> str:
        """Load one or more reasoning protocols to guide your next steps.

        Call this when you need structured guidance for domain decisions.
        Protocols will be injected into your instructions by middleware.

        IMPORTANT: Load all needed protocols in ONE call to avoid parallel execution issues.

        Args:
            names: List of protocol names (e.g., ['family_fit', 'pricing'])

        Returns:
            Protocol content formatted for middleware injection.
        """
        results = []
        errors = []

        for name in names:
            try:
                content = _load_protocol_content(agent_type, name)
                results.append(f"## Protocol: {name}\n{content}")
            except FileNotFoundError as e:
                errors.append(f"Error: {e}")

        if errors and not results:
            return "\n".join(errors)

        output = "\n\n".join(results)
        if errors:
            output += "\n\n" + "\n".join(errors)

        return output

    return load_protocol
```

**Key Design:**

- **List input:** Single call loads multiple protocols - prevents parallel tool call issues
- **Direct content return:** Tool returns formatted protocol content (no markers)
- **Tool name identification:** Middleware checks `msg.name == 'load_protocol'`

**Status:** [ ] Not Started

### 1.3 Business Context Protocol (Catalog)

Create: `agents/src/autifyme_agents/prompts/protocols/catalog/business_context.protocol`

```xml
<business_context domain="catalog">

## Positioning Tiers

### UTILITY (Budget: Rs 0-50)
- Customer: Price-conscious, functional buyers
- Products: Plain, bulk, everyday use
- Signal: "Affordable, practical"

### DECORATIVE (Mid: Rs 50-150)
- Customer: Gift buyers, aesthetics-conscious
- Products: Designed, gift-worthy, display items
- Signal: "Worth presenting, thoughtful"

### PREMIUM (Rs 150+)
- Customer: Luxury seekers, statement makers
- Products: Artisan, unique, high-quality
- Signal: "Special, exclusive"

## Key Relationships

- product_families --> customer_segments (who buys from this family)
- products --> product_families (which family product belongs to)
- customer_segments DETERMINES family fit (not material, not price)

## Common Misconceptions

- NOT: Same material = same family
- ACTUALLY: Same customer journey = same family
- NOT: Price determines positioning
- ACTUALLY: Positioning determines price range

## Critical Domain Rules

1. **Customer Segment is Primary:** Family assignment is about WHO BUYS, not what it's made of
2. **Price Follows Positioning:** Don't set price first, then find family. Find family, then price within range.
3. **Explore Before Concluding:** Always query the database - don't use general retail knowledge

</business_context>
```

**Status:** [ ] Not Started

### 1.4 Update Specialist Prompt Structure

Modify `catalog_specialist_lean.prompt` to include protocol index (lean prompt, dynamic loading):

```xml
<identity>
... existing identity (unchanged) ...
</identity>

<tools>
... existing tools ...

## load_protocol
Load a reasoning protocol when you need structured guidance.
Protocols appear in your instructions after loading.
</tools>

<protocol_index>
When you need structured guidance, use load_protocol:

| Situation | Protocol |
|-----------|----------|
| Which family does product belong to? | family_fit |
| What should this product cost? | pricing |
| Does this product already exist? | duplicate_prevention |
| Understanding the catalog landscape | business_context |
| No existing family matches | new_entity |
| Cold start (empty/sparse catalog) | cold_start |

For familiar tasks with clear paths, proceed without loading protocols.
</protocol_index>

<protocol_usage>
When protocols are loaded (appear in <active_protocols>):

1. Execute ALL steps in order - do not skip
2. Document results of each step with evidence
3. Reach conclusion based on step results
4. If uncertain, escalate with evidence gathered

**Protocols provide:** WHAT to investigate, WHICH queries to run
**Your intelligence provides:** HOW to interpret results, WHEN to escalate
</protocol_usage>

<!-- DYNAMIC: Protocols injected here by middleware after load_protocol calls -->

... rest of existing prompt ...
```

**Status:** [ ] Not Started

### 1.5 Protocol Injection Middleware

```python
# agents/src/autifyme_agents/middleware/protocol_injection.py

from typing import Callable
from deepagents.graph import AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import SystemMessage, ToolMessage


class ProtocolInjectionMiddleware(AgentMiddleware):
    """Injects loaded protocols into system prompt before LLM call.

    Uses wrap_model_call to:
    1. Scan state.messages for ToolMessages where name == 'load_protocol'
    2. Deduplicate protocols by name (prevents duplicate injection)
    3. Inject protocol content into system prompt via request.override()

    Lifecycle:
    - SubAgents: Fresh messages per invocation = automatic isolation
    - PM: New conversation = fresh messages = automatic cleanup
    - No explicit unload needed
    """

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Scan for load_protocol results, deduplicate, inject into system prompt."""
        # Collect protocols, deduplicate by name
        seen_protocols: dict[str, str] = {}  # name -> formatted content

        for msg in request.state.get("messages", []):
            if not isinstance(msg, ToolMessage):
                continue
            if msg.name != "load_protocol":
                continue
            if str(msg.content).startswith("Error:"):
                continue

            # Parse protocol sections from tool output
            # Format: "## Protocol: name\n<content>\n\n## Protocol: name2\n<content>"
            content = str(msg.content)
            for section in content.split("## Protocol: ")[1:]:
                lines = section.split("\n", 1)
                name = lines[0].strip()
                body = lines[1] if len(lines) > 1 else ""
                # Deduplicate - first occurrence wins
                if name not in seen_protocols:
                    seen_protocols[name] = f"## Protocol: {name}\n{body}"

        # Inject if we found protocols
        if seen_protocols:
            protocol_section = (
                "<active_protocols>\n"
                + "\n\n".join(seen_protocols.values())
                + "\n</active_protocols>"
            )
            current_prompt = request.system_prompt or ""
            new_prompt = current_prompt + "\n\n" + protocol_section

            # Use immutable override pattern
            request = request.override(
                system_message=SystemMessage(content=new_prompt)
            )

        return handler(request)
```

**Key Design:**

- **wrap_model_call:** Correct LangChain v1 hook with access to both state and system_message
- **Tool name check:** `msg.name == 'load_protocol'` - no marker parsing
- **Deduplication:** `seen_protocols` dict prevents same protocol injected multiple times
- **Immutable update:** `request.override()` follows LangChain best practices

**Status:** [ ] Not Started

### 1.6 Phase 1 Deliverables Checklist

- [ ] Protocol file structure created (per-agent directories)
- [ ] `create_load_protocol_tool()` implemented in `tools/protocol_tools.py`
- [ ] `ProtocolInjectionMiddleware` implemented in `middleware/protocol_injection.py`
- [ ] Business context protocol for Catalog
- [ ] Tool mastery protocols (read_data, aggregate_data, write_data)
- [ ] Specialist prompt updated with protocol index (lean prompt)
- [ ] Integration: Add load_protocol tool + middleware to catalog_specialist
- [ ] Integration test: Load protocol -> middleware injection -> system prompt

---

## Phase 2: Protocol Execution (Catalog Domain)

**Goal:** Implement core decision protocols with confidence scoring.

### 2.1 Core Protocols to Implement

| Protocol | File | Priority |
|----------|------|----------|
| Duplicate Prevention | `generic/duplicate_prevention.protocol` | P0 |
| Family Fit | `catalog/family_fit.protocol` | P0 |
| Pricing (Value Discovery) | `catalog/pricing.protocol` | P0 |
| Domain Orientation | `generic/domain_orientation.protocol` | P1 |
| New Entity | `generic/new_entity.protocol` | P1 |
| Cold Start | `catalog/cold_start.protocol` | P2 |

**Status:** [ ] Not Started

### 2.2 Family Fit Protocol Implementation

Create: `agents/src/autifyme_agents/prompts/protocols/catalog/family_fit.protocol`

```xml
<protocol name="Family Fit Protocol" domain="catalog" type="decision">

## PURPOSE
Determine if a product belongs in a candidate family.

## WHEN TO USE
- Adding new product to catalog
- Evaluating family placement during update
- Verifying analyst's family suggestion

## STEPS

### Step 1: IDENTIFY - Candidate Family
Identify the family being evaluated for fit.
Document: family_id, family_name

**Result:**
Candidate family: [id, name]

### Step 2: QUERY - Customer Segment
**Execute:**
read_data(
  table="customer_segments",
  filters={"family_id": [candidate_family_id]}
)

**Why This Matters:**
customer_segments is THE deciding factor for family fit.
NOT material. NOT price. WHO BUYS determines family.

**How to Interpret:**
The description tells you the buyer persona.
"Households organizing kitchen pantry" = utility buyers
"Gift buyers, home decor enthusiasts" = decorative buyers

**Result:**
Customer segment for this family.

### Step 3: QUERY - Family's Current Products
**Execute:**
read_data(
  table="products",
  filters={"family_id": [candidate_family_id]},
  columns=["name", "price", "positioning"],
  limit=10
)

**Understand:**
What products currently belong? What's their style, price range?

**Result:**
Sample products with their attributes.

### Step 4: ANALYZE - Product's Target Customer
Based on product attributes (visual style, materials, price point):
- Is this for utility/everyday use?
- Is this for decorative/display purposes?
- Is this for gifting?
- Is this for premium/luxury buyers?

**Result:**
Target customer profile for THIS product.

### Step 5: COMPARE - Customer Match
Compare Step 2 (family's customer) with Step 4 (product's customer):
- MATCH: Same customer type (90%+ alignment)
- PARTIAL: Overlapping but distinct (60-89% alignment)
- MISMATCH: Different customer type (<60% alignment)

**Result:**
Match assessment with evidence and percentage.

### Step 6: COMPARE - Product Cohesion
Compare Step 3 (family's products) with this product:
- Would a customer browsing the family naturally consider this?
- Does style/positioning align?
- Does price range align?

**Result:**
Cohesion assessment.

### Step 7: CONCLUDE with Confidence
**Based on Steps 5 and 6:**
- MATCH + Cohesive: Product FITS this family (HIGH confidence)
- MATCH + Not Cohesive: Product FITS but consider sub-family (MEDIUM confidence)
- PARTIAL: Consider alternatives, present options (MEDIUM confidence)
- MISMATCH: Product needs DIFFERENT family (HIGH confidence of mismatch)

**Output Format:**
```
CONCLUSION: [FIT/PARTIAL/NO_FIT]
CONFIDENCE: [HIGH/MEDIUM/LOW]
EVIDENCE:
- Customer match: [% and reasoning]
- Product cohesion: [assessment]
RECOMMENDATION: [specific action]
```

## VERIFICATION
- [ ] Step 2 query executed (not assumed)
- [ ] Step 3 query executed
- [ ] Customer comparison based on evidence
- [ ] Conclusion references step results

## ANTI-PATTERNS
- Concluding based on material match alone
- Skipping customer segment query
- Using general retail knowledge instead of queried data

</protocol>
```

**Status:** [ ] Not Started

### 2.3 Confidence-Enhanced Output Schema

```python
# agents/src/autifyme_agents/schemas/protocol_output.py

from typing import Literal
from pydantic import BaseModel, Field

class ProtocolStepResult(BaseModel):
    """Result from a single protocol step."""
    step_name: str
    step_number: int
    query_executed: str | None = None
    result_summary: str
    confidence_contribution: Literal["HIGH", "MEDIUM", "LOW"]

class ProtocolConclusion(BaseModel):
    """Conclusion from protocol execution."""
    protocol_name: str
    conclusion: str  # FIT, PARTIAL, NO_FIT, MATCH, MISMATCH, etc.
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    confidence_score: int = Field(ge=0, le=100, description="0-100 score")
    evidence: list[str]
    recommendation: str
    steps_executed: list[ProtocolStepResult]

class CatalogSpecialistOutput(BaseModel):
    """Enhanced output with protocol execution tracking."""
    task_type: Literal["ACTION", "ANALYSIS"]
    protocols_executed: list[ProtocolConclusion]
    overall_confidence: Literal["HIGH", "MEDIUM", "LOW"]
    hitl_required: bool
    hitl_reason: str | None = None

    # For ACTION tasks
    write_intent: dict | None = None

    # For ANALYSIS tasks
    findings: str | None = None
    recommendations: list[str] | None = None
```

**Status:** [ ] Not Started

### 2.4 HITL Integration with Confidence

Update `interrupt_on` logic to trigger on LOW confidence:

```python
# In specialist creation
spec = {
    ...
    "interrupt_on": {
        "write_data": True,  # Always for writes
        # Add dynamic interrupts via middleware
    },
    "middleware": [
        ProtocolInjectionMiddleware(domain="catalog"),
        ConfidenceBasedHITLMiddleware(
            low_confidence_interrupt=True,
            medium_confidence_flag=True,
        ),
        MultimodalInjectionMiddleware(),
    ],
}
```

**Status:** [ ] Not Started

### 2.5 Phase 2 Deliverables Checklist

- [ ] Duplicate Prevention protocol
- [ ] Family Fit protocol
- [ ] Pricing protocol
- [ ] Domain Orientation protocol
- [ ] New Entity protocol
- [ ] Cold Start protocol
- [ ] `ProtocolConclusion` schema
- [ ] `CatalogSpecialistOutput` schema
- [ ] Confidence-based HITL middleware
- [ ] Integration test: Full protocol chain execution

---

## Phase 3: Token Optimization

**Goal:** Reduce token usage through intelligent protocol selection and tiered depth.

### 3.1 PM Protocol Selection

Update PM prompt with protocol index:

```xml
<protocol_selection>

## Protocol Selection for Specialist Tasks

Before delegating to Catalog Specialist, select appropriate protocols:

| Task Pattern | Protocols to Include | Token Budget |
|--------------|---------------------|--------------|
| New product, unknown family | duplicate_prevention, family_fit, pricing | ~1,500 |
| New product, family specified | duplicate_prevention, pricing | ~800 |
| Price recommendation only | pricing | ~400 |
| Family assignment only | family_fit | ~500 |
| First product (cold start) | cold_start | ~600 |
| Product update | duplicate_prevention | ~300 |
| Catalog audit | domain_orientation | ~400 |

**Include in Task Specification:**
```
protocols_to_inject: ["family_fit", "pricing"]
protocol_depth: "full"  # or "summary"
```

</protocol_selection>
```

**Status:** [ ] Not Started

### 3.2 Tiered Protocol Depth

Create summary versions of each protocol:

| Version | Contents | Tokens |
|---------|----------|--------|
| **summary** | Steps only, no rationale | ~150-200 |
| **full** | Steps + Why + How + Anti-patterns | ~400-600 |

```python
# protocol_loader.py addition

def load_protocol(
    name: str,
    layer: ProtocolLayer = "generic",
    depth: Literal["summary", "full"] = "full",
) -> str:
    """Load protocol with optional depth control."""
    base_path = Path(__file__).parent.parent / "prompts" / "protocols"

    if depth == "summary":
        summary_path = base_path / layer / f"{name}_summary.protocol"
        if summary_path.exists():
            return summary_path.read_text(encoding="utf-8")

    # Fall back to full version
    protocol_path = (base_path / layer / f"{name}.protocol").resolve()
    return protocol_path.read_text(encoding="utf-8")
```

**Status:** [ ] Not Started

### 3.3 Token Budget Enforcement

```python
# middleware/protocol_injection.py addition

class TokenBudgetMiddleware(AgentMiddleware):
    """Enforce token budget for protocol injection."""

    def __init__(self, max_protocol_tokens: int = 2000):
        self.max_tokens = max_protocol_tokens

    def before_model(self, messages, config):
        protocols = config.get("metadata", {}).get("protocols_to_inject", [])
        depth = config.get("metadata", {}).get("protocol_depth", "full")

        # Load and measure
        content = load_protocol_bundle(protocols, domain="catalog")
        token_count = self._estimate_tokens(content)

        if token_count > self.max_tokens and depth == "full":
            # Downgrade to summary
            content = load_protocol_bundle(
                protocols,
                domain="catalog",
                depth="summary"
            )
            logger.info(f"Downgraded to summary protocols: {token_count} -> {self._estimate_tokens(content)}")

        # Inject into messages
        ...

        return messages, config

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token)."""
        return len(text) // 4
```

**Status:** [ ] Not Started

### 3.4 Phase 3 Deliverables Checklist

- [ ] PM prompt updated with protocol index
- [ ] Summary versions of all protocols
- [ ] `protocol_depth` parameter support
- [ ] `TokenBudgetMiddleware` implemented
- [ ] Task Specification schema with protocol fields
- [ ] Metrics: Token usage before/after

---

## Phase 4: Multi-Domain Expansion

**Goal:** Generalize framework and add Marketing + Operations domains.

### 4.1 Generic Pattern Validation

Verify generic patterns work across domains:

| Pattern | Catalog Instantiation | Marketing Instantiation |
|---------|----------------------|------------------------|
| Fit Assessment | Product -> Family | Campaign -> Audience |
| Value Discovery | Product -> Price | Campaign -> Budget |
| New Entity | New Family | New Audience Segment |
| Duplicate Prevention | Product duplicates | Campaign duplicates |
| Domain Orientation | Catalog landscape | Marketing landscape |

**Status:** [ ] Not Started

### 4.2 Marketing Domain Protocols

```
agents/src/autifyme_agents/prompts/protocols/marketing/
├── business_context.protocol
├── audience_fit.protocol
├── budget_discovery.protocol
└── campaign_creation.protocol
```

**Status:** [ ] Not Started

### 4.3 Operations Domain Protocols

```
agents/src/autifyme_agents/prompts/protocols/operations/
├── business_context.protocol
├── priority_assessment.protocol
├── resource_allocation.protocol
└── fulfillment_routing.protocol
```

**Status:** [ ] Not Started

### 4.4 Cross-Domain Coordination

Implement PM-level coordination protocol for multi-domain tasks:

```xml
<protocol name="Cross-Domain Coordination" level="PM">
... (from DOMAIN_REASONING_PROTOCOLS.md Section 3.6)
</protocol>
```

**Status:** [ ] Not Started

### 4.5 Phase 4 Deliverables Checklist

- [ ] Generic patterns validated across domains
- [ ] Marketing domain protocols
- [ ] Operations domain protocols
- [ ] Cross-domain coordination protocol
- [ ] Multi-domain routing in PM
- [ ] Integration test: Cross-domain task

---

## Decision Log

Track architectural decisions made during implementation.

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2025-12-16 | Unified Tool + Middleware mechanism | All agents use same pattern; semantically correct (protocols as instructions in system prompt) | Simplified architecture |
| 2025-12-16 | Message-history based (not config) | REPL verified: config doesn't persist across tool calls; ToolMessages do | Reliable state mechanism |
| 2025-12-16 | wrap_model_call (not before_model) | Proper LangChain v1 API with access to both state.messages AND system_message + request.override() | Correct API usage |
| 2025-12-16 | Tool name identification | Check `msg.name == 'load_protocol'` instead of marker parsing; cleaner, no string parsing | Simpler identification |
| 2025-12-16 | List input for load_protocol | Accepts `list[str]` to load multiple protocols in single call; prevents parallel tool call issues | Prevents race conditions |
| 2025-12-16 | Middleware deduplication | Track seen protocol names, inject each only once regardless of how many times loaded | Prevents duplicate injection |
| 2025-12-16 | Direct content return | Tool returns formatted protocol content directly; middleware just aggregates and injects | Clean separation |
| 2025-12-16 | No unload_protocol tool | Natural scope boundaries handle cleanup; adds complexity with no benefit | Simpler API |
| 2025-12-16 | Agent-driven protocol selection | Agent decides what to load via protocol index; PM doesn't specify protocols for specialists | Agent autonomy preserved |
| 2025-12-16 | Per-agent protocol directories | Resolution: agent-specific first, then shared; enables specialization | Flexible protocol organization |

---

## Progress Tracking

### Phase 1: Foundation
- Start Date: ___
- Target End: ___
- Actual End: ___
- Status: NOT STARTED

### Phase 2: Protocol Execution
- Start Date: ___
- Target End: ___
- Actual End: ___
- Status: NOT STARTED

### Phase 3: Token Optimization
- Start Date: ___
- Target End: ___
- Actual End: ___
- Status: NOT STARTED

### Phase 4: Multi-Domain
- Start Date: ___
- Target End: ___
- Actual End: ___
- Status: NOT STARTED

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Protocol size causes attention dilution | Medium | High | Token budget enforcement, tiered depth |
| Visual analysis remains ungrounded | High | Medium | Structured criteria, HITL for visual-heavy decisions |
| Cold start bootstrap errors cascade | Medium | High | Heavy user confirmation, clear anchor warnings |
| Protocol coverage gaps | Medium | Medium | "No protocol fits" fallback, gap tracking |

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Family assignment accuracy | TBD | 90%+ | HITL approval rate |
| Pricing recommendation acceptance | TBD | 85%+ | HITL approval rate |
| Duplicate prevention | TBD | 99%+ | Zero duplicates created |
| Token usage per specialist call | ~8,000 | ~3,000 | LangSmith traces |
| Protocol step completion | TBD | 100% | Trace analysis |

---

## References

- [DOMAIN_REASONING_PROTOCOLS.md](./DOMAIN_REASONING_PROTOCOLS.md) - Framework specification
- [WORKFLOW_EVALUATION_FRAMEWORK.md](../testing/WORKFLOW_EVALUATION_FRAMEWORK.md) - Trace evaluation
- [PROMPT_ENGINEERING_STANDARDS.md](../tech/PROMPT_ENGINEERING_STANDARDS.md) - Prompt design
- [UV_REPL_BEST_PRACTICES.md](../tech/UV_REPL_BEST_PRACTICES.md) - API verification

---

**Document Version:** 1.0
**Last Updated:** December 16, 2025
