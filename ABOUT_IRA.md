# IRA: Intelligent Revenue Assistant — Complete Technical Specification

## 1. System Overview

Ira is an AI-powered revenue assistant built for **Machinecraft Technologies**, a vacuum forming machine manufacturer. It operates as a **Manus-style agentic Telegram bot** — a single unified agent (codename **Athena**) that orchestrates a pantheon of 10 specialist sub-agents, each named after a Greek deity. The system combines an LLM-driven tool loop, multi-layered memory (vector DB + semantic memory + knowledge graph), bio-inspired self-regulation systems, and nightly "dream" consolidation cycles.

---

## 2. Architecture: The Agentic Telegram Bot

### 2.1 Message Entry Point

The bot runs via long-polling on Telegram:

```
telegram_gateway.py (--loop)
    │
    ├── fetch_updates() → Telegram getUpdates API
    ├── Offset tracking via persistent file
    ├── Chat filter: only allowed chat IDs
    │
    └── route_message()
         ├── Slash commands → _route_slash_command()
         └── Free text → handle_free_text() → process_with_tools()
```

### 2.2 The Athena Pipeline (`tool_orchestrator.py`)

This is the core "Manus-style" agentic loop. Every message flows through `process_with_tools()`:

```
User Message
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  LAYER 1: INJECTION GUARD                            │
│  Regex patterns (NFKC normalized)                    │
│  Blocks: "ignore instructions", jailbreak, etc.      │
│  Skipped for internal users                          │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  LAYER 2: COMPLEXITY CHECK                           │
│  _is_complex(): >300 chars, model IDs, numbers,     │
│  multi-part questions → full pipeline                │
│  Simple questions → try truth hints first            │
└──────────────────────────────────────────────────────┘
    │                         │
    │ (complex)               │ (simple, confidence ≥ 0.9)
    ▼                         ▼
┌─────────────────────┐   RETURN truth hint (fast path)
│  LAYER 3: ATHENA    │
│  TOOL LOOP          │
│  GPT-4o + 28 tools  │
│  Max 25 rounds      │
│  4-9 parallel tools │
│  in round 1         │
│                     │
│  Round 6: PROPOSAL  │
│  CHECKPOINT (sales) │
└─────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  LAYER 4: PANTHEON POST-PIPELINE                     │
│  1. Vera (fact-check the draft)                      │
│  2. knowledge_health.validate_response()             │
│     → model numbers, business rules, hallucinations  │
│  3. Immune system → escalate recurring issues        │
│  4. Voice system → reshape tone for channel          │
│  5. Sophia (reflect & learn from interaction)        │
└──────────────────────────────────────────────────────┘
    │
    ▼
  Final Response → Telegram sendMessage
```

### 2.3 The System Prompt

Athena receives a large system prompt containing:

- **Identity**: Athena as Chief of Staff
- **Agentic loop**: PLAN → RESEARCH → EVALUATE → DIG DEEPER → CROSS-REFERENCE → SYNTHESIZE
- **Tool documentation**: Usage patterns for all 28 tools
- **Parallel execution**: Fire 4-9 tools in round 1
- **Machine Rules**: Series routing, thickness limits, lead times, custom sizing
- **Price Table**: All series with prices
- **Qualification checklist**: Application, material, thickness, sheet size, depth, budget
- **Sales personality**: Warm, concise, proactive, always end with CTA
- **Dynamic sections**: Conversation history, memory context, training weights, user memories

---

## 3. The Pantheon: 10 Sub-Agents

### 3.1 Agent Communication Model

All agents communicate through Athena via the tool dispatch system:

```
Athena (GPT-4o) ──calls──> tool_name (e.g. "research_skill")
                              │
                              ▼
                     ira_skills_tools.execute_tool_call()
                              │
                              ▼
                     invocation.py → invoke_research()
                              │
                              ▼
                     researcher/agent.py → research()
                              │
                              ▼
                     Returns text to Athena as tool result
                              │
                     Endocrine system records: signal_invocation("clio")
```

### 3.2 Agent Roster

