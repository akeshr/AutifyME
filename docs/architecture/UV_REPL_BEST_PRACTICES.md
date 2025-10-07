# UV REPL Best Practices for AutifyME

**Date:** 2025-10-07
**Purpose:** Document correct `uv run` usage patterns for REPL testing with environment variables

---

## TL;DR - The Right Way

```bash
# ✅ CORRECT - Loads .env, resolves dependencies properly
cd agents && uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')  # Load project root .env
# ... your code with API keys available
"

# ❌ INCORRECT - Skips project config, no .env loading
cd agents && uv run --no-project python -c "..."
```

---

## The Problem We Solved

### Initial Issue
When running REPL tests with `uv run --no-project`, the `.env` file at project root was not loaded, causing API key errors:

```bash
# This failed with "OPENAI_API_KEY not set"
cd agents && uv run --no-project python -c "
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model='gpt-4o-mini')  # ❌ Error: API key not set
"
```

### Root Cause
- `uv run --no-project` bypasses the project's environment setup
- No automatic `.env` file loading occurs
- Environment variables from shell session only (not from `.env` file)

---

## Solution: Project Mode + Prerelease Config

### Step 1: Enable Prerelease in pyproject.toml

**File:** `pyproject.toml`

```toml
[tool.uv]
prerelease = "allow"  # Required for LangChain v1 alpha packages
```

**Why:** Our project uses v1 alpha packages (`langchain==1.0.0a12`, `langchain-core==1.0.0a7`, etc.). Without `prerelease = "allow"`, `uv run` fails to resolve dependencies.

### Step 2: Use Project Mode with dotenv

**Pattern:**
```bash
cd agents && uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')  # Relative to agents/ directory

# Now environment variables are available
import os
api_key = os.getenv('OPENAI_API_KEY')
print(f'API key loaded: {\"Yes\" if api_key else \"No\"}')
"
```

**Benefits:**
- ✅ Loads `.env` from project root
- ✅ Resolves project dependencies correctly
- ✅ Uses installed packages from virtual environment
- ✅ Works with pre-release packages

---

## Common REPL Patterns

### Pattern 1: Quick Library Inspection (No API Keys Needed)

```bash
# Inspect signatures, check available methods
cd agents && uv run python -c "
from langchain.agents import create_agent
import inspect
print(inspect.signature(create_agent))
"
```

**When to use:** Verifying API signatures, checking available exports, testing imports.

**Note:** No need to load `.env` if you're not making actual API calls.

---

### Pattern 2: Testing with API Keys

```bash
# Full integration test with real LLM
cd agents && uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model='gpt-4o-mini')
response = llm.invoke('Say hello')
print(f'Response: {response.content}')
"
```

**When to use:** Testing actual LLM calls, verifying API connectivity, integration smoke tests.

**Important:** Always load `.env` explicitly with `load_dotenv()`.

---

### Pattern 3: Testing with Fake Models (No API Keys)

```bash
# Test agent structure without API calls
cd agents && uv run python -c "
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.language_models.fake_chat_models import FakeChatModel

@tool
def my_tool(input: str) -> str:
    return f'Processed: {input}'

fake_llm = FakeChatModel(responses=['test response'])
agent = create_agent(model=fake_llm, tools=[my_tool])

print(f'Agent created: {type(agent).__name__}')
"
```

**When to use:** Testing agent structure, middleware integration, graph compilation without consuming API credits.

**Benefit:** No API keys needed, fast iteration.

---

## Environment Variable Loading Hierarchy

**Priority Order (highest to lowest):**

1. **Shell environment variables** - Set in current session
   ```bash
   export OPENAI_API_KEY="sk-..."
   cd agents && uv run python -c "import os; print(os.getenv('OPENAI_API_KEY'))"
   ```

2. **`.env` file via `load_dotenv()`** - Explicitly loaded in code
   ```python
   from dotenv import load_dotenv
   load_dotenv('../.env')  # Loads into os.environ
   ```

3. **System environment variables** - OS-level configuration
   - Windows: System Properties → Environment Variables
   - Linux/Mac: `/etc/environment`, `.bashrc`, `.zshrc`

**Note:** `load_dotenv()` does NOT override existing environment variables by default. Shell variables take precedence.

