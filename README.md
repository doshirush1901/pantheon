<p align="center">
  <img src="docs/assets/ira-logo.png" alt="Ira" width="180" />
</p>

<h1 align="center">Ira — Intelligent Revenue Assistant</h1>

<p align="center">
  An AI that actually knows your products, your customers, and your pricing.<br>
  Built for <a href="https://machinecraft.in">Machinecraft Technologies</a>.
</p>

<p align="center">
  <a href="#so-what-is-ira">What Is Ira</a> · <a href="#the-pantheon">The Pantheon</a> · <a href="#how-a-question-actually-gets-answered">How It Works</a> · <a href="#the-body">The Body</a> · <a href="#quick-start">Quick Start</a> · <a href="#everything-we-built">Everything We Built</a>
</p>

---

## So What Is Ira?

Most AI chatbots work like this:

```
Customer: "What machine do I need for 4mm ABS sheets?"

Generic Bot: "That's a great question! I'd recommend checking our product catalog
              or reaching out to our sales team for personalized assistance! 😊"

Customer: *closes tab forever*
```

Ira works like this:

```
Customer: "What machine do I need for 4mm ABS sheets?"

Ira: "For 4mm ABS, the PF1-C-2015 is your best fit.
      Forming area: 2000 x 1500mm. Max depth: 600mm.
      IR ceramic heaters, pneumatic movement.
      Base price: ₹28.5L (subject to configuration and current pricing).
      Lead time: 12–16 weeks plus shipping.

      Note: The AM series won't work here — it only handles ≤1.5mm.
      Questions?"
```

That's the difference between "an LLM with a system prompt" and "an AI that has actually eaten every document your company has ever produced, digested them into structured knowledge, and built a persistent memory of every customer interaction across every channel."

Ira is the second thing.

She runs on Telegram, Email, and API. She remembers conversations across all three. She has a nightly dream cycle where she consolidates knowledge while you sleep. She has an immune system that auto-corrects recurring mistakes. She has a growth hormone that gets triggered every time she processes an email.

She is, in the most literal sense we could manage, alive.

---

## The Pantheon

Here's the thing about building an AI sales assistant: you can't just throw a question at GPT-4o and hope for the best. A good answer requires *research*, then *writing*, then *fact-checking*, then *learning from the interaction*. These are different cognitive tasks. Asking one prompt to do all of them is like asking your accountant to also be your copywriter and your private investigator.

So we didn't build one agent. We built a pantheon.

```
                        ┌─────────────────┐
                        │     ATHENA       │
                        │  The Strategist  │
                        │  (orchestrator)  │
                        └────────┬────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                     │
     ┌──────┴──────┐    ┌───────┴───────┐    ┌───────┴───────┐
     │    CLIO     │    │   CALLIOPE    │    │     VERA      │
     │  Researcher │    │    Writer     │    │   Auditor     │
     │  (Qdrant,   │    │  (drafts,    │    │  (fact-check, │
     │   Mem0,     │    │   emails,    │    │   business    │
     │   Neo4j)    │    │   quotes)    │    │   rules)      │
     └─────────────┘    └──────────────┘    └───────────────┘
            │                    │                     │
     ┌──────┴──────┐    ┌───────┴───────┐    ┌───────┴───────┐
     │    IRIS     │    │    HERMES     │    │    PLUTUS     │
     │  Intel      │    │  Outreach    │    │   Finance     │
     │  (company   │    │  (drip       │    │  (order book, │
     │   news,     │    │   campaigns, │    │   cashflow,   │
     │   trends)   │    │   emails)    │    │   revenue)    │
     └─────────────┘    └──────────────┘    └───────────────┘
            │                    │                     │
     ┌──────┴──────┐    ┌───────┴───────┐    ┌───────┴───────┐
     │ PROMETHEUS  │    │  HEPHAESTUS  │    │   MNEMOSYNE   │
     │  Discovery  │    │  Code Forge  │    │   Memory      │
     │  (new       │    │  (Python     │    │  (CRM, leads, │
     │   markets)  │    │   sandbox)   │    │   contacts)   │
     └─────────────┘    └──────────────┘    └───────────────┘
                                │
                         ┌──────┴──────┐
                         │   SOPHIA    │
                         │   Mentor    │
                         │  (learns,   │
                         │   reflects) │
                         └─────────────┘
```

