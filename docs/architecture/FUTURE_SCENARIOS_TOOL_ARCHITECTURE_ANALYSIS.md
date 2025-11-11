# Future Scenarios: Tool Architecture Analysis

**Date:** 2025-01-11
**Status:** Analysis Complete - Architectural Decision Support
**Purpose:** Exhaustive scenario analysis to inform tool consolidation decisions

---

## Executive Summary

This document analyzes 8 future scenarios (scale, multi-tenancy, new domains, integrations, advanced workflows, real-time collaboration, compliance, AI evolution) to determine optimal tool architecture strategy.

**Critical Finding:** Current architecture is well-positioned for most scenarios but requires strategic enhancements for scale and multi-tenancy.

**Recommendation:** **EVOLUTIONARY APPROACH**
- Keep universal CRUD tool as foundation (proven, working)
- Add strategic domain-specific tools for hot paths (performance optimization)
- Enhance access control for multi-tenancy (row-level security)
- Implement caching + pagination for scale
- Monitor and adapt based on actual usage patterns

---

## Scenario Matrix: Architectural Impact Analysis

| Scenario | Current Architecture Breaks? | Tool Layer Changes | Access Control Needed | Business Logic Location | Consolidation Impact |
|----------|------------------------------|-------------------|----------------------|------------------------|---------------------|
| **1. Scale (10x-100x)** | ⚠️ Partial (query performance) | Add pagination, caching, streaming | Same (operation-scoped) | Schema layer (existing) | ✅ Favor consolidated (fewer cache layers) |
| **2. Multi-Tenancy** | ❌ Yes (missing RLS) | Add company_id injection | Row-level security (RLS) | Database constraints | ⚠️ Neutral (RLS works for both) |
| **3. New Domains** | ✅ No (schema-driven) | Zero changes (schema evolves) | Domain-specific read/write | Schema metadata | ✅ Favor consolidated (instant domain support) |
| **4. External Integrations** | ✅ No (tool layer separate) | New integration tools | API key scoping | Integration adapters | ❌ Favor specialized (API vs DB different) |
| **5. Advanced Workflows** | ⚠️ Partial (orchestration complexity) | Add workflow-specific tools | State-based permissions | Workflow engine | ⚠️ Neutral (depends on workflow type) |
| **6. Real-Time Collaboration** | ⚠️ Partial (concurrency) | Add optimistic locking | User-level permissions | Database triggers | ✅ Favor consolidated (single conflict resolution) |
| **7. Compliance & Audit** | ✅ No (audit log exists) | Add audit query tools | Audit access restrictions | Database triggers | ✅ Favor consolidated (single audit trail) |
| **8. AI Evolution** | ✅ No (LLM-friendly design) | Potentially simplify further | Context-aware permissions | Prompt engineering | ✅ Favor consolidated (simpler for smarter LLMs) |

**Legend:**
- ✅ No breaks / Favors consolidation
- ⚠️ Partial breaks / Neutral
- ❌ Breaks / Favors specialization

---

## Scenario 1: Scale (10x-100x Data Growth)

### Current State
- **Products:** ~100 (64 currently)
- **Families:** ~10 (7 currently)
- **Query Pattern:** Load all products for a family (simple query)

### Future State
- **Products:** 10K-100K per company
- **Families:** 1K-10K per company
- **Problem:** Loading all products becomes prohibitively expensive

### What Breaks

**1. Query Performance (Response Time)**
```python
# Current: Load all products for a family
products = await storage.query_entities(
    "products",
    filters={"product_family_id": family_id}
)
# 100 products = 50ms response
# 10K products = 5s response (UNACCEPTABLE)
```

**2. LLM Context Window**
```python
# Current: Specialist sees all 100 products in context
# Future: Cannot fit 10K products in 200K token context
# Impact: Specialist cannot "see everything" to make decisions
```

**3. CRUD Tool Parameter Size**
```python
# Current: OperationIntent with 100 entities = 50KB JSON
# Future: OperationIntent with 10K entities = 5MB JSON (TOO LARGE)
# Impact: HTTP request size limits, serialization overhead
```

### Tool Layer Changes Required

**Add Pagination Support**
```python
# NEW: Paginated query tool parameter
class PaginatedQueryInput(BaseModel):
    query_filter: dict[str, Any]
    page_size: int = 100  # Default page size
    page_token: str | None = None  # Cursor for next page
    sort_by: str = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"

# Tool returns page + cursor
class PaginatedResult(BaseModel):
    entities: list[dict[str, Any]]  # Current page
    next_page_token: str | None  # Cursor for next page
    total_count: int  # Total matching records (optional)
    has_more: bool  # Are there more pages?
```

**Add Streaming Support**
```python
# NEW: Stream results for large datasets
async def stream_query_results(
    table: str,
    filters: dict[str, Any],
    batch_size: int = 100
) -> AsyncIterator[list[dict[str, Any]]]:
    """Yield batches of results instead of loading all at once."""
    offset = 0
    while True:
        batch = await storage.query_entities(
            table, filters, limit=batch_size, offset=offset
        )
        if not batch:
            break
        yield batch
        offset += batch_size
```

**Add Caching Layer**
```python
# NEW: Redis/in-memory cache for hot queries
class CachedStorageAdapter:
    def __init__(self, storage: StorageInterface, cache: CacheInterface):
        self.storage = storage
        self.cache = cache
    
    async def query_entities(self, table: str, filters: dict):
        cache_key = f"{table}:{hash(frozenset(filters.items()))}"
        
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Cache miss - query database
        result = await self.storage.query_entities(table, filters)
        
        # Cache with TTL (5 minutes for semi-static data)
        await self.cache.set(cache_key, result, ttl=300)
        return result
```

### Access Control Changes

**No Changes Needed**
- Operation-scoped access control remains the same
- Pagination/caching are performance optimizations, not security concerns
- Read-only vs full CRUD distinction still valid

### Business Logic Location

**Stays in Schema Layer**
```python
# Schema metadata already defines indexes for performance
class TableSchema(BaseModel):
    name: str
    columns: dict[str, ColumnSchema]
    indexes: list[IndexDefinition]  # EXISTING
    
class IndexDefinition(BaseModel):
    columns: list[str]
    index_type: Literal["btree", "gin", "gist"]
    is_unique: bool = False
```

**Performance rules in schema registry:**
```python
# NEW: Performance hints in schema
class TableSchema(BaseModel):
    # ... existing fields
    performance_hints: PerformanceHints | None = None

class PerformanceHints(BaseModel):
    default_page_size: int = 100
    max_page_size: int = 1000
    cache_ttl_seconds: int = 300
    requires_pagination_above: int = 1000  # Auto-paginate if total > 1000
```

### Impact on Tool Consolidation Decision

**✅ FAVORS CONSOLIDATED TOOL**

**Why:**
1. **Fewer cache layers:** One universal tool = one cache implementation
2. **Consistent pagination:** All queries use same pagination strategy
3. **Unified performance monitoring:** Single tool to optimize
4. **Schema-driven optimization:** Table metadata controls pagination settings

**Specialized tools would require:**
- Duplicate pagination logic across 10+ domain-specific tools
- Multiple cache implementations (cache invalidation nightmare)
- Inconsistent performance characteristics per domain

---

## Scenario 2: Multi-Tenancy (1 → 1000s Companies)

### Current State
- **Companies:** 1 (Pavisha, single-tenant)
- **Architecture:** No company_id in queries, single company assumed
- **Access Control:** Operation-scoped only (read/write/etc)

### Future State
- **Companies:** 100-1000 companies in same database
- **Isolation Requirement:** Company A cannot see Company B's data
- **Problem:** Every query must filter by company_id

### What Breaks

**1. Missing Company Context in Queries**
```python
# Current: Query all products (assumes single company)
products = await storage.query_entities("products", {})
# Returns: 64 products for Pavisha

# Future: Query without company_id filter
products = await storage.query_entities("products", {})
# Returns: 50,000 products across 1000 companies (DATA LEAK!)
```

**2. No Row-Level Security (RLS)**
```sql
-- Current: No RLS policies
SELECT * FROM products WHERE id = 'uuid-123';
-- Returns product regardless of company ownership

-- Future (REQUIRED): RLS policy enforcement
CREATE POLICY tenant_isolation ON products
  USING (company_id = current_setting('app.current_company_id')::uuid);

SELECT * FROM products WHERE id = 'uuid-123';
-- Returns product ONLY if it belongs to current company
```

