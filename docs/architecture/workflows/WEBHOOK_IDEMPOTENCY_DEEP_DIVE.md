# Webhook Idempotency: Complete Architectural Analysis

**Date:** 2025-10-13
**Status:** CRITICAL - Production waste (35x processing), no data corruption
**Impact:** $$ wasted on LLM calls, cluttered logs, poor observability

---

## Executive Summary

**Problem:** WhatsApp webhook retries cause duplicate workflow invocations despite in-memory deduplication.

**Root Cause:** Serverless container churn invalidates in-memory cache. 35 duplicate invocations observed within 7.5 minutes for single message.

**Why No Duplicate Products:** LangGraph's checkpoint-based architecture provides workflow-level idempotency. Thread state prevents duplicate tool executions.

**Recommended Solution:** Database-backed idempotency using UPSERT with RETURNING (atomic, single round-trip, no new table needed - reuse `workflow_outcomes.tracking_id`).

---

## Investigation Findings

### Data Evidence

**Query 1: Duplicate products?**
```sql
SELECT name, COUNT(*) FROM products GROUP BY name HAVING COUNT(*) > 1;
-- Result: [] (ZERO duplicates)
```

**Query 2: Duplicate workflow invocations?**
```sql
SELECT message_hash, COUNT(*) FROM workflow_outcomes GROUP BY message_hash HAVING COUNT(*) > 1;
-- Result: 35 executions for message_hash 'f5b4b8bc7a551309' within 7.5 minutes
```

**Query 3: Execution timeline for hash 'f5b4b8bc7a551309':**
```
06:34:01 → 06:34:08 (6.4s)
06:34:11 → 06:34:15 (3.4s)  [10s gap - RETRY #1]
06:34:18 → 06:34:22 (3.8s)  [7s gap - RETRY #2]
06:34:26 → 06:34:29 (2.9s)  [7s gap - RETRY #3]
... (35 total executions)
06:41:26 → 06:41:48 (22s)   [Final retry]
```

**Pattern Analysis:**
- **Timing:** 3-22 second intervals (classic exponential backoff)
- **Duration:** Most complete in 3-15s (suspiciously fast for full cataloging workflow)
- **Result:** All marked `success=true`, but `result_status=null` (no product saved)
- **Conclusion:** WhatsApp retry behavior, NOT user sending same message 35 times

---

## Root Cause: Three-Layer Failure

### Layer 1: Webhook Idempotency (FAILS in serverless)

**Code:** `whatsapp_webhook.py:82-136`

```python
# In-memory LRU cache
_processed_messages: OrderedDict[str, bool] = OrderedDict()

def _is_duplicate_message(message_id: str) -> bool:
    return message_id in _processed_messages

def _mark_message_processed(message_id: str) -> None:
    _processed_messages[message_id] = True
```

**Why it fails:**
1. **Serverless cold starts:** Each request may hit a fresh container with empty cache
2. **Parallel retries:** WhatsApp sends retry before first request completes
3. **Memory limits:** LRU evicts old entries (10k max), no TTL enforcement
4. **Zero persistence:** Process crash/restart = cache gone

**Webhook retry timeline:**
```
t=0s:  Request 1 → Container A (cache empty) → Start workflow
t=10s: Retry 1 → Container B (cache empty, A still running) → Start workflow AGAIN
t=17s: Retry 2 → Container A (cache has msg1) → SKIP ✅
t=24s: Retry 3 → Container C (cache empty) → Start workflow AGAIN
```

Result: ~50% cache hit rate in distributed environment.

---

### Layer 2: Workflow Idempotency (WORKS via LangGraph checkpoints)

**Code:** `runner.py:286-311`

```python
# Check for pending HITL interrupt
state_snapshot = pm.get_state(config)
if state_snapshot and state_snapshot.interrupts:
    # Resume existing workflow with Command
    pending_interrupt = state_snapshot.interrupts[0]
    command = Command(resume={interrupt_id: resume_value})
    pm.stream(command, config=config)
else:
    # Start new workflow
    payload = {"messages": [HumanMessage(content=json.dumps(raw_payload))]}
    pm.stream(payload, config=config)
```

