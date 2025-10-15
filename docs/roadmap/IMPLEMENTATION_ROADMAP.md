# Implementation Roadmap (LangChain v1 Stack)

**Last Updated:** 2025-10-07 (Post Architectural Review)
**Stack Version:** LangChain `1.0.0a10`, LangGraph `1.0.0a4`, DeepAgents `0.0.11rc1`

This roadmap captures concrete engineering work prioritized by severity. It follows from the comprehensive architectural review and aligns with available features in our installed stack.

---

## 🔴 CRITICAL (P0) - Production Blockers

These issues prevent deployment and must be resolved before any production rollout.

### 1. Fix Checkpointer Resource Leak in Project Manager
**File:** `agents/src/autifyme_agents/workflows/project_manager.py:112-114`
**Severity:** P0 - Resource leak, blocks PM invocation

**Issue:**
```python
if checkpointer is None:
    with get_checkpointer() as saver:
        checkpointer = saver
# ← Context exits here, checkpointer is now CLOSED but used later
```

**Fix:**
```python
# Option 1: Remove context manager (caller manages lifecycle)
if checkpointer is None:
    checkpointer = get_checkpointer()

# Option 2: Keep at call site (already done correctly in whatsapp_cataloging_runner)
```

**Estimated Effort:** 30 minutes
**Owner:** TBD
**Blocks:** Project Manager workflows

---

### 2. Add ToolException Error Handling to Cataloging Tools
**File:** `agents/src/autifyme_agents/tools/cataloging_tools.py:52-94`
**Severity:** P0 - Breaks LangChain v1 error handling contract

**Issue:** `create_cataloging_specialist_tool` always returns `success=True`, preventing LLM self-healing.

**Current Code (Line 82):**
```python
product: Product = specialist.invoke(payload, config=config)

return CatalogingResult(
    stage="draft",
    success=True,  # ← Always True! No error handling
    ...
)
```

**Fix:**
```python
from langchain_core.tools import ToolException

try:
    product: Product = specialist.invoke(payload, config=config)
    return CatalogingResult(
        stage="draft",
        success=True,
        product_id=product.id,
        product_name=product.name,
        message="Draft product ready for approval",
        data={"draft": product.model_dump()},
    )
except Exception as exc:
    raise ToolException(
        f"Cataloging specialist failed: {str(exc)}",
    ) from exc
```

**Estimated Effort:** 1 hour
**Owner:** TBD
**Related:** Aligns with `storage_tools.py` error handling pattern

---

### 3. Implement Pytest Test Framework
**Directory:** `tests/` (to be created)
**Severity:** P0 - No CI/CD, no regression detection

**Status:** `pyproject.toml` already has pytest dependencies ✅, but no test suite exists.

**Tasks:**
1. Create directory structure:
   ```
   tests/
   ├── __init__.py
   ├── conftest.py          # Shared fixtures
   ├── unit/
   │   ├── test_storage_tools.py
   │   ├── test_cataloging_tools.py
   │   ├── test_specialists.py
   │   └── test_middleware.py
   ├── integration/
   │   ├── test_cataloging_department.py
   │   └── test_project_manager.py
   └── e2e/
       └── test_whatsapp_workflow.py
   ```

2. Create fixtures (`conftest.py`):
   ```python
   import pytest
   from autifyme_agents.schemas.models import CompanyProfile
   from autifyme_agents.core.ports import StorageInterface

   @pytest.fixture
   def mock_company_profile():
       return CompanyProfile(
           id="test-company",
           name="Test Co",
           brand_voice="Professional and friendly",
           target_audience="Small businesses",
       )

   @pytest.fixture
   def mock_storage(mock_company_profile):
       class MockStorage(StorageInterface):
           def get_company_profile(self):
               return mock_company_profile
           # ... implement other methods
       return MockStorage()
   ```

3. Write initial unit tests (start with tools):
   ```python
   # tests/unit/test_storage_tools.py
   import pytest
   from autifyme_agents.tools import create_save_product_tool
   from autifyme_agents.core.exceptions import ConfigurationError

   def test_save_product_requires_storage():
       tool = create_save_product_tool(storage=None)
       with pytest.raises(ConfigurationError, match="Storage client not provided"):
           tool.invoke({"name": "Test", "description": "Test", "price": 10.0})

   def test_save_product_success(mock_storage):
       tool = create_save_product_tool(storage=mock_storage)
       result = tool.invoke({
           "name": "Test Product",
           "description": "A test",
           "price": 99.99,
           "sizes": ["M", "L"],
       })
       assert result.success is True
       assert result.stage == "saved"
   ```