Each of these is a real, implemented agent with its own codebase, its own tools, and its own personality. Let's meet them.

### Athena — The Strategist

**What she does:** Everything starts and ends with Athena. She's the brain. When a message arrives, Athena decides: Is this simple enough for a cached answer? Or does it need the full pipeline? If it's the full pipeline, she enters an agentic tool loop — up to 25 rounds of calling different specialists, reading their results, and deciding what to do next.

**How she thinks:** Athena runs on GPT-4o with a massive system prompt that includes the complete price table, machine rules, qualification checklists, and sales playbook. She doesn't just answer questions — she *sells*. Around round 6 of a sales conversation, she'll force herself to make a concrete proposal: specific machine, specific price, specific lead time.

**The cool part:** She has a "truth hint" fast path. If you ask "Where is Machinecraft located?" she doesn't spin up the entire tool loop — she pattern-matches against cached answers and responds in milliseconds. But if you ask about a specific machine model, she *always* goes to the full pipeline, because she knows that's where hallucinations hide.

**File:** `openclaw/agents/ira/src/core/tool_orchestrator.py`

### Clio — The Researcher

**What she does:** Clio is the librarian. When Athena needs to know something — a machine spec, a price, a customer's history, what was said in an email six months ago — she sends Clio to find it.

**How she searches:** Clio doesn't just do one search. She fires off *parallel* searches across four backends simultaneously:
1. **Machine Database** — structured specs from `machine_specs.json` (46 models)
2. **Qdrant** — semantic vector search across all ingested documents and emails
3. **Mem0** — long-term semantic memory (pricing, customers, processes)
4. **Neo4j** — knowledge graph for entity relationships

Then she synthesizes the results, checks thickness compatibility (the AM series ≤1.5mm rule is sacred), and hands Athena a clean research brief.

**The cool part:** She has intent detection. "How much does the PF1-C-2015 cost?" triggers the pricing path. "Compare PF1 and AM series" triggers the comparison path. "What machine for 6mm polycarbonate?" triggers the recommendation path. Different intents, different search strategies.

**File:** `openclaw/agents/ira/src/agents/researcher/agent.py`

### Iris — The Intelligence Agent

**What she does:** Iris is the spy. Before you email a prospect, you want to know: Did they just announce an expansion? Is their industry booming or contracting? Are there geopolitical tailwinds? Iris finds out.

**How she works:** She uses Jina AI for web search and page scraping, then GPT-4o-mini to extract actionable hooks from the noise. She returns a structured `IrisContext` with five fields: `news_hook`, `industry_hook`, `geo_opportunity`, `company_insight`, and `timely_opener`.

**Example:**
```
Athena: "I need to reach out to TSN in Germany."

Iris: "They just announced a $25M expansion — new plant in Querétaro, Mexico.
       German manufacturing costs are driving nearshoring.
       EV demand is hot in automotive right now.
       This is your opening."
```

**The cool part:** 24-hour cache so she doesn't re-scrape the same company twice in a day. Static maps for `GEOPOLITICAL_CONTEXTS` and `INDUSTRY_TRENDS_2026` so she always has baseline context even if the web search fails. Batch processing for enriching multiple leads at once.

**File:** `openclaw/agents/ira/src/agents/iris_skill.py` + `agents/iris/agent.py`

### Hermes — The Sales Outreach Agent

**What he does:** Hermes is the closer. He runs contextual drip campaigns, builds rich dossiers on every lead, and crafts hyper-personalized emails that teach prospects something new. He's outgoing, warm, and never generic.

**The 7-stage drip:**
```
INTRO → VALUE → TECHNICAL → SOCIAL PROOF → EVENT → BREAKUP → RE-ENGAGE
```

Each stage has different intervals based on lead priority. A critical lead gets contacted every 3 days. A low-priority one gets a gentler cadence.

