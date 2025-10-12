# Refactor to Native Library Patterns

**Purpose:** Audit custom implementations and refactor to use native LangChain/LangGraph/DeepAgents features

**Context:** As frameworks evolve, custom code often duplicates built-in functionality. This command performs deep analysis and refactors to standard patterns.

## Execution Steps

### Phase 1: Comprehensive Audit

1. **Research Current Library Features**
   - Search official docs for latest features (LangChain v1, LangGraph v1, DeepAgents)
   - Use WebFetch to get current documentation
   - Query latest blog posts and changelogs (2025)
   - NEVER rely on outdated knowledge - verify everything

2. **API Verification via REPL**
   ```bash
   # From root directory - uv auto-detects agents/pyproject.toml
   uv run python -c "
   from dotenv import load_dotenv
   load_dotenv('.env')

   import inspect
   # Inspect every API we're considering
   # Verify signatures, parameters, return types
   # Test with real calls, not just inspection
   "
   ```

3. **Systematic Code Analysis**
   For each major component:
   - Read current implementation
   - Identify framework features that could replace it
   - Compare line counts, complexity, maintainability
   - List pros/cons for each approach

4. **Create Audit Document**
   - File: `docs/architecture/LIBRARY_FEATURES_AUDIT_[YYYY].md`
   - Include: before/after code samples, line count savings, migration steps
   - Document: risks, testing requirements, rollback plan

### Phase 2: Implementation

5. **Prioritize Changes**
   - Phase 1: Quick wins (unused code removal)
   - Phase 2: High-impact refactors (interrupt handling, state management)
   - Phase 3: Observability improvements
   - Phase 4: Nice-to-haves

6. **Implement with TodoWrite**
   - Create detailed task list for tracking
   - Mark completed as you go
   - Update status in real-time

7. **Quality Checks**
   ```bash
   # From root directory - uv auto-detects project
   # Lint
   uv run ruff check . --fix

   # Import verification
   uv run python -c "from autifyme_agents.workflows.orchestration import WorkflowRunner; print('OK')"

   # Type checks
   uv run mypy .
   ```

### Phase 3: Documentation

8. **Create Migration Summary**
   - File: `docs/architecture/REFACTORING_SUMMARY_[YYYY].md`
   - Include:
     - Line count changes (before/after table)
     - Architecture diagrams (old vs new)
     - Performance impact analysis
     - Testing requirements
     - Rollback plan
     - Next steps

9. **Update Related Docs**
   - Architecture decision records
   - Design documents
   - README if public APIs changed

### Phase 4: Verification

10. **Testing Checklist**
    - [ ] All imports resolve
    - [ ] Lint passes (ruff)
    - [ ] Type checks pass (mypy)
    - [ ] Unit tests pass
    - [ ] Integration tests pass (local simulation)
    - [ ] End-to-end tests (staging environment)

## Key Principles

1. **Research First, Code Second**
   - Enumerate all viable options before choosing
   - Use WebSearch for latest docs (account for current year)
   - Test APIs in REPL before committing to implementation

2. **Think Exhaustively**
   - Consider edge cases, platform differences
   - Challenge assumptions with code inspection
   - When blocked, dig deeper - inspect source, test alternatives

3. **Document Complex Findings**
   - Create architectural analysis docs for multi-step migrations
   - Include code examples, not just descriptions
   - Make docs scannable (tables, summaries, checklists)

4. **Preserve Core Architecture**
   - Verify changes don't break hierarchical design
   - PM must remain main orchestrator
   - Maintain separation of concerns

5. **Non-Blocking Quality**
   - Tracking failures shouldn't crash workflows
   - Log errors, continue execution
   - Degrade gracefully

## Example: Recent Refactoring (2025-01-12)

**Task:** Replace custom HITL interrupt handling with native LangGraph patterns

**Audit findings:**
- Custom: 708 lines (InterruptCoordinator, StateManager, RecoveryStrategy)
- Native: Framework handles via `interrupt()` + `Command` + checkpoints
- Savings: 665 lines, 90% performance improvement

**Implementation:**
1. Removed unused middleware decorator (48 lines)
2. Rewrote WorkflowRunner to use native patterns
3. Deleted 3 coordinator files (708 lines)
4. Simplified OutcomeTracker (delegate to LangSmith)
5. Updated package exports
6. Passed all lint checks
7. Created comprehensive documentation

**Result:**
- ✅ 665 lines removed
- ✅ 90% faster HITL workflows
- ✅ Standard patterns (better docs)
- ✅ PM unchanged (main orchestrator)

## Success Criteria

- [ ] Comprehensive audit document created
- [ ] All custom code analyzed vs library features
- [ ] Implementation complete with TodoWrite tracking
- [ ] Lint/type checks pass
- [ ] Migration summary document created
- [ ] Testing plan documented
- [ ] Rollback plan documented

## Common Refactoring Targets

1. **Interrupt Handling**
   - Custom coordinators → Native `interrupt()` + `Command`
   - Custom state tables → Checkpoint-based state
   - Manual resume logic → Framework resume primitives

2. **Observability**
   - Custom tracking → LangSmith native tracing
   - Manual metrics → Framework-provided metrics
   - Custom logging → Structured framework logs

3. **Middleware**
   - Decorator patterns → LangChain v1 AgentMiddleware
   - Manual context injection → Middleware hooks
   - Custom summarization → SummarizationMiddleware

4. **Agent Creation**
   - Manual graph building → `create_agent` / `create_deep_agent`
   - Custom structured output → `response_format` parameter
   - Manual tool binding → Framework tool configs

## Notes

- Always verify library versions match documentation (v1, not v0.x)
- Use REPL extensively - documentation can lag reality
- Think harder for critical decisions - enumerate all options
- Create architectural analysis docs for complex migrations
- Test locally before WhatsApp (use CLI tools)

---

**Usage:** `/refactor-native` when custom code could use framework features