**3. Tool Configuration Lacks Company Context**
```python
# Current: Tool created without company awareness
tool = create_database_tool(
    storage=storage,
    allowed_operations=["read", "create", "update", "delete"]
)

# Future (REQUIRED): Tool needs company injection
tool = create_database_tool(
    storage=storage,
    allowed_operations=["read", "create", "update", "delete"],
    company_id="uuid-pavisha"  # NEW PARAMETER
)
```

### Tool Layer Changes Required

**1. Add Company Context Injection**
```python
# NEW: Company-aware tool factory
def create_database_tool(
    storage: StorageInterface,
    allowed_operations: list[str],
    company_id: str,  # NEW REQUIRED PARAMETER
    tables: list[str] | None = None,
    tool_name_suffix: str | None = None,
) -> BaseTool:
    """Create company-scoped database tool."""
    
    # Closure captures company_id
    async def _execute_database_operation_impl(operation_intent: dict):
        # Validate company context
        if not company_id:
            raise ToolException("Company context required for multi-tenant operation")
        
        # Inject company_id into ALL operations
        for operation in operation_intent["change_spec"]["operations"]:
            # Add company_id filter/field automatically
            if operation["op_type"] == "insert":
                # Ensure all new entities have company_id
                for entity in operation.get("new_entities", []):
                    entity["company_id"] = company_id
            
            elif operation["op_type"] in ["update", "delete", "query"]:
                # Add company_id to filter automatically
                filter_dict = operation.get("target_filter") or operation.get("delete_filter") or operation.get("query_filter")
                if filter_dict:
                    filter_dict["company_id"] = company_id
        
        # Execute with company context enforced
        result = await executor.execute_plan(...)
        return result
```

**2. Add Middleware for Company Injection**
```python
# NEW: Middleware pattern for company context
class CompanyContextMiddleware:
    """Inject company_id from authenticated user session."""
    
    def __init__(self, storage: StorageInterface):
        self.storage = storage
    
    async def __call__(self, request: Request, call_next):
        # Extract company_id from JWT token or session
        company_id = self._extract_company_from_auth(request)
        
        # Set company context in storage adapter
        self.storage.set_company_context(company_id)
        
        # Set Postgres session variable for RLS
        await self.storage.execute_sql(
            f"SET app.current_company_id = '{company_id}'"
        )
        
        response = await call_next(request)
        return response
```

### Access Control Changes Required

**Row-Level Security (RLS) in Database**
```sql
-- Enable RLS on all business tables
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_families ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
-- ... repeat for all 34 tables

-- Create RLS policy for tenant isolation
CREATE POLICY tenant_isolation_products ON products
  USING (company_id = current_setting('app.current_company_id')::uuid);

CREATE POLICY tenant_isolation_families ON product_families
  USING (company_id = current_setting('app.current_company_id')::uuid);

-- Repeat for all tables...
```

**Application-Level Access Control**
```python
# NEW: Company-scoped access control in tool factory
def create_database_tool(
    storage: StorageInterface,
    allowed_operations: list[str],
    company_id: str,
    tables: list[str] | None = None,
):
    # Validate company_id against authenticated user
    if not storage.validate_company_access(company_id):
        raise PermissionError(f"User does not have access to company {company_id}")
    
    # Create tool with company context baked in
    # ...
```

### Business Logic Location

**Database Constraints + Application Middleware**
```sql
-- Database enforces isolation via RLS policies
-- Application enforces via middleware injection

-- Add company_id to all business tables
ALTER TABLE products ADD COLUMN company_id UUID NOT NULL REFERENCES companies(id);
ALTER TABLE product_families ADD COLUMN company_id UUID NOT NULL REFERENCES companies(id);
-- ... repeat for all tables

-- Create compound indexes for performance
CREATE INDEX idx_products_company_family ON products(company_id, product_family_id);
CREATE INDEX idx_families_company ON product_families(company_id);
```

**Migration Strategy:**
```python
# Phase 1: Add company_id columns (nullable)
# Phase 2: Backfill company_id for existing data
# Phase 3: Make company_id NOT NULL
# Phase 4: Enable RLS policies
# Phase 5: Add compound indexes
```

### Impact on Tool Consolidation Decision

**⚠️ NEUTRAL - Works for Both Consolidated and Specialized**

**Why Neutral:**
1. **RLS applies regardless of tool count:** Whether 1 universal tool or 10 specialized tools, RLS policies enforce isolation at database level
2. **Middleware injection works for both:** Company context middleware injects company_id for any tool architecture
3. **Performance impact similar:** Compound indexes (`company_id, other_columns`) work for all query patterns

**Consolidated tool pros:**
- Single middleware injection point
- One place to enforce company context validation
- Consistent company_id handling across all operations

**Specialized tools pros:**
- Could optimize per-domain indexes (e.g., `campaigns` table might need different index strategy than `products`)
- Domain-specific company isolation rules (e.g., marketing domain allows cross-company analytics, product domain forbids)

**Conclusion:** Multi-tenancy is orthogonal to tool consolidation. Choose based on other factors.

---

## Scenario 3: New Domains (Beyond Product Catalog)

### Current State
- **Domains:** Product Catalog (14 tables)
- **Specialists:** Product Architecture, Taxonomy, Market Intelligence, Visual Assets, Content & SEO
- **Tool:** Universal CRUD tool (works on any table defined in schema)

### Future Domains
1. **Inventory Management** (4 new tables: locations, movements, counts, forecasts)
2. **Order Processing** (5 new tables: orders, order_items, shipments, payments, returns)
3. **Customer Data** (4 new tables: customers, interactions, preferences, loyalty_points)
4. **Analytics** (3 new tables: attribution_events, ab_tests, journey_snapshots)

### What Breaks

**NOTHING BREAKS!** ✅

**Current Architecture is Schema-Driven:**
```python
# Adding new domain = Add tables to schema registry
INVENTORY_SCHEMA = SchemaRegistry(
    version="v1",
    domain="inventory_management",
    tables={
        "inventory_locations": TableSchema(...),
        "inventory_movements": TableSchema(...),
        "inventory_counts": TableSchema(...),
        "inventory_forecasts": TableSchema(...),
    }
)

# Universal CRUD tool immediately supports new domain
inventory_tool = create_database_tool(
    storage=storage,
    allowed_operations=["create", "read", "update", "delete"],
    tables=["inventory_locations", "inventory_movements", "inventory_counts", "inventory_forecasts"],
    tool_name_suffix="inventory"
)

# Specialist can use tool without ANY tool changes
inventory_specialist = create_agent(
    name="inventory_specialist",
    tools=[inventory_tool, get_inventory_schema_tool],
    system_prompt=load_prompt("specialists/inventory.prompt")
)
```

**Zero Code Changes Required:**
1. ✅ Add schema metadata (inventory_schema_v1.json)
2. ✅ Create database migrations (4 new tables)
3. ✅ Create inventory specialist prompt
4. ✅ Add PM routing rules for inventory domain

**No Changes to:**
- ❌ Universal CRUD tool (schema-agnostic)
- ❌ Operation executor (works on any table)
- ❌ Schema validator (validates against any schema)
- ❌ Transaction handler (operates on any table)

### Tool Layer Changes Required

**ZERO CHANGES!** ✅

**Why:**
```python
# Universal tool is domain-agnostic by design
class OperationExecutor:
    async def _execute_operation(
        self, operation: Operation, context: dict
    ):
        # Get table schema dynamically
        table_schema = self.schema.get_table(operation.table)
        
        # Route to handler based on operation type, not domain
        handlers = {
            "insert": self._execute_insert,
            "update": self._execute_update,
            "delete": self._execute_delete,
            "query": self._execute_query,
        }
        
        handler = handlers[operation.op_type]
        return await handler(operation, table_schema, context)
```

**Inventory domain operations use SAME handlers:**
- INSERT inventory_movements → `_execute_insert()`
- UPDATE inventory_counts → `_execute_update()`
- DELETE inventory_forecasts → `_execute_delete()`
- QUERY inventory_locations → `_execute_query()`

### Access Control Changes Required

