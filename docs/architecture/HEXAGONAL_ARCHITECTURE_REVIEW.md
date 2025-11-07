# HEXAGONAL ARCHITECTURE REVIEW: AutifyME Integration Layer

**Date:** 2025-11-07  
**Repository:** AutifyME  
**Current Branch:** claude/codebase-review  
**Scope:** Storage, Communication, LLM integrations and port abstractions

---

## EXECUTIVE SUMMARY

The hexagonal architecture implementation has **CRITICAL VIOLATIONS** that undermine the core design principle. Core modules are directly accessing private adapter methods and calling non-existent adapter-specific methods, creating tight coupling to Supabase specifics.

### Severity Assessment
- **Critical (Must Fix):** 3 blocker violations
- **High (Should Fix):** 2 design violations  
- **Medium (Consider):** 4 improvement opportunities
- **Low (Optional):** 3 cleanup items

---

## PART 1: PORT DEFINITION ANALYSIS

### StorageInterface (core/ports.py)

**Status:** WELL-DESIGNED PORT ✓

**Strengths:**
- Clean abstraction with 17 methods covering all storage needs
- Database-agnostic operation names (query_entities, insert_entity, etc.)
- No Supabase-specific details in signatures
- Comprehensive docstrings with clear contracts
- Includes lifecycle management (cleanup)
- Supports both sync (get_company_profile, save_product, check_and_mark_message_processed, save_workflow_outcome) and async (query_entities, insert_entity, etc.) operations

**Architecture Compliance:**
- Defines port contract correctly
- No implementation leakage (hypothetically clean)
- Clear separation of concerns
- Proper error handling expectations

**Issues Found:**
- **CRITICAL:** Method `execute_sql()` referenced in code but NOT defined in port (see Violation 1)
- Missing transaction documentation detail (interface defined but async context manager pattern not fully specified)

### Missing Port Methods

The StorageInterface port is missing explicit definitions for:
1. `execute_sql(query: str, params: list)` - Referenced in campaign_persistence_tools.py but missing from port
2. Async transaction context manager protocol documentation

---

## PART 2: ADAPTER IMPLEMENTATION ANALYSIS

### SupabaseStorageClient (integrations/storage/supabase_client.py)

**Status:** GOOD IMPLEMENTATION, POOR ISOLATION ✓/✗

**Strengths:**
- Properly implements StorageInterface contract
- Well-documented implementation
- Handles both sync and async clients
- Proper HTTP/2 configuration and event loop awareness
- Comprehensive error handling with StorageError wrapper
- Transaction support with rollback tracking
- Good logging and debugging support

**Architecture Violations:**

#### VIOLATION 1: Missing Port Method (CRITICAL)
**Location:** campaign_persistence_tools.py (lines 252, 274, 302, 322, 345, 369)

The code calls `storage.execute_sql()` which is:
- NOT defined in StorageInterface port
- Only available as adapter-specific implementation detail
- Used for raw SQL execution on campaigns table

```python
# VIOLATES HEXAGONAL ARCHITECTURE
campaign_result = storage.execute_sql(
    "INSERT INTO campaigns ({}) VALUES ({}) RETURNING id".format(...),
    list(campaign_data.values())
)
```

**Impact:** Core logic (campaign_persistence_tools) has tight coupling to adapter's SQL execution capability. Breaking the port contract - if Supabase were swapped for another database, this code would fail.

**Fix Required:** Add `execute_sql()` to StorageInterface port definition, OR refactor campaign persistence to use existing port methods (insert_entity + transaction).

---

#### VIOLATION 2: Direct Private Method Access (CRITICAL)
**Location:** product_search_tools.py (line 330)

The code calls `storage._ensure_client()` which is:
- Private method (underscore prefix indicates internal use)
- Adapter-specific (only exists in SupabaseStorageClient)
- Directly uses Supabase PostgREST client

```python
# VIOLATES HEXAGONAL ARCHITECTURE - accessing private adapter method
query = storage._ensure_client().table("product_families").select(
    "*,variant_axes(id,name,display_label,sort_order,...)"
)
```

**Impact:** Core business logic (product search) is tightly coupled to Supabase client details. The tool only works with Supabase; incompatible with any other storage implementation.

**Fix Required:** Add `query_advanced()` with relation support to StorageInterface, or use existing port method with normalized select syntax.