4. Configure pytest (`agents/pytest.ini`):
   ```ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   addopts =
       -v
       --strict-markers
       --cov=autifyme_agents
       --cov-report=term-missing
       --cov-report=html
   asyncio_mode = auto
   ```

**Estimated Effort:** 2-3 days (setup + initial coverage)
**Owner:** TBD
**Acceptance Criteria:**
- [ ] Directory structure created
- [ ] `conftest.py` with shared fixtures
- [ ] 80%+ coverage on tools layer
- [ ] 60%+ coverage on specialists
- [ ] CI/CD integration documented

---

## 🟠 HIGH SEVERITY (P1) - Architectural Integrity

These issues compromise architectural quality and must be addressed before scaling.

### 4. Remove Image Path Injection from Prompts
**File:** `agents/src/autifyme_agents/workflows/whatsapp_cataloging_runner.py:512-513`
**Severity:** P1 - Security risk, brittle parsing

**Issue:** Local file paths embedded in LLM prompts create path traversal risk and rely on LLM text parsing.

**Current Code:**
```python
content = f"{text}\n\n[An image was provided - analyze it using the image_analysis_specialist tool with path: {image_path}]"
```

**Fix:** Pass via structured metadata instead of natural language:
```python
def _build_project_manager_payload(self, text: str, image_path: Path | None) -> dict[str, Any]:
    messages = []

    if image_path and image_path.exists():
        # Store path in metadata, instruct PM to use it
        messages.append(HumanMessage(
            content=text or "Analyze the provided product image.",
            additional_kwargs={
                "image_metadata": {
                    "path": str(image_path),
                    "type": "product_photo",
                }
            }
        ))
    elif text:
        messages.append(HumanMessage(content=text))

    return {"messages": messages}
```

Update PM prompt to check `additional_kwargs.image_metadata` and extract path deterministically.

**Estimated Effort:** 2 hours
**Owner:** TBD
**Security Impact:** Prevents path traversal attacks

---

### 5. Apply Middleware Universally
**Files:**
- `agents/src/autifyme_agents/core/middleware.py` (defines but unused)
- `agents/src/autifyme_agents/departments/cataloging_department.py`
- `agents/src/autifyme_agents/tools/cataloging_tools.py`

**Severity:** P1 - Incomplete architecture implementation

**Issue:** `langsmith_tracing_middleware` defined but never applied. Missing prompt caching and summarization middleware.

**Current State:**
- ✅ Company context injection (implemented)
- ❌ LangSmith tracing enrichment (defined but unused)
- ❌ Prompt caching (available in v1, not used)
- ❌ Summarization (for long conversations, per AGENTS_DESIGN.md § 8.4)

**Tasks:**

1. **Apply LangSmith Tracing:**
   ```python
   # departments/cataloging_department.py
   from autifyme_agents.core.middleware import langsmith_tracing_middleware

   @tool("cataloging_specialist")
   @langsmith_tracing_middleware("cataloging")  # ← Add
   @company_context
   def cataloging_tool(...):
       ...
   ```

2. **Add Prompt Caching Middleware:**
   ```python
   # core/middleware.py
   from langchain.agents.middleware import AnthropicPromptCachingMiddleware

   def create_prompt_caching_middleware():
       return AnthropicPromptCachingMiddleware(
           cache_ttl=300,  # 5 minutes
           fallback_on_error=True,
       )
   ```

3. **Add Summarization Middleware (for long conversations):**
   ```python
   # core/middleware.py
   from langchain.agents.middleware import SummarizationMiddleware

   def create_summarization_middleware():
       return SummarizationMiddleware(
           max_tokens=4000,  # Trigger summarization after 4k tokens
           messages_to_keep=5,  # Keep last 5 messages
       )
   ```

4. **Wire into Department:**
   ```python
   # departments/cataloging_department.py
   middleware = [hitl_middleware]
   if enable_prompt_caching:
       middleware.append(create_prompt_caching_middleware())
   if enable_summarization:
       middleware.append(create_summarization_middleware())

   agent_graph = create_agent(
       llm, tools, prompt=prompt,
       middleware=tuple(middleware),  # ← Apply all
       ...
   )
   ```

