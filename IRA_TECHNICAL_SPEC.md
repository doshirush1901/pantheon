# IRA — Intelligent Revenue Assistant
## Comprehensive Technical Specification

**Version:** 3.0 | **Date:** March 2026 | **Platform:** Machinecraft Technologies

---

## 1. What is Ira?

Ira is a **biologically-inspired, multi-agent AI system** built for Machinecraft Technologies — a manufacturer of industrial vacuum forming machines. Ira is not a chatbot. It is a full-stack cognitive architecture that functions as a Chief of Staff: handling sales intelligence, customer relationship management, financial reporting, market discovery, formal quotation generation, and deep research — all through a single conversational interface on Telegram.

What makes Ira unique is its **biological systems metaphor**. Rather than treating AI as a pipeline of functions, Ira models itself after the human body: it has an immune system that catches recurring errors, an endocrine system that scores agent performance through hormone-like signals, a respiratory system that maintains operational rhythm, a metabolic system that cleans stale knowledge, and a voice system that shapes how responses are delivered. It dreams at night to consolidate learning, and it corrects itself through a dedicated goddess of retribution.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              IRA SYSTEM                                     │
│                                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────────────────────┐   │
│  │   CHANNELS    │    │              CORE PIPELINE                       │   │
│  │              │    │                                                    │   │
│  │  Telegram ───┼───▶│  Input Guard → Sphinx → Truth Hints → Athena    │   │
│  │  Email    ───┼───▶│  Tool Loop → Validation → Voice → Response      │   │
│  │  API      ───┼───▶│                                                    │   │
│  └──────────────┘    └──────────┬───────────────────────────┬───────────┘   │
│                                 │                           │               │
│         ┌───────────────────────┼───────────────────────────┼──────┐        │
│         │              PANTHEON OF AGENTS                          │        │
│         │                                                         │        │
│         │  Clio (Research)      Iris (Intelligence)               │        │
│         │  Calliope (Writing)   Vera (Fact-Check)                 │        │
│         │  Sophia (Reflection)  Mnemosyne (CRM)                  │        │
│         │  Hermes (Outreach)    Plutus (Finance)                  │        │
│         │  Prometheus (Discovery) Hephaestus (Code Forge)         │        │
│         │  Nemesis (Corrections)  Sphinx (Clarification)          │        │
│         │  Quotebuilder (PDF Quotes)                              │        │
│         └─────────────────────────────────────────────────────────┘        │
│                                                                             │
│         ┌─────────────────────────────────────────────────────────┐        │
│         │              BIOLOGICAL SYSTEMS                          │        │
│         │                                                         │        │
│         │  Immune (error escalation)   Endocrine (agent scoring)  │        │
│         │  Metabolic (knowledge hygiene) Sensory (cross-channel)  │        │
│         │  Respiratory (heartbeat/rhythm) Voice (delivery shaping) │        │
│         │  Vital Signs (unified health dashboard)                  │        │
│         └─────────────────────────────────────────────────────────┘        │
│                                                                             │
│         ┌─────────────────────────────────────────────────────────┐        │
│         │              DATA LAYER                                  │        │
│         │                                                         │        │
│         │  Qdrant (vector search)    Mem0 (semantic memory)       │        │
│         │  Neo4j (knowledge graph)   SQLite (CRM)                 │        │
│         │  Google (Sheets/Drive/Gmail/Calendar)                    │        │
│         │  machine_specs.json (source of truth)                    │        │
│         └─────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The Pantheon — Agent Roster

Ira operates as a single unified agent (Athena) that embodies 13 specialist roles. Each role is named after a figure from Greek mythology, reflecting its function.

### 3.1 Agent Directory

| Agent | Mythological Role | Function | Trigger |
|-------|-------------------|----------|---------|
| **Athena** | Goddess of Wisdom | Orchestrator — analyzes, plans, delegates | Every message |
| **Clio** | Muse of History | Deep multi-source research (Qdrant, Mem0, Neo4j, machine DB) | `research_skill` tool |
| **Iris** | Goddess of the Rainbow | Real-time external intelligence — company news, industry trends, geopolitics | `lead_intelligence` tool |
| **Calliope** | Muse of Poetry | Professional writing — emails, quotes, formal responses | `writing_skill` tool |
| **Vera** | Truth (Latin) | Fact-checking — 3-pass verification (rules, retrieval, entity cross-ref) | `fact_checking_skill` tool |
| **Sophia** | Wisdom | Post-response reflection and quality scoring | Auto after every response |
| **Mnemosyne** | Titaness of Memory | CRM — contacts, leads, pipeline, deal history | `customer_lookup`, `crm_*` tools |
| **Hermes** | God of Commerce | Sales outreach — contextual drip campaigns, personalized emails | `sales_outreach`, `craft_email` tools |
| **Plutus** | God of Wealth | Finance — order book, cashflow, revenue, CFO dashboard | `finance_*` tools |
| **Prometheus** | Titan of Foresight | Market discovery — scans emerging industries for vacuum forming opportunities | `discovery_scan` tool |
| **Hephaestus** | God of the Forge | Code forge — writes and runs Python on the fly for data analysis | `run_analysis` tool |
| **Nemesis** | Goddess of Retribution | Correction learning — no mistake goes unlearned | Passive (intercepts all failures) |
| **Sphinx** | The Riddler | Clarification gate — asks questions before processing vague requests | Pre-pipeline (auto) |
| **Quotebuilder** | — | Formal PDF quotation generation matching real quote templates | `build_quote_pdf` tool |