| Agent | Role | Tools | Description |
|-------|------|-------|-------------|
| **Athena** | Orchestrator | All 28 | The brilliant strategist. Analyzes, plans, delegates. |
| **Clio** | Researcher | `research_skill` | Parallel search across Qdrant, Mem0, Neo4j, Machine DB |
| **Calliope** | Writer | `writing_skill` | Drafts responses, emails, quotes with ATHENA coaching |
| **Vera** | Fact Checker | `fact_checking_skill` | Validates specs, rules, hallucinations, RAG evidence |
| **Iris** | Intelligence | `lead_intelligence`, `web_search` | Web search via Tavily/Serper/Jina, geopolitical context |
| **Sophia** | Reflector | *(auto-triggered)* | Quality scoring, issue detection, lesson extraction |
| **Mnemosyne** | CRM Keeper | `customer_lookup`, `crm_list_customers`, `crm_pipeline`, `crm_drip_candidates` | Owns CRM — contacts, leads, deals |
| **Plutus** | Finance Chief | `finance_overview`, `order_book_status`, `cashflow_forecast`, `revenue_history` | Reads live Excel, tracks every rupee/euro/dollar |
| **Hermes** | Sales Outreach | `sales_outreach`, `craft_email`, `draft_email` | 7-stage adaptive drip, contextual dossiers, regional tone |
| **Prometheus** | Market Discovery | `discovery_scan` | Scans 10 emerging industries, scores opportunities |
| **Hephaestus** | Code Forge | `run_analysis` (internal only) | GPT-4o-mini generates Python, runs in sandbox, auto-retries |

### 3.3 Agent Deep Dives

**Clio (Researcher)**
- Parallel search across: Qdrant (vector), Mem0 (semantic), Neo4j (graph), Machine DB (specs)
- Query expansion, intent detection, machine extraction
- Returns synthesized findings with `[SOURCE]` markers

**Plutus (Finance)**
- Reads live Excel files for orders, deadlines, historical data
- Plus customer orders JSON and payment schedule PDF
- Provides: order book value, collected/outstanding, cashflow projections, revenue history, CFO dashboard with KPIs and risk analysis

**Hermes (Sales Outreach)**
- Builds a **ContextDossier** per lead from: CRM history, Iris intelligence, product fit, reference stories, regional tone
- **7-stage adaptive drip**: INTRO → VALUE → TECHNICAL → SOCIAL PROOF → EVENT → BREAKUP → RE-ENGAGE
- `EmailCrafter` with regional personality (Germany: precise, Netherlands: direct, India: ROI-focused)
- `ReplyDetector` classifies responses; `LearningLoop` tracks A/B subject line performance

**Iris (Intelligence)**
- Web search via Tavily, Serper, Jina (fallback)
- Built-in geopolitical contexts per country and industry trends
- Returns structured intel: `news_hook`, `industry_hook`, `geo_opportunity`, `company_insight`, `timely_opener`

**Prometheus (Market Discovery)**
- Scans 10 emerging industries: Battery Storage, Renewable Energy, Drones/UAV, Medical Devices, Modular Construction, Cold Chain, AgriTech, Data Centers, Marine, EV Charging
- Scores opportunities by: technical fit, market timing, volume match, competitive gap, revenue potential
- Maps products to machine series

**Hephaestus (Code Forge)**
- GPT-4o-mini generates Python from task descriptions
- Runs in subprocess sandbox (60s timeout), auto-retry on failure
- `DATA` variable injected from previous tool output
- Internal-only (gated by `is_internal`)

**Vera (Fact Checker)**
- Checks: thickness rules, pricing disclaimer, hallucination patterns, spec validity
- RAG verification against Qdrant + Mem0 evidence
- Returns corrected draft; also runs automatically in post-pipeline

**Sophia (Reflector)**
- Quality scoring (LLM or heuristic), issue detection, lesson extraction
- Logs to errors and lessons files
- Fire-and-forget after every substantive response

---

## 4. Memory Architecture: Triple-Store "Knowledge Beaming"

