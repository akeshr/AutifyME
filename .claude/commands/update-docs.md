# Update Docs

Comprehensive documentation audit, cleanup, and consolidation. Eliminate bloat, archive obsolete docs, consolidate redundancies, and ensure all documentation reflects current codebase reality.

## Usage

```
/update-docs [mode]
```

**Modes**: `audit`, `consolidate`, `verify`, `all`

- `audit` - Full documentation health check with actionable recommendations
- `consolidate` - Execute consolidation and cleanup actions
- `verify` - Verify all code examples and architectural claims against implementation
- `all` - Complete audit → consolidate → verify cycle

## Task

Perform comprehensive documentation audit and cleanup using the **docs-maintainer agent**:

### Phase 1: Inventory & Analysis
- List ALL documentation files with creation/modification dates
- **[CRITICAL]** Identify files created/modified in last 2-3 days as latest design reference
- Categorize by domain: core, workflows, tech, testing, deployment, etc.
- Deep-read every document thoroughly
- Compare against actual code in `agents/src/autifyme_agents/`

### Phase 2: Bloat Identification
Identify and categorize problematic documentation:

**DELETE Candidates:**
- Completely obsolete directories/files superseded by newer docs
- Planning documents for completed work
- Outdated architectural references (e.g., 3-level when code is 2-level)

**ARCHIVE Candidates:**
- Pre-implementation research (conclusions now in production docs)
- Completed migration documentation
- Rejected design alternatives (preserve for rationale)
- Historical analysis with no current relevance

**CONSOLIDATE Candidates:**
- Multiple docs covering same topic (e.g., LangChain patterns across 3+ files)
- Duplicate reference documentation
- Overlapping workflow specifications
- Fragmented implementation plans that should be unified

**UPDATE Candidates:**
- Docs with accurate core but outdated examples
- Navigation files missing references to active docs
- Incomplete cross-linking between related docs

### Phase 3: Code Verification
For each architectural claim in documentation:
- Verify against actual implementation in codebase
- Check imports, class names, patterns, configurations
- Validate code examples are executable and current
- Flag architectural debt or implementation deviations
- Use `inspect`/`dir` for library API verification if needed

### Phase 4: Consolidation Mapping
Create actionable consolidation plan:
```
Target Doc → Source Docs to Merge → Rationale → Code Evidence
```

### Phase 5: Generate Report
Provide structured findings with:

1. **Executive Summary**: Documentation health score, major issues, consolidation opportunities

2. **Detailed Findings Table**:
   - File path with absolute path references
   - Status (DELETE/ARCHIVE/CONSOLIDATE/UPDATE/KEEP)
   - Specific issues found
   - Recommendation with rationale
   - Code evidence supporting recommendation

3. **Consolidation Map**: Exact merge targets and sequences

4. **Critical Updates Needed**: Sections contradicting current code

5. **Deletion/Archive Candidates**: With justification

6. **Action Plan**: Prioritized phases with effort estimates and risk assessment

### Standards & Criteria

**Check for:**
- Outdated architectural references (verify hierarchy, patterns, tool names)
- Research docs for completed implementations
- Migration docs for completed migrations
- Duplicate coverage of same topics
- Missing navigation references
- Incomplete cross-linking
- Code examples that don't match current implementation
- Contradictions between documents
- Planning docs that should be archived post-implementation
- Files created recently (2-3 days) - treat as latest design authority

**Verification Requirements:**
- All code examples must be verified against actual implementation
- All architectural claims checked against current codebase structure
- Library API references validated (especially LangChain v1 alpha instability)
- File modification dates considered when determining latest authority

**Consolidation Principles:**
- Single source of truth for each topic
- Latest design files (last 2-3 days) take precedence
- Archive historical artifacts, don't delete design rationale
- Preserve rejected alternatives for architectural context
- Update navigation hubs to reference all active docs

**Be Ruthless:**
- If outdated → flag for update or archive
- If redundant → consolidate to single source
- If bloated → trim or restructure
- If irrelevant → archive or delete
- Only keep what serves current architectural reality

Generate comprehensive audit report with clear action plan, risk assessment, and estimated effort for each phase.
