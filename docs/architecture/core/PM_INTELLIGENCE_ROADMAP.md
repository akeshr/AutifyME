# PM Intelligence Roadmap

**Created:** December 17, 2025
**Status:** ROADMAP - Future Capabilities
**Extracted From:** DOMAIN_REASONING_PROTOCOLS.md Sections 3-4

---

## Purpose

This document describes the TARGET STATE for PM intelligence capabilities. These are NOT current implementations - they represent the architectural vision for future development.

**Current PM:** Basic routing and delegation
**Target PM:** Intelligent orchestrator with reference resolution, intent inference, and adaptive communication

---

## 1. Multi-Domain Vision

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
|  STATE: conversation_history, current_topic, recent_entities,        |
|         user_preferences, pending_entity, active_workflow            |
|                                                                      |
|  INTELLIGENCE LAYER (Pre-Routing):                                   |
|  1. RESOLVE - Turn "this", "it" into explicit entities               |
|  2. CONTEXT - Load conversation continuity                           |
|  3. INFER - Detect implicit intent                                   |
|  4. ASSESS - User state (efficient, exploring, frustrated)           |
|  5. ENRICH - Build complete understanding                            |
+=====================================================================+
                                  |
                    TASK SPECIFICATION CONTRACT
                                  |
            +---------------------+---------------------+
            v                     v                     v
+------------------+   +------------------+   +------------------+
|   CATALOGING     |   |    MARKETING     |   |   OPERATIONS     |
|  (STATELESS)     |   |   (STATELESS)    |   |   (STATELESS)    |
+------------------+   +------------------+   +------------------+
```

### Domain Registry (Future)

| Domain | Purpose | Key Entities | Status |
|--------|---------|--------------|--------|
| **Cataloging** | Product catalog | products, families | ACTIVE |
| **Marketing** | Campaigns | campaigns, audiences | FUTURE |
| **Operations** | Fulfillment | orders, inventory | FUTURE |
| **Customer Service** | Support | tickets, customers | FUTURE |

---

## 2. Stateful/Stateless Architecture

**Critical Constraint:** PM is DeepAgent (stateful), Specialists are SubAgents (stateless).

| Capability | PM (Stateful) | Specialist (Stateless) |
|------------|---------------|------------------------|
| Reference resolution | YES | NO - receives resolved |
| Conversation memory | YES | NO - receives summary |
| User state tracking | YES | NO - receives as context |
| Protocol selection | YES | NO - receives which to run |
| Learning from outcomes | YES | NO |

### PM State (Conceptual)

| State Category | Contents | Purpose |
|----------------|----------|---------|
| **Conversation** | Recent turns, current topic | Continuity |
| **Entities** | Recent entities, pending entity | Reference resolution |
| **User Model** | Preferences, state | Adaptive responses |
| **Workflow** | Active workflow, pending HITL | Coordination |

---

## 3. PM Intelligence Layer

### 3.1 Intelligence Protocol (Future)

```xml
<protocol name="PM Intelligence" level="PM" type="pre-routing">

## PURPOSE
Understand user intent BEFORE routing. Uses PM's stateful context.

## EXECUTE BEFORE DOMAIN ROUTING

### Step 1: RESOLVE - References
| Reference Type | Example | Resolution |
|----------------|---------|------------|
| Pronoun | "this", "it" | Check pending_entity |
| Temporal | "yesterday" | Query by timestamp |
| Relational | "the same" | Check recent_entities |
| Implicit | [just "350"] | Check current_topic |

### Step 2: CONTEXT - Continuity
| Signal | Meaning |
|--------|---------|
| current_topic exists | Continuing prior work |
| pending_entity set | Input relates to this |

### Step 3: INFER - Implicit Intent
| Input | With Context | Inferred |
|-------|--------------|----------|
| Just number "350" | Discussing pricing | Price = 350 |
| Just image | After "add more" | Add to same batch |
| "wrong" | After result | Correction needed |

### Step 4: ASSESS - User State
| Signal | State | Adapt |
|--------|-------|-------|
| Short messages | Efficient | Skip pleasantries |
| "asap", "urgent" | Time pressure | Prioritize |
| Questions | Exploring | Explain more |
| "wrong", "again" | Frustrated | Be efficient |

### Step 5: ENRICH - Synthesize
Output: Resolved references, continuation status, implicit intent, user state

</protocol>
```

### 3.2 Domain Discovery Protocol (Future)

```xml
<protocol name="Domain Discovery" level="PM" type="routing">

## PURPOSE
Determine which domain handles ambiguous input.

## STEPS

### Step 1: CLASSIFY - Input Type
| Type | Examples |
|------|----------|
| Image only | Product photos, creatives |
| Text only | Commands, questions |
| Image + Text | Product with description |

