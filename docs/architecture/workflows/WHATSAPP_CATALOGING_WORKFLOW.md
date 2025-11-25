# WhatsApp-Based Product Cataloging Workflow

**Created:** September 30, 2025

This document outlines the design for the Cataloging MVP feature: enabling Indian small business owners to build a product catalog. The current implementation validates the workflow via scripts; WhatsApp integration now supports sandbox testing with HITL approvals. Implementation notes are limited to cataloging; broader agent architecture details remain in `AGENTS_DESIGN.md`.

---

## Architecture

**Native LangGraph HITL with 2-level DeepAgents hierarchy.**

### Components

- **Webhook**: `entrypoints/whatsapp_webhook.py` - FastAPI webhook (verification, routing)
- **Channel Adapter**: `integrations/communication/whatsapp_client.py` - WhatsApp Graph API client
- **Workflow Runner**: `workflows/orchestration/runner.py` - Generic orchestrator (PM invocation, HITL detection)
- **Approval Analyzer**: `workflows/approval_analyzer.py` - HITL interpretation with structured output
- **Project Manager**: `workflows/project_manager.py` - DeepAgent (delegates to specialists via SubAgents)
- **Cataloging Specialist**: `specialists/cataloging_specialist.py` - SubAgent (uses tools directly: image_analysis, save_product)
- **Tools**: `tools/` - Utility functions (image_analysis_tool, storage_tools)

### Key Features

- ✅ Native LangGraph interrupt handling (no custom coordinators)
- ✅ 2-Level DeepAgents hierarchy (**PM → Specialist → Tools**)
- ✅ Structured approval interpretation (BatchApprovalResponse)
- ✅ Type-safe via Pydantic throughout

---

## 1. User Experience (UX) Flow

The entire user experience is conversational and happens within WhatsApp.

1.  **Initiation:** The user sends one or more images of a product to the AutifyME WhatsApp number.
2.  **Information Extraction:** The system replies: *"Thanks! I've received 3 images. I see a [Product Category, e.g., 'kurta']. Working on drafting the product details now..."*
3.  **Follow-up Questions:** If details are missing, the system asks clarifying questions.
    -   *"What is the price for this item?"*
    -   *"Do you have it in other sizes or colors?"*
    -   *"Can you give me a short description?"*
4.  **Draft for Approval (HITL):** Once enough data is gathered, the system sends a formatted summary for approval.
    -   **Product Name:** Blue Printed Kurta Set
    -   **Price:** ₹1299
    -   **Sizes:** M, L, XL
    -   **Description:** A beautiful blue kurta perfect for festive occasions.
    -   **Images:** [Image 1], [Image 2], [Image 3]
    -   
    -   *"Here is the product draft. Shall I add this to your catalog? (Yes/No)"*
5.  **Confirmation:** Upon receiving "Yes," the system replies: *"Great! The product has been added to your catalog. You can view your full catalog at [link]."*

### HITL Interaction

1. Specialist attempts `save_product` after synthesizing product draft
2. `tool_configs` (configured on specialist) triggers native LangGraph interrupt (HumanInTheLoopMiddleware)
3. Runner detects `__interrupt__` in event stream, extracts draft from interrupt value
4. Runner sends approval request to user via channel
5. User responds (approve/reject/edits)
6. **Approval analyzer interprets response** → `BatchApprovalResponse` (structured Pydantic output)
   - Handles batch approvals (N responses for N interrupts)
   - Type-safe interpretation (no text parsing)
   - Returns structured approval/edit/reject decisions
7. Runner builds LangGraph `Command` from structured response
8. Runner invokes PM with Command to resume workflow
9. Tool executes, returns CatalogingResult

---

## 2. Agentic Architecture & Workflow

This workflow is managed by a generic `ProjectManagerAgent` that delegates directly to specialists. The system is context-aware, loading company-specific information at the start of each workflow.

1.  **Entrypoint & Context Injection:**
    -   An `api.py` entrypoint exposes a webhook to receive incoming messages from the WhatsApp Cloud API.
    -   Upon receiving a message, the system uses the user's phone number to look up their associated `company_id`.
    -   It fetches the corresponding `company_profile` from the Supabase database.
    -   This `company_profile` object is passed as initial input to the `ProjectManagerAgent`, making all subsequent actions context-aware.

2.  **`ProjectManagerAgent` (Top-Level Orchestrator):**
    -   Implemented via `deepagents.create_deep_agent` with specialists registered as SubAgents.
    -   **Intent Analysis:** Filters greetings/noise, recognizes cataloging requests, and detects pending interrupts for workflow resumption.
    -   **Direct Delegation:** Passes raw platform messages to cataloging specialist with complete context.
    -   **Self-Correction:** Applies recursion-limit guards and surfaces failures to human support rather than looping.

