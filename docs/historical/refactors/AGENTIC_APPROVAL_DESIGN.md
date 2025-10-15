# Agentic Approval Architecture

**Status**: Design Phase
**Created**: 2025-10-11
**Purpose**: Comprehensive approval system that handles all user intent permutations

---

## Problem Statement

Current approval is **static and brittle**:
- Hardcoded "approve"/"reject" string matching
- Binary gate instead of conversation continuation
- State corruption when resuming nested subagents
- No support for edits, questions, partial approvals, or multi-action scenarios

---

## Scenario Permutation Matrix

### **Dimension 1: User Intent During Approval**

| Intent | Example | Current Behavior | Should Be |
|--------|---------|------------------|-----------|
| **Binary Approval** | "approve" | ✅ Resume | ✅ Resume |
| **Natural Language Approval** | "looks good!" | ❌ Ignored | ✅ Classify → Resume |
| **Rejection** | "reject" | ✅ Cancel | ✅ Cancel |
| **Natural Language Rejection** | "no thanks" | ❌ Ignored | ✅ Classify → Cancel |
| **Single Field Edit** | "change price to $25" | ❌ Ignored/New workflow | ✅ Edit args → Resume |
| **Multi-Field Edit** | "name should be X and price $25" | ❌ Ignored | ✅ Parse edits → Resume |
| **Conditional Approval** | "approve if price < $50" | ❌ Ignored | ✅ Evaluate condition → Resume or clarify |
| **Question** | "what's the category?" | ❌ New workflow | ✅ Answer → Stay in approval |
| **Clarification** | "can you show me similar products?" | ❌ New workflow | ✅ Execute query → Stay in approval |
| **Defer** | "remind me in 2 hours" | ❌ Stuck | ✅ Schedule reminder → Expire approval |
| **Delegate** | "ask Sarah to approve" | ❌ Stuck | ✅ Transfer approval (future) |
| **Context Switch** | "wait, catalog this other product first" | ❌ State corruption | ✅ Park approval → New workflow |
| **Abandonment** | "never mind, forget it" | ❌ Stuck | ✅ Clear state → Idle |
| **Mixed Intent** | "approve and post to Instagram" | ❌ Partial execute | ✅ Approve + Queue follow-up |

---

### **Dimension 2: Multi-Action Scenarios**

| Scenario | Example | Challenge |
|----------|---------|-----------|
| **Sequential Actions** | Save → Post → Email | Single approval for chain or individual? |
| **Parallel Actions** | Save Product A + Save Product B | Independent approvals, can approve in any order |
| **Conditional Chain** | Save → IF approved THEN Post | Later actions depend on earlier |
| **Cross-Department** | Cataloging + Marketing + Operations | Multiple agents, multiple interrupts |
| **Partial Approval** | "Save product but skip Instagram" | User cherry-picks actions |
| **Batch Operations** | Catalog 10 products | Approve all, approve individually, or approve pattern |

---

### **Dimension 3: Temporal & State Concerns**

| Scenario | Challenge |
|----------|-----------|
| **Out-of-Order Approval** | User has 3 pending approvals, approves #2 first |
| **Conflicting Messages** | User sends "approve" then "wait, reject" in quick succession |
| **Timeout Expiry** | Approval expires after 24h - what happens to state? |
| **Forgot Context** | User approves 3 days later after forgetting what it was |
| **Server Restart** | Approval pending when server crashes - can we recover? |
| **Concurrent Workflows** | User sends new product while approval pending |
| **Race Conditions** | User sends message while webhook processing approval |

---

### **Dimension 4: Nested Agent Complexity**

| Layer | Agent | Interrupt Source | Resume Target | State Owner |
|-------|-------|------------------|---------------|-------------|
| 1 | PM | Never interrupts | N/A | PM checkpoint |
| 2 | Department (via task tool) | HITL on save_product | **Department** | Nested checkpoint |
| 3 | Specialist (via dept tool) | Could interrupt (future) | **Specialist** | Nested checkpoint |
| 4 | Deterministic Tool | Never interrupts | N/A | Tool state |

**Key Insight**: Resume must target the **originating agent** (Layer 2/3), NOT the PM (Layer 1).

