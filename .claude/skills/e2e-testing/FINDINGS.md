# Evaluation Findings Log

Human-readable log of evaluation findings. Structured data also stored in Supabase `test_runs` table.

---

## Summary Statistics

| Metric | Value | Updated |
|--------|-------|---------|
| Total Evaluations | 0 | - |
| Pass Rate | - | - |
| Open Issues | 0 | - |
| Regressions | 0 | - |

---

## Issue Patterns

Track recurring patterns across evaluations:

| Pattern | Occurrences | Status | Notes |
|---------|-------------|--------|-------|
| - | - | - | - |

---

## Recent Findings

### Template

```markdown
## [YYYY-MM-DD] [Scenario ID]: [Brief Title]

**Scenario:** [Name]
**Result:** PASS | PARTIAL | FAIL | ERROR
**Trace:** [trace_id]

### What Happened
[Brief description of actual behavior]

### Expected
[What should have happened]

### Issues Found
- [ ] Issue 1 description
- [ ] Issue 2 description

### Root Cause
[If identified - link to specific prompt/protocol/code]

### Fix Applied
[Description of fix]
- File: [path]
- Change: [summary]

### Verification
- [ ] Re-ran scenario
- [ ] Issue resolved
- [ ] No regressions
- Verification trace: [trace_id]

### Actions
- [ ] Add to regression suite
- [ ] Update documentation
- [ ] Create follow-up scenarios

---
```

---

## 2025-01 Findings

<!-- Add findings chronologically, newest first -->

### [2025-01-08] Initial Setup

**Note:** E2E testing skill created. Begin evaluation process.

**Next Steps:**
1. Run smoke suite to establish baseline
2. Identify any immediate issues
3. Document findings here

---

## Archived Findings

<!-- Move old findings here after 30 days -->

---

## Finding Categories

Use these categories when logging:

| Category | Description |
|----------|-------------|
| `ROUTING` | PM routed to wrong specialist |
| `INTENT` | Intent misunderstood |
| `CONTEXT` | Context not passed correctly |
| `HITL` | Approval flow issue |
| `PROTOCOL` | Protocol not loaded/followed |
| `TOOL` | Tool usage error |
| `OUTPUT` | Output quality issue |
| `PERFORMANCE` | Latency or token issue |
| `EDGE_CASE` | Unexpected input handling |

---

## Severity Levels

| Severity | Description | Action |
|----------|-------------|--------|
| `CRITICAL` | Workflow fails completely | Fix immediately |
| `HIGH` | Major functionality impacted | Fix in current sprint |
| `MEDIUM` | Degraded experience | Schedule fix |
| `LOW` | Minor issue | Track for later |

---

## How to Use This Log

### Adding Findings

1. Copy the template above
2. Fill in all sections
3. Add under "Recent Findings" (newest first)
4. Update summary statistics

### Linking to Traces

Always include:
- `trace_id` from LangSmith
- `scenario_id` from SCENARIOS.md
- `test_run_id` from Supabase (if available)

### After Fixing

1. Update finding with fix details
2. Re-run scenario
3. Add verification trace
4. Mark checkboxes complete
5. If verified, add scenario to regression suite

### Monthly Maintenance

1. Archive findings older than 30 days
2. Update issue patterns table
3. Review recurring issues for systemic fixes
4. Update summary statistics
