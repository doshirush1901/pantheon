#!/usr/bin/env python3
"""
Truth Hints - Pre-defined Accurate Answers for Common Questions
===============================================================

Provides ground-truth responses for frequently asked questions about
Machinecraft, improving response accuracy and consistency.

Usage:
    from truth_hints import get_truth_hint, TruthHintMatcher
    
    hint = get_truth_hint("What is PF1?")
    if hint:
        # Use hint.answer as ground truth
        print(hint.answer)
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass
class TruthHint:
    """A pre-defined truth hint."""
    id: str
    question_patterns: List[str]
    answer: str
    category: str
    confidence: float = 0.95
    keywords: List[str] = None
    
    def matches(self, query: str) -> Tuple[bool, float]:
        """Check if query matches this hint."""
        query_lower = query.lower()
        
        # Check keyword match first (quick filter)
        if self.keywords:
            if not any(kw in query_lower for kw in self.keywords):
                return False, 0.0
        
        # Check pattern match
        for pattern in self.question_patterns:
            if re.search(pattern, query_lower):
                return True, self.confidence
        
        return False, 0.0


# =============================================================================
# MACHINECRAFT TRUTH HINTS
# =============================================================================

TRUTH_HINTS: List[TruthHint] = [
    # -------------------------------------------------------------------------
    # COMPANY INFO
    # -------------------------------------------------------------------------
    TruthHint(
        id="company_founding",
        question_patterns=[
            r"when.*founded|founded.*when",
            r"how old.*machinecraft",
            r"when.*start|start.*when",
            r"history.*machinecraft",
        ],
        answer="Machinecraft Technologies was founded in 1976 in Mumbai, India. With nearly 50 years of experience, we are one of the pioneers of thermoforming technology in Asia.",
        category="company",
        keywords=["founded", "when", "start", "history", "old"],
    ),
    TruthHint(
        id="company_location",
        question_patterns=[
            r"where.*located|location",
            r"where.*factory|factory.*where",
            r"address|headquarter",
        ],
        answer="Machinecraft is headquartered in Mumbai, India with manufacturing facilities in the Mumbai metropolitan region. We serve customers globally with offices and representatives across Asia, Europe, and the Americas.",
        category="company",
        keywords=["where", "located", "factory", "address", "headquarter"],
    ),
    TruthHint(
        id="what_is_machinecraft",
        question_patterns=[
            r"what is machinecraft",
            r"tell me about machinecraft",
            r"who is machinecraft",
        ],
        answer="Machinecraft Technologies is a leading manufacturer of thermoforming machines and automation solutions, founded in 1976 in India. We specialize in pressure forming (PF series), vacuum forming, and automation equipment for industries including automotive, packaging, medical, and aerospace.",
        category="company",
        keywords=["what", "machinecraft", "who", "tell"],
    ),
    
    # -------------------------------------------------------------------------
    # PRODUCTS - PF1 SERIES
    # -------------------------------------------------------------------------
    TruthHint(
        id="what_is_pf1",
        question_patterns=[
            r"what is pf[-\s]?1",
            r"tell me about pf[-\s]?1",
            r"pf[-\s]?1.*what",
            r"pf[-\s]?1.*series",
            r"pf[-\s]?1.*machine",
        ],
        answer="""PF1 is our flagship HEAVY-GAUGE vacuum forming machine series (single-station, closed chamber).

**Material Thickness:** >1.5mm up to 8mm (some models up to 10mm). This is NOT a thin-gauge or flexible materials machine.

**Materials:** ABS, HDPE, PC (Polycarbonate), PMMA (Acrylic), PP, HIPS, TPO, PVC — all in HEAVY GAUGE (thick sheets).

**Applications:** Automotive interiors, truck bedliners, refrigerator liners, luggage shells, EV battery enclosures, industrial enclosures, sanitary ware, equipment housings.

**NOT suitable for:** Flexible packaging, thin films, food trays, blister packs, clamshells — those need the AM Series (≤1.5mm).