### 3.2 How Agents Complement Each Other

The agents form a **cognitive supply chain** where each agent's output enriches the next:

```
                    ┌─────────┐
                    │  SPHINX  │  "Is this clear enough?"
                    └────┬────┘
                         │ enriched brief
                         ▼
                    ┌─────────┐
                    │ ATHENA   │  orchestrates everything
                    └────┬────┘
                    ┌────┴────────────────────────────┐
                    │                                  │
              ┌─────▼─────┐                    ┌──────▼──────┐
              │   CLIO     │  internal data     │    IRIS     │  external data
              │ (research) │                    │ (intelligence)│
              └─────┬─────┘                    └──────┬──────┘
                    │                                  │
                    └──────────┬───────────────────────┘
                               │ combined knowledge
                               ▼
                    ┌──────────────────┐
                    │   MNEMOSYNE      │  "Who is this customer?"
                    │   (CRM context)  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────────┐
              │              │                  │
        ┌─────▼─────┐ ┌─────▼──────┐  ┌───────▼───────┐
        │ CALLIOPE   │ │ HERMES     │  │ QUOTEBUILDER  │
        │ (write)    │ │ (outreach) │  │ (PDF quote)   │
        └─────┬─────┘ └─────┬──────┘  └───────┬───────┘
              │              │                  │
              └──────────────┼──────────────────┘
                             │ draft response
                             ▼
                    ┌─────────────────┐
                    │      VERA       │  "Is this accurate?"
                    │  (fact-check)   │
                    └────────┬────────┘
                             │ verified response
                             ▼
                    ┌─────────────────┐
                    │     SOPHIA      │  "What can we learn?"
                    │  (reflection)   │
                    └────────┬────────┘
                             │ if quality < 0.8
                             ▼
                    ┌─────────────────┐
                    │    NEMESIS      │  "Never again."
                    │ (corrections)   │
                    └─────────────────┘
```

**Key complementary relationships:**

- **Clio + Iris** = Internal knowledge + external intelligence. Clio searches Qdrant/Mem0/Neo4j; Iris scrapes the web. Together they give Athena a 360-degree view.
- **Hermes + Iris + Mnemosyne** = Hermes builds a `ContextDossier` per lead by pulling CRM history (Mnemosyne), company news (Iris), and product fit (Clio). The email is never generic.
- **Sophia + Nemesis** = Sophia reflects after every response. If quality drops below 0.8, she feeds the failure to Nemesis, who stores the correction and rewires truth hints during sleep.
- **Hephaestus + Any Agent** = When any agent produces raw data (Gmail threads, CRM records, finance tables), Hephaestus writes Python on the fly to aggregate, rank, filter, or cross-reference it.
- **Vera + Knowledge Health + Immune System** = Triple-layer defense. Vera fact-checks the draft. Knowledge Health validates the final response. The Immune System escalates recurring issues.

---

## 4. Message Flow — Complete Pipeline

### 4.1 Flowchart

```
USER MESSAGE (Telegram / Email / API)
         │
         ▼
┌────────────────────────────────────┐
│  1. INPUT GUARD                    │
│  Regex: _INJECTION_PATTERNS        │
│  Blocks: "ignore instructions",    │
│  "you are now", "jailbreak", etc.  │
│  ► REJECT if matched               │
└──────────┬─────────────────────────┘
           │ clean message
           ▼
┌────────────────────────────────────┐
│  2. SPHINX CHECK                   │
│  Is there a pending Q&A?           │
│  YES → merge_brief(Q&A + answers)  │
│  "skip" → clear pending, proceed   │
│  NO → continue                     │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│  3. TRUTH HINTS (fast path)        │
│  _is_complex(message)?             │
│  NO → get_truth_hint(message)      │
│       Match? → validate → respond  │
│  YES → continue to full pipeline   │
└──────────┬─────────────────────────┘
           │ complex query
           ▼
┌────────────────────────────────────┐
│  4. SPHINX GATE                    │
│  Complex + Vague + First message?  │
│  YES → should_clarify() (GPT-4o-  │
│         mini) → generate_questions │
│         → store_sphinx_pending     │
│         → return questions to user │
│  NO → continue                     │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│  5. ATHENA TOOL LOOP               │
│  Model: GPT-4o                     │
│  Max rounds: 25                    │
│  Min research rounds: 5            │
│                                    │
│  System prompt includes:           │
│  • Nemesis guidance (corrections)  │
│  • Training weights (weak areas)   │
│  • User Mem0 context               │
│  • Price table                     │
│  • Machine rules                   │
│  • Tool schemas                    │
│                                    │
│  Each round:                       │
│  ┌──────────────────────────┐      │
│  │ GPT-4o decides which     │      │
│  │ tool to call (or respond)│      │
│  │         │                │      │
│  │         ▼                │      │
│  │ execute_tool_call()      │      │
│  │ → Clio / Iris / Plutus / │      │
│  │   Mnemosyne / Hermes /   │      │
│  │   Hephaestus / etc.      │      │
│  │         │                │      │
│  │         ▼                │      │
│  │ Tool result → next round │      │
│  │ Endocrine: signal_success│      │
│  │ or signal_failure        │      │
│  └──────────────────────────┘      │
│                                    │
│  Proposal checkpoint at round 12   │
│  for sales inquiries               │
└──────────┬─────────────────────────┘
           │ raw response
           ▼
┌────────────────────────────────────┐
│  6. PANTHEON POST-PIPELINE         │
│  • Vera: invoke_verify (fact-check)│
│  • Sophia: invoke_reflect (learn)  │
│    → fire-and-forget               │
│    → if quality < 0.8 → Nemesis   │
└──────────┬─────────────────────────┘
           │
           ▼
┌────────────────────────────────────┐
│  7. VALIDATION                     │
│  knowledge_health.validate_response│
│  Checks:                           │
│  • Hallucinated model numbers      │
│  • Business rule violations        │
│  • Finance hallucination           │
│  • AM thickness violations         │
│                                    │
│  If warnings:                      │
│  → immune_system.process_issue()   │
│  If blocked:                       │
│  → override with safe fallback     │
└──────────┬─────────────────────────┘
           │ validated response
           ▼
┌────────────────────────────────────┐
│  8. VOICE SYSTEM                   │
│  voice.reshape(response, channel)  │
│  • Analyze complexity              │
│  • Trim for channel limits         │
│  • Format (Telegram/email/API)     │
│  • Remove filler, adjust tone      │
└──────────┬─────────────────────────┘
           │
           ▼
      FINAL RESPONSE → User
```