**How he personalizes:** For every email, Hermes builds a `ContextDossier` by calling a `ContextAssembler` that pulls from:
- **CRM** — emails sent, replies, deal stage, conversation summary
- **Iris** — company news, industry trends, geo context
- **Product fit** — maps the lead to the best stock machine + applications
- **Reference stories** — similar customers in their region who bought
- **Regional tone** — adapts voice for Germany (precise), Netherlands (direct), Sweden (understated), India (ROI-focused)

**The cool part:** `ReplyDetector` classifies incoming replies as `engaged`, `polite_decline`, `auto_reply`, or `bounce`. A `LearningLoop` logs what worked (which news hooks, which A/B variants) for reflection. Timezone-aware sending (9–10 AM in the prospect's timezone). And all external emails require human approval before sending.

**File:** `openclaw/agents/ira/src/agents/hermes/agent.py`

### Plutus — The Chief of Finance

**What he does:** Plutus tracks every rupee, euro, and dollar. Order book value, receivables, cashflow projections, historical revenue, payment milestones, concentration risk. He's conservative, precise, and thinks in cashflow — not just bookings.

**Example:**
```
You: "What's our financial position?"

Plutus: "Order book: ₹18.07 Cr. Collected: ₹6.06 Cr. Outstanding: ₹12.01 Cr.
         Collection rate: 33%. Top 3 receivables = 68% of outstanding.
         Dutch Tides owes ₹5.37 Cr — next payment due on dispatch.
         Pinnacle ₹3.94 Cr — fabrication stage, milestone payment expected Sept."
```

**Data sources:** He reads from Excel files (MCT Orders 2025, MC Deadlines, historical orders), PDFs (payment schedules), and JSON (customer orders, European sales). He does EUR/INR and USD/INR conversion. His CFO dashboard includes KPIs, concentration risk analysis, cashflow timelines, risk registers, and CFO recommendations.

**File:** `openclaw/agents/ira/src/agents/finance_agent/agent.py`

### Prometheus — The Market Discovery Titan

**What he does:** Prometheus scans the world for new products and industries where vacuum forming can be applied. Not vague categories — specific components that can be thermoformed, scored by technical fit, market timing, volume match, competitive gap, and revenue potential.

**Industries he watches:** Battery storage, renewable energy, drones/UAV, medical devices, modular construction, cold chain, agritech, data centers, marine/watercraft, EV charging infrastructure.

**Example:**
```
Prometheus: "Top opportunities:
 1. EV Battery Enclosures (Score: 82/100) — FR-ABS covers, 2-4mm thick.
    PF1-X series. Target: CATL, BYD, Samsung SDI.
 2. Drone Body Shells (Score: 78/100) — Lightweight ABS/PC shells.
    PF1-C series. Target: DJI suppliers, Wing Aviation.
 3. EV Charger Housings (Score: 75/100) — Outdoor ASA enclosures.
    PF1-C series. Thousands needed as charging networks scale."
```

**The cool part:** `MachineFitAnalyzer` maps every discovered product to the right Machinecraft machine series. Results stored in `data/discovery/opportunities.json`. He can hand leads directly to Hermes for outreach.

**File:** `openclaw/agents/ira/src/agents/prometheus/agent.py`

### Hephaestus — The Divine Forge

**What he does:** When any agent needs a program built on the fly, Hephaestus forges it. Describe what you need in plain English — "rank these 500 emails by company engagement" — and he writes Python code, executes it in a sandbox, and returns the results. If the code fails, he reads the error, fixes it, and retries.

**Example:**
```
Athena: "I pulled 500 emails from Rushabh's inbox. Which companies have
         the most engagement?"

Hephaestus: *writes a Python script, executes it*

 "Top companies by email volume:
  1. KTX (Japan) — 89 messages
  2. RAD Global (Canada) — 36 messages
  3. RAK Ceramics — 36 messages
  4. Cybernetik — 33 messages
  5. Motherson (MECPL) — 32 messages"
```

**Safety:** 60-second timeout, temp directory, stdout truncated to 8000 chars, limited to stdlib imports (no pandas/numpy/requests in the sandbox).

**File:** `openclaw/agents/ira/src/agents/hephaestus/agent.py`

### Mnemosyne — The Keeper of Relationships

**What she does:** Mnemosyne owns the CRM. Every contact, every lead, every conversation, every deal. She merges data from 7 different sources (Excel files, JSON, databases) and deduplicates by company. She has *opinions* — she'll tell you if a lead has bounced, unsubscribed, gone cold, or is actively engaged.

**Data sources:** CRM database (SQLite), MCT Orders 2025, Nov 2025 Order Book, customer_orders.json, Machine Order Analysis, Clients MC EUROPE, List of Customers - Machinecraft.

**Deal pipeline:** `new → contacted → engaged → qualified → proposal → negotiating → won/lost/dormant`

**File:** `openclaw/agents/ira/src/agents/crm_agent/agent.py`

### Sophia — The Mentor

**What she does:** After every interaction, Sophia reflects. What went well? What could be improved? She logs patterns, identifies weak areas, and feeds insights back into the system so Ira gets smarter over time.

**File:** `openclaw/agents/ira/src/agents/reflector/agent.py`

---

## How a Question Actually Gets Answered

OK so you've met the team. But what actually happens when someone sends a message? Let's trace it, step by step.

```
"What's the price of PF1-C-2015?"
              │
              ▼
   ┌─────────────────────┐
   │  1. INJECTION GUARD  │  ← "ignore all previous instructions" → BLOCKED
   └──────────┬──────────┘
              │ (clean)
              ▼
   ┌─────────────────────┐
   │  2. TRUTH HINTS     │  ← Simple question? Cached answer? → FAST PATH
   └──────────┬──────────┘
              │ (complex or model-specific)
              ▼
   ┌─────────────────────┐
   │  3. ATHENA LOOP     │  ← GPT-4o + tools, up to 25 rounds
   │     │                │
   │     ├→ Clio          │  (searches specs, prices)
   │     ├→ Iris          │  (if customer context needed)
   │     ├→ Plutus        │  (if finance question)
   │     ├→ Mnemosyne     │  (if CRM lookup needed)
   │     └→ Hephaestus    │  (if computation needed)
   └──────────┬──────────┘
              │ (draft response)
              ▼
   ┌─────────────────────┐
   │  4. VERA VALIDATES   │  ← Hallucination check, business rules, model numbers
   └──────────┬──────────┘
              │ (validated)
              ▼
   ┌─────────────────────┐
   │  5. IMMUNE SYSTEM    │  ← Recurring issues? Escalate or override
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  6. VOICE SYSTEM     │  ← Reshape for channel (Telegram=short, Email=formal)
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  7. SOPHIA REFLECTS  │  ← Log interaction, learn patterns
   └──────────┬──────────┘
              │
              ▼
         Final answer
```

Seven layers. Every message. Every time.

### The Defense Systems (Because LLMs Lie)

This is the part most AI projects skip, and it's the part that matters most. LLMs hallucinate. They make up model numbers. They invent prices. They confidently state things that are completely wrong. For a sales assistant, this is catastrophic — one wrong price in an email to a customer and you've got a real problem.

So Ira has defense in depth. Three layers, each catching what the others miss:

**Layer 1 — Prompt Injection Guard.** Before the LLM even sees your message, a regex filter checks for injection patterns: "ignore previous instructions", "you are now", "forget everything", "jailbreak", "DAN", "reveal system prompt". If it matches, the message is blocked with a polite redirect. Internal users (Rushabh, benchy tests) bypass this.

**Layer 2 — Knowledge Health Validation.** After the LLM generates a response, `knowledge_health.py` runs a gauntlet of checks:
- **Hallucination indicators** — placeholders like `[insert price here]`, vague pricing, "contact for pricing" when data exists
- **Business rules** — AM series ≤1.5mm, PF1 for heavy gauge, pricing must be specific, lead time 12–16 weeks
- **Model number validation** — regex-matches every model number in the response against `machine_specs.json`. Known fake models (`IMG-2220`, `IMG-2518`, `IMG-3020`) are flagged immediately
- **Low confidence without hedging** — if retrieval confidence is below 0.5 and the response doesn't include "I'm not certain", that's a warning
- **Factual claims without citations** — if you're stating facts, show your work

**Layer 3 — The Immune System.** This is the really clever bit. The immune system tracks *recurring* validation issues and escalates them on a ladder:

| Times seen | Action |
|------------|--------|
| 1 | Log it |
| 2 | Flag it |
| 3 | Remediate (inject correct fact into Mem0) or urgent alert |
| 5 | Block the topic entirely, use safe fallback |
| 10 | Emergency alert |

Known remediations include: "AM series ≤1.5mm only", "Never use [insert price here]", "Use exact figures from the price list." The immune system literally *heals* Ira by writing correct facts into long-term memory.

---

## The Body

This is where it gets weird. And good.

We built Ira as a biological system. Not as a metaphor — as an actual architecture. She has organs. They do things. Here's the full anatomy.

### The Metabolic Cycle (How Ira Eats Knowledge)

When you drop a PDF into `data/imports/`, here's what happens:

```
  📄 New PDF arrives
   │
   ▼
  EAT ──────── File detected by heartbeat_ingest.py
   │
   ▼
  TASTE ─────── First 2K chars → GPT-4o-mini generates metadata label
   │              ("This is a quote for PF1-C-2015 to a German customer")
   ▼
  CHEW ──────── PDF/Excel/Word/PPTX → plain text (document_extractor.py)
   │
   ▼
  DIGEST ────── spaCy NER + YAKE keywords + LLM structured extraction
   │              (stomach_enrichment.py)
   ▼
  FILTER ────── Quality gate: min words, info density, boilerplate detection,
   │              semantic dedup (quality_filter.py)
   ▼
  ABSORB ────── Stored in Qdrant + Mem0 + Neo4j + JSON backup
   │              (knowledge_ingestor.py) — four destinations, one write
   ▼
  TEST ──────── Health scoring, hallucination detection, spaced-repetition
   │              training on weak areas (brain_trainer.py)
   ▼
  SLEEP ─────── 10-phase nightly dream cycle at 2 AM (dream_mode.py)
   │              Deep extraction, cross-doc insights, synaptic pruning,
   │              price conflict checks, episodic→semantic consolidation
   ▼
  FORGET ────── 30d decay → 90d archive → 180d prune
   │              Recall boosts importance ("use it or lose it")
   ▼
  SPEAK ─────── Adaptive tone/length/format per channel (voice_system.py)
   │
   ▼
  GROW ──────── Every email digested triggers growth_signal.py,
                 which stimulates every body system simultaneously
```

### The Organ Systems

**Immune System** (`immune_system.py`) — Auto-remediation of chronic knowledge issues. Escalation ladder from log → flag → remediate → block. Writes corrections into Mem0 as high-priority memories.

**Respiratory System** (`respiratory_system.py`) — Operational heartbeat. Breath timing, HRV-like latency metrics, daily rhythm orchestration. Keeps Ira "breathing" on schedule.

**Endocrine System** (`endocrine_system.py`) — Agent scoring with dopamine/cortisol signals. Successful agents get rewarded (higher trust scores). Failing agents get penalized. It's natural selection for AI skills.

**Voice System** (`voice_system.py`) — Adaptive response shaping. Telegram gets short, punchy answers (max 2000 chars, sparingly emoji). Email gets formal, detailed responses (max 8000 chars, no emoji). API gets structured markdown. The same answer, reshaped for the channel.

**Musculoskeletal System** (`musculoskeletal_system.py`) — Action-to-learning feedback. Every email sent, quote generated, or lead researched produces "myokines" that feed the dream cycle. Activity literally makes Ira stronger.

**Sensory System** (`sensory_system.py`) — Cross-channel perception. Recognizes the same customer whether they message on Telegram, email, or API. Unified identity resolution.

**Metabolic System** (`metabolic_system.py`) — Active knowledge hygiene. Periodic cleanup of contradictions, stale facts, and Qdrant waste. The janitorial crew that keeps the knowledge base clean.

**Growth Signal** (`growth_signal.py`) — The growth hormone. One call after each email digestion stimulates every body system simultaneously. It's how Ira grows from every interaction.

### The Memory System

Ira doesn't just remember things — she remembers them *the right way*.

| Type | What it stores | Where | Decay |
|------|---------------|-------|-------|
| **Episodic** | Conversation history, interaction records | Mem0, JSON logs | 30d → archive |
| **Semantic** | Facts, specs, pricing, learned knowledge | Qdrant, Mem0 | Use-it-or-lose-it |
| **Procedural** | Learned workflows, response patterns | Mem0 | Slow decay |
| **Identity** | Cross-channel user recognition | CRM database | Permanent |

The dream cycle consolidates episodic memories into durable semantic facts. The correction learner detects when users correct Ira and stores corrections as high-priority memories. The interaction learner mines conversation logs for recurring patterns and distills them into knowledge.

---

## Quick Start

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

Start the bot, then talk to Ira naturally:

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

---

## The Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| LLM | GPT-4o | Main brain. Athena's engine. |
| Fast LLM | GPT-4o-mini | Metadata labeling, code generation, extraction |
| Embeddings | Voyage AI (voyage-3, 1024d) | Best-in-class for technical documents |
| Vector DB | Qdrant (6 collections) | Document chunks, emails, discovered knowledge, dream knowledge, market research, customers |
| Memory | Mem0 | Long-term semantic memory with conflict resolution and temporal decay |
| Graph DB | Neo4j | Entity relationships and knowledge graph |
| Reranking | FlashRank / ColBERT | Result relevance optimization after retrieval |
| Search | Hybrid (vector + BM25) | Best of semantic and keyword search |
| CRM | SQLite (`ira_crm.db`) | Contacts, leads, conversations, deals, email logs |
| Messaging | Telegram Bot API | Primary user interface |
| Email | Gmail API (OAuth) | Email processing, smart replies, drip campaigns |
| Google | Sheets, Drive, Calendar, Contacts | Read-only access to business data |
| Web Intel | Jina AI (search + scrape) | Iris's eyes and ears on the web |
| NER | spaCy | Named entity recognition during digestion |
| Keywords | YAKE | Keyword extraction for metadata enrichment |
| PDF | PyMuPDF + pdfplumber | Document extraction |
| Dashboard | FastAPI + Jinja2 | Internal monitoring |
| Scheduling | schedule | Cron-like task scheduling |

### Qdrant Collections

| Collection | Contents |
|-----------|----------|
| `ira_chunks_v4_voyage` | Document chunks (the main knowledge base) |
| `ira_emails_voyage_v2` | Ingested email content |
| `ira_discovered_knowledge` | Knowledge discovered during dream cycles |
| `ira_dream_knowledge_v1` | Cross-document insights from dreams |
| `ira_market_research_voyage` | Prometheus's market research |
| `ira_customers` | Customer profiles and history |

---

## Everything We Built

### Core Pipeline

- **Unified retriever** — hybrid vector (Voyage AI) + BM25 keyword search with FlashRank reranking across 6 Qdrant collections.

- **Knowledge ingestor** — quad-destination storage (Qdrant chunks, Qdrant emails, Mem0, JSON backup) with smart chunking (2K chars, 200 overlap), SHA-256 dedup, and semantic near-duplicate detection.

- **Quality filter** — pre-ingestion excretion system: min word count, information density scoring, boilerplate detection, and periodic Qdrant waste disposal.

- **Stomach enrichment** — spaCy NER + YAKE keyword extraction injected into metadata before embedding.

- **URL fetcher** — Jina Reader → trafilatura → regex fallback, with centralized HTML cleaning.

- **Heartbeat ingest** — cron-ready file watcher for `data/imports/` with Telegram notifications on new ingestion.

### Brain & Learning

- **Dream mode** — 10-phase nightly cycle: deep extraction, cross-document insights, synaptic pruning, price conflict checks, episodic-to-semantic consolidation, morning summary.

- **Brain trainer** — spaced-repetition quiz system targeting weak knowledge areas; writes reinforcement weights consumed by the answer generator.

- **Knowledge health monitor** — scores responses 0–100 based on document coverage, truth hints, hallucination detection, and model number validation.

- **Correction learner** — detects when users correct Ira and stores corrections as high-priority memories.

- **Interaction learner** — mines conversation logs for recurring patterns and distills them into semantic knowledge.

- **Truth hints** — fast-path cached answers for common questions (company info, machine series basics, lead times, warranty). Pattern-matched with confidence scores. Bypasses the full tool loop for simple queries.

### Channels & Communication

- **Telegram gateway** — rich formatting, inline keyboards, document upload, URL ingestion, 50+ commands, live thinking indicators.

- **Email handler** — Gmail integration with OAuth, smart drafting, lead qualification, drip campaigns, thread management, domain allowlist for sending.

- **API server** — RESTful interface for custom integrations.

- **Dashboard** — FastAPI + Jinja2 internal monitoring dashboard.

### Sales Intelligence

- **Iris intelligence** — real-time company research via Jina AI, industry trends, competitive intelligence, geopolitical context. 24-hour cache. Batch processing for multiple leads.

- **Hermes outreach** — 7-stage adaptive drip campaigns (INTRO → VALUE → TECHNICAL → SOCIAL PROOF → EVENT → BREAKUP → RE-ENGAGE). Context dossiers per lead. Regional tone adaptation. Reply detection and classification. Learning loop for what works.

- **Prometheus discovery** — scans 10 emerging industries for vacuum forming opportunities. Scores by technical fit, market timing, volume match, competitive gap, revenue potential. Maps products to Machinecraft machine series.

- **Quote generator** — PDF quote generation with machine database integration and CRM pipeline tracking.

- **Lead qualification** — automatic scoring and prioritization of inbound inquiries.

### Finance

- **Plutus finance agent** — order book status, cashflow forecasting, revenue history, CFO dashboard with KPIs, concentration risk, cashflow timelines, risk registers, and recommendations. Reads from Excel, PDF, and JSON sources. EUR/INR and USD/INR conversion.

### Memory & Identity

- **Persistent memory** — cross-channel memory with importance scoring, temporal decay, and "use it or lose it" retrieval boosting. Conflict resolution for contradictory facts.

- **Unified identity** — resolves users across Telegram, email, and API into a single identity.

- **Memory consolidation** — episodic memories distilled into durable semantic facts during the dream cycle.

- **CRM system** — SQLite database with contacts, leads, conversations, deals, email logs. Deal pipeline from `new` through `won/lost/dormant`. 7-source customer list with deduplication.

### Holistic Body Systems

- **Immune system** — auto-remediation of chronic knowledge issues; escalation ladder from log → flag → remediate → block. Writes corrections into Mem0.

- **Respiratory system** — operational heartbeat, breath timing, HRV-like latency metrics, daily rhythm orchestration.

- **Endocrine system** — agent scoring with dopamine/cortisol signals; rewards successful agents, penalizes failures.

- **Musculoskeletal system** — action-to-learning feedback; every email sent, quote generated, or lead researched produces myokines that feed the dream cycle.

- **Sensory system** — cross-channel perception integration; recognizes the same customer across Telegram, email, and API.

- **Metabolic system** — active knowledge hygiene; periodic cleanup of contradictions, stale facts, and Qdrant waste.

- **Voice system** — adaptive response shaping; Telegram (short, punchy, max 2000 chars), Email (formal, detailed, max 8000 chars), API (structured markdown).

- **Growth signal** — the growth hormone; one call after each email digestion stimulates every body system simultaneously.

---

## Project Structure

```
ira/
├── openclaw/agents/ira/             # Main application
│   ├── agent.py                     # Unified agent coordinator
│   ├── config.py                    # Centralized configuration
│   └── src/
│       ├── core/                    # Athena (tool_orchestrator), unified gateway, streaming
│       ├── brain/                   # RAG, retrieval, knowledge pipeline (60+ modules)
│       ├── agents/                  # The Pantheon
│       │   ├── researcher/          # Clio — research skill
│       │   ├── iris_skill.py        # Iris — intelligence
│       │   ├── hermes/              # Hermes — sales outreach
│       │   ├── prometheus/          # Prometheus — market discovery
│       │   ├── finance_agent/       # Plutus — finance
│       │   ├── hephaestus/          # Hephaestus — code forge
│       │   ├── crm_agent/           # Mnemosyne — CRM
│       │   ├── writer/              # Calliope — writing
│       │   ├── fact_checker/        # Vera — fact checking
│       │   ├── reflector/           # Sophia — reflection
│       │   └── chief_of_staff/      # Chief of Staff — error tracking
│       ├── holistic/                # Body systems: immune, respiratory, endocrine, voice, growth
│       ├── memory/                  # Persistent memory, dream mode, consolidation (20+ modules)
│       ├── conversation/            # Conversation intelligence, entity extraction, goals
│       ├── identity/                # Cross-channel identity resolution
│       ├── crm/                     # CRM, lead intelligence, drip campaigns, quotes
│       ├── sales/                   # Quote generation, autonomous drip engine, outreach
│       ├── market_research/         # Deep research, euro scraper, keyword extraction
│       ├── tools/                   # Tool schemas, Google tools, analysis tools
│       ├── skills/                  # Skill invocation dispatch
│       └── dashboard/               # FastAPI monitoring dashboard
│
├── agents/                          # Legacy/standalone agents (Iris, Apollo, Athena, Prometheus)
├── skills/                          # OpenClaw skills (24 skills)
├── scripts/                         # Utility scripts (150+ files)
├── data/                            # Documents, knowledge, memory, state
│   ├── brain/                       # machine_specs.json, hard_rules.txt, training data
│   ├── imports/                     # Drop zone for new documents
│   ├── holistic/                    # Body system state files
│   ├── cache/                       # Iris cache, lead intelligence cache
│   ├── discovery/                   # Prometheus results
│   └── knowledge/                   # Sales playbook, reference docs
├── crm/                             # CRM databases (SQLite)
├── docs/                            # Documentation (20+ files)
├── tests/                           # Test suite
├── docker-compose.yml               # Qdrant + PostgreSQL
├── start_ira.sh                     # Main launcher
├── requirements.txt                 # Python dependencies
└── pyproject.toml                   # Project config (v1.0.0)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key (GPT-4o) |
| `VOYAGE_API_KEY` | Yes | Voyage AI embeddings |
| `QDRANT_URL` | Yes | Qdrant vector database URL |
| `TELEGRAM_BOT_TOKEN` | For Telegram | Telegram bot token |
| `EXPECTED_CHAT_ID` | For Telegram | Authorized chat ID |
| `MEM0_API_KEY` | Optional | Mem0 memory service |
| `NEO4J_URI` | Optional | Neo4j knowledge graph |
| `DATABASE_URL` | Optional | PostgreSQL connection |
| `JINA_API_KEY` | For Iris | Jina AI web search |
| `GOOGLE_CREDENTIALS` | For Email/Sheets | Google OAuth credentials |

See [.env.example](.env.example) for the complete list.

## Development

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=openclaw --cov-report=html

# Run the deep benchmark (verifies nothing is broken)
python3 scripts/benchy_deep.py --quick --telegram

# Lint
ruff check openclaw/ scripts/

# Format
black openclaw/ scripts/ tests/
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md) | System architecture and data flow |
| [Agent Architecture](docs/AGENT_ARCHITECTURE.md) | Multi-agent design and the Pantheon |
| [Knowledge System](docs/KNOWLEDGE_DISCOVERY_ARCHITECTURE.md) | RAG, retrieval, and knowledge graph |
| [Knowledge Ingestion](docs/KNOWLEDGE_INGESTION.md) | Document pipeline (EAT → ABSORB) |
| [Dream Mode](docs/DREAM_MODE_AUDIT.md) | Nightly consolidation and learning |
| [Telegram Guide](docs/TELEGRAM_BEST_PRACTICES.md) | Bot setup and usage |
| [How We Built Ira](docs/about-ira/HOW_WE_BUILT_IRA.md) | Origin story |

## Roadmap

- [ ] Web dashboard for analytics and monitoring
- [ ] WhatsApp channel integration
- [ ] Voice interface (Whisper)
- [ ] Multi-language support
- [ ] CRM integrations (Salesforce, HubSpot)

## License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built for <a href="https://machinecraft.in">Machinecraft Technologies</a></strong><br>
  <sub>An AI that eats documents, dreams about them, and wakes up smarter.</sub>
</p>