**Why this provides implicit idempotency:**
1. **Shared thread_id:** All retries use `format_thread_id(sender)` → same LangGraph thread
2. **Checkpoint state:** Thread tracks workflow progress in PostgreSQL
3. **Interrupt detection:** If workflow is at HITL, retries see `pending_interrupt` and wait
4. **Message accumulation:** LangGraph appends messages to thread, but PM's logic may short-circuit

**Evidence from data:**
- 35 invocations, but 0 duplicate products
- Durations: 3-15s (too fast for full workflow → early exit?)
- All `success=true` but `result_status=null` → workflow didn't reach save_product tool

**Hypothesis:** Duplicate invocations hit the SAME thread_id, LangGraph/PM detects conversation state, returns early without re-processing.

---

### Layer 3: Data Persistence (Protected by HITL + workflow state)

**HITL as accidental safeguard:**
- Cataloging workflow requires user approval before `save_product`
- User approves ONCE
- Other 34 workflows either:
  - Exit early (see existing thread state)
  - Wait at interrupt that will never be resumed
  - Timeout without completing

**Result:** Even if workflow logic was broken, HITL prevents data corruption.

---

## WhatsApp Webhook Retry Behavior (Researched)

### Official Meta Behavior

**Timeout:** 20-30 seconds before first retry
**Retry pattern:** Exponential backoff up to 7 days
**Triggers:**
- Response time >20-30s
- Non-200 HTTP status
- Network timeout/connection error

**Preservation:** Retried webhooks have:
- **SAME** `message.id`
- **SAME** `message.timestamp` (original send time)
- **SAME** payload structure

### Best Practices (Meta + industry)

1. **Return 200 IMMEDIATELY** (<100ms)
2. **Process asynchronously** (queue-based or background worker)
3. **Idempotency key:** Use `message.id` for deduplication
4. **Persistent tracking:** Database, not memory

Used by: Stripe, Twilio, Shopify, SendGrid (all webhook-heavy platforms).

---

## Solution Space: 8 Options Analyzed

### Option 1: Reuse `workflow_outcomes.tracking_id` (RECOMMENDED)

**Concept:** Leverage existing UNIQUE constraint instead of new table.

```python
# Generate deterministic tracking_id from message_id
tracking_id = f"whatsapp:{sender}:{message_id}"

# Atomic insert
result = supabase.table("workflow_outcomes").insert({
    "tracking_id": tracking_id,
    "thread_id": thread_id,
    "sender_id": sender,
    "message_text": text,
    "message_hash": hash(text),
    "started_at": datetime.now(),
    "success": False,  # Mark false initially, update on completion
}).on_conflict("tracking_id", action="ignore").execute()

if len(result.data) == 0:
    # Conflict occurred - duplicate message
    logger.info(f"Skipping duplicate message_id: {message_id}")
    return {"status": "duplicate"}

# Process workflow...
```

**Pros:**
- ✅ No schema changes
- ✅ Uses existing infrastructure
- ✅ Atomic (UNIQUE constraint at DB level)
- ✅ Survives restarts
- ✅ Works across containers

**Cons:**
- ❌ Pollutes `workflow_outcomes` with "intent to process" rows (success=false initially)
- ❌ Requires deterministic tracking_id generation (breaks current UUID pattern)
- ❌ Cleanup complexity (remove failed/abandoned rows)

**Implementation Complexity:** LOW

---

### Option 2: UPSERT with RETURNING (New table)

**Concept:** Dedicated idempotency table with atomic operation.

```sql
-- Migration: 002_processed_messages.sql
CREATE TABLE processed_messages (
    message_id TEXT PRIMARY KEY,
    sender_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours'),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_processed_messages_expires ON processed_messages(expires_at);
```

```python
# Atomic idempotency check + insert
result = supabase.rpc("check_and_mark_processed", {
    "p_message_id": message_id,
    "p_sender_id": sender,
    "p_thread_id": thread_id,
    "p_received_at": received_at,
}).execute()

if result.data["is_duplicate"]:
    logger.info(f"Skipping duplicate: {message_id}")
    return {"status": "duplicate"}

# Process workflow...
```

