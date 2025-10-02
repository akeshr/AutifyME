# WhatsApp-Based Product Cataloging Workflow

This document outlines the design for the Cataloging MVP feature: enabling Indian small business owners to build a product catalog. The current implementation validates the workflow via scripts; WhatsApp integration is planned once the architecture is proven with customers. Implementation notes are limited to cataloging; broader agent architecture details remain in `AGENTS_DESIGN.md`.

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
