---
inclusion: always
---

# Credential Patterns - MANDATORY RULES

**MANDATORY** credential patterns for AutifyME. All code MUST follow these rules exactly.

## ❌ FORBIDDEN PATTERNS

- **NO** provider names in function arguments: `def tool(provider: str)`
- **NO** generic credential classes: `DatabaseCredentials`, `AICredentials`
- **NO** complex getter functions: `get_supabase_credentials()`
- **NO** global config imports in services
- **NO** provider names in tool documentation

## ✅ REQUIRED PATTERNS

### Service Classes
- **Name after provider**: `Supabase`, `OpenAI` (not `SupabaseCredentials`)
- **Include `@classmethod def load(cls)`** to load from credential manager
- **Add service-specific methods**: `create_client()`, etc.

### Service Getters
- **Simple names**: `supabase()`, `openai()` (not `get_supabase_credentials()`)
- **Return cached instances** after first call
- **No arguments** - services configure themselves

### Tools
- **First parameter = service object**: `database: DatabaseService`
- **Use type unions**: `DatabaseService`, `AIService`, `StorageService`
- **Generic documentation**: "Database service instance" (not provider lists)

### Storage & Clients
- **Service-specific functions**: `store_openai_key()`, `create_openai_client()`
- **NO generic functions**: Never `store_api_key(provider, ...)` or `create_ai_client(provider, ...)`

## 🏗️ ARCHITECTURE RULES

### Service Pattern
1. **Service class** with provider name + `load()` classmethod
2. **Cached getter function** with lowercase service name
3. **Service-specific storage** function
4. **Service-specific client** function (if needed)

### Tool Pattern
1. **First parameter = service object** (never provider string)
2. **Use service methods** directly
3. **Return structured responses** with success/error
4. **Generic documentation** without provider names

## � IMPLEcMENTATION CHECKLIST

### Adding New Services
1. Create service class with provider name
2. Add `@classmethod def load(cls)` 
3. Add cached getter function
4. Add service-specific storage function
5. Add service-specific client function (if needed)
6. Add to type unions
7. Update `__init__.py` exports

### Creating Tools
1. First parameter = service object
2. Use appropriate service type hint
3. Work with service methods
4. Generic documentation only

## ✅ VALIDATION RULES

Before submitting credential code, verify:
- ❌ No provider names in function arguments
- ✅ Service classes named after provider (not "Credentials")  
- ✅ Simple getter functions (no "get_" prefix)
- ✅ Tools take service objects, not provider names
- ✅ No global config imports in services
- ✅ Cached service instances
- ✅ Service-specific storage/client functions
- ✅ Generic tool documentation only

## 🎯 USAGE EXAMPLES

**Correct Usage:**
```python
db = supabase()  # Simple getter
await create_record(database=db, ...)  # Service object
store_openai_key("sk-...")  # Service-specific storage
client = create_openai_client()  # Service-specific client
```

**Forbidden Usage:**
```python
get_supabase_credentials()  # ❌ Complex getter
create_record(provider="supabase", ...)  # ❌ Provider argument
store_api_key("openai", "sk-...")  # ❌ Generic storage
create_ai_client(provider="openai")  # ❌ Generic client
```

These patterns are **MANDATORY** for all credential-related code.