```sql
-- Stored procedure for atomic operation
CREATE OR REPLACE FUNCTION check_and_mark_processed(
    p_message_id TEXT,
    p_sender_id TEXT,
    p_thread_id TEXT,
    p_received_at TIMESTAMPTZ
) RETURNS JSON AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    -- Atomic insert with conflict detection
    INSERT INTO processed_messages (message_id, sender_id, thread_id, received_at)
    VALUES (p_message_id, p_sender_id, p_thread_id, p_received_at)
    ON CONFLICT (message_id) DO NOTHING
    RETURNING true INTO v_exists;

    RETURN json_build_object('is_duplicate', v_exists IS NULL);
END;
$$ LANGUAGE plpgsql;
```

**Pros:**
- ✅ Clean separation of concerns (idempotency ≠ workflow tracking)
- ✅ Atomic (single DB round-trip)
- ✅ TTL-based cleanup (expires_at index)
- ✅ Optimized for fast lookups (indexed primary key)
- ✅ Survives restarts

**Cons:**
- ❌ New table (schema change)
- ❌ Additional storage overhead (but minimal: ~100 bytes/message)

**Implementation Complexity:** LOW-MEDIUM

---

###Option 3: FastAPI BackgroundTasks

**Concept:** Return 200 immediately, process in background thread.

```python
from fastapi import BackgroundTasks

@app.post("/webhook")
async def receive(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    message_id = extract_message_id(body)

    # Check idempotency with DB
    if is_duplicate(message_id):
        return {"status": "duplicate"}

    # Mark as processed
    mark_processed(message_id)

    # Schedule background processing
    background_tasks.add_task(process_workflow, body)

    # Return 200 immediately (<100ms)
    return {"status": "accepted"}
```

**Pros:**
- ✅ Fast webhook response (<100ms prevents retries)
- ✅ Native FastAPI (no new dependencies)
- ✅ Simple implementation

**Cons:**
- ❌ **NOT reliable in serverless:** Container killed before background task completes
- ❌ No task persistence (process crash = lost work)
- ❌ No retry logic (task fails = silent drop)
- ❌ Doesn't fix idempotency (still need DB check)

**Verdict:** ❌ **DO NOT USE** in serverless environments (Vercel, AWS Lambda, Cloud Run).

**Implementation Complexity:** LOW (but unreliable)

---

### Option 4: Persistent Queue + Worker

**Concept:** Full async architecture with DB-backed queue.

```python
# Webhook handler
@app.post("/webhook")
async def receive(request: Request):
    body = await request.json()
    message_id = extract_message_id(body)

    # Check idempotency
    if is_duplicate(message_id):
        return {"status": "duplicate"}

    # Insert into queue
    supabase.table("pending_workflows").insert({
        "message_id": message_id,
        "sender_id": sender,
        "raw_payload": body,
        "status": "pending",
    }).execute()

    return {"status": "queued"}  # <100ms

# Background worker (separate process/service)
while True:
    tasks = supabase.table("pending_workflows") \
        .select("*") \
        .eq("status", "pending") \
        .limit(10) \
        .execute()

    for task in tasks.data:
        try:
            process_workflow(task["raw_payload"])
            mark_completed(task["id"])
        except Exception as e:
            mark_failed(task["id"], str(e))
```

**Pros:**
- ✅ Fast webhook response (WhatsApp retries eliminated)
- ✅ Persistent queue (survives crashes)
- ✅ Retry logic (exponential backoff on failures)
- ✅ Observable (queue depth, processing time metrics)
- ✅ Scales independently (add more workers)

**Cons:**
- ❌ Most complex implementation
- ❌ Requires background worker process (deployment overhead)
- ❌ Harder debugging (async tracing)
- ❌ Queue management (dead letter queue, cleanup)

**When to use:** High-scale production (>1000 webhooks/minute).

**Implementation Complexity:** HIGH

