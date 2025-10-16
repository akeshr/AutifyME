# DeepAgents HITL Architecture Diagrams

Visual reference for the three implementation patterns.

---

## Pattern 1: Current (Runner-Centric) - Production

```
┌────────────────────────────────────────────────────────────────┐
│                       WhatsApp Channel                         │
│              (Receives messages from user)                     │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    WorkflowRunner                              │
│                                                                │
│  1. handle_message(sender, text, media_id)                   │
│  2. _execute_workflow()                                       │
│     ├─ Build raw_payload                                      │
│     ├─ Call _invoke_pm(thread_id, payload)                   │
│     └─ Check for interrupts                                   │
└────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
        No Interrupt│                   │Interrupt
                    ▼                   ▼
              ┌──────────┐      ┌───────────────┐
              │ Workflow │      │ Forward to    │
              │Completes │      │ ApprovalAnalyzer
              │          │      │ (external)    │
              └──────────┘      │               │
                                │ ↓ Returns     │
                                │ BatchApproval │
                                │ Response      │
                                └───────────────┘
                                      │
                                      ▼
                          ┌──────────────────────┐
                          │ Build Command from   │
                          │ approval response    │
                          │                      │
                          │ Command(resume={...})
                          └──────────────────────┘
                                      │
                                      ▼
                          ┌──────────────────────┐
                          │ Execute Command      │
                          │ to resume PM         │
                          └──────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │ Check for completion or new     │
                    │ interrupts, repeat as needed    │
                    └─────────────────────────────────┘
```

**Key Components:**
- RunnerOrchestrates approval flow externally
- ApprovalAnalyzer handles HITL interpretation
- Command built and executed by Runner
- PM stays focused on delegation

**Data Flow:**
```
raw_payload → PM → Department → Interrupt ↓
                                         Runner detects ↓
                              ApprovalAnalyzer ↓
                                    Command ↓
                              Resume execution ↓
                                    Result
```

---

## Pattern 2: Proposed (PM-Centric with Tools) - Recommended

```
┌────────────────────────────────────────────────────────────────┐
│                       WhatsApp Channel                         │
│              (Receives messages from user)                     │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    WorkflowRunner                              │
│                                                                │
│  1. Check checkpoint for pending_interrupts                   │
│  2. Build payload WITH pending_interrupts in state            │
│  3. Call _invoke_pm(thread_id, payload)                      │
│  4. Watch for "APPROVAL_DECISION:" tool output                │
│  5. Intercept and build Command                               │
└────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
                    ▼                    ▼
        ┌───────────────────┐  ┌──────────────────────┐
        │ with pending_     │  │ Initialize initial  │
        │ interrupts        │  │ state with pending   │
        │ state.values      │  │ _interrupts list     │
        │                   │  │                      │
        │ (Get from         │  │ initial_state = {    │
        │ checkpoint)       │  │   "messages": [...], │
        │                   │  │   "pending_interrupts": [...]
        └───────────────────┘  │ }                    │
                │              └──────────────────────┘
                │                       │
                └───────────┬───────────┘
                            ▼
        ┌──────────────────────────────────────────┐
        │ PM Agent (DeepAgents)                    │
        │                                          │
        │  +─────────────────────────────────────+ │
        │  │ PMHITLMiddleware                    │ │
        │  │                                     │ │
        │  │ before_agent():                     │ │
        │  │  • Read pending_interrupts          │ │
        │  │  • Format as human context          │ │
        │  │  • Inject into state                │ │
        │  │    (approval_context)               │ │
        │  └─────────────────────────────────────+ │
        │              │                           │
        │              ▼                           │
        │  ┌──────────────────────────────────┐   │
        │  │ PM Reasoning                     │   │
        │  │                                  │   │
        │  │ "Looking at pending approvals:  │   │
        │  │  - Product X: price looks good  │   │
        │  │  - Description complete         │   │
        │  │  → Call tool to approve"        │   │
        │  └──────────────────────────────────┘   │
        │              │                           │
        │              ▼                           │
        │  ┌──────────────────────────────────┐   │
        │  │ Approval Tools Available:        │   │
        │  │                                  │   │
        │  │ • propose_workflow_resumption()  │   │
        │  │ • reject_workflow_approval()     │   │
        │  │ • request_clarification()        │   │
        │  └──────────────────────────────────┘   │
        │              │                           │
        │              ▼                           │
        │  ┌──────────────────────────────────┐   │
        │  │ Tool Call Output:                │   │
        │  │ "APPROVAL_DECISION: int_1:accept"   │   │
        │  └──────────────────────────────────┘   │
        └──────────────────────────────────────────┘
                            │
                            │ (Output in messages)
                            ▼
        ┌──────────────────────────────────────────┐
        │ WorkflowRunner (Intercepts)              │
        │                                          │
        │ Check messages for:                      │
        │ "APPROVAL_DECISION: <id>:<type>"        │
        │                                          │
        │ Parse approval and build:                │
        │ Command(resume={                         │
        │    "int_1": [{"type": "accept"}]        │
        │ })                                       │
        └──────────────────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────┐
        │ Execute Command                          │
        │ pm.stream(Command, config=config)        │
        │                                          │
        │ Workflow resumes, department executes    │
        └──────────────────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────┐
        │ Check for completion or new interrupts   │
        │ Loop as needed                           │
        └──────────────────────────────────────────┘
```

