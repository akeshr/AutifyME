# Webhook Idempotency Analysis & Solution

**Status:** CRITICAL - Production Issue
**Created:** 2025-10-13
**Author:** Deep Analysis Session

---

## Executive Summary

**Problem:** WhatsApp webhooks trigger duplicate workflow invocations despite existing idempotency checks.

**Root Cause:** In-memory deduplication cache (`_processed_messages` OrderedDict) does NOT survive:
- Server restarts
- Serverless container recycling (Vercel/AWS Lambda)
- Process crashes

**Impact:** Users experience duplicate product creation, wasted LLM costs, confused conversational state.

**Recommended Solution:** Database-backed idempotency table with immediate HTTP 200 response (Option C - Hybrid).

---

## Root Cause Analysis

### Current Implementation

**Location:** `agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py:82-136`

```python
# Lines 82-86: In-memory LRU cache
_MAX_PROCESSED_MESSAGES = 10_000
_processed_messages: OrderedDict[str, bool] = OrderedDict()

# Lines 215-220: Duplicate check
if _is_duplicate_message(message_id):
    logger.info("Skipping duplicate message")
    continue

# Lines 225-229: Mark as processed IMMEDIATELY
_mark_message_processed(message_id)

# Line 304: BLOCKS until workflow completes (20-60s)
_get_runner().handle_message(sender, text, media_id)
```

**Architecture flaw:** The code EXPLICITLY documents this limitation (lines 83-84, 111-112):
> "In production, this should be persisted in the database with a TTL (e.g., 24 hours)"

### WhatsApp Webhook Retry Behavior

Based on Meta documentation and community reports:

1. **Timeout threshold:** 20-30 seconds
2. **Retry pattern:** Exponential backoff for up to 7 days
3. **Trigger conditions:**
   - Response time >20-30s
   - Non-200 HTTP status
   - Connection timeout/error
4. **Message preservation:** Retried webhooks have SAME `message.id` and original `timestamp`

### Why This Fails in Production

**Serverless/Container Environments:**
```
Request 1 → Container A → Cache empty → Mark processed → Start workflow (30s)
                                                               ↓
Request 2 (retry) → Container B → Cache empty (different instance!) → DUPLICATE
```

