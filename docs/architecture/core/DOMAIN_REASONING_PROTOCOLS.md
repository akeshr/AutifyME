# Domain-Specific Reasoning Protocols

**Created:** December 15, 2025
**Status:** APPROVED - Ready for Implementation
**Purpose:** Domain-agnostic framework for encoding domain expertise as executable reasoning protocols

---

## Executive Summary

LLMs are general-purpose. Our domains require specific behavior. Fine-tuning is not an option. Examples get replicated, not understood. Rules get applied blindly.

**The Solution:** Domain-Specific Reasoning Protocols - encoding domain expertise as mandatory reasoning steps that agents EXECUTE, not patterns they REPLICATE.

**Key Insight:** Domain knowledge can be encoded as PROCESS, not as facts or rules. The protocol IS the expertise.

**Framework Approach:** Generic patterns that apply to ANY domain, instantiated with domain-specific entities and values.

---

## Table of Contents

**FOUNDATION**
1. [The Problem](#1-the-problem)
2. [The Solution: Reasoning Protocols](#2-the-solution-reasoning-protocols)
3. [Multi-Domain Architecture](#3-multi-domain-architecture)

**PM-LEVEL PROTOCOLS**
4. [PM Intelligence and Routing](#4-pm-intelligence-and-routing)
   - 4.1 [Stateful/Stateless Architecture](#41-statefulstateless-architecture)
   - 4.2 [PM State Schema](#42-pm-state-schema)
   - 4.3 [PM Intelligence Layer (Pre-Routing)](#43-pm-intelligence-layer-pre-routing)
   - 4.4 [The Routing Problem](#44-the-routing-problem)
   - 4.5 [Domain Discovery Protocol](#45-domain-discovery-protocol)
   - 4.6 [Intent Classification Protocol](#46-intent-classification-protocol)
   - 4.7 [Complete PM Routing Flow](#47-complete-pm-routing-flow)
   - 4.8 [Task Specification Contract](#48-task-specification-contract)
   - 4.9 [Example: Image Only Scenario](#49-example-1-image-only-scenario)
   - 4.10 [Discussion Points](#410-discussion-points)

**GENERIC PATTERNS**
5. [Generic Protocol Patterns](#5-generic-protocol-patterns)
6. [Tool Mastery Protocols](#6-tool-mastery-protocols)

**DOMAIN IMPLEMENTATION**
7. [Protocol Creation Guide](#7-protocol-creation-guide)
8. [Domain Instantiation](#8-domain-instantiation)
9. [Catalog Domain Example](#9-catalog-domain-example)
10. [Marketing Domain Example](#10-marketing-domain-example)

**INTEGRATION**
11. [Integration with Agent Architecture](#11-integration-with-agent-architecture)
12. [Protocol Composition Framework](#12-protocol-composition-framework)

**QUALITY & CONFIDENCE**
13. [Confidence Scoring Framework](#13-confidence-scoring-framework)
14. [Failure Handling](#14-failure-handling)

**RETRIEVAL & MEMORY**
15. [RAG Strategy](#15-rag-strategy)
16. [Episodic Memory (Layer 4)](#16-episodic-memory-layer-4)
17. [Feedback Loop (Layer 5)](#17-feedback-loop-layer-5)

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

### 1.2 Why Common Solutions Fail

| Approach | Problem |
|----------|---------|
| **Examples** | Get REPLICATED, not understood. Agent copies structure without reasoning. |
| **Rules** | Get APPLIED BLINDLY. Agent doesn't know when/how to apply. |
| **RAG** | Requires knowing WHAT to retrieve. Agent doesn't know what questions to ask. |
| **More context** | Passive. Sits in prompt but doesn't guide reasoning. |

### 1.3 The Core Insight

**The agent doesn't know:**
- What questions to ask
- What matters for each decision type
- How YOUR business thinks about problems
- How to use YOUR tools effectively

**Examples can't teach this** because examples show WHAT to conclude, not HOW to reason.

**Rules can't teach this** because rules are abstract - the agent doesn't know how to apply them.

**The solution:** Encode domain expertise as EXECUTABLE PROCESS that works across ANY domain.

---

## 2. The Solution: Reasoning Protocols

### 2.1 What Is a Reasoning Protocol?

A Domain-Specific Reasoning Protocol is a **step-by-step reasoning process** that:
- Encodes WHAT to investigate
- Specifies WHICH queries to execute
- Defines HOW to interpret results
- Guides WHEN to conclude vs continue

**The protocol IS the domain expertise in executable form.**

### 2.2 Protocol vs Example vs Rule

| Type | What It Provides | How Agent Uses It |
|------|------------------|-------------------|
| **Rule** | Abstract principle | Tries to apply (often incorrectly) |
| **Example** | Specific case | Copies the pattern |
| **Protocol** | Executable steps | EXECUTES the process |

**Protocols can't be replicated - they must be executed.**

### 2.3 Why Protocols Work

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

### 3.4 Protocol Ownership by Agent Level

| Agent Level | Protocol Type | Purpose |
|-------------|---------------|---------|
| **PM** | Domain Routing Protocols | Classify, route, synthesize |
| **Analysts** | Exploration Protocols | Thorough, consistent investigation |
| **Specialists** | Decision Protocols | Domain-specific reasoning |
| **Any Agent** | Tool Mastery Protocols | Powerful, efficient tool usage |
| **Any Agent** | Orientation Protocols | Understanding domain state |

### 3.5 Cross-Domain Scenarios

Some tasks span multiple domains. PM orchestrates:

| Scenario | Domains Involved | PM Orchestration |
|----------|------------------|------------------|
| "New product launch" | Cataloging + Marketing | Catalog product first, then create campaign |
| "Customer complaint about order" | Customer Service + Operations | Triage in CS, route to Ops for resolution |
| "Inventory restock" | Operations + Finance | Assess need in Ops, approve budget in Finance |

---

## 4. PM Intelligence and Routing

> STATUS: DISCUSSION NEEDED

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

### 4.2 PM State Schema

```python
# What PM maintains across conversation turns

class PMSessionState:
    """State managed by PM DeepAgent via LangGraph checkpointer."""

    # Conversation tracking
    conversation_history: list[ConversationTurn]  # Summarized, last 5-10 turns
    current_topic: TopicContext | None            # What we're working on

    # Entity tracking (for reference resolution)
    recent_entities: list[EntityReference]        # Last 5-10 entities mentioned
    pending_entity: EntityReference | None        # "The one we're working on"

    # User modeling (for intelligent responses)
    user_preferences: dict[str, Any]              # Learned from corrections
    user_state: UserState                         # frustrated, exploring, efficient

    # Workflow tracking
    active_workflow: WorkflowState | None
    pending_hitl: list[HITLRequest]

class EntityReference:
    """Reference to an entity for resolution."""
    entity_type: str      # product, family, campaign, etc.
    entity_id: str
    entity_name: str
    last_action: str      # created, updated, discussed
    timestamp: datetime

class TopicContext:
    """Current topic of conversation."""
    domain: str
    intent: str           # CREATE, UPDATE, QUERY, etc.
    primary_entity: EntityReference | None
    related_entities: list[EntityReference]
```

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

```python
# What PM passes to EVERY specialist invocation

class TaskSpecification:
    """Contract between PM (stateful) and Specialist (stateless)."""

    # Identity - WHO is being asked
    specialist: str                    # "cataloging_specialist", "marketing_specialist"
    domain: str                        # "catalog", "marketing"

    # Intent - WHAT to do
    action: str                        # "CREATE", "UPDATE", "ANALYZE", "QUERY"
    target_entity: str                 # "product", "campaign", "family"
    target_id: str | None              # If UPDATE/specific entity

    # Context - ALL resolved context (no references left)
    resolved_context: ResolvedContext

    # Protocols - WHICH to execute
    protocols_to_apply: list[str]      # ["duplicate_prevention", "family_fit", "pricing"]

    # User hints - inference from PM intelligence layer
    user_hints: dict[str, Any]         # {"preferred_price": 350, "style": "casual"}

    # Communication - HOW to respond
    response_style: str                # "efficient", "detailed", "exploratory"
    user_state: str                    # "frustrated", "exploring", "efficient"


class ResolvedContext:
    """All references resolved to explicit values."""

    # Resolved entities (no "this", "it", "that product")
    primary_entity: dict | None        # Full entity data if relevant
    related_entities: list[dict]       # Other entities mentioned

    # Resolved inputs
    images: list[str]                  # Image URLs/paths
    text_input: str                    # Original user text
    resolved_text: str                 # With references replaced

    # Conversation summary (not full history)
    conversation_summary: str          # "User is adding products to Blue Pottery family"
    relevant_prior_decisions: list[str]  # ["User rejected suggested family 'Vases'"]

    # Business context
    company_id: str
    company_context: dict              # Company settings, preferences
```

**Example Task Specification:**

```
TaskSpecification(
    specialist="cataloging_specialist",
    domain="catalog",
    action="CREATE",
    target_entity="product",
    target_id=None,

    resolved_context=ResolvedContext(
        primary_entity=None,  # Creating new
        related_entities=[
            {"type": "family", "id": "fam_123", "name": "Blue Pottery Collection"}
        ],
        images=["https://storage.../img_abc.jpg"],
        text_input="add this to the same family",
        resolved_text="add this product to Blue Pottery Collection family",
        conversation_summary="User adding products to Blue Pottery Collection. Last product was a vase priced at 450.",
        relevant_prior_decisions=["User prefers descriptive names over SKU-style"],
        company_id="comp_xyz",
        company_context={"default_currency": "INR", "pricing_strategy": "premium"}
    ),

    protocols_to_apply=["duplicate_prevention", "family_fit_assessment", "pricing_discovery"],
    user_hints={"likely_price_range": "400-500", "style": "ceramic"},
    response_style="efficient",
    user_state="efficient"
)
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

TaskSpecification(
    specialist="cataloging_specialist",
    domain="catalog",
    action="CREATE",
    target_entity="product",
    target_id=None,

    resolved_context=ResolvedContext(
        primary_entity=None,
        related_entities=[
            {"type": "family", "id": "fam_123", "name": "Blue Pottery Collection"}
        ],
        images=["https://storage.../vase_img.jpg"],
        text_input="",  # No text provided
        resolved_text="Create product in Blue Pottery Collection family",
        conversation_summary="User batch-adding products to Blue Pottery Collection. Last 3 products: ceramic bowl (450), ceramic plate (380), ceramic cup (320).",
        relevant_prior_decisions=["User confirmed Blue Pottery as target family"],
        company_id="comp_xyz",
        company_context={"default_currency": "INR"}
    ),

    protocols_to_apply=["duplicate_prevention", "family_fit_assessment", "pricing_discovery"],
    user_hints={"likely_family": "Blue Pottery Collection", "price_range": "300-500", "style": "ceramic"},
    response_style="efficient",
    user_state="efficient"
)

=== SPECIALIST EXECUTION (STATELESS) ===

Specialist receives COMPLETE context:
- Knows the target family (no need to ask)
- Knows price range from similar products
- Knows user wants efficiency (no lengthy explanations)
- Runs only specified protocols
- Returns result and forgets everything
```

### 4.10 Discussion Points

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

## 10. Marketing Domain Example

This section shows how the same patterns apply to a different domain.

### 10.1 Marketing Domain Elements

| Element | Marketing Instantiation |
|---------|------------------------|
| Entity | audience_segments |
| Subject | campaigns |
| Value | budget |
| Criteria | audience_profiles |
| Category | funnel_stage (awareness, consideration, conversion) |
| Identifier | campaign_name |

### 10.2 Marketing Business Context

```xml
<business_context domain="marketing">

## Funnel Stages

### AWARENESS (Budget: Rs 5K-20K)
- Objective: Reach new audiences, build recognition
- Channels: Social, display, video
- Metric: Impressions, reach

### CONSIDERATION (Budget: Rs 10K-50K)
- Objective: Engage interested prospects
- Channels: Search, retargeting, email
- Metric: Clicks, engagement, time on site

### CONVERSION (Budget: Rs 20K-100K)
- Objective: Drive purchases, sign-ups
- Channels: Search, shopping, remarketing
- Metric: Conversions, ROAS

## Key Relationships
- audience_segments --> audience_profiles (who is in this segment)
- campaigns --> audience_segments (who campaign targets)
- audience_profiles DETERMINES segment fit (not channel, not budget)

## Common Misconceptions
- NOT: Same channel = same audience segment
- ACTUALLY: Same customer need = same segment
- NOT: Budget determines funnel stage
- ACTUALLY: Objective determines funnel stage

</business_context>
```

### 10.3 Audience Fit Protocol (Instantiated)

```xml
<protocol name="Audience Fit Protocol" domain="marketing" type="decision">

## PURPOSE
Determine if a campaign should target a candidate audience segment.

## STEPS

### Step 1: IDENTIFY - Candidate Segment
Identify the audience segment being evaluated.
Document: segment_id, segment_name

**Result:**
Candidate segment: [id, name]

### Step 2: QUERY - Audience Profile
**Execute:**
read_data(
  table="audience_profiles",
  filters={"segment_id": [candidate_segment_id]}
)

**Why This Matters:**
audience_profiles is THE deciding factor for segment fit.
NOT channel. NOT budget. WHO YOU'RE REACHING determines fit.

**How to Interpret:**
The profile tells you demographics, interests, behaviors.
"Tech-savvy millennials, early adopters" = different from
"Budget-conscious families, value seekers"

**Result:**
Audience profile for this segment.

### Step 3: QUERY - Segment's Current Campaigns
**Execute:**
read_data(
  table="campaigns",
  filters={"segment_id": [candidate_segment_id]},
  columns=["name", "objective", "funnel_stage"],
  limit=10
)

**Understand:**
What campaigns currently target this? What objectives?

**Result:**
Sample campaigns with their attributes.

### Step 4: ANALYZE - Campaign's Target Audience
Based on campaign attributes (message, offer, creative):
- Who is this speaking to?
- What need does it address?
- What action does it want?

**Result:**
Target audience profile for THIS campaign.

### Step 5: COMPARE - Audience Match
Compare Step 2 (segment's audience) with Step 4 (campaign's audience):
- MATCH: Same audience type
- MISMATCH: Different audience type
- PARTIAL: Overlapping but distinct

**Result:**
Match assessment with evidence.

### Step 6: CONCLUDE
**Based on Step 5:**
- MATCH: Campaign FITS this segment
- MISMATCH: Campaign needs DIFFERENT segment
- PARTIAL: Consider sub-segment

## VERIFICATION
- [ ] Step 2 query executed
- [ ] Audience comparison based on evidence
- [ ] Conclusion references step results

## ANTI-PATTERNS
- Matching based on channel alone
- Skipping audience profile query
- Using general marketing assumptions

</protocol>
```

### 10.4 Example: Marketing Protocol Execution

```
TASK: Determine audience fit for "Summer Sale" campaign

PROTOCOL SELECTED: Audience Fit Protocol

STEP 1: IDENTIFY - Candidate Segment
Candidate: "Young Professionals" (seg-003)
Source: Suggested based on past summer campaigns

STEP 2: QUERY - Audience Profile
Executed: read_data(table="audience_profiles", filters={"segment_id": "seg-003"})
Result: "Career-focused 25-35, premium buyers, convenience-oriented"

STEP 3: QUERY - Segment Campaigns
Executed: read_data(table="campaigns", filters={"segment_id": "seg-003"}, limit=10)
Result: Premium product launches, time-saving offers. Avg budget Rs 50K.

STEP 4: ANALYZE - Campaign's Audience
Campaign: "Summer Sale" - 40% off clearance, bulk deals, family sizes
Target: Budget-conscious, value-seeking, bulk buyers
NOT: Premium, convenience-focused

STEP 5: COMPARE - Audience Match
Segment: Premium, convenience-focused professionals
Campaign: Value-focused, bulk buyers
Assessment: MISMATCH - different purchase motivation

STEP 6: CONCLUDE
MISMATCH = Campaign needs DIFFERENT segment

--> Search for value-focused family segment instead
```

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

You are a PROTOCOL EXECUTOR + INTELLIGENT INTERPRETER.
- Follow protocols precisely
- Apply intelligence to interpret results
- Escalate when protocols don't cover the situation
</protocol_usage>

<examples>
[Examples showing protocol execution]
</examples>
```

---

## 18. References

### 18.1 Related Architecture Docs

- [ARCHITECTURAL_VISION.md](./ARCHITECTURAL_VISION.md) - Overall system vision
- [AGENTS_DESIGN.md](./AGENTS_DESIGN.md) - Agent hierarchy and roles
- [AI_AGENT_ANATOMY.md](./AI_AGENT_ANATOMY.md) - SENSE-THINK-ACT-FEEDBACK framework
- [PROMPT_ENGINEERING_STANDARDS.md](../tech/PROMPT_ENGINEERING_STANDARDS.md) - Prompt design standards

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

## 12. Protocol Composition Framework

> STATUS: DISCUSSION NEEDED

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

### 12.5 Discussion Points

- [ ] Should composition be agent-driven (prompt) or system-driven (code)?
- [ ] How explicit should sequencing guidance be?
- [ ] Should we enforce composition rules or leave flexible?

---

## 13. Confidence Scoring Framework

> STATUS: DISCUSSION NEEDED

Protocols currently conclude with binary (MATCH/MISMATCH). Need gradients.

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

### 13.4 Discussion Points

- [ ] Are three levels (HIGH/MEDIUM/LOW) sufficient?
- [ ] Should LOW confidence auto-escalate or present options?
- [ ] How to handle confidence across chained protocols?

---

## 14. Failure Handling

> STATUS: DISCUSSION NEEDED

Each protocol needs explicit edge case handling.

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

### 14.2 Per-Protocol Failure Handling

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

### 14.3 Discussion Points

- [ ] Should failure handling be inline in each protocol or separate section?
- [ ] How detailed should edge case documentation be?
- [ ] Should we track failure patterns for protocol improvement?

---

## 15. RAG Strategy

> STATUS: DISCUSSION NEEDED

How to efficiently deliver protocols to agents without context bloat.

### 15.1 The Problem

| Approach | Tokens | Issue |
|----------|--------|-------|
| Full document injection | ~8,000 | Attention dilution, expensive |
| No injection (agent figures it out) | 0 | Agent doesn't know protocols |

### 15.2 Layered Architecture

```
+====================================================================+
|              DOMAIN REASONING ARCHITECTURE (LAYERED)               |
+====================================================================+

ALWAYS INJECTED (~1,700 tokens):
+--------------------------------------------------------------------+
| LAYER 0: Protocol Framework (~500 tokens)                          |
| - Protocol Selection Guide                                         |
| - Composition Patterns                                             |
| - Confidence Framework                                             |
| - Failure Handling Principles                                      |
+--------------------------------------------------------------------+
| LAYER 1: Tool Mastery (~800 tokens)                                |
| - read_data mastery                                                |
| - aggregate_data mastery                                           |
| - write_data mastery                                               |
| - inspect_schema mastery                                           |
+--------------------------------------------------------------------+
| LAYER 2: Domain Context (~400 tokens)                              |
| - Business Context (tiers, relationships)                          |
| - Domain-Specific Anti-patterns                                    |
+--------------------------------------------------------------------+

RETRIEVED BASED ON TASK (~600-1,200 tokens):
+--------------------------------------------------------------------+
| LAYER 3: Decision Protocols (1-2 per task)                         |
| - Fit Assessment (~600 tokens)                                     |
| - Value Discovery (~500 tokens)                                    |
| - New Entity (~600 tokens)                                         |
| - Duplicate Prevention (~400 tokens)                               |
| - Domain Orientation (~500 tokens)                                 |
+--------------------------------------------------------------------+

OPTIONAL (~300 tokens):
+--------------------------------------------------------------------+
| LAYER 4: Episodic Memory                                           |
| - Relevant execution examples                                      |
+--------------------------------------------------------------------+

TOTAL: ~2,600-3,200 tokens (vs ~8,000 for full doc)
```

### 15.3 File Structure for RAG

```
docs/architecture/core/protocols/
|-- PROTOCOL_FRAMEWORK.md           # Layer 0 (always inject)
|-- TOOL_MASTERY.md                 # Layer 1 (always inject)
|-- GENERIC_PATTERNS.md             # Reference only
|
|-- domains/
    |-- catalog/
    |   |-- CONTEXT.md              # Layer 2 (inject for catalog)
    |   |-- FIT_PROTOCOL.md         # Layer 3 (retrieve when needed)
    |   |-- PRICING_PROTOCOL.md     # Layer 3 (retrieve when needed)
    |   |-- NEW_ENTITY_PROTOCOL.md  # Layer 3 (retrieve when needed)
    |   |-- DUPLICATE_PROTOCOL.md   # Layer 3 (retrieve when needed)
    |
    |-- marketing/
        |-- CONTEXT.md
        |-- [protocols...]
```

### 15.4 Retrieval Options

| Option | How It Works | Pros | Cons |
|--------|--------------|------|------|
| **A: Agent-Driven** | Agent selects protocols via prompt guidance | Simple, transparent | Relies on agent judgment |
| **B: Keyword-Based** | Match task keywords to protocol triggers | Predictable | Brittle, misses synonyms |
| **C: Semantic Search** | Embed task, find similar protocols | Flexible | May retrieve wrong protocols |
| **D: Hybrid** | Keywords first, semantic fallback | Balanced | More complex |

### 15.5 Discussion Points

- [ ] Should we split the document into separate files (15.3)?
- [ ] Which retrieval option (A/B/C/D)?
- [ ] Is ~3,000 tokens acceptable for protocol context?
- [ ] Should protocols live in prompts directory or docs?

---

## 16. Episodic Memory (Layer 4)

> STATUS: DISCUSSION NEEDED

Successful protocol executions become examples for future similar tasks.

### 16.1 The Vision

```
Workflow succeeds --> Capture as episode --> Index for retrieval -->
Future similar task --> Retrieve relevant episode --> Inject as example
```

### 16.2 What is an Episode?

An episode captures a SUCCESSFUL protocol execution:

| Component | Purpose |
|-----------|---------|
| Task Description | For semantic matching to future tasks |
| Protocols Used | Which protocols applied |
| Key Queries | Evidence gathered |
| Decision Points | Where judgment was applied |
| Final Output | What was produced |
| User Feedback | Approved? Edited? Rejected? |

### 16.3 Episode Schema

```python
class Episode:
    # Identity
    id: str
    created_at: datetime
    domain: str

    # Task Context
    task_description: str
    task_embedding: list[float]  # For semantic search

    # Execution
    protocols_used: list[str]
    key_queries: list[dict]      # {query, result_summary}
    key_decisions: list[str]     # Reasoning at decision points
    final_output: dict

    # Outcome
    user_feedback: "approved" | "approved_with_edits" | "rejected"
    edit_details: str | None

    # Metadata
    execution_time_ms: int
    tags: list[str]
```

### 16.4 Episode Capture

**When to Capture:**

| Outcome | Capture? | Reason |
|---------|----------|--------|
| Approved | Yes | Protocol worked perfectly |
| Approved with Edits | Yes | Protocol mostly worked, edits inform gaps |
| Rejected | No | Goes to feedback loop instead |

**Capture Point:**
After HITL resolution in workflow runner.

### 16.5 Episode Retrieval

```python
def get_relevant_episodes(task: str, domain: str, k: int = 2):
    """Retrieve episodes relevant to current task."""

    # 1. Semantic search by task similarity
    task_embedding = embed(task)

    candidates = episode_store.search(
        namespace=["episodes", domain],
        query_embedding=task_embedding,
        k=k * 3,
        filter={"user_feedback": ["approved", "approved_with_edits"]}
    )

    # 2. Prefer clean approvals
    approved = [e for e in candidates if e.user_feedback == "approved"]
    edited = [e for e in candidates if e.user_feedback == "approved_with_edits"]

    # 3. Select diverse examples
    return select_diverse(approved + edited, k)
```

### 16.6 Episode Injection Format

```xml
<relevant_episode>

## Similar Task: Product Family Assignment

### Task
"Add ceramic flower vase to catalog"

### Protocols Applied
1. Duplicate Prevention --> No duplicates found
2. Family Fit Assessment --> Evaluated "Decorative Ceramics"
   - Queried: customer_segments for family
   - Result: "Gift buyers, home decor enthusiasts"
   - Conclusion: MATCH (HIGH confidence)

### Key Decision
Product's decorative nature aligned with family's customer segment.
Price Rs 150 placed in mid-decorative range.

### Outcome
Approved without edits.

</relevant_episode>
```

### 16.7 Discussion Points

| Question | Options |
|----------|---------|
| **When to capture?** | All approvals / Clean only / Sampled / Agent-flagged |
| **When to inject?** | Always / On uncertainty / Agent requests / Never |
| **Storage backend?** | LangGraph Store / PostgreSQL / Vector DB |
| **Retention policy?** | Keep all / Rolling window / Quality-based |
| **Episode format?** | Full trace / Summarized / Key decisions only |

---

## 17. Feedback Loop (Layer 5)

> STATUS: DISCUSSION NEEDED

Protocols improve over time based on production outcomes.

### 17.1 The Vision

```
Execution outcome --> Classify feedback --> Route to improvement queue -->
Periodic review --> Protocol refinement --> Deploy updated protocol
```

### 17.2 Feedback Types

| Outcome | Meaning | Action |
|---------|---------|--------|
| **Approved** | Protocol worked | Validate, capture episode |
| **Approved with Edits** | Protocol mostly worked | Analyze what was edited |
| **Rejected** | Protocol failed | Critical gap, immediate review |
| **No Protocol Fit** | Coverage gap | New protocol candidate |
| **Escalated** | Agent uncertain | Clarity gap in protocol |

### 17.3 Feedback Schema

```python
class ProtocolFeedback:
    # Identity
    id: str
    workflow_id: str
    domain: str
    created_at: datetime

    # Context
    task_description: str
    protocols_attempted: list[str]

    # Outcome
    feedback_type: str  # approved, edited, rejected, no_fit, escalated

    # Details
    agent_conclusion: str
    user_action: str
    edit_details: str | None
    rejection_reason: str | None

    # Analysis (populated during review)
    root_cause: str | None
    gap_type: str | None  # missing_step, unclear_guidance, edge_case, etc.
    suggested_fix: str | None
    priority: str | None  # critical, high, medium, low
```

### 17.4 Feedback Capture

```python
async def capture_feedback(workflow_id, task, protocols_used,
                           agent_conclusion, user_feedback,
                           edit_details=None, rejection_reason=None):

    feedback = ProtocolFeedback(
        id=f"fb_{workflow_id}",
        workflow_id=workflow_id,
        domain=extract_domain(task),
        task_description=task,
        protocols_attempted=protocols_used,
        feedback_type=classify_feedback(user_feedback),
        agent_conclusion=agent_conclusion,
        user_action=user_feedback,
        edit_details=edit_details,
        rejection_reason=rejection_reason
    )

    await feedback_store.put(
        namespace=["feedback", feedback.domain],
        key=feedback.id,
        value=feedback
    )

    # Alert on critical
    if feedback.feedback_type == "rejected":
        await alert_protocol_failure(feedback)
```

### 17.5 Review Cycle

```
+------------------------------------------------------------------+
|                    WEEKLY REVIEW CYCLE                            |
+------------------------------------------------------------------+

1. AGGREGATE
   - Collect feedback from past week
   - Calculate success metrics per protocol
   - Identify recurring patterns

2. ANALYZE
   - Cluster edit patterns (what's being changed?)
   - Cluster rejection reasons (what's failing?)
   - Identify coverage gaps (what's not covered?)

3. PRIORITIZE
   - Critical: Any rejection
   - High: Recurring edits (3+ same edit)
   - Medium: Single edits
   - Low: Coverage gaps

4. FIX
   - Update protocol steps/guidance
   - Add edge case handling
   - Clarify ambiguous criteria
   - Add new protocols if needed

5. VALIDATE
   - Test updated protocol against historical cases
   - Check for regression

6. DEPLOY
   - Update protocol documents
   - Monitor next week

+------------------------------------------------------------------+
```

### 17.6 Metrics Dashboard

| Metric | Target | Alert |
|--------|--------|-------|
| Success Rate | >90% | <80% |
| Clean Approval Rate | >70% | <60% |
| Rejection Rate | <5% | >10% |
| Coverage Rate | >95% | <90% |

### 17.7 Discussion Points

| Question | Options |
|----------|---------|
| **Automation level?** | Manual review / Semi-auto (suggest fixes) / Auto-pilot |
| **Review frequency?** | Daily / Weekly / On-demand |
| **Who reviews?** | Human / AI-assisted / Fully automated |
| **How to track improvements?** | Version protocols / A/B test / Before/after metrics |

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

**Document Version:** 4.0
**Last Updated:** December 16, 2025
**Revision:**
- v4.0: Added Multi-Domain Architecture (Section 3), PM Domain Routing Protocol (Section 4). Restructured ToC.
- v3.0: Added Sections 12-17 (Composition, Confidence, Failure, RAG, Episodic Memory, Feedback Loop) - STATUS: DISCUSSION NEEDED