**Estimated Effort:** 1 day
**Owner:** TBD
**Benefits:** Cost reduction (caching), better observability (tracing), context management (summarization)

---

### 6. ✅ Clarify and Document Department-as-Tools Pattern
**Files:**
- `agents/src/autifyme_agents/workflows/project_manager.py:57-68`
- `agents/src/autifyme_agents/tools/registry.py`
- `docs/architecture/AGENTS_DESIGN.md` (✅ **DOCUMENTED**)

**Severity:** P1 - Documentation and code alignment

**Architectural Decision (Confirmed):**
- ✅ **Project Manager ONLY** uses DeepAgents (`create_deep_agent`)
- ✅ **Departments** use standard LangChain agents (`create_agent`)
- ✅ **Specialists** use simple chains (`RunnableLambda` + `with_structured_output`)
- ✅ **Departments are exposed to PM as tools**, not DeepAgents sub-agents

**Current Implementation Status:**
The existing code in `project_manager.py:62-68` that passes tool names is **partially correct** but needs refinement:

```python
# Current (project_manager.py:62-68) - exposes tools, not department agents
return [
    {
        "name": "cataloging_department",
        "description": "Manages product ingestion...",
        "prompt": cataloging_prompt,
        "tools": tools_registry.get_cataloging_tool_names(),  # ← Tool names only
    }
]
```

**Correct Pattern (per AGENTS_DESIGN.md § 3):**
Departments should be invoked as **tools that wrap department agents**:

```python
# tools/registry.py - add department tool factory
def create_cataloging_department_tool(storage: StorageInterface, checkpointer: BaseCheckpointSaver):
    """Create a tool that invokes the cataloging department agent."""

    @tool("cataloging_department")
    def cataloging_department(
        user_message: str,
        image_url: str | None = None,
        *,
        company_profile,
        config=None,
    ) -> CatalogingResult:
        """Process product cataloging requests with image analysis and HITL approval."""

        # Create department agent (standard LangChain agent, NOT DeepAgent)
        dept_agent = create_cataloging_department(
            storage=storage,
            checkpointer=checkpointer,
            enable_hitl=True,
        )

        # Build payload
        messages = [HumanMessage(content=user_message)]
        if image_url:
            messages[0].additional_kwargs = {"image_url": image_url}

        # Invoke department agent
        result = dept_agent.invoke({"messages": messages}, config=config)

        # Extract structured result from department response
        return extract_cataloging_result(result)

    return cataloging_department
```

Then in PM:
```python
# project_manager.py - pass tool objects, not names
cataloging_dept_tool = create_cataloging_department_tool(storage, checkpointer)

project_manager = create_deep_agent(
    tools=[cataloging_dept_tool, ...],  # ← Department as tool
    instructions=instructions,
    model=llm,
    checkpointer=checkpointer,
)
```

**Why This Pattern:**
1. **PM complexity stays isolated**: Only PM uses DeepAgents' advanced features
2. **Departments stay simple**: Standard `create_agent` is stable and well-documented
3. **Clean delegation**: PM → department via tool calls (standard LangChain pattern)
4. **Type safety**: Tool signature enforces department input/output contracts
5. **Testable**: Can mock department tools for PM unit tests

**Tasks:**
1. ✅ Document pattern in `AGENTS_DESIGN.md` (DONE)
2. Create `create_cataloging_department_tool()` in `tools/registry.py`
3. Update PM to use department tool objects instead of flat tool names
4. Add unit tests for department-as-tool pattern

**Estimated Effort:** 3-4 hours
**Owner:** TBD
**Benefits:** Clear separation of concerns, aligns code with documented architecture

---

### 7. Standardize Cataloging Specialist Return Type
**Files:**
- `agents/src/autifyme_agents/specialists/cataloging_specialist.py:54`
- `agents/src/autifyme_agents/departments/cataloging_department.py:78-92`

**Severity:** P1 - Type contract inconsistency

**Issue:** Specialist returns `Product`, department manually wraps into `CatalogingResult`. This creates confusion about who owns result structuring.

**Current Flow:**
```python
# Specialist returns Product
structured_llm = llm.with_structured_output(Product)  # cataloging_specialist.py:51

# Department wraps manually
product: Product = cataloging_tool(...)  # cataloging_department.py:92
# Then manually constructs CatalogingResult (lines 84-91)
```