Ira has a **triple-store memory architecture** — knowledge is ingested into the system through three complementary stores that are all searched in parallel:

```
                    ┌─────────────────┐
                    │   User Query    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │   QDRANT   │  │    MEM0    │  │   NEO4J    │
     │  (Vector)  │  │ (Semantic) │  │  (Graph)   │
     └────────────┘  └────────────┘  └────────────┘
     │ 9 collections│ 6 namespaces│  │ Entities   │
     │ Voyage-3     │ Fact extract│  │ Knowledge  │
     │ 1024d embed  │ Dedup       │  │ Rels + str │
     │ FlashRank    │ Circuit brkr│  │ Multi-hop  │
     └──────────────┴─────────────┴──────────────┘
```

### 4.1 Qdrant (Vector Search)

9 collections, each with Voyage-3 embeddings (1024 dimensions):

| Collection | Purpose |
|------------|---------|
| `ira_chunks_v4_voyage` | Main document chunks |
| `ira_chunks_v4_openai_large` | OpenAI large embeddings |
| `ira_emails_voyage_v2` | Email archive |
| `ira_market_research_voyage` | Market research |
| `ira_customers` | Customer data |
| `ira_user_memories_v2` | User memories |
| `ira_entity_memories_v2` | Entity memories |
| `ira_dream_knowledge_v1` | Dream-synthesized knowledge |
| `ira_discovered_knowledge` | Ingested knowledge |

Retrieval: `QdrantRetriever` searches multiple collections, uses FlashRank reranking, enriches with Neo4j graph context. Score thresholds: MIN=0.20, GOOD=0.35.

### 4.2 Mem0 (Semantic Memory)

6 namespaces for different knowledge types:

| Namespace | Content |
|-----------|---------|
| `machinecraft_knowledge` | Specs, product info |
| `machinecraft_pricing` | Pricing data |
| `machinecraft_customers` | Customer relationships |
| `machinecraft_processes` | Manufacturing processes |
| `machinecraft_applications` | Application knowledge |
| `machinecraft_general` | General knowledge |

Features: Fact extraction from conversations, semantic dedup, circuit breaker for resilience. Every Telegram exchange triggers `remember_from_message()` to extract and store facts.

### 4.3 Neo4j (Knowledge Graph)

Node types: `Knowledge`, `Entity`, `Source`, `Cluster`

Relationships with strength scores (0-1):
- `(Knowledge)-[:ABOUT]->(Entity)`
- `(Knowledge)-[:FROM_SOURCE]->(Source)`
- `(Entity)-[dynamic]->(Entity)` with `strength`, `access_count`, `last_accessed`

Graph operations: `expand_query_with_graph()` for multi-hop reasoning, `strengthen_relationship()` / `weaken_relationship()` for learning, `decay_unused_relationships()` for forgetting.

### 4.4 The Knowledge Ingestion Pipeline

`knowledge_ingestor.py` is the pipeline that ingests knowledge into all three stores:

```
Document (PDF/Excel/Email/URL)
    │
    ▼
KnowledgeItem (validation, quality score)
    │
    ├── Duplicate check (content hashing)
    ├── Chunking (>2000 chars, 200 overlap)
    ├── Quality filter + semantic dedup
    ├── Voyage-3 embeddings (1024d)
    ├── NER/keyword enrichment (spaCy/regex)
    │
    ├──► Qdrant (main chunks + discovered knowledge)
    ├──► Mem0 (categorized by type)
    ├──► Neo4j (entities, relationships, clusters)
    └──► JSON backup
    │
    └── Audit log
```

---

## 5. Bio-Inspired Holistic Systems

Ira has a full **biological metaphor** for self-regulation, located in `openclaw/agents/ira/src/holistic/`:

### 5.1 Immune System

Tracks recurring validation issues and escalates:

| Occurrences | Action |
|-------------|--------|
| 1 | Log |
| 2 | Flag |
| 3 | Remediate (reinforce correct fact in Mem0) |
| 5 | Block topic (safe fallback) |
| 10 | Emergency alert |