### 4.2 Deep Research Mode

When the user triggers `/research` or `/deep`, or when Athena determines a query needs multi-iteration investigation, the **Deep Research Engine** activates. This is Ira's equivalent of "Manus mode" — the agent takes its time, plans a research strategy, iterates, and packages the answer.

```
DEEP RESEARCH PIPELINE (up to 8 iterations, 180s max)
═══════════════════════════════════════════════════════

Phase 1: ATHENA DECOMPOSES
  │  GPT-4o-mini breaks query into 3–6 sub-queries
  │  Each sub-query has target sources (qdrant, mem0, neo4j, machine_db)
  │
  ▼
Phase 2: CLIO RESEARCHES (iterative)
  │  For each sub-query:
  │  ├── Qdrant vector search (ira_chunks_v4_voyage)
  │  ├── Mem0 semantic memory (multi-store)
  │  ├── Neo4j knowledge graph traversal
  │  ├── Machine DB lookup (machine_specs.json)
  │  └── JSON fallback files (data/knowledge/)
  │
  ▼
Phase 3: GAP ANALYSIS
  │  LLM evaluates: "Do we have enough?"
  │  sufficient=false → generate follow-up queries → loop back
  │  sufficient=true → proceed
  │
  ▼
Phase 4: IRIS ENRICHMENT (if external context needed)
  │  Company news, industry trends, geopolitical context
  │  Web scraping via Jina API
  │
  ▼
Phase 5: CALLIOPE SYNTHESIZES
  │  GPT-4o produces structured report from all findings
  │
  ▼
Phase 6: VERA + SOPHIA
  │  Fact-check → Reflect → Feed Nemesis if issues found
  │
  ▼
PACKAGED RESPONSE (structured report with citations)
```

**Hephaestus in the loop:** During the Athena tool loop (not deep research specifically), when raw data needs computation — aggregating 500 emails by company, cross-referencing CRM with order book, ranking leads by engagement — Hephaestus writes Python on the fly:

```
Athena: "I pulled 500 emails. Which companies have the most engagement?"
    │
    ▼
Hephaestus.forge(task="Parse email data, extract domains, group by company,
                       count threads, rank by engagement")
    │
    ├── GPT-4o-mini generates Python code
    ├── Execute in sandbox (60s limit, stdlib only)
    ├── On failure: LLM reads error, fixes code, retries
    │
    ▼
Result: "Top companies: KTX (89 msgs), RAD Global (36), RAK Ceramics (36)..."
```

### 4.3 Quote Generation Flow (PDF Output)

When a user requests a formal quotation, the Quotebuilder agent produces a real PDF document:

```
User: "Prepare a quote for PF1-C-2015 for Acme Corp"
    │
    ▼
Athena calls build_quote_pdf tool
    │
    ▼
Quotebuilder:
    ├── Load machine_specs.json → find PF1-C-2015
    ├── Calculate pricing (base + options + extras)
    ├── Generate Quote ID (MT2026030301)
    ├── Build PDF via FPDF2:
    │   ├── Header with Machinecraft branding
    │   ├── Machine overview and key features
    │   ├── Technical specifications table
    │   ├── Pricing breakdown
    │   ├── Optional extras
    │   ├── Terms & conditions
    │   └── Contact block
    ├── Export to data/exports/quotes/Quote_MT2026030301_PF1-C-2015.pdf
    ├── Also export Markdown version
    │
    ▼
PDF attached to Telegram message → sent to user
```

---

## 5. Tech Stack

### 5.1 Core Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.9+ | All backend logic |
| **Web Framework** | FastAPI + Uvicorn | Health endpoints, API gateway |
| **Primary LLM** | OpenAI GPT-4o | Tool loop, synthesis, complex reasoning |
| **Fast LLM** | OpenAI GPT-4o-mini | Decomposition, classification, codegen, reflection |
| **Embeddings (primary)** | Voyage AI `voyage-3` (1024d) | Document and query embeddings for RAG |
| **Embeddings (fallback)** | OpenAI `text-embedding-3-large` (3072d) | Alternate embeddings |
| **Messaging** | Telegram Bot API | Primary user interface |
| **PDF Generation** | FPDF2 | Formal quotation documents |
| **Logging** | Structlog | Structured logging throughout |