---

### **Dimension 5: Approval Context Richness**

What information does user need to make informed decision?

| Context Element | Why Needed | Example |
|----------------|------------|---------|
| **Action Description** | What will happen | "Save product to catalog" |
| **Structured Data Preview** | What's being saved | Product name, price, sizes, etc. |
| **Visual Preview** | Confirm image/media | Thumbnail of product image |
| **Alternatives** | Other options | "Similar product exists: Merge or create new?" |
| **Risk Assessment** | Why approval needed | "Price exceeds $100 threshold" |
| **Edit Options** | What can be changed | "Edit: name, price, description" |
| **Workflow Chain** | What happens next | "After saving, I'll post to Instagram" |
| **Timeout Policy** | What happens if ignored | "Auto-approve in 24h" |

---

## Architectural Principles

### **Principle 1: Approval is Conversation Continuation, Not Mode**

```python
# ❌ Current: Binary mode switch
if _is_approval_message(text):
    handle_approval(sender, text)
else:
    handle_message(sender, text)

# ✅ Agentic: PM always handles, with approval context
handle_message(sender, text)  # PM sees approval_context in state
```

**Rationale**: User doesn't think "I'm in approval mode" - they just talk naturally.

---

### **Principle 2: Approval State is Structured Metadata, Not Message History**

```python
# ❌ Current: Approval pollutes message history
messages.append(HumanMessage(content="approve"))  # Breaks HITL validation

# ✅ Agentic: Approval is state metadata
state.approval_queue = [
    ApprovalRequest(
        id="interrupt_123",
        action="save_product",
        agent_source="cataloging_department",
        checkpoint_ns="task:cataloging_department",
        preview={"name": "Product X", "price": 25},
        created_at=timestamp,
        expires_at=timestamp + 24h,
    )
]
```

**Rationale**: Approval is business logic, not conversation content.

---

### **Principle 3: Resume Targets Originating Agent, Not PM**

```python
# ❌ Current: Resume PM → task tool re-invokes dept with stale state
pm.stream(Command(resume={...}), config={"thread_id": thread_id})

# ✅ Agentic: Resume department directly with isolated checkpoint
dept.stream(
    Command(resume={interrupt_id: {...}}),
    config={
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": approval.checkpoint_ns,  # Isolated namespace
        }
    }
)
```

**Rationale**: Avoids task tool re-invocation and message history corruption.

---

### **Principle 4: PM Has Approval-Aware Tools**

PM gets specialized tools to manage approval lifecycle:

```python
@tool
def resume_approved_action(approval_id: str, edits: dict | None = None):
    """Resume a pending action with optional edits."""
    ...

@tool
def cancel_pending_action(approval_id: str, reason: str):
    """Cancel a pending action."""
    ...

@tool
def answer_approval_question(approval_id: str, question: str):
    """Answer user question about pending action without resuming."""
    ...

@tool
def park_approval(approval_id: str):
    """Park approval to handle new request, can resume later."""
    ...
```

**Rationale**: PM orchestrates approval lifecycle naturally through tools.

---

### **Principle 5: Multi-Action Approval Queue**

```python
class ApprovalQueue:
    """Manages multiple pending approvals with dependencies."""

    approvals: list[ApprovalRequest]  # Ordered queue

    def add(self, request: ApprovalRequest):
        """Add approval to queue with dependency tracking."""

    def next_pending(self) -> ApprovalRequest | None:
        """Get next approvable action (respecting dependencies)."""

    def resolve(self, approval_id: str, decision: ApprovalDecision):
        """Resolve approval and update dependencies."""
```

**Rationale**: Users will have multiple pending actions, need to track dependencies.

---

## State Schema Design

### **ApprovalRequest**