3.  **`CatalogingSpecialist` (Domain Expert):**
    -   **Purpose:** Transform user descriptions and images into complete Product models.
    -   **Implementation:** Created via `create_agent()` with tools attached.
    -   **Tools:**
        -   `image_analysis_tool`: Analyzes product images using Vision API → returns `ImageAnalysisResult`
        -   `save_product`: Persists product to database (HITL-enabled via `tool_configs`)
    -   **Workflow:** Adaptive execution based on available data:
        -   If images present → call `image_analysis_tool(image_path)` for visual extraction
        -   Synthesize data from user text + image insights into Product model
        -   Call `save_product(name, price, ...)` → triggers HITL approval
    -   **Output:** `CatalogingResult` with success status, product_id, and message

### Error Handling & Resilience

- **External API Errors:** Classified via `classify_api_error()` to detect transient vs permanent failures
- **Retry Strategy:** Transient errors (timeout, rate limit, connection) retried up to 3 times with exponential backoff
- **Thread Safety:** Concurrent webhook invocations safely tracked via OutcomeTracker with locks
- **Idempotency:** Duplicate messages raise error immediately (fail-closed design) for better observability

---

## 3. Required Components

This feature uses the following components:

1.  **`integrations/communication/whatsapp_client.py`:** Adapter to handle sending and receiving messages via the WhatsApp Business Cloud API.
2.  **`tools/communication_tools.py`:** Provides `send_whatsapp_message`.
3.  **`schemas/models.py`:** Pydantic model for `Product` (fields: `id`, `name`, `description`, `price`, `sizes`, `colors`, `image_urls`).
4.  **Supabase Schema:** `products` table in database to store catalog information.
5.  **`workflows/project_manager.py`:** Project Manager agent with specialist delegation.
6.  **`specialists/cataloging_specialist.py`:** Cataloging specialist with image_analysis_tool and save_product tools.

## Implementation Notes

- Temporary media files are stored on disk (`tempfile.NamedTemporaryFile`) and deleted after processing. Future enhancement: upload to Supabase storage for persistence.
- Resume mechanism uses the checkpointer thread ID `whatsapp:{phone_number}` so conversation history is maintained.
- Approval commands currently support `approve` and `reject`. Extend runner to handle structured edits when the workflow design is finalized.

---

## 4. Diagnostics & Test Automation Roadmap (2025-10)

To honour our Architecture-First and Context-Efficient principles, we instrumented the WhatsApp adapter so each stage can be validated without invoking the LLM stack. This section documents the current tooling and the planned automated tests that will graduate our manual checks into repeatable scripts.

### 4.1 Runtime Instrumentation

- **Payload capture:** `entrypoints/whatsapp_webhook.py` persists every incoming event under `tmp/whatsapp_events/` and logs the file path. This guarantees lossless replay during debugging sessions (Codespaces or local).
- **Media diagnostics:** `WhatsAppMediaClient` logs metadata fetch/download status codes with verbose httpx tracing (`--verbose` flag in the helper script). This isolates token/scope issues before cataloging runs.
- **Agent toggle:** `WhatsAppCatalogingRunner(enable_agent=False)` pauses the LangGraph workflow so we can focus on the adapter. Re-enable once media handling is stable.

### 4.2 Debug Scripts (Manual Workflow)

| Script | Purpose | Example |
| --- | --- | --- |
| `tests/scripts/debug_whatsapp_payload.py` | List/inspect captured JSON events | `uv run python tests/scripts/debug_whatsapp_payload.py --list` |
| `tests/scripts/debug_whatsapp_event.py` | Summarise an event and (optionally) download its media | `uv run python tests/scripts/debug_whatsapp_event.py --download --verbose` |
| `tests/scripts/run_whatsapp_server.py` | Operate webhook server / tunnels (`serve`, `ngrok`, `cloudflare`) | `uv run python tests/scripts/run_whatsapp_server.py serve --port 8000` |

These tools support the Codespace workflow documented earlier: start the server, expose port 8000, send a WhatsApp message, inspect payloads, download media, then re-enable the agent.

### 4.3 Automated Test Plan (Planned Work)

- **Webhook replay tests:** Use `TestClient` to POST recorded `messages` payloads and assert the handler saves events and calls the runner exactly once. Separate tests confirm `statuses` payloads return `{"status": "ignored"}`.
- **Media client unit tests:** Mock Graph API responses (e.g., with `respx`/`httpx_mock`) to validate metadata parsing, HTTP headers, and file suffix inference.
- **Replay harness tests:** Exercise `debug_whatsapp_event.py` with fixture files to ensure summaries and downloads succeed without regressions.
- **Optional integration smoke test:** Run FastAPI in-process with `enable_agent=False`, inject a synthetic payload, and assert the diagnostic response is returned.

Once implemented, these tests keep the adapter reliable across Codespaces and CI, and they align with our Hexagonal strategy—each port is validated independently before the LLM layer is involved.
