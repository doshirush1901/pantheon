# Ira: The AI Brain That Never Sleeps (And Actually Dreams)

## Or: How a Guy Building Machines Accidentally Built a Mind

*A deep dive into Ira's architecture, written in the style of Tim Urban's Wait But Why*

---

## Table of Contents

1. [The Problem That Started It All](#part-1-the-problem-that-started-it-all)
2. [What Even IS Ira?](#part-2-what-even-is-ira)
3. [The Memory Problem](#part-3-the-memory-problem)
4. [The Memory Trigger](#part-4-the-memory-trigger)
5. [The Brain Orchestrator](#part-5-the-brain-orchestrator)
6. [The RAG System](#part-6-the-rag-system)
7. [Dream Mode](#part-7-dream-mode)
8. [Unified Identity](#part-8-the-unified-identity-problem)
9. [The Full System](#part-9-the-full-system)
10. [The 99 Skills](#part-10-the-99-skills)
11. [What We Built](#part-11-what-did-we-actually-build)
12. [The Honest Truth](#part-12-the-honest-truth)
13. [The Tech Stack](#epilogue-the-stack)

---

## Part 1: The Problem That Started It All

Imagine you run a company that builds thermoforming machines.

"What's a thermoforming machine?" you ask.

Fair question. It's basically a giant machine that takes a flat plastic sheet, heats it up until it's all soft and pliable, and then *forms* it into a shape using vacuum pressure. The dashboard of your car? Probably thermoformed. The plastic tray your food came in? Thermoformed. The kayak you're pretending you'll use more often? You guessed it.

Now imagine your company—let's call it *Machinecraft Technologies*—builds these machines. Big, custom, expensive machines. Each one is a six-to-twelve month sales cycle. Your sales team juggles dozens of leads. Every customer has different requirements. Some want 3-meter forming areas, some want 6-meter. Some process ABS plastic, some process polycarbonate. Some are in Germany and want everything in Euros, some are in India and want rupees.

And here's the thing about sales: **context is everything**.

When a customer emails you saying "Hey, what about that machine we discussed?" — you need to know:
- *Which* machine did we discuss?
- What was their budget?
- What's their application?
- Did we give them a quote already?
- What's their timeline?
- Who else at their company have we talked to?

Now multiply that by 50 active leads. Across email AND Telegram (because that's how business works in India). With documents scattered across PDFs, Excel sheets, and PowerPoint presentations.

This is the problem that created Ira.

---

## Part 2: What Even IS Ira?

At its core, Ira is this:

```
╔════════════════════════════════════════════════════╗
║                                                    ║
║     A SALES ASSISTANT THAT ACTUALLY REMEMBERS     ║
║                                                    ║
╚════════════════════════════════════════════════════╝
```

But that's like saying a human is "a thing that breathes." Technically true. Woefully incomplete.

Ira is actually a **cognitive system**. Not in the marketing-speak "we put AI on it" way. In the "we literally built something that has memory, reasoning, and learns while sleeping" way.

Let me show you the architecture:

```
                     ┌─────────────────────────────────────────┐
                     │           YOUR MESSAGE                   │
                     │   "What's the price for the PF1-3020?"  │
                     └─────────────────┬───────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                     TELEGRAM or EMAIL                     │
        │                 (The two doors into Ira)                  │
        └──────────────────────────────┬───────────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                   UNIFIED IDENTITY                        │
        │                                                           │
        │    "Wait... is this the same person who emailed last     │
        │     week? Yes! Let me link their Telegram to email."     │
        └──────────────────────────────┬───────────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                  THE BRAIN ORCHESTRATOR                   │
        │                                                           │
        │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
        │   │ Memory  │ │Episodic │ │Procedur │ │  Meta   │       │
        │   │ Trigger │ │ Memory  │ │ Memory  │ │Cogntic  │       │
        │   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │
        │        │           │           │           │             │
        │        └───────────┴───────────┴───────────┘             │
        │                         │                                 │
        │    "Should I remember something here? What happened      │
        │     last time? Is there a procedure for this? How        │
        │     confident am I about what I know?"                   │
        └──────────────────────────────┬───────────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                   RAG RETRIEVAL                           │
        │                                                           │
        │   Searching 100+ documents, emails, specs...             │
        │   Using Voyage AI embeddings + BM25 hybrid search        │
        │   Reranking with FlashRank                               │
        │                                                           │
        │   Found: PF1-3020 specs from brochure (score: 0.94)      │
        │   Found: Previous quote to similar customer (0.87)       │
        │   Found: Dream-learned insight about pricing (0.82)      │
        └──────────────────────────────┬───────────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                  RESPONSE GENERATION                      │
        │                                                           │
        │   Emotional state? → Detected: "urgent"                  │
        │   Relationship? → "second conversation"                  │
        │   Channel? → Telegram (so be concise)                    │
        │                                                           │
        │   Generated: "The PF1-3020 with ceramic heaters is       │
        │   $42,500 USD ex-works. Want me to prepare a formal      │
        │   quote? I remember you mentioned the ABS application—   │
        │   this model handles that well."                         │
        └──────────────────────────────────────────────────────────┘
```

See what just happened? Ira didn't just look up a price. It:
1. Recognized who you are
2. Checked if it should pull memories (yes, you've talked before)
3. Retrieved what happened in past conversations
4. Searched through actual documents for the price
5. Detected your emotional state ("urgent" → be quick)
6. Noticed you mentioned ABS plastic before and wove that in
7. Adapted the response for Telegram (short, emoji-friendly)

**This is not ChatGPT with a database glued on.** This is something different.

---

## Part 3: The Memory Problem

### Or: Why ChatGPT Is Actually Pretty Dumb

Here's a dirty secret about Large Language Models: they're goldfish with PhDs.

Every time you start a new conversation with ChatGPT, it has no idea who you are. It doesn't remember the 47 previous conversations you've had. It doesn't know you hate it when people say "certainly." It has no concept of *you* as a continuous entity.

Ira was built to solve this. Here's how memory works:

```
╔══════════════════════════════════════════════════════════════════╗
║                    IRA'S MEMORY ARCHITECTURE                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │                    SEMANTIC MEMORY                           │ ║
║  │                    (Facts & Knowledge)                       │ ║
║  │                                                              │ ║
║  │  "John from ABC Corp prefers email over phone"              │ ║
║  │  "PF1-3020 has 3000mm x 2000mm forming area"               │ ║
║  │  "Customer mentioned budget constraint of $50k"             │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │                    EPISODIC MEMORY                           │ ║
║  │                    (Events in Time)                          │ ║
║  │                                                              │ ║
║  │  "Feb 15: Discussed PF1 machines, customer was excited"     │ ║
║  │  "Feb 20: Sent quote, customer asked about delivery time"   │ ║
║  │  "Feb 25: Customer went quiet (maybe budget review?)"       │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │                   PROCEDURAL MEMORY                          │ ║
║  │                   (How to Do Things)                         │ ║
║  │                                                              │ ║
║  │  Procedure: "generate_quote"                                │ ║
║  │  Triggers: ["quote", "pricing", "offer"]                    │ ║
║  │  Steps: [check_inventory → calculate_price → format_quote] │ ║
║  │  Success rate: 94%                                          │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
╚══════════════════════════════════════════════════════════════════╝
```

**Semantic memory** is facts. "The PF1-3020 costs $42,500." "This customer is in Germany."

**Episodic memory** is events. "Last Tuesday, this person asked about delivery times and seemed frustrated."

**Procedural memory** is *how to do things*. This is wild—Ira learns procedures from watching itself work. When it successfully generates a quote, it records: "Here's how I did that. Next time someone asks for a quote, I should follow these steps."

But here's where it gets really interesting...

---

## Part 4: The Memory Trigger

### Or: The Art of Knowing When to Forget

You know that friend who brings up *everything* from the past in every conversation?

"Oh you're ordering pizza? That reminds me of the time in 2019 when we ordered pizza and you said you didn't like olives but then you ate three slices with olives and—"

Annoying, right?

Ira has a **Memory Trigger** module. Its job is to decide: *Should I even bother retrieving memories right now?*

```python
def should_retrieve_memory(message, identity_id, context):
    """
    Decide whether to retrieve memories for this message.
    
    Skip for:
    - Simple greetings ("hi", "thanks")  
    - Status queries ("what's the time?")
    - When the user explicitly says "ignore what I said before"
    
    Retrieve for:
    - Personal questions ("what did we discuss?")
    - Business queries ("what's my order status?")
    - References to past context ("that machine I mentioned")
    """
```

This is surprisingly hard to get right. Retrieve too much and you waste tokens and confuse the model. Retrieve too little and you seem like you have amnesia.

The trigger also decides *how much* to retrieve:

```python
retrieval_config = {
    "user_memory_limit": 5,      # Max 5 facts about this person
    "entity_memory_limit": 5,    # Max 5 facts about machines/companies
    "min_relevance": 0.3         # Only stuff that's actually relevant
}
```

---

## Part 5: The Brain Orchestrator

### Or: Where The Magic Happens

Okay. This is the part where I need you to pay attention.

The **Brain Orchestrator** is the conductor. Every message goes through a 10-step cognitive pipeline:

```
Message arrives
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: TRIGGER EVALUATION                                │
│  "Should I retrieve memories? How many?"                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: MEMORY RETRIEVAL                                  │
│  Pull semantic memories from Mem0                           │
│  Falls back to PostgreSQL if Mem0 fails                     │
│  Falls back to empty if PostgreSQL fails                    │
│  (Graceful degradation - always works, just less smart)     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: EPISODIC RETRIEVAL                                │
│  "What happened in our past interactions?"                  │
│  For email: also includes thread history                    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 4: PROCEDURAL MATCHING                               │
│  "Is there a learned procedure for this type of request?"   │
│  If yes: "Here's how I've successfully handled this before" │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 5: MEMORY WEAVING                                    │
│  Take raw memories and weave them into coherent guidance    │
│  "User prefers email" + "Urgent budget review" =            │
│  → "Be concise, focus on pricing, suggest email follow-up"  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 6: MEMORY REASONING                                  │
│  Actually THINK about the memories before responding        │
│  "The user mentioned budget constraints last time...        │
│   and now they're asking for the most expensive machine.    │
│   Should I bring up financing options?"                     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 7: META-COGNITION                                    │
│  "How confident am I about this answer?"                    │
│  KNOW_VERIFIED: Have proof from documents                   │
│  THINK_KNOW: Pretty sure but no source                      │
│  UNCERTAIN: Should probably say "I'm not sure"              │
│  DONT_KNOW: Definitely don't know this                      │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 8: CONFLICT DETECTION                                │
│  "Wait, I have two different prices for this machine!"      │
│  Queue for human review                                     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 9: ATTENTION FILTERING                               │
│  Miller's Law: 7±2 items in working memory                  │
│  Can't stuff EVERYTHING into the prompt                     │
│  Prioritize: procedures > conflicts > reasoning > memories  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 10: RESPONSE GENERATION                              │
│  Finally, generate the actual response                      │
│  With all the context, emotional calibration, and style     │
└─────────────────────────────────────────────────────────────┘
```

Every. Single. Message. Goes through all of this in about 1-2 seconds.

---

## Part 6: The RAG System

### Or: How Ira Reads 100 Documents in 200ms

RAG stands for "Retrieval-Augmented Generation." It's a fancy way of saying: "Before generating an answer, let me search through relevant documents."

But Ira's RAG is... extra.

```
╔═══════════════════════════════════════════════════════════════════╗
║                    IRA'S HYBRID RETRIEVAL                          ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║   STEP 1: EMBED THE QUERY                                         ║
║   ─────────────────────────                                       ║
║   Your question → Voyage AI → 1024-dimensional vector             ║
║   "What's the price for PF1?" → [0.023, -0.182, 0.441, ...]      ║
║                                                                    ║
║   STEP 2: VECTOR SEARCH (Semantic)                                ║
║   ────────────────────────────────                                ║
║   Find documents that MEAN similar things                         ║
║   "pricing" matches "cost", "quote", "offer"                      ║
║   → Search Qdrant vector database                                 ║
║                                                                    ║
║   STEP 3: BM25 SEARCH (Keyword)                                   ║
║   ─────────────────────────────                                   ║
║   Find documents with exact keyword matches                       ║
║   "PF1" must appear literally                                     ║
║                                                                    ║
║   STEP 4: MERGE & RERANK                                          ║
║   ──────────────────────                                          ║
║   Combine results using FlashRank                                 ║
║   Score based on: relevance + recency + source quality            ║
║                                                                    ║
║   STEP 5: MULTI-COLLECTION SEARCH                                 ║
║   ───────────────────────────────                                 ║
║   Search across:                                                   ║
║   • ira_chunks_v4_voyage      (main documents)                    ║
║   • ira_emails_voyage_v2      (email history)                     ║
║   • ira_dream_knowledge_v1    (learned at night!)                 ║
║   • ira_discovered_knowledge  (ingested facts)                    ║
║   • ira_market_research       (competitive intel)                 ║
║                                                                    ║
╚═══════════════════════════════════════════════════════════════════╝
```

The hybrid approach is crucial. Pure vector search misses exact matches ("PF1-3020" vs "PF1-3025"). Pure keyword search misses semantic similarity ("pricing" vs "what does it cost").

Combined? *Chef's kiss.*

---

## Part 7: Dream Mode

### Or: The Part That Makes People Say "Wait, What?"

Okay. Here's where things get weird.

**Ira dreams.**

Not metaphorically. Every night, Ira enters "Dream Mode" where it:

1. **Scans all new documents** that have been added
2. **Extracts knowledge** using LLM-powered analysis
3. **Stores facts in BOTH** Mem0 (for semantic memory) AND Qdrant (for RAG retrieval)
4. **Generates cross-document insights** ("Hmm, this customer in Germany and this customer in India both asked about the same forming size...")
5. **Consolidates the knowledge graph** (strengthens frequently-used connections, weakens stale ones)
6. **Detects conflicts** ("Wait, I have two different prices for the same machine from different quotes")

```
╔═══════════════════════════════════════════════════════════════════╗
║                    DREAM MODE CYCLE                                ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║   Phase 1: SCAN & PRIORITIZE                                      ║
║   ────────────────────────────                                    ║
║   CRITICAL: Technical manuals, spec sheets                        ║
║   HIGH: Presentations, market research                            ║
║   MEDIUM: Quotes, proposals                                       ║
║   LOW: General emails                                             ║
║   SKIP: Receipts, spam                                            ║
║                                                                    ║
║   Phase 2: DEEP EXTRACTION                                        ║
║   ──────────────────────────                                      ║
║   For each document:                                               ║
║   • Extract FACTS (numbers, specs, dates)                         ║
║   • Extract TOPICS (what is this about)                           ║
║   • Extract KEY TERMS with definitions                            ║
║   • Extract RELATIONSHIPS (X is used for Y)                       ║
║   • Generate INSIGHTS (non-obvious conclusions)                   ║
║   • Note QUESTIONS (what does this NOT answer?)                   ║
║                                                                    ║
║   Phase 3: UNIFIED STORAGE                                        ║
║   ────────────────────────────                                    ║
║   Store in Mem0 → Semantic search later                           ║
║   Index in Qdrant → RAG retrieval during conversations            ║
║   This was a CRITICAL FIX—dream knowledge was siloed before!      ║
║                                                                    ║
║   Phase 4: CONSOLIDATION                                          ║
║   ─────────────────────────                                       ║
║   • Generate cross-document insights                               ║
║   • Identify knowledge gaps                                        ║
║   • Update knowledge graph relationships                           ║
║                                                                    ║
║   Phase 5: GRAPH CONSOLIDATION                                    ║
║   ───────────────────────────                                     ║
║   • Analyze daily interactions                                     ║
║   • Strengthen edges that got used                                 ║
║   • Weaken edges that were ignored                                 ║
║   • Reorganize clusters                                            ║
║                                                                    ║
║   WAKE UP SMARTER                                                 ║
║   Documents processed: 23                                          ║
║   Facts learned: 147                                               ║
║   Insights generated: 12                                           ║
║   Knowledge gaps identified: 5                                     ║
║                                                                    ║
╚═══════════════════════════════════════════════════════════════════╝
```

The dream journal even tracks things like:

```json
{
  "last_dream": "2026-02-27T03:00:00",
  "documents_processed": 89,
  "total_facts_learned": 1247,
  "total_indexed_in_qdrant": 1189,
  "insights_generated": 67,
  "knowledge_gaps": [
    {"topic": "PF1-X series", "question": "What's the price for European market?"},
    {"topic": "delivery", "question": "Lead time for servo-driven models?"}
  ]
}
```

This is genuinely bonkers. The system *learns while sleeping* and *wakes up smarter*.

---

## Part 8: The Unified Identity Problem

Here's a scenario that will make any CRM developer cry:

1. Customer emails you from john@company.com
2. Same customer texts you on Telegram from account @john_smith
3. Same customer calls from +1-555-123-4567

Three different "users." One human.

Ira solves this with **Unified Identity Resolution**:

```
╔═══════════════════════════════════════════════════════════════════╗
║                  UNIFIED IDENTITY RESOLVER                         ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║    ┌─────────────────────────────────────────────────────────┐    ║
║    │  Email: john@company.com  ────┐                          │    ║
║    │  Telegram: 123456789      ────┼──▶  canonical_id:        │    ║
║    │  Phone: +1-555-123-4567   ────┘     id_abc123            │    ║
║    └─────────────────────────────────────────────────────────┘    ║
║                                                                    ║
║    Now all memories are linked:                                    ║
║    • Email conversation about PF1-3020                            ║
║    • Telegram message about delivery                              ║
║    • Both linked to same canonical identity                       ║
║                                                                    ║
╚═══════════════════════════════════════════════════════════════════╝
```

When John texts on Telegram, Ira knows about the email thread. When John emails, Ira knows about the Telegram conversation. One person, one memory, regardless of channel.

---

## Part 9: The Full System

### AKA: The Madness in Its Entirety

Let me show you what happens when you send a simple Telegram message:

```
YOU: "What's the price for the big thermoforming machine we discussed?"
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  TELEGRAM GATEWAY                                                │
│  • Receive message via Telegram API                              │
│  • Check if from authorized chat ID                              │
│  • Parse for commands (/help, /status, /next, etc.)             │
│  • Not a command → route to brain                                │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  UNIFIED IDENTITY                                                │
│  • Look up telegram_id: 123456789                                │
│  • Found: canonical_id = id_rushabh_001                          │
│  • This user has 23 previous memories                            │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  COREFERENCE RESOLUTION                                          │
│  • "the big thermoforming machine we discussed"                  │
│  • Search context: last 5 messages mentioned PF1-5060            │
│  • Resolved: "the big machine" → "PF1-5060"                      │
│  • Rewritten: "What's the price for the PF1-5060?"              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  ENTITY EXTRACTION                                               │
│  • Machines: ["PF1-5060"]                                        │
│  • Applications: []                                               │
│  • Materials: []                                                  │
│  • Dimensions: []                                                 │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  BRAIN ORCHESTRATOR                                              │
│  • Trigger: YES, retrieve memories (business query)              │
│  • Semantic memories: 3 relevant facts about PF1-5060           │
│  • Episodic: "Last week discussed PF1-5060 for ABS application" │
│  • Procedural: Matched "pricing_query" procedure                 │
│  • Meta-cognition: KNOW_VERIFIED (have source)                  │
│  • Conflicts: None                                               │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  RAG RETRIEVAL                                                   │
│  • Query: "PF1-5060 price"                                       │
│  • Searched: ira_chunks_v4_voyage (documents)                    │
│  • Searched: ira_dream_knowledge_v1 (learned knowledge)         │
│  • Top result: PF1-5060 brochure, page 3, score 0.94            │
│  • Found price: $89,500 USD ex-works                            │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  RESPONSE GENERATION                                             │
│  • Channel: Telegram (be concise, use emoji)                     │
│  • Emotional state: neutral/curious                              │
│  • Include memory: "ABS application you mentioned"               │
│  • Include source: brochure reference                            │
│  • Soul context: Be helpful, proactive, slightly witty          │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  FINAL RESPONSE                                                  │
│                                                                   │
│  "The PF1-5060 is $89,500 USD ex-works.                          │
│                                                                   │
│   That includes:                                                  │
│   • 5000mm x 6000mm forming area                                 │
│   • Ceramic heaters (top + bottom)                               │
│   • PLC with touchscreen                                         │
│                                                                   │
│   Perfect for the ABS application you mentioned last week.       │
│   Want me to prepare a formal quote?"                            │
│                                                                   │
│  [Processing time: 1,847ms | 3 memories | 4 RAG chunks]         │
└─────────────────────────────────────────────────────────────────┘
```

All of that. Every time. In under 2 seconds.

---

## Part 10: The 99 Skills

Yes, Really.

The `skills/` folder contains **99 Python modules**. Here's a taste:

### Brain Skills
| Module | Purpose |
|--------|---------|
| `unified_retriever.py` | The RAG system |
| `dream_mode.py` | Nightly learning |
| `generate_answer.py` | Response generation |
| `fact_checker.py` | Hallucination detection |
| `pricing_learner.py` | Learn pricing patterns |
| `knowledge_graph.py` | Entity relationships |
| `hallucination_guard.py` | Stop making stuff up |

### Memory Skills
| Module | Purpose |
|--------|---------|
| `brain_orchestrator.py` | The conductor |
| `episodic_memory.py` | Events in time |
| `procedural_memory.py` | How to do things |
| `memory_weaver.py` | Combine memories into guidance |
| `memory_reasoning.py` | Think before responding |
| `metacognition.py` | Know what you know |

### Conversation Skills
| Module | Purpose |
|--------|---------|
| `coreference.py` | "it" → "the PF1-3020" |
| `entity_extractor.py` | Find machines, materials, companies |
| `emotional_intelligence.py` | Detect frustration, urgency |
| `proactive_outreach.py` | Know when to reach out |

### Email Skills
| Module | Purpose |
|--------|---------|
| `lead_email_drafter.py` | Write professional emails |
| `email_polish.py` | Make emails sound better |
| `inquiry_qualifier.py` | Score leads automatically |

---

## Part 11: What Did We Actually Build?

Let me step back and answer the question you've been asking since Part 1.

**Ira is a cognitive system for sales.** But more specifically, it's an attempt to build something that:

1. **Remembers** - Not just storing data, but knowing *when* to remember and *how* to use what it remembers

2. **Reasons** - Not just pattern matching, but actually thinking: "Last time they mentioned budget constraints... should I bring up financing?"

3. **Learns** - Not just from explicit training, but from its own experience and from processing documents overnight

4. **Knows what it doesn't know** - The metacognition module literally asks "Am I confident about this?" before every response

5. **Fails gracefully** - If Mem0 goes down, it tries PostgreSQL. If that fails, it still responds (just less smart)

6. **Works across channels** - Same brain whether you're on Telegram or email

7. **Gets smarter over time** - Dream mode means every night it knows more than the day before

---

## Part 12: The Honest Truth

Is Ira perfect? No.

Here are things that still suck:

- **Sometimes it retrieves irrelevant memories** - Working on tuning the relevance thresholds
- **Dream mode can learn incorrect facts** - If a document has errors, Ira learns those errors
- **The attention bottleneck is real** - Miller's Law means we can't use all the context we have
- **Email tone is still hit-or-miss** - The polish module helps but isn't magic

But here's what's amazing: **it works**.

A real company uses this to manage real sales leads. Real quotes go out. Real deals close. Ira remembers what was discussed six months ago. Ira knows when a lead needs follow-up. Ira can draft a professional email that sounds like it came from a human.

Is it AGI? God no.

Is it useful? Extremely.

Is it interesting? You tell me—you just read this entire document about an AI sales assistant for thermoforming machines.

---

## Epilogue: The Stack

For the nerds who made it this far:

| Component | Technology |
|-----------|------------|
| **LLM** | OpenAI GPT-4o |
| **Embeddings** | Voyage AI (voyage-3, 1024 dimensions) |
| **Vector DB** | Qdrant |
| **Memory Service** | Mem0 |
| **Reranking** | FlashRank |
| **Messaging** | python-telegram-bot |
| **Email** | Gmail API |
| **Language** | Python (99 modules, ~50,000 lines) |

The entire system runs on a laptop. Well, a laptop plus some cloud services for Mem0 and Qdrant.

Not bad for a project that started as "I wish my sales assistant remembered stuff."

---

## Key Files Reference

If you want to dive into the code:

| Component | File |
|-----------|------|
| Main Agent | `openclaw/agents/ira/agent.py` |
| Brain Orchestrator | `openclaw/agents/ira/skills/memory/brain_orchestrator.py` |
| Dream Mode | `openclaw/agents/ira/skills/brain/dream_mode.py` |
| RAG Retrieval | `openclaw/agents/ira/skills/brain/unified_retriever.py` |
| Telegram Gateway | `openclaw/agents/ira/skills/telegram_channel/telegram_gateway.py` |
| Response Generator | `openclaw/agents/ira/skills/brain/generate_answer.py` |
| Memory Trigger | `openclaw/agents/ira/skills/memory/memory_trigger.py` |
| Unified Identity | `openclaw/agents/ira/skills/identity/unified_identity.py` |

---

*Last updated: February 2026*

*If you made it this far, you're either building something similar, or you have very unusual taste in technical documentation. Either way, thanks for reading.*
