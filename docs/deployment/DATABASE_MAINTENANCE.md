# Database Maintenance Guide

Operational guide for maintaining AutifyME database health and performance.

---

## **Automated Cleanup Tasks**

### **1. Expired Messages Cleanup (processed_messages table)**

**Purpose:** Remove expired idempotency records to prevent unbounded storage growth

**Function:** `cleanup_expired_processed_messages()`
**Defined in:** `database/migrations/002_processed_messages.sql`
**TTL:** 24 hours (configurable via `expires_at`)
**Recommended frequency:** Daily at 2 AM (low-traffic hours)

---

### **Scheduling Options**

#### **Option A: pg_cron (Recommended for Supabase/PostgreSQL)**

```sql
-- Enable pg_cron extension (requires superuser or Supabase dashboard)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule daily cleanup at 2 AM UTC
SELECT cron.schedule(
    'cleanup-processed-messages',  -- Job name
    '0 2 * * *',                   -- Cron expression (daily at 2 AM)
    $$SELECT cleanup_expired_processed_messages()$$
);

-- Verify scheduled job
SELECT * FROM cron.job;

-- Check job run history
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;
```

**Pros:** Runs automatically within database, no external dependencies
**Cons:** Requires `pg_cron` extension (not available on all hosts)

---

#### **Option B: Supabase Edge Functions**

```typescript
// supabase/functions/cleanup-messages/index.ts
import { createClient } from '@supabase/supabase-js'

Deno.serve(async (_req) => {
  const supabaseUrl = Deno.env.get('SUPABASE_URL')!
  const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  const supabase = createClient(supabaseUrl, supabaseKey)

  const { data, error } = await supabase.rpc('cleanup_expired_processed_messages')

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), { status: 500 })
  }

  return new Response(
    JSON.stringify({ deleted_count: data, timestamp: new Date().toISOString() }),
    { headers: { "Content-Type": "application/json" } }
  )
})
```

**Schedule via GitHub Actions:**
```yaml
# .github/workflows/db-cleanup.yml
name: Database Cleanup
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:     # Manual trigger

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Call Supabase cleanup function
        run: |
          curl -X POST https://your-project.supabase.co/functions/v1/cleanup-messages \
            -H "Authorization: Bearer ${{ secrets.SUPABASE_ANON_KEY }}"
```

**Pros:** Serverless, fits Supabase ecosystem
**Cons:** Requires Supabase Edge Functions setup

---

#### **Option C: Application-level Scheduler (APScheduler)**

```python
# agents/src/autifyme_agents/scheduled_tasks.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

from autifyme_agents.integrations.storage.storage_factory import get_storage

logger = logging.getLogger(__name__)

def cleanup_expired_messages():
    """Run database cleanup for expired idempotency records."""
    try:
        storage = get_storage()
        # Call the PostgreSQL function via RPC
        deleted_count = storage._client.rpc('cleanup_expired_processed_messages').execute()
        logger.info(f"Cleanup completed: {deleted_count} expired messages removed")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)

def start_scheduled_tasks():
    """Initialize background scheduler for maintenance tasks."""
    scheduler = BackgroundScheduler()

    # Daily cleanup at 2 AM
    scheduler.add_job(
        cleanup_expired_messages,
        trigger=CronTrigger(hour=2, minute=0),
        id='cleanup_messages',
        name='Cleanup expired processed_messages',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Background scheduler started")
    return scheduler
```

**Add to FastAPI startup:**
```python
# agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py
from autifyme_agents.scheduled_tasks import start_scheduled_tasks

@app.on_event("startup")
async def startup_event():
    # Start background scheduler
    start_scheduled_tasks()
```

**Install dependency:**
```bash
uv pip install apscheduler
```

**Pros:** Runs within application, no external dependencies
**Cons:** Only runs when application is running (not suitable for serverless)

---

#### **Option D: Manual/Cron Job on Server**

For VPS or dedicated server deployments:

```bash
# Add to crontab: crontab -e
0 2 * * * psql $DATABASE_URL -c "SELECT cleanup_expired_processed_messages();" >> /var/log/db-cleanup.log 2>&1
```

**Pros:** Simple, works anywhere with cron
**Cons:** Requires shell access, manual setup

---