**Domain-Specific Access Control (Optional)**
```python
# Create domain-scoped tools if needed
inventory_read_tool = create_database_tool(
    storage=storage,
    allowed_operations=["read"],  # Read-only for reporting specialist
    tables=["inventory_locations", "inventory_movements", "inventory_counts", "inventory_forecasts"],
    tool_name_suffix="inventory_read"
)

inventory_write_tool = create_database_tool(
    storage=storage,
    allowed_operations=["create", "update"],  # No delete for inventory
    tables=["inventory_locations", "inventory_movements"],  # Subset of tables
    tool_name_suffix="inventory_write"
)
```

**No changes to access control mechanism:**
- Operation-scoped access (read/write/etc) already works
- Table-level access already works
- Just configure tools per specialist's role

### Business Logic Location

**Schema Metadata (Same Pattern as Product Domain)**
```python
# inventory_schema_v1.json
{
  "version": "v1",
  "domain": "inventory_management",
  "tables": {
    "inventory_movements": {
      "name": "inventory_movements",
      "columns": {
        "id": {"type": "uuid", "primary_key": true},
        "product_id": {"type": "uuid", "foreign_key": "products.id"},
        "from_location_id": {"type": "uuid", "foreign_key": "inventory_locations.id"},
        "to_location_id": {"type": "uuid", "foreign_key": "inventory_locations.id"},
        "quantity": {"type": "integer"},
        "movement_type": {"type": "text", "enum": ["transfer", "adjustment", "receipt", "return"]}
      },
      "relationships": [
        {"type": "parent", "target_table": "products", "foreign_key": "product_id"},
        {"type": "parent", "target_table": "inventory_locations", "foreign_key": "from_location_id"},
        {"type": "parent", "target_table": "inventory_locations", "foreign_key": "to_location_id"}
      ],
      "business_rules": [
        {
          "rule_type": "validation",
          "trigger": "before_insert",
          "handler": "validate_inventory_movement",
          "parameters": {"prevent_negative_stock": true}
        }
      ]
    }
  }
}
```

**Business rules in schema (reusable handlers):**
```python
# Business rule handlers (domain-specific, but registered once)
class InventoryBusinessRules:
    @staticmethod
    async def validate_inventory_movement(
        storage: StorageInterface,
        operation: Operation,
        result: dict,
        parameters: dict,
        schema: SchemaRegistry
    ):
        """Prevent inventory from going negative."""
        if parameters.get("prevent_negative_stock"):
            # Check current stock levels before movement
            # Raise ToolException if movement would cause negative stock
            pass
```

### Impact on Tool Consolidation Decision

**✅ STRONGLY FAVORS CONSOLIDATED TOOL**

**Why:**
1. **Instant domain support:** Add schema → domain works immediately
2. **No tool proliferation:** 10 new domains ≠ 10 new CRUD tools
3. **Consistent behavior:** All domains use same CRUD semantics
4. **Reusable business rules:** Schema-driven rules work across domains
5. **Zero maintenance overhead:** No per-domain tool code to maintain

**Specialized tools would require:**
- `create_inventory_crud_tool()` - duplicate CRUD logic
- `create_orders_crud_tool()` - duplicate CRUD logic
- `create_customers_crud_tool()` - duplicate CRUD logic
- ... 10 more tools, each 1500 LOC, each needing maintenance

**Real-world comparison:**
- **Consolidated:** 1 tool × 1500 LOC = 1500 LOC for all domains
- **Specialized:** 10 tools × 1500 LOC = 15,000 LOC for 10 domains

---

## Scenario 4: External Integrations

### Current State
- **Integrations:** None (database-only operations)
- **Tool Layer:** Universal CRUD for database
- **API Calls:** Handled by specialist-specific tools (e.g., `research_product_online()`)

### Future Integrations
1. **Shopify Sync** (bi-directional product data)
2. **WhatsApp Commerce** (product catalog API)
3. **Analytics Platforms** (Google Analytics, Mixpanel)
4. **Payment Gateways** (Stripe, Razorpay)
5. **Advertising Platforms** (Meta Ads, Google Ads, Amazon Advertising)

### What Breaks

**NOTHING BREAKS (Different Tool Category)** ✅

**Why:**
```python
# Database CRUD tools and API integration tools are SEPARATE
database_tool = create_database_tool(...)  # For database operations
shopify_sync_tool = create_shopify_sync_tool(...)  # For API operations

# Specialist gets both tool types
product_sync_specialist = create_agent(
    name="product_sync_specialist",
    tools=[
        database_tool,        # Read products from local DB
        shopify_sync_tool,    # Sync products to Shopify
        analytics_tool,       # Send events to Google Analytics
    ],
    system_prompt=load_prompt("specialists/product_sync.prompt")
)
```

**Architecture principle:** Tool consolidation applies WITHIN a category, not ACROSS categories.

### Tool Layer Changes Required

**Add Integration Tool Category**
```python
# NEW CATEGORY: External Integration Tools (orthogonal to CRUD tools)

# 1. Platform API Tool Factory
def create_platform_api_tool(
    platform: Literal["shopify", "meta", "google_ads", "stripe"],
    operation: str,  # "sync_product", "create_campaign", "process_payment"
    credentials_store: CredentialsInterface,
) -> BaseTool:
    """Create platform-specific API tool."""
    
    # Each platform has different API contract
    platform_adapters = {
        "shopify": ShopifyAdapter(credentials_store),
        "meta": MetaAdsAdapter(credentials_store),
        "google_ads": GoogleAdsAdapter(credentials_store),
        "stripe": StripeAdapter(credentials_store),
    }
    
    adapter = platform_adapters[platform]
    
    async def _execute_platform_operation(operation_params: dict):
        # Platform-specific logic
        result = await adapter.execute(operation, operation_params)
        return result
    
    return StructuredTool.from_function(
        coroutine=_execute_platform_operation,
        name=f"{platform}_{operation}",
        description=f"Execute {operation} on {platform} platform"
    )

# 2. Shopify Sync Tool
shopify_sync_tool = create_platform_api_tool(
    platform="shopify",
    operation="sync_product",
    credentials_store=credentials
)

# 3. Meta Ads Tool
meta_ads_tool = create_platform_api_tool(
    platform="meta",
    operation="create_campaign",
    credentials_store=credentials
)
```

**Integration tools are SPECIALIZED by necessity:**
- Shopify API ≠ Meta Ads API ≠ Google Ads API
- Different authentication mechanisms (OAuth, API keys, service accounts)
- Different rate limits (Shopify: 40 req/s, Meta: CPU time budget, Google: quota units)
- Different error handling (retry strategies vary per platform)
- Different data models (Shopify variants ≠ Meta product sets)

### Access Control Changes Required

**API Key Scoping**
```python
# NEW: Platform credentials with scoping
class PlatformCredential(BaseModel):
    platform: str
    credential_type: Literal["oauth_token", "api_key", "service_account"]
    access_token_encrypted: str
    refresh_token_encrypted: str | None
    scopes: list[str]  # OAuth scopes
    company_id: str  # Multi-tenant support
    account_id: str  # Platform account ID

# Tool factory validates credential access
def create_platform_api_tool(platform: str, credentials_store: CredentialsInterface):
    # Retrieve platform credentials for current company
    credential = credentials_store.get_credential(
        platform=platform,
        company_id=current_company_id
    )
    
    if not credential:
        raise PermissionError(f"No credentials configured for {platform}")
    
    # Validate scopes match operation requirements
    if not credential.has_required_scopes(operation):
        raise PermissionError(f"Insufficient scopes for {operation} on {platform}")
    
    # Create tool with validated credentials
    # ...
```

### Business Logic Location

**Integration Adapters (Separate from Database Layer)**
```python
# Domain-specific adapters for each platform
class ShopifyAdapter:
    """Adapter for Shopify Admin API."""
    
    def __init__(self, credentials: PlatformCredential):
        self.credentials = credentials
        self.client = ShopifyClient(
            api_key=credentials.access_token_encrypted,
            shop_url=credentials.account_id
        )
    
    async def sync_product(self, product: Product) -> ShopifyProduct:
        """Map internal Product to Shopify product and sync."""
        shopify_product = self._map_to_shopify_format(product)
        result = await self.client.products.create(shopify_product)
        return result
    
    def _map_to_shopify_format(self, product: Product) -> dict:
        """Business logic: Internal product → Shopify API format."""
        return {
            "title": product.name,
            "body_html": product.description,
            "vendor": product.brand,
            "product_type": product.category,
            "variants": self._map_variants(product.variants),
            # ... Shopify-specific mapping
        }

class MetaAdsAdapter:
    """Adapter for Meta Marketing API."""
    
    async def create_campaign(self, campaign: Campaign) -> MetaCampaign:
        """Map internal Campaign to Meta campaign and create."""
        meta_campaign = self._map_to_meta_format(campaign)
        result = await self.client.campaigns.create(meta_campaign)
        return result
```

