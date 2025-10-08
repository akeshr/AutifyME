# Workflow Orchestration Architecture

**Status**: ✅ Implemented
**Date**: 2025-10-08

---

## Problem

Original `WhatsAppCatalogingRunner` (800 lines) violated Single Responsibility:
- 10+ distinct responsibilities in one class
- WhatsApp logic embedded throughout
- Not reusable for SMS/Telegram
- Hard to test (requires mocking 7+ dependencies)

---

## Solution

Decomposed into 6 focused components with clear separation:

```
workflows/
├── orchestration/              # Generic, channel-agnostic
│   ├── runner.py              # Workflow coordination
│   ├── interrupt_coordinator.py # HITL handling
│   ├── state_manager.py       # Approval persistence
│   └── recovery_strategy.py   # Error recovery
└── channels/                   # Channel-specific
    ├── protocol.py            # Abstract interface
    └── whatsapp/adapter.py    # WhatsApp implementation
```

---

## Architecture

### MessagingChannel Protocol

Abstract interface for all messaging platforms:

```python
class MessagingChannel(Protocol):
    def send_text(self, recipient: str, message: str, ...) -> dict: ...
    def send_approval_request(self, recipient: str, draft: Product) -> dict: ...
    def send_completion(self, recipient: str, result: CatalogingResult) -> dict: ...
    def send_error(self, recipient: str, error_type: str, ...) -> dict: ...
    def download_media(self, media_id: str) -> Path | None: ...
    def format_thread_id(self, sender: str) -> str: ...
```

### WorkflowRunner

Generic orchestrator (channel-agnostic):

```python
runner = WorkflowRunner(
    channel=WhatsAppChannel(),  # Strategy Pattern - swap for SMS/Telegram
    storage=storage,
    # Optional DI for testing:
    interrupt_coordinator=...,
    state_manager=...,
    recovery_strategy=...,
)

# API unchanged:
runner.handle_message(sender, text, media_id)
runner.handle_approval(sender, "approve")
```

**Responsibilities:**
- Orchestrate workflow execution
- Invoke Project Manager
- Detect interrupts and delegate
- Thread-safe per-sender coordination

**NOT responsible for:**
- Channel communication (delegates to `channel`)
- Interrupt logic (delegates to `interrupt_coordinator`)
- State persistence (delegates to `state_manager`)
- Recovery logic (delegates to `recovery_strategy`)

### InterruptCoordinator

Handles HITL interrupts:

```python
coordinator = InterruptCoordinator(state_manager)

# Process interrupt from PM
request = coordinator.process_interrupt(
    interrupt=langgraph_interrupt,
    thread_id="whatsapp:user123",
    pm_state=last_state,
)
# Returns: ApprovalRequest(draft=Product(...), interrupt_id="...")

# Resume after approval
result = coordinator.resume_workflow(
    thread_id="whatsapp:user123",
    decision="approve",
    pm_factory=create_pm_func,
)
```

### StateManager

Approval state persistence:

```python
state = StateManager(storage)

state.save_pending_approval(thread_id, approval_data, media_path)
approval = state.get_pending_approval(thread_id)
has_pending = state.has_pending_approval(thread_id)
state.delete_pending_approval(thread_id)
```

### RecoveryStrategy

Error recovery and abandonment detection:

```python
recovery = RecoveryStrategy(state_manager, checkpointer_factory)

# Proactive: detect abandonment
if recovery.should_clear_state(thread_id, new_has_media):
    recovery.clear_orphaned_state(thread_id)

# Reactive: auto-recover from errors
try:
    invoke_pm(...)
except ValueError as e:
    if "INVALID_CHAT_HISTORY" in str(e):
        recovery.auto_recover(thread_id)
```

### WhatsAppChannel

WhatsApp-specific implementation:

```python
channel = WhatsAppChannel(
    whatsapp_client=WhatsAppClient(),
    media_client=WhatsAppMediaClient(),
)

# Implements MessagingChannel protocol
channel.send_approval_request(sender, draft)
# → Formats with WhatsApp markdown: *bold*, newlines, etc.

channel.format_thread_id(sender)
# → "whatsapp:919876543210"
```