**Decision:**
- **Option 1 (Current - Recommended):** Specialists return domain models, departments wrap.
  - **Pro:** Specialists stay reusable across departments
  - **Con:** Requires documentation

- **Option 2:** Specialists return department-specific outputs.
  - **Pro:** Type safety end-to-end
  - **Con:** Reduces specialist reusability

**Action:** Document the pattern in `docs/architecture/AGENTS_DESIGN.md` § 3.3:

```markdown
### Specialist Output Convention

**Rule:** Specialists return pure domain models (`Product`, `ImageAnalysisResult`).
Department Heads wrap specialist outputs into department-specific result schemas
(`CatalogingResult`, `MarketingResult`) for Project Manager consumption.

**Rationale:** Maximizes specialist reusability. A `cataloging_specialist` returning
`Product` can be used by both Cataloging and Marketing departments, each wrapping
the output differently.
```

**Estimated Effort:** 1 hour (documentation only)
**Owner:** TBD
**Impact:** Clarifies contract, prevents future confusion

---

## 🟡 MEDIUM SEVERITY (P2) - Technical Debt

Address these to ensure long-term maintainability and production readiness.

### 8. Persist Idempotency Cache to Database
**File:** `agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py:34`
**Severity:** P2 - Data loss on restart

**Issue:** In-memory `_processed_messages` loses state on server restart. WhatsApp retries webhooks for 24 hours.

**Current:**
```python
_processed_messages: OrderedDict[str, bool] = OrderedDict()  # ← In-memory only
```

**Fix:**

1. **Create Supabase table:**
   ```sql
   CREATE TABLE processed_webhook_messages (
       message_id TEXT PRIMARY KEY,
       processed_at TIMESTAMP DEFAULT NOW(),
       expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '24 hours')
   );
   CREATE INDEX idx_expires_at ON processed_webhook_messages(expires_at);

   -- Auto-cleanup expired entries
   CREATE OR REPLACE FUNCTION cleanup_expired_webhook_messages()
   RETURNS void AS $$
   BEGIN
       DELETE FROM processed_webhook_messages WHERE expires_at < NOW();
   END;
   $$ LANGUAGE plpgsql;
   ```

2. **Add method to StorageInterface:**
   ```python
   # core/ports.py
   @abstractmethod
   def is_webhook_message_processed(self, message_id: str) -> bool:
       pass

   @abstractmethod
   def mark_webhook_message_processed(self, message_id: str) -> None:
       pass
   ```

3. **Implement in SupabaseStorageClient:**
   ```python
   # integrations/storage/supabase_client.py
   def is_webhook_message_processed(self, message_id: str) -> bool:
       client = self._ensure_client()
       now = datetime.now(timezone.utc).isoformat()
       response = (
           client.table("processed_webhook_messages")
           .select("message_id")
           .eq("message_id", message_id)
           .gt("expires_at", now)
           .execute()
       )
       return bool(response.data)

   def mark_webhook_message_processed(self, message_id: str) -> None:
       client = self._ensure_client()
       expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
       client.table("processed_webhook_messages").insert({
           "message_id": message_id,
           "expires_at": expires_at.isoformat(),
       }).execute()
   ```

4. **Update webhook:**
   ```python
   # entrypoints/whatsapp_webhook.py
   if storage_adapter.is_webhook_message_processed(message_id):
       logger.info("Skipping duplicate message", extra={"message_id": message_id})
       continue

   # Process message...

   storage_adapter.mark_webhook_message_processed(message_id)
   ```

**Estimated Effort:** 3 hours
**Owner:** TBD
**Benefits:** Restart-safe idempotency, auto-cleanup

---

### 9. Implement Prompt Versioning with LangSmith Hub
**Directory:** `tests/scripts/` (create `sync_prompts.py`)
**Severity:** P2 - Slows experimentation velocity

**Issue:** AGENTS_DESIGN.md § 9 specifies LangSmith Hub integration, but no sync tooling exists.

