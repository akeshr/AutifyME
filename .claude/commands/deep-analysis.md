# Deep Architectural Analysis Command

Execute comprehensive architectural review and implementation gap analysis.

## What This Does

1. **Review Architectural Canon** - Read all design docs, guidelines, and specs
2. **Analyze Current Implementation** - Audit codebase, specialists, tools, persistence
3. **Inspect Database State** - Query Supabase for schema completeness and data
4. **Map Implementation Gaps** - Compare designed vs implemented features
5. **Identify Architectural Debt** - Find blockers, missing components, technical debt
6. **Create Phased Roadmap** - Prioritized implementation plan with discussion checkpoints

## Outputs

- Implementation status for all domains (Product Onboarding, Marketing, etc.)
- Database schema gap analysis
- Specialist implementation mapping
- Complete phased roadmap with milestones
- Critical next actions with discussion checkpoints

## Usage

```
/deep-analysis
```

## When to Use

- Before starting new domain implementation
- After major architectural changes
- When planning next development phase
- To validate current implementation completeness
- Before major releases

## Process

The agent will:
1. Read architecture docs (DOMAIN_DESIGN_GUIDELINES, ACTUAL_IMPLEMENTATION_ARCHITECTURE, etc.)
2. Scan codebase for specialists, tools, workflows
3. Query database via Supabase MCP (tables, migrations, data counts)
4. Compare design docs vs actual implementation
5. Generate comprehensive report with phased roadmap
6. Present findings with discussion checkpoints

## Result Format

- **Executive Summary** - Current state vs designed state
- **Implementation Audit** - What's built, what's missing
- **Gap Analysis** - Detailed breakdown by domain
- **Phased Roadmap** - Sequential implementation plan with checkpoints
- **Immediate Next Actions** - What to do this week

## Example Output

```
DOMAIN STATUS:
✅ Product Onboarding - Fully Implemented (DB + 5 Specialists + Persistence)
❌ Marketing Campaigns - Design Only (No DB schema, no specialists)

CRITICAL GAPS:
- Marketing DB schema missing (15 tables needed)
- 5 marketing specialists not implemented
- Campaign persistence tool missing

ROADMAP:
Phase 1: Complete DB Schema Design (1-2 weeks) → DISCUSS
Phase 2: Marketing Specialists (2-3 weeks) → DISCUSS
Phase 3: Persistence Layer (1 week) → DISCUSS
...
```

## Notes

- This is a read-only analysis (no code changes)
- Requires Supabase MCP connection for DB inspection
- Output helps plan implementation sequences
- Use for strategic planning, not tactical debugging