**Why separate adapters:**
- Each platform has unique API contract (cannot be generalized)
- Business logic for mapping internal models → platform models varies
- Error handling, retry logic, rate limiting differs per platform
- Platform-specific features (Meta Advantage+, Shopify metafields, etc.)

### Impact on Tool Consolidation Decision

**❌ FAVORS SPECIALIZED TOOLS (For Integration Layer)**

**Why:**
1. **Heterogeneous APIs:** Shopify API ≠ Meta API → cannot consolidate
2. **Platform-specific logic:** Each platform requires custom adapter
3. **Different authentication:** OAuth, API keys, service accounts vary
4. **Different error semantics:** Retry strategies, rate limits unique per platform

**Tool layer architecture:**
```
Database Layer (Consolidated):
  - Universal CRUD Tool → Works on any schema

Integration Layer (Specialized):
  - Shopify Sync Tool → Shopify adapter
  - Meta Ads Tool → Meta adapter
  - Google Ads Tool → Google adapter
  - Stripe Payment Tool → Stripe adapter
```

**Conclusion:** **Hybrid approach** is optimal
- **Consolidate** database CRUD (schema-driven, uniform semantics)
- **Specialize** platform integrations (heterogeneous APIs, unique logic)

---

## Scenario 5: Advanced Workflows

### Current State
- **Workflows:** Product Onboarding (5 specialists → PM synthesis → atomic persistence)
- **Orchestration:** LangGraph state machine + PM delegation
- **Persistence:** Single atomic transaction (9 tables)

### Future Advanced Workflows
1. **Automated Pricing** (competitor analysis → price optimization → update products)
2. **Content Generation** (bulk product descriptions → 10K products)
3. **Image Processing** (background removal → enhancement → variant generation)
4. **A/B Testing** (variant performance tracking → automated winner selection)

### What Breaks

**⚠️ PARTIAL BREAKS - Orchestration Complexity**

**1. Long-Running Operations**
```python
# Current: Product onboarding completes in <30 seconds
await pm.delegate_to_specialists(...)
await atomic_persistence(result)  # Single transaction

# Future: Bulk content generation for 10K products takes 2 hours
await content_specialist.generate_descriptions(10000 products)
# Cannot hold transaction open for 2 hours (database timeout)
```

**2. Asynchronous Execution**
```python
# Current: Synchronous workflow (specialist → PM → persistence)

# Future: Async workflow (kick off job → poll for completion)
job_id = await image_processing_specialist.start_batch_job(1000 images)
# PM needs to:
# 1. Store job_id for later polling
# 2. Check job status periodically
# 3. Resume when complete
```

**3. Partial Success Handling**
```python
# Current: All-or-nothing (transaction commits or rolls back)

# Future: Partial success (500 descriptions generated, 500 failed)
# Need to:
# 1. Save successful results
# 2. Track failed items for retry
# 3. Report progress to user
```

### Tool Layer Changes Required

**Add Workflow-Specific Tools**
```python
# NEW: Batch operation tools with progress tracking

class BatchOperationInput(BaseModel):
    operation_type: str  # "generate_descriptions", "process_images", "optimize_prices"
    batch_size: int = 100  # Process in chunks
    entity_ids: list[str]  # Which products to process
    options: dict[str, Any]  # Operation-specific parameters

class BatchOperationResult(BaseModel):
    job_id: str  # Unique job ID for polling
    status: Literal["queued", "running", "completed", "failed", "partial"]
    total_items: int
    processed_items: int
    failed_items: int
    results: list[dict[str, Any]]  # Results for completed items
    errors: list[dict[str, Any]]  # Errors for failed items
    next_batch_token: str | None  # For resuming

# Tool factory for batch operations
def create_batch_operation_tool(
    operation_name: str,
    executor: Callable,
    storage: StorageInterface,
) -> BaseTool:
    """Create batch operation tool with progress tracking."""
    
    async def _execute_batch_operation(params: BatchOperationInput):
        # Create job record for tracking
        job = await storage.insert_entity("batch_jobs", {
            "operation_type": params.operation_type,
            "total_items": len(params.entity_ids),
            "status": "queued",
            "created_at": datetime.now(UTC),
        })
        
        # Process in batches (async)
        results = []
        errors = []
        
        for batch in chunk_list(params.entity_ids, params.batch_size):
            try:
                batch_result = await executor(batch, params.options)
                results.extend(batch_result)
                
                # Update progress
                await storage.update_entities(
                    "batch_jobs",
                    {"id": job["id"]},
                    {"processed_items": len(results)}
                )
            except Exception as e:
                errors.append({"batch": batch, "error": str(e)})
        
        # Mark job complete
        await storage.update_entities(
            "batch_jobs",
            {"id": job["id"]},
            {
                "status": "completed" if not errors else "partial",
                "processed_items": len(results),
                "failed_items": len(errors),
                "completed_at": datetime.now(UTC),
            }
        )
        
        return BatchOperationResult(
            job_id=job["id"],
            status="completed" if not errors else "partial",
            total_items=len(params.entity_ids),
            processed_items=len(results),
            failed_items=len(errors),
            results=results,
            errors=errors,
        )
    
    return StructuredTool.from_function(
        coroutine=_execute_batch_operation,
        name=f"batch_{operation_name}",
        description=f"Execute {operation_name} in batches with progress tracking"
    )
```

**Add Job Polling Tools**
```python
# NEW: Poll batch job status
@tool("poll_batch_job_status")
async def poll_batch_job_status(job_id: str, storage: StorageInterface) -> dict:
    """Check status of batch operation job."""
    job = await storage.query_entities("batch_jobs", {"id": job_id})
    if not job:
        raise ToolException(f"Job {job_id} not found")
    
    return {
        "job_id": job_id,
        "status": job[0]["status"],
        "total_items": job[0]["total_items"],
        "processed_items": job[0]["processed_items"],
        "failed_items": job[0]["failed_items"],
        "progress_percent": (job[0]["processed_items"] / job[0]["total_items"]) * 100,
    }
```

### Access Control Changes Required

**State-Based Permissions**
```python
# NEW: Job ownership validation
async def validate_job_access(job_id: str, company_id: str) -> bool:
    """Ensure user can access job (belongs to their company)."""
    job = await storage.query_entities("batch_jobs", {"id": job_id})
    
    if not job:
        return False
    
    return job[0]["company_id"] == company_id

# Tool enforces job ownership
@tool("poll_batch_job_status")
async def poll_batch_job_status(job_id: str):
    if not await validate_job_access(job_id, current_company_id):
        raise PermissionError(f"Access denied to job {job_id}")
    
    # ... poll job status
```

### Business Logic Location

**Workflow Engine (LangGraph + Custom Orchestration)**
```python
# LangGraph workflow for batch operations
class BatchWorkflowState(TypedDict):
    operation_type: str
    entity_ids: list[str]
    batch_size: int
    job_id: str | None
    current_batch_index: int
    results: list[dict]
    errors: list[dict]
    status: str

# Workflow graph
workflow = StateGraph(BatchWorkflowState)

workflow.add_node("initialize_job", initialize_job_node)
workflow.add_node("process_batch", process_batch_node)
workflow.add_node("update_progress", update_progress_node)
workflow.add_node("finalize_job", finalize_job_node)

# Conditional edges
workflow.add_conditional_edges(
    "process_batch",
    lambda state: "process_batch" if state["current_batch_index"] < len(state["entity_ids"]) else "finalize_job",
)

# Run workflow
app = workflow.compile()
result = await app.ainvoke({
    "operation_type": "generate_descriptions",
    "entity_ids": product_ids,
    "batch_size": 100,
})
```

### Impact on Tool Consolidation Decision

**⚠️ NEUTRAL - Depends on Workflow Type**