**Create:**
```python
# tests/scripts/sync_prompts.py
"""Sync local prompt files with LangSmith Hub for A/B testing and versioning."""

import argparse
from pathlib import Path
from langsmith import Client

PROMPTS_DIR = Path(__file__).parent.parent / "src" / "autifyme_agents" / "prompts"

def push_prompts_to_hub(hub_prefix: str = "autifyme"):
    """Push all local .prompt files to LangSmith Hub."""
    client = Client()

    for prompt_file in PROMPTS_DIR.rglob("*.prompt"):
        relative_path = prompt_file.relative_to(PROMPTS_DIR)
        prompt_name = f"{hub_prefix}/{relative_path.with_suffix('').as_posix()}"

        print(f"Pushing {prompt_file.name} → {prompt_name}")
        client.push_prompt(
            prompt_name=prompt_name,
            object=prompt_file.read_text(encoding="utf-8"),
            is_public=False,
        )

    print(f"✓ Pushed {len(list(PROMPTS_DIR.rglob('*.prompt')))} prompts to LangSmith Hub")

def pull_prompt_from_hub(prompt_name: str, output_path: Path):
    """Pull a specific prompt version from LangSmith Hub."""
    client = Client()

    prompt = client.pull_prompt(prompt_name)
    output_path.write_text(prompt, encoding="utf-8")
    print(f"✓ Pulled {prompt_name} → {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync prompts with LangSmith Hub")
    parser.add_argument("action", choices=["push", "pull"], help="Push or pull prompts")
    parser.add_argument("--name", help="Prompt name (for pull)")
    parser.add_argument("--output", help="Output file path (for pull)")

    args = parser.parse_args()

    if args.action == "push":
        push_prompts_to_hub()
    elif args.action == "pull":
        if not args.name or not args.output:
            parser.error("--name and --output required for pull")
        pull_prompt_from_hub(args.name, Path(args.output))
```

**Usage:**
```bash
# Push all local prompts to LangSmith Hub
uv run python tests/scripts/sync_prompts.py push

# Pull updated prompt from Hub after A/B testing
uv run python tests/scripts/sync_prompts.py pull \
    --name autifyme/departments/cataloging_department \
    --output agents/src/autifyme_agents/prompts/departments/cataloging_department.prompt
```

**Estimated Effort:** 2 hours
**Owner:** TBD
**Benefits:** Enable A/B testing, evaluation datasets, collaborative prompt iteration

---

### 10. Migrate to Structured JSON Logging
**All Files:** Logging calls throughout codebase
**Severity:** P2 - Observability gap

**Issue:** String interpolation logs are hard to parse/query. Most calls already use `extra={}`, so halfway there.

**Good (already doing):**
```python
# whatsapp_cataloging_runner.py:129
logger.info(
    "Skipping department invocation for low-intent message",
    extra={"sender": sender, "text": normalized_text, "thread_id": thread_id},
)
```

**Bad (still some):**
```python
logger.info(f"Processing message from {sender}")  # ← String interpolation
```

**Fix:**

1. **Install JSON logger:**
   ```bash
   uv pip install python-json-logger
   ```

2. **Configure logging (`core/logging_config.py`):**
   ```python
   import logging.config
   from pythonjsonlogger import jsonlogger

   LOGGING_CONFIG = {
       "version": 1,
       "disable_existing_loggers": False,
       "formatters": {
           "json": {
               "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
               "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
           },
           "console": {
               "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
           },
       },
       "handlers": {
           "console": {
               "class": "logging.StreamHandler",
               "formatter": "console" if os.getenv("ENV") == "development" else "json",
               "stream": "ext://sys.stdout",
           },
       },
       "root": {
           "level": "INFO",
           "handlers": ["console"],
       },
   }

   def configure_logging():
       logging.config.dictConfig(LOGGING_CONFIG)
   ```

3. **Apply in entrypoints:**
   ```python
   # entrypoints/whatsapp_webhook.py
   from autifyme_agents.core.logging_config import configure_logging

   configure_logging()
   ```

**Estimated Effort:** 3 hours (config + audit existing logs)
**Owner:** TBD
**Benefits:** Queryable logs, better production debugging

---

### 11. Add Database Migration Tooling (Alembic)
**Directory:** `agents/migrations/` (to be created)
**Severity:** P2 - Schema evolution friction

**Issue:** No migration tooling. Schema changes require manual SQL.

**Setup:**

1. **Install Alembic:**
   ```bash
   cd agents
   uv pip install alembic
   alembic init migrations
   ```

2. **Configure (`agents/alembic.ini`):**
   ```ini
   [alembic]
   script_location = migrations
   sqlalchemy.url = postgresql://user:pass@host:5432/dbname
   # Or read from env:
   # sqlalchemy.url = driver://user:pass@localhost/dbname?charset=utf8
   ```