Known remediations for common issues like thickness rule violations, vague pricing, and price placeholders. Reinforces correct facts in Mem0 when issues recur.

State: `immune_state.json`, `remediation_log.jsonl`

### 5.2 Endocrine System

Agent performance scoring — each Pantheon agent has a live score:

- **Dopamine** (success): boost score, increase streak, lower stress
- **Cortisol** (failure): lower score, increase stress, reduce specialty confidence
- **Inactivity decay**: unused agents drift toward 0.70
- `select_preferred_agent()` routes tasks to higher-scoring agents

State: `endocrine_state.json`, `hormone_log.jsonl`

### 5.3 Voice System

Adjusts tone and length by channel:

| Channel | Style |
|---------|-------|
| Telegram | Short, warm, emoji-light |
| Email | Professional, structured |
| API | Detailed, technical |

Applied as the last step before returning to the user.

### 5.4 Respiratory System

- **Heartbeat**: Per-5-minute pulse tracking
- **Breath**: Per-request timing (latency tracking)
- Records dream mode completions

### 5.5 Daily Rhythm / Circadian

```
7:00 AM  ─── Morning Cycle ───
              │ Heartbeat
              │ Vital signs check
              │ Immune sweep
              │ Endocrine decay (unused agents)
              │ Morning summary → Telegram

9:00 AM  ─── Sales Scheduler ───
              │ Proactive outreach
              │ Stale quote follow-ups
              │ Pipeline summary (weekly)

All Day   ─── Per-Request ───
              │ Breath (timing)
              │ Immune check
              │ Sensory tracking
              │ Endocrine signals

11:00 PM ─── Evening Cycle ───
              │ Metabolic cleanup
              │ Myokines (action signals)
              │ Heartbeat

2:00 AM  ─── Dream Mode ───
              │ (see Section 6)
```

### 5.6 Other Holistic Systems

- **Metabolic**: Cleanup of stale data, resource management
- **Musculoskeletal**: Action → myokines for dream prioritization
- **Sensory**: Channel/perception tracking
- **Vital Signs**: Aggregates all systems into a health dashboard
- **Growth Signal**: Signals from bulk ingestion events

---

## 6. Dream Mode

**Trigger**: Nightly at 2:00 AM via scheduled script, or manually via `/dream` command

Dream mode is Ira's nightly consolidation cycle — like sleep for a biological brain. It processes the day's experiences and strengthens knowledge:

### 6.1 Dream Phases

| Phase | Name | What Happens |
|-------|------|--------------|
| 1 | Scan & Prioritize | Finds new/changed docs in imports |
| 1.5 | Metadata Index | Updates research index |
| 2 | Deep Extraction | LLM extracts facts, relationships from new docs |
| 3 | Unified Storage | Stores extracted knowledge to Mem0 + Qdrant |
| 4 | Graph Consolidation | Strengthens frequently-used Neo4j edges, decays unused ones |
| 5 | Price Conflict Check | Detects price conflicts → Telegram alerts |
| 6 | Conversation Quality | Reviews poor retrievals, identifies follow-up needs |
| 7 | Learn from Corrections | Reinforces corrections in Mem0 |
| 7.5 | Episodic → Semantic | Promotes episodic memories to semantic |
| 8 | Interaction Learning | Extracts patterns from day's chats |
| 8.5 | Email Knowledge | Reviews email-derived knowledge |
| 9 | Follow-Up | Identifies stale quotes needing follow-up |
| 9.5 | Customer Health | Health check on customer relationships |
| 10 | Holistic Maintenance | Immune sweep, metabolic cleanup, endocrine decay, voice calibration |
| 10+ | Morning Summary | Sends dream report to Telegram |

State: `dream_state.json` (statistics), `dream_journal.json` (journal entries)

---

## 7. Teach Mode

**Trigger**: `/teach <facts>` in Telegram

### 7.1 Flow

