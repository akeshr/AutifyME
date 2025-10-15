# Health Check

Validate all system components are healthy and accessible.

## Usage

```
/health-check [component]
```

**Components**: `all`, `db`, `api`, `agents`, `services`

## Task

Check health of databases (Supabase, PostgreSQL), external APIs (OpenAI, WhatsApp, LangSmith), agent system (PM, departments, specialists), configuration, dependencies, runtime state, and system resources.

Generate comprehensive health report with:
- 🟢 Healthy components with details
- ⚠️ Warnings (degraded but functional)
- ❌ Critical issues requiring immediate attention
- 📊 Statistics (pending approvals, checkpoints, media files, disk usage)
- 🔧 Actionable recommendations

Non-critical failures (LangSmith) should warn, not fail.