---

#### VIOLATION 3: Direct Private Method Access (CRITICAL)
**Location:** specialists/taxonomy_specialist.py (lines 131, 290)

Same pattern as Violation 2:

```python
# VIOLATES HEXAGONAL ARCHITECTURE
client = storage._ensure_client()
response = (
    client.table("categories")
    .select("id, name, slug, description, parent_id")
    .eq("is_active", True)
    .execute()
)
```

**Impact:** Specialist logic is hardcoded to Supabase API. Cannot work with PostgreSQL, DynamoDB, or cloud storage adapters.

**Fix Required:** Use existing port methods (query_entities or query_advanced) instead of direct client access.

---

### WhatsAppClient (integrations/communication/whatsapp_client.py)

**Status:** ACCEPTABLE ADAPTER, NO PORT ✗

**Issues:**
- No AbstractCommunicationPort defined
- Direct implementation used throughout codebase
- Tight coupling to WhatsApp Cloud API specifics
- If WhatsApp API changes or alternative messaging provider added, code is fragile

**Recommendation:** Define CommunicationPort abstraction:

```python
class CommunicationPort(ABC):
    @abstractmethod
    async def send_message(self, recipient: str, message: str) -> str:
        """Send message, return message ID"""
        pass
    
    @abstractmethod
    async def send_typing_indicator(self, recipient: str) -> None:
        pass
```

---

### WhatsAppMediaClient (integrations/communication/whatsapp_media_client.py)

**Status:** ORPHANED ADAPTER, NO PORT ✗

**Issues:**
- No MediaPort abstraction
- Only WhatsApp implementation exists
- Imports Config directly (core.config)
- Platform-specific temp directory handling hardcoded

---

### LLM Integrations (core/llm_factory.py)

**Status:** FACTORY PATTERN GOOD, ADAPTER WRAPPER NEEDED

**Current Implementation:**
- `get_llm()` factory function supports multiple providers (OpenAI, Anthropic, Google)
- No abstract port definition
- Creates concrete LangChain model instances directly

**Issues:**
- Core code should depend on LLMPort abstraction, not concrete BaseChatModel
- StrictChatOpenAI is an adapter-specific wrapper only for OpenAI

**Recommendation:** Define:
```python
class LLMPort(ABC):
    """Abstract interface for language models"""
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass
```

Then factories return LLMPort implementations.

---

### Google Integrations (core/google_live_api.py, core/google_media_factory.py)

**Status:** PROVIDER-SPECIFIC, NO PORT ✗

**Issues:**
- GeminiLiveSession and VeoVideoGenerator are specialized implementations
- No abstraction layer (port)
- Direct Google genai imports
- Cannot swap providers without changing core code

---

## PART 3: DEPENDENCY DIRECTION ANALYSIS

### Current State

```
CORRECT DIRECTION:
entrypoints/ -> get_storage() -> StorageInterface
tools/ ------> get_storage() -> StorageInterface  
workflows/ --> get_storage() -> StorageInterface

VIOLATION - REVERSE DEPENDENCY:
product_search_tools.py ------> storage._ensure_client() [ADAPTER]
taxonomy_specialist.py --------> storage._ensure_client() [ADAPTER]  
campaign_persistence_tools.py -> storage.execute_sql() [ADAPTER]
```

### Dependency Graph Issues

```
SHOULD BE:
[Core Logic] --depends on--> [Port] <--implements-- [Adapter]

CURRENTLY:
[Core Logic] --directly uses--> [Adapter private methods]
[Core Logic] --calls--> [adapter-only methods]
```

### Core Modules Affected

| Module | Dependency | Violation |
|--------|-----------|-----------|
| product_search_tools.py | _ensure_client() | Direct private method access |
| taxonomy_specialist.py | _ensure_client() | Direct private method access |
| campaign_persistence_tools.py | execute_sql() | Non-existent port method |
| communication_tools.py | WhatsAppClient() | Direct adapter instantiation |
| tools/storage_tools.py | References adapter type in docstring | Leakage in documentation |

---

## PART 4: ADAPTER LEAKAGE ANALYSIS

### Supabase-Specific Leakage

#### Active Leakage Points:

1. **Supabase PostgREST API**
   - Located: product_search_tools.py:330
   - Code: `storage._ensure_client().table().select().eq()`
   - Impact: Locks implementation to Supabase PostgREST
   - Severity: CRITICAL