**Simple Workflows (CRUD-heavy):**
- ✅ Universal CRUD tool sufficient
- Example: Product onboarding (insert 100 records)

**Complex Workflows (Long-running, Batch):**
- ⚠️ Need specialized batch tools
- Example: Content generation for 10K products

**Recommended Architecture:**
```python
# Base layer: Universal CRUD (for simple operations)
crud_tool = create_database_tool(storage, ["create", "read", "update", "delete"])

# Workflow layer: Batch operation tools (for complex workflows)
batch_content_tool = create_batch_operation_tool(
    operation_name="generate_content",
    executor=content_generator.batch_generate,
    storage=storage,
)

batch_image_tool = create_batch_operation_tool(
    operation_name="process_images",
    executor=image_processor.batch_process,
    storage=storage,
)

# Specialist gets both
content_specialist = create_agent(
    tools=[
        crud_tool,            # For simple CRUD
        batch_content_tool,   # For bulk operations
    ]
)
```

**Conclusion:** **Hybrid approach**
- Keep universal CRUD for simple workflows
- Add specialized batch tools for complex workflows
- Orchestration complexity lives in LangGraph state machine, not in tools

---

## Scenario 6: Real-Time Collaboration

### Current State
- **Users:** Single user per workflow (WhatsApp message)
- **Concurrency:** None (one workflow at a time per thread)
- **Conflict Resolution:** Not needed (no concurrent edits)

### Future State
- **Users:** Multiple users editing same product simultaneously
- **Live Updates:** Real-time catalog changes
- **Notifications:** Product published, price changed, etc.

### What Breaks

**⚠️ PARTIAL BREAKS - Concurrency Control**

**1. Lost Updates (Race Condition)**
```python
# Current: No concurrency control
# User A: Read product price = $100
product_a = await storage.query_entities("products", {"id": "uuid-123"})
# User B: Read product price = $100 (at same time)
product_b = await storage.query_entities("products", {"id": "uuid-123"})

# User A: Update price to $110
await storage.update_entities("products", {"id": "uuid-123"}, {"price": 110})

# User B: Update price to $120 (overwrites User A's change!)
await storage.update_entities("products", {"id": "uuid-123"}, {"price": 120})

# Final price: $120 (User A's update LOST)
```

**2. No Version Tracking**
```python
# Current: No version field in schema
class Product(BaseModel):
    id: str
    name: str
    price: float
    # NO version field!

# Future: Need version for optimistic locking
class Product(BaseModel):
    id: str
    name: str
    price: float
    version: int  # Incremented on each update
```

**3. No Notifications**
```python
# Current: No event system for changes

# Future: Need to notify users of changes
# User A changes price → User B sees notification "Price updated by User A"
```

### Tool Layer Changes Required

**Add Optimistic Locking**
```python
# NEW: Version-aware update operation
class OptimisticUpdateInput(BaseModel):
    table: str
    entity_id: str
    expected_version: int  # Client's known version
    field_updates: dict[str, Any]

@tool("optimistic_update")
async def optimistic_update(params: OptimisticUpdateInput, storage: StorageInterface):
    """Update entity with optimistic locking."""
    
    # Atomic check-and-update (PostgreSQL)
    result = await storage.execute_sql(f"""
        UPDATE {params.table}
        SET
            {', '.join(f'{k} = ${i+2}' for i, k in enumerate(params.field_updates.keys()))},
            version = version + 1,
            updated_at = NOW()
        WHERE
            id = $1
            AND version = ${len(params.field_updates) + 2}  -- Expected version
        RETURNING *;
    """, params.entity_id, *params.field_updates.values(), params.expected_version)
    
    if not result:
        # Version mismatch - entity was modified by another user
        current_entity = await storage.query_entities(params.table, {"id": params.entity_id})
        raise ToolException(
            f"Conflict: Entity was modified by another user. "
            f"Expected version {params.expected_version}, current version {current_entity[0]['version']}. "
            f"Please refresh and retry."
        )
    
    return result[0]
```

**Add Event Publishing**
```python
# NEW: Publish entity change events
class EntityChangeEvent(BaseModel):
    event_type: Literal["created", "updated", "deleted"]
    table: str
    entity_id: str
    changed_fields: list[str]
    changed_by: str  # User ID
    changed_at: datetime

@tool("publish_entity_change")
async def publish_entity_change(event: EntityChangeEvent, event_bus: EventBusInterface):
    """Publish entity change event for real-time notifications."""
    await event_bus.publish(
        topic=f"{event.table}.{event.event_type}",
        payload=event.model_dump(),
    )
```

### Access Control Changes Required

**User-Level Permissions**
```python
# NEW: User-scoped access control
class UserPermission(BaseModel):
    user_id: str
    company_id: str
    role: Literal["admin", "editor", "viewer"]
    table_permissions: dict[str, list[str]]  # {"products": ["read", "update"], "campaigns": ["read"]}

def create_database_tool(
    storage: StorageInterface,
    user_id: str,  # NEW PARAMETER
    company_id: str,
):
    """Create user-scoped database tool."""
    
    # Load user permissions
    permissions = await storage.query_entities(
        "user_permissions",
        {"user_id": user_id, "company_id": company_id}
    )
    
    if not permissions:
        raise PermissionError(f"No permissions found for user {user_id}")
    
    user_permissions = UserPermission.model_validate(permissions[0])
    
    # Create tool with user-specific access control
    # ...
```

### Business Logic Location

**Database Triggers (Event Publishing)**
```sql
-- Automatically publish change events via trigger
CREATE OR REPLACE FUNCTION publish_entity_change_event()
RETURNS TRIGGER AS $$
DECLARE
    event_payload JSONB;
BEGIN
    event_payload := jsonb_build_object(
        'event_type', TG_OP,
        'table', TG_TABLE_NAME,
        'entity_id', NEW.id,
        'changed_at', NOW(),
        'changed_by', current_setting('app.current_user_id', true)
    );
    
    -- Insert into event queue for async processing
    INSERT INTO entity_change_events (payload) VALUES (event_payload);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all business tables
CREATE TRIGGER publish_products_change
    AFTER INSERT OR UPDATE OR DELETE ON products
    FOR EACH ROW EXECUTE FUNCTION publish_entity_change_event();

CREATE TRIGGER publish_campaigns_change
    AFTER INSERT OR UPDATE OR DELETE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION publish_entity_change_event();
```

**Application Layer (Notification Delivery)**
```python
# Background worker processes event queue and sends notifications
class NotificationWorker:
    async def process_entity_change_events(self):
        """Poll event queue and send notifications to connected clients."""
        while True:
            events = await storage.query_entities(
                "entity_change_events",
                {"processed": False},
                limit=100
            )
            
            for event in events:
                # Send notification via WebSocket, push notification, etc.
                await self.send_notification(event)
                
                # Mark event as processed
                await storage.update_entities(
                    "entity_change_events",
                    {"id": event["id"]},
                    {"processed": True}
                )
            
            await asyncio.sleep(1)  # Poll every second
```

### Impact on Tool Consolidation Decision

**✅ FAVORS CONSOLIDATED TOOL**

**Why:**
1. **Single conflict resolution mechanism:** One tool = one optimistic locking implementation
2. **Consistent versioning:** All tables use same version field pattern
3. **Unified event publishing:** Single trigger function for all tables
4. **Simpler client logic:** Clients handle version conflicts the same way for all operations

**Specialized tools would require:**
- Duplicate optimistic locking logic across 10+ domain tools
- Inconsistent version field naming (product.version vs campaign.revision)
- Multiple event publishing mechanisms (harder to maintain)

**Conclusion:** Real-time collaboration reinforces benefit of consolidated tool architecture.

---

## Scenario 7: Compliance & Audit

### Current State
- **Audit Log:** Universal audit_log table (tracks all changes)
- **Triggers:** Automatic triggers on all business tables
- **Retention:** Indefinite (audit_log never deleted)

### Future Compliance Requirements
1. **GDPR** (data deletion, export, right to be forgotten)
2. **SOC2** (audit trails, access logs, change tracking)
3. **Industry Regulations** (pharma, finance - immutable audit trail)

### What Breaks

**✅ NOTHING BREAKS!** (Current architecture already compliance-ready)