**Key Advantages Over Pattern 1:**
- PM REASONS about approvals (not external analyzer)
- PM can read pending_interrupts via middleware
- PM can make contextual decisions
- Maintains Runner control
- More "agentic" architecture

**Data Flow:**
```
pending_interrupts ↓ (in state)
    PMHITLMiddleware ↓ (injects context)
         PM reasoning ↓ (with approval context)
              Tool call ↓ (propose_workflow_resumption)
                   Runner intercepts ↓
                      Command ↓
                     Resume ↓
                     Result
```

**State Progression:**

```python
# Initial state from Runner
state = {
    "messages": [...],
    "pending_interrupts": [
        {"interrupt_id": "int_1", "description": "Product approval", ...}
    ]
}
    ↓ (PMHITLMiddleware.before_agent)
state = {
    "messages": [...],
    "pending_interrupts": [...]
    "approval_context": "The following items are waiting...\n1. Product approval (ID: int_1)"
}
    ↓ (PM reasoning with approval_context visible)
    ↓ (PM calls tool)
    ↓
messages = [
    ...,
    AIMessage(content="APPROVAL_DECISION: int_1:accept")
]
    ↓ (Runner intercepts)
    ↓
Command(resume={"int_1": [{"type": "accept"}]})
    ↓
Workflow resumes
```

---

## Pattern 3: Future (Fully Agentic) - Post-v1.0

