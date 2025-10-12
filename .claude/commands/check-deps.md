# Check Dependencies

Analyze dependencies for issues and optimization opportunities.

## Usage

```
/check-deps [check-type]
```

**Types**: `unused`, `versions`, `conflicts`, `reimplemented`, `alpha`, `all`

## Task

Check dependencies for issues, version mismatches, and opportunities to use built-in features.

### 1. Check Unused Imports

```bash
cd agents
# Check for unused imports with ruff
uv run ruff check --select F401 src/
```

**Fix automatically**:
```bash
uv run ruff check --select F401 --fix src/
```

### 2. Check Version Constraints

```bash
cd agents
cat pyproject.toml | grep -A 50 "dependencies ="
```

**Verify critical versions**:
- `langchain = "^1.0.0a10"` (alpha, expect instability)
- `langgraph = "^1.0.0a4"` (alpha, verify APIs with inspect)
- `deepagents = "^0.0.11rc1"` (RC, check for updates)
- `langchain-openai`
- `pydantic = "^2.0"`

### 3. Check for Version Conflicts

```bash
cd agents
uv pip list | grep langchain
uv pip list | grep pydantic
```

**Verify compatibility**:
```bash
uv run python -c "
import langchain
import langgraph
import deepagents
import pydantic

print(f'langchain: {langchain.__version__}')
print(f'langgraph: {langgraph.__version__}')
print(f'deepagents: {deepagents.__version__}')
print(f'pydantic: {pydantic.__version__}')
"
```

### 4. Check for Reimplemented Features

**Search for custom implementations that could use library features**:

```bash
cd agents
# Custom planning (should use write_todos)
grep -r "def.*plan\|def.*track.*progress" src/ --include="*.py" | grep -v test | grep -v "__pycache__"

# Custom state management (should use checkpointer)
grep -r "def.*save.*state\|def.*load.*state" src/ --include="*.py" | grep -v test

# Custom error handling (should use ToolException)
grep -r "class.*Error.*Exception" src/ --include="*.py" | grep -v test

# Custom middleware (should use LangChain middleware)
grep -r "def.*before_\|def.*after_" src/ --include="*.py" | grep -v test | grep -v "Middleware"
```

### 5. Check Alpha API Usage

**Find usage of unstable APIs**:
```bash
cd agents
# Check for direct langchain_core usage
grep -r "from langchain_core" src/ --include="*.py"

# Check for experimental features
grep -r "@experimental\|@beta" src/ --include="*.py"
```

**Document alpha API dependencies**:
```bash
cd agents
grep -r "from deepagents import\|from langgraph" src/ --include="*.py" | cut -d: -f1 | sort -u
```

### 6. Check Missing Dependencies

**Test all imports**:
```bash
cd agents
uv run python -c "
# Test critical imports
try:
    from langchain.agents import create_agent
    from langgraph.checkpoint.postgres import PostgresSaver
    from deepagents import create_deep_agent
    from deepagents.tools import write_todos
    from openai import OpenAI
    from anthropic import Anthropic
    print('✅ All critical imports working')
except ImportError as e:
    print(f'❌ Import error: {e}')
"
```

### 7. Check for Security Issues

```bash
cd agents
# Check for pinned vulnerable versions
uv pip list --outdated

# Check for known vulnerabilities (if safety is installed)
# pip install safety
# safety check
```

### 8. Check DeepAgents Feature Usage

**Verify we're using built-in features**:
```bash
cd agents
# Should be using write_todos
grep -r "write_todos" src/

# Should be using FilesystemMiddleware if needed
grep -r "FilesystemMiddleware" src/

# Should be using SubAgent/CustomSubAgent
grep -r "SubAgent\|CustomSubAgent" src/
```

### 9. Generate Report

```markdown
## Dependency Analysis Report

### Installed Versions
- langchain: [version] [⚠️ alpha]
- langgraph: [version] [⚠️ alpha]
- deepagents: [version] [⚠️ RC]
- pydantic: [version]
- openai: [version]

### Issues Found

#### Unused Imports
- `file.py:line` - [import statement]

#### Version Conflicts
- [package]: expected [version], found [version]

#### Reimplemented Features
**File**: `path/to/file.py`
- Custom planning logic → Use `write_todos`
- Custom state management → Use LangGraph checkpointer
- Custom error handling → Use `ToolException`

#### Alpha API Usage
**Unstable APIs in use**:
- `langchain.agents.create_agent` (verify with inspect)
- `langgraph.types.Command` (check for changes)
- `deepagents.create_deep_agent` (RC, expect updates)

### Recommendations

1. **Remove unused imports**: Run `ruff check --fix`
2. **Replace custom code**: Use DeepAgents built-in features
3. **Pin alpha versions**: Prevent breaking changes
4. **Monitor for updates**: Check weekly for stable releases
5. **Verify APIs**: Use `inspect` before depending on alpha APIs

### Missing Opportunities

- [DeepAgents feature not being used]
- [LangChain v1 pattern not adopted]
- [Middleware that could be added]
```

## Notes

- Alpha versions expect breaking changes
- Always verify alpha APIs with `inspect.signature()`
- Keep UV_REPL_BEST_PRACTICES.md updated
- Pin versions in pyproject.toml for stability
- Check for updates monthly
