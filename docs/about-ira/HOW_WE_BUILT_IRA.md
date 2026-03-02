# How We Built Ira: A Step-by-Step Guide

## The Complete Engineering Journey from Concept to Production

*Last Updated: February 27, 2026*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Building Blocks (What We Used)](#2-the-building-blocks)
3. [Phase 1: Foundation - RAG & Knowledge](#3-phase-1-foundation)
4. [Phase 2: Memory System](#4-phase-2-memory-system)
5. [Phase 3: Brain Orchestrator](#5-phase-3-brain-orchestrator)
6. [Phase 4: Communication Channels](#6-phase-4-channels)
7. [Phase 5: Conversational Intelligence](#7-phase-5-conversational)
8. [Phase 6: Dream Mode & Learning](#8-phase-6-dream-mode)
9. [Key Prompts & System Instructions](#9-key-prompts)
10. [Current Progress Assessment](#10-progress-assessment)
11. [What's Left To Do](#11-whats-left)
12. [Lessons Learned](#12-lessons-learned)

---

## 1. Project Overview

### What We Built
Ira (Intelligent Revenue Assistant) is an AI sales assistant for Machinecraft Technologies, a B2B industrial machinery company selling thermoforming machines globally.

### The Core Problem
Sales teams managing 50+ leads across email and Telegram couldn't remember:
- What was discussed 6 months ago
- Which machines were quoted
- Customer preferences and budget constraints
- Where each lead is in the sales cycle

### The Solution Approach
Build a cognitive system that:
1. **Remembers** - Persistent memory across channels
2. **Retrieves** - RAG over 100+ company documents
3. **Reasons** - Think before responding
4. **Learns** - Improves from corrections and overnight processing

### Timeline
- **Start Date**: Late 2025
- **Current State**: February 2026
- **Total Development Time**: ~4-5 months

---

## 2. The Building Blocks

### Technology Stack

| Component | Technology | Why We Chose It |
|-----------|------------|-----------------|
| **LLM** | OpenAI GPT-4o | Best overall quality, reliable API |
| **Embeddings** | Voyage AI voyage-3 | No rate limits, 1024 dimensions, optimized for retrieval |
| **Vector DB** | Qdrant | Fast, reliable, runs locally via Docker |
| **Memory** | Mem0 | Modern AI memory layer, semantic search |
| **Reranking** | FlashRank | Fast cross-encoder, improves retrieval accuracy |
| **Telegram** | python-telegram-bot | Mature library, webhook support |
| **Email** | Gmail API | OAuth2, reliable delivery |
| **Language** | Python 3.10+ | AI ecosystem, rapid development |

### Key Dependencies

```
# Core AI
openai
voyageai
mem0ai
tiktoken

# Vector & Search
qdrant-client
flashrank

# Documents
pdfplumber
openpyxl
python-docx

# APIs
requests
fastapi
uvicorn

# Telegram
python-telegram-bot
```

### Infrastructure

```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_data:/qdrant/storage

  # PostgreSQL (optional, migrating to Mem0)
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ira_db
      POSTGRES_USER: ira
```

---

## 3. Phase 1: Foundation - RAG & Knowledge

### What We Built First

**Goal**: Get Ira to answer questions using company documents.

### Step 1: Document Ingestion

```python
# scripts/ingest_doc.py - The core logic

def ingest_document(file_path: Path):
    """Ingest a document into the knowledge base."""
    
    # 1. Extract text based on file type
    if file_path.suffix == '.pdf':
        text = extract_pdf(file_path)
    elif file_path.suffix == '.xlsx':
        text = extract_excel(file_path)
    elif file_path.suffix == '.docx':
        text = extract_docx(file_path)
    
    # 2. Chunk the text
    chunks = semantic_chunk(text, max_size=2000, overlap=200)
    
    # 3. Generate embeddings
    embeddings = voyage_client.embed(
        [chunk.text for chunk in chunks],
        model="voyage-3",
        input_type="document"
    )
    
    # 4. Store in Qdrant
    qdrant.upsert(
        collection_name="ira_chunks_v4_voyage",
        points=[
            PointStruct(
                id=uuid4().hex,
                vector=embedding,
                payload={
                    "text": chunk.text,
                    "filename": file_path.name,
                    "page": chunk.page,
                    "doc_type": classify_doc(file_path)
                }
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
    )
```

### Step 2: Retrieval System

```python
# skills/brain/unified_retriever.py

class UnifiedRetriever:
    """Hybrid retrieval: Vector + BM25 + Reranking"""
    
    def retrieve(self, query: str, top_k: int = 10):
        # 1. Embed the query
        query_embedding = self._embed_query(query)
        
        # 2. Vector search
        vector_results = self._vector_search(query_embedding, top_k * 2)
        
        # 3. BM25 keyword search  
        if self.use_hybrid:
            bm25_results = self._bm25_search(query, top_k * 2)
            results = self._merge_results(vector_results, bm25_results)
        else:
            results = vector_results
        
        # 4. Rerank with FlashRank
        if self.use_reranker:
            results = self._rerank(query, results)
        
        return results[:top_k]
```

### Step 3: Answer Generation

The key prompt that drives response quality:

```python
# skills/brain/generate_answer.py

SYSTEM_PROMPT = """You are Ira, the AI sales assistant for Machinecraft Technologies.

## Your Role
- Help sales team with product information, customer context, and communications
- Be accurate - use only information from provided sources
- Be helpful - anticipate what the user needs next
- Be professional but warm - not robotic

## When Answering
1. Ground your response in the retrieved evidence
2. If uncertain, say so and offer to investigate
3. For pricing, always cite the source document
4. For technical specs, include relevant numbers

## Style
- Concise but complete
- Use bullet points for lists
- End with a helpful follow-up when appropriate
"""
```

### What We Learned

| Challenge | Solution |
|-----------|----------|
| PDFs with tables extracted poorly | Used pdfplumber with table detection |
| Excel sheets needed structure | Preserved row/column context in chunks |
| Too many irrelevant results | Added FlashRank reranking |
| Duplicate documents in index | Content hashing + deduplication |

### Files Created in This Phase

```
skills/brain/
├── unified_retriever.py      # Main retrieval
├── qdrant_retriever.py       # Vector search
├── semantic_chunker.py       # Document chunking
├── generate_answer.py        # Response generation
├── reindex_docs.py           # Document ingestion
└── embedding_cache.py        # Cache for embeddings
```

---

## 4. Phase 2: Memory System

### What We Built

**Goal**: Make Ira remember conversations and facts about people/entities.

### The Memory Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 MEMORY LAYERS                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SEMANTIC MEMORY (Facts)                               │
│  "John from ABC Corp prefers email over phone"         │
│  "PF1-3020 was quoted at $45,000 last month"          │
│  → Stored in: Mem0 (cloud) + Qdrant (vectors)         │
│                                                         │
│  EPISODIC MEMORY (Events)                              │
│  "Feb 15: Discussed PF1 machines, customer excited"    │
│  "Feb 20: Sent quote, customer asked about delivery"   │
│  → Stored in: PostgreSQL (structured) + JSON backup    │
│                                                         │
│  PROCEDURAL MEMORY (How-to)                            │
│  Procedure: "generate_quote"                           │
│  Triggers: ["quote", "pricing", "offer"]              │
│  Steps: [check_inventory → calculate → format]        │
│  → Stored in: JSON + Mem0                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Step 1: Persistent Memory Service

```python
# skills/memory/persistent_memory.py

class PersistentMemory:
    """Store and retrieve user memories."""
    
    def store_memory(
        self,
        identity_id: str,
        memory_text: str,
        memory_type: str = "fact",
        confidence: float = 0.8
    ):
        """Store a memory about a user or entity."""
        
        # Generate embedding for search
        embedding = self._embed(memory_text)
        
        # Store in Mem0 (primary)
        self.mem0.add(
            messages=[{"role": "user", "content": memory_text}],
            user_id=identity_id,
            metadata={"type": memory_type, "confidence": confidence}
        )
        
        # Store in Qdrant (for hybrid search)
        self.qdrant.upsert(
            collection_name="ira_user_memories_v2",
            points=[PointStruct(id=..., vector=embedding, payload={...})]
        )
    
    def retrieve_for_prompt(
        self,
        identity_id: str,
        query: str,
        limit: int = 5
    ) -> List[Memory]:
        """Get relevant memories for the current query."""
        
        # Search Mem0 by user_id + semantic similarity
        results = self.mem0.search(
            query=query,
            user_id=identity_id,
            limit=limit
        )
        
        return [Memory(text=r.memory, confidence=r.score) for r in results]
```

### Step 2: Episodic Memory

```python
# skills/memory/episodic_memory.py

class EpisodicMemory:
    """Track events over time."""
    
    def record_episode(
        self,
        identity_id: str,
        channel: str,
        summary: str,
        episode_type: EpisodeType,
        key_topics: List[str],
        entities_mentioned: List[str],
        user_intent: str
    ):
        """Record a conversation episode."""
        
        # Generate embedding for the episode
        episode_text = f"{summary}. Topics: {', '.join(key_topics)}"
        embedding = self._embed(episode_text)
        
        # Store with temporal metadata
        self.store.insert({
            "identity_id": identity_id,
            "channel": channel,
            "summary": summary,
            "episode_type": episode_type.value,
            "topics": key_topics,
            "entities": entities_mentioned,
            "timestamp": datetime.now(),
            "embedding": embedding
        })
    
    def retrieve_for_prompt(
        self,
        identity_id: str,
        query: str,
        limit: int = 3
    ) -> str:
        """Get relevant past episodes formatted for prompt."""
        
        episodes = self._search(identity_id, query, limit)
        
        if not episodes:
            return ""
        
        formatted = ["[Past Interactions]"]
        for ep in episodes:
            time_ago = self._humanize_time(ep.timestamp)
            formatted.append(f"• {time_ago}: {ep.summary}")
        
        return "\n".join(formatted)
```

### Step 3: Memory Trigger

The key insight: **Don't retrieve memory for every message**.

```python
# skills/memory/memory_trigger.py

def should_retrieve_memory(
    message: str,
    identity_id: str,
    context: Dict
) -> Tuple[bool, Dict]:
    """Decide whether to retrieve memories."""
    
    # Skip for simple messages
    if is_greeting(message) or is_thanks(message):
        return False, {}
    
    # Skip if user says "forget" or "ignore"
    if contains_forget_signal(message):
        return False, {}
    
    # Retrieve for personal/business questions
    if needs_context(message):
        return True, {
            "user_memory_limit": 5,
            "entity_memory_limit": 5,
            "min_relevance": 0.3
        }
    
    # Retrieve if references past context
    if has_past_reference(message):  # "that machine", "last time"
        return True, {"user_memory_limit": 7}
    
    return True, {"user_memory_limit": 3}
```

### What We Learned

| Challenge | Solution |
|-----------|----------|
| Memory retrieval too slow | Added memory trigger to skip when unnecessary |
| Too many irrelevant memories | Increased min_relevance threshold |
| Memories getting stale | Implemented decay function |
| Memory conflicts | Added conflict detection + human review queue |

### Files Created in This Phase

```
skills/memory/
├── persistent_memory.py       # Semantic memory
├── episodic_memory.py         # Event memory
├── procedural_memory.py       # Procedure memory
├── memory_trigger.py          # When to retrieve
├── memory_weaver.py           # Combine memories
├── memory_reasoning.py        # Think with memories
├── unified_mem0.py            # Mem0 integration
├── mem0_storage.py            # Storage abstraction
└── memory_controller.py       # Route memory updates
```

---

## 5. Phase 3: Brain Orchestrator

### What We Built

**Goal**: Coordinate all cognitive processes into a coherent pipeline.

### The 10-Phase Pipeline

```python
# skills/memory/brain_orchestrator.py

class BrainOrchestrator:
    """Unified cognitive processing pipeline."""
    
    def process(self, message: str, identity_id: str, context: Dict) -> BrainState:
        """Process message through complete pipeline."""
        
        state = BrainState(message=message, identity_id=identity_id)
        
        # Phase 1: Should we retrieve memories?
        self._phase_trigger(state)
        
        # Phase 2: Retrieve semantic memories
        if state.should_retrieve:
            self._phase_retrieval(state)
        
        # Phase 3: Retrieve episodic memories
        self._phase_episodic(state)
        
        # Phase 4: Match procedural memory
        self._phase_procedural(state)
        
        # Phase 5: Weave memories into guidance
        self._phase_weaving(state)
        
        # Phase 6: Reason with memories
        self._phase_reasoning(state)
        
        # Phase 7: Assess knowledge confidence
        self._phase_metacognition(state)
        
        # Phase 8: Detect conflicts
        self._phase_conflicts(state)
        
        # Phase 9: Attention filtering (Miller's Law)
        self._phase_attention(state)
        
        return state
```

### Key Innovation: BrainState

The coordination object that flows through all phases:

```python
@dataclass
class BrainState:
    """Shared state across all brain modules."""
    
    # Input
    message: str = ""
    identity_id: Optional[str] = None
    channel: str = "telegram"
    
    # Processing state
    phase: ProcessingPhase = ProcessingPhase.INIT
    should_retrieve: bool = True
    
    # Retrieved context
    user_memories: List[Any] = field(default_factory=list)
    entity_memories: List[Any] = field(default_factory=list)
    episodic_context: str = ""
    
    # Processed guidance
    procedure_guidance: str = ""
    memory_guidance: Dict = field(default_factory=dict)
    reasoning_context: str = ""
    metacognitive_guidance: str = ""
    
    # Output
    conflicts_detected: List[Dict] = field(default_factory=list)
    final_context: Dict = field(default_factory=dict)
```

### Meta-Cognition: Knowing What You Know

```python
# skills/memory/metacognition.py

class KnowledgeState(Enum):
    KNOW_VERIFIED = "know_verified"    # Have proof from documents
    THINK_KNOW = "think_know"          # Pretty sure but no source
    UNCERTAIN = "uncertain"            # Should say "I'm not sure"
    DONT_KNOW = "dont_know"            # Definitely don't know

def assess_knowledge(
    query: str,
    user_memories: List,
    entity_memories: List,
    rag_chunks: List
) -> KnowledgeAssessment:
    """Assess confidence in our knowledge."""
    
    # High confidence: multiple corroborating sources
    if len(rag_chunks) >= 2 and rag_chunks[0].score > 0.8:
        return KnowledgeAssessment(
            state=KnowledgeState.KNOW_VERIFIED,
            confidence=0.9,
            sources=[c.filename for c in rag_chunks[:3]]
        )
    
    # Medium confidence: some relevant info
    if rag_chunks and rag_chunks[0].score > 0.5:
        return KnowledgeAssessment(
            state=KnowledgeState.THINK_KNOW,
            confidence=0.6,
            gaps=["May need verification"]
        )
    
    # Low confidence
    return KnowledgeAssessment(
        state=KnowledgeState.UNCERTAIN,
        confidence=0.3,
        gaps=["No direct sources found"]
    )
```

### Attention Filtering (Miller's Law)

Can't stuff everything into the prompt. Must prioritize:

```python
# Attention Manager

class AttentionManager:
    """Working memory limits (7±2 items)."""
    
    MAX_ITEMS = 7
    
    PRIORITY_WEIGHTS = {
        "procedure_guidance": 0.95,      # How to respond
        "conflicts": 0.90,               # Must address
        "metacognitive_guidance": 0.85,  # Calibrate confidence
        "reasoning_context": 0.80,       # Inner thoughts
        "episodic_context": 0.75,        # Past events
        "memory_guidance": 0.70,         # Weaved memories
        "rag_chunks": 0.50,              # General knowledge
    }
    
    def prioritize(self, items: Dict) -> Dict:
        """Filter to top 7 items by priority."""
        scored = []
        for key, value in items.items():
            if not value:
                continue
            score = self.PRIORITY_WEIGHTS.get(key, 0.3)
            scored.append((key, value, score))
        
        scored.sort(key=lambda x: x[2], reverse=True)
        return {k: v for k, v, _ in scored[:self.MAX_ITEMS]}
```

---

## 6. Phase 4: Communication Channels

### Telegram Gateway

The primary interface (~5,000 lines):

```python
# skills/telegram_channel/telegram_gateway.py

class TelegramGateway:
    """Main interface for Telegram communication."""
    
    async def handle_message(self, update, context):
        """Process incoming Telegram message."""
        
        message = update.message.text
        chat_id = str(update.message.chat_id)
        
        # 1. Check authorization
        if chat_id != EXPECTED_CHAT_ID:
            return
        
        # 2. Parse commands
        if message.startswith('/'):
            return await self._handle_command(message, chat_id)
        
        # 3. Resolve identity
        identity_id = self._resolve_identity(chat_id)
        
        # 4. Get conversation context
        context_pack = self.memory.get_context_pack("telegram", chat_id, message)
        
        # 5. Resolve coreferences ("it" → "PF1-3020")
        resolved = self.coreference.resolve(message, context_pack)
        
        # 6. Process through brain
        brain_state = self.brain.process(
            message=resolved.resolved,
            identity_id=identity_id,
            context=context_pack,
            channel="telegram"
        )
        
        # 7. Retrieve RAG context
        rag_chunks = self.retriever.retrieve(resolved.resolved, top_k=8)
        
        # 8. Generate response
        response = generate_answer(
            intent=resolved.resolved,
            context_pack={
                **brain_state.to_context_pack(),
                "rag_chunks": rag_chunks
            },
            channel="telegram"
        )
        
        # 9. Record episode
        self._record_episode(identity_id, message, response)
        
        # 10. Send response
        await self._send_message(chat_id, response.text)
```

### Email Handler

Integration with Gmail API:

```python
# skills/email_channel/email_handler.py

class EmailHandler:
    """Process incoming emails."""
    
    def process_email(self, email: IncomingEmail):
        """Process an email using the brain orchestrator."""
        
        # 1. Preprocess email (clean signatures, extract thread)
        preprocessed = self.preprocessor.preprocess(email)
        
        # 2. Resolve sender identity
        identity_id = self._resolve_email_identity(email.from_email)
        
        # 3. Process through brain (with email context)
        brain_state = self.brain.process(
            message=preprocessed.clean_body,
            identity_id=identity_id,
            context={
                "thread_id": email.thread_id,
                "subject": email.subject,
                "from_email": email.from_email,
                "is_reply": preprocessed.is_reply,
                "thread_history": preprocessed.thread_history
            },
            channel="email"
        )
        
        # 4. Generate response
        response = generate_answer(
            intent=preprocessed.clean_body,
            context_pack=brain_state.to_context_pack(),
            channel="email"
        )
        
        # 5. Post-process for email format
        formatted = self.postprocessor.format_email(
            response.text,
            recipient_name=email.from_name
        )
        
        return formatted
```

### Unified Identity

One person across all channels:

```python
# skills/identity/unified_identity.py

class UnifiedIdentityService:
    """Resolve identity across channels."""
    
    def resolve(
        self,
        channel: str,
        identifier: str,
        create_if_missing: bool = True
    ) -> str:
        """Resolve to canonical identity ID."""
        
        # Check existing mappings
        mapping = self.db.query(
            "SELECT canonical_id FROM identity_mappings WHERE channel = ? AND identifier = ?",
            (channel, identifier)
        )
        
        if mapping:
            return mapping.canonical_id
        
        # Check if this identifier is linked
        linked = self._find_linked_identity(identifier)
        if linked:
            # Add mapping for this channel
            self._add_mapping(channel, identifier, linked)
            return linked
        
        # Create new identity
        if create_if_missing:
            new_id = f"id_{uuid4().hex[:12]}"
            self._create_identity(new_id, channel, identifier)
            return new_id
        
        return identifier
    
    def link(
        self,
        channel1: str, id1: str,
        channel2: str, id2: str,
        confidence: float = 0.9
    ):
        """Link two identifiers as same person."""
        
        canonical1 = self.resolve(channel1, id1)
        canonical2 = self.resolve(channel2, id2)
        
        if canonical1 != canonical2:
            # Merge identities (keep older one)
            self._merge_identities(canonical1, canonical2)
```

---

## 7. Phase 5: Conversational Intelligence

### Coreference Resolution

Understanding "it", "that machine", etc.:

```python
# skills/conversation/coreference.py

class CoreferenceResolver:
    """Resolve pronouns and references."""
    
    MACHINE_REFS = [
        r'\b(it|this machine|that machine|the machine|this one|that one)\b',
    ]
    
    def resolve(self, text: str, context: Dict) -> ResolvedQuery:
        """Resolve coreferences in user text."""
        
        resolved = text
        substitutions = []
        
        # Get last mentioned machine from context
        machines = context.get("key_entities", {}).get("machines", [])
        
        if machines:
            last_machine = machines[-1]
            
            for pattern in self.MACHINE_REFS:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if self._is_machine_context(text, match):
                        resolved = re.sub(
                            rf'\b{re.escape(match)}\b',
                            last_machine,
                            resolved,
                            count=1,
                            flags=re.IGNORECASE
                        )
                        substitutions.append((match, last_machine))
        
        return ResolvedQuery(
            original=text,
            resolved=resolved,
            substitutions=substitutions
        )
```

### Entity Extraction

Domain-specific entity detection:

```python
# skills/conversation/entity_extractor.py

class EntityExtractor:
    """Extract Machinecraft-specific entities."""
    
    MACHINE_PATTERNS = [
        r'\b(PF1-[A-Z]-\d{3,4}(-\d{3,4})?)\b',  # PF1-C-3020
        r'\b(ATF-\d{3,4})\b',                     # ATF-1218
        r'\b(AM-[VP]-\d{4})\b',                   # AM-P-5060
    ]
    
    MATERIAL_PATTERNS = [
        r'\b(ABS|HDPE|PP|PC|PMMA|PETG|PVC)\b',
    ]
    
    DIMENSION_PATTERNS = [
        r'(\d+)\s*(?:mm|cm|m|inch|ft)\s*[x×]\s*(\d+)',
    ]
    
    def extract(self, text: str) -> ExtractedEntities:
        """Extract all entities from text."""
        
        entities = ExtractedEntities()
        
        for pattern in self.MACHINE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.machines.extend([m[0] if isinstance(m, tuple) else m for m in matches])
        
        for pattern in self.MATERIAL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.materials.extend(matches)
        
        for pattern in self.DIMENSION_PATTERNS:
            matches = re.findall(pattern, text)
            entities.dimensions.extend([f"{m[0]}x{m[1]}" for m in matches])
        
        return entities
```

### Goal-Directed Dialog

Making Ira pursue goals, not just answer questions:

```python
# skills/conversation/goals.py

class GoalType(Enum):
    QUALIFY_LEAD = "qualify_lead"
    GENERATE_QUOTE = "generate_quote"
    HANDLE_OBJECTION = "handle_objection"
    SCHEDULE_MEETING = "schedule_meeting"

@dataclass
class Slot:
    name: str
    question: str
    value: Optional[str] = None
    status: SlotStatus = SlotStatus.UNKNOWN

# Goal templates with required slots
GOAL_TEMPLATES = {
    GoalType.GENERATE_QUOTE: {
        "machine_model": Slot("machine_model", "Which machine model are you interested in?"),
        "quantity": Slot("quantity", "How many machines do you need?"),
        "delivery_location": Slot("delivery_location", "Where would this be delivered?"),
        "timeline": Slot("timeline", "When do you need delivery?"),
    }
}
```

---

## 8. Phase 6: Dream Mode & Learning

### How Dream Mode Works

Every night, Ira "sleeps" and learns:

```python
# skills/brain/dream_mode.py

class DreamMode:
    """Nightly learning from documents."""
    
    def dream(self, force_all: bool = False):
        """Run the dream cycle."""
        
        print("💤 Entering Dream Mode...")
        
        # Phase 1: Find new/changed documents
        docs = self._find_documents(force_all)
        print(f"Found {len(docs)} documents to process")
        
        # Phase 2: Extract knowledge
        all_knowledge = []
        for path, priority in docs:
            content = self._extract_content(path)
            knowledge = self._extract_knowledge(content, path.name, priority)
            all_knowledge.append(knowledge)
            
            # Store in BOTH Qdrant AND Mem0
            self._store_knowledge_unified(knowledge)
        
        # Phase 3: Generate cross-document insights
        insights = self._generate_cross_document_insights(all_knowledge)
        
        # Phase 4: Consolidate knowledge graph
        self._consolidate_knowledge_graph()
        
        # Phase 5: Check for price conflicts
        self._check_price_conflicts()
        
        print("🌅 Dream Complete - Woke up smarter!")
```

### Knowledge Extraction Prompt

```python
EXTRACTION_PROMPT = """Analyze this document for Ira (AI sales assistant for Machinecraft thermoforming machines).

Document: {filename}
Content:
{content}

Extract:
1. FACTS: Specific, concrete information (numbers, specs, names, dates)
2. TOPICS: Main topics covered
3. KEY_TERMS: Important terms with definitions
4. RELATIONSHIPS: How concepts connect ("X is used for Y", "X requires Y")
5. INSIGHTS: Non-obvious conclusions
6. QUESTIONS: What this document doesn't answer

Return JSON:
{
  "facts": ["fact 1", "fact 2", ...],
  "topics": ["topic1", "topic2", ...],
  "key_terms": {"term": "definition", ...},
  "relationships": [{"subject": "...", "relation": "...", "object": "..."}],
  "insights": ["insight 1", ...],
  "questions": ["question 1", ...]
}"""
```

### Feedback Learning

Learning from corrections:

```python
# skills/brain/feedback_learner.py

class FeedbackLearner:
    """Learn from user corrections."""
    
    def learn_from_correction(
        self,
        original_response: str,
        correction: str,
        query: str
    ):
        """Process a correction and learn from it."""
        
        # 1. Identify what was wrong
        diff = self._analyze_correction(original_response, correction)
        
        # 2. Store as learned fact
        if diff.fact_correction:
            self.memory.store_memory(
                identity_id="system_ira",
                memory_text=f"CORRECTION: {diff.fact_correction}",
                memory_type="correction",
                confidence=0.95
            )
        
        # 3. Update procedural memory if workflow issue
        if diff.procedure_issue:
            self.procedural.update_procedure(
                procedure_id=diff.procedure_id,
                correction=diff.procedure_issue
            )
        
        # 4. Record for calibration
        self.calibration.record_outcome(
            query_type=self._categorize_query(query),
            predicted_confidence=0.8,
            was_correct=False
        )
```

---

## 9. Key Prompts & System Instructions

### Main System Prompt

```python
IRA_SYSTEM_PROMPT = """You are Ira, the AI sales assistant for Machinecraft Technologies.

## About Machinecraft
Machinecraft builds thermoforming machines - industrial equipment that heats plastic sheets and forms them into shapes using vacuum pressure. Applications include automotive interiors, packaging, signage, and medical equipment.

## Your Capabilities
- Deep knowledge of Machinecraft products (PF1 series, ATF series, AM series)
- Access to company documents, price lists, and specifications
- Memory of past conversations with each customer
- Ability to draft emails, quotes, and technical responses

## Communication Style
- Be helpful, professional, and concise
- Use a warm but efficient tone
- Include specific data when available (prices, specs, timelines)
- When uncertain, acknowledge it rather than guess
- End responses with a helpful follow-up when appropriate

## Constraints
- Only quote prices from verified source documents
- Never make up specifications
- If you don't know something, say so and offer to investigate
- For internal users, be more casual; for external, more formal
"""
```

### Email Generation Prompt

```python
EMAIL_PROMPT = """Generate a professional email response.

Context:
- Sender: {sender_name} from {company}
- Subject: {subject}
- Their message: {message}

Relevant information:
{context}

Guidelines:
1. Start with appropriate greeting (use first name for returning contacts)
2. Address their query directly
3. Include specific data (prices, specs) when available
4. Be concise but complete
5. End with clear next steps or helpful offer
6. Sign as "Ira" (AI assistant) or "Rushabh" depending on context

Write the email body (no subject line needed):
"""
```

### Memory Weaving Prompt

```python
MEMORY_WEAVER_PROMPT = """Given these memories about the user and their context, generate guidance for responding.

User Memories:
{user_memories}

Entity Memories (machines, companies):
{entity_memories}

Current Query: {query}

Generate brief guidance on:
1. What to remember/reference from past interactions
2. Personal preferences to respect
3. Context that should influence the response
4. Any warnings or things to avoid

Keep it concise - this goes into the response prompt.
"""
```

---

## 10. Current Progress Assessment

### Overall Completion: ~75%

| Component | Status | Completion | Notes |
|-----------|--------|------------|-------|
| RAG/Retrieval | ✅ Complete | 95% | Hybrid search + reranking working |
| Document Ingestion | ✅ Complete | 90% | PDF, Excel, DOCX supported |
| Memory System | ✅ Complete | 85% | Mem0 + PostgreSQL hybrid |
| Brain Orchestrator | ✅ Complete | 90% | All 10 phases implemented |
| Telegram Gateway | ✅ Complete | 90% | Full functionality |
| Email Handler | ✅ Complete | 85% | Integrated with brain |
| Unified Identity | ✅ Complete | 80% | Cross-channel linking works |
| Coreference Resolution | ✅ Complete | 85% | Domain patterns + LLM fallback |
| Entity Extraction | ✅ Complete | 85% | Machinecraft-specific |
| Dream Mode | ✅ Complete | 85% | Nightly learning active |
| Goal-Directed Dialog | ✅ Complete | 80% | Slot filling implemented |
| Email Polish | ⚠️ Partial | 60% | Inconsistently applied |
| Proactive Outreach | ⚠️ Partial | 50% | Framework built, needs tuning |
| Config Unification | ✅ Complete | 90% | Single source of truth |
| Testing | ⚠️ Partial | 40% | Needs more coverage |
| Production Hardening | ⚠️ Partial | 50% | Monitoring, alerting needed |

### What's Working Well

1. **RAG Retrieval** - Fast, accurate, hybrid search with reranking
2. **Memory Persistence** - Conversations remembered across sessions
3. **Brain Pipeline** - Coherent cognitive processing
4. **Telegram Interface** - Reliable, feature-rich
5. **Dream Mode** - Learning new documents overnight
6. **Identity Resolution** - Same person across channels

### What Needs Work

1. **Email Tone** - Sometimes too robotic, polish inconsistent
2. **Proactive Questioning** - Doesn't ask follow-ups enough
3. **Test Coverage** - Only ~40% of functionality tested
4. **Monitoring** - No alerting for errors
5. **Price Conflicts** - Detection works, resolution manual

---

## 11. What's Left To Do

### Priority 1: Production Critical (Blocking)

| Task | Effort | Impact |
|------|--------|--------|
| **Email polish consistency** | 4-8 hrs | HIGH - Emails sound robotic |
| **Error monitoring/alerting** | 8-16 hrs | HIGH - Silent failures |
| **Rate limit handling** | 4 hrs | HIGH - API failures |
| **Startup health check** | 2 hrs | MEDIUM - Catch config issues |

### Priority 2: Quality Improvement

| Task | Effort | Impact |
|------|--------|--------|
| **Increase test coverage to 70%** | 16-24 hrs | HIGH - Catch regressions |
| **Proactive questioning tuning** | 8 hrs | MEDIUM - Better conversations |
| **Memory relevance tuning** | 4-8 hrs | MEDIUM - Less noise |
| **Response time optimization** | 8 hrs | MEDIUM - Faster UX |

### Priority 3: Feature Enhancement

| Task | Effort | Impact |
|------|--------|--------|
| **Quote generation automation** | 16 hrs | HIGH - Sales efficiency |
| **Customer enrichment pipeline** | 8 hrs | MEDIUM - Better context |
| **Market research integration** | 8 hrs | LOW - Competitive intel |
| **Voice message support** | 16 hrs | LOW - New channel |

### Priority 4: Technical Debt

| Task | Effort | Impact |
|------|--------|--------|
| **PostgreSQL → Mem0 migration** | 8 hrs | MEDIUM - Simplify stack |
| **Collection name cleanup** | 2 hrs | LOW - Consistency |
| **Dead code removal** | 4 hrs | LOW - Maintainability |
| **Documentation updates** | 8 hrs | LOW - Developer experience |

### Estimated Total Remaining Work

| Category | Hours | Weeks (1 engineer) |
|----------|-------|-------------------|
| Production Critical | 18-30 | 0.5-1 |
| Quality Improvement | 36-48 | 1-1.5 |
| Feature Enhancement | 48+ | 1.5+ |
| Technical Debt | 22 | 0.5 |
| **Total to Production-Grade** | **60-80 hrs** | **1.5-2 weeks** |

### Remaining Work Percentage

```
┌────────────────────────────────────────────────────────────┐
│                   PROGRESS TO PRODUCTION                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ████████████████████████████████████░░░░░░░░  75%        │
│                                                            │
│  Done:                                                     │
│  ✅ Core RAG system                                        │
│  ✅ Memory architecture                                    │
│  ✅ Brain orchestrator                                     │
│  ✅ Telegram integration                                   │
│  ✅ Email integration                                      │
│  ✅ Dream mode                                             │
│  ✅ Conversational intelligence                            │
│                                                            │
│  Remaining (25%):                                          │
│  ⬜ Production hardening (monitoring, alerting)            │
│  ⬜ Test coverage (40% → 70%)                              │
│  ⬜ Email polish consistency                               │
│  ⬜ Proactive behavior tuning                              │
│  ⬜ Quote automation                                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 12. Lessons Learned

### What Worked

1. **Modular skill architecture** - Easy to add/modify capabilities
2. **Centralized config** - Single source of truth prevents drift
3. **Graceful degradation** - System works even when components fail
4. **Hybrid memory** - Mem0 + local backup = reliability
5. **Dream mode concept** - Nightly learning is powerful

### What We'd Do Differently

1. **Start with tests** - Retrofitting tests is painful
2. **Config from day 1** - Unifying config after the fact was tedious
3. **Simpler memory architecture** - PostgreSQL + Mem0 is redundant
4. **Email polish earlier** - Tone issues persist due to late addition
5. **More prompt engineering upfront** - System prompts evolved too much

### Key Technical Decisions

| Decision | Reasoning | Would Do Again? |
|----------|-----------|-----------------|
| Voyage over OpenAI embeddings | No rate limits, retrieval-optimized | ✅ Yes |
| Qdrant over Pinecone | Runs locally, fast, cheap | ✅ Yes |
| Mem0 for memory | Modern, semantic, managed | ✅ Yes |
| GPT-4o over Claude | Better function calling, reliable | ⚠️ Maybe try Claude |
| Python over TypeScript | AI ecosystem, rapid dev | ✅ Yes |
| Telegram as primary | Fast iteration, user preference | ✅ Yes |

### Performance Characteristics

| Metric | Current | Target |
|--------|---------|--------|
| Response time (Telegram) | 1.5-3s | <2s |
| Response time (Email) | 3-5s | <4s |
| RAG retrieval | 200-400ms | <300ms |
| Memory retrieval | 100-200ms | <150ms |
| Dream mode (full run) | 10-30min | <15min |

---

## Appendix: File Structure Reference

```
Ira/
├── openclaw/agents/ira/
│   ├── agent.py                    # Main agent coordinator
│   ├── config.py                   # Single source of truth
│   ├── core/
│   │   └── state.py               # State management
│   │
│   └── skills/
│       ├── brain/                  # 40+ files
│       │   ├── generate_answer.py
│       │   ├── unified_retriever.py
│       │   ├── qdrant_retriever.py
│       │   ├── dream_mode.py
│       │   ├── knowledge_graph.py
│       │   ├── pricing_learner.py
│       │   ├── fact_checker.py
│       │   └── ...
│       │
│       ├── memory/                 # 20+ files
│       │   ├── brain_orchestrator.py
│       │   ├── persistent_memory.py
│       │   ├── episodic_memory.py
│       │   ├── procedural_memory.py
│       │   ├── unified_mem0.py
│       │   └── ...
│       │
│       ├── conversation/           # 15+ files
│       │   ├── coreference.py
│       │   ├── entity_extractor.py
│       │   ├── emotional_intelligence.py
│       │   ├── goals.py
│       │   └── ...
│       │
│       ├── telegram_channel/
│       │   └── telegram_gateway.py
│       │
│       ├── email_channel/
│       │   ├── email_handler.py
│       │   ├── email_preprocessor.py
│       │   └── email_postprocessor.py
│       │
│       └── identity/
│           └── unified_identity.py
│
├── scripts/                        # 30+ utility scripts
├── data/                           # Documents, knowledge, exports
├── docs/                           # 15+ documentation files
└── tests/                          # 25+ test files
```

---

## Quick Reference: Key Commands

```bash
# Start Ira
python orchestrator.py

# Telegram only
python orchestrator.py --telegram

# Run dream mode
python scripts/run_dream_mode.py

# Reindex documents
python openclaw/agents/ira/skills/brain/reindex_docs.py

# Check health
python openclaw/agents/ira/skills/brain/knowledge_health.py --check

# Run tests
pytest tests/
```

---

*Document created: February 27, 2026*
*For questions: rushabh@machinecraft.org*
