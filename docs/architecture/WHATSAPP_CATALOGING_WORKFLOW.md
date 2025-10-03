# WhatsApp-Based Product Cataloging Workflow

This document outlines the design for the Cataloging MVP feature: enabling Indian small business owners to build a product catalog. The current implementation validates the workflow via scripts; WhatsApp integration now supports sandbox testing with HITL approvals. Implementation notes are limited to cataloging; broader agent architecture details remain in `AGENTS_DESIGN.md`.

---

## Architecture Snapshot (2025-10)

- **Webhook Entry**: `FastAPI` app in `entrypoints/whatsapp_webhook.py` handles GET verification, POST events, and approval routing
- **Workflow Runner**: `workflows/whatsapp_cataloging_runner.py` orchestrates cataloging runs, media fetching, and HITL resumes
- **Messaging Adapter**: `WhatsAppClient` wraps Facebook Graph v23 send endpoint
- **Media Adapter**: `WhatsAppMediaClient` fetches media IDs and downloads to temporary files
- **Tooling**: `send_whatsapp_message` in `tools/communication_tools.py`
- **HITL Strategy**: `create_cataloging_department(... interrupt_before=["save_product"])` pauses before writes; resume handled via WhatsApp replies

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

2.  **`ProjectManagerAgent` (The "Deep" Orchestrator) – Roadmap:**
    -   This is the top-level, generic orchestrator for the entire system. Implementation begins after Cataloging MVP validation.
    -   **Intent Analysis:** It will analyze raw input (images and text) to determine the goal (e.g., `create_new_product`, `update_inventory`).
    -   **Dynamic Planning with Reflection:** It will create a multi-step plan (DAG) to achieve the goal. Before execution, it reflects on the plan for completeness and opportunities for parallelism.
    -   **Orchestration:** For this workflow, it will delegate tasks to the `CatalogingDept`, manage the conversational flow (asking for missing info), handle the HITL approval step, and ensure the final data is saved.
    -   **Self-Correction:** It will catch errors from sub-agents and dynamically replan to recover from failures.

3.  **`CatalogingDept` Agent (Department Head):**
    -   **Purpose:** To manage the analysis of unstructured user messages.
    -   **Plan:** When it receives a message, it will delegate to the appropriate specialist based on the content type.
        -   If the message contains images -> `ImageAnalysisSpecialist`.
        -   If the message contains text -> `TextAnalysisSpecialist`.

4.  **Specialist Agents:**
    -   **`ImageAnalysisSpecialist`:**
        -   **Purpose:** To extract product information from an image.
        -   **Tools:** It will use a multimodal LLM (like GPT-4o or Gemini) via our `integrations` layer.
        -   **Output:** Returns a structured JSON object with fields like `product_category`, `color`, `pattern`, `description_from_image`.
    -   **`TextAnalysisSpecialist`:**
        -   **Purpose:** To extract product information from a text message.
        -   **Tools:** Uses an LLM to parse the user's text and extract entities like `price`, `sizes`, `colors`, etc.
        -   **Output:** Returns a structured JSON object with the extracted fields.

---

## 3. Required New Components

This feature requires the creation of several new components in our project structure.

1.  **`integrations/communication/whatsapp_client.py`:** A new adapter to handle the specifics of sending and receiving messages via the WhatsApp Business Cloud API.
2.  **`tools/communication_tools.py`:** Will contain a `send_whatsapp_message` tool that the agents can call. This tool will use the `whatsapp_client`.
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
