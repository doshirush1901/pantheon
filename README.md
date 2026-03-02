<p align="center">
  <img src="docs/assets/ira-logo.png" alt="Ira" width="180" />
</p>

<h1 align="center">Ira — Intelligent Revenue Assistant</h1>

<p align="center">
  AI sales intelligence for industrial manufacturing. Built for <a href="https://machinecraft.in">Machinecraft Technologies</a>.
</p>

<p align="center">
  <a href="#about">About</a> · <a href="#how-it-works">How It Works</a> · <a href="#quick-start">Quick Start</a> · <a href="#usage">Usage</a> · <a href="#architecture">Architecture</a> · <a href="#the-pantheon">Pantheon</a> · <a href="#everything-we-built">Everything We Built</a>
</p>

---

## About

Ira is a purpose-built AI sales assistant that runs on your own infrastructure. She answers on Telegram, Email, and API — and she remembers everything.

Unlike generic chatbots, Ira has deep domain expertise in thermoforming machinery, persistent cross-channel memory, built-in hallucination guards, and a nightly "dream cycle" that consolidates knowledge while you sleep.

She's not a wrapper around an LLM. She's a full metabolic system: she eats documents, digests them into structured knowledge, filters out waste, absorbs nutrients into a vector database, and forgets what's no longer relevant.

If you want a sales assistant that actually knows your products, your customers, and your pricing — and gets smarter every day — this is it.

## How it works (short)

```
Telegram / Email / API / CLI
│
▼
┌──────────────────────────────────┐
│        Unified Agent (Athena)    │
│    orchestrates the Pantheon     │
└───────────────┬──────────────────┘
                │
  ┌─────────────┼─────────────┐
  │             │             │
  ▼             ▼             ▼
┌──────┐  ┌──────────┐  ┌──────┐
│ Clio │  │ Calliope │  │ Vera │
│search│  │  write   │  │verify│
└──┬───┘  └────┬─────┘  └──┬───┘
   │           │            │
   └───────────┴────────────┘
                │
                ▼
┌──────────────────────────────────┐
│          Core Systems            │
│  Qdrant · Mem0 · Neo4j · JSON   │
└──────────────────────────────────┘
```

## The Pantheon

Ira operates as a coordinated team of specialist agents, not a single monolith.

| Agent | Codename | What they do |
|-------|----------|--------------|
| **Athena** | Strategist | Analyzes requests, plans execution, delegates to specialists |
| **Clio** | Researcher | Retrieves knowledge from documents, emails, memory, and the knowledge graph |
| **Iris** | Intelligence | Gathers real-time external data — company news, industry trends, geopolitics |
| **Calliope** | Writer | Crafts professional emails, quotes, and customer communications |
| **Vera** | Auditor | Verifies every fact, enforces business rules, catches hallucinations |
| **Sophia** | Mentor | Learns from interactions, improves responses over time |

```
User: "What machine for 4mm ABS?"

Athena → Clio (searches specs) → finds PF1-C-2015
       → Calliope (writes recommendation)
       → Vera (confirms: AM series ≤1.5mm, PF1 handles 4mm ✓)
       → Sophia (logs interaction for learning)
```

## Quick start

**Prerequisites:** Python 3.10+, Docker (for Qdrant), API keys (OpenAI, Voyage AI).

```bash
git clone https://github.com/machinecraft/ira.git
cd ira

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: add OPENAI_API_KEY, VOYAGE_API_KEY, TELEGRAM_BOT_TOKEN

docker-compose up -d   # starts Qdrant + PostgreSQL

./start_ira.sh         # starts all services
```

First run? Place documents in `data/imports/` and run:

```bash
python scripts/ingest_all_imports.py
```

Ira will eat, digest, filter, and absorb them automatically.

## Usage

### Telegram (primary interface)

Start the bot, then talk to Ira naturally. She handles:

- **Free text** — "What's the price for PF1-3020?" → researched answer with sources
- **Documents** — Upload PDF/Excel/Word → auto-ingested into knowledge base
- **URLs** — Send a link → web content fetched and ingested
- **Commands** — `/help`, `/status`, `/brief <topic>`, `/docs`, `/research <query>`

### Email

Ira monitors Gmail, drafts context-aware replies, and manages follow-up sequences.

```bash
./start_ira.sh email
```

### Python API

```python
from openclaw.agents.ira import get_agent

agent = get_agent()
response = agent.process(
    message="Recommend a machine for automotive interior parts, 3mm ABS",
    channel="api",
    user_id="customer@example.com"
)
```

### Direct retrieval

```python
from openclaw.agents.ira.src.brain.unified_retriever import UnifiedRetriever

retriever = UnifiedRetriever()
results = retriever.search("thermoforming machine specifications", top_k=5)
```

