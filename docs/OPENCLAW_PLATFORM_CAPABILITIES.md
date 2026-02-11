# OpenClaw Platform — Atomic Features & Tools Reference

**Purpose:** Complete inventory of every atomic capability available in OpenClaw, mapped to AutifyME's Business OS vision. This is the foundation document for the pivot from custom-built infrastructure to OpenClaw-native skills.

**Last Updated:** 2026-02-11

---

## 1. COMMUNICATION LAYER

### 1.1 Channels (Inbound + Outbound Messaging)

| Channel | Status | Notes |
|---------|--------|-------|
| **WhatsApp** | Active | Via Baileys (WhatsApp Web). Supports DMs, groups, media, reactions, polls. Multiple accounts possible. |
| **Telegram** | Available | Via grammY. Bot mode. Voice note bubbles for TTS. |
| **Discord** | Available | Bot mode. Channels, threads, reactions, embeds. |
| **Signal** | Available | Via signal-cli. |
| **Slack** | Available | Bot mode. Threads, channels. |
| **iMessage** | Available | macOS only, via imsg CLI. |
| **Google Chat** | Available | Workspace integration. |
| **IRC** | Available | Classic protocol support. |
| **Matrix** | Available | Decentralized chat. |
| **Mattermost** | Available | Via plugin. |
| **MS Teams** | Available | Enterprise chat. |
| **Line** | Available | Popular in Asia. |
| **Zalo** | Available | Popular in Vietnam. |
| **Feishu/Lark** | Available | Popular in China. |
| **Nostr** | Available | Decentralized protocol. |
| **Twitch** | Available | Streaming chat. |
| **WebChat** | Available | Built-in web UI. |

**Atomic capabilities per channel:**
- `message.send` — Send text, media, files to any target
- `message.react` — Add emoji reactions
- `message.poll` — Create polls (WhatsApp, Telegram, Discord)
- `message.broadcast` — Send to multiple targets
- Reply threading (where supported)
- Media: images, audio, video, documents (in/out)
- Voice notes (with TTS integration)
- Location sharing

**AutifyME mapping:** Replaces the entire custom WhatsApp webhook + media client. Every future channel (Telegram for enterprises, Discord for communities) is already built.

### 1.2 Channel Routing & Multi-Account

- **Multiple WhatsApp accounts** on one Gateway (e.g., personal + business)
- **Per-channel DM policies**: allowlist, open, blocklist
- **Group chat policies**: mention-based activation, allowlist
- **Channel-specific formatting**: auto-adapts markdown for each platform
- **Broadcast groups**: one message → multiple channels simultaneously

### 1.3 Group Chat Intelligence

- Mention-based activation (customizable patterns)
- Smart participation: knows when to speak vs stay silent
- Per-group session isolation
- React without replying (lightweight acknowledgment)

---

## 2. AGENT ARCHITECTURE

### 2.1 Core Agent (Single Agent)

Each agent is a fully isolated "brain" with:
- **Workspace**: files, AGENTS.md, SOUL.md, USER.md, memory, skills
- **State directory**: auth profiles, model registry, per-agent config
- **Session store**: chat history + routing state
- **Identity**: name, personality, emoji, avatar

**Atomic capabilities:**
- Natural language understanding and generation
- Tool calling (structured function invocation)
- Multi-turn conversation with context
- Streaming responses (chunked for long replies)
- Context window management with auto-compaction

### 2.2 Multi-Agent Routing

- **Multiple isolated agents** in one Gateway
- **Deterministic routing**: channel → accountId → peer → agentId
- **Per-agent configuration**: different models, tools, sandboxes, personalities
- **Agent-to-agent messaging** (opt-in, allowlisted)

**Example use case:** One WhatsApp number, different agents for different customers:
```
Customer A (DM) → cataloging-agent
Customer B (DM) → support-agent  
Group "Pavisha Team" → operations-agent
```

### 2.3 Sub-Agents (Background Workers)

- **`sessions_spawn`**: Launch isolated background tasks
- Non-blocking: main agent continues while sub-agent works
- Configurable model per sub-agent (use cheaper models for simple tasks)
- Auto-announce results back to requester chat
- Max 8 concurrent (configurable)
- Auto-archive after 60 minutes

**Atomic capabilities:**
- `sessions_spawn(task, label, model, thinking, timeout, cleanup)`
- `sessions_list()` — List active/completed sub-agents
- `sessions_history(sessionKey)` — Read sub-agent transcripts
- `sessions_send(sessionKey, message)` — Send follow-up to running sub-agent

