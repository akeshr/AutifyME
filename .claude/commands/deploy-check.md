# Deploy Check

Pre-deployment validation checklist.

## Usage

```
/deploy-check
```

## Task

Run comprehensive pre-deployment checks to ensure code quality and readiness:

### 1. Code Quality
- Run linting (ruff) - must pass
- Run tests (pytest) with coverage - must pass
- Check coverage >70% for critical files
- Verify no test failures

### 2. Architecture Compliance
- Verify DeepAgents patterns used correctly (write_todos in PM/departments)
- Check HITL resume at PM level (not department)
- Verify Hexagonal architecture maintained (no context leakage in tools)
- Check for missing planning tools

### 3. Environment Variables
- Verify all required variables set:
  - SUPABASE_URL, SUPABASE_ANON_KEY
  - DATABASE_URL
  - OPENAI_API_KEY
  - WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN
- Show which are set (don't expose values)

### 4. Code Hygiene
- Check for TODOs/FIXMEs (list first 10 if any)
- Check for unused imports
- Verify no critical dependencies missing

### 5. Database Connections
- Test Supabase connection
- Test PostgreSQL connection
- Verify tables accessible

### 6. API Access
- Test OpenAI API
- Test LangSmith API (warn if unavailable, don't fail)

### 7. Git Status
- Check for uncommitted changes
- Verify current branch
- Warn if not on main

## Output

Generate checklist report:
- ✅/❌ for each check category
- List of blockers (must fix before deploy)
- List of warnings (non-critical issues to monitor)
- **Deploy Status**: Ready / With Caution / Not Ready
- **Recommendation**: Deploy / Fix issues first / Review warnings

## Quick Check

For rapid validation: `ruff check && pytest -q` is sufficient for hotfixes

## Notes

- Run full check before merging to main
- Quick check sufficient for hotfixes
- Always test in staging first
- Monitor logs after deployment
