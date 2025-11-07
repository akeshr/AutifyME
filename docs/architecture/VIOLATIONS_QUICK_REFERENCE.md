# QUICK REFERENCE: HEXAGONAL ARCHITECTURE VIOLATIONS

## Critical Violations (MUST FIX)

### VIOLATION 1: Missing Port Method `execute_sql()`
- **Severity:** CRITICAL
- **Files Affected:** 
  - `agents/src/autifyme_agents/tools/campaign_persistence_tools.py` (lines 252, 274, 302, 322, 345, 369)
- **Issue:** Calls `storage.execute_sql()` which is NOT in StorageInterface port
- **Fix Time:** 3-5 hours
- **Risk:** Cannot swap database adapters

```python
# CURRENT (VIOLATES)
campaign_result = storage.execute_sql(
    "INSERT INTO campaigns ({}) VALUES ({}) RETURNING id".format(...),
    list(campaign_data.values())
)

# FIX OPTION A: Add to port
# In core/ports.py add:
@abstractmethod
async def execute_sql(self, query: str, params: list[Any] | None = None) -> list[dict[str, Any]]: pass

# FIX OPTION B: Refactor to use transaction + insert_entity
# async with storage.transaction():
#     campaign = await storage.insert_entity("campaigns", campaign_data)
```

---

### VIOLATION 2: Direct Private Adapter Method Access
- **Severity:** CRITICAL
- **Files Affected:**
  - `agents/src/autifyme_agents/tools/product_search_tools.py` (line 330)
- **Issue:** Calls private method `storage._ensure_client()` - adapter specific
- **Fix Time:** 2-3 hours
- **Risk:** Product search only works with Supabase

```python
# CURRENT (VIOLATES)
query = storage._ensure_client().table("product_families").select(
    "*,variant_axes(id,name,display_label,sort_order,variant_values(...))"
)

# FIX: Use existing port method
families = await storage.query_advanced(
    "product_families",
    filters={"is_active": True},
    relations=["variant_axes(*)", "variant_values(*)"],
    limit=50
)
```

---

### VIOLATION 3: Direct Private Adapter Method Access
- **Severity:** CRITICAL
- **Files Affected:**
  - `agents/src/autifyme_agents/specialists/taxonomy_specialist.py` (lines 131, 290)
- **Issue:** Calls private method `storage._ensure_client()` - adapter specific
- **Fix Time:** 1-2 hours
- **Risk:** Taxonomy classification only works with Supabase

```python
# CURRENT (VIOLATES)
client = storage._ensure_client()
response = client.table("categories").select(...).eq(...).execute()

# FIX: Use existing port method
categories = await storage.query_entities(
    "categories",
    filters={"is_active": True},
    columns=["id", "name", "slug", "description", "parent_id"]
)
```

---

## High-Priority Violations (SHOULD FIX)

### VIOLATION 4: No CommunicationPort Abstraction
- **Severity:** HIGH
- **Files Affected:**
  - `agents/src/autifyme_agents/tools/communication_tools.py` (line 8)
  - `agents/src/autifyme_agents/integrations/communication/whatsapp_client.py`
- **Issue:** Direct WhatsAppClient import - no port abstraction
- **Fix Time:** 4-6 hours
- **Risk:** WhatsApp-locked, cannot swap messaging providers

```python
# CURRENT (VIOLATES)
from autifyme_agents.integrations.communication.whatsapp_client import WhatsAppClient
messaging_client = client or WhatsAppClient()

# FIX: Add CommunicationPort to core/ports.py
class CommunicationPort(ABC):
    @abstractmethod
    async def send_text(self, recipient: str, message: str, preview_url: bool = False) -> dict[str, Any]: pass
    @abstractmethod
    async def send_typing_indicator(self, recipient: str) -> None: pass

# Create factory: integrations/communication/communication_factory.py
def get_communication() -> CommunicationPort:
    return WhatsAppClient()  # Adapter behind port
```

---

### VIOLATION 5: No LLMPort Abstraction
- **Severity:** HIGH
- **Files Affected:**
  - `agents/src/autifyme_agents/core/llm_factory.py` (all return statements)
- **Issue:** Returns concrete LangChain models (BaseChatModel), not port abstraction
- **Fix Time:** 8-12 hours (affects all specialist code)
- **Risk:** Code depends on LangChain types, cannot swap LLM frameworks

