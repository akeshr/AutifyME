# Check Architecture

Validate architectural patterns and best practices.

## Usage

```
/check-architecture [focus]
```

**Focus**: `all`, `deepagents`, `hitl`, `hexagonal`, `context`, `tools`

## Task

Scan codebase for architectural violations and anti-patterns.

### 1. Check DeepAgents Patterns

**Planning Tools**:
```bash
cd agents
# Check if planning tools are used
grep -r "write_todos" src/autifyme_agents/workflows/
grep -r "write_todos" src/autifyme_agents/departments/
```

**Expected**: PM and departments should import and use `write_todos`.

**SubAgent Patterns**:
```bash
# Check CustomSubAgent usage
grep -r "CustomSubAgent" src/autifyme_agents/workflows/
```

**Expected**: PM uses CustomSubAgent for pre-built department graphs.

**Built-in Tools**:
```bash
# Check for custom code that could use DeepAgents features
grep -r "def.*_plan\|def.*_coordinate\|def.*_track" src/
```

**Expected**: Use DeepAgents planning instead of custom coordination.

### 2. Check HITL Patterns

**Interrupt Configuration**:
```bash
# Check tool_configs usage
grep -r "tool_configs" src/autifyme_agents/departments/
grep -r "ToolConfig" src/autifyme_agents/departments/
```

**Expected**: Departments configure HITL via tool_configs.

**Resume Pattern**:
```bash
# Check resume implementation
grep -A 20 "def resume_workflow" src/autifyme_agents/workflows/orchestration/interrupt_coordinator.py
```

**Expected**:
- Resume at PM level using pm_factory
- Use Command.resume with correct format
- Fully consume stream to avoid GeneratorExit

### 3. Check Hexagonal Architecture

**Port Definitions**:
```bash
# Check ports are defined
ls -l src/autifyme_agents/core/ports.py
```

**Adapter Usage**:
```bash
# Check adapters implement ports
grep -r "StorageInterface" src/autifyme_agents/integrations/
grep -r "MessagingChannel" src/autifyme_agents/workflows/channels/
```

**Core Dependencies**:
```bash
# Core should NOT import from integrations
grep -r "from.*integrations" src/autifyme_agents/core/
grep -r "from.*integrations" src/autifyme_agents/workflows/project_manager.py
```

**Expected**: No imports from integrations in core/workflows.

### 4. Check Context Engineering

**Middleware Usage**:
```bash
# Check middleware is used for context injection
grep -r "CompanyContextMiddleware" src/
```

**Tool Context**:
```bash
# Tools should NOT accept company_profile directly
grep -r "def.*company_profile.*:" src/autifyme_agents/tools/
```

**Expected**: Tools get context via middleware, not function parameters.

**Prompt Parameterization**:
```bash
# Check prompts are templates
grep -r "\.format\(" src/autifyme_agents/workflows/project_manager.py
```

**Expected**: Prompts templated with company context.

### 5. Check Tool Patterns

**Tool Factories**:
```bash
# All tools should be factories
grep -r "def create_.*_tool" src/autifyme_agents/tools/
```

**ToolException Usage**:
```bash
# Tools should raise ToolException for errors
grep -r "ToolException" src/autifyme_agents/tools/
grep -r "raise.*ToolException" src/autifyme_agents/tools/
```

**Structured Outputs**:
```bash
# Check tools return Pydantic models
grep -r "-> Product\|-> ImageAnalysisResult\|-> CatalogingResult" src/autifyme_agents/tools/
```

### 6. Check Specialist Patterns

**Agent Factory**:
```bash
# Specialists should use create_agent
grep -r "create_agent" src/autifyme_agents/specialists/
```

**Response Format**:
```bash
# Check structured outputs
grep -r "response_format=" src/autifyme_agents/specialists/
```

**No Direct LLM Calls**:
```bash
# Should NOT have direct llm.invoke outside of create_agent
grep -r "llm\.invoke\|llm\.ainvoke" src/autifyme_agents/specialists/
```

### 7. Check Import Patterns

**Alpha API Usage**:
```bash
# Check for langchain_core usage (should use langchain v1)
grep -r "from langchain_core" src/
```

**Expected**: Minimal langchain_core usage, prefer langchain v1.

**Deprecated Imports**:
```bash
# Check for old patterns
grep -r "from langchain.chains import\|from langchain.agents import AgentExecutor" src/
```

**Expected**: No deprecated chain/executor patterns.

### 8. Generate Report

```markdown
## Architecture Validation Report

### ✅ Compliant Patterns

#### DeepAgents
- Planning tools: ✅/❌ Used in PM and departments
- CustomSubAgent: ✅/❌ Proper delegation hierarchy
- Built-in features: ✅/❌ No custom reimplementation

#### HITL
- Tool configs: ✅/❌ Proper ToolConfig usage
- Resume pattern: ✅/❌ PM-level resume with Command
- Stream handling: ✅/❌ Full consumption, no GeneratorExit

#### Hexagonal Architecture
- Ports defined: ✅/❌ Clean interfaces
- Adapters compliant: ✅/❌ Implement ports
- Core dependencies: ✅/❌ No integration imports

#### Context Engineering
- Middleware: ✅/❌ CompanyContextMiddleware used
- Tool context: ✅/❌ No direct profile parameters
- Prompt templates: ✅/❌ Proper parameterization

### ❌ Violations Found

#### [Category]
**File**: `path/to/file.py:123`
**Issue**: [Description]
**Fix**: [Recommended action]

---

### 📊 Statistics

- Total files scanned: [count]
- Violations found: [count]
- Compliance rate: [percentage]%

### 🔧 Recommendations

1. [Priority fix]
2. [Next fix]
3. [Improvement]
```

## Notes

- Run before major changes
- Run before deployment
- Check after merging feature branches
- Update CLAUDE.md if patterns change