**Key Features:** Closed chamber, sag control, pre-blow, zone heating, recipe management, servo drives (X variant), auto load/unload, plug assist.

**Variants:**
- PF1-C (pneumatic, affordable) — heavy gauge sheet-fed
- PF1-X (all-servo, premium) — heavy gauge sheet-fed
- PF1-R (roll-fed) — for thin materials 0.2mm to 1.5mm on PF1 platform

Available in sizes from PF1-C-1008 (1000x800mm) to PF1-C-3020 (3000x2000mm) forming area.""",
        category="product",
        keywords=["pf1", "pf-1", "pf 1"],
    ),
    TruthHint(
        id="pf1_sizes",
        question_patterns=[
            r"pf[-\s]?1.*size",
            r"pf[-\s]?1.*dimension",
            r"how big.*pf[-\s]?1",
            r"pf[-\s]?1.*model",
        ],
        answer="""PF1 is available in multiple sizes:
- PF1-1510: 1500 x 1000mm forming area (entry-level)
- PF1-2015: 2000 x 1500mm forming area
- PF1-3020: 3000 x 2000mm forming area (most popular)
- PF1-3030: 3000 x 3000mm forming area
- PF1-4022: 4000 x 2200mm forming area (largest)

Custom sizes available on request. The -X, -C, -S suffixes indicate different configurations (speed, servo, custom).""",
        category="product",
        keywords=["pf1", "size", "dimension", "model", "big"],
    ),
    TruthHint(
        id="pf1_price_range",
        question_patterns=[
            r"pf[-\s]?1.*price|price.*pf[-\s]?1",
            r"pf[-\s]?1.*cost|cost.*pf[-\s]?1",
            r"how much.*pf[-\s]?1",
            r"pf[-\s]?1.*inr|inr.*pf[-\s]?1",
        ],
        answer="""PF1 Pneumatic Machine Prices (INR Budget Pricing):

| Model | Size (mm) | Price (INR) |
|-------|-----------|-------------|
| PF1-C-1008 | 1000x800 | 33,00,000 |
| PF1-C-1208 | 1200x800 | 35,00,000 |
| PF1-C-1212 | 1200x1200 | 38,00,000 |
| PF1-C-1510 | 1500x1000 | 40,00,000 |
| PF1-C-1812 | 1800x1200 | 45,00,000 |
| PF1-C-2010 | 2000x1000 | 50,00,000 |
| PF1-C-2015 | 2000x1500 | 60,00,000 |
| PF1-C-2020 | 2000x2000 | 65,00,000 |
| PF1-C-2515 | 2500x1500 | 70,00,000 |
| PF1-C-3015 | 3000x1500 | 75,00,000 |
| PF1-C-3020 | 3000x2000 | 80,00,000 |
| PF1-R-1510 (Roll Feeder) | 1500x1000 | 55,00,000 |

Note: These are budget prices. Final quotation depends on specific configuration, automation level, tooling, and customizations. Contact sales for detailed quotation.""",
        category="product",
        keywords=["pf1", "price", "cost", "how much", "quotation", "inr", "lakh"],
        confidence=0.98,
    ),
    TruthHint(
        id="pf1_heavy_gauge",
        question_patterns=[
            r"pf[-\s]?1.*heavy",
            r"heavy.*gauge.*machine",
            r"thick.*sheet.*machine",
            r"machine.*thick.*abs",
            r"machine.*thick.*hdpe",
            r"machine.*[2-9]\s*mm",
            r"pf[-\s]?1.*material",
            r"pf[-\s]?1.*application",
            r"pf[-\s]?1.*used for",
            r"what.*pf[-\s]?1.*for",
            r"pf[-\s]?1.*suitable",
            r"pf[-\s]?1.*packaging",
            r"pf[-\s]?1.*rigid",
            r"pf[-\s]?1.*flexible",
        ],
        answer="""PF1 Series — Heavy-Gauge Thermoforming Machine:

**What PF1 is for:**
The PF1 is a HEAVY-GAUGE vacuum forming machine for thick plastic sheets (>1.5mm up to 8mm, some models up to 10mm).

**Materials:** ABS, HDPE, PC (Polycarbonate), PMMA (Acrylic), HIPS, TPO, PP — all in heavy gauge.

**Applications:**
- Automotive interiors (dashboards, door panels, trunk liners)
- Truck bedliners
- Refrigerator liners
- Luggage shells
- EV battery enclosures
- Industrial equipment housings
- Sanitary ware components

**What PF1 is NOT for:**
- NOT for flexible packaging or thin films
- NOT for food trays, blister packs, or clamshells
- NOT for materials ≤1.5mm (use AM Series instead)
- NOT a packaging machine — it is an industrial heavy-gauge forming machine

**Key Features:** Closed chamber, sag control, pre-blow, zone heating, servo drives, plug assist.""",
        category="product",
        keywords=["pf1", "heavy", "gauge", "thick", "abs", "hdpe", "application", "material", "packaging", "flexible", "rigid"],
        confidence=0.97,
    ),
    TruthHint(
        id="pf1_vs_pf2",
        question_patterns=[
            r"pf[-\s]?1.*vs.*pf[-\s]?2|pf[-\s]?2.*vs.*pf[-\s]?1",
            r"difference.*pf[-\s]?1.*pf[-\s]?2",
            r"compare.*pf[-\s]?1.*pf[-\s]?2",
        ],
        answer="""PF1 vs PF2 comparison:

**PF1 (Closed Chamber, Heavy-Gauge Vacuum Forming)**
- Single-station, closed chamber machine
- Materials: 2–8mm thick ABS, HDPE, PC, PMMA, HIPS, TPO
- Best for: Automotive interiors, refrigerator liners, truck bedliners, luggage, EV parts, industrial enclosures
- Features: Sag control, pre-blow, zone heating, servo drives, plug assist
- Variants: PF1-C (pneumatic, affordable), PF1-X (all-servo, premium)

**PF2 (Open Frame, Bath Industry)**
- Open frame, basic machine — bath industry ONLY
- Air cylinder drive, manual loading, basic PLC
- NO chamber, NO sag control, NO pre-blow, NO automation
- For: Bathtubs, spa shells, shower trays — NOTHING ELSE
- Material sags freely under gravity into negative (female) cavity molds

Choose PF1 for heavy-gauge industrial forming, PF2 ONLY for bathtubs/spa shells.""",
        category="product",
        keywords=["pf1", "pf2", "vs", "difference", "compare"],
    ),
    
    # -------------------------------------------------------------------------
    # PRODUCTS - OTHER MACHINES
    # -------------------------------------------------------------------------
    TruthHint(
        id="am_series",
        question_patterns=[
            r"what is am[-\s]?[mvy]|am[-\s]?[mvy].*what",
            r"am machine|am series",
            r"am[-\s]?5060|am[-\s]?6060|am[-\s]?7080",
        ],
        answer="""AM Series - Entry-level Vacuum Forming Machines:

The AM Series is designed for THIN GAUGE materials ONLY (maximum 1.5mm standard, up to 1.8mm with duplex chain option).

**Key Models:**
- AM-5060: INR 7,50,000 - 500x600mm forming area
- AM-6060: INR 9,00,000 - 600x600mm forming area  
- AM-7080-CM: INR 28,00,000 - 700x800mm (for car mats)
- AM-5060-P: INR 15,00,000 - with inline hydro-pneumatic press
- AMP-5060: INR 35,00,000 - pressure forming version

**CRITICAL LIMITATION:**
AM Series can ONLY handle sheet thickness ≤1.5mm. For materials thicker than 1.5mm (e.g., 2mm+, 4mm ABS), you MUST use the PF1 Series instead.