---

## Adding New Channels

**SMS Example (~150 lines):**

```python
# workflows/channels/sms/adapter.py
class SMSChannel:
    def send_text(self, recipient, message, ...):
        # 160 char limit
        return twilio_client.send(recipient, message[:160])

    def send_approval_request(self, recipient, draft):
        # Plain text, no markdown
        msg = f"Product: {draft.name} | Price: {draft.price} | Reply YES/NO"
        return self.send_text(recipient, msg)

    def download_media(self, media_id):
        return twilio_client.download_mms(media_id)

    def format_thread_id(self, sender):
        return f"sms:{sender}"

# entrypoints/sms_webhook.py
runner = WorkflowRunner(channel=SMSChannel(), storage=storage)
```

**That's it.** ~150 lines total.

---

## Migration

### Before
```python
from autifyme_agents.workflows.whatsapp_cataloging_runner import WhatsAppCatalogingRunner

runner = WhatsAppCatalogingRunner(storage=storage)
```

### After
```python
from autifyme_agents.workflows.orchestration.runner import WorkflowRunner
from autifyme_agents.workflows.channels.whatsapp.adapter import WhatsAppChannel

channel = WhatsAppChannel()
runner = WorkflowRunner(channel=channel, storage=storage)
```

**API unchanged** - `handle_message()` and `handle_approval()` work identically.

---

## Benefits

| Metric | Before | After |
|--------|--------|-------|
| Max file size | 800 lines | 450 lines |
| Single Responsibility | ❌ Violated | ✅ Enforced |
| Multi-channel | ❌ No | ✅ <200 lines/channel |
| Testability | ❌ Hard | ✅ Isolated components |
| Maintainability | ❌ Poor | ✅ Changes localized |

---

## Design Principles

1. **Single Responsibility** - Each component does ONE thing
2. **Dependency Inversion** - Depend on abstractions (Protocol), not concretions
3. **Strategy Pattern** - Channel behavior injected
4. **Open/Closed** - Open for extension (new channels), closed for modification
5. **Interface Segregation** - Clean, focused interfaces

---

## Testing

### Unit Tests
Each component testable in isolation with mocks:

```python
def test_state_manager():
    mock_storage = create_autospec(StorageInterface)
    manager = StateManager(mock_storage)
    manager.save_pending_approval(...)
    mock_storage.save_pending_approval.assert_called_once()
```

### Integration Tests
```python
def test_runner_with_interrupt(mock_channel):
    runner = WorkflowRunner(channel=mock_channel, storage=...)
    runner.handle_message("user", "catalog shoes", None)
    mock_channel.send_approval_request.assert_called_once()
```

### E2E Test
```python
# test_cataloging_workflow_clean.py
channel = WhatsAppChannel(test_client, test_media)
runner = WorkflowRunner(channel=channel, ...)
runner.handle_message(sender, text, media_id)
# ✅ PASS
```

---

## Files

### Created
```
workflows/orchestration/
├── runner.py                   (450 lines)
├── interrupt_coordinator.py    (287 lines)
├── state_manager.py            (113 lines)
└── recovery_strategy.py        (129 lines)

workflows/channels/
├── protocol.py                 (189 lines)
└── whatsapp/adapter.py         (247 lines)
```

### Modified
```
entrypoints/whatsapp_webhook.py    (migrated)
test_cataloging_workflow_clean.py  (migrated)
```

### Deprecated
```
workflows/whatsapp_cataloging_runner.py  (keep for rollback, delete after validation)
```

---

## Validation

**Smoke test**: ✅ PASS

```bash
$ uv run python test_cataloging_workflow_clean.py
✅ Runner ready (Project Manager orchestrated with refactored architecture)
✅ SUCCESS - All systems operational
```

---

## Next Steps

1. **Production validation** - Monitor for 1-2 weeks
2. **Unit tests** - Complete test coverage
3. **Delete deprecated** - Remove old runner after validation
4. **Add channels** - SMS, Telegram (validate design)
