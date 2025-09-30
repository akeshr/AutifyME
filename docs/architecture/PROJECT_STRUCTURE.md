# AutifyME Agentic Service Project Structure

This document outlines the project structure for the `agents` service. The design is based on the principles of Hexagonal Architecture (Ports and Adapters) to ensure a clear separation of concerns, high maintainability, and scalability.

**Note:** This structure is optimized for full LangSmith integration. See `LANGSMITH_INTEGRATION_STRATEGY.md` for details.

---

## Top-Level Directory Structure

```
agents/
├── src/
│   └── autifyme_agents/
│       └── ... (Core Application Code)
│
├── tests/
│   └── ... (Unit and Integration Tests)
│
├── e2e_tests/
│   └── ... (End-to-End Tests)
│
├── .env
├── .gitignore
├── pyproject.toml
└── README.md
```

-   **`src/autifyme_agents/`**: The main container for the Python package. Using a `src` layout is a best practice that prevents common import issues and makes the package cleanly installable.
-   **`tests/`**: Contains all automated unit and integration tests. The structure of this directory mirrors the application code, making it easy to locate tests for specific components. Agent-level evaluation is handled by LangSmith, not traditional test files.
-   **`e2e_tests/`**: Contains all automated end-to-end (E2E) tests. These tests use a framework like Playwright to interact with the live application UI, simulating real user behavior to validate the entire system from frontend to backend.
-   **`.env`**: Environment configuration including Supabase credentials and LangSmith API keys. **Never commit this file.**
-   **`pyproject.toml`**: The definitive project definition file for modern Python projects. It manages dependencies, project metadata, and tool configuration, replacing the traditional `requirements.txt`.

---

## Core Application Structure (`src/autifyme_agents/`)

The core application follows a hexagonal, domain-driven design pattern.

```
autifyme_agents/
├── __init__.py
├── workflows/
│   └── ... (The "Project Managers")
├── departments/
│   └── ... (The "Managers" and "Specialists")
│
├── integrations/
│   └── ... (The "Adapters" Layer for External Services)
│
├── tools/
│   └── ... (The "Ports" Layer defining capabilities)
│
├── prompts/
│   ├── __init__.py
│   ├── templates.py    (LangChain PromptTemplate definitions)
│   └── prompts.json    (Optional: external prompt storage)
│
├── schemas/
│   └── ... (Data Models and State Schemas)
├── core/
│   └── ... (Configuration, Logging, Prompt Loading)
└── entrypoints/
    └── ... (UI and API Servers)
```

### 1. The Core Logic

-   **`workflows/`**: The highest level of business logic. Each file represents a long-running, multi-department `Project Manager` agent that orchestrates a complete business process (e.g., `company_onboarding.py`).
-   **`departments/`**: Encapsulates the logic for a specific business domain (e.g., `marketing/`, `website/`). Each department is a Python sub-package containing its `Department Head` agent and its team of `Specialist` agents. This co-locates related business logic.

### 2. The Hexagonal Boundary (Ports & Adapters)

This is the key to decoupling our application from the outside world.

-   **`integrations/` (The "Adapters"):**
    -   This is the **outermost layer**. It contains all the code that communicates directly with external, third-party services (LLMs, Supabase, WhatsApp, MCP, etc.).
    -   Each service has its own sub-package (e.g., `llm/`, `storage/`).
    -   The code here is responsible for handling the specific details of a service's SDK, authentication, and API quirks.

-   **`tools/` (The "Ports"):**
    -   This is the **boundary layer**. It defines the clean, internal interfaces that our agents use. It represents the *capabilities* of our system (e.g., `send_notification`, `get_file_from_storage`).
    -   The tools act as a Façade, abstracting away the complexity of the adapters. A tool's code will import a specific client from the `integrations/` layer and use it. This allows us to change the external provider without changing any of the core agent logic.

### 3. Supporting Components

-   **`prompts/`**: Contains all LLM prompt templates, following LangChain best practices:
    -   `templates.py` - LangChain `PromptTemplate` definitions for all agents (recommended approach)
    -   `prompts.json` - Optional external prompt storage for scalability
    -   Prompts are version-controlled in Git for auditability and rollback
    -   LangSmith is used for experimentation and A/B testing, not as primary storage
-   **`schemas/`**: Defines the Pydantic models for our data structures and the state objects used by LangGraph. This ensures data consistency throughout the application.
-   **`core/`**: Holds application-wide singleton services:
    -   `config.py` - Configuration management using Pydantic Settings
    -   `ports.py` - Abstract interfaces (the "Ports" in Hexagonal Architecture)
    -   `logging.py` - Lightweight, LangSmith-aware logging
    -   `prompt_loader.py` - Centralized prompt loading (if using JSON approach)
    -   `langsmith_config.py` - LangSmith client setup and utilities
    -   `tracing.py` - Helper decorators and trace management
    -   `evaluators.py` - Custom evaluator functions for LangSmith
    -   `exceptions.py` - Custom exception hierarchy
-   **`entrypoints/`**: The layer that exposes our application to the world. Contains the Streamlit app (`streamlit_app.py`) for user interaction and, in the future, a REST API server (`api.py`) for programmatic access.
