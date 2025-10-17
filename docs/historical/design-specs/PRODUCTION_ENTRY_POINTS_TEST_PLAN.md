# Production Entry Points Test Plan

**Status**: In Progress
**Date**: 2025-10-15
**Target**: Achieve production-grade coverage for critical entry points before WhatsApp deployment

---

## Executive Summary

Current e2e tests validate core orchestration (PM → Departments → HITL) at 100% coverage, but production entry points remain untested, creating deployment risk. This plan addresses the critical 0-30% coverage gap in webhook handling, media pipeline, and vision analysis — the three components that handle all inbound WhatsApp traffic.

**Priority**: [CRITICAL] - Blocks production deployment

---

## Coverage Targets

| Component | Current | Target | Gap | Priority |
|-----------|---------|--------|-----|----------|
| **WhatsApp Webhook** | 0% | 60% | +60% | P0 (CRITICAL) |
| **Media Client** | 28% | 60% | +32% | P0 (CRITICAL) |
| **Image Analysis Specialist** | 30% | 70% | +40% | P0 (CRITICAL) |
| **Interrupt Coordinator** | 73% | 85% | +12% | P1 (High) |
| **Runner Error Recovery** | 71% | 75% | +4% | P1 (High) |

---

## 1. WhatsApp Webhook Tests (0% → 60%)

**File**: `agents/src/autifyme_agents/entrypoints/whatsapp_webhook.py` (268 lines, 0% covered)

### Critical Paths to Cover

**A. Webhook Verification** (`/webhook GET`):
- ✅ Valid verification request → Return challenge (Line 104-113)
- ✅ Invalid token → 403 error
- ✅ Missing parameters → 403 error

**B. Message Reception** (`/webhook POST`):
- ✅ Text message → Extracted and processed (Line 199-200)
- ✅ Image with caption → Both extracted (Line 201-204)
- ✅ Image without caption → Media ID only (Line 201-204)
- ✅ Video with caption → Both extracted (Line 205-208)
- ✅ Document with caption → Both extracted (Line 209-212)
- ✅ Audio/voice (no caption) → Media ID only (Line 213-216)

**C. Event Filtering**:
- ✅ Status update events → Ignored (Line 143-149)
- ✅ Non-message events → Ignored (Line 150-154)
- ✅ Multiple messages in payload → All processed (Line 158)

**D. Idempotency & Error Handling**:
- ✅ Duplicate message_id → Skipped (DB check) (Line 177-187)
- ✅ Missing message_id or sender → Skipped with warning (Line 165-170)
- ✅ WorkflowRunner exception → Logged, continue processing (Line 250-262)
- ✅ GeneratorExit (timeout) → Logged, continue (Line 237-249)

**E. Observability**:
- ✅ Event persistence to `/tmp/whatsapp_events/` (Line 83-89)
- ✅ Structured logging with metadata (Line 218-230)

### Test Structure

```python
# tests/integration/test_whatsapp_webhook.py

from fastapi.testclient import TestClient
from autifyme_agents.entrypoints.whatsapp_webhook import app

class TestWebhookVerification:
    """Test GET /webhook verification endpoint."""

class TestMessageReception:
    """Test POST /webhook message processing."""

class TestIdempotency:
    """Test duplicate message handling."""

class TestErrorRecovery:
    """Test workflow error scenarios."""
```

### Mock Strategy

- Mock `WorkflowRunner.handle_message` to test webhook layer in isolation
- Mock `storage.check_and_mark_message_processed` for idempotency tests
- Use FastAPI `TestClient` for HTTP layer testing
- Mock file system for event persistence tests

---

## 2. Media Client Tests (28% → 60%)

**File**: `agents/src/autifyme_agents/integrations/communication/whatsapp_media_client.py` (139 lines, 28% covered)

### Critical Paths to Cover

**A. Media URL Fetching**:
- ✅ Valid media_id → Returns URL and mime_type (Line 40-58)
- ❌ HTTP 404 → Raises HTTPStatusError (Line 46-51) **[UNCOVERED]**
- ❌ HTTP 403 → Raises HTTPStatusError **[UNCOVERED]**
- ❌ Network timeout → Raises timeout error (Line 43) **[UNCOVERED]**
- ❌ Malformed JSON response → Raises error **[UNCOVERED]**