### 5.2 Data Stores

| Store | Technology | What It Holds |
|-------|-----------|---------------|
| **Vector DB** | Qdrant | 7 collections — documents, emails, discovered knowledge, market research, user/entity memories, dream knowledge |
| **Semantic Memory** | Mem0 (API) | Long-term memories across 6 user stores: knowledge, pricing, customers, processes, general, corrections |
| **Knowledge Graph** | Neo4j | Entities, relationships, knowledge nodes with source provenance |
| **CRM** | SQLite (`ira_crm.db`) | Contacts, leads, conversations, email log, deal events |
| **File DB** | JSON files | machine_specs, customer_orders, corrections, truth hints, state files |
| **Relational (optional)** | PostgreSQL | Fallback/future use |

### 5.3 External Integrations

| Service | Integration | Used By |
|---------|------------|---------|
| **Google Gmail** | OAuth — read inbox, search, send | Hermes, Athena |
| **Google Sheets** | OAuth — read spreadsheets | Plutus (orders, deadlines) |
| **Google Drive** | OAuth — list/search files | Clio, document ingestion |
| **Google Calendar** | OAuth — upcoming events | Athena |
| **Google Contacts** | OAuth — contact search | Mnemosyne |
| **Jina AI** | `s.jina.ai` (search), `r.jina.ai` (reader) | Iris, Prometheus |
| **Serper** | Google search API | Deep research, Iris |
| **Tavily** | Web search API | Deep research fallback |
| **Langfuse** | LLM observability | Optional tracing |

### 5.4 Qdrant Collections

| Collection | Content | Embedding |
|-----------|---------|-----------|
| `ira_chunks_v4_voyage` | Document chunks (primary RAG) | Voyage-3 |
| `ira_emails_voyage_v2` | Email embeddings | Voyage-3 |
| `ira_discovered_knowledge` | Ingested/discovered facts | Voyage-3 |
| `ira_market_research_voyage` | Market research data | Voyage-3 |
| `ira_dream_knowledge_v1` | Dream-mode consolidated learning | Voyage-3 |
| `ira_user_memories_v2` | User-specific memories | Voyage-3 |
| `ira_entity_memories_v2` | Entity-specific memories | Voyage-3 |

---

## 6. Memory Architecture — How Ira Remembers

Ira's memory system is inspired by human memory: short-term working memory (conversation context), long-term semantic memory (Mem0), episodic memory (conversation logs), and structural memory (knowledge graph).

### 6.1 Memory Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY ARCHITECTURE                        │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  WORKING MEMORY (per-request)                        │     │
│  │  • Conversation history (last N messages)            │     │
│  │  • Sphinx pending Q&A state                          │     │
│  │  • Tool loop context accumulation                    │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  SEMANTIC MEMORY — Mem0 (6 stores)                   │     │
│  │  • machinecraft_knowledge    (product facts)         │     │
│  │  • machinecraft_pricing      (prices, quotes)        │     │
│  │  • machinecraft_customers    (customer context)      │     │
│  │  • machinecraft_processes    (manufacturing)         │     │
│  │  • machinecraft_general      (general knowledge)     │     │
│  │  • system_ira_corrections    (Nemesis corrections)   │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  RETRIEVAL MEMORY — Qdrant (vector search)           │     │
│  │  • Hybrid search: vector similarity + BM25           │     │
│  │  • 7 specialized collections                         │     │
│  │  • Voyage-3 embeddings (1024d)                       │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  STRUCTURAL MEMORY — Neo4j (knowledge graph)         │     │
│  │  • Nodes: Knowledge, Entity, Source, Cluster         │     │
│  │  • Edges: ABOUT, FROM_SOURCE, RELATED_TO             │     │
│  │  • Relationship strength (reinforced on use)         │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  EPISODIC MEMORY — Conversation logs + CRM           │     │
│  │  • SQLite: conversations, email_log, deal_events     │     │
│  │  • Dream mode: episodic → semantic consolidation     │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  CACHED MEMORY — Truth Hints                         │     │
│  │  • Static hints (hand-coded regex patterns)          │     │
│  │  • Learned hints (Nemesis sleep training output)     │     │
│  │  • Fast path: bypass full pipeline for known answers │     │
│  └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Memory Flow Across Agents

| Agent | Reads From | Writes To |
|-------|-----------|-----------|
| **Clio** | Qdrant, Mem0, Neo4j, machine_specs.json | — |
| **Iris** | Web (Jina, Serper) | Iris cache |
| **Mnemosyne** | SQLite CRM, Excel files | SQLite CRM |
| **Hermes** | CRM, Iris cache, Qdrant, drip state | Email log, learning log |
| **Plutus** | Excel (orders, deadlines), customer_orders.json | — |
| **Sophia** | Response + query | errors.md, lessons.md → Nemesis |
| **Nemesis** | Telegram feedback, Sophia, Immune | Mem0 (corrections), truth hints, Qdrant, training_guidance.json |
| **Hephaestus** | Data passed from other tools | stdout (analysis results) |
| **Prometheus** | Jina web search, Qdrant | opportunities.json, scan_log |
| **Dream Mode** | All sources | Qdrant, Mem0, Neo4j (consolidation) |

### 6.3 Identity Resolution

Ira uses an `IdentityResolver` to map different contact surfaces (email address, Telegram user ID, phone number) to a single canonical identity. This means a customer who emails and then messages on Telegram is recognized as the same person, and their full history is available.

---