```python
# CURRENT (VIOLATES)
def get_llm(...) -> BaseChatModel:  # Returns LangChain type
    return ChatGoogleGenerativeAI(model=model, ...)

# FIX: Define LLMPort
class LLMPort(ABC):
    @abstractmethod
    async def invoke(self, messages: list[dict[str, str]], tools: list[BaseTool] | None = None) -> AIMessage: pass

# Wrapper
class LLMPortImpl(LLMPort):
    def __init__(self, model: BaseChatModel):
        self._model = model
    async def invoke(self, messages, tools=None) -> AIMessage:
        return self._model.invoke(...)

# Update factory
def get_llm(...) -> LLMPort:
    base_model = ChatGoogleGenerativeAI(...)
    return LLMPortImpl(base_model)
```

---

## Medium-Priority Issues

### VIOLATION 6: LangGraph Hard-Coded as Storage
- **Files:** postgres_saver_factory.py, postgres_store_factory.py
- **Issue:** No checkpoint/store port abstraction - only PostgreSQL supported
- **Fix Time:** 6-8 hours

### VIOLATION 7: Provider-Specific Code in core/
- **Files:** google_live_api.py, google_media_factory.py
- **Issue:** Specialized Google implementations without port abstraction
- **Fix Time:** 4-6 hours

---

## Compliance Summary Table

| Module | Port | Adapter | Violation | Severity |
|--------|------|---------|-----------|----------|
| Storage | StorageInterface ✓ | SupabaseStorageClient ✓ | Missing execute_sql() | CRITICAL |
| Storage | StorageInterface ✓ | SupabaseStorageClient ✓ | Private _ensure_client() accessed (2 places) | CRITICAL |
| Communication | NONE ✗ | WhatsAppClient ✓ | No CommunicationPort | HIGH |
| LLM | NONE ✗ | ChatOpenAI, ChatAnthropic, ChatGoogle ✓ | No LLMPort | HIGH |
| Checkpoint | NONE ✗ | PostgresSaver ✓ | LangGraph locked | MEDIUM |
| Media | NONE ✗ | VeoVideoGenerator ✓ | No MediaPort | MEDIUM |
| Voice | NONE ✗ | GeminiLiveSession ✓ | No VoicePort | MEDIUM |

---

## Files That Need Changes

### IMMEDIATE (Phase 1)

1. **core/ports.py**
   - ADD: execute_sql() method
   - ADD: CommunicationPort abstraction
   - ADD: LLMPort abstraction (optional, can be Phase 2)

2. **tools/campaign_persistence_tools.py**
   - REFACTOR: Execute_sql() calls to use transaction + insert_entity

3. **tools/product_search_tools.py**
   - REPLACE: _ensure_client() call with query_advanced()

4. **specialists/taxonomy_specialist.py**
   - REPLACE: _ensure_client() calls with query_entities()

### SHORT-TERM (Phase 2-3)

5. **integrations/communication/factory.py** (new)
   - CREATE: CommunicationPort factory

6. **core/llm_factory.py** + new wrapper
   - UPDATE: Return LLMPort instead of BaseChatModel

7. **Integration file reorganization**
   - MOVE: llm_factory.py to integrations/llm/
   - MOVE: google_live_api.py to integrations/llm/google/
   - MOVE: google_media_factory.py to integrations/llm/google/
   - MOVE: strict_openai_model.py to integrations/llm/openai/

---

## Testing Additions

Add multi-adapter tests to catch violations automatically:

```python
# tests/test_storage_port_compliance.py
@pytest.fixture(params=[SupabaseStorageClient, MockStorageAdapter])
def storage(request):
    """Test each tool against multiple adapters"""
    return request.param()

def test_product_search_with_any_adapter(storage: StorageInterface):
    """MUST NOT access _ensure_client()"""
    result = search_product_families(storage)
    assert result is not None

def test_campaign_persistence_with_any_adapter(storage: StorageInterface):
    """MUST use existing port methods"""
    result = persist_campaign(storage)
    assert result["success"]
```

---

## Risk Assessment

| Fix | Complexity | Risk | Time | Breaking Changes |
|-----|-----------|------|------|------------------|
| Add execute_sql() to port | Low | Low | 3-5 hrs | None |
| Fix _ensure_client() in product_search_tools | Low | Low | 2-3 hrs | None |
| Fix _ensure_client() in taxonomy_specialist | Very Low | Very Low | 1-2 hrs | None |
| Add CommunicationPort | Medium | Medium | 4-6 hrs | Low (new abstraction) |
| Add LLMPort | High | High | 8-12 hrs | High (affects agents) |
| LangGraph abstractions | High | Medium | 6-8 hrs | Medium |

**Total effort to full compliance:** 24-36 hours

**Recommended approach:** Fix critical violations first (6-10 hours), then ports (18-26 hours).