---

## Common Mistakes & Fixes

### Mistake 1: Wrong .env Path

```bash
# ❌ WRONG - .env is at project root, not in agents/
cd agents && uv run python -c "
from dotenv import load_dotenv
load_dotenv('.env')  # Looks in agents/.env (doesn't exist)
"
```

**Fix:**
```bash
# ✅ CORRECT - Use relative path to project root
load_dotenv('../.env')
```

---

### Mistake 2: Forgetting to Import load_dotenv

```bash
# ❌ WRONG - Expects .env to load automatically
cd agents && uv run python -c "
import os
api_key = os.getenv('OPENAI_API_KEY')  # None!
"
```

**Fix:**
```bash
# ✅ CORRECT - Explicit loading required
from dotenv import load_dotenv
load_dotenv('../.env')
```

---

### Mistake 3: Using --no-project Flag

```bash
# ❌ WRONG - Bypasses project config
cd agents && uv run --no-project python -c "..."
```

**Fix:**
```bash
# ✅ CORRECT - Use project mode
cd agents && uv run python -c "..."
```

**Exception:** Only use `--no-project` for quick library inspections that don't need dependencies or env vars.

---

## Debugging Environment Loading

### Check if .env File is Loaded

```bash
cd agents && uv run python -c "
from dotenv import load_dotenv
import os

env_path = '../.env'
loaded = load_dotenv(env_path)

print(f'dotenv loaded: {loaded}')
print(f'File exists: {os.path.exists(env_path)}')

# Check specific variables
vars_to_check = ['OPENAI_API_KEY', 'SUPABASE_URL', 'LANGSMITH_API_KEY']
for var in vars_to_check:
    value = os.getenv(var)
    print(f'{var}: {\"Set\" if value else \"Not set\"}')
"
```

### Verify API Key is Valid

```bash
cd agents && uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')

from langchain_openai import ChatOpenAI

try:
    llm = ChatOpenAI(model='gpt-4o-mini')
    print('✅ ChatOpenAI initialized successfully')
    print(f'Model: {llm.model_name}')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

---

## Project-Specific Notes

### AutifyME .env Location
- **File:** `C:\Abhi\personal\AutifyME\.env` (project root)
- **From agents/:** Use `load_dotenv('../.env')`
- **Git Status:** `.env` is gitignored (never commit!)

### Required Environment Variables
```bash
# LLM Providers
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Database
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
DATABASE_URL=postgresql://...

# WhatsApp
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_WEBHOOK_VERIFY_TOKEN=...

# Observability
LANGSMITH_API_KEY=lsv2_pt_...
```

### Config Loading in Application Code

**Location:** `agents/src/autifyme_agents/core/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # Looks in CWD
        env_file_encoding="utf-8",
        extra="ignore"
    )

    OPENAI_API_KEY: str
    SUPABASE_URL: str
    # ... other fields
```

**Note:** When running the app normally (`uvicorn`, `streamlit`), Pydantic Settings auto-loads `.env` from CWD. For REPL tests, we need explicit `load_dotenv()`.

---

## Best Practices Summary

1. **Always use `uv run` (not `--no-project`)** for tests needing dependencies or env vars
2. **Explicitly load .env** with `load_dotenv('../.env')` from agents/ directory
3. **Add `prerelease = "allow"`** to `[tool.uv]` in pyproject.toml for v1 alpha packages
4. **Use FakeChatModel** for structural tests to avoid API costs
5. **Check env loading** with debug script when API key errors occur
6. **Never commit .env** - use `.env.example` for documentation

---

## Quick Reference Commands

```bash
# Library inspection (no env needed)
cd agents && uv run python -c "import X; print(dir(X))"

# With API keys
cd agents && uv run python -c "
from dotenv import load_dotenv; load_dotenv('../.env')
# ... your code
"

# Debug env loading
cd agents && uv run python -c "
from dotenv import load_dotenv
load_dotenv('../.env')
import os
print('OPENAI_API_KEY:', 'Set' if os.getenv('OPENAI_API_KEY') else 'Not set')
"
```

---

**Last Updated:** 2025-10-07
**Maintainer:** AutifyME Team