### Step 2: ANALYZE - Domain Signals
| Signal | Suggests |
|--------|----------|
| Product-like image | Cataloging |
| Marketing creative | Marketing |
| Order/invoice | Operations |

### Step 3: ASSESS - Confidence
| Confidence | Criteria |
|------------|----------|
| HIGH | Multiple signals same domain |
| MEDIUM | Single strong signal |
| LOW | No clear signals |

### Step 4: ROUTE or CLARIFY
- HIGH: Route directly
- MEDIUM: Route with validation flag
- LOW: Ask user

</protocol>
```

---

## 4. Task Specification Contract

Specialists are stateless. PM must pass EVERYTHING needed in explicit task specification.

### 4.1 Task Specification Elements

| Category | Elements |
|----------|----------|
| **Identity** | specialist, domain |
| **Intent** | action, target_entity, target_id |
| **Context** | resolved_context (all references resolved) |
| **Protocols** | protocols_to_apply |
| **User Hints** | Inferences from PM intelligence |
| **Communication** | response_style, user_state |

### 4.2 Example Task Specification

```
TASK SPECIFICATION
==================
Identity:
  - specialist: catalog_specialist
  - domain: catalog

Intent:
  - action: CREATE
  - target_entity: product

Resolved Context:
  - related_entities: Blue Pottery Collection (fam_123)
  - images: [https://storage.../img.jpg]
  - text_input: "add this to the same family"
  - resolved_text: "add product to Blue Pottery Collection"
  - conversation_summary: "User adding to Blue Pottery. Last was vase at 450."
  - relevant_prior_decisions: ["prefers descriptive names"]

Protocols: duplicate_prevention, family_fit, pricing
User Hints: likely_price_range=400-500, style=ceramic
Communication: response_style=efficient
```

---

## 5. Correction Flow

**Problem:** Specialist suggests X. User says "No, Y." Specialist has no memory.

### 5.1 Correction Detection

| Signal | Example | Interpretation |
|--------|---------|----------------|
| Explicit rejection | "No", "Wrong" | Rejects suggestion |
| Alternative provided | "It should be X" | Provides correct answer |
| Frustration | "I said..." | Repeated correction |

### 5.2 PM Response to Correction

1. **IDENTIFY** - What's being corrected?
2. **BUILD** - Correction context:
   ```
   correction_context:
     original_suggestion: "Family A"
     user_rejection: "No, Family B"
     user_preference: "Family B"
     instruction: "Apply user's choice. Do NOT re-evaluate."
   ```
3. **RE-INVOKE** - With override
4. **UPDATE** - PM state with preference

### 5.3 Specialist Handling

When correction_context present:
- Apply user's preference directly
- Skip protocol steps that would re-evaluate
- Acknowledge: "Using [choice] as specified"

---

## 6. Cross-Domain Coordination (Future)

### 6.1 When Tasks Span Domains

| Scenario | Domains | Orchestration |
|----------|---------|---------------|
| Product launch | Catalog + Marketing | Create product, then campaign |
| Customer complaint | Service + Operations | Triage, then resolve |

### 6.2 Cross-Domain Protocol

```xml
<protocol name="Cross-Domain Coordination" level="PM">

### Step 1: DECOMPOSE
Parse into domain components with dependencies.

### Step 2: EXECUTE - Sequential with Context Passing
For each component:
1. Build Task Specification
2. Execute, capture output
3. Extract relevant outputs for next domain
4. Build next Task Specification with cross_domain_context

### Step 3: SYNTHESIZE
Merge results, track entities, report combined outcome.

## CROSS-DOMAIN CONTEXT
cross_domain_context:
  from_domain: "catalog"
  outputs:
    - entity_type: "product"
      entity_id: "prod_123"
      action_taken: "created"
  relevant_for: "Use this product in campaign"

</protocol>
```

### 6.3 Entity Ownership

| Entity | Owner | Can Reference |
|--------|-------|---------------|
| Product | Catalog | Marketing, Operations |
| Campaign | Marketing | - |
| Order | Operations | Service, Finance |

**Rules:**
- Owner can CREATE, UPDATE, DELETE
- Others can READ, REFERENCE
- Conflicts escalate to owner domain

---

## 7. Implementation Roadmap

| Phase | Capability | Prerequisites |
|-------|------------|---------------|
| **Current** | Basic routing | - |
| **Phase 2** | Reference resolution | Stable specialist protocols |
| **Phase 3** | Intent inference | Reference resolution |
| **Phase 4** | User state tracking | Intent inference |
| **Phase 5** | Cross-domain coordination | Second domain active |

---

## 8. Open Questions

- [ ] How explicit should PM be about routing decisions?
- [ ] Should MEDIUM confidence proceed or always ask?
- [ ] How to handle multi-domain inputs?
- [ ] Should routing decisions be logged for learning?

---

**Document Version:** 1.0
**Last Updated:** December 17, 2025