---

### Option 5: PostgreSQL Advisory Locks

**Concept:** Distributed coordination without schema changes.

```python
import psycopg2

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Try to acquire lock (non-blocking)
cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))", (message_id,))
lock_acquired = cursor.fetchone()[0]

if not lock_acquired:
    logger.info(f"Duplicate detected via advisory lock: {message_id}")
    return {"status": "duplicate"}

try:
    # Process workflow
    process_workflow(...)
finally:
    # Release lock
    cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", (message_id,))
    conn.close()
```

**Pros:**
- ✅ No schema changes
- ✅ Built-in PostgreSQL feature
- ✅ Fast (in-memory locks)

**Cons:**
- ❌ Session-scoped (requires persistent connection)
- ❌ NOT persistent (memory-only, lost on restart)
- ❌ Orphaned lock risk (process crash without unlock)
- ❌ Complex connection management in serverless
- ❌ Doesn't prevent container churn duplicates

**Verdict:** ❌ **NOT suitable** for serverless or stateless apps.

**Implementation Complexity:** MEDIUM (connection management complexity)

---

### Option 6: Redis Distributed Lock

**Concept:** External cache for distributed coordination.

```python
import redis

r = redis.Redis(host=REDIS_HOST)

# Try to acquire lock with TTL
lock_acquired = r.set(f"lock:{message_id}", "1", nx=True, ex=60)

if not lock_acquired:
    logger.info(f"Duplicate detected via Redis: {message_id}")
    return {"status": "duplicate"}

# Process workflow
process_workflow(...)
```

**Pros:**
- ✅ Fast (<1ms latency)
- ✅ Battle-tested (industry standard)
- ✅ TTL-based auto-cleanup
- ✅ Works across containers

**Cons:**
- ❌ New infrastructure dependency (Redis instance)
- ❌ Additional costs ($20-50/month for managed Redis)
- ❌ Network latency (if external)
- ❌ Single point of failure (unless Redis cluster)

**When to use:** Already have Redis in stack, high throughput needs.

**Implementation Complexity:** LOW (if Redis exists), HIGH (if new infra)

---

### Option 7: WhatsApp Timestamp Deduplication

**Concept:** Use `message.timestamp` instead of `message.id`.

```python
# WhatsApp preserves original timestamp on retries
timestamp = message.get("timestamp")  # Unix timestamp
sender = message.get("from")

# Composite key: (sender, timestamp)
dedup_key = f"{sender}:{timestamp}"

if is_processed(dedup_key):
    logger.info(f"Duplicate detected via timestamp: {dedup_key}")
    return {"status": "duplicate"}
```

**Pros:**
- ✅ Works even if `message.id` format changes
- ✅ Simple implementation

**Cons:**
- ❌ Clock skew issues (user clock vs server clock)
- ❌ Timestamp precision (WhatsApp uses seconds, not milliseconds)
- ❌ Multiple messages in same second from same user (edge case)
- ❌ Less reliable than `message.id`

**Verdict:** ❌ Use `message.id` (explicit, guaranteed unique by WhatsApp).

**Implementation Complexity:** LOW

---

### Option 8: LangGraph-Aware Deduplication

**Concept:** Check if thread already has message before invoking PM.

```python
# Check checkpoint for recent messages
state_snapshot = pm.get_state(config)
recent_messages = state_snapshot.values.get("messages", [])[-5:]  # Last 5 messages

# Check if incoming message matches recent message
incoming_hash = hash(text)
for msg in recent_messages:
    if hash(msg.content) == incoming_hash:
        logger.info("Duplicate detected via LangGraph state")
        return {"status": "duplicate"}

# Process workflow
pm.stream(payload, config=config)
```

**Pros:**
- ✅ No new tables
- ✅ Leverages existing checkpoint infrastructure
- ✅ Content-based deduplication

**Cons:**
- ❌ Complex state inspection (fragile)
- ❌ Requires loading checkpoint for every webhook (slow)
- ❌ Can't distinguish: user sending same text vs WhatsApp retry
- ❌ Hash collisions (different messages, same hash)
- ❌ Doesn't use WhatsApp's `message.id` (explicit unique identifier)