## Architecture

### The metabolic cycle

Ira's data pipeline follows a biological metaphor — a complete metabolic cycle from ingestion to forgetting.

| Stage | Analogy | What happens | Module |
|-------|---------|-------------|--------|
| **EAT** | Food enters body | New files detected in `data/imports/` | `heartbeat_ingest.py` |
| **TASTE** | Sniffing | First 2K chars → GPT-4o-mini generates metadata label | `imports_metadata_index.py` |
| **CHEW** | Mechanical digestion | PDF/Excel/Word/PPTX → plain text | `document_extractor.py` |
| **DIGEST** | Chemical digestion | NER + keyword extraction; LLM extracts structured knowledge | `stomach_enrichment.py` |
| **FILTER** | Excretion | Quality filter (min words, density, boilerplate, semantic dedup) | `quality_filter.py` |
| **ABSORB** | Bloodstream | Stored in Qdrant + Mem0 + Neo4j + JSON backup | `knowledge_ingestor.py` |
| **TEST** | Immune system | Health scoring, hallucination detection, spaced-repetition training | `brain_trainer.py` |
| **SLEEP** | Dream cycle | 10-phase nightly consolidation at 2 AM | `dream_mode.py` |
| **FORGET** | Memory decay | 30d decay → 90d archive → 180d prune; recall boosts importance | `persistent_memory.py` |
| **SPEAK** | Voice / larynx | Adaptive tone, length, format shaping per channel and complexity | `voice_system.py` |
| **GROW** | Growth hormone | Email-to-knowledge pipeline; one signal stimulates every body system | `growth_signal.py` |

### Technology stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | OpenAI GPT-4o | Response generation, knowledge extraction |
| Embeddings | Voyage AI (voyage-3, 1024d) | Semantic search vectors |
| Vector DB | Qdrant | Document and memory storage (2 collections) |
| Memory | Mem0 | Long-term semantic memory |
| Graph DB | Neo4j | Entity relationships and knowledge graph |
| Reranking | FlashRank | Result relevance optimization |
| Messaging | Telegram Bot API | Primary user interface |
| Email | Gmail API | Email processing and smart replies |
| Database | PostgreSQL | Relational data and identity |

### Memory system

| Type | What it stores | Where |
|------|---------------|-------|
| **Episodic** | Conversation history, interaction records | Mem0, JSON logs |
| **Semantic** | Facts, preferences, learned knowledge | Qdrant, Mem0 |
| **Procedural** | Learned workflows, response patterns | Mem0 |
| **Identity** | Cross-channel user recognition | PostgreSQL |

## Everything we built

### Core pipeline

- **Unified retriever** — hybrid vector (Voyage AI) + BM25 keyword search with FlashRank reranking.

- **Knowledge ingestor** — quad-destination storage (2× Qdrant, Mem0, JSON) with smart chunking (2K chars, 200 overlap), SHA-256 dedup, and semantic near-duplicate detection.

- **Quality filter** — pre-ingestion excretion system: min word count, information density, boilerplate detection, and periodic Qdrant waste disposal.

- **Stomach enrichment** — spaCy NER + YAKE keyword extraction injected into metadata before embedding.

- **URL fetcher** — Jina Reader → trafilatura → regex fallback, with centralized HTML cleaning.

- **Heartbeat ingest** — cron-ready file watcher for `data/imports/` with Telegram notifications.

### Brain & learning

- **Dream mode** — 10-phase nightly cycle: deep extraction, cross-document insights, synaptic pruning, price conflict checks, episodic-to-semantic consolidation, morning summary.

- **Brain trainer** — spaced-repetition quiz system targeting weak knowledge areas; writes reinforcement weights consumed by the answer generator.

- **Knowledge health monitor** — scores responses 0–100 based on document coverage, truth hints, and hallucination detection.

- **Correction learner** — detects when users correct Ira and stores corrections as high-priority memories.

- **Interaction learner** — mines conversation logs for recurring patterns and distills them into semantic knowledge.

### Channels & communication

- **Telegram gateway** — rich formatting, inline keyboards, document upload, URL ingestion, 50+ commands, live thinking indicators.

- **Email handler** — Gmail integration, smart drafting, lead qualification, drip campaigns, thread management.

- **API server** — RESTful interface for custom integrations.

### Sales intelligence

- **Iris (intelligence agent)** — real-time company research, industry trends, competitive intelligence, geopolitical context.

- **Quote generator** — PDF quote generation with machine database integration and CRM pipeline.

- **Lead qualification** — automatic scoring and prioritization of inbound inquiries.