**B. Media Download**:
- ✅ Valid download → Returns (path, bytes, mime_type) (Line 60-101)
- ❌ Download HTTP error → Raises HTTPStatusError (Line 78-83) **[UNCOVERED]**
- ❌ Network timeout → Raises timeout error (Line 75) **[UNCOVERED]**
- ❌ /tmp write failure → Returns bytes only (Line 95-99) **[UNCOVERED]**
- ❌ Large file handling (>10MB) → Succeeds **[UNCOVERED]**

**C. MIME Type Mapping**:
- ✅ Common image types → Correct extensions (Line 110-138)
- ❌ Uncommon/unknown MIME → Empty suffix (Line 106) **[UNCOVERED]**
- ❌ None MIME type → Empty suffix (Line 106) **[UNCOVERED]**

### Test Structure

```python
# tests/unit/test_whatsapp_media_client.py

import httpx
import pytest
from unittest.mock import Mock, patch

class TestMediaURLFetching:
    """Test get_media_url with various HTTP scenarios."""

class TestMediaDownload:
    """Test download_media with bytes and path handling."""

class TestMIMETypeMapping:
    """Test _derive_suffix for all supported types."""

class TestErrorConditions:
    """Test network failures and edge cases."""
```

### Mock Strategy

- Mock `httpx.get` for API responses
- Use `respx` library for httpx request mocking
- Test with real bytes (small test images in fixtures)
- Mock filesystem write failures for serverless scenarios

---

## 3. Image Analysis Specialist Tests (30% → 70%)

**File**: `agents/src/autifyme_agents/specialists/image_analysis_specialist.py` (308 lines, 30% covered)

### Critical Paths to Cover

**A. Base64 Encoding**:
- ✅ Bytes to data URI → Valid base64 (Line 22-35)
- ❌ File path to data URI → Valid base64 (Line 38-71) **[UNCOVERED]**
- ❌ File not found → Raises FileNotFoundError (Line 55-56) **[UNCOVERED]**
- ❌ Unknown file extension → Defaults to image/jpeg (Line 60-66) **[UNCOVERED]**

**B. Specialist Invocation**:
- ✅ With image_bytes → Returns ImageAnalysisResult (Line 107-178)
- ❌ With image_url (HTTPS) → Returns ImageAnalysisResult (Line 136-142) **[UNCOVERED]**
- ❌ With image_url (data URI) → Returns ImageAnalysisResult (Line 136-142) **[UNCOVERED]**
- ❌ With image_url (file path) → Converts and returns (Line 138-139) **[UNCOVERED]**
- ❌ With company_profile (Pydantic) → Uses brand context (Line 147-149) **[UNCOVERED]**
- ❌ With company_profile (dict) → Uses brand context (Line 151-153) **[UNCOVERED]**
- ❌ No company_profile → Uses defaults (Line 154-156) **[UNCOVERED]**
- ❌ Neither image_url nor image_bytes → Raises ValueError (Line 140-141) **[UNCOVERED]**

**C. Graph Wrapper** (for DeepAgents integration):
- ❌ Extract file path from delegation message → Unix path (Line 236-250) **[UNCOVERED]**
- ❌ Extract file path from delegation message → Windows path (Line 236-250) **[UNCOVERED]**
- ❌ No file path in message → Raises ValueError (Line 252-257) **[UNCOVERED]**
- ❌ File doesn't exist → Raises FileNotFoundError (Line 264-268) **[UNCOVERED]**
- ❌ Successful analysis → Returns state with AIMessage (Line 292-304) **[UNCOVERED]**

### Test Structure

```python
# tests/unit/test_image_analysis_specialist.py

from autifyme_agents.specialists.image_analysis_specialist import (
    _encode_bytes_to_data_uri,
    _encode_image_to_data_uri,
    image_analysis_specialist_invoke,
    create_image_analysis_specialist_graph,
)

class TestBase64Encoding:
    """Test image encoding utilities."""

class TestSpecialistInvocation:
    """Test image_analysis_specialist_invoke with various inputs."""

class TestGraphWrapper:
    """Test create_image_analysis_specialist_graph for DeepAgents."""

class TestCompanyProfileHandling:
    """Test brand context injection."""
```

