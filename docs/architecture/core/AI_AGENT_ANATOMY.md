# AI Agent Anatomy: Foundational Architecture

**Created:** December 13, 2025
**Status:** Reference Architecture
**Source:** [IBM Technology - AI Agent Anatomy](https://youtu.be/CAKGKkWf0tI)
**Purpose:** Foundational framework for understanding and designing autonomous AI agents

---

## Executive Summary

All autonomous AI agents share a common four-component architecture:

1. **SENSE** - Perception layer that ingests data from the environment
2. **THINK** - Reasoning layer that processes inputs with knowledge and policy
3. **ACT** - Execution layer that generates outputs and performs actions
4. **FEEDBACK** - Learning loop that evaluates performance and drives improvement

This framework provides a mental model for designing robust agent systems and identifying architectural gaps.

---

## The Four-Layer Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         FEEDBACK LOOP                         │
│              (Self-Evaluation + Human Feedback)               │
└──────────────────────────────────────────────────────────────┘
       ▲                                                  │
       │                                                  ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│    SENSE     │ ───► │    THINK     │ ───► │     ACT      │
│              │      │              │      │              │
│ - Text/NLP   │      │ - Knowledge  │      │ - Generate   │
│ - Sensors    │      │ - Policy     │      │ - Control    │
│ - APIs       │      │ - Reasoning  │      │ - Execute    │
└──────────────┘      └──────────────┘      └──────────────┘
```

---

## Layer 1: SENSE (Perception)

**Purpose:** Bring external information into the system

### Input Channels

| Channel | Description | Examples |
|---------|-------------|----------|
| **Text/NLP** | Natural language input | Chat messages, commands, emails |
| **Sensors** | Physical world data | Camera (vision), microphone (audio), IoT devices |
| **APIs** | Structured data from systems | REST APIs, webhooks, database queries |
| **Events** | Trigger-based inputs | Scheduled tasks, state changes, alerts |

**Design Principle:** Agents need multiple sensory modalities to operate in complex environments.

---

## Layer 2: THINK (Reasoning)

**Purpose:** Process inputs with context to make intelligent decisions

This layer has three sub-components that work together:

### 2A. Knowledge Base

**What it stores:**
- **Facts** - Immutable truths relevant to the domain
- **Rules** - Constraints and relationships that govern behavior
- **Context** - Situational information that affects decisions

**Data Sources:**
| Source | Purpose |
|--------|---------|
| **Database** | Persistent facts and historical data |
| **RAG (Retrieval Augmented Generation)** | Dynamically retrieved relevant context |
| **Vector Stores** | Semantic search for similar past situations |
| **External APIs** | Real-time data (maps, prices, availability) |

### 2B. Policy Information

**What it defines:**
- **Goals** - High-level objectives the system should achieve
- **Objectives** - Specific measurable outcomes
- **Priorities** - Ranking when multiple goals conflict

**Example (Business Travel):**
- Goal: Book cost-effective travel that meets company policy
- Objectives: Stay within $200/night hotel cap, use preferred airlines
- Priorities: Policy compliance > convenience > cost optimization

### 2C. Reasoning Engine

**Core Capabilities:**

| Capability | Description |
|------------|-------------|
| **If-Then-Else Logic** | Conditional decision-making |
| **Planning** | Sequencing actions to achieve goals |
| **Task Decomposition** | Breaking complex tasks into subtasks |
| **Machine Learning** | Pattern recognition and prediction |
| **LLM Processing** | Natural language understanding and chain-of-thought reasoning |

**Process Flow:**
```
Inputs (Sense) + Knowledge + Policy
          │
          ▼
    [Reasoning Engine]
    - Analyze situation
    - Decompose task
    - Plan approach
    - Consider constraints
          │
          ▼
    Decision/Action Plan
```

---

## Layer 3: ACT (Execution)

**Purpose:** Execute decisions and interact with the external world

### Output Types

| Output Type | Description | Examples |
|-------------|-------------|----------|
| **Generate** | Create content | Text responses, speech, alerts, video |
| **Read/Write DB** | Persist or retrieve data | Save state, log actions, query records |
| **Control** | Physical world interaction | Robotic actuators, autonomous vehicle controls |
| **API Calls** | Trigger external systems | Book reservations, send notifications, update CRM |

**Design Principle:** Actions should be observable and reversible when possible (enables feedback).

---

## Layer 4: FEEDBACK (Learning Loop)

**Purpose:** Continuous improvement through evaluation and adaptation

### Two Feedback Mechanisms

#### 1. Self-Evaluation
- Agent compares output against goals/objectives
- Runs hypothetical scenarios to test alternative approaches
- Detects when outputs don't match intended outcomes
- Triggers self-correction without human intervention

#### 2. RLHF (Reinforcement Learning with Human Feedback)
- Explicit user feedback (thumbs up/down, ratings, surveys)
- Human overrides incorrect actions
- System learns user preferences over time
- Personalizes behavior based on feedback history

### Feedback Data Flow

```
[Action Executed]
      │
      ├─► Self-Evaluation: Does output match goal?
      │         │
      │         ├─► YES: Reinforce pattern
      │         └─► NO:  Adjust approach
      │
      └─► Human Feedback: User satisfaction?
                │
                ├─► Positive: Strengthen decision weights
                └─► Negative: Explore alternatives
```

**Critical Insight:** Without feedback, agents cannot improve. This layer transforms static automation into learning systems.

---

## Concrete Example: Travel Booking Agent

**Scenario:** Book business travel for an upcoming conference

### SENSE Layer
**Inputs:**
- Travel dates (from calendar or chat input)
- Destination city
- Event location (conference venue)

### THINK Layer

**Knowledge Base:**
- User preferences (preferred airlines, hotel chains)
- Personal habits (runs daily, needs running routes)
- Maps and location data
- Real-time prices and availability

**Policy:**
- IBM business travel policy (hotel cap: $200/night in this city)
- Preferred travel partners (Delta, Marriott)
- Must book within company guidelines

**Reasoning:**
1. Identify conference venue location
2. Search hotels near venue + good running routes
3. Filter by price cap and preferred chains
4. Check flight options on preferred airlines
5. Optimize for: policy compliance > convenience > cost

### ACT Layer
**Actions:**
- Call airline reservation API
- Call hotel reservation API
- Generate confirmation emails
- Add bookings to calendar
- Send itinerary to user

### FEEDBACK Layer
**Evaluation:**
- Post-trip survey: "Did this meet your needs?"
- User gives thumbs up/down
- System notes: "User preferred Courtyard over Residence Inn despite both meeting criteria"
- Future bookings prioritize Courtyard in similar situations

**Self-Correction:**
- Agent tests alternative hotel choices against preferences
- Verifies it selected optimal running route location
- Confirms it didn't exceed budget constraints

---

## Key Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Multi-modal sensing** | Rich inputs enable better decisions |
| **Separate knowledge from logic** | Knowledge changes frequently; reasoning patterns are stable |
| **Explicit policy layer** | Goals/priorities must be queryable and auditable |
| **Task decomposition** | Complex problems become manageable subtasks |
| **Observable actions** | Can't evaluate what you can't measure |
| **Mandatory feedback** | Learning requires evaluation |
| **Self-awareness** | Agents should critique own outputs before acting |

---

## References

- **Video Source:** IBM Technology - "AI Agent Anatomy Explained" - https://youtu.be/CAKGKkWf0tI
- **Key Concepts:** Sense-Think-Act architecture, RLHF, Task Decomposition, Policy-driven reasoning