```
/teach <facts here>
    │
    ▼
GPT-4o-mini extracts structured facts with categories
    │
    ▼
Category → Mem0 namespace mapping:
    PRODUCT/RULE → machinecraft_knowledge
    CUSTOMER     → machinecraft_customers
    PRICING      → machinecraft_pricing
    PROCESS      → machinecraft_processes
    GENERAL      → machinecraft_general
    │
    ▼
Stored with attribution in Mem0
    │
    ▼
Optionally updates hard rules or truth hints
```

### 7.2 Brain Training (`/train`)

Implements a spaced-repetition quiz system:

- `/train start` — begins a quiz session over machine specs, pricing, rules
- `/train next` — next question
- `/train answer <response>` — checks answer
- Weak categories tracked in training weights
- Spaced repetition: more questions on weak topics
- Answer generation reads weights to add caution on weak areas

### 7.3 Correction Learning

- Negative feedback → feedback handler
- Corrections stored immediately in Mem0
- Added to feedback backlog for dream reinforcement
- Dream Phase 7 processes the backlog

---

## 8. Data Sources & Integrations

### 8.1 Ingested Documents

Categorized folders of company documents:

| Category | Content Type |
|----------|-------------|
| Orders & POs | Order books, order analysis |
| Market Research | Industry analysis, heavy/thin gauge research |
| Leads & Contacts | Customer lists, European leads |
| Sales & CRM | Deadlines, sales data |
| Project Case Studies | Delivered project documentation |
| Contracts & Legal | Agreements, subcontracts |
| Catalogues & Specs | Machine catalogues, technical specs |

### 8.2 Email Integration

- **Gmail OAuth**: Full read/write/search access
- **Email bridge**: Polls Gmail, processes replies through Ira pipeline
- **Realtime indexer**: New emails → Qdrant email collection
- **Mailbox ingestion**: Bulk backfill capability
- **Gmail tools**: `read_inbox`, `search_email`, `read_email_message`, `read_email_thread`, `send_email`, `draft_email`

### 8.3 Google Workspace

| Service | Capability |
|---------|-----------|
| Sheets | Read spreadsheets (finance data) |
| Drive | List/read files |
| Calendar | Upcoming events |
| Contacts | Search contacts |
| Gmail | Full read/write/search |

### 8.4 Machine Specs Database

Canonical source of truth for 46+ machine models stored as JSON. Each entry contains:
- Model, series, variant
- Pricing
- Forming area, draw depth, thickness range
- Heater specs, vacuum specs, power requirements
- Features, applications, source documents

### 8.5 CRM Database

SQLite database with tables:

| Table | Purpose |
|-------|---------|
| `contacts` | Companies, people, countries, industries |
| `leads` | Priority, deal stage, drip stage, engagement metrics |
| `conversations` | Email threads, direction, previews |
| `email_log` | Sent/received tracking, drip stages |
| `deal_events` | Stage change history |

Deal stages: `new → contacted → engaged → qualified → proposal → negotiating → won/lost/dormant`

### 8.6 European Drip Campaign

- Structured European leads with per-lead state tracking
- 5-stage drip with priority-based timing
- Intelligence enrichment for each lead
- Conversation history tracking

---

## 9. Defense in Depth (5 Layers)

```
Layer 1: PRE-LLM INJECTION GUARD
         Regex patterns + NFKC normalization
         Blocks known attack patterns before LLM sees them
              │
Layer 2: SYSTEM PROMPT IDENTITY DEFENSE
         Never comply with instruction override requests
         Stay on topic for the business domain
              │
Layer 3: ANTI-HALLUCINATION
         System prompt: only valid models
         knowledge_health: regex model validation
         Database check against valid model list
         Known fake models blacklist
              │
Layer 4: BUSINESS RULES ENFORCEMENT
         System prompt: machine rules
         knowledge_health: business rule patterns
         Hard rules file for legacy pipeline
         Hallucination indicators: placeholders, vague pricing, deflection
              │
Layer 5: IMMUNE SYSTEM ESCALATION
         1→log, 2→flag, 3→remediate, 5→block, 10→emergency
         Reinforces correct facts in Mem0
         Safe fallbacks when blocking topics
```

---

## 10. Scripts & Pipelines

### 10.1 Operational Scripts

