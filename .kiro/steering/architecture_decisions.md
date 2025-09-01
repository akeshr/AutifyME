---
inclusion: always
---

# AutifyME Architecture Decisions & Standards

This document captures key architectural decisions made for AutifyME to ensure consistency across all future development.

## Core Architecture Principles

### 1. Three-Layer Architecture (MANDATORY)
```
Agents (Orchestration) → Specialists (Expertise) → Tools (Execution)
```

**Decision**: Always maintain clear separation between:
- **Agents**: LangGraph workflows that orchestrate business processes
- **Specialists**: LangChain agents providing domain expertise  
- **Tools**: Deterministic functions with predictable inputs/outputs

**Rationale**: Enables reusability, testability, and clear responsibility boundaries.

### 2. Model Organization (MANDATORY)
**Decision**: Split models by domain, never use monolithic model files.

**Structure**:
```
src/core/models/
├── __init__.py          # Imports all for convenience
├── base.py              # System-wide common models
├── {domain}.py          # Domain-specific models (cataloging, marketing, etc.)
├── workflow.py          # Workflow orchestration models
└── audit.py             # Logging and compliance models
```

**Rationale**: Prevents large unmaintainable files, enables domain-focused development.

### 3. Technology Stack (FIXED)
- **AI Framework**: LangGraph + LangChain + LangSmith
- **Package Manager**: uv (not pip)
- **Database**: Supabase (PostgreSQL + pgvector)
- **Storage**: Google Drive API for assets
- **Language**: Python 3.11+
- **Validation**: Pydantic v2

**Rationale**: Optimized for speed, cost-effectiveness, and modern Python practices.

## Code Organization Standards

### 1. Directory Structure (MANDATORY)
```
src/
├── agents/{domain}/     # One folder per business domain
├── specialists/{type}/  # Reusable expertise modules
├── tools/{category}/    # Deterministic functions grouped by purpose
├── core/               # Framework components
├── workflows/          # End-to-end process definitions
└── api/                # REST API endpoints
```

### 2. Import Patterns (MANDATORY)
```python
# Preferred - absolute imports from project root
from src.core.models import ProductFeatures, WorkflowState
from src.core.models.cataloging import ProductDraft

# Alternative - relative imports (use sparingly)
from ...core.models.cataloging import ProductFeatures

# Avoid - mixing import styles in same file
```

### 3. Error Handling (MANDATORY)
**All tools and agents MUST**:
- Use try/except blocks for external API calls
- Return structured error responses, never crash
- Log errors with context for debugging
- Provide fallback behavior when possible

```python
try:
    result = external_api_call()
    return success_response(result)
except Exception as e:
    log_error(f"Operation failed: {e}", context={"input": input_data})
    return fallback_response()
```

## Data Management Standards

### 1. State Management (MANDATORY)
- All workflow state MUST be stored in `WorkflowState` model
- State transitions MUST be logged in audit trail
- State MUST be recoverable after system restart

### 2. Multi-Tenancy (MANDATORY)
- Every data model MUST include `business_id` field
- Database queries MUST filter by business_id
- File storage MUST be isolated per business

### 3. Human-in-the-Loop (MANDATORY)
- High-risk operations MUST require approval
- Approval requests MUST use `ApprovalRequest` model
- Workflows MUST pause at approval nodes, not skip them

## Performance & Cost Standards

### 1. AI Model Usage (MANDATORY)
- Use model routing: simple tasks → cheaper models
- Cache results for 24 hours minimum where appropriate
- Set token limits on all AI calls
- Track costs in `CostEntry` model

### 2. Database Optimization (MANDATORY)
- Use indexes on frequently queried fields
- Implement connection pooling
- Use batch operations for bulk data
- Monitor query performance

## Security & Compliance Standards

### 1. Data Protection (MANDATORY)
- Never log sensitive data (API keys, personal info)
- Use Credential Manager for all secrets (never direct env access)
- Implement Row Level Security in Supabase
- Encrypt data at rest and in transit
- Centralize credential validation and rotation

### 2. Audit Trail (MANDATORY)
- Log ALL system actions using `AuditEntry` model
- Include actor, action, resource, and timestamp
- Store audit logs separately from business data
- Make audit logs immutable

## Development Workflow Standards

### 1. Testing Requirements (MANDATORY)
- Unit tests for all tools
- Integration tests for specialists
- End-to-end tests for complete workflows
- Mock external APIs in tests

### 2. Code Quality (MANDATORY)
- Use type hints on all functions
- Format with Black
- Lint with flake8
- Type check with mypy
- Document all public methods

### 3. Deployment Standards (MANDATORY)
- Use Docker for containerization
- Environment-specific configuration
- Health checks for all services
- Rollback capability for all deployments

## Anti-Patterns (NEVER DO THIS)

### ❌ Monolithic Files
- Never put all models in one file
- Never create giant utility modules
- Split by domain/responsibility

### ❌ Direct Database Access
- Never bypass the Database Specialist
- Never write raw SQL in agents or tools
- Always use Database Specialist for data operations
- Never create multiple database clients

### ❌ Hardcoded Values
- Never hardcode API endpoints
- Never hardcode business rules
- Use configuration files and environment variables

### ❌ Synchronous Blocking
- Never make synchronous calls to external APIs in workflows
- Use async/await patterns
- Implement proper timeouts

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-09-01 | Split models by domain | Maintainability and scalability |
| 2025-09-01 | Use uv instead of pip | 10-100x faster dependency management |
| 2025-09-01 | Three-layer architecture | Clear separation of concerns |
| 2025-09-01 | Database Specialist pattern | Centralized, intelligent database operations |
| 2025-09-01 | Centralized credential management | Secure, reusable credential handling |

## Future Considerations

When adding new domains (marketing, HR, billing):
1. Create new model file in `src/core/models/{domain}.py`
2. Create agent folder in `src/agents/{domain}/`
3. Add domain-specific tools in `src/tools/{domain}/`
4. Update this steering document with domain-specific decisions