**Current Implementation (from database schema):**
```sql
-- Universal audit table (already exists)
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name TEXT NOT NULL,
  record_id UUID NOT NULL,
  operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
  old_values JSONB,          -- Before state
  new_values JSONB,          -- After state
  changed_fields TEXT[],     -- What changed
  changed_by TEXT,           -- Who changed it
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  change_reason TEXT,
  session_id TEXT,
  ip_address INET,
  user_agent TEXT
);

-- Automatic trigger on all tables
CREATE TRIGGER audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON products
    FOR EACH ROW EXECUTE FUNCTION audit_log_trigger();
```

**This already provides:**
- ✅ Complete change history (INSERT/UPDATE/DELETE)
- ✅ JSONB snapshots (old_values, new_values for rollback)
- ✅ Changed fields tracking (efficient queries)
- ✅ Who/when/why context (changed_by, changed_at, change_reason)
- ✅ Session tracking (session_id, ip_address, user_agent)

### Tool Layer Changes Required

**Add Audit Query Tools**
```python
# NEW: Query audit trail for compliance reporting

@tool("query_audit_trail")
async def query_audit_trail(
    table: str | None = None,
    record_id: str | None = None,
    operation: Literal["INSERT", "UPDATE", "DELETE"] | None = None,
    changed_by: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    storage: StorageInterface,
) -> list[dict]:
    """Query audit log for compliance reporting."""
    
    filters = {}
    if table:
        filters["table_name"] = table
    if record_id:
        filters["record_id"] = record_id
    if operation:
        filters["operation"] = operation
    if changed_by:
        filters["changed_by"] = changed_by
    
    # Date range filtering
    date_filters = {}
    if start_date:
        date_filters["gte"] = start_date.isoformat()
    if end_date:
        date_filters["lte"] = end_date.isoformat()
    
    query = storage.query_entities(
        "audit_log",
        filters=filters,
        limit=limit,
    )
    
    # Apply date range via SQL (complex filter)
    if date_filters:
        query = query.gte("changed_at", date_filters.get("gte"))
        query = query.lte("changed_at", date_filters.get("lte"))
    
    results = await query
    return results

@tool("export_user_data_gdpr")
async def export_user_data_gdpr(user_id: str, storage: StorageInterface) -> dict:
    """Export all user data for GDPR compliance."""
    
    # Collect all data related to user across all tables
    user_data = {
        "user_id": user_id,
        "exported_at": datetime.now(UTC).isoformat(),
        "data": {}
    }
    
    # Query each table for user's data
    tables_with_user_data = ["customers", "orders", "interactions", "preferences"]
    
    for table in tables_with_user_data:
        records = await storage.query_entities(table, {"user_id": user_id})
        user_data["data"][table] = records
    
    # Include audit trail
    audit_trail = await storage.query_entities("audit_log", {"changed_by": user_id})
    user_data["audit_trail"] = audit_trail
    
    return user_data

@tool("delete_user_data_gdpr")
async def delete_user_data_gdpr(user_id: str, storage: StorageInterface) -> dict:
    """Delete all user data for GDPR right to be forgotten."""
    
    deleted_counts = {}
    
    # Delete from each table (with audit logging)
    tables_with_user_data = ["customers", "orders", "interactions", "preferences"]
    
    async with storage.transaction():
        for table in tables_with_user_data:
            count = await storage.delete_entities(table, {"user_id": user_id})
            deleted_counts[table] = count
        
        # Anonymize audit trail (cannot delete for compliance)
        await storage.update_entities(
            "audit_log",
            {"changed_by": user_id},
            {"changed_by": f"ANONYMIZED_{user_id[:8]}"}
        )
    
    return {
        "user_id": user_id,
        "deleted_at": datetime.now(UTC).isoformat(),
        "deleted_counts": deleted_counts,
        "audit_trail_anonymized": True,
    }
```

### Access Control Changes Required

**Audit Access Restrictions**
```python
# NEW: Restrict audit log access to compliance officers
def create_audit_query_tool(
    storage: StorageInterface,
    user_role: str,  # Only "compliance_officer" or "admin"
) -> BaseTool:
    """Create audit query tool with role restriction."""
    
    if user_role not in ["compliance_officer", "admin"]:
        raise PermissionError("Audit log access requires compliance officer or admin role")
    
    # Create tool with audit-specific access control
    return audit_tool
```

### Business Logic Location

**Database Triggers (Automatic Audit Trail)**
```sql
-- Already implemented (from current schema)
CREATE OR REPLACE FUNCTION audit_log_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Log all changes automatically
    INSERT INTO audit_log (
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_fields,
        changed_by,
        changed_at,
        session_id,
        ip_address
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
        CASE WHEN TG_OP = 'UPDATE' THEN (
            SELECT array_agg(key)
            FROM jsonb_each_text(to_jsonb(NEW))
            WHERE to_jsonb(NEW) ->> key IS DISTINCT FROM to_jsonb(OLD) ->> key
        ) ELSE NULL END,
        current_setting('app.current_user_id', true),
        NOW(),
        current_setting('app.session_id', true),
        inet_client_addr()
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Impact on Tool Consolidation Decision

**✅ STRONGLY FAVORS CONSOLIDATED TOOL**

**Why:**
1. **Single audit trail:** One tool = one audit log implementation = consistent trail
2. **Automatic tracking:** Database triggers log ALL operations regardless of tool
3. **No audit gaps:** Universal tool ensures every operation is audited the same way
4. **Compliance simplicity:** Single audit schema easier to certify (SOC2, GDPR)
5. **Efficient queries:** One audit_log table with proper indexes

**Specialized tools would create:**
- Risk of audit gaps (forgot to add trigger to one domain tool)
- Inconsistent audit formats (each domain logs differently)
- Multiple audit tables (products_audit, campaigns_audit) - harder to query
- Certification complexity (need to prove all 10 tools are compliant)

**Conclusion:** Compliance requirements STRONGLY favor consolidated tool architecture.

---

## Scenario 8: AI Evolution (Larger Context, Better Reasoning)

### Current State
- **Context Window:** 200K tokens (Claude Sonnet 4.5)
- **Reasoning:** Strong but requires structured guidance
- **Tool Schema:** Dynamic Pydantic models with field descriptions

### Future AI Capabilities
- **Context Window:** 1M+ tokens (future models)
- **Reasoning:** O1-level reasoning (stronger planning, self-correction)
- **Multimodal:** Native video analysis, voice, interactive code execution

### What Breaks

**✅ NOTHING BREAKS!** (Better AI makes current architecture MORE effective)

**Current Architecture Already Optimized for AI Evolution:**

**1. Schema-Driven Design**
```python
# LLM reads schema metadata to understand database structure
schema = await get_product_schema()

# LLM reasons about operations dynamically
operation_intent = OperationIntent(
    intent_type="create",
    change_spec=ChangeSpecification(
        operations=[
            # LLM figures out dependencies, ordering, etc.
            Operation(op_type="insert", table="variant_values", ...),
            Operation(op_type="insert", table="products", depends_on=[0]),
        ]
    ),
    impact_analysis=ImpactAnalysis(
        # LLM calculates impact from schema + current data
        new_entities_count={"variant_values": 1, "products": 2},
        business_impact_summary="Will create 2 new SKUs for 2L capacity",
    )
)
```

**Future (with better reasoning):**
- ✅ LLM handles more complex multi-table operations (50+ operations in single plan)
- ✅ LLM self-corrects mistakes before execution (validates plan against schema)
- ✅ LLM generates better impact analysis (deeper understanding of business logic)

**2. Minimal Scaffolding (Intelligence-First)**
```python
# Current: Trust LLM to plan operations dynamically (not rigid recipes)

# Future: Even less scaffolding needed
# O1-level reasoning can handle:
# - Complex dependency graphs (topological sorting)
# - Edge case handling (null checks, data validation)
# - Optimization (batch operations, minimize queries)
```

**3. Rich Context in Tool Schema**
```python
# Current: Dynamic Pydantic models with context-aware descriptions
class ReadOperationInput(BaseModel):
    intent_type: str = Field(
        ...,
        description='Intent type. Must be "read". This tool handles read operations only.'
    )

# Future: LLM uses descriptions more effectively
# Better models = better tool selection (fewer wrong tool calls)
```

### Tool Layer Changes Could Simplify

**Potential Simplifications:**

**1. Fewer Input Validations**
```python
# Current: Validate operation completeness (LLM sometimes forgets entities)
_validate_operation_completeness(operations, impact_analysis)

