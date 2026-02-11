# Migration Plan: Generic Atomic Architecture on OpenClaw

**Date:** 2026-02-12  
**Philosophy:** Generic agents + injected domain knowledge. No domain-specific sub-agents.

---

## ARCHITECTURE

```
User (WhatsApp/Telegram/etc.)
  ↓
OpenClaw Main Agent (I am the orchestrator)
  ├── Skills (domain knowledge libraries — protocols, templates, schemas)
  │   ├── product-cataloging/     → catalog domain protocols
  │   ├── accounting-tally/       → TallyPrime integration
  │   ├── marketing/              → social, Google Business, content
  │   └── [any future domain]/    → just add a skill folder
  │
  ├── Generic Sub-Agents (spawned on demand with task + domain context)
  │   ├── Vision Agent     → image tool + task-specific analysis questions
  │   ├── Researcher Agent → web_search + web_fetch + task-specific queries  
  │   ├── Database Agent   → db utility (exec) + schema context + domain rules
  │   └── Creator Agent    → image gen script (exec) + creative direction
  │
  ├── Native Tools (no migration needed)
  │   ├── web_search / web_fetch   → replaces Tavily research_product_tool
  │   ├── image (analysis)         → replaces view_image tool
  │   ├── browser                  → replaces browser automation specialist
  │   ├── tts                      → voice responses
  │   ├── message                  → replaces WhatsApp webhook
  │   └── cron                     → replaces external schedulers
  │
  └── Custom Utilities (Python scripts invoked via exec)
      ├── db_tool.py               → Supabase CRUD (inspect/read/write/aggregate)
      ├── image_gen.py             → Gemini/DALL-E image generation wrapper
      └── tally_api.py             → TallyPrime XML API wrapper (already exists)
```

## KEY PRINCIPLE

**Sub-agents are generic. Domain knowledge is injected.**

```python
# WRONG (AutifyME approach):
catalog_specialist = Agent(prompt="You are a catalog architect...", tools=[write_data])

# RIGHT (OpenClaw approach):
sessions_spawn(task=f"""
  You have access to a database tool (db_tool.py via exec).
  
  YOUR TASK: Create a product record.
  
  DOMAIN RULES:
  {catalog_business_context_protocol}
  {family_fit_protocol}
  {pricing_protocol}
  
  SCHEMA: {schema_from_inspect}
  
  CONTEXT: {visual_analysis_results + research_results}
  
  HITL: Before any write, present what you're about to do and STOP.
  Wait for confirmation before executing.
""")
```

---

## MIGRATION ITEMS (Priority Order)

### 1. Database Utility (db_tool.py) — FOUNDATION

**What it replaces:** inspect_schema, read_data, write_data, aggregate_data  
**Why first:** Every domain needs database access. Catalog, CRM, inventory, billing — all need CRUD.

**Design:**

```
db_tool.py <command> [options]

Commands:
  inspect   <table> [--details structure|constraints|all]
  read      <table> [--filters JSON] [--search JSON] [--select cols] [--limit N] [--join JSON]
  write     <table> --data JSON [--operation insert|update|upsert|delete] [--dry-run]
  aggregate <table> --function count|sum|avg|min|max [--column col] [--group-by col] [--filters JSON]
  tables    [--pattern wildcard]
```

**Output:** Always JSON to stdout. Errors to stderr.

**What the skill teaches:**
- When to inspect before writing (ALWAYS)
- How to construct filters vs search_patterns
- WriteIntent pattern: goal → reasoning → operations → present to user → execute
- Schema discovery: "inspect_schema FIRST, then map your data to actual columns"

**Implementation:**

```python
# db_tool.py — Generic Supabase CRUD utility
# Reads SUPABASE_URL and SUPABASE_KEY from environment
# All commands output JSON to stdout

import argparse, json, sys, os
from supabase import create_client

def get_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]  
    return create_client(url, key)

def cmd_tables(pattern=None):
    """List all tables (via information_schema)"""
    client = get_client()
    result = client.rpc("get_tables", {}).execute()
    # Filter by pattern if provided
    ...

def cmd_inspect(table, details="all"):
    """Inspect table schema: columns, types, constraints, relationships"""
    client = get_client()
    # Query information_schema.columns + constraints
    ...

def cmd_read(table, filters=None, search=None, select=None, limit=50, join=None):
    """Query data with filters, ILIKE search, joins, pagination"""
    client = get_client()
    query = client.table(table).select(select or "*")
    if filters:
        for k, v in json.loads(filters).items():
            if isinstance(v, list):
                query = query.in_(k, v)
            else:
                query = query.eq(k, v)
    if search:
        for k, v in json.loads(search).items():
            query = query.ilike(k, v)
    result = query.limit(limit).execute()
    print(json.dumps(result.data, indent=2))

def cmd_write(table, data, operation="insert", dry_run=False):
    """Write data with optional dry-run"""
    if dry_run:
        print(json.dumps({"dry_run": True, "table": table, "operation": operation, "data": json.loads(data)}))
        return
    client = get_client()
    data_parsed = json.loads(data)
    if operation == "insert":
        result = client.table(table).insert(data_parsed).execute()
    elif operation == "update":
        # data must include filter key
        ...
    elif operation == "upsert":
        result = client.table(table).upsert(data_parsed).execute()
    elif operation == "delete":
        ...
    print(json.dumps(result.data, indent=2))

def cmd_aggregate(table, function, column=None, group_by=None, filters=None):
    """Aggregate queries: count, sum, avg, min, max"""
    client = get_client()
    # Use RPC or raw SQL via Supabase
    ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supabase CRUD utility")
    sub = parser.add_subparsers(dest="command")
    
    # ... argparse setup for each command
    
    args = parser.parse_args()
    # ... dispatch to appropriate function
```