### Mock Strategy

- Mock `get_llm()` to return fake vision model
- Mock vision model `.invoke()` to return structured output
- Use real small test images (1x1 pixel JPEG/PNG) in fixtures
- Mock filesystem for graph wrapper tests

---

## 4. Interrupt Coordinator Tests (73% → 85%)

**File**: `agents/src/autifyme_agents/core/interrupt_coordinator.py`

### Missing Coverage (Estimated Lines)

**Based on 73% coverage, likely uncovered**:
- Multi-interrupt timeout scenarios
- Interrupt state transitions edge cases
- Approval conflict resolution
- Checkpoint state recovery

### Test Additions Needed

```python
# tests/unit/test_interrupt_coordinator.py (extend existing)

class TestMultiInterruptScenarios:
    """Test handling multiple simultaneous interrupts."""

class TestTimeoutHandling:
    """Test interrupt timeout and expiry."""

class TestStateTransitions:
    """Test all valid/invalid state transitions."""
```

---

## 5. Runner Error Recovery Tests (71% → 75%)

**File**: `agents/src/autifyme_agents/workflows/orchestration/runner_v2.py` (approx line 448-469, 513-531)

### Missing Coverage (Estimated Paths)

**Based on 71% coverage, likely uncovered**:
- State persistence on crash
- Resume from checkpoint after error
- Department failure cascade handling
- Tool exception propagation

### Test Additions Needed

```python
# tests/integration/test_runner_error_recovery.py (new file)

class TestStateRecovery:
    """Test checkpoint restore after crash."""

class TestDepartmentFailures:
    """Test handling of department-level errors."""

class TestToolExceptions:
    """Test tool error propagation and recovery."""
```

---

## Implementation Sequence

### Phase 1: Production Entry Points (P0 - Week 1)
1. ✅ **Day 1-2**: Webhook tests → 60% coverage
2. ✅ **Day 2-3**: Media client tests → 60% coverage
3. ✅ **Day 3-4**: Image specialist tests → 70% coverage
4. ✅ **Day 4**: Integration smoke test (webhook → media → vision end-to-end)

### Phase 2: Resilience (P1 - Week 2)
5. ✅ **Day 5-6**: Interrupt coordinator → 85% coverage
6. ✅ **Day 6-7**: Runner error recovery → 75% coverage

---

## Success Criteria

**Deployment Readiness**:
- ✅ All P0 tests passing in CI
- ✅ Webhook handles all WhatsApp event types correctly
- ✅ Media download failures don't crash workflow
- ✅ Vision analysis errors gracefully degrade
- ✅ Duplicate messages never processed twice
- ✅ Worker timeouts don't lose message processing
- ✅ Overall coverage: 63% → 73% (+10 percentage points)

**Quality Gates**:
- Zero flaky tests
- All tests isolated (no external API calls)
- Mock strategy documented
- Test execution <3 minutes

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Vision model mocking complex | Tests may not catch real API issues | Add integration test flag for optional real API testing |
| Webhook idempotency DB-dependent | Tests need real Supabase | Use mock storage interface as other tests do |
| Media download tests slow | CI timeout | Use small 1x1 pixel test images |
| /tmp write failures on Windows | Test environment inconsistency | Mock filesystem writes, test bytes-only path |

---

## Follow-up Work (Post-Deployment)

**P2 (Nice-to-have)**:
- HITL approval rejection flows (currently soft-fails)
- Multi-user concurrent access tests
- Long-running workflow stress tests
- Storage adapter failure modes (Supabase at 49%)
- WhatsApp channel adapter (27% coverage)

**P3 (Technical debt)**:
- Fix Pydantic v2 deprecation warnings
- Register pytest markers (integration, unit, e2e)
- Convert e2e test return values to assertions
- Fix flaky `test_department_parallel_interrupts` timing
