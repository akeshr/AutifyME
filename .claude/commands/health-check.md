# Health Check

Comprehensive system health validation.

## Usage

```
/health-check [component]
```

**Components**: `all`, `db`, `api`, `agents`, `services`

## Task

Validate system health across all critical components:

### 1. Database Connections
- **Supabase**: Test connection, query company profile, check products table access
- **PostgreSQL**: Test checkpointer connection, verify tables exist, count checkpoints
- Check connection pool health

### 2. External APIs
- **OpenAI**: Verify API key, test with minimal completion request
- **WhatsApp**: Check credentials (phone_number_id, access_token, verify_token)
- **LangSmith**: Test tracing connection (non-critical, should warn not fail)

### 3. Agent System
- **PM Factory**: Verify PM can be instantiated with checkpointer + storage
- **Departments**: Test cataloging department creation
- **Specialists**: Verify image_analysis_specialist, cataloging_specialist initialization
- **Tools**: Check tool registration and availability

### 4. Configuration
- Verify all required environment variables set
- Check file permissions on temp directories (/tmp/media_downloads)
- Validate webhook tokens and secrets (show masked values)

### 5. Dependencies
- Check critical library versions (langchain, langgraph, deepagents)
- Verify no import errors
- Test LLM factory configuration (default LLM, vision LLM)

### 6. Runtime State
- Check pending approvals count (warn if >10)
- Verify checkpoint count (warn if >10,000)
- Check media downloads directory (file count, disk usage)
- Test media download directory writable

### 7. System Resources
- Check disk space (especially /tmp)
- Memory usage (if available)

## Output

Generate health report with:
- 🟢 Healthy Components (✅ checkmarks)
- ⚠️ Warnings (degraded but functional)
- ❌ Critical Issues (requires immediate attention)
- 📊 Statistics (counts, sizes, usage)
- 🔧 Recommendations (action items)
- **Overall Status**: Healthy / Degraded / Critical

## Notes

- Run before deployments or after incidents
- Non-critical failures (LangSmith) should warn, not fail
- Include actionable remediation steps for failures
- Show masked credentials (first 4 + last 4 chars)