## **Monitoring Cleanup**

### **Check Cleanup Effectiveness**

```sql
-- How many expired messages exist?
SELECT COUNT(*) as expired_count
FROM processed_messages
WHERE expires_at < NOW();

-- Should be 0 if cleanup is running

-- Table growth rate
SELECT
    COUNT(*) as total_messages,
    MIN(created_at) as oldest_message,
    MAX(created_at) as newest_message,
    pg_size_pretty(pg_total_relation_size('processed_messages')) as table_size
FROM processed_messages;
```

### **Alert Thresholds**

Set up alerts if:
- `expired_count` > 1000 (cleanup not running)
- `table_size` > 100MB (unusual growth, investigate)
- `oldest_message` > 48 hours (cleanup failures)

---

## **Backup Strategy**

### **Automated Backups (Supabase)**

Supabase provides automatic daily backups on paid plans. Enable in dashboard:
- Settings → Database → Backups
- Retention: 7 days (free), 30 days (pro)

### **Manual Backup**

```bash
# Full database backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Table-specific backup
pg_dump $DATABASE_URL -t processed_messages > processed_messages_backup.sql
```

### **Restore from Backup**

```bash
psql $DATABASE_URL < backup_20251021.sql
```

---

## **Index Maintenance**

### **Check Index Usage**

```sql
-- Find unused indexes
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### **Rebuild Indexes (if needed)**

```sql
-- Reindex specific table
REINDEX TABLE workflow_outcomes;

-- Reindex all tables (maintenance window only!)
REINDEX DATABASE your_database_name;
```

---

## **Query Performance Monitoring**

### **Slow Query Identification**

```sql
-- Enable slow query logging (PostgreSQL config)
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1 second
SELECT pg_reload_conf();

-- View slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## **Storage Growth Monitoring**

### **Table Size Tracking**

```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY size_bytes DESC;
```

### **Database Size Limit Alerts**

```sql
-- Check current database size vs limit
SELECT
    pg_size_pretty(pg_database_size(current_database())) as current_size,
    '500 MB' as free_tier_limit,  -- Supabase free tier
    CASE
        WHEN pg_database_size(current_database()) > 500 * 1024 * 1024 * 0.8
        THEN 'WARNING: Approaching limit'
        ELSE 'OK'
    END as status;
```

---

## **Production Checklist**

- [ ] TTL cleanup scheduled (choose Option A-D above)
- [ ] Cleanup monitoring alerts configured
- [ ] Backup strategy documented and tested
- [ ] Slow query logging enabled
- [ ] Storage growth monitoring in place
- [ ] Index usage reviewed monthly
- [ ] Connection pool configured (Supabase handles automatically)
- [ ] Database credentials rotated quarterly

---

## **Troubleshooting**

### **Cleanup function not running**

```sql
-- Check if function exists
SELECT proname, prokind
FROM pg_proc
WHERE proname = 'cleanup_expired_processed_messages';

-- Test function manually
SELECT cleanup_expired_processed_messages();

-- Check for locks
SELECT * FROM pg_locks WHERE relation = 'processed_messages'::regclass;
```

### **High table bloat**

```sql
-- Check table bloat
SELECT
    schemaname, tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables
WHERE tablename = 'processed_messages';

-- Vacuum if needed
VACUUM ANALYZE processed_messages;
```

### **Connection pool exhaustion**

Supabase includes built-in PgBouncer connection pooling. Use the pooled connection string:
```
postgresql://[user]:[password]@[host]:6543/[db]?pgbouncer=true
```

---

## **Recommended Schedule**

| Task | Frequency | Time | Method |
|------|-----------|------|--------|
| Cleanup expired messages | Daily | 2 AM | pg_cron or GitHub Actions |
| Vacuum analyze | Weekly | Sunday 3 AM | pg_cron |
| Index usage review | Monthly | 1st of month | Manual query |
| Backup verification | Monthly | 1st of month | Manual test restore |
| Storage growth check | Weekly | Automated alert | SQL query |

---

## **Next Steps**

1. Choose cleanup scheduling option (A, B, C, or D based on your deployment)
2. Implement monitoring queries in your observability tool
3. Set up storage growth alerts
4. Test manual backup/restore process
5. Document in your operations runbook