```python
@dataclass
class ApprovalRequest:
    """Single pending approval with full context."""

    # Identity
    id: str  # Interrupt ID from LangGraph
    thread_id: str
    created_at: datetime
    expires_at: datetime | None

    # Action Context
    action: str  # "save_product", "post_instagram", etc.
    action_description: str  # Human-readable: "Save product to catalog"
    agent_source: str  # "cataloging_department"
    checkpoint_ns: str  # "task:cataloging_department" for resume

    # Approval Preview
    preview_data: dict[str, Any]  # Structured data for user review
    preview_message: str  # Formatted preview for WhatsApp
    media_path: str | None  # Visual preview if applicable

    # Workflow Context
    dependencies: list[str]  # Other approval IDs that must complete first
    follow_up_actions: list[str]  # What happens after approval
    risk_level: Literal["low", "medium", "high"]

    # Edit Configuration
    editable_fields: list[str]  # Fields user can edit
    validation_schema: dict  # Pydantic schema for edits

    # State
    status: Literal["pending", "expired", "parked", "resolved"]
    resolution: ApprovalDecision | None
```

### **ApprovalDecision**

```python
class ApprovalDecision(BaseModel):
    """Structured decision from user message classification."""

    intent: Literal[
        "approve",
        "approve_with_edits",
        "reject",
        "question",
        "defer",
        "park",
        "abandon"
    ]

    # For approve_with_edits
    edited_fields: dict[str, Any] | None = None

    # For question
    question_text: str | None = None
    clarification_needed: list[str] | None = None

    # For defer
    defer_until: datetime | None = None

    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str  # Why did LLM classify this way?
```

### **Enhanced PM State**

```python
class ProjectManagerState(TypedDict):
    # Existing
    messages: Annotated[Sequence[BaseMessage], operator.add]
    company_profile: dict

    # NEW: Approval Queue
    approval_queue: list[ApprovalRequest]
    active_approval_id: str | None  # Currently discussing

    # NEW: Approval Context in Conversation
    approval_mode: bool  # Are we discussing pending approvals?
    last_approval_interaction: datetime | None
```

---

## Component Design

### **1. ApprovalIntentClassifier**

```python
class ApprovalIntentClassifier:
    """LLM-powered intent classification for approval messages."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm.with_structured_output(ApprovalDecision)

    def classify(
        self,
        user_message: str,
        approval_context: ApprovalRequest,
        conversation_history: list[BaseMessage],
    ) -> ApprovalDecision:
        """Classify user intent given approval context."""

        prompt = f"""You are analyzing a user's response to a pending approval request.

PENDING ACTION:
{approval_context.action_description}

PREVIEW:
{json.dumps(approval_context.preview_data, indent=2)}

EDITABLE FIELDS: {', '.join(approval_context.editable_fields)}

USER MESSAGE:
{user_message}

Classify the user's intent and extract relevant details.

Examples:
- "looks good" → approve
- "change price to $25" → approve_with_edits (edited_fields: {{"price": 25}})
- "what category is this?" → question (question_text: "what category is this?")
- "never mind" → reject
- "remind me later" → defer
- "wait, catalog this other product first" → park
"""

        return self.llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=user_message)
        ])
```

---

### **2. ApprovalQueueManager**

```python
class ApprovalQueueManager:
    """Manages approval queue with dependencies and expiration."""

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def enqueue(
        self,
        thread_id: str,
        request: ApprovalRequest,
    ) -> None:
        """Add approval to thread's queue."""

        queue = self.storage.get_approval_queue(thread_id) or []
        queue.append(request)
        self.storage.save_approval_queue(thread_id, queue)

    def get_next_pending(self, thread_id: str) -> ApprovalRequest | None:
        """Get next approvable item (no unresolved dependencies)."""

        queue = self.storage.get_approval_queue(thread_id) or []

        for approval in queue:
            if approval.status != "pending":
                continue

            # Check if expired
            if approval.expires_at and datetime.now() > approval.expires_at:
                approval.status = "expired"
                continue

            # Check dependencies
            if all(self._is_resolved(dep, queue) for dep in approval.dependencies):
                return approval

        return None

    def resolve(
        self,
        thread_id: str,
        approval_id: str,
        decision: ApprovalDecision,
    ) -> ApprovalRequest:
        """Mark approval as resolved and update queue."""

        queue = self.storage.get_approval_queue(thread_id)

        for approval in queue:
            if approval.id == approval_id:
                approval.status = "resolved"
                approval.resolution = decision
                break

        self.storage.save_approval_queue(thread_id, queue)
        return approval

    def _is_resolved(self, approval_id: str, queue: list[ApprovalRequest]) -> bool:
        """Check if approval is resolved."""
        for approval in queue:
            if approval.id == approval_id:
                return approval.status == "resolved"
        return False
```