2. **Supabase RPC Functions**
   - Located: supabase_client.py:369 (check_and_mark_message_processed)
   - Uses: `.rpc("check_and_mark_processed", {...})`
   - Port Support: None (not in StorageInterface)
   - Impact: Database-specific stored procedures in adapter only

3. **Raw SQL Execution**
   - Located: campaign_persistence_tools.py (multiple lines)
   - Code: `storage.execute_sql()`
   - Port Support: Not defined
   - Severity: CRITICAL

4. **Private Client Access**
   - Located: taxonomy_specialist.py:131, 290
   - Code: `storage._ensure_client().table().select()`
   - Impact: Supabase client API exposed to business logic
   - Severity: CRITICAL

#### Potential Leakage (Private Implementation Details):

```python
# From supabase_client.py - These should not be accessed externally:
_client: Client | None
_async_client: AsyncClient | None
_async_client_loop: asyncio.AbstractEventLoop | None
_current_transaction: SupabaseTransaction | None
_ensure_client() -> Client  # PRIVATE - but called from product_search_tools
```

### Communication Leakage

1. **Direct WhatsAppClient Usage**
   - Location: communication_tools.py:8, tools/storage_tools.py
   - Creates tight coupling to WhatsApp provider
   - No abstraction allows provider swap

2. **WhatsAppMediaClient Configuration**
   - Hardcoded temp directory for media downloads
   - Platform-specific path handling in adapter
   - Leaks platform assumptions

### Provider-Specific Integrations

1. **Google APIs** (google_live_api.py, google_media_factory.py)
   - No ports defined
   - Direct genai package imports in core/
   - Cannot be extended to other voice/video providers

2. **LLM Providers** (llm_factory.py)
   - Factory creates concrete models (ChatOpenAI, ChatAnthropic, etc.)
   - No intermediate abstraction
   - Core code imports from langchain_openai, langchain_anthropic, etc.

---

## PART 5: FACTORY PATTERN ASSESSMENT

### Storage Factory (integrations/storage/storage_factory.py)

**Status:** CORRECT PATTERN ✓

```python
def get_storage() -> StorageInterface:  # Returns port, not adapter
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = SupabaseStorageClient()  # Adapter created internally
    return _storage_instance
```

**Strengths:**
- Singleton pattern with cleanup handler
- Returns StorageInterface (port) not SupabaseStorageClient
- Isolates adapter instantiation
- Proper atexit cleanup registration

**Improvement:** Could support adapter swapping via environment variable:

```python
def get_storage() -> StorageInterface:
    adapter_type = settings.STORAGE_ADAPTER  # "supabase", "postgres", "dynamodb"
    if adapter_type == "postgres":
        return PostgresStorageClient()
    elif adapter_type == "supabase":
        return SupabaseStorageClient()
```

---

### LLM Factory (core/llm_factory.py)

**Status:** GOOD PATTERN, MISSING PORT ABSTRACTION ✗

**Strengths:**
- Centralized LLM instantiation
- Multi-provider support (OpenAI, Anthropic, Google)
- Comprehensive parameter handling
- Prompt caching documentation

**Issues:**
- Returns `BaseChatModel` (LangChain type) not application-level port
- Core code depends on LangChain types, not application abstraction
- Provider-specific parameters leak into core code

**Recommendation:** Add LLMPort wrapper:

```python
class LLMPort(ABC):
    @abstractmethod
    async def invoke(self, prompt: str) -> str: pass

class LLMPortImpl(LLMPort):
    def __init__(self, model: BaseChatModel):
        self._model = model
    
    async def invoke(self, prompt: str) -> str:
        # Delegate to underlying model
```

---

### Checkpointer Factories (postgres_saver_factory.py, postgres_store_factory.py)

**Status:** VENDOR-LOCKED, NO PORT ✗

**Issues:**
- `get_checkpointer()` returns LangGraph PostgresSaver directly
- `get_store()` returns LangGraph PostgresStore directly
- No abstraction for checkpoint/store backends
- Only PostgreSQL supported
- Hard-coded dependency on LangGraph internals

**Recommendation:** Create CheckpointPort and StorePort abstractions for future multi-backend support.

---

## PART 6: CODE ORGANIZATION & BLOAT

### Storage Integration Structure

