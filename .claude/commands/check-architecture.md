# Check Architecture

Validate architectural patterns and best practices.

## Usage

```
/check-architecture [focus]
```

**Focus**: `all`, `deepagents`, `hitl`, `hexagonal`, `context`, `tools`

## Task

Scan codebase for architectural violations and anti-patterns:

### 1. Check DeepAgents Patterns
- **Planning Tools**: `write_todos` used in PM and departments
- **SubAgent Patterns**: CustomSubAgent usage for departments
- **Built-in Tools**: No custom reimplementation of DeepAgents features

### 2. Check HITL Patterns
- **Interrupt Configuration**: tool_configs with ToolConfig usage
- **Resume Pattern**: PM-level resume using pm_factory, Command.resume, full stream consumption

### 3. Check Hexagonal Architecture
- **Port Definitions**: Ports defined in `core/ports.py`
- **Adapter Usage**: Adapters implement StorageInterface, MessagingChannel
- **Core Dependencies**: No imports from `integrations` in `core/` or PM

### 4. Check Context Engineering
- **Middleware Usage**: CompanyContextMiddleware for context injection
- **Tool Context**: Tools should NOT accept company_profile as parameter
- **Prompt Parameterization**: Prompts templated with company context

### 5. Check Tool Patterns
- **Tool Factories**: All tools are factory functions
- **ToolException**: Tools raise ToolException for errors
- **Structured Outputs**: Tools return Pydantic models

### 6. Check Specialist Patterns
- **Agent Factory**: Specialists use create_agent
- **Response Format**: Structured outputs via response_format parameter
- **No Direct LLM**: No llm.invoke outside create_agent

### 7. Check Import Patterns
- **Alpha API Usage**: Minimal langchain_core usage, prefer langchain v1
- **Deprecated Imports**: No AgentExecutor, chain patterns

## Output

Generate architecture validation report with:
- ✅ **Compliant Patterns**: DeepAgents, HITL, Hexagonal, Context categories
- ❌ **Violations Found**: File/line, issue description, recommended fix
- 📊 **Statistics**: Files scanned, violations, compliance rate
- 🔧 **Recommendations**: Prioritized fix list

## Notes

- Run before major changes
- Run before deployment
- Check after merging feature branches
- Update CLAUDE.md if patterns change