```
┌────────────────────────────────────────────────────────────────┐
│                       WhatsApp Channel                         │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    WorkflowRunner                              │
│         (Simplified - just message pump)                       │
│                                                                │
│  1. handle_message()                                           │
│  2. _invoke_pm()                                               │
│  3. Check for GraphInterrupt                                   │
│  4. If interrupt: send to user, wait for response              │
│  5. Resume with user response                                  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────┐
        │ PM Agent (DeepAgents)                    │
        │                                          │
        │  +─────────────────────────────────────+ │
        │  │ HumanInTheLoopMiddleware            │ │
        │  │ (from DeepAgents/LangChain)         │ │
        │  │                                     │ │
        │  │ tool_configs = {                    │ │
        │  │     'cataloging_department': {      │ │
        │  │         'allow_accept': True,       │ │
        │  │         'allow_edit': True,         │ │
        │  │         'description': '...'        │ │
        │  │     }                               │ │
        │  │ }                                   │ │
        │  └─────────────────────────────────────+ │
        │              │                           │
        │              ▼                           │
        │  ┌──────────────────────────────────┐   │
        │  │ PM Reasoning                     │   │
        │  │                                  │   │
        │  │ "I need cataloging help,         │   │
        │  │  let me delegate to department"  │   │
        │  └──────────────────────────────────┘   │
        │              │                           │
        │              ▼                           │
        │  ┌──────────────────────────────────┐   │
        │  │ Call: task()                     │   │
        │  │   (implicit subagent tool)       │   │
        │  │                                  │   │
        │  │ → cataloging_department()        │   │
        │  └──────────────────────────────────┘   │
        │              │                           │
        │              ▼                           │
        │  ┌──────────────────────────────────┐   │
        │  │ HumanInTheLoopMiddleware detects │   │
        │  │ tool_configs match:              │   │
        │  │ cataloging_department → interrupt│   │
        │  │                                  │   │
        │  │ Raises GraphInterrupt            │   │
        │  └──────────────────────────────────┘   │
        └──────────────────────────────────────────┘
                            │
                   (GraphInterrupt exception)
                            │
                            ▼
        ┌──────────────────────────────────────────┐
        │ WorkflowRunner                           │
        │                                          │
        │ Catch GraphInterrupt                     │
        │ Extract: interrupted_value =             │
        │   "Product draft for approval"           │
        │                                          │
        │ Send to user via channel                 │
        └──────────────────────────────────────────┘
                            │
                     (User responds)
                            │
                            ▼
        ┌──────────────────────────────────────────┐
        │ WorkflowRunner                           │
        │                                          │
        │ Convert response to Command:             │
        │ Command(resume={...})                    │
        │                                          │
        │ Execute: pm.stream(Command, ...)         │
        └──────────────────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────┐
        │ PM Agent Resumes                         │
        │                                          │
        │ HumanInTheLoopMiddleware handles resume  │
        │ DeepAgents manages all state/commands    │
        │                                          │
        │ Workflow continues...                    │
        └──────────────────────────────────────────┘
```

**Key Differences From Pattern 2:**
- NO custom middleware (DeepAgents built-in)
- NO custom approval tools (auto-managed)
- NO Runner-side Command building (DeepAgents internal)
- Auto pause/resume at tool_configs boundaries
- More truly "agentic" (DeepAgents orchestrates)

**Trade-offs:**
- Less visibility into approval process
- Less control (auto-pauses where tool_configs says)
- Requires DeepAgents v1.0+ stability
- Simpler code but less flexible

---

## State Diagram: Pattern 2 Implementation

```
╔════════════════════════════════════════════════════════════╗
║                     Workflow States                        ║
╚════════════════════════════════════════════════════════════╝

Initial State:
┌──────────────────────────────────┐
│ PENDING_INTERRUPT                │
│                                  │
│ • pending_interrupts: [...]      │
│ • messages: [user_input]         │
│ • status: "awaiting_approval"    │
│                                  │
│ Action: Middleware injects       │
│         approval_context         │
└──────────────────────────────────┘
           │
           ▼
PM Reasoning State:
┌──────────────────────────────────┐
│ PM_REASONING                     │
│                                  │
│ • pending_interrupts: [...]      │
│ • messages: [user, approval_ctx] │
│ • approval_context: "..."        │
│ • status: "analyzing"            │
│                                  │
│ PM: "I see pending approvals,    │
│      analyzing them..."          │
│                                  │
│ Action: PM calls tool            │
└──────────────────────────────────┘
           │
           ▼
Approval Decision State:
┌──────────────────────────────────┐
│ DECISION_PROPOSED                │
│                                  │
│ • messages: [                    │
│     ...,                         │
│     AIMessage(                   │
│       "APPROVAL_DECISION:        │
│        int_1:accept"             │
│     )                            │
│   ]                              │
│ • status: "decision_pending"     │
│                                  │
│ Action: Runner detects output    │
└──────────────────────────────────┘
           │
           ▼
Command Building State:
┌──────────────────────────────────┐
│ COMMAND_READY                    │
│                                  │
│ • command: Command(              │
│     resume={                     │
│       "int_1": [{                │
│         "type": "accept"         │
│       }]                         │
│     }                            │
│   )                              │
│                                  │
│ Action: Execute Command          │
└──────────────────────────────────┘
           │
           ▼
Workflow Resuming State:
┌──────────────────────────────────┐
│ WORKFLOW_RESUMING                │
│                                  │
│ • command: Executed              │
│ • status: "processing"           │
│ • department: Running...         │
│                                  │
│ Action: Department executes      │
│         approved action          │
└──────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ SUCCESS / NEW_INTERRUPT / ERROR  │
│                                  │
│ Loop back if needed              │
└──────────────────────────────────┘
```