**AutifyME mapping:** Replaces the entire LangGraph orchestration layer. Instead of Project Manager → Department → Specialist agent hierarchy, use:
- Main agent as orchestrator
- Sub-agents as specialists (each with a focused task prompt)
- Skills as domain knowledge packages

### 2.4 Session Management

- **Main session**: direct chats collapse into one persistent session
- **Group sessions**: isolated per group
- **Sub-agent sessions**: isolated per task
- **Cron sessions**: isolated per scheduled job
- **Session compaction**: automatic context summarization when approaching limits
- **Memory flush**: auto-saves durable context before compaction

---

## 3. TOOL LAYER (Atomic Primitives)

### 3.1 File System

| Tool | Function |
|------|----------|
| `read` | Read any file (text, images). Supports offset/limit for large files. |
| `write` | Create or overwrite files. Auto-creates parent directories. |
| `edit` | Surgical text replacement (exact match). |

### 3.2 Shell Execution

| Tool | Function |
|------|----------|
| `exec` | Run any shell command. Foreground or background. PTY support for interactive CLIs. |
| `process` | Manage background sessions: poll, log, write stdin, send keys, kill. |

**Capabilities:**
- Foreground execution with timeout
- Background execution with yield (auto-background after N ms)
- PTY mode for interactive terminals (coding agents, TUIs)
- Environment variable injection
- Working directory control
- Exit notification (system event on completion)

**AutifyME mapping:** This is how we run TallyPrime commands, Python scripts, Node.js tools, database queries — anything.

### 3.3 Web Tools

| Tool | Function |
|------|----------|
| `web_search` | Brave Search API or Perplexity Sonar. Returns titles, URLs, snippets. |
| `web_fetch` | HTTP GET + readable extraction (HTML → markdown). No JS execution. |

**AutifyME mapping:** Replaces need for custom web scraping tools. Use for market research, competitor analysis, price checking, news monitoring.

### 3.4 Browser Automation

| Tool | Function |
|------|----------|
| `browser.start/stop` | Launch/kill managed browser |
| `browser.open` | Open URL in new tab |
| `browser.navigate` | Navigate existing tab |
| `browser.snapshot` | Get page accessibility tree (structured DOM) |
| `browser.screenshot` | Capture page as image |
| `browser.act` | Perform actions: click, type, press, hover, drag, select, fill |
| `browser.pdf` | Generate PDF from page |
| `browser.upload` | Upload files to page |
| `browser.console` | Read browser console logs |

**Profiles:**
- `openclaw`: Isolated managed browser (agent-only, no interference with personal browsing)
- `chrome`: Extension relay to system browser (for sites requiring existing login sessions)

**AutifyME mapping:** Replaces the entire Browser Automation Specialist design. Covers:
- Website intelligence (DOM crawling, section mapping, screenshots)
- Google Business Profile management
- IndiaMART/JustDial listing management
- Social media posting (Facebook, Instagram)
- Any web-based admin panel

### 3.5 Image Analysis

| Tool | Function |
|------|----------|
| `image` | Analyze image with vision model. Accepts file path or URL. |

**AutifyME mapping:** Replaces Visual Analyst and Image Analysis specialists. Product photo analysis, quality inspection, catalog image review.

### 3.6 Text-to-Speech (TTS)

| Tool | Function |
|------|----------|
| `tts` | Convert text to audio. Returns media path for sending. |

**Providers:** ElevenLabs, OpenAI, Edge TTS (free, no API key)
**AutifyME mapping:** Voice responses, audio summaries, accessibility.

### 3.7 Messaging Tools

| Tool | Function |
|------|----------|
| `message.send` | Send message to any channel target |
| `message.react` | Add emoji reaction |
| `message.poll` | Create polls |
| `message.broadcast` | Multi-target send |

---

## 4. AUTOMATION LAYER

### 4.1 Cron (Scheduled Jobs)

**Schedule types:**
- `at`: One-shot at absolute time (reminders, one-off tasks)
- `every`: Recurring interval (every N milliseconds)
- `cron`: Cron expression with timezone (e.g., "0 9 * * MON-FRI")

**Execution types:**
- `systemEvent` → Main session (injects text as system event)
- `agentTurn` → Isolated session (runs full agent turn with own context)

**Delivery:**
- `announce`: Post results to a channel
- `none`: Silent execution

**AutifyME mapping:** Replaces need for external schedulers. Covers:
- Daily business reports
- Scheduled social media posts
- Inventory check reminders
- Invoice generation triggers
- Customer follow-up reminders
- Market price monitoring