---

### **3. Enhanced InterruptCoordinator**

```python
class InterruptCoordinator:
    """Enhanced with approval queue and intent classification."""

    def __init__(
        self,
        state_manager: StateManager,
        queue_manager: ApprovalQueueManager,
        classifier: ApprovalIntentClassifier,
    ):
        self.state = state_manager
        self.queue = queue_manager
        self.classifier = classifier

    def process_interrupt(
        self,
        interrupt: Interrupt,
        thread_id: str,
        pm_state: dict[str, Any],
        agent_source: str,  # NEW: Which agent interrupted
        checkpoint_ns: str,  # NEW: Namespace for resume
        media_path: Path | None = None,
    ) -> ApprovalRequest:
        """Create approval request from interrupt and enqueue."""

        tool_calls = self._extract_tool_calls(interrupt, pm_state)
        save_call = self._find_save_product(tool_calls)
        draft = self._parse_draft(save_call["args"])

        # Build rich approval request
        request = ApprovalRequest(
            id=interrupt.id or save_call["id"],
            thread_id=thread_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24),

            action="save_product",
            action_description="Save product to catalog",
            agent_source=agent_source,
            checkpoint_ns=checkpoint_ns,

            preview_data=draft.model_dump(),
            preview_message=self._format_preview(draft),
            media_path=str(media_path) if media_path else None,

            dependencies=[],
            follow_up_actions=[],
            risk_level="low",

            editable_fields=["name", "description", "price", "sizes", "colors"],
            validation_schema=Product.model_json_schema(),

            status="pending",
            resolution=None,
        )

        # Enqueue
        self.queue.enqueue(thread_id, request)

        return request

    def handle_approval_message(
        self,
        thread_id: str,
        user_message: str,
        conversation_history: list[BaseMessage],
    ) -> tuple[ApprovalDecision, ApprovalRequest | None]:
        """Classify intent and return decision + affected approval."""

        # Get next pending approval
        approval = self.queue.get_next_pending(thread_id)
        if not approval:
            return None, None

        # Classify intent
        decision = self.classifier.classify(
            user_message=user_message,
            approval_context=approval,
            conversation_history=conversation_history,
        )

        return decision, approval

    def execute_decision(
        self,
        thread_id: str,
        approval: ApprovalRequest,
        decision: ApprovalDecision,
    ) -> Any:
        """Execute approval decision (resume, answer question, etc.)."""

        if decision.intent == "reject" or decision.intent == "abandon":
            self.queue.resolve(thread_id, approval.id, decision)
            return None

        if decision.intent == "question":
            # Answer question, don't resolve approval yet
            answer = self._answer_question(approval, decision.question_text)
            return {"type": "question_answer", "answer": answer}

        if decision.intent == "defer":
            approval.expires_at = decision.defer_until
            self.queue.resolve(thread_id, approval.id, decision)
            return {"type": "deferred", "until": decision.defer_until}

        if decision.intent == "park":
            approval.status = "parked"
            self.queue.resolve(thread_id, approval.id, decision)
            return {"type": "parked"}

        # Approve or approve_with_edits
        edited_args = decision.edited_fields if decision.intent == "approve_with_edits" else None

        result = self._resume_workflow(
            approval=approval,
            edited_args=edited_args,
        )

        self.queue.resolve(thread_id, approval.id, decision)

        return result

    def _resume_workflow(
        self,
        approval: ApprovalRequest,
        edited_args: dict | None,
    ) -> CatalogingResult | None:
        """Resume workflow at originating agent level."""

        # Build resume command
        command_type = "accept" if not edited_args else "edit"
        command = Command(
            resume={
                approval.id: {
                    "type": command_type,
                    "args": edited_args,
                }
            }
        )

        # ✅ Resume at DEPARTMENT level using checkpoint namespace
        dept = self._get_agent_by_source(approval.agent_source)

        config = {
            "configurable": {
                "thread_id": approval.thread_id,
                "checkpoint_ns": approval.checkpoint_ns,  # Isolated namespace
            }
        }

        logger.info(
            "Resuming workflow at department level",
            extra={
                "agent": approval.agent_source,
                "checkpoint_ns": approval.checkpoint_ns,
                "command_type": command_type,
            }
        )

        # Stream and extract result
        for event in dept.stream(command, config=config):
            if result := self._extract_result(event):
                return result

        return None

    def _get_agent_by_source(self, agent_source: str):
        """Factory to create agent by source name."""
        if agent_source == "cataloging_department":
            from autifyme_agents.departments.cataloging_department import create_cataloging_department
            return create_cataloging_department(
                checkpointer=self.state.storage.get_checkpointer(),
                storage=self.state.storage,
                enable_hitl=True,
            )

        raise ValueError(f"Unknown agent source: {agent_source}")
```