**Long-running workflows trigger retries:**
- Image download from WhatsApp CDN: 2-5s
- LLM vision analysis: 5-15s
- Multi-agent orchestration: 10-30s
- Database writes: 1-2s
- **Total: 20-60s** (exceeds WhatsApp's retry threshold)

**Race conditions:**
- Even with database, if both requests arrive simultaneously before first marks processed
- Thread locks (runner_v2.py:156-160) only prevent concurrency WITHIN same process

---

## Database Schema Analysis

### Existing Tables

**workflow_outcomes** (database/migrations/001_workflow_outcomes.sql):
- Tracks workflow execution AFTER processing
- Has `message_hash` for similarity (line 20)
- NOT designed for upfront idempotency (no `message_id` from WhatsApp)

**pending_approvals**:
- Stores HITL interrupt state
- Unrelated to webhook deduplication

**Conclusion:** NO table currently tracks WhatsApp `message.id` for idempotency.

---

## Solution Options

### Option A: Database-Backed Idempotency Table

**Architecture:**
```
WhatsApp → Check DB for message_id → If exists: return 200 immediately
                                   ↓
                                If new: Mark processed → Execute workflow → Return 200
```

**Schema:**
```sql
CREATE TABLE processed_messages (
    message_id TEXT PRIMARY KEY,
    sender_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX idx_processed_messages_expires ON processed_messages(expires_at);
```

**Pros:**
- Survives restarts/crashes
- Works across distributed instances
- Simple implementation

**Cons:**
- Still synchronous (workflow blocks webhook response)
- Doesn't prevent WhatsApp retries if processing >30s
- Database query adds latency (but negligible: ~5ms)

**Implementation complexity:** LOW

---

### Option B: Async Processing with Immediate Response

**Architecture:**
```
WhatsApp → Validate payload → Push to queue → Return 200 IMMEDIATELY
                                              ↓
                                         Background worker processes queue
```

**Pros:**
- Eliminates WhatsApp retries (response <100ms)
- Decouples webhook from workflow execution
- Scales independently

**Cons:**
- Requires message queue (Redis, RabbitMQ, or DB-backed)
- More complex error handling (dead letter queues)
- Harder to debug (async tracing)
- Doesn't prevent duplicates if queue accepts same message twice

**Implementation complexity:** MEDIUM-HIGH

---

### Option C: Hybrid Approach (RECOMMENDED)

**Architecture:**
```
WhatsApp → Check DB idempotency → Mark processed → Push to queue → Return 200 (100ms)
                                                                    ↓
                                                          Background: Process workflow
```

**Implementation:**
1. **Webhook handler** (whatsapp_webhook.py):
   - Query `processed_messages` table by `message_id`
   - If duplicate: return 200 immediately (no-op)
   - If new: insert into `processed_messages`, push to queue, return 200

2. **Background worker** (new: `workflow_worker.py`):
   - Polls queue (or triggered by DB insert)
   - Executes `WorkflowRunner.handle_message()`
   - Updates `workflow_outcomes` on completion

**Pros:**
- **Idempotent:** Database prevents duplicates
- **Fast response:** <100ms webhook latency
- **Resilient:** Survives crashes, scales horizontally
- **Observable:** Queue depth, processing time metrics

**Cons:**
- Most complex to implement
- Requires infrastructure (queue or polling worker)
- Slightly harder local testing (need worker running)

**Implementation complexity:** MEDIUM

---

## Recommended Solution: Option C (Hybrid)

### Rationale

1. **Immediate idempotency:** Database prevents duplicates across ALL scenarios (restarts, races, retries)
2. **WhatsApp compliance:** <100ms response prevents retries entirely
3. **Production-grade:** Used by Stripe, Twilio, Shopify webhooks
4. **Separation of concerns:** Webhook validation ≠ workflow execution
5. **Observability:** Queue metrics surface processing health

### Phased Rollout

**Phase 1 (Immediate fix - 1 day):**
- Create `processed_messages` table
- Add DB check/insert to webhook handler
- Keep synchronous processing
- **Result:** Eliminates duplicates, still slow

**Phase 2 (Async processing - 2-3 days):**
- Add message queue (start with DB-backed: `pending_workflows` table)
- Create background worker
- Async processing with queue polling
- **Result:** Fast responses, no retries

**Phase 3 (Production hardening - 1 day):**
- Add queue metrics (depth, age, failures)
- Dead letter queue for failures
- Exponential backoff retries
- **Result:** Production-grade reliability

---

## Implementation Details

### Phase 1: Database Idempotency (Immediate)

**Migration: `database/migrations/002_processed_messages.sql`**
```sql
CREATE TABLE processed_messages (
    message_id TEXT PRIMARY KEY,
    sender_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'whatsapp',
    thread_id TEXT NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for TTL cleanup
CREATE INDEX idx_processed_messages_expires
    ON processed_messages(expires_at)
    WHERE expires_at IS NOT NULL;

-- Cleanup function (run via cron or pg_cron)
CREATE OR REPLACE FUNCTION cleanup_expired_processed_messages()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM processed_messages
    WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE processed_messages IS
'Idempotency tracking for webhook message deduplication.
Stores WhatsApp message IDs to prevent duplicate processing across server restarts.
TTL: 24 hours (auto-cleanup via expires_at).';
```

**Code changes: `whatsapp_webhook.py`**
```python
# Add to imports
from autifyme_agents.integrations.storage.idempotency import IdempotencyChecker

# Initialize in _get_runner() or module level
_idempotency_checker = IdempotencyChecker()

# Replace _is_duplicate_message() call (line 215) with:
if _idempotency_checker.is_processed(message_id, sender, thread_id):
    logger.info(
        "Skipping duplicate message (DB idempotency)",
        extra={"message_id": message_id, "sender": sender},
    )
    continue

# Replace _mark_message_processed() call (line 225) with:
_idempotency_checker.mark_processed(
    message_id=message_id,
    sender_id=sender,
    thread_id=thread_id,
    received_at=datetime.fromtimestamp(int(timestamp)),
)
```

**New file: `agents/src/autifyme_agents/integrations/storage/idempotency.py`**
```python
"""Database-backed idempotency checker for webhook deduplication."""

from datetime import datetime
from autifyme_agents.integrations.storage.supabase_client import get_supabase_client

class IdempotencyChecker:
    """Persistent idempotency checks using database."""

    def is_processed(self, message_id: str, sender_id: str, thread_id: str) -> bool:
        """Check if message has been processed (survives restarts)."""
        client = get_supabase_client()
        result = client.table("processed_messages") \
            .select("message_id") \
            .eq("message_id", message_id) \
            .execute()
        return len(result.data) > 0

    def mark_processed(
        self,
        message_id: str,
        sender_id: str,
        thread_id: str,
        received_at: datetime,
    ) -> None:
        """Mark message as processed (idempotent insert)."""
        client = get_supabase_client()
        client.table("processed_messages").upsert({
            "message_id": message_id,
            "sender_id": sender_id,
            "thread_id": thread_id,
            "received_at": received_at.isoformat(),
        }).execute()
```

---

### Phase 2: Async Processing (Future)

**Schema:**
```sql
CREATE TABLE pending_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT NOT NULL REFERENCES processed_messages(message_id),
    sender_id TEXT NOT NULL,
    text TEXT,
    media_id TEXT,
    raw_payload JSONB NOT NULL,

    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,

    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_pending_workflows_status ON pending_workflows(status, scheduled_at);
```

**Worker implementation:** Deferred to avoid over-engineering upfront.

---

## Testing Strategy

### Phase 1 Verification

**1. Duplicate detection:**
```bash
# Terminal 1: Start server
uv run uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --reload

# Terminal 2: Simulate duplicate webhook
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "id": "test_msg_001",
            "from": "1234567890",
            "type": "text",
            "text": {"body": "test duplicate"},
            "timestamp": "1697000000"
          }]
        }
      }]
    }]
  }'

# Send SAME payload again - should log "Skipping duplicate message (DB idempotency)"
```

**2. Server restart persistence:**
```bash
# Send webhook → Check DB → Restart server → Send same webhook → Verify skipped
```

**3. Race condition:**
```bash
# Send 2 simultaneous requests with same message_id
# Only ONE should process (DB constraint prevents both)
```

---

## Monitoring & Observability

**Metrics to track:**
1. Duplicate detection rate: `processed_messages.count` vs `workflow_outcomes.count`
2. Processing latency: Time from webhook receipt to HTTP 200 response
3. Workflow duration: Time from queue insertion to completion
4. Queue depth (Phase 2): `pending_workflows` where status='pending'

**Alerts:**
- Duplicate rate >5% (indicates systematic retry issue)
- Processing latency >100ms (Phase 2 target)
- Workflow duration >60s (investigate slow LLM calls)

---

## Migration Checklist

- [ ] Create database migration `002_processed_messages.sql`
- [ ] Apply migration to development DB
- [ ] Implement `IdempotencyChecker` class
- [ ] Update `whatsapp_webhook.py` to use DB checks
- [ ] Remove in-memory `_processed_messages` OrderedDict (or keep as fallback)
- [ ] Add logging for idempotency hits/misses
- [ ] Test duplicate detection locally
- [ ] Test server restart persistence
- [ ] Deploy to staging
- [ ] Monitor for 24h, verify no duplicates
- [ ] Deploy to production
- [ ] Add cleanup cron job (run daily: `SELECT cleanup_expired_processed_messages()`)

---

## Open Questions

1. **Queue choice for Phase 2:** Database-backed (simple) vs Redis (fast) vs RabbitMQ (robust)?
2. **Cleanup frequency:** Daily cron sufficient, or need real-time TTL?
3. **Fallback strategy:** If DB is down, fail open (allow duplicates) or fail closed (reject webhooks)?

---

## Related Documents

- `AGENTS_DESIGN.md` - Context engineering, error handling principles
- `LANGCHAIN_V1_FEATURES.md` - LangGraph checkpointer integration
- `WHATSAPP_CATALOGING_WORKFLOW.md` - Current workflow implementation
- `LOCAL_TESTING_STRATEGY.md` - Testing approach for webhook changes