### 4.2 Heartbeats (Periodic Polling)

- Configurable interval (default ~30 min)
- Agent checks `HEARTBEAT.md` for pending tasks
- Batches multiple checks in one turn (email + calendar + notifications)
- Smart quiet hours (respects sleep schedule)

**AutifyME mapping:** Continuous monitoring — email inbox, order notifications, stock alerts, social mentions.

### 4.3 Webhooks (External Triggers)

- `POST /hooks/wake` — Wake agent with system event
- `POST /hooks/agent` — Run isolated agent turn from external trigger
- Token-authenticated
- Supports routing to specific agents

**AutifyME mapping:** Replaces custom WhatsApp webhook endpoint. External systems (payment gateways, shipping APIs, CRM events) can trigger agent actions.

### 4.4 Hooks (Event-Driven Automation)

- Trigger on: `/new`, `/reset`, `/stop`, lifecycle events
- Save session context to memory automatically
- Command logging for audit trails
- Custom automation on agent events

---

## 5. MEMORY & PERSISTENCE

### 5.1 File-Based Memory

| File | Purpose |
|------|---------|
| `MEMORY.md` | Curated long-term memory (private, main session only) |
| `memory/YYYY-MM-DD.md` | Daily logs (append-only) |
| `SOUL.md` | Agent personality and behavior rules |
| `USER.md` | User profile and preferences |
| `IDENTITY.md` | Agent identity (name, vibe, emoji) |
| `TOOLS.md` | Local environment notes (cameras, SSH, devices) |
| `HEARTBEAT.md` | Periodic task checklist |
| `AGENTS.md` | Agent operating instructions |

### 5.2 Memory Search (Semantic)

| Tool | Function |
|------|---------|
| `memory_search` | Semantic search across all memory files |
| `memory_get` | Read specific lines from memory files |

**Note:** Requires embedding API key (OpenAI/Google/Voyage). Currently not configured.

### 5.3 Session Persistence

- All sessions persisted to disk
- Survives gateway restarts
- Auto-compaction with summary preservation
- Pre-compaction memory flush (saves important context before summarization)

---

## 6. DEVICE & NODE LAYER

### 6.1 Paired Nodes (Mobile/Desktop)

| Capability | Function |
|-----------|----------|
| `nodes.camera_snap` | Take photo (front/back/both) |
| `nodes.camera_clip` | Record video clip |
| `nodes.screen_record` | Record device screen |
| `nodes.location_get` | Get device GPS location |
| `nodes.run` | Execute commands on node |
| `nodes.notify` | Send push notification to device |
| `nodes.invoke` | Call custom node commands |

**Supported nodes:** iOS, Android, macOS, headless Linux

**AutifyME mapping:** Future capabilities — factory floor monitoring via phone camera, delivery tracking via GPS, inventory scanning.

### 6.2 Canvas (UI Surface)

| Capability | Function |
|-----------|----------|
| `canvas.present` | Show HTML content on node |
| `canvas.navigate` | Navigate canvas to URL |
| `canvas.eval` | Execute JavaScript in canvas |
| `canvas.snapshot` | Capture canvas state |
| `canvas.a2ui_push` | Push AI-generated UI |

**AutifyME mapping:** Could be used for dashboards, approval UIs, real-time monitoring displays.

---

## 7. SKILLS SYSTEM

### 7.1 Skill Structure

```
skills/
  my-skill/
    SKILL.md          # Instructions + metadata (YAML frontmatter)
    scripts/          # Optional helper scripts
    prompts/          # Optional prompt templates
    assets/           # Optional reference files
```

### 7.2 Skill Features

- **Auto-discovery**: Drop a skill folder → agent learns it next session
- **Gating**: Skills can require specific binaries, env vars, or config
- **Environment injection**: Per-skill API keys and env vars
- **Hot reload**: File watcher detects changes mid-session
- **Precedence**: workspace > managed (~/.openclaw/skills) > bundled
- **ClawHub**: Public skill registry for sharing/installing

### 7.3 Skill Capabilities

Skills can:
- Teach the agent new domain knowledge (prompts, protocols)
- Provide scripts the agent can execute
- Reference external tools and APIs
- Define custom slash commands
- Include reference data (product catalogs, price lists, templates)

---

## 8. CONFIGURATION & ADMINISTRATION

### 8.1 Gateway Management

| Tool | Function |
|------|----------|
| `gateway.config.get` | Read current configuration |
| `gateway.config.patch` | Partial config update (merge) |
| `gateway.config.apply` | Full config replacement |
| `gateway.restart` | Restart gateway |
| `gateway.update.run` | Self-update |