---

## Webhook Flow Changes

### **Current (Broken)**

```python
@app.post("/webhook")
async def receive(request: Request):
    text = message.get("text", {}).get("body")

    # ❌ Binary routing
    if _is_approval_message(text):
        _get_runner().handle_approval(sender, text)
    else:
        _get_runner().handle_message(sender, text, media_id)
```

### **Agentic (Fixed)**

```python
@app.post("/webhook")
async def receive(request: Request):
    text = message.get("text", {}).get("body")
    media_id = message.get("image", {}).get("id")

    # ✅ Unified routing - PM handles all messages with context
    _get_runner().handle_message(
        sender=sender,
        text=text,
        media_id=media_id,
    )

    # PM sees approval_queue in state and decides:
    # - Resume pending approval if message indicates approval
    # - Answer questions about pending approval
    # - Park approval and handle new request
    # - Proceed with new workflow if no pending approvals
```

---

## PM Tools for Approval Management

PM gets new tools to manage approval lifecycle:

```python
@tool
def check_pending_approvals() -> list[dict]:
    """Check if there are pending approvals requiring user attention.

    Returns list of pending approvals with previews.
    """
    ...

@tool
def resume_approved_action(
    approval_id: str,
    edited_fields: dict[str, Any] | None = None,
) -> CatalogingResult:
    """Resume a pending action after user approval.

    Use this when user approves an action, optionally with edits.
    """
    ...

@tool
def cancel_pending_action(approval_id: str, reason: str) -> None:
    """Cancel a pending action after user rejection."""
    ...

@tool
def answer_approval_question(approval_id: str, question: str) -> str:
    """Answer user question about a pending approval without resuming.

    Use this when user asks clarifying questions during approval.
    """
    ...

@tool
def park_approval_for_new_request(approval_id: str) -> None:
    """Temporarily park a pending approval to handle a new user request.

    Use this when user wants to do something else first.
    """
    ...
```

PM's system prompt gets updated:

```
You are the Project Manager for AutifyME.

APPROVAL CONTEXT:
- You have {len(approval_queue)} pending approvals requiring user attention
- Active approval: {active_approval.action_description if active_approval else "None"}

When user sends a message:
1. Check if you have pending approvals
2. If yes, analyze if message relates to approval:
   - Natural approval: "looks good", "yes", "go ahead" → resume_approved_action
   - Edits: "change price to $25" → resume_approved_action with edited_fields
   - Questions: "what category?" → answer_approval_question
   - Rejection: "no", "cancel" → cancel_pending_action
   - New request: "catalog this other product" → park_approval_for_new_request
3. If no pending approvals, proceed with delegation to departments

NEVER assume binary "approve"/"reject" - understand user intent naturally.
```

---

## Implementation Phases

### **Phase 1: Fix State Corruption (Immediate)** ✅

**Goal**: Resolve Trace 2 error - resume at department level

**Changes**:
1. `InterruptCoordinator.resume_workflow()` resumes department directly
2. Use `checkpoint_ns` for isolated state
3. Track `agent_source` in approval metadata

**Test**: Create product → Interrupt → Approve → Should save without ValueError

---

### **Phase 2: Remove Static Routing (Week 1)** 🔄

**Goal**: Unify message handling - PM handles all messages