**When to use AM vs PF1:**
- AM Series: Sheet thickness ≤1.5mm ONLY, blister packs, thin-wall parts
- PF1 Series: Sheet thickness >1.5mm, heavy-gauge forming, deep draws""",
        category="product",
        keywords=["am", "am-m", "am-v", "am-p", "thin", "5060", "6060"],
    ),
    TruthHint(
        id="machine_selection_thickness",
        question_patterns=[
            r"^which machine.*thick|^what machine.*\d+\s*mm$",
            r"^.*\d+\s*mm.*which machine\??$",
            r"^suggest.*machine.*\d+\s*mm|^recommend.*machine.*\d+\s*mm",
        ],
        answer="""Machine Selection by Material Thickness:

**For material thickness ≤1.5mm (thin gauge):**
→ AM Series (budget-friendly, INR 7.5L - 50L) — up to 1.8mm with duplex chain
→ PF1-R (roll-fed PF1 variant, 0.2-1.5mm) — alternative to AM on PF1 platform

**For material thickness >1.5mm (2mm, 3mm, 4mm, 5mm+, heavy gauge):**
→ PF1-C or PF1-X Series ONLY (INR 33L - 80L depending on size)

**If customer needs BOTH thin AND thick:** Two separate machines required. Cannot combine.

**PF1 Size Selection (for 4x8 feet / 1220x2440mm sheets):**
- PF1-C-2515 (2500x1500mm): INR 70,00,000
- PF1-C-3015 (3000x1500mm): INR 75,00,000
- PF1-C-3020 (3000x2000mm): INR 80,00,000

**PF1 Price List (INR):**
- PF1-C-1008: 33,00,000
- PF1-C-1208: 35,00,000
- PF1-C-1212: 38,00,000
- PF1-C-1510: 40,00,000
- PF1-C-1812: 45,00,000
- PF1-C-2010: 50,00,000
- PF1-C-2015: 60,00,000
- PF1-C-2020: 65,00,000
- PF1-C-2515: 70,00,000
- PF1-C-3015: 75,00,000
- PF1-C-3020: 80,00,000

The model number indicates forming area: PF1-C-XXYY = XX00 x YY00 mm""",
        category="technical",
        keywords=["thick", "mm"],
        confidence=0.90,
    ),
    TruthHint(
        id="fcs_trimming",
        question_patterns=[
            r"what is fcs|fcs.*what",
            r"trimming.*machine",
            r"cutting.*machine",
        ],
        answer="FCS is our CNC trimming system for thermoformed parts. It uses 5-axis routing for precise edge finishing, hole cutting, and trimming. Available in various sizes to match your forming machine. Can be integrated inline with PF1 for continuous production.",
        category="product",
        keywords=["fcs", "trimming", "cutting", "trim"],
    ),
    
    # -------------------------------------------------------------------------
    # TECHNICAL SPECS
    # -------------------------------------------------------------------------
    TruthHint(
        id="materials_supported",
        question_patterns=[
            r"what material|material.*support",
            r"which plastic|plastic.*work",
            r"can.*process|process.*what",
        ],
        answer="""Materials supported by PF1:

**Standard Materials:**
- ABS, PMMA (Acrylic), PC (Polycarbonate)
- PP, PE, PET, PVC
- HDPE, LDPE

**Specialty Materials:**
- TPO (automotive)
- Foam-backed sheets
- Multi-layer films
- Coextruded materials

Sheet thickness: 0.5mm to 12mm (depending on model)
Maximum draw depth: Up to 600mm""",
        category="technical",
        keywords=["material", "plastic", "process", "sheet"],
    ),
    TruthHint(
        id="cycle_time",
        question_patterns=[
            r"cycle time|how fast|speed",
            r"output.*hour|parts.*hour",
            r"production rate",
        ],
        answer="""PF1 cycle times vary by part complexity and material:

**Typical cycle times:**
- Simple shallow parts: 15-30 seconds
- Medium complexity: 30-60 seconds
- Deep draw parts: 60-120 seconds