---

## Component Interaction: Pattern 2

```
┌──────────────────────────────────────────────────────────────┐
│ RUNNER                                                       │
│                                                              │
│  check_checkpoint()                                          │
│      │                                                       │
│      ▼                                                       │
│  get pending_interrupts ────────────┐                        │
│      │                              │                        │
│      ▼                              │                        │
│  create_payload(                    │                        │
│    messages=[...],                  │                        │
│    pending_interrupts=[...] ◄──────┘                        │
│  )                                  │                        │
│      │                              │                        │
│      └─────────────────────┬────────┘                        │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
         ┌───────────────────────────────────┐
         │ PM AGENT                          │
         │                                   │
         │  PMHITLMiddleware.before_agent()  │
         │      state (with pending_...)     │
         │         │                         │
         │         ▼                         │
         │    read pending_interrupts ───┐   │
         │         │                     │   │
         │         ▼                     │   │
         │    format approval_context    │   │
         │         │                     │   │
         │         ▼                     │   │
         │    return state_update ───┐   │   │
         │                           │   │   │
         │  [middleware complete]    │   │   │
         │         │                 │   │   │
         │         ▼                 │   │   │
         │  PM Reasoning             │   │   │
         │  (sees approval_context)  │   │   │
         │         │                 │   │   │
         │         ▼                 │   │   │
         │  Call: propose_workflow   │   │   │
         │  _resumption()            │   │   │
         │         │                 │   │   │
         │         ▼                 │   │   │
         │  Tool execution ◄─────────┘   │   │
         │         │                     │   │
         │         ▼                     │   │
         │  Return: "APPROVAL_DECISION   │   │
         │           : int_1:accept"    │   │
         │         │                     │   │
         │         ▼                     │   │
         │  Add to messages ◄────────────┘   │
         │         │                         │
         └─────────┼───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ RUNNER                                                       │
│                                                              │
│  stream() iteration:                                         │
│      event["messages"] contains:                             │
│        "APPROVAL_DECISION: int_1:accept"                    │
│         │                                                    │
│         ▼                                                    │
│  Intercept tool output                                       │
│         │                                                    │
│         ▼                                                    │
│  Parse: interrupt_id="int_1", type="accept"                │
│         │                                                    │
│         ▼                                                    │
│  Build Command(resume={"int_1": [{"type": "accept"}]})     │
│         │                                                    │
│         ▼                                                    │
│  Execute: pm.stream(Command, ...)                           │
│         │                                                    │
│         ▼                                                    │
│  [Workflow resumes]                                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Timeline: Implementation & Rollout

```
T0: Current (Pattern 1)
├─ WorkflowRunner orchestrating interrupts
├─ ApprovalAnalyzer external
└─ Production: ✓ Working

T1: Approved (Pattern 2)
├─ Build PMHITLMiddleware
├─ Add approval tools to PM
├─ Update runner to intercept
├─ Test in staging
└─ Deploy to production (1-2 days)

T2: Monitoring (Pattern 2)
├─ Track approval success rate
├─ Monitor PM decision quality
├─ Fine-tune instructions
└─ Gather metrics (1-2 weeks)

T3: Future (Pattern 3)
├─ Wait for DeepAgents v1.0
├─ Evaluate fully-agentic HITL
├─ Consider migration
└─ Implement post-v1.0 (Q1 2026+)
```

---

## Summary: Choose Your Pattern

| When to Use | Pattern | Reason |
|-------------|---------|--------|
| Already working | 1 | Low risk, proven |
| Moving HITL to PM | 2 | Bridge, agentic, safe |
| Full agentic future | 3 | Wait for v1.0 |