# Future: O1-level reasoning won't forget entities
# Could remove validation (or make it a warning instead of error)
```

**2. More Atomic Tools**
```python
# Current: Universal tool handles complex multi-step operations

# Future: Could potentially break into smaller atomic tools
# LLM orchestrates composition (O1 reasoning handles complexity)

# Example:
create_variant_value_tool = create_database_tool(operations=["create"], tables=["variant_values"])
create_product_tool = create_database_tool(operations=["create"], tables=["products"])

# LLM composes:
# 1. Call create_variant_value_tool
# 2. Extract new variant_value_id from result
# 3. Call create_product_tool with reference to new variant_value_id
```

**3. Natural Language Filters**
```python
# Current: Structured filters (dict[str, Any])
filters = {"category": "electronics", "price": {"gte": 100, "lte": 500}}

# Future: Could support natural language filters
filters = "electronics category, price between $100 and $500"
# LLM translates to structured filter internally
```

### Access Control Changes

**Context-Aware Permissions**
```python
# Future: LLM-assisted access control
# Tool provides permission context, LLM reasons about access

class PermissionContext(BaseModel):
    user_role: str
    operation_type: str
    affected_tables: list[str]
    data_sensitivity: Literal["public", "internal", "confidential"]

# LLM-assisted permission check
permission_prompt = f"""
Given this permission context:
- User role: {context.user_role}
- Operation: {context.operation_type}
- Tables: {context.affected_tables}
- Data sensitivity: {context.data_sensitivity}

Company policy:
{company_permission_policy}

Should this operation be allowed? Explain reasoning.
"""

# LLM provides decision + justification
# (Still validated by code, but LLM helps with complex policies)
```

### Business Logic Location

**Stays in Schema Layer + LLM Reasoning**
```python
# Schema metadata provides structure
# LLM reasoning provides intelligence

# Example: Complex business rule
rule = BusinessRule(
    rule_type="validate_pricing",
    trigger="before_update",
    handler="llm_assisted_pricing_validation",
    parameters={
        "max_price_change_percent": 50,
        "reasoning_required": True,
    }
)

# Handler delegates to LLM for complex validation
async def llm_assisted_pricing_validation(operation, parameters):
    """Use LLM to validate complex pricing changes."""
    
    prompt = f"""
    Validate this pricing change:
    - Old price: {operation.old_values['price']}
    - New price: {operation.field_updates['price']}
    - Max allowed change: {parameters['max_price_change_percent']}%
    
    Consider:
    - Historical pricing for this product
    - Competitor pricing
    - Market conditions
    
    Is this change reasonable? Provide reasoning.
    """
    
    response = await llm.generate(prompt)
    
    if not response.approved:
        raise ToolException(f"Pricing change rejected: {response.reasoning}")
```

### Impact on Tool Consolidation Decision

**✅ STRONGLY FAVORS CONSOLIDATED TOOL**

**Why:**
1. **Smarter LLMs prefer simpler interfaces:** One universal tool easier to understand than 10 specialized tools
2. **Better reasoning handles complexity:** O1-level models can orchestrate complex multi-table operations via single tool
3. **Larger context windows:** Can fit entire schema + tool documentation in single prompt
4. **Self-correction:** Better models validate their own plans against schema before execution

**Future architecture (AI evolution):**
```python
# Simplified - LLM handles even more complexity
universal_tool = create_database_tool(
    storage=storage,
    allowed_operations=["create", "read", "update", "delete"],
)

# LLM orchestrates everything
specialist = create_agent(
    tools=[universal_tool],  # Single tool!
    system_prompt="""
    You have access to the complete database schema via get_schema().
    You can perform ANY database operation via execute_database_operation().
    
    Plan complex multi-table operations. Validate your plans before execution.
    Calculate impact analysis from schema and current data.
    Self-correct if operation fails.
    """
)
```

**Conclusion:** AI evolution STRONGLY favors consolidated tool architecture.

---

## Critical Path Scenarios (Must Handle)

Based on architectural impact analysis, scenarios ranked by priority:

### Tier 1: Critical (Must Handle in Phase 2-3)

**1. Scale (10x-100x Data Growth)** ⚠️
- **Impact:** HIGH - Performance degradation at 10K+ products
- **Urgency:** MEDIUM - Currently 64 products, will hit 1K within 6 months
- **Changes:** Add pagination, caching, streaming (implementation cost: 2-3 weeks)
- **Decision Impact:** FAVORS consolidated tool (simpler caching)

**2. Multi-Tenancy (100-1000 Companies)** ❌
- **Impact:** HIGH - Architecture change required (RLS, company_id injection)
- **Urgency:** HIGH - Business model requires multi-tenancy for SaaS
- **Changes:** Database RLS, company context injection, access control (implementation cost: 3-4 weeks)
- **Decision Impact:** NEUTRAL (works for both consolidated and specialized)

**3. New Domains (Inventory, Orders, CRM)** ✅
- **Impact:** HIGH - Business expansion requires new domains
- **Urgency:** HIGH - Inventory domain needed in Q1 2025
- **Changes:** ZERO (schema-driven architecture handles automatically)
- **Decision Impact:** STRONGLY FAVORS consolidated tool

### Tier 2: Important (Handle in Phase 4-5)

**4. External Integrations (Shopify, Meta, Google)** ✅
- **Impact:** MEDIUM - Required for platform expansion
- **Urgency:** MEDIUM - Q2 2025 target
- **Changes:** Add integration tool category (orthogonal to CRUD)
- **Decision Impact:** FAVORS specialized (per-platform tools)

**5. Advanced Workflows (Batch Operations)** ⚠️
- **Impact:** MEDIUM - Performance optimization for bulk operations
- **Urgency:** LOW - Not critical for MVP
- **Changes:** Add batch operation tools + job tracking
- **Decision Impact:** NEUTRAL (hybrid approach)

**6. Compliance & Audit (GDPR, SOC2)** ✅
- **Impact:** MEDIUM - Required for enterprise customers
- **Urgency:** MEDIUM - Q3 2025 target (SOC2 certification)
- **Changes:** Add audit query tools (audit trail already exists)
- **Decision Impact:** STRONGLY FAVORS consolidated tool

### Tier 3: Nice-to-Have (Future Phases)

**7. Real-Time Collaboration** ⚠️
- **Impact:** LOW - Nice UX improvement, not critical
- **Urgency:** LOW - Post-MVP feature
- **Changes:** Optimistic locking, event publishing
- **Decision Impact:** FAVORS consolidated tool

**8. AI Evolution** ✅
- **Impact:** POSITIVE - Better AI makes current architecture MORE effective
- **Urgency:** N/A - External factor (model evolution)
- **Changes:** Potential simplifications (fewer validations)
- **Decision Impact:** STRONGLY FAVORS consolidated tool

---

## Architectural Patterns for Multiple Scenarios

### Pattern 1: Pagination + Caching (Handles Scale)

**Implementation:**
```python
class PaginatedCachedStorage(StorageInterface):
    """Wrapper adding pagination and caching to any storage adapter."""
    
    def __init__(
        self,
        storage: StorageInterface,
        cache: CacheInterface,
        default_page_size: int = 100,
    ):
        self.storage = storage
        self.cache = cache
        self.default_page_size = default_page_size
    
    async def query_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> PaginatedResult:
        """Query with automatic pagination and caching."""
        
        page_size = page_size or self.default_page_size
        
        # Check cache
        cache_key = self._build_cache_key(table, filters, page_token)
        cached = await self.cache.get(cache_key)
        if cached:
            return PaginatedResult.model_validate(cached)
        
        # Cache miss - query database with pagination
        offset = self._decode_page_token(page_token) if page_token else 0
        
        entities = await self.storage.query_entities(
            table,
            filters,
            limit=page_size + 1,  # Fetch one extra to check if more pages
            offset=offset,
        )
        
        # Build paginated result
        has_more = len(entities) > page_size
        result_entities = entities[:page_size] if has_more else entities
        next_token = self._encode_page_token(offset + page_size) if has_more else None
        
        result = PaginatedResult(
            entities=result_entities,
            next_page_token=next_token,
            has_more=has_more,
        )
        
        # Cache result
        await self.cache.set(cache_key, result.model_dump(), ttl=300)
        
        return result