**Productivity factors:**
- Dual-shuttle systems can halve effective cycle time
- Automation reduces non-forming time by 40%
- Proper tooling optimization is key

A PF1-3020 typically produces 40-120 parts/hour depending on part size and complexity.""",
        category="technical",
        keywords=["cycle", "time", "fast", "speed", "hour", "output"],
    ),
    TruthHint(
        id="lead_time",
        question_patterns=[
            r"lead time|delivery time",
            r"how long.*deliver|when.*ready",
            r"manufacturing time",
        ],
        answer="""Standard lead times:

- **PF1 machines**: 16-24 weeks from order confirmation
- **AM automation**: 12-16 weeks
- **FCS trimming**: 12-16 weeks

Lead time includes:
- Engineering and design approval
- Manufacturing
- Factory testing
- Shipping and installation

Rush orders possible with premium - contact us for urgent requirements.""",
        category="commercial",
        keywords=["lead", "time", "delivery", "when", "ready", "long"],
    ),
    
    # -------------------------------------------------------------------------
    # SUPPORT & SERVICE
    # -------------------------------------------------------------------------
    TruthHint(
        id="warranty",
        question_patterns=[
            r"warranty|guarantee",
            r"support.*after|after.*support",
            r"service.*agreement",
        ],
        answer="""Machinecraft Warranty & Support:

**Standard Warranty:**
- 12 months parts and labor
- Covers manufacturing defects
- Excludes wear parts and consumables

**Extended Support Options:**
- 24-month extended warranty
- Annual maintenance contracts
- Remote diagnostics and support
- On-site service packages

**Support Includes:**
- 24/7 phone/email technical support
- Spare parts availability: 20+ years
- Training at our facility or yours""",
        category="support",
        keywords=["warranty", "guarantee", "support", "service"],
    ),
    TruthHint(
        id="spare_parts",
        question_patterns=[
            r"spare part|replacement part",
            r"consumable|wear part",
        ],
        answer="We maintain spare parts availability for 20+ years after machine delivery. Common wear parts (heaters, seals, valves) ship within 24-48 hours. Critical spares packages available for on-site inventory. Contact parts@machinecraft.in for orders.",
        category="support",
        keywords=["spare", "part", "replacement", "consumable"],
    ),
    TruthHint(
        id="training",
        question_patterns=[
            r"training|how to operate",
            r"learn.*machine|machine.*learn",
            r"operator.*training",
        ],
        answer="""Training programs available:

**Standard Training (included with machine):**
- 3-5 days at your facility
- Operation, safety, basic maintenance
- Process parameter optimization

**Advanced Training:**
- 1 week at Machinecraft facility
- Advanced troubleshooting
- Tooling design principles

**Ongoing Support:**
- Video tutorials library
- Remote training sessions
- Refresher courses available""",
        category="support",
        keywords=["training", "learn", "operate", "operator"],
    ),

    # -------------------------------------------------------------------------
    # IRA SELF-KNOWLEDGE (Architecture, Pipeline, Agents)
    # -------------------------------------------------------------------------
    TruthHint(
        id="ira_architecture",
        question_patterns=[
            r"your.*architecture|architecture.*pipeline",
            r"how.*you.*work|how.*do.*you.*process",
            r"your.*pipeline|what.*pipeline",
            r"explain.*your.*system",
            r"what.*your.*stack",
        ],
        answer="""My architecture has several layers:

1. Telegram/Email gateways receive messages
2. Memory Service loads conversation history and identity
3. Coreference Resolver handles pronouns ("it", "that machine")
4. Entity Extractor identifies machines, materials, dimensions
5. Brain Orchestrator coordinates cognitive functions (memory retrieval, episodic recall, procedural matching, attention filtering)
6. RAG Retrieval searches Qdrant (Voyage AI embeddings) across document, email, and knowledge collections
7. Mem0 provides long-term semantic memory (what I remember about users and facts)
8. generate_answer() builds a system prompt with all context and calls GPT-4o
9. Multi-pass verification checks facts against the machine database
10. Response is delivered back through the channel