### 8.2 Model Configuration

- **Multi-provider**: Anthropic, OpenAI, Google, Ollama, OpenRouter, Together, and 20+ more
- **Model failover**: Primary → fallback chain
- **Per-agent models**: Different models for different agents
- **Per-sub-agent models**: Cheaper models for background tasks
- **Thinking levels**: off, low, medium, high (for reasoning models)

### 8.3 Security

- Per-agent sandboxing (Docker containers)
- Per-agent tool allow/deny lists
- Exec approvals (allowlist mode)
- Gateway auth tokens
- Webhook auth tokens
- Node pairing with device-based trust

---

## 9. MAPPING: AutifyME Custom Code → OpenClaw Native

| AutifyME Component | Lines of Code | OpenClaw Replacement | Effort |
|-------------------|---------------|---------------------|--------|
| WhatsApp webhook + media client | ~800 | Channel (built-in) | Zero |
| LangGraph workflow orchestration | ~1500 | Sub-agents + Skills | Skill design |
| Project Manager agent | ~600 | Main agent + AGENTS.md | Configuration |
| Catalog Specialist | ~400 | Skill (SKILL.md + scripts) | 1 skill |
| Creative Specialist | ~300 | Skill (SKILL.md + image tool) | 1 skill |
| Visual/Catalog/Product Analysts | ~500 | Skill (SKILL.md + prompts) | 1 skill |
| HITL approval flow | ~400 | WhatsApp conversation (native) | Zero |
| State persistence (Supabase) | ~600 | Memory files + sessions | Zero |
| Error handling + retry | ~300 | Built-in retry + failover | Zero |
| LangSmith observability | ~200 | Session status + logs | Zero |
| Middleware (context, limits) | ~400 | Built-in session management | Zero |
| Database migrations + schema | ~500 | File-based (or exec + any DB) | Minimal |
| **Total** | **~6,600** | **~3 skills + config** | **Days, not months** |

---

## 10. WHAT OpenClaw CANNOT DO (Gaps to Address)

| Gap | Description | Workaround |
|-----|-------------|------------|
| **No native database** | No built-in SQL/Supabase | Use exec to run DB commands, or file-based storage |
| **No native image generation** | Can analyze but not generate images | Skill wrapping DALL-E/Midjourney/Gemini API via exec |
| **No native payment processing** | No billing/invoicing engine | Skill wrapping Razorpay/Stripe API, or TallyPrime integration |
| **No native e-commerce** | No product catalog database | File-based catalog + Supabase via exec, or Tally integration |
| **No native email** | No SMTP/IMAP built-in | Gmail API via webhook/exec, or skill |
| **No native CRM** | No contact/lead database | File-based + Supabase via exec |
| **Limited structured data** | Memory is Markdown files, not relational | Supplement with JSON files or external DB via exec |

**Key insight:** These gaps are all solvable via **Skills + exec**. OpenClaw doesn't need to be a database or payment processor — it just needs to know how to use them. That's what skills teach it.

---

## 11. ARCHITECTURE COMPARISON

### AutifyME Original (Custom Stack)
```
WhatsApp API → Webhook Server → LangGraph Orchestrator
                                    ├── Project Manager Agent
                                    │   ├── Cataloging Department
                                    │   │   ├── Catalog Specialist
                                    │   │   ├── Creative Specialist
                                    │   │   └── Tools (DB, Storage, Analysis)
                                    │   └── [Future Departments...]
                                    ├── Supabase (State + Data)
                                    ├── LangSmith (Observability)
                                    └── HITL Engine
```

### AutifyME on OpenClaw (Skills-Based)
```
Any Channel → OpenClaw Gateway → Main Agent (orchestrator)
                                    ├── Skills (domain knowledge)
                                    │   ├── product-cataloging/
                                    │   ├── accounting-tally/
                                    │   ├── marketing/
                                    │   ├── crm/
                                    │   └── [any new skill...]
                                    ├── Sub-agents (parallel workers)
                                    ├── Browser (web automation)
                                    ├── Exec (any CLI/script/API)
                                    ├── Memory (file-based persistence)
                                    ├── Cron (scheduled automation)
                                    └── Webhooks (external triggers)
```

**The shift:** From building infrastructure to building intelligence. Every line of code in a skill is pure business logic — no boilerplate, no plumbing.

---

*This document serves as the foundation for designing AutifyME skills on the OpenClaw platform.*
