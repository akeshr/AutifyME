# Domain-Specific Reasoning Protocols

**Created:** December 15, 2025
**Updated:** December 16, 2025
**Status:** APPROVED - Ready for Implementation
**Purpose:** Domain-agnostic framework for encoding domain expertise as executable reasoning protocols

---

## Executive Summary

LLMs are general-purpose. Our domains require specific behavior. Fine-tuning is not an option.

**The Problem:** Output examples get COPIED, not understood. Rules get applied blindly.

**The Solution:** Domain-Specific Reasoning Protocols - examples that encode the REASONING PROCESS, not just the output. Agents must EXECUTE the steps, not copy the answer.

**Key Insight:** Domain knowledge can be encoded as PROCESS. The protocol IS the expertise.

**Framework Approach:** Generic patterns that apply to ANY domain, instantiated with domain-specific entities and values.

---

## Table of Contents

**FOUNDATION**
1. [The Problem](#1-the-problem)
2. [The Solution: Reasoning Protocols](#2-the-solution-reasoning-protocols)
   - 2.3 [Why Protocols Work: Tool Grounding](#23-why-protocols-work-tool-grounding)
   - 2.4 [The Grounding Boundary: Data vs Interpretation](#24-the-grounding-boundary-data-vs-interpretation)
3. [Multi-Domain Architecture](#3-multi-domain-architecture)
   - 3.4 [Protocol Applicability: ALL Agents Need Domain Expertise](#34-protocol-applicability-all-agents-need-domain-expertise)
   - 3.6 [Cross-Domain Coordination Protocol](#36-cross-domain-coordination-protocol)
   - 3.7 [Shared Entity References](#37-shared-entity-references)

**PM-LEVEL PROTOCOLS**
4. [PM Intelligence and Routing](#4-pm-intelligence-and-routing)
   - 4.8 [Task Specification Contract](#48-task-specification-contract)
   - 4.10 [Correction Flow for Stateless Specialists](#410-correction-flow-for-stateless-specialists)

**GENERIC PATTERNS**
5. [Generic Protocol Patterns](#5-generic-protocol-patterns)
6. [Tool Mastery Protocols](#6-tool-mastery-protocols)

**DOMAIN IMPLEMENTATION**
7. [Protocol Creation Guide](#7-protocol-creation-guide)
8. [Domain Instantiation](#8-domain-instantiation)
9. [Catalog Domain Example](#9-catalog-domain-example)
10. [Other Domains (Future)](#10-other-domains-future)

**INTEGRATION**
11. [Integration with Agent Architecture](#11-integration-with-agent-architecture)
12. [Protocol Composition Framework](#12-protocol-composition-framework)
    - 12.5 [PARTIAL Result Branching](#125-partial-result-branching)

**QUALITY & CONFIDENCE**
13. [Confidence Scoring Framework](#13-confidence-scoring-framework)
    - 13.4 [Chained Confidence Handling](#134-chained-confidence-handling)
14. [Failure Handling](#14-failure-handling)
    - 14.2 [Escalation Paths](#142-escalation-paths)
    - 14.3 [Cold Start Protocols](#143-cold-start-protocols)

**FUTURE WORK**
15. [Protocol Delivery Strategy](#15-protocol-delivery-strategy)
16. [Episodic Memory](#16-episodic-memory-layer-4)
17. [Protocol Feedback and Improvement](#17-protocol-feedback-and-improvement)

**REFERENCES**
18. [References](#18-references)

---

## 1. The Problem

### 1.1 The Fundamental Gap

| What LLM Has | What Domain Needs |
|--------------|-------------------|
| General intelligence | Specific expertise |
| Broad knowledge | YOUR business rules |
| Pattern matching | Grounded reasoning |
| Training data patterns | YOUR operational patterns |

### 1.2 Why Common Solutions Are Incomplete

| Approach | Limitation |
|----------|------------|
| **Output Examples** | Agent copies the OUTPUT format, not the REASONING that produced it |
| **Rules** | Abstract principles - agent doesn't know when/how to apply |
| **RAG** | Requires knowing WHAT to retrieve - agent doesn't know what questions to ask |
| **More context** | Passive information - doesn't guide reasoning process |

### 1.3 The Core Insight

**The agent doesn't know:**
- What questions to ask
- What matters for each decision type
- How YOUR business thinks about problems
- How to use YOUR tools effectively

**Output examples alone can't teach this** - they show WHAT to conclude, not HOW to reason.

**The solution:** Examples that encode the REASONING PROCESS, not just the output. These are protocols - structured examples that show the steps the agent MUST execute.

**Key distinction:**
- Output example: "Here's what a good product listing looks like"
- Protocol (reasoning example): "Here's how to THINK through creating a product listing - step by step"

---

## 2. The Solution: Reasoning Protocols

### 2.1 What Is a Reasoning Protocol?

A Domain-Specific Reasoning Protocol is a **step-by-step reasoning process** that:
- Encodes WHAT to investigate
- Specifies WHICH queries to execute
- Defines HOW to interpret results
- Guides WHEN to conclude vs continue

**The protocol IS the domain expertise in executable form.**

### 2.2 Protocols ARE Structured Examples

Protocols are NOT an alternative to examples - they ARE examples, but examples of REASONING rather than OUTPUT.

| Type | What It Shows | How Agent Uses It |
|------|---------------|-------------------|
| **Rule** | Abstract principle | Tries to apply (often incorrectly) |
| **Output Example** | Final result | Copies the format |
| **Protocol (Reasoning Example)** | Step-by-step process | EXECUTES each step |

**Protocols show the reasoning that PRODUCES the output.** When the agent sees explicit steps, it must execute them - it can't just copy the final answer.

### 2.3 Why Protocols Work: Tool Grounding

**The key insight:** Protocols work because they force TOOL CALLS that ground reasoning in real data.

```
Without protocols:
Agent sees example --> Copies output format --> Hallucinates plausible-looking data

With protocols:
Agent sees steps --> Executes read_data() --> Gets REAL data --> Must reason about ACTUAL results
```

**The agent can't fake query results.** When Step 2 says "EXECUTE read_data(...)", the tool returns actual database records. The agent must then reason about what it actually found, not what it imagines might exist.

**This is the core mechanism:** Protocols don't just structure reasoning - they GROUND it in reality through mandatory tool execution.

### 2.4 The Grounding Boundary: Data vs Interpretation

**Critical clarification:** Tool grounding prevents DATA hallucination, not INTERPRETATION errors.

| Step Type | Grounded? | Example | What Can Go Wrong |
|-----------|-----------|---------|-------------------|
| **QUERY steps** | YES | read_data returns real records | Nothing - data is factual |
| **AGGREGATE steps** | YES | Price range is 50-150 | Nothing - statistics are factual |
| **ANALYZE steps** | NO | "This looks decorative" | Inference can be wrong |
| **COMPARE steps** | PARTIAL | Compare data vs inference | Data side grounded, interpretation not |

**Visual Analysis is the Key Ungrounded Step:**

When a protocol says "ANALYZE - Product's Target Customer based on visual attributes":
- The agent INFERS: "This looks decorative" (no tool verification possible)
- The agent INFERS: "This seems premium quality" (subjective assessment)
- The agent INFERS: "Target customer: gift buyers" (derived from visual inference)

**Why this matters:** Visual analysis is where INTELLIGENCE is most critical. Protocols structure the reasoning, but the agent must apply genuine judgment.

**How we mitigate:**
1. **Structured criteria** - Define what "decorative" means (designed patterns, gift packaging, display-oriented)
2. **Comparison to grounded data** - Compare inference against queried family characteristics
3. **Confidence signaling** - Visual inference should drive MEDIUM confidence, not HIGH
4. **HITL checkpoint** - Visual-heavy decisions get human review

**The balance:**
- Tool grounding prevents: "The database shows..." hallucinations
- Intelligence handles: "Based on visual attributes..." interpretations
- Protocols ensure: Both happen in structured sequence

### 2.5 Protocol Structure

```
RULE (Abstract):
"Fit is determined by qualifying criteria alignment"
--> Agent interprets abstractly, applies inconsistently

PROTOCOL (Executable):
"Step 2: EXECUTE query to get qualifying criteria for target entity
 Step 3: ANALYZE subject's attributes against criteria
 Step 4: COMPARE and determine match/mismatch"
--> Agent executes concrete steps, discovers the answer
```

The domain knowledge is encoded IN THE STEPS, not in abstract principles.

---

## 3. Multi-Domain Architecture

AutifyME is an **Autonomous Agentic Organization** - not a single-purpose tool. Multiple domains work together under PM orchestration.

### 3.1 The Multi-Domain Vision

```
+=====================================================================+
|                    AUTIFYME: AUTONOMOUS AGENTIC ORGANIZATION         |
+=====================================================================+

                              USER INPUT
                                  |
                                  v
+=====================================================================+
|                  PROJECT MANAGER (STATEFUL DeepAgent)                |
+=====================================================================+
|                                                                      |
|  STATE: conversation_history, current_topic, recent_entities,        |
|         user_preferences, pending_entity, active_workflow            |
|                                                                      |
|  INTELLIGENCE LAYER (Pre-Routing):                                   |
|  1. RESOLVE - Turn "this", "it" into explicit entities               |
|  2. CONTEXT - Load conversation continuity                           |
|  3. INFER - Detect implicit intent                                   |
|  4. ASSESS - User state (efficient, exploring, frustrated)           |
|  5. ENRICH - Build complete understanding                            |
|                                                                      |
|  ROUTING LAYER:                                                      |
|  - Domain Discovery (What domain handles this?)                      |
|  - Intent Classification (What does user want?)                      |
|  - Protocol Selection (Which protocols to apply?)                    |
+=====================================================================+
                                  |
                    TASK SPECIFICATION CONTRACT
                    (All context resolved, explicit)
                                  |
            +---------------------+---------------------+
            |                     |                     |
            v                     v                     v
+------------------+   +------------------+   +------------------+
|   CATALOGING     |   |    MARKETING     |   |   OPERATIONS     |
|  (STATELESS)     |   |   (STATELESS)    |   |   (STATELESS)    |
+------------------+   +------------------+   +------------------+
| Fresh every call |   | Fresh every call |   | Fresh every call |
| No memory        |   | No memory        |   | No memory        |
| Execute & return |   | Execute & return |   | Execute & return |
+------------------+   +------------------+   +------------------+
| Specialists:     |   | Specialists:     |   | Specialists:     |
| - Catalog Spec   |   | - Content Spec   |   | - Order Spec     |
| - Image Spec     |   | - Campaign Spec  |   | - Fulfillment    |
| - Data Spec      |   | - Analytics Spec |   |                  |
+------------------+   +------------------+   +------------------+
| Protocols:       |   | Protocols:       |   | Protocols:       |
| - Family Fit     |   | - Audience Fit   |   | - Priority Fit   |
| - Pricing        |   | - Budget Disc.   |   | - Resource Alloc |
| - New Entity     |   | - New Segment    |   | - SLA Assessment |
+------------------+   +------------------+   +------------------+
            |                     |                     |
            +---------------------+---------------------+
                                  |
                                  v
+---------------------------------------------------------------------+
|                         SHARED LAYER                                 |
|  - Generic Protocol Patterns (Fit, Value, New Entity, etc.)          |
|  - Tool Mastery Protocols (read_data, aggregate_data, etc.)          |
|  - Universal Data Engine                                             |
+---------------------------------------------------------------------+
```

### 3.2 Domain Registry

| Domain | Purpose | Key Entities | Primary Protocols |
|--------|---------|--------------|-------------------|
| **Cataloging** | Product catalog management | products, families, segments | Family Fit, Pricing, New Entity |
| **Marketing** | Campaign and content | campaigns, audiences, content | Audience Fit, Budget Discovery |
| **Operations** | Order and fulfillment | orders, inventory, shipments | Priority Assessment, Resource Allocation |
| **Customer Service** | Support and inquiries | tickets, customers, resolutions | Urgency Assessment, Resolution Routing |
| **Finance** | Invoicing and payments | invoices, payments, accounts | Payment Fit, Credit Assessment |

### 3.3 Protocol Layer Architecture

```
+=====================================================================+
|                 PROTOCOL FRAMEWORK (LAYERED)                         |
+=====================================================================+

LAYER 0: PM-LEVEL PROTOCOLS (Section 4)
+---------------------------------------------------------------------+
| - Domain Discovery           | What domain handles this input?       |
| - Intent Classification      | What does the user want?              |
| - Domain Routing             | Which specialists to invoke?          |
+---------------------------------------------------------------------+

LAYER 1: GENERIC PATTERNS (Reusable Across ALL Domains)
+---------------------------------------------------------------------+
| - Fit Assessment Pattern     | Does X belong with Y?                 |
| - Value Discovery Pattern    | What should the value of X be?        |
| - New Entity Pattern         | Should we create a new X?             |
| - Duplicate Prevention       | Does X already exist?                 |
| - Domain Orientation         | What is the current state of X?       |
+---------------------------------------------------------------------+

LAYER 2: TOOL MASTERY (Applies to ALL Domains)
+---------------------------------------------------------------------+
| - read_data Mastery          | Query patterns, efficiency            |
| - aggregate_data Mastery     | Pattern discovery, statistics         |
| - write_data Mastery         | Safe mutation, verification           |
| - inspect_schema Mastery     | Structure understanding               |
+---------------------------------------------------------------------+

LAYER 3: DOMAIN INSTANTIATION (Per Domain)
+---------------------------------------------------------------------+
| Generic Pattern + Domain Entities + Domain Values = Domain Protocol  |
|                                                                      |
| Example:                                                             |
| Fit Assessment + (family, customer_segment, product) = Family Fit    |
| Fit Assessment + (audience, audience_profile, campaign) = Audience Fit|
+---------------------------------------------------------------------+
```

### 3.4 Protocol Applicability: ALL Agents Need Domain Expertise

**Critical:** Protocols are NOT just for specialists. EVERY agent type requires domain, tool, and data expertise to perform effectively.

| Agent Level | Protocol Types | Why They Need Protocols |
|-------------|----------------|------------------------|
| **PM** | Routing, Intelligence, Synthesis | Must understand domains to route correctly, resolve references, infer intent |
| **Analysts** | Exploration, Orientation, Tool Mastery | Must query comprehensively, interpret data correctly, discover patterns |
| **Specialists** | Decision, Domain-Specific, Tool Mastery | Must make grounded decisions using domain business rules |
| **Any SubAgent** | Tool Mastery, Orientation | Must use tools efficiently and understand data context |

**The common thread:** All agents interact with YOUR data using YOUR tools in YOUR domain context. Without protocols:
- PM routes incorrectly (doesn't understand domain boundaries)
- Analysts explore superficially (don't know what questions to ask)
- Specialists decide poorly (apply general knowledge instead of your business rules)

**Protocol coverage by agent:**

| Protocol Category | PM | Analysts | Specialists |
|-------------------|-------|----------|-------------|
| Tool Mastery | YES | YES | YES |
| Domain Orientation | YES | YES | YES |
| Routing/Intelligence | YES | - | - |
| Exploration Patterns | - | YES | - |
| Decision Protocols | - | - | YES |
| Business Context | YES | YES | YES |

**Analyst vs Specialist: The Real Distinction**

The line between analysts and specialists is about ACCOUNTABILITY, not capability:

| Aspect | Analyst | Specialist |
|--------|---------|------------|
| **Primary function** | Explore and suggest | Decide and commit |
| **Output type** | Findings, options, recommendations | Decisions, actions, writes |
| **Accountability** | "Here's what I found" | "This is the answer" |
| **HITL trigger** | Never (read-only) | On writes and uncertain decisions |
| **Protocol usage** | Lightweight (gather data) | Full (execute to conclusion) |

**Why this matters:**

Analysts DO reason about fit, value, etc. - but they present OPTIONS.
Specialists COMMIT to decisions - they execute full protocols and conclude.

```
Analyst exploring family fit:
  "Product could fit in:
   - Decorative Ceramics (material match)
   - Kitchen Display (use case match)
   - Gift Items (customer match)
   Recommend evaluating each."

Specialist deciding family fit:
  [Executes full Fit Assessment Protocol]
  "Family: Decorative Ceramics
   Confidence: HIGH
   Evidence: Customer segment 85% match, price range aligned
   DECISION: Assign to Decorative Ceramics"
```

**Analysts use protocols IMPLICITLY** (mental model for exploration).
**Specialists use protocols EXPLICITLY** (documented step execution).

### 3.5 Cross-Domain Scenarios

Some tasks span multiple domains. PM orchestrates:

| Scenario | Domains Involved | PM Orchestration |
|----------|------------------|------------------|
| "New product launch" | Cataloging + Marketing | Catalog product first, then create campaign |
| "Customer complaint about order" | Customer Service + Operations | Triage in CS, route to Ops for resolution |
| "Inventory restock" | Operations + Finance | Assess need in Ops, approve budget in Finance |

### 3.6 Cross-Domain Coordination Protocol

**Problem:** When tasks span domains, specialists are stateless and isolated. How do results flow between domains?

```xml
<protocol name="Cross-Domain Coordination" level="PM" type="orchestration">

## PURPOSE
Coordinate multi-domain tasks where output from Domain A feeds into Domain B.

## WHEN TO USE
- User request spans multiple domains
- Task requires sequential domain processing
- One domain's output is another's input

## PM RESPONSIBILITIES

### Step 1: DECOMPOSE - Identify Domain Sequence
Parse task into domain components:

| Component | Domain | Depends On |
|-----------|--------|------------|
| Component A | Domain X | (none - first) |
| Component B | Domain Y | Component A output |
| Component C | Domain Z | Component B output |

### Step 2: EXECUTE - Sequential with Context Passing
For each component in sequence:

1. Build Task Specification for Domain X
2. Execute, capture output
3. EXTRACT relevant outputs for next domain:
   - Entity IDs created
   - Decisions made
   - Values determined
4. Build Task Specification for Domain Y INCLUDING:
   - cross_domain_context: {from: "Domain X", outputs: [...]}
5. Continue chain

### Step 3: SYNTHESIZE - Combined Response
After all domains complete:
- Merge results into coherent response
- Track entities created across domains
- Report combined outcome to user

## CROSS-DOMAIN CONTEXT STRUCTURE

```
cross_domain_context:
  from_domain: "catalog"
  outputs:
    - entity_type: "product"
      entity_id: "prod_123"
      entity_name: "Blue Ceramic Vase"
      action_taken: "created"
    - decision: "family_assignment"
      result: "Decorative Ceramics"
  relevant_for: "Use this product in campaign creative"
```

## CONFLICT RESOLUTION

**What if domains disagree?**

| Conflict Type | Resolution |
|---------------|------------|
| Entity interpretation differs | Primary domain (owner) wins |
| Timing conflict | PM sequences appropriately |
| Resource conflict | Escalate to user |

**Entity Ownership:**
- Product entity: Catalog owns, Marketing references
- Campaign entity: Marketing owns, may reference products
- Order entity: Operations owns, Finance references

## EXAMPLE: Product Launch

```
Task: "Launch this new product with a campaign"

STEP 1: DECOMPOSE
- Component 1: Create product (Catalog)
- Component 2: Create campaign (Marketing) - needs product_id

STEP 2: EXECUTE

[Catalog Specialist]
Task: Create product
Result: product_id=prod_123, name="Blue Vase", family="Decorative"

[PM extracts cross-domain context]

[Marketing Specialist]
Task: Create campaign for product launch
Cross-domain context:
  - Product: prod_123 "Blue Vase" in "Decorative" family
  - Catalog positioning: mid-premium
  - Target customer: gift buyers (from family)
Result: campaign_id=camp_456

STEP 3: SYNTHESIZE
"Created Blue Vase (prod_123) in Decorative family.
 Launched campaign (camp_456) targeting gift buyers."
```

</protocol>
```

### 3.7 Shared Entity References

**Problem:** Same entity exists in multiple domain contexts.

| Entity | Primary Domain (Owner) | Secondary Domains (Reference) |
|--------|------------------------|------------------------------|
| Product | Catalog | Marketing, Operations, Finance |
| Customer | Customer Service | Marketing, Finance |
| Order | Operations | Customer Service, Finance |
| Campaign | Marketing | (none) |

**Rules:**
1. **Owner domain** can CREATE, UPDATE, DELETE
2. **Reference domains** can READ, REFERENCE
3. **Changes propagate** - PM notifies reference domains of owner changes
4. **Conflicts escalate** - If reference domain needs change, escalate to owner

---

## 4. PM Intelligence and Routing

> **Design Target** - Describes ideal PM behavior. Current implementation may not include all aspects.

The PM is the **brain** of AutifyME - it thinks, remembers, and decides. Specialists are the **hands** - they execute, return, and forget.

### 4.1 Stateful/Stateless Architecture

**Critical Constraint:** PM is a DeepAgent (stateful), Specialists are SubAgents (stateless).

```
+=======================================================================+
|                    AGENT STATE ARCHITECTURE                            |
+=======================================================================+

+----------------------------------+    +----------------------------------+
|     PM (STATEFUL DEEPAGENT)      |    |  SPECIALIST (STATELESS SUBAGENT) |
+----------------------------------+    +----------------------------------+
| - Maintains conversation state   |    | - Fresh every invocation         |
| - Remembers prior turns          |    | - No memory of previous calls    |
| - Tracks user patterns           |    | - Receives ALL context needed    |
| - Resolves references            |    | - Cannot look up history         |
| - Learns from corrections        |    | - Executes and returns           |
+----------------------------------+    +----------------------------------+
           |                                         ^
           | EXPLICIT TASK SPECIFICATION             |
           | (no ambiguity, all context included)    |
           +-----------------------------------------+
```

| Capability | PM (Stateful) | Specialist (Stateless) |
|------------|---------------|------------------------|
| Reference resolution ("this", "yesterday") | YES | NO - receives resolved |
| Conversation memory | YES | NO - receives summary |
| User state tracking | YES | NO - receives as context |
| Protocol selection | YES | NO - receives which to run |
| Domain reasoning | ROUTING | EXECUTION |
| Learning from outcomes | YES | NO |
| Proactive suggestions | YES | NO |

### 4.2 PM State (Conceptual)

The PM maintains state across conversation turns. This is managed by LangGraph's checkpointer - no custom code needed.

**What PM Tracks:**

| State Category | What It Contains | Purpose |
|----------------|------------------|---------|
| **Conversation** | Recent turns (5-10), current topic | Continuity |
| **Entities** | Recent entities, pending entity | Reference resolution |
| **User Model** | Preferences, state (frustrated/exploring/efficient) | Adaptive responses |
| **Workflow** | Active workflow, pending HITL | Coordination |

**Entity Reference Elements:**
- entity_type (product, family, campaign)
- entity_id, entity_name
- last_action (created, updated, discussed)
- timestamp

**Topic Context Elements:**
- domain, intent (CREATE, UPDATE, QUERY)
- primary_entity, related_entities

### 4.3 PM Intelligence Layer (Pre-Routing)

**Before routing, PM must UNDERSTAND.** This is where stateful intelligence applies.

```
USER INPUT
    |
    v
+=======================================================================+
|                 PM INTELLIGENCE LAYER (STATEFUL)                       |
+=======================================================================+
| 1. RESOLVE - Turn implicit references into explicit entities           |
| 2. CONTEXT - Load conversational history, understand continuation      |
| 3. INFER - Read between the lines, detect implicit intent              |
| 4. ASSESS - Understand user state (frustrated, exploring, efficient)   |
| 5. ENRICH - Build complete understanding before routing                |
+=======================================================================+
    |
    v (Enriched Understanding)
+=======================================================================+
|                 PM ROUTING LAYER (PROTOCOLS)                           |
+=======================================================================+
| - Domain Discovery Protocol                                            |
| - Intent Classification Protocol                                       |
| - Protocol Selection                                                   |
+=======================================================================+
    |
    v (Task Specification)
+=======================================================================+
|                 SPECIALIST EXECUTION (STATELESS)                       |
+=======================================================================+
```

```xml
<protocol name="PM Intelligence" level="PM" type="pre-routing">

## PURPOSE
Understand user intent BEFORE applying routing protocols.
Uses PM's stateful context to resolve ambiguity.

## ALWAYS EXECUTE FIRST (before Domain Discovery)

### Step 1: RESOLVE - References
Check PM state for references in user input:

| Reference Type | Example | How to Resolve |
|----------------|---------|----------------|
| Pronoun | "this", "it", "that" | Check pending_entity in state |
| Temporal | "yesterday", "earlier" | Query by timestamp |
| Relational | "the same", "like before" | Check recent_entities |
| Implicit | [just a number like "350"] | Check current_topic context |

**Action:**
- If state has context: Resolve and document
- If unclear: State assumption, continue (don't ask unless truly ambiguous)

### Step 2: CONTEXT - Conversation Continuity
Check if current input continues prior work:

| State Signal | Meaning |
|--------------|---------|
| current_topic exists | User likely continuing that work |
| pending_entity set | Input probably relates to this entity |
| recent conversation about X | New input may reference X |

**Action:**
- If continuation: Carry forward context
- If new topic: Clear pending state, start fresh

### Step 3: INFER - Implicit Intent
Read between the lines using context:

| Input Pattern | With Context | Inferred Intent |
|---------------|--------------|-----------------|
| Just a number "350" | Discussing pricing | Price = 350 |
| Just an image | After "add more" | Add to same batch |
| "wrong" | After showing result | Correction needed |
| Entity name only | No current task | Lookup/inquiry |

**Action:**
- Note inferred intents
- Document user_hints for specialist

### Step 4: ASSESS - User State
Detect user's communication mode:

| Signal | State | Adapt By |
|--------|-------|----------|
| Short messages | Efficient | Skip pleasantries, just do it |
| "asap", "urgent" | Time pressure | Prioritize, confirm speed |
| Questions, "what if" | Exploring | Explain more, offer options |
| "wrong", "again", "still" | Frustrated | Be efficient, acknowledge issue |

**Action:**
- Set user_state in PM state
- Adapt communication style

### Step 5: ENRICH - Synthesize Understanding
Combine all intelligence into enriched understanding:

**Output:**
```
ENRICHED UNDERSTANDING:
- Resolved references: [list]
- Continuation: [yes/no, of what]
- Implicit intent: [what user probably means]
- User state: [mode]
- User hints: {field: value} for specialist
```

## THEN PROCEED TO DOMAIN ROUTING

</protocol>
```

### 4.4 The Routing Problem

```
User sends: [1 image]

After Intelligence Layer:
- References: None (new item)
- Continuation: No active topic
- Implicit intent: CREATE (new input = creation)
- User state: Efficient (single image, no text)

PM must now determine:
1. DOMAIN: Which domain handles this? (Cataloging? Marketing?)
2. INTENT: What action? (CREATE product)
3. ROUTING: Which specialists and protocols?
```

### 4.5 Domain Discovery Protocol

```xml
<protocol name="Domain Discovery" level="PM" type="routing">

## PURPOSE
Determine which domain handles an ambiguous input.

## WHEN TO USE
- Input doesn't clearly indicate domain (e.g., image only, vague text)
- Input could belong to multiple domains
- New input type not seen before

## STEPS

### Step 1: CLASSIFY - Input Type
Classify what was received:

| Input Type | Examples |
|------------|----------|
| Image(s) only | Product photos, marketing creatives, screenshots |
| Text only | Commands, questions, descriptions |
| Image + Text | Product with description, image with question |
| Document | Invoice, order, specification |
| Structured data | CSV, spreadsheet, JSON |

**Result:**
Input type: [classification]

### Step 2: ANALYZE - Context Signals
Look for domain indicators:

| Signal | Suggests Domain |
|--------|-----------------|
| Product-like image | Cataloging |
| Marketing creative | Marketing |
| Order/invoice | Operations/Finance |
| Question about existing | Customer Service |
| Price/budget mention | Finance or relevant domain |
| Customer/audience mention | Marketing |
| Stock/inventory mention | Operations |

**Result:**
Domain signals: [list of signals and suggested domains]

### Step 3: ASSESS - Confidence
How confident is domain assignment?

| Confidence | Criteria |
|------------|----------|
| HIGH | Multiple signals point to same domain |
| MEDIUM | Some signals, or single strong signal |
| LOW | No clear signals, or conflicting signals |

**Result:**
Confidence: [HIGH/MEDIUM/LOW]

### Step 4: ROUTE or CLARIFY

**If HIGH confidence:**
- Route to identified domain
- State: "Routing to [domain] based on [signals]"

**If MEDIUM confidence:**
- Route to likely domain
- Flag for early validation: "Assumed [domain] intent - confirm if different"

**If LOW confidence:**
- DO NOT GUESS
- Ask user: "I see [input type]. Are you looking to:
  - A) Add this to product catalog
  - B) Use for marketing content
  - C) Something else: [describe]"

## ANTI-PATTERNS
- Guessing domain without signals
- Not asking when genuinely ambiguous
- Assuming cataloging for all images (domain-biased)

</protocol>
```

### 4.6 Intent Classification Protocol

```xml
<protocol name="Intent Classification" level="PM" type="routing">

## PURPOSE
Determine what action the user wants within a domain.

## WHEN TO USE
After domain is determined, before invoking specialists.

## STEPS

### Step 1: IDENTIFY - Action Verbs
Look for explicit action indicators:

| Verb/Phrase | Intent |
|-------------|--------|
| "add", "create", "new" | CREATE entity |
| "update", "change", "modify" | UPDATE entity |
| "find", "search", "show" | READ/QUERY entity |
| "delete", "remove" | DELETE entity |
| "what is", "how much", "tell me" | INQUIRY |
| "help", "fix", "problem" | SUPPORT |

**Result:**
Action intent: [CREATE/UPDATE/READ/DELETE/INQUIRY/SUPPORT]

### Step 2: IDENTIFY - Target Entity
What entity is the action targeting?

| Domain | Possible Entities |
|--------|-------------------|
| Cataloging | product, family, variant, image |
| Marketing | campaign, content, audience, creative |
| Operations | order, shipment, inventory, return |
| Customer Service | ticket, inquiry, complaint |

**Result:**
Target entity: [entity type]

### Step 3: SYNTHESIZE - Intent Statement
Combine action + entity + context:

**Result:**
"User wants to [ACTION] a [ENTITY] with context: [relevant details]"

### Step 4: MAP - To Workflow/Specialist

| Intent Pattern | Route To |
|----------------|----------|
| CREATE + product | Cataloging workflow |
| CREATE + campaign | Marketing workflow |
| INQUIRY + order | Customer Service + Operations |
| UPDATE + product | Cataloging specialist |

**Result:**
Route: [workflow or specialist]

</protocol>
```

### 4.7 Complete PM Routing Flow

```
USER INPUT
    |
    v
+---------------------------+
| Step 1: Domain Discovery   |
| - Classify input type      |
| - Analyze context signals  |
| - Assess confidence        |
+---------------------------+
    |
    | If LOW confidence --> Ask user for clarification
    |
    v
+---------------------------+
| Step 2: Intent Classification |
| - Identify action verb     |
| - Identify target entity   |
| - Synthesize intent        |
+---------------------------+
    |
    v
+---------------------------+
| Step 3: Route to Domain    |
| - Select appropriate       |
|   workflow/specialist      |
| - Load domain context      |
| - Load relevant protocols  |
+---------------------------+
    |
    v
DOMAIN SPECIALIST EXECUTES
(using domain-specific protocols)
```

### 4.8 Task Specification Contract

**Critical:** Specialists are stateless. They cannot look up context, resolve references, or remember previous calls. PM must pass EVERYTHING the specialist needs in a single, explicit task specification.

**Task Specification Elements:**

| Category | Elements | Purpose |
|----------|----------|---------|
| **Identity** | specialist, domain | WHO is being asked |
| **Intent** | action (CREATE/UPDATE/ANALYZE/QUERY), target_entity, target_id | WHAT to do |
| **Context** | resolved_context (see below) | ALL resolved context |
| **Protocols** | protocols_to_apply | WHICH protocols to execute |
| **User Hints** | user_hints | Inference from PM intelligence |
| **Communication** | response_style, user_state | HOW to respond |

**Resolved Context Elements:**

| Element | Description |
|---------|-------------|
| primary_entity | Full entity data (no "this", "it") |
| related_entities | Other entities mentioned |
| images | Image URLs/paths |
| text_input | Original user text |
| resolved_text | With references replaced |
| conversation_summary | Brief context (not full history) |
| relevant_prior_decisions | What user rejected/confirmed |
| company_id, company_context | Business settings |

**Example Task Specification:**

```
TASK SPECIFICATION
==================
Identity:
  - specialist: cataloging_specialist
  - domain: catalog

Intent:
  - action: CREATE
  - target_entity: product
  - target_id: (none - creating new)

Resolved Context:
  - primary_entity: (none - creating new)
  - related_entities: Blue Pottery Collection (fam_123)
  - images: [https://storage.../img_abc.jpg]
  - text_input: "add this to the same family"
  - resolved_text: "add this product to Blue Pottery Collection family"
  - conversation_summary: "User adding products to Blue Pottery Collection. Last product was vase at 450."
  - relevant_prior_decisions: ["User prefers descriptive names over SKU-style"]
  - company_context: INR currency, premium pricing strategy

Protocols: duplicate_prevention, family_fit_assessment, pricing_discovery
User Hints: likely_price_range=400-500, style=ceramic
Communication: response_style=efficient, user_state=efficient
```

**Why This Matters:**

| Without Task Spec | With Task Spec |
|-------------------|----------------|
| Specialist sees "add this to the same family" | Specialist sees "add to Blue Pottery Collection (fam_123)" |
| Specialist doesn't know prior context | Specialist knows "last product was vase at 450" |
| Specialist guesses communication style | Specialist knows "user wants efficiency" |
| Specialist runs all protocols | Specialist runs only relevant protocols |

### 4.9 Example: "1 Image Only" Scenario

```
INPUT: [Image of decorative ceramic vase]
CONTEXT: User has been adding products to "Blue Pottery Collection" family

=== PM INTELLIGENCE LAYER (STATEFUL) ===

STEP 1 - RESOLVE:
  - No explicit references in input (just image)
  - Check state: pending_entity = None, current_topic = "Blue Pottery Collection"
  - Likely continuation of current topic

STEP 2 - CONTEXT:
  - current_topic: { domain: "catalog", intent: "CREATE", family: "Blue Pottery" }
  - Recent: User added 3 products to this family in last 10 minutes
  - Pattern: User is batch-adding products

STEP 3 - INFER:
  - Image only + active cataloging topic = ADD to current family
  - No explicit price = use similar product pricing as hint

STEP 4 - ASSESS:
  - Short messages, no pleasantries = EFFICIENT user state
  - Rapid submissions = batch mode

STEP 5 - ENRICH:
  Resolved references: [current_topic -> Blue Pottery Collection]
  Continuation: YES, of batch cataloging
  Implicit intent: ADD to current family (not new context)
  User state: EFFICIENT
  User hints: {family: "Blue Pottery", price_range: "400-500"}

=== PM ROUTING LAYER ===

DOMAIN DISCOVERY:
  Step 1: Input type = Image only
  Step 2: Signals: Product-like + active catalog topic = Cataloging
  Step 3: Confidence = HIGH (context confirms)
  Step 4: Route to Cataloging

INTENT CLASSIFICATION:
  Step 1: No verb - infer CREATE from context
  Step 2: Target = product
  Step 3: "CREATE product in Blue Pottery Collection family"
  Step 4: Route = Cataloging specialist

=== TASK SPECIFICATION (PASSED TO STATELESS SPECIALIST) ===

TASK SPECIFICATION
==================
Identity:
  - specialist: cataloging_specialist
  - domain: catalog

Intent:
  - action: CREATE
  - target_entity: product
  - target_id: (none - creating new)

Resolved Context:
  - primary_entity: (none - creating new)
  - related_entities: Blue Pottery Collection (fam_123)
  - images: [https://storage.../vase_img.jpg]
  - text_input: (none - image only)
  - resolved_text: "Create product in Blue Pottery Collection family"
  - conversation_summary: "User batch-adding to Blue Pottery. Last 3: bowl (450), plate (380), cup (320)"
  - relevant_prior_decisions: ["User confirmed Blue Pottery as target family"]
  - company_context: INR currency

Protocols: duplicate_prevention, family_fit_assessment, pricing_discovery
User Hints: likely_family=Blue Pottery, price_range=300-500, style=ceramic
Communication: response_style=efficient, user_state=efficient

=== SPECIALIST EXECUTION (STATELESS) ===

Specialist receives COMPLETE context:
- Knows the target family (no need to ask)
- Knows price range from similar products
- Knows user wants efficiency (no lengthy explanations)
- Runs only specified protocols
- Returns result and forgets everything
```

### 4.10 Correction Flow for Stateless Specialists

**Problem:** Specialist suggests Family A. User says "No, Family B." Specialist has no memory.

**How corrections flow through stateless architecture:**

```
Turn 1: User sends image
Turn 2: PM routes to Specialist --> Specialist suggests Family A
Turn 3: User says "No, it should be Family B"

PM MUST:
1. Recognize this as CORRECTION (not new task)
2. Load original context from PM state
3. Build NEW Task Specification with correction context
4. Re-invoke specialist with explicit rejection
```

**Correction Detection (PM Intelligence Layer):**

```xml
<correction_detection>

## Correction Signals

| Signal | Example | Interpretation |
|--------|---------|----------------|
| Explicit rejection | "No", "Wrong", "Not that" | User rejects suggestion |
| Alternative provided | "It should be X" | User provides correct answer |
| Frustration markers | "I said...", "Again..." | Repeated correction |
| Partial acceptance | "Yes but change X" | Accept with modification |

## PM Response to Correction

### Step 1: IDENTIFY - What's Being Corrected
- Which specialist made the suggestion?
- What specific output is wrong?
- What does user want instead?

### Step 2: BUILD - Correction Context
Add to Task Specification:

```
correction_context:
  original_suggestion: "Family A"
  user_rejection: "No, it should be Family B"
  rejection_reason: [inferred or explicit]
  user_preference: "Family B"
  instruction: "User has explicitly chosen Family B. Do NOT re-evaluate. Apply user's choice."
```

### Step 3: RE-INVOKE - With Override
New Task Specification includes:
- All original context
- correction_context block
- Clear instruction to APPLY user choice, not re-evaluate

### Step 4: UPDATE - PM State
Record user preference for future:
- User prefers [specific choice]
- Add to relevant_prior_decisions for future tasks

</correction_detection>
```

**Specialist Handling of Corrections:**

```xml
<specialist_correction_handling>

## When Task Specification Contains correction_context

### DO:
- Apply user's stated preference directly
- Skip protocol steps that would re-evaluate the corrected decision
- Proceed with remaining protocols using user's choice
- Acknowledge: "Using [user choice] as specified"

### DO NOT:
- Re-run the protocol that was corrected
- Question user's choice
- Suggest alternatives to corrected decision
- Explain why original suggestion was made

### Example:

Task with correction_context:
  correction_context:
    original_suggestion: "Family: PET Kitchen Storage"
    user_preference: "Family: Decorative Ceramics"
    instruction: "Apply user's choice"

Specialist Response:
"Using Decorative Ceramics family as specified.
 Proceeding with pricing protocol..."
[Skip Family Fit protocol, go to Pricing]

</specialist_correction_handling>
```

**Multi-Turn Correction Tracking:**

| Turn | User Action | PM State Update |
|------|-------------|-----------------|
| T1 | Sends image | pending_entity = image context |
| T2 | Sees suggestion | pending_entity += suggestion |
| T3 | Rejects | relevant_prior_decisions += "rejected A" |
| T4 | Accepts modified | user_preferences += learned preference |

### 4.11 Discussion Points

- [ ] How explicit should PM be about routing decisions?
- [ ] Should MEDIUM confidence proceed or always ask?
- [ ] How to handle multi-domain inputs (e.g., "catalog this and create a campaign")?
- [ ] Should routing decisions be logged for learning?

---

## 5. Generic Protocol Patterns

These patterns are **domain-agnostic** and form the foundation for all domain-specific protocols.

### 5.1 Fit Assessment Pattern

**Purpose:** Determine if a SUBJECT belongs with/in a TARGET ENTITY.

**Applicable To:**
- Catalog: Does product fit in this family?
- Marketing: Does campaign fit this audience?
- Procurement: Does supplier fit this requirement?
- Operations: Does resource fit this task?

```xml
<pattern name="Fit Assessment" type="generic">

## ABSTRACT STRUCTURE

### Step 1: IDENTIFY - Target Entity
Identify the [TARGET_ENTITY] being evaluated for fit.
Document: [TARGET_ENTITY_ID], [TARGET_ENTITY_NAME]

### Step 2: QUERY - Qualifying Criteria
**Execute:**
read_data(
  table="[QUALIFYING_CRITERIA_TABLE]",
  filters={"[TARGET_ENTITY_KEY]": [target_id]}
)

**Why This Matters:**
[QUALIFYING_CRITERIA] is THE deciding factor for fit.
Not [COMMON_MISCONCEPTION]. This determines alignment.

**Interpret:**
[HOW_TO_INTERPRET_CRITERIA]

### Step 3: QUERY - Target Entity Examples (Optional)
**Execute:**
read_data(
  table="[SUBJECT_TABLE]",
  filters={"[TARGET_ENTITY_KEY]": [target_id]},
  limit=10
)

**Understand:**
What [SUBJECTS] currently belong to this [TARGET_ENTITY]?
What patterns do they share?

### Step 4: ANALYZE - Subject Attributes
Based on [SUBJECT] attributes, determine:
- [ATTRIBUTE_QUESTION_1]?
- [ATTRIBUTE_QUESTION_2]?
- [ATTRIBUTE_QUESTION_3]?

**Result:**
[SUBJECT] profile based on attributes.

### Step 5: COMPARE - Criteria vs Attributes
Compare Step 2 (target criteria) with Step 4 (subject attributes):
- MATCH: Criteria aligns with attributes
- MISMATCH: Criteria does not align
- PARTIAL: Some alignment, some gaps

**Result:**
Match assessment with specific evidence.

### Step 6: CONCLUDE
**Based on Steps 2-5:**
- If MATCH: [SUBJECT] FITS this [TARGET_ENTITY]
- If MISMATCH: [SUBJECT] needs DIFFERENT [TARGET_ENTITY]
- If PARTIAL: Consider [ALTERNATIVE_OPTIONS]
- If unclear: ESCALATE with evidence gathered

## VERIFICATION
- [ ] Step 2 query was executed (not assumed)
- [ ] Comparison is based on evidence, not intuition
- [ ] Conclusion explicitly references step results

## ANTI-PATTERNS
- Concluding based on surface attributes alone
- Skipping the qualifying criteria query
- Using general knowledge instead of queried data

</pattern>
```

### 5.2 Value Discovery Pattern

**Purpose:** Determine the appropriate VALUE for a SUBJECT based on existing patterns.

**Applicable To:**
- Catalog: What price for this product?
- Marketing: What budget for this campaign?
- Procurement: What cost estimate for this order?
- Operations: What time estimate for this task?

```xml
<pattern name="Value Discovery" type="generic">

## ABSTRACT STRUCTURE

### Step 1: IDENTIFY - Subject Category
Classify [SUBJECT] into a category/tier:
- [TIER_1]: [TIER_1_DESCRIPTION]
- [TIER_2]: [TIER_2_DESCRIPTION]
- [TIER_3]: [TIER_3_DESCRIPTION]

**Result:**
Category classification with reasoning.

### Step 2: QUERY - Similar Entities
**Execute:**
read_data(
  table="[SUBJECT_TABLE]",
  filters={"[CATEGORY_FIELD]": "[category_from_step_1]"},
  columns=["[IDENTIFIER]", "[VALUE_FIELD]", "[GROUPING_FIELD]"],
  limit=15
)

**Why This Matters:**
Similar [SUBJECTS] reveal the established [VALUE] patterns.
This is YOUR data, not general market assumptions.

**Result:**
List of similar [SUBJECTS] with their [VALUES].

### Step 3: AGGREGATE - Discover Range
**Execute:**
aggregate_data(
  table="[SUBJECT_TABLE]",
  filters={"[CATEGORY_FIELD]": "[category_from_step_1]"},
  aggregations={
    "min": "[VALUE_FIELD]",
    "max": "[VALUE_FIELD]",
    "avg": "[VALUE_FIELD]",
    "count": "id"
  }
)

**Understand:**
- What is the [VALUE] range for this category?
- What is typical?
- How many data points support this?

**Result:**
[VALUE] range: [min] - [max], typical: [avg], based on [count] records.

### Step 4: QUERY - Specific Context (If Applicable)
**Execute:**
read_data(
  table="[SUBJECT_TABLE]",
  filters={"[GROUPING_FIELD]": "[specific_group]"},
  columns=["[IDENTIFIER]", "[VALUE_FIELD]"],
  limit=10
)

**Understand:**
Within the specific [GROUPING], what are [VALUES]?

### Step 5: POSITION - Subject Within Range
Given [SUBJECT]'s specific attributes:
- Lower end of range: [WHEN_LOWER]
- Middle of range: [WHEN_MIDDLE]
- Upper end of range: [WHEN_UPPER]

**Result:**
Recommended position within discovered range.

### Step 6: CONCLUDE - Value Recommendation
**Based on Steps 3-5:**
- Recommend specific [VALUE] or range
- [VALUE] MUST be within discovered range from Step 3
- If [SUBJECT] warrants [VALUE] outside range, FLAG for review

**Result:**
"Recommended [VALUE]: [X] (within [category] range of [min]-[max])"

## VERIFICATION
- [ ] Step 2 query executed with actual results
- [ ] Recommendation is within discovered range
- [ ] Reasoning connects category --> range --> specific recommendation

## ANTI-PATTERNS
- Using general knowledge instead of queried patterns
- Recommending value outside discovered range without flagging
- Skipping the aggregate step

</pattern>
```

### 5.3 New Entity Pattern

**Purpose:** Determine if a NEW ENTITY should be created, and if so, define it properly.

**Applicable To:**
- Catalog: Should we create a new product family?
- Marketing: Should we create a new audience segment?
- Procurement: Should we create a new supplier category?
- Operations: Should we create a new process type?

```xml
<pattern name="New Entity" type="generic">

## ABSTRACT STRUCTURE

### Step 1: VERIFY - Existing Entities Exhausted
**Execute:**
read_data(
  table="[ENTITY_TABLE]",
  columns=["id", "name", "description", "[CATEGORY_FIELD]"],
  limit=50
)

**Result:**
Complete list of existing [ENTITIES].

### Step 2: EVALUATE - Each Candidate Entity
For each [ENTITY] that SEEMS like it might fit:
- State [ENTITY] name
- Apply Fit Assessment (or reason through fit)
- Document why it doesn't fit

**Result:**
Documented evaluation of each candidate [ENTITY].

### Step 3: ARTICULATE - The Gap
Based on Steps 1-2, articulate:
- What [QUALIFYING_CRITERIA] is not served by existing [ENTITIES]?
- What [SUBJECT] type has no home?
- Why is this gap meaningful (not just minor variation)?

**Result:**
Clear gap statement: "No [ENTITY] serves [criteria] for [subject_type]"

### Step 4: DEFINE - New Entity Proposal
Define the new [ENTITY]:
- Name: [Descriptive, meaningful name]
- [QUALIFYING_CRITERIA]: [Who/what this serves]
- [SUBJECT] Types: [What belongs here]
- [CATEGORY]: [Tier/positioning]
- Differentiation: [How it differs from closest existing]

**Result:**
Complete new [ENTITY] definition.

### Step 5: VALIDATE - Entity Viability
Answer viability questions:
- Would at least [MINIMUM_COUNT] [SUBJECTS] fit this [ENTITY]?
- Is the [QUALIFYING_CRITERIA] distinct and real?
- Does the name clearly communicate purpose?

**Result:**
Viability assessment.

### Step 6: CONCLUDE
**Based on Steps 1-5:**
- If gap is clear AND viable: RECOMMEND new [ENTITY] with full definition
- If gap is marginal: Consider sub-entity or alternative
- If viability uncertain: ESCALATE with findings

## VERIFICATION
- [ ] All existing [ENTITIES] were queried (Step 1 executed)
- [ ] Each rejected [ENTITY] has documented reasoning
- [ ] New [ENTITY] has complete definition
- [ ] Viability questions answered

## ANTI-PATTERNS
- Creating new [ENTITY] without exhausting existing options
- Defining [ENTITY] based on single [SUBJECT] (entity of one)
- Creating [ENTITY] based on surface attributes alone

</pattern>
```

### 5.4 Duplicate Prevention Pattern

**Purpose:** Verify a SUBJECT doesn't already exist before creating.

**Applicable To:**
- Any domain with entity creation

```xml
<pattern name="Duplicate Prevention" type="generic">

## ABSTRACT STRUCTURE

### Step 1: SEARCH - Exact Identifier Match
**Execute:**
read_data(
  table="[SUBJECT_TABLE]",
  search_patterns={"[IDENTIFIER_FIELD]": "[exact_value]"}
)

**Result:**
Any exact matches.

### Step 2: SEARCH - Fuzzy Identifier Match
**Execute:**
read_data(
  table="[SUBJECT_TABLE]",
  search_patterns={"[IDENTIFIER_FIELD]": "%[key_words]%"}
)

**Result:**
Similar identifier matches.

### Step 3: SEARCH - Attribute Combination Match
**Execute:**
read_data(
  table="[SUBJECT_TABLE]",
  filters={
    "[ATTRIBUTE_1]": "[value_1]",
    "[ATTRIBUTE_2]": "[value_2]"
  },
  search_patterns={"[IDENTIFIER_FIELD]": "%[variant]%"}
)

**Result:**
Attribute-based matches.

### Step 4: ASSESS - Each Potential Match
For each potential match from Steps 1-3:
- Is this the SAME [SUBJECT]? (True duplicate)
- Is this a VARIANT of existing? (Should add variant, not new)
- Is this SIMILAR but distinct? (OK to create new)

**Result:**
Assessment of each match.

### Step 5: CONCLUDE
**Based on Step 4:**
- If TRUE DUPLICATE: DO NOT CREATE, return existing
- If should be VARIANT: DO NOT CREATE new, add variant
- If SIMILAR but distinct: OK to proceed
- If NO matches: OK to proceed

## VERIFICATION
- [ ] All three search types executed
- [ ] Each potential match evaluated
- [ ] Decision documented

## ANTI-PATTERNS
- Skipping duplicate check
- Only checking exact match
- Creating duplicate hoping it's caught later

</pattern>
```

### 5.5 Domain Orientation Pattern

**Purpose:** Understand the current state of a domain before making decisions.

**Applicable To:**
- Any domain when context is unclear or task is complex

```xml
<pattern name="Domain Orientation" type="generic">

## ABSTRACT STRUCTURE

### Step 1: DISCOVER - Entity Landscape
**Execute:**
aggregate_data(
  table="[ENTITY_TABLE]",
  group_by=["[CATEGORY_FIELD]"],
  aggregations={"count": "id"}
)

**Understand:**
- How many [ENTITIES] exist at each [CATEGORY]?
- What's the distribution?
- Where are gaps?

**Result:**
[ENTITY] distribution across [CATEGORIES].

### Step 2: DISCOVER - Value Patterns
**Execute:**
aggregate_data(
  table="[SUBJECT_TABLE]",
  group_by=["[CATEGORY_FIELD]"],
  aggregations={
    "min": "[VALUE_FIELD]",
    "max": "[VALUE_FIELD]",
    "avg": "[VALUE_FIELD]",
    "count": "id"
  }
)

**Understand:**
- What are actual [VALUE] ranges per [CATEGORY]?
- This is YOUR data, not assumptions.

**Result:**
[VALUE] ranges by [CATEGORY].

### Step 3: DISCOVER - Entity Structure
**Execute:**
read_data(
  table="[ENTITY_TABLE]",
  columns=["name", "[CATEGORY_FIELD]", "description"],
  limit=50
)

**Understand:**
- What [ENTITIES] exist?
- How are they organized?
- What do they contain?

**Result:**
[ENTITY] inventory.

### Step 4: DISCOVER - Qualifying Criteria
**Execute:**
read_data(
  table="[QUALIFYING_CRITERIA_TABLE]",
  columns=["[ENTITY_KEY]", "description"],
  relations=["[ENTITY_RELATION]"],
  limit=50
)

**Understand:**
- What [CRITERIA] exist for each [ENTITY]?
- What patterns emerge?

**Result:**
[CRITERIA] map.

### Step 5: SYNTHESIZE - Mental Model
Based on Steps 1-4, articulate:
- The structure of this domain
- The established patterns
- Any gaps or opportunities

**Result:**
Mental model of domain state.

## WHEN TO USE
- Starting work in unfamiliar area
- Before creating new [ENTITY]
- When [VALUE] patterns are unclear
- Complex tasks requiring context

</pattern>
```

---

## 6. Tool Mastery Protocols

Tool Mastery Protocols teach **power patterns** and **efficiency rules** for each tool. These apply to ALL domains.

### 6.1 read_data Mastery

```xml
<protocol name="read_data Mastery" domain="tools" type="mastery">

## PURPOSE
Master read_data for powerful, efficient queries across any domain.

## POWER PATTERNS

### Pattern 1: Relationship Loading
**Problem:** Multiple queries to get related data.
**Solution:** Use relations parameter.

Instead of:
  records = read_data(table="subjects", filters={...})
  for each record:
    related = read_data(table="entities", filters={"id": record.entity_id})

Do:
  read_data(
    table="subjects",
    filters={...},
    relations=["entity"]  -- Get related data in SAME call
  )

**Benefit:** One call instead of N+1 calls.

### Pattern 2: Filter + Search Combo
**Problem:** Broad search returns too much noise.
**Solution:** Combine filters (exact) with search_patterns (fuzzy).

Instead of:
  read_data(table="subjects", search_patterns={"name": "%keyword%"})

Do:
  read_data(
    table="subjects",
    filters={"category": "specific"},      -- Narrow first (fast)
    search_patterns={"name": "%keyword%"}  -- Then search (slower)
  )

**Benefit:** Smaller, more relevant result set.

### Pattern 3: Column Selection
**Problem:** Fetching all columns when only a few needed.
**Solution:** Specify columns parameter.

Instead of:
  read_data(table="subjects")  -- Gets ALL columns

Do:
  read_data(
    table="subjects",
    columns=["id", "name", "value", "category"]  -- Only what you need
  )

**Benefit:** Faster, less noise, clearer results.

### Pattern 4: Count Before Fetch
**Problem:** Fetching many records just to check existence.
**Solution:** Use count_only first.

Instead of:
  results = read_data(table="subjects", filters={...})
  if len(results) > 0: ...

Do:
  count = read_data(table="subjects", filters={...}, count_only=True)
  if count > 0:
    results = read_data(table="subjects", filters={...}, limit=needed)

**Benefit:** Avoid fetching 1000 records for existence check.

### Pattern 5: Strategic Limits
**Problem:** Fetching too much or too little.
**Solution:** Match limit to purpose.

| Purpose | Recommended Limit |
|---------|-------------------|
| Existence check | count_only=True |
| Pattern discovery | limit=15-20 |
| Specific lookup | limit=5-10 |
| Full analysis | limit based on need |

## EFFICIENCY RULES

1. **Never query same table twice in one reasoning step**
   Plan data needs, fetch once.

2. **Use filters before search_patterns**
   Filters use indexes (fast). Search is pattern-based (slower).

3. **Leverage relations for related data**
   One call with relations beats multiple calls.

4. **Select only needed columns**
   Reduces data transfer and noise.

5. **Use appropriate limits**
   Don't fetch 100 when you need 10.

## ANTI-PATTERNS
- Fetching all records then filtering in reasoning
- Multiple queries for data available in one call
- Ignoring columns parameter
- Not using count_only for existence checks
- Using search_patterns alone without filters

</protocol>
```

### 6.2 aggregate_data Mastery

```xml
<protocol name="aggregate_data Mastery" domain="tools" type="mastery">

## PURPOSE
Master aggregate_data for pattern discovery and statistics across any domain.

## WHEN TO USE aggregate_data vs read_data

| Need | Use |
|------|-----|
| Actual records | read_data |
| Counts, sums, averages | aggregate_data |
| Range discovery | aggregate_data |
| Distribution analysis | aggregate_data |
| Specific examples | read_data |
| Pattern confirmation | aggregate_data |

## POWER PATTERNS

### Pattern 1: Range Discovery
**Purpose:** Find min/max/avg for a value field.

aggregate_data(
  table="subjects",
  filters={"category": "target"},
  aggregations={
    "min": "value_field",
    "max": "value_field",
    "avg": "value_field",
    "count": "id"
  }
)

**Use for:** Price ranges, budget ranges, time estimates.

### Pattern 2: Distribution Analysis
**Purpose:** Understand how entities are distributed.

aggregate_data(
  table="subjects",
  group_by=["category"],
  aggregations={"count": "id"}
)

**Use for:** Entity counts per category, tier distribution.

### Pattern 3: Multi-Dimension Grouping
**Purpose:** Cross-tabulate two dimensions.

aggregate_data(
  table="subjects",
  group_by=["category", "subcategory"],
  aggregations={
    "count": "id",
    "avg": "value_field"
  }
)

**Use for:** Complex pattern analysis.

### Pattern 4: Filtered Aggregation
**Purpose:** Statistics for specific subset.

aggregate_data(
  table="subjects",
  filters={"status": "active", "category": "target"},
  aggregations={"sum": "value_field", "count": "id"}
)

**Use for:** Scoped statistics.

## EFFICIENCY RULES

1. **Use aggregate for patterns, read for records**
   Don't fetch 1000 records to count them.

2. **Filter before aggregating**
   Narrower data = faster aggregation.

3. **Group by meaningful dimensions**
   Choose grouping that reveals actionable patterns.

4. **Combine multiple aggregations in one call**
   Get min, max, avg, count together.

## ANTI-PATTERNS
- Using read_data then counting in reasoning
- Multiple aggregate calls for same data
- Aggregating without filters (entire table)
- Using aggregate when you need actual records

</protocol>
```

### 6.3 write_data Mastery

```xml
<protocol name="write_data Mastery" domain="tools" type="mastery">

## PURPOSE
Master write_data for safe, verified mutations across any domain.

## CRITICAL: ALWAYS BEFORE write_data

### Pre-Write Checklist
1. **Verify schema** - inspect_schema to confirm fields and types
2. **Check duplicates** - Duplicate Prevention Pattern
3. **Prepare complete data** - Fill ALL relevant fields
4. **Plan verification** - How will you confirm success?

## POWER PATTERNS

### Pattern 1: Complete Context
**Always provide full context in write_data calls:**

write_data(
  table="subjects",
  operation="create",
  data={...},
  goal="[What you're trying to achieve]",
  reasoning="[Why this data is correct]",
  impact="[What this affects]",
  hitl_summary="[Human-readable summary for approval]"
)

**Why:** HITL approval requires understanding. Give complete context.

### Pattern 2: Verify After Write
**Always verify mutations succeeded:**

1. Execute write_data
2. If approved, query to verify:
   read_data(table="subjects", filters={"id": [created_id]})
3. Confirm data matches expectations

### Pattern 3: Batch Awareness
**Understand when batch vs single:**

| Scenario | Approach |
|----------|----------|
| Single record, needs approval | Single write_data |
| Multiple related records | Consider transaction |
| Independent records | Can be separate calls |

## EFFICIENCY RULES

1. **Never write without verifying schema first**
   One inspect_schema call prevents many errors.

2. **Never write without duplicate check**
   Duplicate Prevention Pattern is mandatory.

3. **Complete data > partial data**
   Fill all relevant fields. Don't leave blanks.

4. **HITL summary is critical**
   User approves based on summary. Make it clear.

## ANTI-PATTERNS
- Writing without checking for duplicates
- Incomplete data with blank fields
- No verification after write
- Vague HITL summary

</protocol>
```

### 6.4 inspect_schema Mastery

```xml
<protocol name="inspect_schema Mastery" domain="tools" type="mastery">

## PURPOSE
Master inspect_schema for structure understanding across any domain.

## WHEN TO USE

| Scenario | Use inspect_schema |
|----------|-------------------|
| First time working with table | Yes |
| Before write_data | Yes |
| Unclear what columns exist | Yes |
| Need to understand relationships | Yes |
| Already know schema well | Skip |

## POWER PATTERNS

### Pattern 1: Full Table Discovery
**First time with a table:**

inspect_schema(table="target_table")

**Returns:** All columns, types, relationships, constraints.

### Pattern 2: Relationship Discovery
**Understand how tables connect:**

inspect_schema(table="subjects")
-- Note: Check "relationships" in output
-- Shows: what tables are related and how

### Pattern 3: Before Write Verification
**Always before write_data:**

schema = inspect_schema(table="target")
-- Verify: required fields, data types, constraints
-- Then: prepare data that matches schema

## EFFICIENCY RULES

1. **Cache mentally** - Don't call repeatedly for same table in one session
2. **Check relationships** - Understand connections for relations parameter
3. **Note constraints** - Required fields, unique constraints

## ANTI-PATTERNS
- Calling inspect_schema repeatedly for same table
- Ignoring relationship information
- Writing without schema verification

</protocol>
```

---

## 7. Protocol Creation Guide

Use this guide to create protocols for ANY new domain.

### 7.1 Protocol Creation Template

```xml
<protocol_creation_template>

## STEP 1: Identify Key Decisions

What decisions does this domain's specialist make?

| Decision | Description | Frequency |
|----------|-------------|-----------|
| Decision A | [what it determines] | [how often] |
| Decision B | [what it determines] | [how often] |
| Decision C | [what it determines] | [how often] |

## STEP 2: Map Decisions to Generic Patterns

| Domain Decision | Generic Pattern | Why This Pattern |
|-----------------|-----------------|------------------|
| Decision A | Fit Assessment | Determines if X belongs with Y |
| Decision B | Value Discovery | Determines what value X should have |
| Decision C | New Entity | Determines if new X should be created |

## STEP 3: Identify Domain-Specific Elements

**Entities (Tables/Concepts):**
- Primary entity: [e.g., families, audiences, suppliers]
- Subject entity: [e.g., products, campaigns, orders]
- Qualifying entity: [e.g., customer_segments, audience_profiles]

**Values:**
- Primary value: [e.g., price, budget, cost]
- Secondary values: [e.g., quantity, duration]

**Relationships:**
- [Entity A] --> [Entity B]: [relationship type]
- [Entity B] --> [Entity C]: [relationship type]

**Categories/Tiers:**
- Tier 1: [name] - [description]
- Tier 2: [name] - [description]
- Tier 3: [name] - [description]

**Qualifying Criteria:**
- What determines fit: [criteria description]
- Where stored: [table/field]

## STEP 4: Instantiate Protocols

For each decision, take the generic pattern and:

1. Replace [PLACEHOLDERS] with domain entities
2. Add domain-specific "Why This Matters" explanations
3. Add domain-specific "How to Interpret" guidance
4. Add domain-specific anti-patterns
5. Add domain-specific verification checks

## STEP 5: Create Domain Orientation Protocol

What must agent understand about this domain's state?

- Entity landscape: [what entities, how distributed]
- Value patterns: [what values, what ranges]
- Relationships: [what connects to what]
- Segments/Tiers: [what categories exist]

## STEP 6: Write Business Context

Define the business context that will be embedded in the prompt:

<business_context>
## [Domain Name] Business Context

### Tiers/Categories
- [Tier 1]: [Definition, characteristics]
- [Tier 2]: [Definition, characteristics]
- [Tier 3]: [Definition, characteristics]

### Key Relationships
- [Entity A] determines [Entity B]
- [Qualifying Criteria] is primary factor for [Decision Type]

### Common Misconceptions
- NOT: [what people assume]
- ACTUALLY: [what's true in this business]
</business_context>

</protocol_creation_template>
```

### 7.2 Protocol Quality Checklist

For each protocol, verify:

**Structure:**
- [ ] All steps have ACTION VERB + description
- [ ] Each step has Execute and Result sections
- [ ] Steps are numbered and sequential
- [ ] Verification section exists
- [ ] Anti-patterns documented

**Content:**
- [ ] "Why This Matters" explains business significance
- [ ] "How to Interpret" provides domain-specific guidance
- [ ] Placeholders replaced with domain entities
- [ ] Queries are specific and executable
- [ ] Conclusions map to evidence from steps

**Integration:**
- [ ] Protocol references available tools
- [ ] Protocol fits agent's role (analyst/specialist)
- [ ] Escalation path is clear
- [ ] HITL requirements noted if applicable

---

## 8. Domain Instantiation

### 8.1 Instantiation Process

```
GENERIC PATTERN
      |
      v
+------------------+
| Replace          |
| - [ENTITY]       |
| - [SUBJECT]      |
| - [VALUE]        |
| - [CRITERIA]     |
+------------------+
      |
      v
+------------------+
| Add Domain       |
| - Why This Matters
| - How to Interpret
| - Anti-patterns  |
+------------------+
      |
      v
DOMAIN PROTOCOL
```

### 8.2 Placeholder Reference

| Placeholder | Meaning | Examples |
|-------------|---------|----------|
| `[ENTITY]` | Grouping/container | family, audience, supplier, process |
| `[SUBJECT]` | Item being evaluated | product, campaign, order, task |
| `[VALUE]` | Numeric measure | price, budget, cost, estimate |
| `[CRITERIA]` | What determines fit | customer_segment, audience_profile, qualifications |
| `[CATEGORY]` | Tier/positioning | utility/decorative/premium, awareness/conversion |
| `[IDENTIFIER]` | Name/code field | name, title, sku, code |

---

## 9. Catalog Domain Example

This section shows the generic patterns instantiated for the Catalog domain.

### 9.1 Catalog Domain Elements

| Element | Catalog Instantiation |
|---------|----------------------|
| Entity | product_families |
| Subject | products |
| Value | price |
| Criteria | customer_segments |
| Category | positioning (utility, decorative, premium) |
| Identifier | name |

### 9.2 Catalog Business Context

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

</business_context>
```

### 9.3 Family Fit Protocol (Instantiated)

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
- MATCH: Same customer type
- MISMATCH: Different customer type
- PARTIAL: Overlapping but distinct

**Result:**
Match assessment with evidence.

### Step 6: COMPARE - Product Cohesion
Compare Step 3 (family's products) with this product:
- Would a customer browsing the family naturally consider this?
- Does style/positioning align?
- Does price range align?

**Result:**
Cohesion assessment.

### Step 7: CONCLUDE
**Based on Steps 5 and 6:**
- MATCH + Cohesive: Product FITS this family
- MISMATCH on customer: Product needs DIFFERENT family
- Match but not cohesive: Consider sub-family

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

### 9.4 Pricing Protocol (Instantiated)

```xml
<protocol name="Pricing Protocol" domain="catalog" type="decision">

## PURPOSE
Determine appropriate price for a product based on catalog patterns.

## STEPS

### Step 1: IDENTIFY - Product Positioning
Classify product positioning (see business_context):
- UTILITY: Functional, everyday, bulk
- DECORATIVE: Aesthetic, gift-worthy, display
- PREMIUM: Luxury, artisan, statement

**Result:**
Positioning with reasoning.

### Step 2: QUERY - Similar Products
**Execute:**
read_data(
  table="products",
  filters={"positioning": "[from_step_1]"},
  columns=["name", "price", "family_id"],
  relations=["family"],
  limit=15
)

**Why This Matters:**
Similar products reveal YOUR established price patterns.
Not general market knowledge.

**Result:**
Similar products with prices.

### Step 3: AGGREGATE - Price Range
**Execute:**
aggregate_data(
  table="products",
  filters={"positioning": "[from_step_1]"},
  aggregations={
    "min": "price",
    "max": "price",
    "avg": "price",
    "count": "id"
  }
)

**Understand:**
What is the ACTUAL range for this positioning in YOUR catalog?

**Result:**
Price range: Rs [min] - [max], avg Rs [avg], based on [count] products.

### Step 4: POSITION - Within Range
Given product's specific attributes:
- Lower end: Basic, simple, functional
- Middle: Standard, typical for category
- Upper end: Premium features, higher quality

**Result:**
Position recommendation.

### Step 5: CONCLUDE
**Based on Steps 3-4:**
- Recommend specific price
- Price MUST be within discovered range
- If outside range warranted, FLAG for review

**Result:**
"Recommended: Rs [X] (within range Rs [min]-[max])"

## VERIFICATION
- [ ] Step 2 query executed
- [ ] Step 3 aggregate executed
- [ ] Recommendation within range
- [ ] Not using general market assumptions

</protocol>
```

### 9.5 Example: Protocol Execution

```
TASK: Determine family fit for printed floral PET jar

PROTOCOL SELECTED: Family Fit Protocol

STEP 1: IDENTIFY - Candidate Family
Candidate: "PET Kitchen Storage" (fam-001)
Source: Analyst suggestion based on material match

STEP 2: QUERY - Customer Segment
Executed: read_data(table="customer_segments", filters={"family_id": "fam-001"})
Result: "Households organizing kitchen pantry - utility-focused buyers"

STEP 3: QUERY - Family Products
Executed: read_data(table="products", filters={"family_id": "fam-001"}, limit=10)
Result: Plain containers, bulk storage, organizers. Price range Rs 25-60.

STEP 4: ANALYZE - Product's Customer
Product attributes: Printed floral design, decorative finish, gift packaging
Target customer: Gift buyers, home decor enthusiasts
NOT: Pantry organizers

STEP 5: COMPARE - Customer Match
Family: Utility buyers (pantry organization)
Product: Decorative buyers (gifting, display)
Assessment: MISMATCH - fundamentally different customer intent

STEP 6: COMPARE - Cohesion
Family products: Plain, functional, budget
This product: Decorative, designed, mid-premium
Assessment: Would NOT be browsed together

STEP 7: CONCLUDE
MISMATCH + Not Cohesive = Product needs DIFFERENT FAMILY

--> Trigger: New Entity Pattern (or search for decorative family)
```

---

## 10. Other Domains (Future)

The same patterns apply to all domains in AutifyME's multi-domain architecture.

**To create protocols for a new domain:**

1. **Map domain elements** to generic placeholders:
   | Element | Example (Marketing) | Example (Operations) |
   |---------|---------------------|----------------------|
   | Entity | audience_segments | processes |
   | Subject | campaigns | orders |
   | Value | budget | priority |
   | Criteria | audience_profiles | requirements |

2. **Define business context** (tiers, relationships, misconceptions)

3. **Instantiate generic patterns** with domain-specific:
   - Table names
   - Field names
   - Interpretation guidance
   - Anti-patterns

4. **Add domain-specific protocols** for unique decisions

**See Protocol Creation Guide (Section 7) for detailed instructions.**

---

## 11. Integration with Agent Architecture

### 11.1 Protocol Location

**Recommended:** Protocols embedded in agent prompts.

```
agents/src/autifyme_agents/prompts/
├── project_manager.prompt
│   └── Orchestration Protocols
├── analysts/
│   └── [domain]_analyst.prompt
│       └── Exploration Protocols for domain
└── specialists/
    └── [domain]_specialist.prompt
        └── Decision Protocols for domain
        └── Tool Mastery Protocols
        └── Domain Orientation Protocol
        └── Business Context
```

### 11.2 Prompt Structure

```xml
<identity>
[Agent identity and role]
</identity>

<business_context>
[Domain-specific tiers, relationships, misconceptions]
</business_context>

<tools>
[Available tools]
</tools>

<tool_mastery>
[Tool Mastery Protocols - power patterns, efficiency rules]
</tool_mastery>

<protocols>
[Domain Decision Protocols]
[Domain Orientation Protocol]
</protocols>

<protocol_usage>
## How to Use Protocols

1. Identify which protocol applies to current task
2. Execute ALL steps in order - do not skip
3. Document results of each step
4. Reach conclusion based on step results
5. If no protocol fits, state this and escalate

## The Balance: Protocols + Intelligence

You are an **AUTONOMOUS DOMAIN EXPERT** who uses protocols as your reasoning framework.

**Protocols provide:**
- WHAT to investigate (the steps)
- WHICH queries to run (tool calls)
- HOW to interpret data types (domain context)

**Your intelligence provides:**
- HOW to interpret specific results (judgment)
- WHEN edge cases require escalation (recognition)
- HOW to communicate findings (adaptation)

**The balance:**
- Protocol steps are MANDATORY - execute all of them
- Interpretation is INTELLIGENT - apply domain expertise to actual results
- Escalation is AUTONOMOUS - recognize when you're uncertain

**Anti-pattern:** Skipping steps because "I already know the answer"
**Anti-pattern:** Blindly following steps without intelligent interpretation
**Correct:** Execute steps rigorously, interpret results intelligently
</protocol_usage>

<examples>
[Examples showing protocol execution]
</examples>
```

---

## 12. Protocol Composition Framework

Tasks rarely require a single protocol. This section defines how protocols chain together.

### 12.1 The Problem

```
Task: "Add this ceramic vase to catalog"

Required Protocols:
1. Duplicate Prevention (does it exist?)
2. Domain Orientation (understand families)
3. Family Fit (which family?)
4. If no fit: New Entity (create family?)
5. Pricing (what price?)

Current doc doesn't address this sequencing.
```

### 12.2 Composition Patterns

```xml
<protocol_composition>

## Sequential Chain
Protocol A --> Protocol B --> Protocol C
Use when: Each protocol depends on previous conclusion

Example: New Product Cataloging
  1. Duplicate Prevention --> If no duplicate, continue
  2. Domain Orientation --> Understand family landscape
  3. Family Fit --> Evaluate candidate families
  4. If MISMATCH: New Entity --> Create new family
  5. Pricing --> Determine price
  6. write_data --> Save product

## Conditional Branch
If A.conclusion == X: Protocol B
Else: Protocol C

Example: Family Assignment
  If Fit Assessment == MATCH: Proceed to Pricing
  Else If Fit Assessment == PARTIAL: Explore similar families
  Else: Trigger New Entity Protocol

## Parallel Execution
Protocol A || Protocol B (independent)
Merge results for decision

Example: Product Validation
  Duplicate Prevention || Schema Validation
  Both must pass before proceeding

</protocol_composition>
```

### 12.3 Standard Compositions by Task Type

| Task | Protocol Sequence |
|------|-------------------|
| New Product | Duplicate --> Orientation --> Fit --> (New Entity?) --> Pricing --> Write |
| Update Product | Read Current --> Validate Changes --> Write |
| Family Assignment | Orientation --> Fit --> (New Entity?) |
| Price Recommendation | Orientation --> Value Discovery |
| Bulk Import | For each: Duplicate --> Fit --> Pricing --> Write |

### 12.4 Agent-Driven Selection (Recommended Approach)

Instead of complex retrieval logic, the AGENT selects protocols:

```xml
<protocol_selection>

## Protocol Selection (EXECUTE FIRST)

Before any domain task, determine which protocol(s) apply:

### Step 1: Classify Task Type
What is the primary decision being made?

| Task Pattern | Primary Protocol |
|--------------|------------------|
| "Does X belong in/with Y?" | Fit Assessment |
| "What should X cost/value?" | Value Discovery |
| "Should we create new Y?" | New Entity |
| "Does X already exist?" | Duplicate Prevention |
| "What's the current state?" | Domain Orientation |

### Step 2: Identify Secondary Protocols
Does task require additional protocols?

### Step 3: Determine Sequence
Order by dependency (see 12.3)

### Result
State: "Applying protocols: [list] in sequence: [order]"
Then execute each protocol in order.

</protocol_selection>
```

### 12.5 PARTIAL Result Branching

**Problem:** Fit Assessment returns PARTIAL for multiple candidates. What now?

```
Fit Assessment Results:
- Family A: PARTIAL (70% match - customer aligns, price range differs)
- Family B: PARTIAL (65% match - material aligns, customer differs)
- Family C: PARTIAL (60% match - use case aligns, quality tier differs)

No MATCH. Multiple PARTIAL. What's the decision path?
```

**PARTIAL Branching Logic:**

```xml
<partial_branching>

## Decision Tree for PARTIAL Results

### Case 1: Single PARTIAL (others MISMATCH)
Decision: Proceed with PARTIAL candidate
Confidence: MEDIUM
Action: Continue chain, flag for HITL review

### Case 2: Multiple PARTIAL (ranked)
If one PARTIAL significantly higher (>10% gap):
  Decision: Proceed with highest-ranked
  Confidence: MEDIUM
  Action: Continue chain, note alternatives in HITL

If PARTIALs are close (<10% gap):
  Decision: STOP - present options to user
  Confidence: LOW
  Action: User selects before continuing

### Case 3: No MATCH, No PARTIAL (all MISMATCH)
Decision: Trigger New Entity Protocol
Confidence: N/A (new protocol)
Action: Create new entity OR escalate

### Case 4: PARTIAL + Correction Context
If user previously rejected a PARTIAL candidate:
  Decision: Exclude rejected, evaluate remaining
  Confidence: Depends on remaining candidates

## Scoring PARTIAL Results

When Fit Assessment yields PARTIAL, calculate score:

| Factor | Weight | Scoring |
|--------|--------|---------|
| Customer segment match | 40% | 0-100 |
| Price range alignment | 25% | 0-100 |
| Existing product cohesion | 20% | 0-100 |
| Use case alignment | 15% | 0-100 |

Total score determines PARTIAL ranking.

## Example: Multiple PARTIAL Handling

```
Fit Assessment for "Decorative Ceramic Vase"

Candidate A: "Kitchen Storage"
  - Customer: 30% (utility vs decorative buyers)
  - Price: 80% (within range)
  - Cohesion: 40% (functional items vs display)
  - Use case: 50% (storage vs display)
  Score: 30*.4 + 80*.25 + 40*.2 + 50*.15 = 47.5%
  Result: MISMATCH

Candidate B: "Decorative Ceramics"
  - Customer: 85% (decorative/gift buyers)
  - Price: 70% (slightly above typical)
  - Cohesion: 80% (similar display items)
  - Use case: 90% (display purpose)
  Score: 85*.4 + 70*.25 + 80*.2 + 90*.15 = 81%
  Result: PARTIAL (>60%, <90%)

Candidate C: "Gift Items"
  - Customer: 75% (gift buyers)
  - Price: 85% (gift price range)
  - Cohesion: 60% (mixed gift items)
  - Use case: 70% (gifting purpose)
  Score: 75*.4 + 85*.25 + 60*.2 + 70*.15 = 74%
  Result: PARTIAL

Decision:
  B (81%) vs C (74%) = 7% gap < 10%
  Action: Present options to user

  "This vase could fit in:
   1. Decorative Ceramics (81% match) - best customer/use alignment
   2. Gift Items (74% match) - good price/gifting alignment
   Which family would you prefer?"
```

</partial_branching>
```

### 12.6 Discussion Points

- [ ] Should composition be agent-driven (prompt) or system-driven (code)?
- [ ] How explicit should sequencing guidance be?
- [ ] Should we enforce composition rules or leave flexible?

---

## 13. Confidence Scoring Framework

Protocols should conclude with confidence levels, not just binary outcomes.

### 13.1 The Problem

```
Step 5: COMPARE - Customer Match
Family customer: "Gift buyers and home organizers"
Product customer: "Gift buyers" (partial match)

Result: MATCH? PARTIAL? MISMATCH?
Protocol doesn't provide decision criteria.
```

### 13.2 Confidence Levels

| Level | Criteria | Action |
|-------|----------|--------|
| **HIGH (90%+)** | Multiple data points align, no contradictions | Proceed autonomously |
| **MEDIUM (60-90%)** | Most evidence aligns, some gaps | Proceed with HITL flag |
| **LOW (<60%)** | Limited data, significant inference, contradictions | Present options, human decides |

### 13.3 Confidence Determination

```xml
<confidence_framework>

## Determining Confidence

### HIGH Confidence Indicators
- Query returned 5+ supporting data points
- All evidence aligns with conclusion
- No contradictory signals
- Pattern matches established precedent

### MEDIUM Confidence Indicators
- Query returned 2-4 supporting data points
- Most evidence aligns, minor gaps
- Some inference required
- Pattern partially matches precedent

### LOW Confidence Indicators
- Query returned 0-1 data points
- Evidence is mixed or contradictory
- Significant inference required
- No clear precedent exists

## In Protocol Conclusions

### Step N: CONCLUDE with Confidence

**Conclusion:** [MATCH/MISMATCH/PARTIAL]
**Confidence:** [HIGH/MEDIUM/LOW]
**Evidence:** [What supports this conclusion]
**Gaps:** [What's uncertain or missing]

**Action Based on Confidence:**
- HIGH: Proceed to next step/protocol
- MEDIUM: Proceed but flag for HITL review
- LOW: STOP. Present finding + options to user. Do NOT proceed autonomously.

</confidence_framework>
```

### 13.4 Chained Confidence Handling

**Problem:** Task requires multiple protocols. Each has confidence. How do they combine?

```
Protocol Chain: Duplicate --> Fit --> Pricing
Confidence:     HIGH        MEDIUM   HIGH

What's the overall confidence?
```

**Rules for Chained Confidence:**

```xml
<chained_confidence>

## Rule 1: Chain Stops at LOW
If ANY protocol concludes with LOW confidence:
- STOP the chain immediately
- Present options to user
- Do NOT proceed to subsequent protocols
- User must resolve before continuing

Example:
  Duplicate: HIGH --> continue
  Fit: LOW --> STOP
  Pricing: not executed

  "I found possible family matches but I'm uncertain:
   Option A: Decorative Ceramics (60% match)
   Option B: Kitchen Storage (55% match)
   Option C: Create new family
   Please select before I determine pricing."

## Rule 2: MEDIUM Accumulates
If protocols have MEDIUM confidence:
- Continue executing chain
- ACCUMULATE all MEDIUM decisions
- Present combined HITL review at end
- User reviews all uncertain decisions together

Example:
  Duplicate: HIGH --> continue
  Fit: MEDIUM (family choice) --> continue, flag
  Pricing: MEDIUM (price point) --> continue, flag

  Combined HITL:
  "Please review these decisions:
   1. Family: Decorative Ceramics (75% match) [Confirm/Change]
   2. Price: Rs 120 (within range, mid-point) [Confirm/Change]"

## Rule 3: Overall Confidence = Minimum
Final confidence for the task = lowest confidence in chain

| Protocol Confidences | Overall | Action |
|---------------------|---------|--------|
| HIGH, HIGH, HIGH | HIGH | Proceed autonomously |
| HIGH, MEDIUM, HIGH | MEDIUM | Combined HITL at end |
| HIGH, HIGH, LOW | LOW | Stop at LOW, resolve first |
| MEDIUM, MEDIUM, MEDIUM | MEDIUM | Combined HITL at end |

## Rule 4: Sequential Dependency
If Protocol B depends on Protocol A's output:
- LOW in A = cannot meaningfully run B
- MEDIUM in A = run B but note uncertainty inherited

Example:
  Fit (MEDIUM) --> chose Family X
  Pricing depends on family's price range
  Pricing inherits: "Note: Family assignment is uncertain (MEDIUM).
                     Price range based on assumed family."

</chained_confidence>
```

**Confidence Propagation in Task Specification:**

```
protocols_confidence:
  - protocol: duplicate_prevention
    confidence: HIGH
    result: "No duplicates found"
  - protocol: family_fit
    confidence: MEDIUM
    result: "Decorative Ceramics (75% match)"
    uncertainty: "Partial customer segment match"
  - protocol: pricing
    confidence: HIGH
    result: "Rs 120"
    note: "Inherited uncertainty from family assignment"

overall_confidence: MEDIUM
hitl_required: true
hitl_items:
  - decision: "family_assignment"
    current: "Decorative Ceramics"
    confidence: 75%
    alternatives: ["Kitchen Storage (60%)", "New family"]
```

### 13.5 Discussion Points

- [ ] Are three levels (HIGH/MEDIUM/LOW) sufficient?
- [ ] Should LOW confidence auto-escalate or present options?

---

## 14. Failure Handling

Each protocol needs explicit edge case handling. This section provides universal patterns.

### 14.1 Universal Failure Patterns

```xml
<failure_handling>

## Empty Query Results

When read_data or aggregate_data returns []:

### Diagnosis
1. Is filter too restrictive?
   --> Try broader filter
2. Is table populated at all?
   --> Check with count_only=True on unfiltered table
3. Is this a cold-start situation?
   --> Domain genuinely has no data yet

### Actions
- If filter too restrictive: Broaden and retry
- If table empty: Document "No [X] exist yet"
- If cold-start: Flag as "Cannot apply protocol - no baseline data"

### Anti-Pattern
DO NOT conclude "doesn't exist" without trying broader search.

---

## Ambiguous Results

When comparison yields unclear result:

### Actions
1. Document the ambiguity explicitly
2. List the options with trade-offs
3. Present to user via HITL
4. Do NOT pick arbitrarily

### Example
"Family fit is ambiguous:
- Option A: 'Decorative Ceramics' - 70% match (customer aligns, price range differs)
- Option B: 'Kitchen Storage' - 60% match (material aligns, customer differs)
- Option C: Create new family

Recommendation: Option A (customer alignment more important than price range)
Please confirm or select alternative."

---

## Data Quality Issues

When data seems inconsistent:

### Actions
1. Flag the inconsistency explicitly
2. Query alternative sources if available
3. Present finding with caveat
4. Recommend data cleanup as follow-up task

### Example
"Found 3 products with same name but different families.
This may indicate data quality issue.
Proceeding with most recent entry.
Recommend: Review duplicate products."

---

## Protocol Doesn't Fit

When no protocol applies to the task:

### Actions
1. State: "No protocol covers this task type"
2. Describe what makes this task different
3. Either:
   - Handle with general reasoning (if straightforward)
   - Escalate to human (if complex)
4. Flag for protocol coverage review

</failure_handling>
```

### 14.2 Escalation Paths

**Problem:** Protocol says "ESCALATE" - but to whom? Through what mechanism?

**Escalation Matrix:**

| Agent | Escalation Target | Mechanism | When |
|-------|-------------------|-----------|------|
| **Analyst** | Specialist (via PM) | Return findings, PM routes | Analysis complete, decision needed |
| **Specialist** | PM | Return with escalation flag | Cannot decide, needs context |
| **Specialist** | User (via HITL) | HITL request | Write approval OR decision options |
| **PM** | User | Direct conversation | Ambiguous input, clarification needed |

**Escalation Types:**

```xml
<escalation_types>

## Type 1: Decision Escalation (Specialist --> User)
When: Protocol concludes with LOW confidence or PARTIAL result
How: Present options via HITL mechanism
Format:
  "I need your input on [decision]:
   Option A: [option] - [rationale]
   Option B: [option] - [rationale]
   Option C: [option] - [rationale]
   Which would you prefer?"

## Type 2: Context Escalation (Specialist --> PM)
When: Task specification missing required context
How: Return error response to PM
Format:
  {
    "status": "escalation",
    "type": "missing_context",
    "missing": ["family_id", "customer_segment"],
    "message": "Cannot execute Fit Assessment without target family"
  }
PM Response: Gather missing context, re-invoke specialist

## Type 3: Capability Escalation (Any --> PM --> User)
When: Task outside agent's capability
How: Return capability limitation
Format:
  {
    "status": "escalation",
    "type": "capability_limit",
    "task": "Generate marketing video",
    "message": "Video generation not supported. Can assist with: [list]"
  }

## Type 4: Data Quality Escalation
When: Data inconsistency discovered
How: Flag and continue OR stop if critical
Format:
  "Data quality issue detected:
   Found: [inconsistency]
   Impact: [how it affects decision]
   Proceeding with: [assumption]
   Recommended: [data cleanup task]"

</escalation_types>
```

**Escalation Flow Diagram:**

```
SPECIALIST EXECUTION
        |
        v
   Can conclude?
   /           \
 YES            NO
  |              |
  v              v
RETURN       What's blocking?
RESULT            |
            +-----+-----+
            |     |     |
          LOW   MISSING  CAPABILITY
       CONFIDENCE CONTEXT  LIMIT
            |     |        |
            v     v        v
         HITL   PM       PM
        OPTIONS GATHERS  INFORMS
                CONTEXT  USER
```

### 14.3 Per-Protocol Failure Handling

Each protocol should add specific failure handling:

```xml
<!-- Example: Add to Family Fit Protocol -->

## EDGE CASES

### No Customer Segment Found (Step 2 empty)
- This family has no defined customer segment
- Cannot determine fit without this data
- Action: Flag family as "incomplete" and escalate

### No Products in Family (Step 3 empty)
- Family exists but has no products yet
- Can still proceed with customer segment comparison
- Note: "First product in family" in conclusion

### Product Doesn't Fit ANY Family
- All families evaluated, none match
- Trigger: New Entity Protocol
- Pass: Evaluation results as context
```

### 14.3 Cold Start Protocols

**Problem:** Standard protocols assume existing data. New companies have empty databases.

**Which protocols fail on cold start:**

| Protocol | Empty DB Result | Standard Behavior | Cold Start Behavior |
|----------|-----------------|-------------------|---------------------|
| Duplicate Prevention | [] | Proceed (no duplicates) | Works as-is |
| Domain Orientation | [] | Can't orient | Use Bootstrap mode |
| Fit Assessment | [] | No families to fit | Use First Entity mode |
| Value Discovery | [] | No price patterns | Use Bootstrap Pricing |
| New Entity | [] | No comparison | Works (creates first) |

**Cold Start Detection:**

```xml
<cold_start_detection>

## Before Any Protocol

### Step 0: CHECK - Domain State
Execute: aggregate_data(table="[ENTITY_TABLE]", aggregations={"count": "id"})

**If count == 0:**
- Domain is in COLD START state
- Switch to Bootstrap protocols
- Flag all outputs for human review

**If count < 5:**
- Domain is in EARLY state
- Protocols work but confidence capped at MEDIUM
- Patterns not yet established

**If count >= 5:**
- Domain has baseline data
- Standard protocols apply

</cold_start_detection>
```

**Bootstrap Protocols:**

```xml
<protocol name="Bootstrap - First Family" domain="catalog" type="cold_start">

## PURPOSE
Create the first product family when none exist.

## WHEN TO USE
- Cold start detection shows 0 families
- First product being added to catalog

## STEPS

### Step 1: ANALYZE - Product Attributes
Based on product (image + any text):
- What customer would buy this?
- What use case does it serve?
- What quality tier is it?

**Result:**
Customer profile, use case, quality assessment.

### Step 2: DEFINE - Family Proposal
Based on Step 1, propose first family:
- Name: [Descriptive name based on customer/use]
- Customer Segment: [Who buys this]
- Positioning: [utility/decorative/premium]

**Critical:** This becomes the ANCHOR for future products.
Choose a name broad enough to accommodate similar products.

### Step 3: VALIDATE - With User
**This is COLD START - human MUST confirm:**

"I'm creating your first product family. This will set the pattern for your catalog.

Proposed Family:
- Name: [name]
- Target Customer: [segment]
- Positioning: [tier]

Does this align with your business? [Confirm/Modify]"

### Step 4: CREATE - Foundation
On confirmation:
- Create family
- Create customer segment
- Add product to family

**Result:**
First family created. Domain exits cold start for families.

## VERIFICATION
- [ ] User explicitly confirmed family definition
- [ ] Family name is broad enough for growth
- [ ] Customer segment is defined

</protocol>
```

```xml
<protocol name="Bootstrap - First Pricing" domain="catalog" type="cold_start">

## PURPOSE
Establish first price point when no pricing patterns exist.

## WHEN TO USE
- Cold start detection shows 0 products with prices
- First product being priced

## STEPS

### Step 1: GATHER - External Context
Ask user or infer from company context:
- What currency?
- What market positioning? (budget/mid/premium)
- Any reference prices user has in mind?

### Step 2: ESTABLISH - Anchor Price
**This price becomes the ANCHOR for all future pricing.**

Present to user:
"This is your first product price. It will anchor your catalog's pricing patterns.

Product: [name]
Suggested positioning: [tier based on visual analysis]
Price: [user's input or suggestion]

Future products will be priced relative to this. Confirm?"

### Step 3: DOCUMENT - Pricing Anchor
Record:
- First product price
- Positioning tier
- This becomes reference for Value Discovery protocol

**Result:**
Pricing anchor established. Future products use this as baseline.

</protocol>
```

**Cold Start Confidence Rules:**

| Scenario | Maximum Confidence | Reason |
|----------|-------------------|--------|
| First entity in domain | LOW | No patterns to validate against |
| 1-4 entities exist | MEDIUM | Insufficient pattern data |
| 5+ entities exist | HIGH possible | Patterns established |

**Cold Start User Communication:**

Always inform user when in cold start:
```
"Your [domain] is just getting started. I'll guide you through setting up
the foundation. These first few entries will establish patterns for
everything that follows, so I'll ask for confirmation more often."
```

---

## 15. Protocol Delivery Strategy

> STATUS: FUTURE - For now, protocols live directly in prompts

**Problem:** Full document injection (~8,000 tokens) causes attention dilution.

**Current Approach:** Embed relevant protocols directly in specialist prompts.

**Future Consideration:** When protocols grow, consider:
- Layered architecture (always inject vs task-specific retrieval)
- Agent-driven selection (agent picks which protocols to apply)
- Semantic retrieval (match task to relevant protocols)

**Protocol Location:** For now, protocols are embedded in:
```
agents/src/autifyme_agents/prompts/specialists/[domain]_specialist.prompt
```

**When to revisit:** When prompt size becomes a performance/cost concern

---

## 16. Episodic Memory (Layer 4)

> STATUS: FUTURE - Not needed for initial implementation

**Vision:** Successful protocol executions become examples for future similar tasks.

**Concept:**
- Capture successful protocol executions as "episodes"
- Index for semantic retrieval
- Inject relevant episodes as examples for similar future tasks

**Episode Components:**
- Task description (for matching)
- Protocols used
- Key queries and evidence
- Decision points and reasoning
- Final output
- User feedback (approved/edited/rejected)

**When to implement:** After protocols are stable and we have sufficient execution history to learn from.

**For now:** Canonical examples in prompts serve this purpose

---

## 17. Protocol Feedback and Improvement

Protocol improvement is handled through trace evaluation using the existing **Workflow Evaluation Framework**.

**See:** [WORKFLOW_EVALUATION_FRAMEWORK.md](../testing/WORKFLOW_EVALUATION_FRAMEWORK.md)

**Process:**
1. Evaluate workflow traces using the evaluation framework
2. Identify protocol gaps from trace analysis (reasoning quality, decision quality dimensions)
3. Update protocols based on findings
4. Re-evaluate to confirm improvement

**No additional infrastructure required** - trace evaluation provides all the feedback signals needed.

---

## 18. References

### 18.1 Related Architecture Docs

- [ARCHITECTURAL_VISION.md](./ARCHITECTURAL_VISION.md) - Overall system vision
- [AGENTS_DESIGN.md](./AGENTS_DESIGN.md) - Agent hierarchy and roles
- [AI_AGENT_ANATOMY.md](./AI_AGENT_ANATOMY.md) - SENSE-THINK-ACT-FEEDBACK framework
- [PROMPT_ENGINEERING_STANDARDS.md](../tech/PROMPT_ENGINEERING_STANDARDS.md) - Prompt design standards
- [WORKFLOW_EVALUATION_FRAMEWORK.md](../testing/WORKFLOW_EVALUATION_FRAMEWORK.md) - Trace evaluation for protocol improvement

### 18.2 Quick Reference

**Generic Patterns:**
- Fit Assessment - Does X belong with Y?
- Value Discovery - What value should X have?
- New Entity - Should we create new X?
- Duplicate Prevention - Does X already exist?
- Domain Orientation - What is current state of X?

**Tool Mastery:**
- read_data - Relations, filters, columns, limits
- aggregate_data - Patterns, ranges, distributions
- write_data - Verification, complete data, HITL
- inspect_schema - Structure, relationships

**Instantiation Process:**
1. Map domain decisions to generic patterns
2. Identify domain entities, values, criteria
3. Replace placeholders
4. Add domain-specific guidance
5. Write business context

---

## Appendix A: Pattern Quick Reference

### A.1 Pattern Selection Guide

| Decision Type | Pattern | Key Question |
|---------------|---------|--------------|
| "Does X belong in Y?" | Fit Assessment | Match qualifying criteria? |
| "What should X cost/be valued at?" | Value Discovery | What do similar Xs have? |
| "Should we create new Y?" | New Entity | Do existing Ys serve this need? |
| "Does X already exist?" | Duplicate Prevention | Any matches found? |
| "What's the current state?" | Domain Orientation | How is domain structured? |

### A.2 Step Action Verbs

| Verb | Use For |
|------|---------|
| IDENTIFY | Establishing what we're working with |
| QUERY | Executing database calls |
| AGGREGATE | Finding patterns/statistics |
| ANALYZE | Interpreting results |
| COMPARE | Evaluating against criteria |
| CONCLUDE | Reaching decision |
| ESCALATE | Handing off |

### A.3 Universal Anti-Patterns

- Concluding without querying
- Using general knowledge instead of data
- Skipping steps in protocol
- Not documenting step results
- Ignoring mismatches

---

**Document Version:** 5.2
**Last Updated:** December 16, 2025
**Revision:**
- v5.2: Aggressive ULTRATHINK review - addressed all P0/P1/P2 gaps:
  - P0: Added grounding boundary clarification (2.4) - visual analysis is ungrounded interpretation
  - P0: Added cold start protocols (14.3) - bootstrap protocols for empty databases
  - P1: Added cross-domain coordination (3.6-3.7) - entity ownership, context passing
  - P1: Added correction flow (4.10) - how corrections work with stateless specialists
  - P1: Added chained confidence handling (13.4) - rules for protocol chains
  - P2: Clarified analyst/specialist distinction (3.4) - accountability vs capability
  - P2: Added escalation paths (14.2) - explicit escalation matrix and types
  - P2: Added PARTIAL branching logic (12.5) - scoring and decision tree for partial matches
- v5.1: ULTRATHINK review fixes - fixed section ordering, resolved status contradictions, added tool grounding, clarified ALL agents need protocols, added protocols+intelligence balance
- v5.0: Streamlined document - removed Python code sections, simplified Sections 15-17 as FUTURE
- v4.0: Added Multi-Domain Architecture (Section 3), PM Domain Routing Protocol (Section 4)
- v3.0: Added Sections 12-17 (Composition, Confidence, Failure, RAG, Episodic Memory, Feedback Loop)