**Skill structure:**

```
skills/
  database/
    SKILL.md          # Teaches agent how to use db_tool.py
    db_tool.py        # The actual utility
    setup.py          # pip install supabase (one-time setup)
```

---

### 2. Image Generation Utility (image_gen.py) — FOR CREATIVE AGENT

**What it replaces:** image_studio tool (Gemini 3 Pro Image API wrapper)  
**Why second:** Needed for any visual output — hero shots, social content, marketing.

**Design:**

```
image_gen.py generate --prompt "..." --source path [--output path] [--provider gemini|dalle]
image_gen.py edit --source path --prompt "..." [--mask path] [--output path]
image_gen.py remove-bg --source path [--output path]
```

**What the skill teaches:**
- Material-aware prompting (glass → specific lighting, plastic → specific treatment)
- Quality validation (view output, check identity/composition/lighting)
- Iteration pattern (generate → validate → iterate if needed)
- The creative protocols (catalog_visual, lifestyle_visual, social_content) as embedded knowledge

---

### 3. TallyPrime API Utility (already exists: tally_helper.ps1 + XML API)

**Status:** Already working from Day 1 setup.  
**Enhancement needed:** Wrap XML API calls into a cleaner utility.

```
tally_api.py ledgers [--list | --create JSON | --alter JSON]
tally_api.py vouchers [--list | --create JSON]
tally_api.py stock [--items | --groups | --summary]
tally_api.py reports [--balance-sheet | --profit-loss | --gst-summary]
```

---

### 4. Domain Knowledge Skills (protocol extraction)

Each skill is a SKILL.md with domain protocols embedded:

```
skills/
  product-cataloging/
    SKILL.md                    # How to manage product catalogs
    protocols/
      business_context.md       # PIM domain vocabulary, table relationships
      family_fit.md             # Customer segment reasoning
      duplicate_prevention.md   # Query patterns to avoid duplicates
      pricing.md                # Competitive pricing logic
      variant_management.md     # Size/color/material variant handling
    templates/
      write_intent.md           # Template for presenting write operations to user

  visual-intelligence/
    SKILL.md                    # How to analyze images for any domain
    protocols/
      material_analysis.md      # Material identification (glass, plastic, metal)
      quality_assessment.md     # Resolution, focus, visibility checks
      relationship_detection.md # Multi-image: angles vs variants vs components

  creative-production/
    SKILL.md                    # How to create commercial-grade images
    protocols/
      catalog_visual.md         # Hero shot specs, lighting, composition
      social_content.md         # Platform-specific content creation
      quality_rubric.md         # 8-point quality scoring

  market-research/
    SKILL.md                    # How to research products and markets
    protocols/
      compliance.md             # HSN codes, certifications, standards
      market_intelligence.md    # Competitive analysis, pricing benchmarks
```

---

## WHAT'S NOT NEEDED (Kill List)

| AutifyME Component | Why Not Needed |
|-------------------|----------------|
| LangGraph/LangChain | OpenClaw IS the orchestration layer |
| deepagents library | Sub-agent spawning is native |
| WhatsApp webhook server | Native channel |
| Supabase checkpointer | Session persistence is native |
| Protocol loader tool | Protocols embedded in skills, injected in task prompts |
| StorageInterface/ports | Direct Supabase access via utility script |
| Execution context (thread_id) | Session management is native |
| Context middleware | Native session compaction |
| Execution limits middleware | Native token management |
| LangSmith tracing | Native session status + logs |
| PM structured output (PMOutput) | Natural conversation |
| Agent error handler framework | Simple try/catch in utility scripts |
| Pydantic schemas for tool I/O | JSON in/out from CLI tools |

**Lines of code eliminated: ~6,000+**  
**Lines of code to write: ~500 (db_tool.py + image_gen.py + tally_api.py)**

---

## EXECUTION ORDER

### Week 1: Foundation
1. Write `db_tool.py` (Supabase CRUD utility)
2. Create `database` skill (SKILL.md that teaches usage)
3. Test: inspect schema, read data, write data with HITL
4. Write `image_gen.py` (Gemini image generation wrapper)
5. Create `creative-production` skill

### Week 2: Domain Knowledge
6. Extract catalog protocols → `product-cataloging` skill
7. Extract visual protocols → `visual-intelligence` skill  
8. Extract research protocols → `market-research` skill
9. Test: full product cataloging workflow via WhatsApp

### Week 3: Integration & Polish
10. End-to-end testing with real products
11. Multi-image workflows
12. Error handling and edge cases
13. Performance optimization (which tasks need sub-agents vs inline)

### Week 4: Expand
14. TallyPrime accounting skill (enhance existing)
15. Marketing skill (Google Business, social media)
16. CRM skill (customer tracking)

---

## SUCCESS CRITERIA

The migrated system must handle these scenarios:

1. **Image → Product:** User sends product photo → Vision analysis → Research → Catalog check → Present findings → User approves → Create product record
2. **Text → Update:** "Update Blue Jar price to Rs 500" → Direct database update with confirmation
3. **Multi-image:** 3 photos → Detect relationship (angles/variants/components) → Route appropriately
4. **Creative:** "Create hero shot for Premium Glass Jar" → Fetch product data → Generate image → Quality check → Store asset
5. **Research:** "What's the HSN code for glass bottles?" → Web search → Synthesize → Answer

All using generic agents with injected domain knowledge. Zero domain-specific agent code.