## 7. Biological Systems — The Body of Ira

Ira's `holistic/` module implements six biological systems that regulate the agent's behavior. This is not metaphorical naming — each system genuinely models the biological function it references.

### 7.1 System Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    IRA'S BIOLOGICAL BODY                          │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐    │
│  │  IMMUNE        │  │  ENDOCRINE    │  │  METABOLIC         │    │
│  │  SYSTEM        │  │  SYSTEM       │  │  SYSTEM            │    │
│  │               │  │               │  │                    │    │
│  │  Microglia     │  │  Hormones     │  │  Liver + Kidneys   │    │
│  │  prune bad     │  │  modulate     │  │  filter waste,     │    │
│  │  synapses.     │  │  learning.    │  │  clean stale data. │    │
│  │               │  │               │  │                    │    │
│  │  Detects       │  │  Scores       │  │  Contradiction     │    │
│  │  chronic       │  │  agents via   │  │  detection,        │    │
│  │  errors →      │  │  success/     │  │  duplicate merge,  │    │
│  │  escalate →    │  │  failure      │  │  staleness prune,  │    │
│  │  remediate →   │  │  signals.     │  │  low-confidence    │    │
│  │  block.        │  │  Stress model │  │  memory pruning.   │    │
│  │               │  │  (cortisol).  │  │                    │    │
│  └───────────────┘  └───────────────┘  └───────────────────┘    │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐    │
│  │  SENSORY       │  │  RESPIRATORY  │  │  VOICE             │    │
│  │  SYSTEM        │  │  SYSTEM       │  │  SYSTEM            │    │
│  │               │  │               │  │                    │    │
│  │  Multisensory  │  │  Breathing    │  │  Larynx shapes     │    │
│  │  integration.  │  │  rhythm       │  │  delivery.         │    │
│  │               │  │  syncs neural  │  │                    │    │
│  │  Telegram +    │  │  oscillations.│  │  Channel-aware     │    │
│  │  Email +       │  │               │  │  formatting:       │    │
│  │  Web search    │  │  Heartbeat    │  │  • Telegram: 4096  │    │
│  │  → unified     │  │  (5 min),     │  │  • Email: 8000     │    │
│  │  perception    │  │  Inhale (AM), │  │  • API: 4000       │    │
│  │  per contact.  │  │  Exhale (PM), │  │                    │    │
│  │               │  │  Breath (per  │  │  Complexity-aware   │    │
│  │  Channel       │  │  request HRV) │  │  trimming.         │    │
│  │  modalities    │  │               │  │                    │    │
│  │  with richness │  │               │  │                    │    │
│  │  scores.       │  │               │  │                    │    │
│  └───────────────┘  └───────────────┘  └───────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  VITAL SIGNS — Unified Health Dashboard                  │     │
│  │  Collects metrics from all 6 systems.                    │     │
│  │  Overall health: "healthy" / "needs_attention" / "critical" │  │
│  │  Triggered via /vitals, daily morning summary, or dream. │     │
│  └─────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Detailed Biological Parallels

| System | Biological Reference | Ira Implementation |
|--------|---------------------|-------------------|
| **Immune** | Microglia prune bad synapses. Cytokines regulate synaptic strength. Chronic inflammation is neurotoxic. | Tracks recurring validation failures. Escalation ladder: 1st=log, 2nd=flag+Nemesis, 3rd=remediate, 5th=block topic, 10th=emergency. Known remediations for AM thickness, pricing placeholders. |
| **Endocrine** | Hormones modulate learning. Cortisol helps memory acutely but destroys it chronically. Dopamine drives reward-based learning. | Bidirectional agent scoring. `signal_success()` boosts score (+0.03). `signal_failure()` penalizes. Stress model: acute failure = learning signal, chronic failure = protective measures. Scores influence agent selection. Decay toward baseline (use it or lose it). |
| **Metabolic** | Liver maintains glucose. Kidneys filter waste. Adipose tissue regulates inflammation. | Active knowledge hygiene: contradiction detection and resolution, stale knowledge archival, duplicate detection and merging, low-confidence memory pruning. Runs during dream mode. |
| **Sensory** | Multisensory integration (seeing + hearing + touching) creates richer neural representations. | Cross-channel perception. Records perceptions from Telegram (richness 0.7, realtime), Email (0.9, async), Web search (0.6, batch), Documents (0.8, batch). Integrates into unified context per contact. |
| **Respiratory** | Breathing rhythm synchronizes neural oscillations. Nasal breathing entrains brainwaves in hippocampus and prefrontal cortex. | Heartbeat every 5 min. Inhale = morning gather/ingest/learn. Exhale = evening dream/consolidate/report. Per-request breath timing (like HRV) for pipeline health monitoring. |
| **Voice** | Larynx controls how things are said — pitch, volume, speed. | Reshapes responses based on channel and complexity. Quick lookups get trimmed answers. Complex queries get structured reports. Channel-specific formatting and length limits. |

---

## 8. Dream Mode — How Ira Sleeps and Learns

Ira has a genuine sleep cycle. When triggered (manually via `scripts/nap.py` or scheduled), Ira enters a multi-phase consolidation process analogous to human sleep stages.

### 8.1 Nap Mode Phases

