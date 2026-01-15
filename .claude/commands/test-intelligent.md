# Test PM Workflow

**DEPRECATED:** Use `/eval test <scenario>` instead.

This command is a redirect to the consolidated `/eval` skill.

## Usage

```bash
# Instead of:
/test-intelligent "Catalog these sneakers"

# Use:
/eval test PM-01                     # Run predefined scenario
/eval test "Catalog these sneakers"  # Run ad-hoc scenario

# For the full test -> evaluate -> improve -> retest cycle:
/eval test PM-01                     # 1. Run scenario
/eval analyze <trace_id> --thorough  # 2. Analyze if issues
/eval improve pm                     # 3. Fix issues
/eval test PM-01                     # 4. Retest
```

## Task

Redirect to `/eval test $ARGUMENTS`.

See `/eval` skill for full documentation: `.claude/skills/eval/SKILL.md`