```
integrations/storage/
├── supabase_client.py (49.5 KB) - Core adapter ✓
├── storage_factory.py (1.9 KB) - Factory ✓
├── postgres_saver_factory.py (3.8 KB) - LangGraph wrapper ✗
├── postgres_store_factory.py (1.1 KB) - LangGraph wrapper ✗
└── __init__.py (277 B) - Exports factory ✓
```

**Issues:**
- postgres_*_factory files are not "storage adapters" (violates naming)
- They wrap LangGraph components, not alternative storage providers
- Should be in core/ or workflows/ not integrations/storage/

### Communication Integration Structure

```
integrations/communication/
├── whatsapp_client.py (3.3 KB) ✓
├── whatsapp_media_client.py (5.4 KB) ✓
└── __init__.py (195 B) ✓
```

**Status:** Minimal and focused. Missing: port abstraction.

### LLM Integration Structure

```
integrations/llm/
└── __init__.py (empty)
```

**Status:** Empty placeholder. LLM factory in core/llm_factory.py instead.

**Recommendation:** Consolidate:
```
integrations/llm/
├── llm_factory.py (factory from core/)
├── google_live_api.py (from core/)
├── google_media_factory.py (from core/)
└── strict_openai_model.py (from core/)
```

### MCP Integration Structure

```
integrations/mcp/
└── __init__.py (empty)
```

**Status:** Unused placeholder for future Model Context Protocol support.

---

## PART 7: VIOLATIONS SUMMARY TABLE

| ID | Violation | Severity | Location | Impact | Fix Effort |
|----|-----------|----|----------|--------|-----------|
| V1 | Missing port method `execute_sql()` | CRITICAL | campaign_persistence_tools.py | Cannot swap database adapters | High |
| V2 | Direct `_ensure_client()` access | CRITICAL | product_search_tools.py:330 | Adapter-specific API in business logic | Medium |
| V3 | Direct `_ensure_client()` access | CRITICAL | taxonomy_specialist.py:131,290 | Same as V2 | Medium |
| V4 | No CommunicationPort abstraction | HIGH | communication_tools.py | WhatsApp-locked | Medium |
| V5 | No LLMPort abstraction | HIGH | core/llm_factory.py | Depends on LangChain types | Medium |
| V6 | LangGraph hardcoded as storage | MEDIUM | postgres_*_factory.py | No checkpoint backend swapping | High |
| V7 | Direct adapter in docstring | LOW | campaign_persistence_tools.py | Documentation leakage | Low |
| V8 | Empty integration directories | LOW | integrations/llm/, integrations/mcp/ | Code organization | Low |
| V9 | StrictChatOpenAI in core/ | LOW | core/strict_openai_model.py | Provider-specific wrapper in core | Low |

---

## PART 8: REFACTORING RECOMMENDATIONS

### IMMEDIATE (Fix Critical Violations)

#### Recommendation 1: Add execute_sql() to StorageInterface

**Option A: Add Method to Port (Recommended)**
```python
# In core/ports.py
@abstractmethod
async def execute_sql(
    self,
    query: str,
    params: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute raw SQL query (database-specific).
    
    Use only for complex operations not covered by CRUD methods.
    Implementations should support parameterized queries for security.
    """
    pass
```

**Option B: Refactor campaign_persistence_tools**
Replace 6 `execute_sql()` calls with atomic transaction + insert_entities:
```python
async with storage.transaction():
    campaign = await storage.insert_entity("campaigns", campaign_data)
    campaign_id = campaign["id"]
    await storage.insert_entities("campaign_products", campaign_products)
    await storage.insert_entities("campaign_assets", campaign_assets)
    # etc.
```

**Recommendation:** Option A (add method) - preserves performance for complex transactions.

---

#### Recommendation 2: Fix Direct Adapter Access (product_search_tools.py)

**Current (VIOLATES):**
```python
query = storage._ensure_client().table("product_families").select(
    "*,variant_axes(id,...,variant_values(...))"
)
```

**Fix:**
```python
# Extend StorageInterface with relation support
families = await storage.query_advanced(
    "product_families",
    filters={"is_active": True},
    relations=["variant_axes(*)", "variant_values(*)"],
    limit=50
)
```

**Effort:** Medium - extend query_advanced, refactor search logic.

---

