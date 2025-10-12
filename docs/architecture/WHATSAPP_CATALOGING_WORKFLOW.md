# WhatsApp-Based Product Cataloging Workflow

This document outlines the design for the Cataloging MVP feature: enabling Indian small business owners to build a product catalog. The current implementation validates the workflow via scripts; WhatsApp integration now supports sandbox testing with HITL approvals. Implementation notes are limited to cataloging; broader agent architecture details remain in `AGENTS_DESIGN.md`.

---

## Architecture (2025-10-08)

**Modular, multi-channel architecture.** See [`WORKFLOW_ORCHESTRATION_REFACTOR.md`](./WORKFLOW_ORCHESTRATION_REFACTOR.md) for complete details.

### Components

- **Webhook**: `entrypoints/whatsapp_webhook.py` - FastAPI webhook (verification, events, routing)
- **Channel Adapter**: `workflows/channels/whatsapp/adapter.py` - WhatsApp-specific (formatting, media, Graph API)
- **Workflow Orchestrator**: `workflows/orchestration/runner.py` - Generic coordination (channel-agnostic)
- **Interrupt Coordinator**: `workflows/orchestration/interrupt_coordinator.py` - HITL handling
- **State Manager**: `workflows/orchestration/state_manager.py` - Approval persistence
- **Recovery Strategy**: `workflows/orchestration/recovery_strategy.py` - Error recovery
- **Project Manager**: `workflows/project_manager.py` - DeepAgent orchestrator (delegates to departments)

### Key Features

- ✅ Multi-channel ready (SMS, Telegram via new adapters)
- ✅ Single Responsibility per component
- ✅ Unit-testable in isolation
- ✅ Clean separation: orchestration ≠ messaging ≠ interrupts

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

1. After specialists produce a cataloging draft, the Department agent attempts `save_product`.
2. `interrupt_before=["save_product"]` pauses execution. `whatsapp_cataloging_runner` sends an approval request via WhatsApp detailing the draft.
3. User replies `approve` / `reject`.
4. Runner resumes the LangGraph thread with the decision. On approval, product is saved and confirmation sent to the user; on rejection, we can extend later to support edits.

---

## 2. Agentic Architecture & Workflow

This workflow will be managed by a generic `ProjectManagerAgent` and a new `Cataloging` department. The system is designed to be context-aware, loading company-specific information at the start of each workflow.

1.  **Entrypoint & Context Injection:**
    -   An `api.py` entrypoint will expose a webhook to receive incoming messages from the WhatsApp Cloud API.
    -   Upon receiving a message, the system will use the user's phone number to look up their associated `company_id`.
    -   It will then fetch the corresponding `company_profile` from the Supabase database.
    -   This `company_profile` object will be passed as initial input to the `ProjectManagerAgent`, making all subsequent actions context-aware.

2.  **`ProjectManagerAgent` (DeepAgent Orchestrator – Roadmap):**
    -   Will be implemented via `deepagents.create_deep_agent` with the cataloging department registered as a sub-agent once readiness checklist is satisfied.
    -   **Intent Analysis:** Filters greetings/noise, recognizes cataloging requests, and routes approval commands back to LangGraph.
    -   **Structured Delegation:** Passes normalized text, media URLs, and `CompanyProfile` context into the cataloging department.
    -   **Self-Correction:** Applies recursion-limit guards and surfaces failures to human support rather than looping.

3.  **`CatalogingDept` Agent (Department Head):**
    -   **Purpose:** To manage the analysis of unstructured user messages.
    -   **Plan:** When it receives a message, it will delegate to the appropriate specialist based on the content type.
        -   If the message contains images -> `ImageAnalysisSpecialist`.
        -   If the message contains text -> `TextAnalysisSpecialist`.

4.  **Specialist Agents:**
    -   **`ImageAnalysisSpecialist`:**
        -   **Purpose:** To extract product information from an image.
        -   **Tools:** It will use a multimodal LLM (like gpt-4.1-nano-2025-04-14 or Gemini) via our `integrations` layer.
        -   **Output:** Returns a structured JSON object with fields like `product_category`, `color`, `pattern`, `description_from_image`.
    -   **`TextAnalysisSpecialist`:**
        -   **Purpose:** To extract product information from a text message.
        -   **Tools:** Uses an LLM to parse the user's text and extract entities like `price`, `sizes`, `colors`, etc.
        -   **Output:** Returns a structured JSON object with the extracted fields.

---

## 3. Required New Components

This feature requires the creation of several new components in our project structure.

1.  **`integrations/communication/whatsapp_client.py`:** A new adapter to handle the specifics of sending and receiving messages via the WhatsApp Business Cloud API.
2.  **`tools/communication_tools.py`:** Provides `send_whatsapp_message` (factory helper will be added alongside the Project Manager rollout).
3.  **`schemas/models.py`:** Will need a new Pydantic model for a `Product` (e.g., with fields `id`, `name`, `description`, `price`, `sizes`, `colors`, `image_urls`).
4.  **Supabase Schema:** A new `products` table in our database to store the catalog information.
5.  **`workflows/product_ingestion.py`:** Planned home for the `Project Manager` agent (post-MVP).
6.  **`departments/cataloging/`:** Future directory for the full 3-layer structure. For now, `cataloging_department.py` implements the department with direct tool orchestration as an interim step.

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
| `agents/scripts/debug_whatsapp_payload.py` | List/inspect captured JSON events | `uv run python agents/scripts/debug_whatsapp_payload.py --list` |
| `agents/scripts/debug_whatsapp_event.py` | Summarise an event and (optionally) download its media | `uv run python agents/scripts/debug_whatsapp_event.py --download --verbose` |
| `agents/scripts/run_whatsapp_server.py` | Operate webhook server / tunnels (`serve`, `ngrok`, `cloudflare`) | `uv run python agents/scripts/run_whatsapp_server.py serve --port 8000` |

These tools support the Codespace workflow documented earlier: start the server, expose port 8000, send a WhatsApp message, inspect payloads, download media, then re-enable the agent.

### 4.3 Automated Test Plan (Planned Work)

- **Webhook replay tests:** Use `TestClient` to POST recorded `messages` payloads and assert the handler saves events and calls the runner exactly once. Separate tests confirm `statuses` payloads return `{"status": "ignored"}`.
- **Media client unit tests:** Mock Graph API responses (e.g., with `respx`/`httpx_mock`) to validate metadata parsing, HTTP headers, and file suffix inference.
- **Replay harness tests:** Exercise `debug_whatsapp_event.py` with fixture files to ensure summaries and downloads succeed without regressions.
- **Optional integration smoke test:** Run FastAPI in-process with `enable_agent=False`, inject a synthetic payload, and assert the diagnostic response is returned.

Once implemented, these tests keep the adapter reliable across Codespaces and CI, and they align with our Hexagonal strategy—each port is validated independently before the LLM layer is involved.