Data stores: Qdrant (vector search), Mem0 (AI memory), PostgreSQL (identity/state), knowledge files (JSON/text).""",
        category="self_knowledge",
        keywords=["architecture", "pipeline", "system", "stack", "how do you work", "how you work"],
    ),
    TruthHint(
        id="ira_agents",
        question_patterns=[
            r"(sub.?)?agents?.*names?|names?.*agents?",
            r"how many agents|what agents",
            r"pantheon|athena|clio|calliope|vera|sophia",
            r"who.*works?.*for you|agents.*working",
        ],
        answer="""I operate as a Pantheon of 5 specialist agents:

1. Athena (Chief of Staff) - The strategist and orchestrator. All tasks start and end with her. She plans, delegates, and synthesizes.
2. Clio (Researcher) - The meticulous historian. Retrieves knowledge from Qdrant, Mem0, machine database, and knowledge files.
3. Calliope (Writer) - The eloquent wordsmith. Crafts all communications, emails, quotes, and responses.
4. Vera (Fact-Checker) - The incorruptible auditor. Verifies specs, prices, and claims against the machine database before any response goes out.
5. Sophia (Reflector) - The wise mentor. Learns from every interaction, stores corrections, and improves over time through the nightly dream cycle.

Flow: User -> Athena (plans) -> Clio (researches) -> Calliope (writes) -> Vera (verifies) -> Athena (synthesizes) -> User. Sophia reflects post-interaction.""",
        category="self_knowledge",
        keywords=["agent", "agents", "pantheon", "sub-agent", "subagent", "names", "athena", "clio", "calliope", "vera", "sophia"],
    ),
    TruthHint(
        id="ira_memory_systems",
        question_patterns=[
            r"what.*memory|memory.*system",
            r"mem0|voyage|qdrant",
            r"what.*data.*access|data.*sources",
            r"where.*pull.*answers|where.*get.*data",
            r"what.*know.*from.*ingested",
        ],
        answer="""I have multiple memory and knowledge layers:

1. Mem0 (Long-term AI Memory) - Stores facts about users, preferences, past conversations, and ingested business data (orders, customers, specs). Searchable by semantic similarity.
2. Qdrant (Vector Database) - Stores document embeddings using Voyage AI (voyage-3, 1024 dimensions). Collections include product specs, emails, discovered knowledge, and dream knowledge.
3. Memory Service (Conversation State) - Tracks recent messages, rolling summaries, and conversation mode per channel.
4. Persistent Memory (PostgreSQL) - User memories and entity memories with relevance scoring.
5. Brain State - Episodic memory (past interactions), procedural memory (how-to guides), and metacognition (knowledge gap assessment).
6. Knowledge Files - Hard rules, learned lessons from training simulations, and truth hints for verified answers.

When you ask a question, I search across all these layers in parallel to build the most complete context.""",
        category="self_knowledge",
        keywords=["memory", "mem0", "voyage", "qdrant", "data", "access", "pull", "answers", "ingested", "know"],
    ),
    TruthHint(
        id="ira_identity",
        question_patterns=[
            r"who are you|what are you",
            r"tell me about yourself",
            r"introduce yourself",
            r"what.*your.*role|your.*purpose",
        ],
        answer="""I'm Ira, the Intelligent Revenue Assistant for Machinecraft Technologies. I'm an AI sales assistant that helps the team with:

- Answering questions about thermoforming machines and applications
- Recommending machines based on customer requirements
- Looking up customer history and relationship context
- Drafting professional sales emails and quotations
- Tracking orders, follow-ups, and customer health

I operate as a Pantheon of 5 specialist agents (Athena, Clio, Calliope, Vera, Sophia) coordinated by Athena. I learn from every interaction and improve during nightly dream cycles.