**Verdict:** ❌ Over-engineered, fragile, doesn't solve root cause.

**Implementation Complexity:** MEDIUM-HIGH

---

## Recommendation: Option 2 (New Table + UPSERT)

### Why Option 2 Wins

| Criterion | Option 1 (Reuse) | Option 2 (New Table) | Option 4 (Queue) |
|-----------|------------------|----------------------|------------------|
| **No Schema Change** | ✅ | ❌ | ❌ |
| **Clean Separation** | ❌ (pollutes outcomes) | ✅ | ✅ |
| **Atomic Operation** | ✅ | ✅ | ✅ |
| **Fast Webhook Response** | ❌ (synchronous) | ❌ (synchronous) | ✅ (<100ms) |
| **Implementation Complexity** | LOW | LOW-MEDIUM | HIGH |
| **Production Ready** | ⚠️ (needs cleanup) | ✅ | ✅ (overkill) |

**Decision Rationale:**

1. **Option 1** is tempting (no schema change), but pollutes `workflow_outcomes` with "intent to process" rows. Cleanup is complex.
2. **Option 2** is clean: idempotency table separate from workflow tracking. Standard pattern (Stripe, Twilio).
3. **Option 4** is overkill for current scale. Add later if webhook latency becomes issue.

### Two-Phase Rollout

**Phase 1 (Immediate - 4 hours):**
- Create `processed_messages` table (migration)
- Implement `IdempotencyChecker` class with UPSERT
- Update `whatsapp_webhook.py` to use DB check
- Deploy + monitor for 24h

**Phase 2 (Future - if needed):**
- Add background queue (`pending_workflows` table)
- Return 200 immediately after idempotency check
- Background worker processes workflows
- **Trigger:** Webhook latency >500ms or retry rate >10%

---

## Implementation: Phase 1 (Database Idempotency)

### Migration: `database/migrations/002_processed_messages.sql`

```sql
-- ============================================================================
-- TABLE: processed_messages (Webhook Idempotency)
-- Purpose: Deduplicate WhatsApp webhook retries using message_id
-- Created: 2025-10-13
-- Dependencies: PostgreSQL 12+
-- ============================================================================

CREATE TABLE IF NOT EXISTS processed_messages (
    -- WhatsApp message identifiers
    message_id TEXT PRIMARY KEY,  -- WhatsApp's unique message ID (wamid.*)
    sender_id TEXT NOT NULL,      -- Phone number (917258067800)
    thread_id TEXT NOT NULL,      -- LangGraph thread ID (whatsapp:917258067800)

    -- Message metadata
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- When webhook received
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- TTL for cleanup
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for TTL cleanup (find expired rows)
CREATE INDEX IF NOT EXISTS idx_processed_messages_expires
    ON processed_messages(expires_at)
    WHERE expires_at IS NOT NULL;

-- Index for sender lookup (analytics)
CREATE INDEX IF NOT EXISTS idx_processed_messages_sender
    ON processed_messages(sender_id, created_at DESC);

-- ============================================================================
-- STORED PROCEDURE: Atomic idempotency check + insert
-- ============================================================================

CREATE OR REPLACE FUNCTION check_and_mark_processed(
    p_message_id TEXT,
    p_sender_id TEXT,
    p_thread_id TEXT,
    p_received_at TIMESTAMPTZ
) RETURNS JSON AS $$
DECLARE
    v_inserted BOOLEAN;
BEGIN
    -- Atomic insert with conflict detection
    -- Returns true if INSERT succeeded (new message)
    -- Returns false if conflict occurred (duplicate message)
    INSERT INTO processed_messages (message_id, sender_id, thread_id, received_at)
    VALUES (p_message_id, p_sender_id, p_thread_id, p_received_at)
    ON CONFLICT (message_id) DO NOTHING
    RETURNING true INTO v_inserted;

    -- Return JSON with result
    RETURN json_build_object(
        'is_duplicate', v_inserted IS NULL,
        'message_id', p_message_id
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CLEANUP FUNCTION: Remove expired rows (run via cron)
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_processed_messages()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM processed_messages
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Log cleanup (optional)
    RAISE NOTICE 'Cleaned up % expired processed_messages', deleted_count;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE processed_messages IS
'Idempotency tracking for WhatsApp webhook deduplication.
Stores message_id from WhatsApp to prevent duplicate processing when webhooks retry.
TTL: 24 hours (auto-cleanup via expires_at).
Used by: whatsapp_webhook.py';

COMMENT ON COLUMN processed_messages.message_id IS
'WhatsApp unique message ID (e.g., wamid.HBgLOTE3MjU4MDY3ODAw...).
Preserved across webhook retries - use this for deduplication.';

COMMENT ON COLUMN processed_messages.expires_at IS
'TTL for cleanup. After 24 hours, message_id can be reused (extremely unlikely).
Run cleanup_expired_processed_messages() daily via cron.';

COMMENT ON FUNCTION check_and_mark_processed IS
'Atomic idempotency check + insert. Single DB round-trip.
Returns {is_duplicate: true} if message already processed, {is_duplicate: false} if new.
Used by webhook handler to deduplicate before processing.';
```

