# Check Deps

Check dependency versions and compatibility.

## Usage

```
/check-deps [check-type]
```

**Types**: `unused`, `versions`, `conflicts`, `reimplemented`, `alpha`, `all`

## Task

Check dependencies for issues, version mismatches, and opportunities to use built-in features:

### 1. Check Unused Imports
- Run `ruff check --select F401 src/`
- Auto-fix with `--fix` flag

### 2. Check Version Constraints
Verify critical versions:
- `langchain` == 1.0.0a10 (alpha, expect instability)
- `langgraph` == 1.0.0a4 (alpha, verify APIs with inspect)
- `deepagents` == 0.0.11rc1 (RC, check for updates)
- `pydantic` >= 2.0

### 3. Check for Version Conflicts
- List installed versions (`uv pip list | grep langchain`)
- Verify compatibility with Python REPL

### 4. Check for Reimplemented Features
Search for custom implementations that could use library features:
- Custom planning (should use `write_todos`)
- Custom state management (should use checkpointer)
- Custom error handling (should use ToolException)
- Custom middleware (should use LangChain middleware)

### 5. Check Alpha API Usage
Find usage of unstable APIs:
- Direct langchain_core usage
- Experimental/beta features
- Document alpha API dependencies

### 6. Check Missing Dependencies
Test all critical imports:
- `create_agent`, `PostgresSaver`, `create_deep_agent`, `write_todos`
- OpenAI, Anthropic clients

### 7. Check for Security Issues
- Check for pinned vulnerable versions (`uv pip list --outdated`)
- Run `safety check` if available

### 8. Check DeepAgents Feature Usage
Verify we're using built-in features:
- `write_todos`, `FilesystemMiddleware`, `SubAgent/CustomSubAgent`

## Output

Generate dependency report with:
- **Installed Versions**: List with alpha/RC warnings
- **Issues Found**: Unused imports, version conflicts, reimplemented features, alpha API usage
- **Recommendations**: Remove unused, replace custom code, pin versions, verify APIs
- **Missing Opportunities**: DeepAgents features not being used

## Notes

- Alpha versions expect breaking changes
- Always verify alpha APIs with `inspect.signature()`
- Keep UV_REPL_BEST_PRACTICES.md updated
- Pin versions in pyproject.toml for stability
- Check for updates monthly