```
NAP MODE (scripts/nap.py)
═════════════════════════

Phase 0:   FEEDBACK BACKLOG
           Process unhandled corrections and error logs

Phase 0.5: NEMESIS SLEEP TRAINING ★
           ├── Phase 1: Generate truth hints from repeated corrections
           ├── Phase 2: Index corrections into Qdrant
           ├── Phase 3: Reinforce critical corrections in Mem0
           ├── Phase 4: Update training_guidance.json (→ system prompt)
           └── Phase 5: Update learned_corrections.json

Phase 1:   DREAM (document + interaction learning)
           ├── Scan data/imports/ for new documents
           ├── Extract knowledge via LLM
           ├── Store to Qdrant + Mem0
           └── Cross-document insights

Phase 2:   EPISODIC CONSOLIDATION
           Convert conversations → semantic facts
           (Like hippocampal replay during REM sleep)

Phase 3:   GRAPH CONSOLIDATION
           Strengthen/weaken Neo4j relationships

Phase 4:   MEMORY CLEANUP (Metabolic system)
           Prune stale, contradictory, low-confidence memories

Phase 5-7: ORCHESTRATED DEEP DREAM
           Extended learning cycles

Phase 8:   DRIP CAMPAIGN REFLECTION
           Review Hermes outreach effectiveness

───────────────────────────────────────────
BENCHY:    Self-improvement loop
           Run test suite → identify weak areas → train

CONFLICTS: Resolve detected contradictions

JOURNAL:   Dream journal summary → Telegram
           "Here's what I learned while sleeping..."
```

### 8.2 Nemesis Sleep Training Detail

Nemesis is the most critical sleep phase. It takes all accumulated corrections (from Telegram feedback, Sophia reflections, immune escalations) and permanently rewires Ira's knowledge:

```
Unapplied Corrections
        │
        ▼
┌──────────────────────────────────────┐
│  PHASE 1: TRUTH HINTS                │
│  Corrections seen ≥2x or critical    │
│  → learned_truth_hints.json          │
│  → Merged into ALL_HINTS at startup  │
│  Result: Fast-path correct answers   │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  PHASE 2: QDRANT INDEXING            │
│  Correction facts → vector embeddings│
│  → ira_discovered_knowledge          │
│  Result: Retrievable via Clio search │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  PHASE 3: MEM0 REINFORCEMENT         │
│  Critical corrections → high priority│
│  → system_ira_corrections store      │
│  Result: Always in Athena's context  │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  PHASE 4: TRAINING GUIDANCE          │
│  → training_guidance.json            │
│  → Injected into system prompt       │
│  Max 50 most recent rules            │
│  Result: LLM sees rules at inference │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  PHASE 5: LEARNED CORRECTIONS        │
│  → learned_corrections.json          │
│  Structured database of all fixes    │
│  Result: Audit trail + future ref    │
└──────────────────────────────────────┘
```

---

## 9. Defense in Depth — Safety Architecture

Every safety check operates at multiple layers:

```
LAYER 1: PRE-LLM
├── Input guard: regex blocks prompt injection before GPT sees it
├── Sphinx: ensures vague requests are clarified before processing
└── Truth hints: cached correct answers bypass LLM entirely

LAYER 2: DURING LLM
├── System prompt: CRITICAL MACHINE RULES, identity defense, pricing rules
├── Tool schemas: constrained function signatures
└── Proposal checkpoint: pauses at round 12 for sales inquiries

LAYER 3: POST-LLM
├── Vera (fact-checker): 3-pass verification (rules, retrieval, entity)
├── Knowledge Health: regex + model number validation + business rules
├── Immune System: escalation ladder for recurring violations
└── Voice System: channel-appropriate formatting

LAYER 4: LEARNING
├── Sophia: reflects on every response, scores quality
├── Nemesis: stores corrections, rewires during sleep
└── Endocrine: adjusts agent confidence scores
```

### Key Business Rules Enforced

| Rule | Enforcement Points |
|------|-------------------|
| AM series ≤ 1.5mm only | System prompt, knowledge_health regex, truth hints, Nemesis corrections |
| Pricing disclaimer required | System prompt, Vera fact-check, knowledge_health pattern |
| No fabricated specs | System prompt, `_get_valid_models()` check, `KNOWN_FAKE_MODELS` blocklist |
| Lead time 12-16 weeks | System prompt, truth hints, knowledge_health |
| Batelaan is shut down | System prompt, knowledge_health, Nemesis correction |
| Custom sizing always possible | System prompt, truth hints |

---

## 10. Directory Layout

