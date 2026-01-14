# Evaluate Trace

**DEPRECATED:** Use `/eval analyze <trace_id>` instead.

This command is a redirect to the consolidated `/eval` skill.

## Usage

```bash
# Instead of:
/evaluate <trace_id>

# Use:
/eval analyze <trace_id>           # Quick analysis (code graders only)
/eval analyze <trace_id> --thorough  # Full analysis (code + model graders)
```

## Task

Redirect to `/eval analyze $ARGUMENTS`.

See `/eval` skill for full documentation: `.claude/skills/eval/SKILL.md`