**Changes**:
1. Remove `_is_approval_message()` from webhook
2. Remove `WorkflowRunner.handle_approval()` method
3. All messages go through `handle_message()`
4. PM gets `approval_queue` in state

**Test**: Create product → Interrupt → Send "looks good" → PM recognizes approval context

---

### **Phase 3: Intent Classification (Week 2)** 🆕

**Goal**: LLM classifies approval intent instead of keywords

**Changes**:
1. Implement `ApprovalIntentClassifier`
2. PM uses `check_pending_approvals` tool
3. PM classifies user message against pending approval
4. Support approve/edit/question/reject

**Test**: All scenario matrix Row 1 (User Intent) scenarios pass

---

### **Phase 4: Approval Queue (Week 3)** 🆕

**Goal**: Support multiple pending approvals

**Changes**:
1. Implement `ApprovalQueueManager`
2. Support approval dependencies
3. Support out-of-order resolution
4. Expiration handling

**Test**: Chain of 3 actions → Interrupt 3 times → User approves #2 first → Works correctly

---

### **Phase 5: Rich Preview & Edit Validation (Week 4)** 🆕

**Goal**: Better approval UX with structured edits

**Changes**:
1. Rich approval preview formatting
2. Pydantic validation for edited fields
3. Visual previews (images, formatted data)
4. Edit suggestions from PM

**Test**: Complex multi-field edit → "change name to X, price to $25, add size L" → Validates and applies

---

## Test Scenario Checklist

### **Basic Flows**
- [ ] Approve with "approve" keyword
- [ ] Approve with natural language "looks good"
- [ ] Reject with "reject" keyword
- [ ] Reject with natural language "no thanks"

### **Edit Scenarios**
- [ ] Single field edit: "change price to $25"
- [ ] Multi-field edit: "name should be X and price $25"
- [ ] Invalid edit: "price should be abc" → PM asks for clarification
- [ ] Edit non-editable field → PM explains limitation

### **Question Scenarios**
- [ ] Question about draft: "what category is this?"
- [ ] Request comparison: "show me similar products"
- [ ] Clarification: "what happens after I approve?"
- [ ] Stay in approval loop after answering

### **Context Switch**
- [ ] Park approval: "wait, catalog this other product first"
- [ ] Abandon: "never mind, forget it"
- [ ] Defer: "remind me in 2 hours"

### **Multi-Action**
- [ ] Sequential approvals: A → B → C
- [ ] Out-of-order: Approve B before A (if no dependency)
- [ ] Partial approval: "approve A but not B"
- [ ] Conflicting messages: "approve" then "wait, reject"

### **Edge Cases**
- [ ] Approval expires → Auto-reject or notify
- [ ] New request during approval → Park or cancel
- [ ] Server restart during approval → Resume from checkpoint
- [ ] Duplicate approval message → Idempotent handling
- [ ] Approval for wrong product → PM catches and clarifies

---

## Success Criteria

1. ✅ **No more ValueError from HITL middleware** - State corruption fixed
2. ✅ **Natural language approval works** - Not dependent on keywords
3. ✅ **Edit support** - Users can modify fields during approval
4. ✅ **Question answering** - PM answers without breaking approval flow
5. ✅ **Multi-action queue** - Multiple pending approvals tracked correctly
6. ✅ **Context switch** - User can park approval and start new request
7. ✅ **Resumption reliability** - Works after server restart, timeout, race conditions

---

## Open Questions for Discussion

1. **Approval timeout policy**: Auto-approve, auto-reject, or notify?
2. **Multi-user approvals**: How do we handle approval delegation to managers?
3. **Approval history**: Do we show "you approved this 3 days ago"?
4. **Batch operations**: "Approve all" vs individual approval for 10 products?
5. **Conditional approvals**: "Approve if X, otherwise Y" - how complex?
6. **Learning from approvals**: Track approval patterns to reduce future interrupts?

---

## Related Documents

- `LANGCHAIN_V1_FEATURES.md` - HITL middleware documentation
- `WHATSAPP_CATALOGING_WORKFLOW.md` - Current workflow implementation
- `PROJECT_MANAGER_DESIGN.md` - PM architecture
