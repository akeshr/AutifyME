# AutifyME → OpenClaw Redesign: Master Document

**Created:** 2026-02-12  
**Purpose:** Single source of truth for the complete redesign. Read this first after any compaction.  
**Status:** Architecture finalized, implementation pending.

---

## TABLE OF CONTENTS

1. [What Is AutifyME](#1-what-is-autifyme)
2. [Why The Pivot](#2-why-the-pivot)
3. [The Original Architecture (What Existed)](#3-the-original-architecture)
4. [The New Architecture (What We're Building)](#4-the-new-architecture)
5. [Key Design Decisions](#5-key-design-decisions)
6. [What OpenClaw Already Provides (Native)](#6-what-openclaw-provides-native)
7. [What Must Be Built (Custom Utilities)](#7-what-must-be-built)
8. [Domain Knowledge Inventory (Protocols)](#8-domain-knowledge-inventory)
9. [Skill Design](#9-skill-design)
10. [DB Tool Specification](#10-db-tool-specification)
11. [Image Generation Tool Specification](#11-image-generation-tool-specification)
12. [TallyPrime Tool Specification](#12-tallyprime-tool-specification)
13. [What's Eliminated](#13-whats-eliminated)
14. [Improvements Over Original](#14-improvements-over-original)
15. [Migration Execution Plan](#15-migration-execution-plan)
16. [Repository & File Locations](#16-repository--file-locations)
17. [Environment & Credentials](#17-environment--credentials)
18. [Open Questions](#18-open-questions)

---

## 1. WHAT IS AUTIFYME

**AutifyME** is an **Agentic Business Operating System** — an AI system that automates end-to-end business functions for Indian MSMEs (Micro, Small, and Medium Enterprises).

**Vision:** Every business task that can be made agentic, will be. From product cataloging to marketing, CRM, billing, inventory, HR, and procurement.

**Target user:** Small business owners like Abhishek (Pavisha PET Industries, Patna, Bihar) who interact via WhatsApp. They send product photos, ask questions, give approvals — and the AI handles everything else.

**Current MVP focus:** Product Cataloging via WhatsApp — user sends product photos → AI analyzes, researches, creates catalog entries with human approval.

**Whitepaper:** `docs/whitepaper.md` (14 planned workflow domains)

**Repo:** `C:\Users\autif\.openclaw\workspace\AutifyME` (github.com/akeshr/AutifyME)  
**Branch:** `specialist-build-up-v11` (created from latest main, which has v10 merged)

---

## 2. WHY THE PIVOT

Abhishek was building AutifyME from scratch using LangChain/LangGraph/deepagents. After setting up OpenClaw for his business, he realized OpenClaw already provides ALL the infrastructure he was building:

| Built From Scratch | OpenClaw Has It |
|-------------------|-----------------|
| WhatsApp webhook + media client (~800 lines) | Native WhatsApp channel (Baileys) |
| LangGraph workflow orchestration (~1500 lines) | Native agent sessions + sub-agent spawning |
| State persistence (Supabase checkpointer) | Native session persistence |
| HITL approval engine (~400 lines) | Natural WhatsApp conversation |
| Context management middleware | Native context compaction |
| LangSmith observability | Native session status + logs |
| Error handling framework | Native retry + failover |
| Multi-channel support (planned) | 18+ channels native |

**The insight:** Stop building the operating system. OpenClaw IS the operating system. Build the business skills on top.

**Cost of custom stack:** ~6,600 lines of infrastructure code, months of development.  
**Cost on OpenClaw:** ~500 lines of utility scripts + skill files, weeks of development.

---

## 3. THE ORIGINAL ARCHITECTURE (What Existed)

### 3.1 Agent Hierarchy

```
Project Manager (orchestrator — 560+ line prompt)
  ├── visual_analyst      (EYES — image analysis, domain=visual)
  ├── product_analyst     (RESEARCH — web search via Tavily, domain=product)
  ├── catalog_analyst     (DB EXPERT — Supabase queries, domain=catalog)
  ├── creative_specialist (IMAGE CREATOR — Gemini 3 Pro Image, domain=creative)
  └── catalog_specialist  (CATALOG WRITER — Supabase writes + HITL, domain=catalog)
```

### 3.2 Core Pattern: Protocol-Driven Reasoning

Agents don't have hardcoded logic. They load `.protocol` files at runtime that give them domain expertise. The `load_protocol` tool resolves protocol names to files:

```
Resolution order:
1. {domain}/{protocol_name}.protocol  (e.g., catalog/family_fit.protocol)
2. shared/{protocol_name}.protocol
3. shared/tool_mastery/{protocol_name}.protocol
```

**This is the core innovation.** The protocols contain the actual business intelligence — not the code.

### 3.3 Two-Phase Workflow

**Phase 1: INTELLIGENCE (Parallel, Read-Only)**
- Fire analysts (visual, product, catalog) in parallel "waves"
- Each produces analysis files (visual_analysis.md, product_research.md, catalog_analysis.md)
- PM synthesizes findings at approval gate

**Phase 2: EXECUTION (Serial, Write Operations)**
- After user approval, route to specialists
- Creative specialist → image processing → asset creation
- Catalog specialist → database writes with HITL approval per operation

### 3.4 Key Tools

| Tool | File | Purpose | External Dependency |
|------|------|---------|-------------------|
| `load_protocol` | `tools/protocol_loader.py` | Load domain protocols at runtime | Filesystem (protocol files) |
| `view_image` | `tools/view_image.py` | Multimodal image viewing | Pillow, Supabase Storage |
| `inspect_schema` | `tools/data_engine/inspect_schema.py` | Discover table schemas | Supabase (information_schema) |
| `read_data` | `tools/data_engine/read_data.py` | Query with filters/search/joins | Supabase (PostgREST) |
| `write_data` | `tools/data_engine/write_data.py` | Multi-op atomic writes + HITL | Supabase (PostgREST) |
| `aggregate_data` | `tools/data_engine/aggregate_data.py` | COUNT/SUM/AVG queries | Supabase (RPC) |
| `image_studio` | `tools/image_studio/tool.py` | Image generation/transformation | Gemini 3 Pro Image API |
| `research_product_tool` | `tools/research_tools.py` | Web search for product info | Tavily API |
| `extract_web_content_tool` | `tools/research_tools.py` | Deep content extraction | Tavily Extract API |
| `download_whatsapp_media` | `tools/platform_tools.py` | Download WhatsApp images | WhatsApp Business API |

### 3.5 Tech Stack

- **Language:** Python 3.11+
- **Framework:** LangChain v1, LangGraph v1, deepagents
- **Database:** Supabase (PostgreSQL + Storage + pgvector)
- **LLMs:** Gemini 3 Flash Preview (PM), Gemini 3 Flash Preview with high thinking (specialists)
- **Image Gen:** Gemini 3 Pro Image
- **Research:** Tavily API
- **Observability:** LangSmith
- **Messaging:** WhatsApp Business API (custom webhook)
- **Package Manager:** uv

### 3.6 Database Schema (Supabase)

Key tables in the product catalog:

```
product_families          → Product groupings (e.g., "PET Bottles", "Glass Jars")
  ├── products            → Individual SKUs (product_family_id FK)
  ├── customer_segments   → WHO the family serves (b2b, b2c, wholesale)
  ├── variant_axes        → Variant dimensions (size, color, cap_type)
  │   └── variant_values  → Values per axis (500ml, 1000ml, Red, Blue)
  └── product_family_industries → Industry targeting

products
  ├── product_variant_values → Product-to-variant junction
  ├── product_prices         → Price list entries
  └── product_assets         → Product-to-image junction

assets → Digital assets (storage_path, asset_type, mime_type)
price_lists → Pricing contexts (wholesale, retail, MRP)
uom → Units of measure
industries → NAICS industry codes
```

---

## 4. THE NEW ARCHITECTURE (What We're Building)

### 4.1 Core Principle

**Generic atomic agents + injected domain knowledge.**

Sub-agents are NOT domain-specific. They are capability-specific. Domain knowledge is injected via the task prompt at spawn time.

### 4.2 Architecture Diagram

```
User (WhatsApp / Telegram / Discord / WebChat / any channel)
  ↓
OpenClaw Main Agent (I am the orchestrator)
  │
  ├── SKILLS (domain knowledge libraries)
  │   ├── product-cataloging/     → catalog protocols as skill knowledge
  │   ├── visual-intelligence/    → visual analysis protocols
  │   ├── creative-production/    → image creation protocols
  │   ├── market-research/        → research & compliance protocols
  │   ├── accounting-tally/       → TallyPrime integration
  │   ├── marketing/              → social media, Google Business
  │   └── [any future domain]/    → just add a skill folder
  │
  ├── GENERIC SUB-AGENTS (spawned on demand)
  │   │
  │   ├── Vision Agent
  │   │   Uses: image tool (native)
  │   │   Receives: image + specific analysis questions + domain context
  │   │   Returns: structured analysis
  │   │
  │   ├── Researcher Agent
  │   │   Uses: web_search + web_fetch (native)
  │   │   Receives: research query + what to look for + domain context
  │   │   Returns: findings with confidence scores
  │   │
  │   ├── Database Agent
  │   │   Uses: exec → db_tool.py
  │   │   Receives: operation + schema context + domain rules (protocols)
  │   │   Returns: query results or write confirmation
  │   │
  │   └── Creator Agent
  │       Uses: exec → image_gen.py
  │       Receives: source image + creative direction + domain context
  │       Returns: generated image path + quality assessment
  │
  ├── NATIVE TOOLS (zero migration needed)
  │   ├── web_search        → replaces Tavily research_product_tool
  │   ├── web_fetch          → replaces Tavily extract_web_content_tool
  │   ├── image (analysis)   → replaces view_image tool
  │   ├── browser            → replaces browser automation specialist design
  │   ├── message            → replaces WhatsApp webhook + client
  │   ├── cron               → scheduled automation
  │   ├── tts                → voice responses
  │   ├── read/write/edit    → file operations
  │   └── exec/process       → run any script/command
  │
  └── CUSTOM UTILITIES (Python scripts called via exec)
      ├── db_tool.py         → Supabase CRUD (inspect/read/write/aggregate)
      ├── image_gen.py       → Gemini/DALL-E image generation
      └── tally_api.py       → TallyPrime XML API (enhance existing)
```

### 4.3 How Domain Knowledge Flows

```
1. User sends message (e.g., photo of a product jar)

2. Main Agent (me) reads the message:
   - I have skills loaded (product-cataloging, visual-intelligence, etc.)
   - Skills give me KNOWLEDGE of the domain — protocols, schemas, patterns
   - I decide what's needed: vision analysis → research → catalog check

3. I spawn a Vision sub-agent:
   sessions_spawn(task="""
     Analyze this image. Answer these questions:
     - What material is the product? (glass, plastic, metal, etc.)
     - What are the physical dimensions/capacity?
     - Any text/labels/branding visible?
     - How many distinct items? Same product different angles, or different products?
     - Quality assessment: resolution, focus, lighting
     
     [Relevant visual protocol knowledge injected here]
   """)

4. Vision agent returns analysis. I now decide: need research? need catalog check?

5. I spawn a Researcher sub-agent:
   sessions_spawn(task="""
     Research this product: PET jar, 500ml, food grade
     Find: HSN code, market price range, material specifications, certifications
     
     [Relevant market-research protocol knowledge injected here]
   """)

6. I spawn a Database sub-agent:
   sessions_spawn(task="""
     Check our catalog for duplicates.
     Use db_tool.py via exec: python db_tool.py read products --search '{"name": "%PET%jar%500%"}'
     Also check family fit: python db_tool.py read product_families --select "id,name"
     Then: python db_tool.py read customer_segments --filters '{"product_family_id": "<id>"}'
     
     [Relevant catalog protocol knowledge injected here]
     [Schema context from prior inspect results]
   """)

7. I SYNTHESIZE all results. Present to user:
   "Here's what I found: [summary]. Should I create this product in the catalog?"

8. User approves. I spawn Database sub-agent for write:
   sessions_spawn(task="""
     Create this product record.
     BEFORE WRITING: inspect schema first.
     python db_tool.py inspect products --details all
     Then: python db_tool.py write products --data '{...}' --dry-run
     Show the dry-run result. STOP and report back. Do not execute without confirmation.
     
     [WriteIntent protocol knowledge injected here]
   """)

9. I review the dry-run, present to user for final confirmation, then execute.
```

### 4.4 HITL Pattern (Simplified)

**AutifyME way:** Complex HITL interrupt mechanism with markers, state persistence, protocol for parsing feedback.

**OpenClaw way:** 
1. Sub-agent does analysis/dry-run
2. Sub-agent reports back to me
3. I present findings to user on WhatsApp
4. User says yes/no/modify
5. I spawn next action based on response

No HITL engine needed. Just natural conversation.

---

## 5. KEY DESIGN DECISIONS

### Decision 1: Generic Agents, Not Domain-Specific
**What:** Sub-agents are capability-based (Vision, Research, Database, Creator), NOT domain-based (catalog_specialist, creative_specialist).

**Why:** 
- Same Vision agent works for product cataloging AND quality inspection AND marketing photo review
- Same Database agent works for catalog AND CRM AND inventory AND billing
- Adding a new domain = adding a skill folder with protocols, NOT building a new agent
- Reusability over specialization

### Decision 2: Protocols as Skill Knowledge, Not Runtime Loading
**What:** Protocol files become embedded knowledge in SKILL.md files, NOT runtime-loaded via a tool.

**Why:**
- Eliminates 2-5 wasted tool calls per task (load_protocol calls)
- Main agent has the knowledge in context via skills
- Injects relevant protocol sections into sub-agent task prompts
- Faster, cheaper, more reliable

### Decision 3: CLI Utilities Over Library Integrations
**What:** Database and image generation are Python CLI scripts called via `exec`, NOT LangChain tool wrappers.

**Why:**
- No LangChain/LangGraph dependency
- Simple JSON in/out, debuggable independently
- Any agent can use them (not tied to a framework)
- Easy to test: `python db_tool.py read products --limit 5`

### Decision 4: Main Agent IS the Orchestrator
**What:** No separate Project Manager agent. The OpenClaw main agent performs orchestration.

**Why:**
- The 560-line PM prompt's intelligence goes into SOUL.md + AGENTS.md + skills
- Wave-based dependency resolution becomes natural reasoning
- No delegation overhead (PM→specialist→tool = 3 hops becomes agent→sub-agent = 1 hop)
- Context naturally accumulates in the session

### Decision 5: File-Based + External DB (Hybrid Storage)
**What:** Use OpenClaw's file-based memory for agent state + Supabase for structured business data.

**Why:**
- Agent memory (decisions, context, preferences) → MEMORY.md + memory/*.md
- Structured business data (products, prices, customers) → Supabase
- Best of both worlds: fast agent memory + relational queries for business data

---

## 6. WHAT OPENCLAW PROVIDES (Native — Zero Work)

### Messaging & Channels
- WhatsApp (active, connected to +917258067800)
- Telegram, Discord, Signal, Slack, iMessage, and 12+ more
- Media support (images, audio, video, documents in/out)
- Reactions, polls, broadcasting
- Group chat intelligence (mention-based activation)

### Agent Runtime
- Multi-turn conversation with context management
- Session persistence (survives restarts)
- Auto-compaction with memory flush
- Streaming responses
- Model failover (primary → fallback chain)
- 20+ model providers (Anthropic, OpenAI, Google, etc.)

### Sub-Agents
- `sessions_spawn` — non-blocking background tasks
- Configurable model per sub-agent (use cheaper models for simple tasks)
- Auto-announce results back to main session
- Max 8 concurrent, auto-archive after 60 minutes

### Tools
- `web_search` — Brave Search API (or Perplexity Sonar)
- `web_fetch` — HTTP fetch + readable extraction (HTML → markdown)
- `image` — Vision model analysis of any image
- `browser` — Full browser automation (open, navigate, click, type, snapshot, screenshot, PDF)
- `exec` / `process` — Run any shell command, manage background processes
- `read` / `write` / `edit` — File system operations
- `tts` — Text-to-speech (ElevenLabs, OpenAI, Edge TTS)
- `message` — Send to any channel target
- `cron` — Scheduled jobs (one-shot, recurring, cron expressions)
- `memory_search` / `memory_get` — Semantic search across memory files
- `canvas` — UI surface for dashboards/approvals
- `nodes` — Camera, screen recording, GPS, remote execution on paired devices

### Automation
- Cron scheduler (at, every, cron expressions with timezone)
- Heartbeats (periodic polling with HEARTBEAT.md)
- Webhooks (external triggers via HTTP)
- Hooks (event-driven: /new, /reset, lifecycle events)

### Skills System
- Auto-discovery from workspace/skills/ folder
- YAML frontmatter + markdown instructions
- Gating (require bins, env vars, config)
- Hot reload on file changes
- ClawHub registry for sharing

---

## 7. WHAT MUST BE BUILT (Custom Utilities)

### 7.1 db_tool.py — Supabase CRUD Utility

**Priority:** #1 (everything depends on database access)

**Location:** `skills/database/db_tool.py` (in workspace)

**Interface:**
```bash
python db_tool.py tables [--pattern "product*"]
python db_tool.py inspect <table> [--details structure|constraints|all]
python db_tool.py read <table> [--filters '{"key":"value"}'] [--search '{"name":"%jar%"}'] [--select "id,name"] [--limit 50] [--order "name.asc"]
python db_tool.py write <table> --data '{"name":"X"}' [--operation insert|update|upsert|delete] [--match '{"id":"xxx"}'] [--dry-run]
python db_tool.py aggregate <table> --function count|sum|avg|min|max [--column col] [--group-by col] [--filters '{"key":"value"}']
```

**Output:** Always JSON to stdout. Errors to stderr with exit code 1.

**Dependencies:** `supabase` Python package (pip install supabase)

**Environment:** Reads `SUPABASE_URL` and `SUPABASE_KEY` from environment.

**Key behaviors from AutifyME to preserve:**
- `read`: filters (exact match) vs search_patterns (ILIKE with %) — separate parameters
- `read`: support for list values in filters (becomes IN operator)
- `read`: join support for related tables
- `write`: dry-run mode that shows what WOULD happen without executing
- `write`: multi-operation support (insert parent + child in one call with FK resolution)
- `inspect`: returns column names, types, nullable, defaults, constraints, foreign keys
- `aggregate`: group-by with having clauses

**AutifyME reference code:**
- `agents/src/autifyme_agents/tools/data_engine/read_data.py` (line 1-60 for schema)
- `agents/src/autifyme_agents/tools/data_engine/write_data.py` (WriteIntent pattern)
- `agents/src/autifyme_agents/tools/data_engine/inspect_schema.py`
- `agents/src/autifyme_agents/tools/data_engine/aggregate_data.py`
- `agents/src/autifyme_agents/integrations/storage/supabase_client.py` (actual Supabase calls)

### 7.2 image_gen.py — Image Generation Wrapper

**Priority:** #2 (needed for creative workflows)

**Location:** `skills/creative-production/image_gen.py`

**Interface:**
```bash
python image_gen.py generate --prompt "..." --source <path> [--output <path>] [--provider gemini|dalle]
python image_gen.py edit --source <path> --prompt "..." [--mask <path>] [--output <path>]
python image_gen.py remove-bg --source <path> [--output <path>]
python image_gen.py enhance --source <path> --prompt "..." [--output <path>]
```

**Dependencies:** `google-genai` or `openai` Python package

**AutifyME reference code:**
- `agents/src/autifyme_agents/tools/image_studio/tool.py` (full implementation)
- `agents/src/autifyme_agents/tools/image_studio/schemas.py` (12-spec palette: Fidelity, Focus, Enhancement, Composition, Background, Lighting, MaterialTreatment, Extraction, Scene, Custom, ProductPlacement, Output)

**Key behaviors to preserve:**
- Stateless: every call must be self-contained (all context in the prompt)
- Quality validation: output should be checked (via image analysis) before shipping
- Material-aware prompting: glass/plastic/metal each need different lighting/treatment descriptions

### 7.3 tally_api.py — TallyPrime Integration (Enhancement)

**Priority:** #3 (already partially working)

**Existing:** `tally_helper.ps1` (GUI automation via Win32 keybd_event) + XML API on localhost:9000

**Location:** `skills/accounting-tally/tally_api.py`

**Interface:**
```bash
python tally_api.py ledgers --list
python tally_api.py ledgers --create '{"name":"X","parent":"Sundry Debtors"}'
python tally_api.py vouchers --create '{"type":"Sales","party":"X","amount":1000}'
python tally_api.py stock --items | --groups | --summary
python tally_api.py reports --balance-sheet | --profit-loss | --gst-summary
```

**Existing TallyPrime setup:**
- Company: "Pavisha PET Industries" (FY 1-Apr-25 to 31-Mar-26)
- XML API: localhost:9000 (POST, Content-Type: text/xml)
- Install path: `C:\Program Files\TallyPrime`
- Data path: `C:\Users\Public\TallyPrime\data`
- Masters created: 31 ledgers, 11 stock groups, 28 stock items, 4 units, 3 godowns
- HSN: 3923 for PET packaging products
- TODO: Fix State (shows "Not Applicable", needs Bihar), set GST rates (18%)

---

## 8. DOMAIN KNOWLEDGE INVENTORY (Protocols)

All protocols live at: `agents/src/autifyme_agents/prompts/protocols/`

### 8.1 Catalog Domain (9 protocols)

| Protocol | File | What It Contains |
|----------|------|-----------------|
| `business_context` | `catalog/business_context.protocol` | PIM tables (products, families, segments, variants, prices, assets), relationships, domain vocabulary (product types, segment types, lifecycle states), family fit principle, cold start handling |
| `family_fit` | `catalog/family_fit.protocol` | Customer segment reasoning — products belong to families serving SAME customer segment, not by material similarity |
| `duplicate_prevention` | `catalog/duplicate_prevention.protocol` | Query patterns to check for existing products before creating new ones |
| `pricing` | `catalog/pricing.protocol` | Competitive pricing logic, price list management, market positioning |
| `variant_management` | `catalog/variant_management.protocol` | Size/color/material variants, axis-value structures |
| `new_family` | `catalog/new_family.protocol` | When and how to create new product families |
| `attribute_extraction` | `catalog/attribute_extraction.protocol` | Extracting product attributes from analysis |
| `asset_management` | `catalog/asset_management.protocol` | Linking images to products, storage paths, XOR constraints |
| `visual_analysis` | `catalog/visual_analysis.protocol` | Catalog-specific visual analysis requirements |

### 8.2 Creative Domain (3 protocols)

| Protocol | File | What It Contains |
|----------|------|-----------------|
| `data` | `creative/data.protocol` | Asset creation workflow, storage paths, junction tables, AI lineage tracking |
| `hitl` | `creative/hitl.protocol` | How to handle user feedback on generated images |
| `multi_item` | `creative/multi_item.protocol` | Anchor-first pattern for multi-item work (one image per turn, wait for feedback) |

### 8.3 PM Domain (9 protocols)

| Protocol | File | What It Contains |
|----------|------|-----------------|
| `discovery_mindset` | `pm/discovery_mindset.protocol` | **THE CORE** — Wave-based dependency resolution, scenario matrix (image/text/mixed/multi-image workflows), conditional agents, direct execution shortcuts, edge cases, error handling |
| `synthesis` | `pm/synthesis.protocol` | How to synthesize findings at approval gate, conflict detection, presentation templates |
| `execution_flows` | `pm/execution_flows.protocol` | Catalog flows A-E, ID tracking, delegation templates for execution phase |
| `multi_image` | `pm/multi_image.protocol` | Multi-image relationship detection (angles/variants/components/bulk), composition patterns |
| `data_driven` | `pm/data_driven.protocol` | Data fetch patterns, creative delegation with data (e.g., price post graphics) |
| `error_recovery` | `pm/error_recovery.protocol` | Partial success, cancellation, quality rejection handling |
| `hitl` | `pm/hitl.protocol` | HITL signal parsing, escalation patterns |
| `conflict_resolution` | `pm/conflict_resolution.protocol` | Domain authority matrix, when analysts disagree |
| `coordination_patterns` | `pm/coordination_patterns.protocol.legacy` | Legacy coordination patterns |

### 8.4 Product Domain (3 protocols)

| Protocol | File | What It Contains |
|----------|------|-----------------|
| `compliance_research` | `product/compliance_research.protocol` | HSN codes, certifications, material safety, regulatory requirements |
| `market_intelligence` | `product/market_intelligence.protocol` | Competitive analysis, market pricing, positioning |
| `research_orchestration` | `product/research_orchestration.protocol` | How to structure research queries, confidence assessment |

### 8.5 Visual Domain (4 protocols)

| Protocol | File | What It Contains |
|----------|------|-----------------|
| `catalog_visual` | `visual/catalog_visual.protocol` | Hero shot specs, studio lighting, product isolation, background treatment |
| `lifestyle_visual` | `visual/lifestyle_visual.protocol` | Lifestyle scene creation, contextual placement |
| `social_content` | `visual/social_content.protocol` | Platform-specific content (Instagram, Facebook sizes/styles) |
| `social_media` | `visual/social_media.protocol.legacy` | Legacy social media protocol |

### 8.6 Shared Domain (13 protocols)

| Protocol | File | What It Contains |
|----------|------|-----------------|
| `resource_efficiency` | `shared/resource_efficiency.protocol` | Tool call budgeting (~30 call limit), batch patterns, stop conditions |
| `input_validation` | `shared/input_validation.protocol` | Verify inputs before executing, missing context detection |
| `hitl` | `shared/hitl.protocol` | Generic HITL feedback handling |
| `read_data` | `shared/tool_mastery/read_data.protocol` | How to use read_data tool effectively |
| `write_data` | `shared/tool_mastery/write_data.protocol` | WriteIntent structure, multi-op transactions |
| `inspect_schema` | `shared/tool_mastery/inspect_schema.protocol` | Schema discovery patterns |
| `schema_discovery` | `shared/tool_mastery/schema_discovery.protocol` | Full schema discovery methodology |
| `aggregate_data` | `shared/tool_mastery/aggregate_data.protocol` | Statistical query patterns |
| `view_image` | `shared/tool_mastery/view_image.protocol` | Image viewing patterns |
| `image_studio` | `shared/tool_mastery/image_studio.protocol` | Image studio usage patterns |
| `list_storage` | `shared/tool_mastery/list_storage.protocol` | Storage listing patterns |
| `generate_rich_output` | `shared/tool_mastery/generate_rich_output.protocol` | Rich output formatting |
| `research_product` | `shared/tool_mastery/research_product.protocol` | Product research patterns |

### 8.7 Agent Prompts (not protocols, but critical)

| Prompt | File | Lines | What It Contains |
|--------|------|-------|-----------------|
| **Project Manager** | `prompts/project_manager.prompt` | ~560 | Delegation doctrine, routing rules, context bridge, HITL signals, output format. Contains: identity, protocol_system, tools, subagents, delegation_doctrine, context_bridge, hitl_signals, output sections |
| **Catalog Specialist** | `prompts/specialists/catalog_specialist.prompt` | ~320 | WriteIntent pattern, HITL gates, verify analyst work, workflow sequence. Contains: identity, company_context, protocol_system, verify_analyst_work, tools, workflow, hitl, output sections |
| **Creative Specialist** | `prompts/specialists/creative_specialist.prompt` | ~300 | 12-spec palette, quality rubric, anchor workflow, path discipline, context discipline. Contains: identity, brand_context, operating_mode, hitl_discipline, anchor_workflow, tools, path_discipline, context_discipline, quality_bar, hero_shot_discipline, upstream_integration, escalation, output_format sections |
| **Visual Analyst** | `prompts/analysts/visual_analyst.prompt` | ~200 | Material analysis, multi-image relationship detection |
| **Product Analyst** | `prompts/analysts/product_analyst.prompt` | ~200 | Research methodology, confidence scoring |
| **Catalog Analyst** | `prompts/analysts/catalog_analyst.prompt` | ~200 | Schema queries, family fit verification |
| **Approval Analyzer** | `prompts/approval_analyzer.prompt` | ~100 | Approval classification |

---

## 9. SKILL DESIGN

### 9.1 Skill Structure

Each skill is a folder with:
```
skills/
  <skill-name>/
    SKILL.md              # YAML frontmatter + instructions for the agent
    scripts/              # Utility scripts (db_tool.py, image_gen.py, etc.)
    knowledge/            # Extracted protocol knowledge as markdown files
    templates/            # Prompt templates for sub-agent task injection
```

### 9.2 Planned Skills

```
skills/
  database/               # Generic database access
    SKILL.md              # How to use db_tool.py (inspect → read → write pattern)
    db_tool.py            # Supabase CRUD utility

  product-cataloging/     # Product catalog management
    SKILL.md              # When to use, orchestration patterns
    knowledge/
      business_context.md # Tables, relationships, vocabulary (from catalog/business_context.protocol)
      family_fit.md       # Customer segment reasoning (from catalog/family_fit.protocol)
      pricing.md          # Pricing logic (from catalog/pricing.protocol)
      variants.md         # Variant management (from catalog/variant_management.protocol)
      duplicates.md       # Duplicate prevention (from catalog/duplicate_prevention.protocol)
    templates/
      write_intent.md     # Template for presenting write operations

  visual-intelligence/    # Image analysis for any domain
    SKILL.md              # How to analyze images, what questions to ask
    knowledge/
      materials.md        # Material identification patterns
      quality.md          # Resolution/focus/lighting assessment
      relationships.md    # Multi-image relationship detection

  creative-production/    # Image generation and transformation
    SKILL.md              # How to create commercial images
    image_gen.py          # Gemini/DALL-E wrapper
    knowledge/
      catalog_visual.md   # Hero shot specs
      social_content.md   # Platform-specific content
      quality_rubric.md   # 8-point quality scoring

  market-research/        # Product and market research
    SKILL.md              # How to research effectively
    knowledge/
      compliance.md       # HSN codes, certifications
      market.md           # Competitive analysis patterns

  accounting-tally/       # TallyPrime integration
    SKILL.md              # How to use TallyPrime XML API
    tally_api.py          # Enhanced XML API wrapper
    knowledge/
      gst.md              # GST rules, rates, filing
      ledgers.md          # Chart of accounts patterns

  marketing/              # Digital marketing
    SKILL.md              # Google Business, social media, content
    knowledge/
      google_business.md  # Profile management, reviews
      social_media.md     # Platform-specific strategies
```

---

## 10. DB TOOL SPECIFICATION

[See Section 7.1 for interface design]

**Implementation approach:**

The AutifyME `supabase_client.py` has the actual Supabase integration. Key methods:

```python
# From agents/src/autifyme_agents/integrations/storage/supabase_client.py
class SupabaseClient(StorageInterface):
    async def read_records(self, table, filters, search_patterns, select, limit, offset, order, join_tables)
    async def write_records(self, table, records, operation, match_columns)
    async def aggregate(self, table, function, column, group_by, filters, having)
    async def inspect_schema(self, tables, details)
    async def upload_file(self, bucket, path, file_bytes, content_type)
```

**db_tool.py should mirror these capabilities** in a simpler CLI form.

**WriteIntent pattern to preserve:**
```
Goal: What you're accomplishing
Reasoning: Why (protocol references)
HITL Summary: Plain language for business user
Operations: [{table, operation, data, match}]
Impact: What changes
```

In OpenClaw, this becomes: Database sub-agent does dry-run → reports back → main agent presents to user → user confirms → Database sub-agent executes.

---

## 11. IMAGE GENERATION TOOL SPECIFICATION

[See Section 7.2 for interface design]

**AutifyME's 12-spec creative palette:**

| Spec | Purpose | Example |
|------|---------|---------|
| FidelitySpec | Identity preservation | "Maintain exact product colors, logo, label artwork" |
| FocusSpec | Where to focus | "Primary: product body. Secondary: cap detail" |
| EnhancementSpec | Image improvements | "Sharpen edges, remove noise, enhance colors" |
| CompositionSpec | Framing and layout | "Center product, 70% frame fill, slight angle" |
| BackgroundSpec | Background treatment | "Pure white #FFFFFF, seamless, no shadows on bg" |
| LightingSpec | Light setup | "Soft diffused key light 45°, fill light, rim light" |
| MaterialTreatmentSpec | Material rendering | "Glass: show transparency, reflections. Plastic: matte finish" |
| ExtractionSpec | Object isolation | "Extract product from background, preserve edges" |
| SceneSpec | Environment/context | "Modern kitchen counter, morning light, lifestyle" |
| CustomSpec | Free-form instructions | Any additional creative direction |
| ProductPlacementSpec | Product in scene | "Product centered on marble surface" |
| OutputSpec | Output requirements | "1080x1080, PNG, transparent bg" |

**In OpenClaw:** These don't need to be structured types. The creative skill's knowledge teaches how to write effective prompts that cover these dimensions naturally.

---

## 12. TALLYPRIME TOOL SPECIFICATION

[See Section 7.3 for interface design]

**Existing TallyPrime state:**
- TallyPrime 4.0 EDU mode installed at `C:\Program Files\TallyPrime`
- Company: "Pavisha PET Industries" created
- XML API running on localhost:9000
- 31 ledgers, 11 stock groups, 28 stock items, 4 units, 3 godowns created
- GUI automation helper: `tally_helper.ps1`
- TODO: Fix State to Bihar, set GST rates (18%)

---

## 13. WHAT'S ELIMINATED

| Component | Lines | Replacement |
|-----------|-------|-------------|
| LangGraph workflow orchestration | ~1500 | OpenClaw agent sessions |
| LangChain tool wrappers | ~800 | OpenClaw exec + native tools |
| deepagents SubAgent compilation | ~400 | OpenClaw sessions_spawn |
| WhatsApp webhook + media client | ~800 | OpenClaw message tool |
| Supabase checkpointer/store factories | ~300 | OpenClaw session persistence |
| StorageInterface + ports pattern | ~600 | Direct Supabase via db_tool.py |
| Context middleware (truncate/clear) | ~400 | OpenClaw native compaction |
| Execution limits middleware | ~200 | OpenClaw native management |
| Protocol loader tool | ~200 | Skills system |
| PM structured output (PMOutput) | ~100 | Natural conversation |
| Agent error handler framework | ~300 | Simple try/catch |
| Pydantic schemas for tool I/O | ~500 | JSON in/out |
| Config management (Settings) | ~200 | OpenClaw env/config |
| LLM factory | ~300 | OpenClaw model selection |
| **TOTAL** | **~6,600** | **~500 lines of utilities** |

---

## 14. IMPROVEMENTS OVER ORIGINAL

### 14.1 Protocol Loading Waste Eliminated
**Before:** 2-5 tool calls per task just loading protocols. PM prompt says "Your FIRST tool call MUST be load_protocol."  
**After:** Domain knowledge is in skills, injected into task prompts. Zero wasted calls.

### 14.2 PM Middleman Removed
**Before:** PM (560-line prompt) exists only to route between specialists. Doesn't DO anything.  
**After:** Main agent IS the orchestrator. Direct routing, no delegation overhead.

### 14.3 File Path Tracking Eliminated
**Before:** Entire `<context_bridge>` section in PM prompt for manually tracking file paths between agents. Constant source of bugs.  
**After:** Session naturally accumulates context. Sub-agent results return to main agent directly.

### 14.4 HITL Simplified
**Before:** HITL interrupt mechanism, markers, state persistence, 400+ lines of code.  
**After:** Ask on WhatsApp. "Here's what I'll do. Proceed?" Yes/No.

### 14.5 Multi-Channel From Day One
**Before:** Only WhatsApp, with custom webhook.  
**After:** 18+ channels native. Same skills work on Telegram, Discord, etc.

### 14.6 No Framework Lock-In
**Before:** Tied to LangChain v1 + LangGraph v1 + deepagents. Upgrading = rewrite.  
**After:** Python CLI utilities + OpenClaw skills. Framework-independent.

---

## 15. MIGRATION EXECUTION PLAN

### Week 1: Foundation
1. ✅ Branch created (specialist-build-up-v11)
2. ✅ Codebase analyzed (CODEBASE_DEEP_ANALYSIS.md)
3. ✅ Architecture documented (this document)
4. ⬜ Build db_tool.py (Supabase CRUD utility)
5. ⬜ Create database skill (SKILL.md)
6. ⬜ Test: inspect schema, read data, write with dry-run

### Week 2: Domain Knowledge
7. ⬜ Extract catalog protocols → product-cataloging skill
8. ⬜ Extract visual protocols → visual-intelligence skill
9. ⬜ Extract research protocols → market-research skill
10. ⬜ Test: full product cataloging workflow via WhatsApp

### Week 3: Creative & Integration
11. ⬜ Build image_gen.py (Gemini image wrapper)
12. ⬜ Create creative-production skill
13. ⬜ End-to-end testing with real products
14. ⬜ Multi-image workflows

### Week 4: Expand & Polish
15. ⬜ Enhance tally_api.py
16. ⬜ Create accounting-tally skill
17. ⬜ Create marketing skill
18. ⬜ Performance optimization

---

## 16. REPOSITORY & FILE LOCATIONS

### AutifyME Repo
- **Path:** `C:\Users\autif\.openclaw\workspace\AutifyME`
- **Remote:** https://github.com/akeshr/AutifyME.git
- **Branch:** specialist-build-up-v11
- **Prompts:** `agents/src/autifyme_agents/prompts/` (all .prompt files)
- **Protocols:** `agents/src/autifyme_agents/prompts/protocols/` (all .protocol files)
- **Tools:** `agents/src/autifyme_agents/tools/` (data_engine, image_studio, etc.)
- **Integrations:** `agents/src/autifyme_agents/integrations/storage/supabase_client.py`
- **Docs:** `docs/` (CODEBASE_DEEP_ANALYSIS.md, OPENCLAW_PLATFORM_CAPABILITIES.md, MIGRATION_PLAN.md, this file)

### OpenClaw Workspace
- **Path:** `C:\Users\autif\.openclaw\workspace`
- **Skills (to create):** `C:\Users\autif\.openclaw\workspace\skills/`
- **Memory:** `C:\Users\autif\.openclaw\workspace\memory/`
- **Config:** `C:\Users\autif\.openclaw\openclaw.json` (or wherever it lives)

### TallyPrime
- **Install:** `C:\Program Files\TallyPrime`
- **Data:** `C:\Users\Public\TallyPrime\data`
- **XML API:** http://localhost:9000
- **Helper:** `C:\Users\autif\.openclaw\workspace\tally_helper.ps1`

---

## 17. ENVIRONMENT & CREDENTIALS

### GitHub
- CLI: `C:\Program Files\GitHub CLI\gh.exe`
- Auth: akeshr (via keyring)
- Protocol: HTTPS with gh credential helper

### Supabase (TBD)
- URL: (need from Abhishek)
- Key: (need from Abhishek)
- Project: (need from Abhishek)

### Gemini API (TBD)
- Key: (need from Abhishek)
- Model: gemini-3-pro (for image generation)

### OpenClaw
- Channel: WhatsApp (active)
- Owner: +917258067800
- Browser: openclaw profile, Chrome on Windows
- Model: anthropic/claude-opus-4-6

---

## 18. OPEN QUESTIONS

1. **Supabase credentials** — Do we use the existing AutifyME Supabase project or create a new one?
2. **Gemini API key** — Where is the existing key? Can we reuse it?
3. **Image storage** — Use Supabase Storage (like AutifyME) or local workspace files?
4. **Multi-tenant** — Is this for Pavisha only, or should we design for multiple businesses?
5. **Which protocols to extract first?** — Start with catalog (most developed) or visual (simplest)?
6. **Tally vs Supabase** — For Pavisha's day-to-day operations, is Tally the primary system? Is Supabase for the product catalog platform?

---

**END OF MASTER DOCUMENT**

This document is the single source of truth. After any compaction, read this first.