### Code: `agents/src/autifyme_agents/integrations/storage/idempotency.py`

```python
"""Database-backed idempotency checker for webhook deduplication."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autifyme_agents.integrations.storage.supabase_client import SupabaseStorageClient

logger = logging.getLogger(__name__)


class IdempotencyChecker:
    """Persistent idempotency checks using PostgreSQL.

    Prevents duplicate webhook processing by tracking message_id in database.
    Survives server restarts and works across distributed containers.
    """

    def __init__(self, storage: "SupabaseStorageClient"):
        """Initialize idempotency checker.

        Args:
            storage: Supabase storage client for database access
        """
        self.storage = storage
        self._client = storage.supabase

    def is_processed_and_mark(
        self,
        message_id: str,
        sender_id: str,
        thread_id: str,
        received_at: datetime,
    ) -> bool:
        """Atomically check if message is duplicate AND mark as processed.

        This is the core idempotency operation. Uses PostgreSQL stored procedure
        for atomic INSERT ON CONFLICT to prevent race conditions.

        Args:
            message_id: WhatsApp message ID (unique across retries)
            sender_id: Phone number
            thread_id: LangGraph thread ID
            received_at: When webhook was received

        Returns:
            True if duplicate (already processed), False if new (now marked as processed)
        """
        try:
            result = self._client.rpc("check_and_mark_processed", {
                "p_message_id": message_id,
                "p_sender_id": sender_id,
                "p_thread_id": thread_id,
                "p_received_at": received_at.isoformat(),
            }).execute()

            is_duplicate = result.data.get("is_duplicate", False)

            if is_duplicate:
                logger.info(
                    "Duplicate message detected (DB idempotency)",
                    extra={
                        "message_id": message_id,
                        "sender_id": sender_id,
                        "thread_id": thread_id,
                    },
                )
            else:
                logger.debug(
                    "New message marked as processed",
                    extra={"message_id": message_id},
                )

            return is_duplicate

        except Exception as exc:
            # If DB check fails, fail OPEN (allow processing) to prevent webhook blocking
            # Log error for monitoring/alerts
            logger.exception(
                "Idempotency check failed - allowing processing (fail open)",
                exc_info=exc,
                extra={
                    "message_id": message_id,
                    "error_type": type(exc).__name__,
                },
            )
            return False  # Process the message (risk: potential duplicate)
```

### Code Changes: `whatsapp_webhook.py`

```python
# At module level (line ~52):
from autifyme_agents.integrations.storage.idempotency import IdempotencyChecker

# In _get_runner() function (line ~73):
_idempotency_checker = None

def _get_runner():
    """Lazy initialization of WorkflowRunner for serverless deployment."""
    global _runner, _storage_adapter, _whatsapp_channel, _idempotency_checker

    if _runner is None:
        logger.info("Initializing WorkflowRunner with WhatsApp channel...")
        try:
            # Create storage adapter
            _storage_adapter = SupabaseStorageClient()
            logger.info("Storage adapter initialized successfully")

            # Create idempotency checker
            _idempotency_checker = IdempotencyChecker(_storage_adapter)
            logger.info("Idempotency checker initialized")

            # ... rest of initialization
```