#### Recommendation 3: Fix Direct Adapter Access (taxonomy_specialist.py)

**Current (VIOLATES):**
```python
client = storage._ensure_client()
response = client.table("categories").select(...).eq(...).execute()
```

**Fix:**
```python
categories = await storage.query_entities(
    "categories",
    filters={"is_active": True},
    columns=["id", "name", "slug", "description", "parent_id"]
)
```

**Effort:** Low - straightforward refactor to existing port method.

---

### SHORT-TERM (Fix High-Priority Violations)

#### Recommendation 4: Define CommunicationPort

```python
# core/ports.py
class CommunicationPort(ABC):
    """Abstract port for outbound communication channels."""
    
    @abstractmethod
    async def send_text(
        self,
        recipient: str,
        message: str,
        preview_url: bool = False
    ) -> dict[str, Any]:
        """Send text message, return response with message_id."""
        pass
    
    @abstractmethod
    async def send_typing_indicator(self, recipient: str) -> None:
        """Show typing indicator (if supported by channel)."""
        pass

# integrations/communication/factory.py
def get_communication() -> CommunicationPort:
    global _instance
    if _instance is None:
        _instance = WhatsAppClient()
    return _instance
```

**Effort:** Medium - affects communication_tools.py, whatsapp/adapter.py.

---

#### Recommendation 5: Define LLMPort

```python
# core/ports.py
class LLMPort(ABC):
    """Abstract port for language models."""
    
    @abstractmethod
    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[BaseTool] | None = None
    ) -> AIMessage:
        pass

# core/llm_factory.py returns LLMPort implementations
def get_llm(...) -> LLMPort:
    base_model = ChatGoogleGenerativeAI(...)  # or ChatOpenAI, etc.
    return LLMPortImpl(base_model)
```

**Effort:** High - affects all specialist/agent code that uses LLMs.

---

### MEDIUM-TERM (Structural Improvements)

#### Recommendation 6: Define CheckpointPort

Decouple from LangGraph PostgresCheckpointer specifics:

```python
class CheckpointPort(ABC):
    @abstractmethod
    async def put(self, checkpoint: dict) -> None: pass
    
    @abstractmethod
    async def get(self, checkpoint_id: str) -> dict: pass

# Support multiple backends: Postgres, Redis, S3, etc.
```

**Effort:** High - requires LangGraph integration refactor.

---

#### Recommendation 7: Reorganize Integration Files

```
BEFORE:
├── core/
│   ├── llm_factory.py
│   ├── google_live_api.py
│   └── google_media_factory.py
├── integrations/
│   ├── llm/ (empty)
│   ├── mcp/ (empty)
│   └── storage/

AFTER:
├── core/
│   ├── ports.py
│   └── middleware.py
├── integrations/
│   ├── llm/
│   │   ├── llm_factory.py
│   │   ├── google_live_api.py
│   │   └── strict_openai_model.py
│   ├── communication/
│   ├── storage/
│   └── mcp/ (future)
```

**Effort:** Low-Medium - file moves, import updates.

---

#### Recommendation 8: Provider-Specific Wrappers

Move provider adapters behind ports:

```
integrations/llm/
├── __init__.py
├── ports.py (LLMPort)
├── openai/
│   └── adapter.py
├── anthropic/
│   └── adapter.py
└── google/
    ├── adapter.py
    ├── live_api.py
    └── media_factory.py
```

**Effort:** Medium - reorganization + port definitions.

---

## PART 9: TESTING IMPLICATIONS

### Current Test Gaps

1. **No Adapter Swappability Tests**
   - No tests verifying code works with non-Supabase storage
   - Cannot detect direct adapter access until runtime

2. **Port Contract Tests**
   - Should test all StorageInterface methods against multiple adapters
   - Currently only Supabase tested

3. **Dependency Injection Tests**
   - No tests mocking StorageInterface to verify port usage
   - Cannot catch _ensure_client() calls in tests

### Recommended Test Strategy

```python
# tests/fixtures/adapters.py
@pytest.fixture(params=["supabase", "postgres", "mock"])
def storage(request):
    """Test against multiple storage adapters."""
    if request.param == "supabase":
        return SupabaseStorageClient()
    elif request.param == "postgres":
        return PostgresStorageClient()
    else:
        return MockStorageAdapter()

# tests/test_product_search.py
def test_search_with_any_adapter(storage: StorageInterface):
    """Verify search works regardless of adapter."""
    # This test will fail if code uses storage._ensure_client()
```