I'm available on Telegram and email (ira@machinecraft.org).""",
        category="self_knowledge",
        keywords=["who are you", "what are you", "yourself", "introduce", "role", "purpose"],
    ),
    TruthHint(
        id="ira_dream_cycle",
        question_patterns=[
            r"dream.*cycle|dream.*report|dream.*mode",
            r"nightly.*dream|dream.*last.*night",
            r"what.*dream|dream.*summary",
            r"sleep.*learn|learn.*overnight",
            r"dream.*journal",
        ],
        answer="""My dream cycle is a nightly self-learning process that runs at 2 AM. It has 7 phases:

1. Phase 0: Process Rushabh's feedback from the day's Telegram chats
2. Phase 1: Document Learning — read PDFs, presentations, and files from data/imports/, extract facts, store in Qdrant and Mem0
3. Phase 2: Episodic Consolidation — find patterns across conversations, turn recurring themes into semantic memories
4. Phase 3: Knowledge Graph — strengthen/weaken connections in Neo4j based on recent interactions
5. Phase 4: Memory Cleanup — decay old unused memories, archive very old ones
6. Phase 5: Neuroscience Processing — spaced repetition, knowledge gap detection, creative insight generation
7. Phase 6: Advanced Processing — memory replay, emotional tagging, self-testing, confidence calibration, dream journal

After the dream, I send a Dream Report to Telegram summarizing what I learned (documents processed, facts learned, patterns found, knowledge gaps identified).

The dream makes me smarter overnight — new facts become searchable, weak memories fade, and patterns from conversations become generalized knowledge.""",
        category="self_knowledge",
        keywords=["dream", "nightly", "sleep", "overnight", "dream cycle", "dream report", "dream journal", "dream mode"],
    ),
]


class TruthHintMatcher:
    """Matches queries to truth hints."""
    
    def __init__(self, hints: List[TruthHint] = None):
        self.hints = hints or TRUTH_HINTS
    
    def find_hint(self, query: str) -> Optional[TruthHint]:
        """Find the best matching hint for a query."""
        best_hint = None
        best_score = 0.0
        
        for hint in self.hints:
            matches, score = hint.matches(query)
            if matches and score > best_score:
                best_hint = hint
                best_score = score
        
        return best_hint
    
    def find_hints(self, query: str, max_hints: int = 3) -> List[Tuple[TruthHint, float]]:
        """Find all matching hints with scores."""
        results = []
        
        for hint in self.hints:
            matches, score = hint.matches(query)
            if matches:
                results.append((hint, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_hints]


def _is_complex_query(query: str) -> bool:
    """Detect multi-part or complex requests that should NOT be short-circuited."""
    if len(query) > 300:
        return True
    if query.count("\n") > 3:
        return True
    complexity_signals = ["draft", "email", "research", "remind me", "who else",
                          "also,", "also ", "and also", "can you also",
                          "give me", "list of", "customers in"]
    if sum(1 for s in complexity_signals if s in query.lower()) >= 2:
        return True
    return False


def get_truth_hint(query: str) -> Optional[TruthHint]:
    """Get the best truth hint for a query. Returns None for complex multi-part requests."""
    if _is_complex_query(query):
        return None
    matcher = TruthHintMatcher()
    return matcher.find_hint(query)


def get_all_hints_for_category(category: str) -> List[TruthHint]:
    """Get all hints in a category."""
    return [h for h in TRUTH_HINTS if h.category == category]


if __name__ == "__main__":
    # Test
    test_queries = [
        "What is PF1?",
        "How much does a PF1 cost?",
        "When was Machinecraft founded?",
        "What materials can you process?",
        "What's the difference between PF1 and PF2?",
        "How long is the warranty?",
        "Do you have spare parts?",
    ]
    
    matcher = TruthHintMatcher()
    
    for q in test_queries:
        hint = matcher.find_hint(q)
        if hint:
            print(f"\n{'='*60}")
            print(f"Q: {q}")
            print(f"Hint: {hint.id} (confidence: {hint.confidence})")
            print(f"A: {hint.answer[:150]}...")
        else:
            print(f"\nQ: {q} -> No hint found")