```

**Applies to:** Scale (Scenario 1), New Domains (Scenario 3)

---

### Pattern 2: Row-Level Security + Company Context (Handles Multi-Tenancy)

**Implementation:**
```python
class MultiTenantStorage(StorageInterface):
    """Wrapper adding company isolation to any storage adapter."""
    
    def __init__(
        self,
        storage: StorageInterface,
        company_id_provider: Callable[[], str],
    ):
        self.storage = storage
        self.get_company_id = company_id_provider
    
    async def _ensure_company_context(self):
        """Set Postgres session variable for RLS enforcement."""
        company_id = self.get_company_id()
        await self.storage.execute_sql(
            f"SET app.current_company_id = '{company_id}'"
        )
    
    async def query_entities(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        **kwargs
    ) -> list[dict[str, Any]]:
        """Query with automatic company_id injection."""
        
        # Ensure company context set
        await self._ensure_company_context()
        
        # RLS handles filtering automatically
        # No need to modify filters - database enforces isolation
        return await self.storage.query_entities(table, filters, **kwargs)
    
    async def insert_entity(
        self,
        table: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Insert with automatic company_id injection."""
        
        # Inject company_id into all inserts
        company_id = self.get_company_id()
        data_with_company = {**data, "company_id": company_id}
        
        return await self.storage.insert_entity(table, data_with_company)
```

**Applies to:** Multi-Tenancy (Scenario 2), Compliance (Scenario 7)

---

### Pattern 3: Hybrid Tool Architecture (Handles Heterogeneous Operations)

**Implementation:**
```python
# Base layer: Universal CRUD (for database operations)
database_tool = create_database_tool(
    storage=storage,
    allowed_operations=["create", "read", "update", "delete"],
)

# Integration layer: Platform-specific tools (for API operations)
shopify_tool = create_shopify_sync_tool(credentials_store)
meta_ads_tool = create_meta_ads_tool(credentials_store)

# Batch layer: Long-running operation tools (for bulk operations)
batch_content_tool = create_batch_operation_tool(
    operation_name="generate_content",
    executor=content_generator,
)

# Specialist gets all three layers
specialist = create_agent(
    tools=[
        database_tool,      # CRUD on local database
        shopify_tool,       # Sync to Shopify
        meta_ads_tool,      # Create Meta campaigns
        batch_content_tool, # Bulk content generation
    ]
)
```

**Applies to:** External Integrations (Scenario 4), Advanced Workflows (Scenario 5)

---

## Red Flags (Decisions That Lock Us In)

### 🚩 Red Flag 1: Over-Specialization Too Early

**Risk:**
```python
# DON'T: Create specialized tools before understanding usage patterns
create_product_crud_tool()
create_inventory_crud_tool()
create_order_crud_tool()
create_campaign_crud_tool()
# ... 10 more specialized tools

# Result: 10,000+ LOC of duplicated CRUD logic
# Maintenance nightmare when fixing bugs (fix in 10 places)
```

**Better:**
```python
# DO: Start with universal tool, specialize only when proven necessary
universal_tool = create_database_tool(...)  # 1500 LOC

# Specialize ONLY after identifying hot paths
if performance_monitoring.shows_bottleneck("product_queries"):
    # Add specialized product query cache
    product_query_tool = create_optimized_query_tool(table="products")
```

---

### 🚩 Red Flag 2: Premature Schema Fragmentation

**Risk:**
```python
# DON'T: Create per-domain schema registries too early
product_schema = SchemaRegistry(domain="products")
inventory_schema = SchemaRegistry(domain="inventory")
orders_schema = SchemaRegistry(domain="orders")

# Result: Cannot handle cross-domain operations
# Example: Order contains products + inventory allocation
# Which schema do we use? How do we validate relationships?
```

**Better:**
```python
# DO: Single schema registry with domain organization
enterprise_schema = SchemaRegistry(
    version="v1",
    domains={
        "product_catalog": {...},
        "inventory_management": {...},
        "order_processing": {...},
    }
)

# Supports cross-domain operations naturally
# Example: Order references products (cross-domain relationship)
```

---

### 🚩 Red Flag 3: Ignoring Multi-Tenancy from Day 1

**Risk:**
```python
# DON'T: Build single-tenant, add multi-tenancy later
# Architectural change required (add company_id to 50+ tables)
# Migration nightmare (backfill company_id for existing data)
# RLS policies hard to add retroactively
```

**Better:**
```python
# DO: Design for multi-tenancy even if launching single-tenant
# Add company_id columns from day 1 (defaulting to single company)
# Enable RLS policies early (even if only one company)
# Makes future transition seamless
```

---

### 🚩 Red Flag 4: Tight Coupling to LLM Capabilities

**Risk:**
```python
# DON'T: Assume LLM will always handle complexity correctly
# No validation, trust LLM blindly
result = await execute_database_operation(llm_generated_intent)

# Result: LLM mistakes corrupt database
# No safeguards for partial data, validation errors
```

**Better:**
```python
# DO: Validate LLM output, provide safeguards
_validate_operation_completeness(operations, impact_analysis)
_validate_against_schema(operations, schema)

# Safe to evolve:
# - Current: Strict validation (LLMs make mistakes)
# - Future: Relaxed validation (better LLMs need less hand-holding)
```

---

## Final Recommendation: Evolutionary Approach

Based on comprehensive scenario analysis, recommended architecture evolution:

### Phase 1 (Current): Foundation ✅
- ✅ Universal CRUD tool (proven, production-ready)
- ✅ Dynamic schema-driven architecture
- ✅ Operation-scoped access control
- ✅ Audit logging (compliance-ready)

### Phase 2 (Next 3 Months): Scale + Multi-Tenancy
**Critical path scenarios:**
1. Add pagination + caching (handle 10K+ products)
2. Implement RLS + company context (enable multi-tenancy)
3. Add new domains (inventory, orders) - ZERO tool changes needed ✅

**Tool architecture changes:**
- Keep universal CRUD as foundation
- Add `PaginatedCachedStorage` wrapper
- Add `MultiTenantStorage` wrapper
- No new CRUD tools needed

### Phase 3 (3-6 Months): Integrations + Advanced Workflows
**Important scenarios:**
1. Add platform integration tools (Shopify, Meta, Google)
2. Add batch operation tools (bulk content generation)
3. Add compliance query tools (GDPR export, audit reporting)

**Tool architecture changes:**
- Add integration tool category (specialized per platform)
- Add batch operation tools (long-running workflows)
- Keep universal CRUD for all database operations

### Phase 4+ (6+ Months): Optimization
**Nice-to-have scenarios:**
1. Real-time collaboration (optimistic locking, events)
2. AI evolution (simplifications as models improve)

**Tool architecture changes:**
- Add optimistic locking to universal CRUD
- Potentially simplify as AI improves
- Monitor and adapt based on usage

---

## Decision Matrix: When to Consolidate vs Specialize

Use this matrix to decide for future tool additions:

| Question | Consolidate | Specialize |
|----------|-------------|------------|
| **Is the operation database CRUD?** | ✅ Yes | ❌ No (external API) |
| **Does it follow schema-driven patterns?** | ✅ Yes | ❌ No (custom logic) |
| **Will it be used across multiple domains?** | ✅ Yes | ⚠️ Maybe |
| **Does it have unique business rules?** | ⚠️ Schema-driven rules | ❌ Complex custom rules |
| **Is performance critical for this path?** | ⚠️ Add caching | ✅ Optimize specialized tool |
| **Does it require external API calls?** | ❌ No (database only) | ✅ Yes (platform integration) |
| **Is it a long-running operation?** | ❌ No (synchronous) | ✅ Yes (batch/async) |
| **Does it need different access control?** | ⚠️ Configure existing | ⚠️ Either works |

**Examples:**
- ✅ Consolidate: Product CRUD, Campaign CRUD, Order CRUD (all database operations)
- ✅ Specialize: Shopify Sync, Meta Ads API, Image Processing (external APIs/custom logic)
- ⚠️ Hybrid: Batch Content Generation (use universal CRUD for persistence + specialized batch tool for execution)

---

**End of Scenario Analysis**

**Document Status:** Complete
**Next Steps:** Review findings, discuss architectural direction, plan Phase 2 implementation
**Maintenance:** Update this analysis as new scenarios emerge or requirements change