- **Proactive outreach** — automated follow-up suggestions based on customer activity and pipeline state.

### Memory & identity

- **Persistent memory** — cross-channel memory with importance scoring, decay, and "use it or lose it" retrieval boosting.

- **Unified identity** — resolves users across Telegram, email, and API into a single identity.

- **Memory consolidation** — episodic memories distilled into durable semantic facts during the dream cycle.

### Holistic body systems

Ira has a complete set of biological body systems that maintain her health autonomously:

- **Immune system** — auto-remediation of chronic knowledge issues; escalation ladder from log to flag to remediate to block.

- **Respiratory system** — operational heartbeat, breath timing, HRV-like latency metrics, daily rhythm orchestration.

- **Endocrine system** — agent scoring with dopamine/cortisol signals; rewards successful agents, penalizes failures.

- **Musculoskeletal system** — action-to-learning feedback; every email sent, quote generated, or lead researched produces myokines that feed the dream cycle.

- **Sensory system** — cross-channel perception integration; recognizes the same customer across Telegram, email, and API.

- **Metabolic system** — active knowledge hygiene; periodic cleanup of contradictions, stale facts, and Qdrant waste.

- **Voice system** — adaptive response shaping; trims verbose answers for quick lookups, expands for complex asks, matches channel tone.

- **Growth signal** — the growth hormone; one call after each email digestion stimulates every body system simultaneously.

### Email growth hormone

- **Email nutrient extractor** — GPT-4o-mini structured extraction from emails: machines, prices, customers, objections, competitors, deal stage, communication style.

- **Mailbox ingestion** — contact-driven bulk backfill; reads 641 customer/lead emails from spreadsheets, queries Gmail for each, extracts and ingests into the full 5-backend pipeline (Qdrant x2, Mem0, Neo4j, JSON).

- **Real-time email digestion** — every email the bridge processes is automatically digested into permanent knowledge after reply.

## Project structure

```
ira/
├── openclaw/agents/ira/         # Main application
│   ├── agent.py                 # Unified agent coordinator
│   ├── config.py                # Centralized configuration
│   └── src/
│       ├── brain/               # RAG, retrieval, knowledge pipeline (40+ modules)
│       ├── holistic/            # Body systems: immune, respiratory, endocrine, voice, growth
│       ├── memory/              # Persistent memory system (20+ modules)
│       ├── conversation/        # Conversation intelligence
│       ├── identity/            # Cross-channel identity resolution
│       ├── crm/                 # CRM and lead management
│       ├── sales/               # Quote generation, outreach
│       └── market_research/     # Iris intelligence gathering
│
├── agents/                      # Specialist agents (Iris, Apollo, Athena, Nemesis)
├── skills/                      # OpenClaw skills (20+)
├── scripts/                     # Utility scripts (34 files)
├── data/                        # Documents, knowledge, memory backups
├── docs/                        # Documentation (20+ files)
└── tests/                       # Test suite (263+ tests)
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `VOYAGE_API_KEY` | Yes | Voyage AI embeddings |
| `QDRANT_URL` | Yes | Qdrant vector database URL |
| `TELEGRAM_BOT_TOKEN` | For Telegram | Telegram bot token |
| `EXPECTED_CHAT_ID` | For Telegram | Authorized chat ID |
| `MEM0_API_KEY` | Optional | Mem0 memory service |
| `DATABASE_URL` | Optional | PostgreSQL connection |

See [.env.example](.env.example) for the complete list.

## Development

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=openclaw --cov-report=html

# Lint
ruff check openclaw/ scripts/

# Format
black openclaw/ scripts/ tests/
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md) | System architecture |
| [Agent Architecture](docs/AGENT_ARCHITECTURE.md) | Multi-agent design |
| [Knowledge System](docs/KNOWLEDGE_DISCOVERY_ARCHITECTURE.md) | RAG and retrieval |
| [Knowledge Ingestion](docs/KNOWLEDGE_INGESTION.md) | Document pipeline |
| [Dream Mode](docs/DREAM_MODE_AUDIT.md) | Nightly consolidation |
| [Telegram Guide](docs/TELEGRAM_BEST_PRACTICES.md) | Bot setup and usage |
| [How We Built Ira](docs/about-ira/HOW_WE_BUILT_IRA.md) | Origin story |

## Roadmap

- [ ] Web dashboard for analytics
- [ ] WhatsApp channel integration
- [ ] Voice interface (Whisper)
- [ ] Multi-language support
- [ ] CRM integrations (Salesforce, HubSpot)

## License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built for <a href="https://machinecraft.in">Machinecraft Technologies</a></strong><br>
  <sub>Empowering industrial sales with AI intelligence</sub>
</p>