---

## PART 10: AUDIT CHECKLIST

Use this checklist to verify hexagonal architecture compliance in future code:

```markdown
[ ] Port Definition
  [ ] Defined in core/ports.py as ABC
  [ ] No implementation details in signatures
  [ ] Database-agnostic method names
  [ ] Comprehensive docstrings

[ ] Adapter Implementation
  [ ] In integrations/ directory
  [ ] Inherits from port ABC
  [ ] All abstract methods implemented
  [ ] Only adapter accesses provider SDKs

[ ] Factory Pattern
  [ ] Returns port type, not adapter
  [ ] Adapter instantiation isolated in factory
  [ ] Singleton or request-scoped appropriately

[ ] Core Code Dependencies
  [ ] Imports ports only (from core.ports)
  [ ] Never imports adapters (from integrations)
  [ ] Never calls private methods (_ensure_client, etc.)
  [ ] Depends on StorageInterface, not SupabaseStorageClient

[ ] Testing
  [ ] Tests use mock port implementations
  [ ] No tests couple to adapter specifics
  [ ] Multi-adapter tests verify swappability
```

---

## PART 11: COMPLIANCE GAPS BY MODULE

### ✓ Compliant Modules

| Module | Pattern | Status |
|--------|---------|--------|
| entrypoints/whatsapp_webhook.py | Calls get_storage() | COMPLIANT |
| core/middleware.py | Uses StorageInterface | COMPLIANT |
| workflows/outcome_tracker.py | Uses StorageInterface methods | COMPLIANT |
| tools/universal_crud_tool.py | Uses port methods | COMPLIANT |
| core/storage_factory.py | Returns StorageInterface | COMPLIANT |

### ✗ Violating Modules

| Module | Violation | Status |
|--------|-----------|--------|
| tools/campaign_persistence_tools.py | Calls execute_sql() | VIOLATES (V1) |
| tools/product_search_tools.py | Calls _ensure_client() | VIOLATES (V2) |
| specialists/taxonomy_specialist.py | Calls _ensure_client() | VIOLATES (V3) |
| tools/communication_tools.py | Direct WhatsAppClient import | VIOLATES (V4) |
| core/llm_factory.py | Returns BaseChatModel | VIOLATES (V5) |
| integrations/storage/postgres_*_factory.py | LangGraph hardcoded | VIOLATES (V6) |

---

## PART 12: MIGRATION PLAN

### Phase 1: Fix Critical Violations (Week 1-2)

1. Add `execute_sql()` to StorageInterface (or refactor campaign persistence)
2. Replace `_ensure_client()` calls with port methods
3. Extract `_ensure_client()` calls in taxonomy_specialist.py

**Impact:** 3 files changed, 15 lines modified, 0 breaking changes

### Phase 2: Define Missing Ports (Week 2-3)

1. Create CommunicationPort abstraction
2. Create LLMPort abstraction
3. Update factories to return port types

**Impact:** 8 files changed, 200 lines added, migration guide needed

### Phase 3: Reorganize Integration Structure (Week 3-4)

1. Move llm_factory, google_* to integrations/llm/
2. Create provider-specific subdirectories
3. Update imports throughout codebase

**Impact:** 20+ files changed (mostly imports), 0 breaking changes

### Phase 4: Multi-Adapter Support (Week 4-6)

1. Implement PostgresStorageClient (alternative to Supabase)
2. Add DynamoDBStorageClient (cloud option)
3. Update factories to support adapter selection

**Impact:** 3 new adapter implementations, comprehensive testing

---

## CONCLUSION

The hexagonal architecture foundation is **solid at the port level** but **severely compromised at the adapter leakage level**. Three critical violations allow core business logic to access private adapter methods and call non-existent port methods, preventing true adapter swappability.

**Total Effort to Fix:**
- Critical violations: 20-30 hours
- Port abstractions: 30-40 hours
- Reorganization: 10-15 hours
- Testing/validation: 15-20 hours

**Recommended Priority:** Fix critical violations in Phase 1 immediately. Adapter swappability cannot be verified until these are resolved.

**Architectural Maturity:** Currently 6/10. Post-fixes: 8/10. Multi-adapter support: 9/10.