3. **Create initial migration:**
   ```bash
   alembic revision -m "Add pending_approvals table"
   ```

4. **Write migration (`migrations/versions/xxxx_add_pending_approvals.py`):**
   ```python
   def upgrade():
       op.create_table(
           'pending_approvals',
           sa.Column('id', sa.String(), primary_key=True),
           sa.Column('thread_id', sa.String(), nullable=False),
           sa.Column('interrupt_id', sa.String(), nullable=False),
           sa.Column('checkpoint_id', sa.String(), nullable=False),
           sa.Column('tool_call', sa.JSON(), nullable=False),
           sa.Column('draft_summary', sa.Text(), nullable=False),
           sa.Column('ai_message', sa.JSON(), nullable=True),
           sa.Column('image_path', sa.String(), nullable=True),
           sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
           sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
       )
       op.create_index('idx_thread_id', 'pending_approvals', ['thread_id'])

   def downgrade():
       op.drop_table('pending_approvals')
   ```

5. **Apply:**
   ```bash
   alembic upgrade head
   ```

**Estimated Effort:** 2 hours (setup + initial migration)
**Owner:** TBD
**Benefits:** Safe schema evolution, rollback capability, team coordination

---

## 🟢 LOW SEVERITY (P3) - Polish & Improvements

Nice-to-haves that improve code quality but don't block progress.

### 12. Extract Magic Strings to Constants
**Files:** Throughout codebase
**Severity:** P3 - Code cleanliness

**Examples:**
- `"whatsapp:{phone_number}"` - Thread ID format
- `"default"` - Company ID
- `"cataloging"` - Workflow name
- `15` - Recursion limit

**Create:**
```python
# core/constants.py
"""Application-wide constants."""

# Thread ID formats
THREAD_ID_PREFIX = "whatsapp"

# Default identifiers
DEFAULT_COMPANY_ID = "default"

# Workflow names
WORKFLOW_CATALOGING = "cataloging"
WORKFLOW_MARKETING = "marketing"

# Agent limits
DEFAULT_RECURSION_LIMIT = 15
MAX_THREAD_LOCKS = 1000

# WhatsApp
MAX_PROCESSED_MESSAGES = 10_000
WHATSAPP_RETRY_WINDOW_HOURS = 24

# Approval expiry
APPROVAL_TTL_HOURS = 24
```

**Update usages:**
```python
# Before
thread_id = f"whatsapp:{sender}"

# After
from autifyme_agents.core.constants import THREAD_ID_PREFIX
thread_id = f"{THREAD_ID_PREFIX}:{sender}"
```

**Estimated Effort:** 1 hour
**Owner:** TBD
**Benefits:** Single source of truth, easier configuration changes

---

### 13. Add Rate Limiting to WhatsApp Client
**File:** `agents/src/autifyme_agents/integrations/communication/whatsapp_client.py:42`
**Severity:** P3 - Production hardening

**Issue:** No throttling. Meta's limit is ~80 messages/second per phone number.

**Add Retry Logic:**
```python
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import httpx

class WhatsAppClient:
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    def send_text(self, recipient: str, message: str, *, preview_url: bool = False):
        response = httpx.post(self._base_url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
        return response.json()
```

**Estimated Effort:** 30 minutes
**Owner:** TBD
**Benefits:** Handles transient WhatsApp API failures

---

## 📋 Original Roadmap (Retained for Context)

### 1. Middleware Adoption for Cataloging Workflow ✅ Partially Complete
- ✅ Add `HumanInTheLoopMiddleware` (implemented in cataloging_department.py)
- ⏳ **P1 Task #5:** Apply `SummarizationMiddleware` and `AnthropicPromptCachingMiddleware`

### 2. Tool & Dependency Injection Refactor 🔄 In Progress
- ⏳ **P0 Task #2:** Fix tool error handling (ToolException pattern)
- 🔜 Replace global storage with `InjectedState` (future enhancement)
- 🔜 Align with ToolNode patterns for `Command` objects

### 3. Checkpointing & Runtime Enhancements ⚠️ Blocker Found
- ⚠️ **P0 Task #1:** Fix checkpointer resource leak in project_manager.py
- ✅ PostgresSaver already implemented in whatsapp_cataloging_runner.py
- 🔜 Leverage `Runtime` context for metadata injection (future enhancement)