```python
# In receive() webhook handler (replace lines 213-225):

# Check for duplicate processing using message_id
# (WhatsApp can retry webhooks, and we might get the same message twice)
if _idempotency_checker.is_processed_and_mark(
    message_id=message_id,
    sender_id=sender,
    thread_id=_whatsapp_channel.format_thread_id(sender),
    received_at=datetime.fromtimestamp(int(timestamp)),
):
    logger.info(
        "Skipping duplicate message (DB idempotency)",
        extra={"message_id": message_id, "sender": sender, "event_path": str(event_path)},
    )
    continue

# REMOVE old in-memory check and mark:
# if _is_duplicate_message(message_id):  # DELETE THIS
# _mark_message_processed(message_id)    # DELETE THIS

# Process workflow...
_get_runner().handle_message(sender, text, media_id)
```

---

## Testing Strategy

### Test 1: Duplicate Detection (Manual)

```bash
# Terminal 1: Start server
cd C:\Abhi\personal\self\AutifyME
uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload

# Terminal 2: Send webhook twice
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "test_msg_idempotency_001",
            "from": "1234567890",
            "type": "text",
            "text": {"body": "Test idempotency"},
            "timestamp": "1697000000"
          }]
        }
      }]
    }]
  }'

# Send SAME payload again
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "test_msg_idempotency_001",
            "from": "1234567890",
            "type": "text",
            "text": {"body": "Test idempotency"},
            "timestamp": "1697000000"
          }]
        }
      }]
    }]
  }'

# Expected: Second request logs "Skipping duplicate message (DB idempotency)"
```

### Test 2: Server Restart Persistence

```bash
# Send webhook
curl -X POST http://localhost:8000/webhook -d '...'

# Verify DB entry
psql $DATABASE_URL -c "SELECT * FROM processed_messages WHERE message_id = 'test_msg_idempotency_001';"

# Restart server (Ctrl+C → uv run uvicorn...)

# Send SAME webhook again
curl -X POST http://localhost:8000/webhook -d '...'

# Expected: Still detects duplicate (survives restart)
```

### Test 3: Race Condition (Parallel Requests)

```bash
# Send 2 simultaneous requests with same message_id
curl -X POST http://localhost:8000/webhook -d '...' &
curl -X POST http://localhost:8000/webhook -d '...' &

# Check DB
psql $DATABASE_URL -c "SELECT COUNT(*) FROM processed_messages WHERE message_id = 'test_msg_idempotency_001';"

# Expected: COUNT = 1 (only one INSERT succeeded, other got conflict)

# Check workflow_outcomes
psql $DATABASE_URL -c "SELECT COUNT(*) FROM workflow_outcomes WHERE tracking_id LIKE '%test_msg_idempotency_001%';"

# Expected: COUNT = 1 (only one workflow executed)
```

### Test 4: TTL Cleanup

```bash
# Insert expired message
psql $DATABASE_URL -c "
INSERT INTO processed_messages (message_id, sender_id, thread_id, received_at, expires_at)
VALUES ('expired_test', '1234567890', 'whatsapp:1234567890', NOW() - INTERVAL '25 hours', NOW() - INTERVAL '1 hour');
"

# Run cleanup function
psql $DATABASE_URL -c "SELECT cleanup_expired_processed_messages();"

# Verify deleted
psql $DATABASE_URL -c "SELECT * FROM processed_messages WHERE message_id = 'expired_test';"

# Expected: 0 rows (expired message cleaned up)
```

---

## Monitoring & Observability

### Metrics to Track