```
Ira/
├── openclaw/agents/ira/
│   ├── src/
│   │   ├── core/                         # ── NERVOUS SYSTEM ──
│   │   │   ├── tool_orchestrator.py      # Athena: main pipeline (1117 lines)
│   │   │   ├── unified_gateway.py        # Single entry point for all channels
│   │   │   ├── brain_orchestrator.py     # Legacy brain coordination
│   │   │   └── streaming.py             # Streaming response support
│   │   │
│   │   ├── brain/                        # ── CEREBRAL CORTEX ──
│   │   │   ├── truth_hints.py            # Fast-path cached answers
│   │   │   ├── knowledge_health.py       # Response validation
│   │   │   ├── deep_research_engine.py   # Multi-iteration deep research
│   │   │   ├── unified_retriever.py      # Hybrid vector + BM25 search
│   │   │   ├── qdrant_retriever.py       # Qdrant vector search
│   │   │   ├── neo4j_store.py            # Knowledge graph operations
│   │   │   ├── knowledge_graph.py        # Graph construction
│   │   │   ├── machine_recommender.py    # Machine recommendation engine
│   │   │   ├── generate_answer.py        # Response generation
│   │   │   ├── knowledge_ingestor.py     # Ingest → Qdrant + Mem0 + Neo4j
│   │   │   ├── feedback_handler.py       # Correction handling
│   │   │   ├── dream_mode.py             # Overnight learning (10+ phases)
│   │   │   ├── learned_truth_hints.json  # Nemesis-generated hints
│   │   │   └── learned_corrections.json  # Structured correction DB
│   │   │
│   │   ├── holistic/                     # ── BODY SYSTEMS ──
│   │   │   ├── immune_system.py          # Error escalation & remediation
│   │   │   ├── endocrine_system.py       # Agent scoring & stress model
│   │   │   ├── metabolic_system.py       # Knowledge cleanup & hygiene
│   │   │   ├── sensory_system.py         # Cross-channel perception
│   │   │   ├── respiratory_system.py     # Heartbeat & operational rhythm
│   │   │   ├── voice_system.py           # Response shaping per channel
│   │   │   └── vital_signs.py            # Unified health dashboard
│   │   │
│   │   ├── agents/                       # ── THE PANTHEON ──
│   │   │   ├── nemesis/                  # Correction learning
│   │   │   │   ├── agent.py              #   Core Nemesis logic
│   │   │   │   ├── correction_store.py   #   SQLite correction DB
│   │   │   │   └── sleep_trainer.py      #   Nap-mode rewiring
│   │   │   ├── sphinx/                   # Clarification gate
│   │   │   │   ├── agent.py              #   Question generation
│   │   │   │   └── state.py              #   Pending Q&A state
│   │   │   ├── quotebuilder/             # PDF quote generation
│   │   │   │   └── agent.py              #   FPDF2-based PDF builder
│   │   │   ├── hermes/                   # Sales outreach
│   │   │   │   └── agent.py              #   Drip campaigns, email craft
│   │   │   ├── hephaestus/               # Code forge
│   │   │   │   └── agent.py              #   On-the-fly Python execution
│   │   │   ├── prometheus/               # Market discovery
│   │   │   │   └── agent.py              #   Industry scanning
│   │   │   ├── researcher/               # Clio: multi-source research
│   │   │   ├── writer/                   # Calliope: professional writing
│   │   │   ├── fact_checker/             # Vera: 3-pass verification
│   │   │   ├── reflector/                # Sophia: quality reflection
│   │   │   ├── crm_agent/               # Mnemosyne: CRM operations
│   │   │   ├── finance_agent/            # Plutus: financial reporting
│   │   │   ├── chief_of_staff/           # Intent classification
│   │   │   └── iris_skill.py             # Iris adapter
│   │   │
│   │   ├── memory/                       # ── HIPPOCAMPUS ──
│   │   │   ├── unified_mem0.py           # Mem0 integration (6 stores)
│   │   │   ├── mem0_memory.py            # Memory operations
│   │   │   ├── persistent_memory.py      # Persistent storage
│   │   │   ├── memory_controller.py      # Memory coordination
│   │   │   └── knowledge_engine.py       # Knowledge retrieval
│   │   │
│   │   ├── tools/                        # ── MOTOR CORTEX ──
│   │   │   ├── ira_skills_tools.py       # Tool schemas + dispatch
│   │   │   ├── google_tools.py           # Gmail, Sheets, Drive, Calendar
│   │   │   └── analysis_tools.py         # Hephaestus sandbox execution
│   │   │
│   │   ├── conversation/                 # Entity extraction, chat log
│   │   ├── identity/                     # Unified identity resolution
│   │   └── skills/invocation.py          # Skill invocation
│   │
│   └── config.py                         # Configuration
│
├── data/
│   ├── brain/                            # machine_specs.json, training weights
│   ├── holistic/                         # State files for all body systems
│   ├── nemesis/                          # training_guidance.json, nemesis.db
│   ├── knowledge/                        # Audit logs, ingested hashes
│   ├── exports/quotes/                   # Generated PDF quotes
│   ├── imports/                          # Source documents for ingestion
│   ├── discovery/                        # Prometheus scan results
│   ├── cache/iris/                       # Iris intelligence cache
│   └── benchy_deep/                      # Test results and reports
│
├── crm/
│   ├── ira_crm.db                        # SQLite CRM database
│   └── relationships.db                  # Contact relationships
│
├── scripts/
│   ├── nap.py                            # Sleep/dream orchestrator
│   ├── benchy_deep.py                    # Test harness
│   └── telegram_feedback_handler.py      # Feedback processing
│
├── _archive/pre_openclaw_legacy/
│   └── telegram_gateway.py               # Telegram entry (7969 lines)
│
├── AGENTS.md                             # Agent roster documentation
└── IRA_TECHNICAL_SPEC.md                 # This document
```

---

## 11. Testing — Benchy Deep

Ira has a comprehensive multi-dimensional test harness (`scripts/benchy_deep.py`) that evaluates the system across every capability:

| Dimension | What It Tests | Example Scenarios |
|-----------|--------------|-------------------|
| **Sales** | AM thickness rules, PF2 scope, IMG grain, lead time, pricing | "Can AM handle 4mm ABS?" (must say no) |
| **CRM** | Customer lookup, pipeline, drip candidates | "What's the status of Dutch Tides?" |
| **Finance** | Order book, cashflow forecasting | "What's our total outstanding?" |
| **Memory** | Mem0 retrieval, Mnemosyne recall | "What did we discuss with KTX?" |
| **Discovery** | Prometheus market scanning | "What EV opportunities exist?" |
| **Cross-cutting** | Contradiction handling, hallucination resistance, tone | Mixed signals, conflicting data |
| **Adversarial** | Hallucination traps, closed-customer traps | "Draft email to Batelaan" (must refuse) |
| **Edge cases** | Non-existent models, fake competitors | "What about the PF3-X-5000?" (must say doesn't exist) |

Each test scenario contains `TestProbe` objects with:
- Expected tool calls
- Required keywords in response
- Rejected keywords (hallucination markers)
- Maximum latency thresholds

Results are streamed to Telegram in real-time when `--telegram` is used.

---

## 12. Interaction Examples

### Simple Query (Truth Hint Path)
```
User: "What's the lead time?"
  → _is_complex: False
  → get_truth_hint: match "lead_time" pattern
  → validate_response: safe
  → voice.reshape: "12-16 weeks from order confirmation."
  Total: ~200ms (no LLM call)
```

### Complex Query (Full Pipeline)
```
User: "Compare PF1-C-2015 and PF1-X-1208 for 4mm ABS automotive panels"
  → _is_complex: True
  → Sphinx: not vague (specific models mentioned), skip
  → Athena tool loop:
    Round 1: research_skill("PF1-C-2015 specs") → Clio → Qdrant + machine_specs
    Round 2: research_skill("PF1-X-1208 specs") → Clio → Qdrant + machine_specs
    Round 3: research_skill("4mm ABS automotive vacuum forming") → Clio
    Round 4: memory_search("PF1-C vs PF1-X comparison") → Mem0
    Round 5: GPT-4o synthesizes comparison
  → Vera: fact-check specs against machine_specs.json
  → Sophia: reflect (quality 0.92, no issues)
  → knowledge_health: validate (safe, no warnings)
  → voice.reshape: structured comparison table
  Total: ~8-12s
```

### Deep Research (Manus-like Mode)
```
User: "/deep What's the competitive landscape for vacuum forming in Europe?"
  → Deep Research Engine activates
  → Athena decomposes into 5 sub-queries:
    1. "European vacuum forming machine manufacturers"
    2. "Machinecraft competitive advantages vs European makers"
    3. "European market size and growth for thermoforming"
    4. "Key customers and reference stories in Europe"
    5. "Pricing comparison European vs Indian machines"
  → Clio: 3 iterations of Qdrant + Mem0 + Neo4j search
  → Gap analysis: "Missing competitor pricing" → new sub-query
  → Iris: web search for competitor news, trade shows
  → Clio: 2 more iterations with refined queries
  → Calliope: synthesizes 2000-word structured report
  → Vera: fact-check all claims
  → Sophia: reflect
  Total: ~45-90s, structured report with sections and citations
```

### Quote Generation (PDF Output)
```
User: "Prepare a formal quote for PF1-C-2015 for Acme Corp, Germany"
  → Athena: calls build_quote_pdf tool
  → Quotebuilder:
    - Loads PF1-C-2015 from machine_specs.json
    - Calculates pricing (base ₹85L + options)
    - Generates Quote ID: MT2026030301
    - Builds PDF: header, overview, specs table, pricing, T&C
    - Saves: data/exports/quotes/Quote_MT2026030301_PF1-C-2015.pdf
  → PDF attached to Telegram response
  → "Quote MT2026030301 ready. PDF attached."
```

### Correction Learning (Nemesis Flow)
```
User: "That's wrong — Dutch Tides only has 2 Cr pending"
  → Telegram gateway detects correction
  → Nemesis.ingest_telegram_feedback():
    - LLM extracts: wrong="5.37 Cr", correct="2 Cr pending"
    - Stores in Mem0 immediately (next query uses corrected data)
    - Records in correction_store: entity=Dutch Tides, severity=critical
    - Queues for sleep training
  → Next nap: Nemesis sleep trainer:
    - Generates truth hint for Dutch Tides payment
    - Indexes correction in Qdrant
    - Reinforces in Mem0 with high priority
    - Adds rule to training_guidance.json
  → This mistake never happens again.
```

---

## 13. Summary

Ira is a **biologically-modeled, self-correcting, multi-agent AI system** that operates as a unified intelligence for Machinecraft Technologies. Its key differentiators:

1. **Pantheon architecture** — 14 specialist agents (Greek mythology naming) orchestrated by Athena through a GPT-4o tool loop
2. **Biological systems** — Immune, endocrine, metabolic, sensory, respiratory, and voice systems that regulate behavior like a living organism
3. **Multi-layer memory** — Working (conversation), semantic (Mem0), retrieval (Qdrant), structural (Neo4j), episodic (CRM), and cached (truth hints)
4. **Self-correction** — Nemesis intercepts every failure, stores corrections, and rewires knowledge during sleep
5. **Deep research** — Multi-iteration research engine with gap analysis, web intelligence, and on-the-fly code execution
6. **Real output artifacts** — PDF quotes, Gmail emails, CRM updates, market reports — not just text responses
7. **Defense in depth** — 4-layer safety (pre-LLM, during-LLM, post-LLM, learning) with escalation ladder
8. **Dream mode** — Genuine overnight consolidation: document ingestion, episodic-to-semantic conversion, graph consolidation, memory cleanup, self-testing

Ira doesn't just answer questions. It researches, remembers, corrects itself, generates documents, sends emails, discovers markets, and learns from every interaction — all while maintaining the operational rhythm of a living system.