### 4. DeepAgents for Project Manager Only ✅ Architecture Clarified
- ✅ **Architecture Documented:** PM uses DeepAgents, departments use `create_agent` (AGENTS_DESIGN.md § 3)
- ⏳ **P1 Task #6:** Implement department-as-tools pattern (3-4 hrs)
- 🔜 Leverage planning/filesystem middleware in PM
- 🔜 Define PM-level structured outputs

### 5. Testing & Observability Upgrades 🔴 Critical Gap
- 🔴 **P0 Task #3:** Implement pytest framework (structure, fixtures, initial tests)
- ⏳ **P2 Task #10:** Structured JSON logging
- ✅ LangSmith traces already active
- 🔜 SSE/stream handling documentation

---

## 🎯 Execution Priority

### Sprint 1: Critical Blockers (Week 1)
**Goal:** Achieve deployment readiness

| Task | Priority | Effort | Owner | Status |
|------|----------|--------|-------|--------|
| Fix checkpointer resource leak | P0 | 30min | TBD | 🔴 |
| Add ToolException to cataloging_tools | P0 | 1hr | TBD | 🔴 |
| Implement pytest framework | P0 | 2-3 days | TBD | 🔴 |

**Acceptance Criteria:**
- [ ] Project Manager can be invoked without resource leaks
- [ ] All tools have proper error handling with ToolException
- [ ] Test suite with 60%+ coverage, CI/CD integration documented

---

### Sprint 2: Architectural Integrity (Week 2)
**Goal:** Solidify production architecture

| Task | Priority | Effort | Owner | Status |
|------|----------|--------|-------|--------|
| Remove image path from prompts | P1 | 2hr | TBD | 🟠 |
| Apply middleware universally | P1 | 1 day | TBD | 🟠 |
| Implement department-as-tools pattern | P1 | 3-4hr | TBD | 🟠 |
| Document specialist output convention | P1 | 1hr | TBD | 🟠 |

**Acceptance Criteria:**
- [ ] Image paths passed via metadata, not natural language
- [ ] LangSmith tracing, caching, summarization middleware active
- [x] DeepAgents strategy documented: PM only (AGENTS_DESIGN.md § 3)
- [ ] Department invoked as tool wrapping agent (not flat tool list)
- [ ] Specialist/department contract documented in AGENTS_DESIGN.md

---

### Sprint 3: Technical Debt (Week 3)
**Goal:** Production hardening

| Task | Priority | Effort | Owner | Status |
|------|----------|--------|-------|--------|
| Database-backed idempotency cache | P2 | 3hr | TBD | 🟡 |
| Prompt versioning with LangSmith Hub | P2 | 2hr | TBD | 🟡 |
| Structured JSON logging | P2 | 3hr | TBD | 🟡 |
| Alembic migration setup | P2 | 2hr | TBD | 🟡 |

**Acceptance Criteria:**
- [ ] Webhook idempotency survives restarts
- [ ] `scripts/sync_prompts.py` can push/pull from LangSmith Hub
- [ ] JSON logs in production, human-readable in development
- [ ] Schema migrations versioned with Alembic

---

### Sprint 4: Polish (Ongoing)
**Goal:** Code quality improvements

| Task | Priority | Effort | Owner | Status |
|------|----------|--------|-------|--------|
| Extract magic strings to constants | P3 | 1hr | TBD | 🟢 |
| Add rate limiting to WhatsApp client | P3 | 30min | TBD | 🟢 |

---

## 📊 Progress Tracking

**Current State:**
- Foundation: 65% complete (up from 40%)
- Production Readiness: Blocked by 3 P0 issues
- Architectural Grade: B+ (solid foundation, completion work needed)

**After Sprint 1 (P0):**
- Foundation: 85% complete
- Production Readiness: ✅ Deployable
- Grade: A-

**After Sprint 2 (P1):**
- Foundation: 95% complete
- Production Readiness: ✅ Production-hardened
- Grade: A

**After Sprint 3 (P2):**
- Foundation: 100% complete
- Production Readiness: ✅ Enterprise-grade
- Grade: A+

---

## 🔍 Next Actions

1. **Immediate:** Assign owners to P0 tasks
2. **This Week:** Complete Sprint 1 (critical blockers)
3. **Next Week:** Begin Sprint 2 (architectural integrity)
4. **Ongoing:** Write tests as you build new features (TDD approach)

---

**Last Updated:** 2025-10-07
**Review Cadence:** Weekly sprint planning
**Owner:** Architecture Team