1. **Duplicate detection rate:**
   ```sql
   SELECT
       DATE_TRUNC('hour', created_at) as hour,
       COUNT(*) as total_messages,
       COUNT(*) FILTER (WHERE was_duplicate) as duplicates,
       ROUND(100.0 * COUNT(*) FILTER (WHERE was_duplicate) / COUNT(*), 2) as duplicate_pct
   FROM processed_messages
   WHERE created_at > NOW() - INTERVAL '24 hours'
   GROUP BY hour
   ORDER BY hour DESC;
   ```

2. **Webhook latency:**
   - Measure time from webhook receipt to HTTP 200 response
   - Target: <500ms (prevents retries)

3. **Workflow outcomes vs processed_messages:**
   ```sql
   -- Should be roughly equal (1 workflow per message)
   SELECT
       (SELECT COUNT(*) FROM processed_messages WHERE created_at > NOW() - INTERVAL '1 hour') as messages_processed,
       (SELECT COUNT(*) FROM workflow_outcomes WHERE started_at > NOW() - INTERVAL '1 hour') as workflows_executed;
   ```

### Alerts

1. **High duplicate rate:** Duplicate % >20% (indicates systematic retry issue)
2. **DB idempotency failures:** `IdempotencyChecker` exceptions >5/min
3. **Cleanup lag:** `processed_messages.count WHERE expires_at < NOW()` >10000

---

## Migration Checklist

- [ ] Review `docs/architecture/WEBHOOK_IDEMPOTENCY_DEEP_DIVE.md`
- [ ] Create migration `database/migrations/002_processed_messages.sql`
- [ ] Apply migration to local database
- [ ] Implement `IdempotencyChecker` class (`agents/src/autifyme_agents/integrations/storage/idempotency.py`)
- [ ] Update `whatsapp_webhook.py` to use `IdempotencyChecker`
- [ ] Remove old in-memory `_processed_messages` OrderedDict
- [ ] Add unit tests for `IdempotencyChecker` (mocked DB)
- [ ] Run manual tests (duplicate detection, restart persistence, race condition)
- [ ] Deploy to development environment
- [ ] Monitor for 24h (check logs, DB growth, duplicate rate)
- [ ] Set up cleanup cron job (daily: `SELECT cleanup_expired_processed_messages()`)
- [ ] Deploy to staging → Monitor → Deploy to production
- [ ] Update monitoring dashboards with new metrics
- [ ] Document in runbook (rollback steps, troubleshooting)

---

## Rollback Strategy

If issues arise post-deployment:

1. **Immediate rollback:**
   ```python
   # In whatsapp_webhook.py, revert to old code:
   if _is_duplicate_message(message_id):  # Old in-memory check
       continue
   _mark_message_processed(message_id)
   ```

2. **Keep migration:**
   - Leave `processed_messages` table in place
   - Monitor DB growth (should be minimal: ~10MB/day)
   - Re-attempt implementation after debugging

3. **Emergency fix:**
   - If DB idempotency is causing webhook delays, add timeout:
     ```python
     try:
         is_duplicate = _idempotency_checker.is_processed_and_mark(...)
     except TimeoutError:
         logger.warning("Idempotency check timeout - processing anyway")
         is_duplicate = False  # Fail open
     ```

---

## Open Questions

1. **Cleanup frequency:** Daily cron sufficient, or need hourly?
2. **TTL duration:** 24h safe, or increase to 48h for extreme edge cases?
3. **Fail open vs fail closed:** If DB is down, allow duplicates or reject webhooks?
   - **Current:** Fail open (allow duplicates) to prevent user-facing outages
   - **Alternative:** Fail closed (reject webhooks) for zero duplicates guarantee
4. **Phase 2 trigger:** At what scale do we need async queue? (Baseline: monitor webhook latency post-Phase 1)

---

## Related Documents

- `AGENTS_DESIGN.md` - Context engineering, error handling principles
- `WHATSAPP_CATALOGING_WORKFLOW.md` - Current workflow implementation
- `LOCAL_TESTING_STRATEGY.md` - Testing philosophy and CLI tools
- `WORKFLOW_ORCHESTRATION_REFACTOR.md` - Runner architecture
