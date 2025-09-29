# AutifyME Agentic Service Tech Stack

This document outlines the technology stack for the AutifyME Agentic Service. Each choice is made with the goal of building a production-grade, scalable, and maintainable system, while enabling rapid iteration.

---

## 1. Core Agentic Logic & Orchestration

- **Choice:** **LangChain & LangGraph**
- **Reasoning:**
  - **Version:** We will be utilizing the latest stable v1 releases of these libraries to ensure access to modern features and long-term support.
  - **Mature Ecosystem:** LangChain is the most mature and widely-adopted framework for building LLM-powered applications. It provides a vast library of integrations for LLMs, vector stores, tools, and more.
  - **Purpose-Built for Agents:** LangGraph is specifically designed for creating stateful, multi-agent systems. Its graph-based approach, where nodes are functions (tools or LLM calls) and edges are the control flow, is a perfect match for the "Agent/Specialist/Tool" architecture described in the whitepaper. It explicitly supports cycles, which are essential for complex reasoning, and has built-in persistence and human-in-the-loop capabilities.
  - **Community & Support:** The large community ensures that we can find solutions to problems quickly and that the framework is constantly improving.
- **Cost Model:** Free (Open Source Libraries).

---

## 2. Database & Backend Services

- **Choice:** **Supabase**
- **Reasoning:**
  - **Postgres Foundation:** At its core, Supabase is a managed Postgres database, which is a robust, reliable, and highly-scalable relational database. This is ideal for modeling the complex relationships in a business OS (companies, users, products, invoices, etc.).
  - **Backend-as-a-Service (BaaS):** Supabase bundles essential backend services that we would otherwise have to build ourselves. This includes authentication, object storage (for generated assets, websites), and instant, secure APIs. This is a massive development accelerator.
  - **Vector Database:** Supabase includes `pgvector`, a Postgres extension for storing and querying vector embeddings. This will be crucial for building any RAG (Retrieval-Augmented Generation) capabilities or semantic search tools for our agents.
- **Cost Model:** Generous Free Tier suitable for development and early production.

---

## 3. Observability & Debugging

- **Choice:** **LangSmith**
- **Reasoning:**
  - **Version:** We will use the latest v1 SDK for seamless integration and stability.
  - **Purpose-Built for LLM Apps:** LangSmith is not a generic observability tool; it's designed specifically for tracing and debugging complex LLM chains and agentic systems.
  - **Seamless Integration:** It integrates flawlessly with LangChain and LangGraph, providing detailed, step-by-step traces of agent execution, including all LLM inputs/outputs, tool calls, and state changes. This is non-negotiable for understanding *why* an agent made a certain decision.
  - **Evaluation & Monitoring:** It includes tools for creating datasets and running evaluations, which will be critical for ensuring the quality and reliability of our agents (i.e., preventing regressions as we update prompts or models).
- **Cost Model:** Free "Developer" Tier suitable for development.

---

## 4. Python Package Management

- **Choice:** **uv**
- **Reasoning:**
  - **Performance:** `uv` is an extremely fast Python package installer and resolver, written in Rust. It can be orders of magnitude faster than `pip` and `pip-tools`, which will improve the development feedback loop.
  - **Modern Tooling:** It's a modern, all-in-one tool that handles dependency resolution and installation, similar to `cargo` in the Rust ecosystem or `pnpm` in the Node.js ecosystem.
  - **From the Astral Team:** The same team behind the `ruff` linter, which has a strong reputation for building high-quality, high-performance developer tools.
- **Cost Model:** Free (Open Source Tool).

---

## 5. Initial User Interface (MVP)

- **Choice:** **Streamlit**
- **Reasoning:**
  - **Speed of Development:** Streamlit allows us to build interactive web UIs for our agents using only Python. We can create simple interfaces for triggering workflows and handling HITL steps in minutes, not hours or days.
  - **Focus on the Backend:** For the MVP, our primary focus is the agentic logic. Streamlit is the fastest way to build a "good enough" UI so we can focus on the core value proposition without getting bogged down in frontend development.
  - **Easy Integration:** It will be trivial to call our Python-based agent functions directly from the Streamlit application.
- **Cost Model:** Free (Open Source Library). Free hosting is available via Streamlit Community Cloud.