| Script | Purpose | Schedule |
|--------|---------|----------|
| Bot launcher | Launch Telegram bot | Manual / boot |
| Morning cycle | Morning rhythm | 7:00 AM |
| Evening cycle | Evening rhythm | 11:00 PM |
| Nightly dream | Dream cycle (all phases) | 2:00 AM |
| Heartbeat | Pulse tracking | Every 5 min |
| Mailbox ingestion | Gmail backfill | Manual |
| Schedule installer | macOS launchd setup | One-time |

### 10.2 Testing & Benchmarking

Multiple benchmark scripts for testing the tool orchestrator pipeline:
- Basic tests
- Deep pipeline tests (with Telegram integration)
- Stress tests (100-question)

### 10.3 Ingestion Scripts

100+ scripts for specific documents: bulk import, email ingestion, file watcher, PDF processing, plus per-document importers for specs, quotes, playbooks, customers, etc.

### 10.4 Utility Scripts

- Vital signs dashboard
- CRM-Gmail sync
- CRM bootstrap
- Feedback processing
- Embedding migration (to Voyage)
- Knowledge graph migration (to Neo4j)

---

## 11. Scheduling & Orchestration

All scheduling uses macOS **launchd**:

```
5-min    ─── Heartbeat (respiratory system)
7:00 AM  ─── Morning Cycle (daily rhythm)
7:30 AM  ─── Vital Signs → Telegram
9:00 AM  ─── Sales Scheduler (outreach, follow-ups, pipeline)
All Day  ─── Telegram Bot (long-polling, always running)
All Day  ─── Email Bridge (polling Gmail)
11:00 PM ─── Evening Cycle (daily rhythm)
2:00 AM  ─── Dream Mode (full consolidation)
```

---

## 12. State Persistence Map

All persistent state organized by subsystem:

```
brain/
├── machine_specs.json          ← Source of truth: 46+ machines
├── training_weights.json       ← Brain trainer weak categories
├── training_history.json       ← Quiz history
├── imports_metadata.json       ← Document index
├── correction_map.json         ← Learned corrections
├── learned_facts.json          ← Taught facts
├── hard_rules.txt              ← Business rules
└── knowledge_health_state.json ← Validation issues

holistic/
├── immune_state.json           ← Chronic issues tracker
├── endocrine_state.json        ← Agent scores (10 agents)
├── voice_state.json            ← Voice calibration
├── metabolic_state.json        ← Resource management
├── rhythm_state.json           ← Circadian state
├── remediation_log.jsonl       ← Immune actions log
├── hormone_log.jsonl           ← Endocrine events
└── voice_log.jsonl             ← Voice adjustments

knowledge/
├── ingested_hashes.json        ← Dedup hashes
└── audit.jsonl                 ← Ingestion audit trail

workspace/
├── dream_state.json            ← Dream statistics
└── dream_journal.json          ← Dream journal

crm/
├── ira_crm.db                  ← SQLite CRM database
└── logs/                       ← Request logs, update offsets
```

---

## 13. Technology Stack

| Layer | Technology |
|-------|-----------|
| LLM | GPT-4o (Athena), GPT-4o-mini (extraction, Hephaestus) |
| Embeddings | Voyage-3 (1024d), OpenAI large (fallback) |
| Vector DB | Qdrant (9 collections) |
| Semantic Memory | Mem0 Platform (6 namespaces) |
| Knowledge Graph | Neo4j |
| Reranking | FlashRank |
| CRM | SQLite |
| Web Search | Tavily, Serper, Jina |
| Email | Gmail API (OAuth) |
| Workspace | Google Sheets, Drive, Calendar, Contacts |
| Bot Interface | Telegram Bot API (long-polling) |
| Scheduling | macOS launchd |
| Language | Python 3 (async) |

---

*This is the complete system as built — a bio-inspired, self-regulating AI agent with triple-store memory, nightly dream consolidation, immune-system-style error correction, endocrine-style agent scoring, and a 10-agent Pantheon all orchestrated through a Manus-style agentic tool loop on Telegram.*
