# Monitoring Queries for AutifyME

**Created:** October 13, 2025
**Purpose:** Key SQL queries for monitoring production health, detecting issues, and analyzing performance.

---

## Webhook Idempotency Monitoring

### 1. Duplicate Detection Rate (Last 24 Hours)

```sql
-- Shows how often WhatsApp retries are being caught
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as total_checks,
    COUNT(*) FILTER (WHERE created_at > processed_at + INTERVAL '1 second') as likely_duplicates,
    ROUND(100.0 * COUNT(*) FILTER (WHERE created_at > processed_at + INTERVAL '1 second') / COUNT(*), 2) as duplicate_pct
FROM processed_messages
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

**Alert:** If `duplicate_pct > 20%`, indicates systematic retry issue (slow processing or infrastructure problems).

---

### 2. Processed Messages vs Workflow Outcomes (Consistency Check)

```sql
-- Should be roughly 1:1 (one workflow per unique message)
SELECT
    (SELECT COUNT(*) FROM processed_messages WHERE created_at > NOW() - INTERVAL '1 hour') as messages_received,
    (SELECT COUNT(*) FROM workflow_outcomes WHERE started_at > NOW() - INTERVAL '1 hour') as workflows_executed,
    (SELECT COUNT(*) FROM workflow_outcomes WHERE started_at > NOW() - INTERVAL '1 hour' AND success = true) as workflows_successful,
    (SELECT COUNT(*) FROM workflow_outcomes WHERE started_at > NOW() - INTERVAL '1 hour' AND success = false) as workflows_failed;
```

**Expected:** `messages_received ~= workflows_executed` (within 5% variance).

**Alert:** If `messages_received >> workflows_executed`, idempotency is working but workflows are failing silently.

---

### 3. Cleanup Monitoring (TTL Health)

```sql
-- Check expired messages needing cleanup
SELECT
    COUNT(*) as expired_count,
    MIN(expires_at) as oldest_expired,
    MAX(expires_at) as newest_expired
FROM processed_messages
WHERE expires_at < NOW();
```

**Action:** If `expired_count > 10000`, run cleanup:
```sql
SELECT cleanup_expired_processed_messages();
```

**Schedule:** Set up daily cron job to run cleanup automatically.

---

## Checkpoint Fork Detection (Concurrent Processing Edge Case)

### 4. Detect Checkpoint Forks

```sql
-- Finds cases where multiple workflows processed same thread concurrently
-- (indicates race condition from user sending messages faster than processing)
SELECT
    thread_id,
    fork_count,
    fork_checkpoint_ids,
    latest_step
FROM v_checkpoint_forks
ORDER BY fork_count DESC
LIMIT 10;
```

**Alert:** If `fork_count > 0` frequently (>5 per day), indicates need for distributed locking (Phase 2).

**False positives:** Occasional forks (<1/day) are acceptable (user impatience edge case).

---

### 5. Fork History (Track Trend)

```sql
-- Track checkpoint forks over time
WITH fork_history AS (
    SELECT
        DATE(created_at) as date,
        thread_id,
        COUNT(*) as checkpoint_count
    FROM checkpoints
    WHERE thread_id LIKE 'whatsapp:%'
      AND created_at > NOW() - INTERVAL '7 days'
    GROUP BY DATE(created_at), thread_id, parent_checkpoint_id
    HAVING COUNT(*) > 1
)
SELECT
    date,
    COUNT(*) as fork_incidents,
    COUNT(DISTINCT thread_id) as affected_threads
FROM fork_history
GROUP BY date
ORDER BY date DESC;
```

**Trend analysis:** Increasing `fork_incidents` indicates need for queue-based sequential processing.

---

## Workflow Performance

### 6. Workflow Duration by Department

```sql
-- Average duration and success rate by department
SELECT
    department,
    COUNT(*) as total_workflows,
    ROUND(AVG(duration_seconds), 2) as avg_duration_seconds,
    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct,
    MAX(duration_seconds) as max_duration_seconds
FROM workflow_outcomes
WHERE started_at > NOW() - INTERVAL '24 hours'
  AND department IS NOT NULL
GROUP BY department
ORDER BY total_workflows DESC;
```

**Alert:**
- `avg_duration_seconds > 60` → Slow processing, risk of WhatsApp retries
- `success_rate_pct < 80%` → High failure rate, investigate errors

---

### 7. Recent Failures (Debugging)

```sql
-- Last 10 failed workflows with error details
SELECT
    tracking_id,
    thread_id,
    message_text,
    department,
    error_type,
    error_message,
    duration_seconds,
    started_at
FROM workflow_outcomes
WHERE success = false
ORDER BY started_at DESC
LIMIT 10;
```

**Action:** Use `tracking_id` to trace in LangSmith for detailed debugging.

---

### 8. Duplicate Workflow Invocations (Pre-Fix Audit)

```sql
-- Find messages that created multiple workflow executions
-- (should decrease to 0 after DB idempotency fix)
SELECT
    message_hash,
    COUNT(*) as execution_count,
    MAX(message_text) as sample_message,
    MIN(started_at) as first_execution,
    MAX(started_at) as last_execution,
    EXTRACT(EPOCH FROM (MAX(started_at) - MIN(started_at))) as time_span_seconds
FROM workflow_outcomes
WHERE started_at > NOW() - INTERVAL '7 days'
GROUP BY message_hash
HAVING COUNT(*) > 1
ORDER BY execution_count DESC
LIMIT 10;
```

**Expected after fix:** `COUNT(*) = 0` (no duplicates for same message_hash).

**If still seeing duplicates:** Check `processed_messages` table for corresponding entries.

---

## Alerts Summary

| Metric | Threshold | Action |
|--------|-----------|--------|
| Duplicate rate | >20% | Investigate slow processing or infrastructure |
| Checkpoint forks | >5/day | Consider distributed locking (Phase 2) |
| Avg workflow duration | >60s | Optimize LLM calls or image processing |
| Success rate | <80% | Review error logs, fix failing workflows |
| Expired messages | >10k | Run cleanup function |

---

## Scheduled Tasks

### Daily Cleanup (Run at 2 AM)

```sql
-- Schedule with pg_cron (if available)
SELECT cron.schedule(
    'cleanup-processed-messages',
    '0 2 * * *',  -- Every day at 2 AM
    $$SELECT cleanup_expired_processed_messages()$$
);
```

**Alternative:** Run from application scheduler or manual cron job.

---

## Quick Health Check (Run Anytime)

```sql
-- One-query health summary
SELECT
    (SELECT COUNT(*) FROM processed_messages WHERE created_at > NOW() - INTERVAL '1 hour') as messages_last_hour,
    (SELECT COUNT(*) FROM workflow_outcomes WHERE started_at > NOW() - INTERVAL '1 hour' AND success = true) as successful_workflows,
    (SELECT COUNT(*) FROM workflow_outcomes WHERE started_at > NOW() - INTERVAL '1 hour' AND success = false) as failed_workflows,
    (SELECT COUNT(*) FROM v_checkpoint_forks) as active_forks,
    (SELECT COUNT(*) FROM processed_messages WHERE expires_at < NOW()) as expired_messages_needing_cleanup;
```

**Healthy system:**
- `messages_last_hour ~= successful_workflows + failed_workflows`
- `active_forks = 0`
- `expired_messages_needing_cleanup < 1000`
