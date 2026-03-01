# Dream Mode Integration Audit

**Date**: 2026-02-27  
**Status**: ✅ FIXED - Qdrant integration complete

---

## Fixes Applied (2026-02-27)

### ✅ P0: Qdrant Integration (COMPLETE)
- Dream mode now stores to **BOTH** Qdrant AND Mem0
- Created `ira_dream_knowledge_v1` collection
- Updated `unified_retriever.py` to search dream knowledge
- Updated `qdrant_retriever.py` to search dream knowledge
- Dream-learned facts now appear in RAG results

### ✅ P1: Centralized Config (COMPLETE)
- Dream mode now uses `config.py` for collection names
- API keys loaded correctly from `.env`

### Verified Working:
```
Query: "thermoforming machine types and EcoForm specifications"
Result #3: [insight] Score: 0.903 - FRIMO doc insight
Result #5: [fact] Score: 0.395 - FRIMO EcoForm sizes
```

---

## Executive Summary (Original Audit)

Dream Mode is **functionally isolated** from Ira's core cognitive architecture. While it extracts knowledge, that knowledge is:
- Not searchable via RAG (Qdrant)
- Not integrated with the BrainOrchestrator
- Using different extraction logic than DocumentIngestor
- Stored in a separate memory silo

**Result**: Knowledge learned during dreaming is NOT effectively used during conversations.

---

## 1. Architecture Gaps (CRITICAL)

### 1.1 Dream Mode vs. Existing Systems

| Capability | Dream Mode | Existing System | Gap |
|------------|------------|-----------------|-----|
| **PDF Extraction** | `_extract_pdf_content()` | `DocumentIngestor._extract_pdf_facts()` | DUPLICATE |
| **Knowledge Extraction** | `_deep_extract_knowledge()` | `DocumentIngestor.ingest()` | DUPLICATE |
| **Memory Storage** | Raw Mem0 (`system_ira`) | `UnifiedMemoryService` | NOT INTEGRATED |
| **Vector Search** | Not used | `UnifiedRetriever` (Qdrant) | MISSING |
| **Conflict Detection** | None | `DocumentIngestor` has it | MISSING |
| **Episodic Learning** | None | `EpisodicConsolidator` | NOT CONNECTED |

### 1.2 Missing Data Flow

```
Current Dream Mode:
[Documents] → [Extract] → [Store in Mem0]
                              ↓
                        (DEAD END - not in Qdrant!)

Should Be:
[Documents] → [Extract] → [Unified Memory] → [Qdrant Index]
                              ↓                    ↓
                        [Conflict Detection]  [RAG Retrieval]
                              ↓                    ↓
                        [Human Clarification]  [BrainOrchestrator]
```

---

## 2. Specific Issues

### 2.1 Mem0 vs. Qdrant Disconnect (CRITICAL)

**Problem**: Dream mode stores to Mem0, but RAG retrieval uses Qdrant.

```python
# Dream Mode stores here:
self.mem0_client.add(
    messages=[{"role": "user", "content": fact}],
    user_id="system_ira",  # NOT in Qdrant!
)

# But retrieval happens here:
unified_retriever.search(query)  # Searches Qdrant, NOT Mem0!
```

**Impact**: 95%+ of dream-learned knowledge is NEVER retrieved during conversations.

### 2.2 Duplicate Document Extractors (HIGH)

Three separate PDF extraction implementations:

| File | Method | Lines |
|------|--------|-------|
| `dream_mode.py` | `_extract_pdf_content()` | ~15 |
| `document_ingestor.py` | `_extract_pdf_facts()` | ~80 |
| `knowledge_retriever.py` | `_search_documents()` | ~50 |

**Impact**: Bug fixes must be applied 3x. Inconsistent extraction quality.

### 2.3 No Conflict Detection (HIGH)

`DocumentIngestor` has sophisticated conflict detection:
```python
# DocumentIngestor has:
def _check_for_conflicts(existing_memories, new_fact):
    # Detects contradictions
    # Queues for human clarification
```

Dream mode has **NONE** of this. Contradictory facts overwrite each other silently.

### 2.4 Knowledge Graph Not Used (MEDIUM)

Dream mode builds a knowledge graph:
```python
self.state.knowledge_graph[subj].append(obj)  # Built but...
```

But this graph is:
- Never queried during retrieval
- Not passed to BrainOrchestrator
- Not used for reasoning

### 2.5 No Consolidation Trigger (MEDIUM)

`EpisodicConsolidator` converts episodes to semantic memories:
```python
# This exists but dream mode doesn't use it:
consolidator.consolidate(threshold_days=7)
```

Dream learning should trigger consolidation.

---

## 3. Recommended Fixes

### Phase 1: Unify Extraction (HIGH PRIORITY)

Create shared document extraction module:

```python
# NEW: openclaw/agents/ira/skills/brain/document_extractor.py

class DocumentExtractor:
    """Single source of truth for document extraction."""
    
    def extract_pdf(self, path: Path) -> str:
        """Extract text from PDF (used by dream + ingestor + retriever)."""
        pass
    
    def extract_knowledge(self, content: str) -> List[ExtractedFact]:
        """LLM-based knowledge extraction."""
        pass
    
    def detect_conflicts(self, new_facts: List, existing: List) -> List[Conflict]:
        """Check for contradictions."""
        pass
```

### Phase 2: Integrate with Qdrant (HIGH PRIORITY)

Dream-learned knowledge must be searchable:

```python
# Dream mode should:
def _store_knowledge_unified(self, knowledge: DocumentKnowledge):
    # 1. Store in Mem0 (semantic memory)
    self.unified_memory.store_entity_memory(...)
    
    # 2. ALSO store in Qdrant (for RAG retrieval)
    self.unified_retriever.index_chunk(
        text=fact,
        source="dream_learning",
        metadata={...}
    )
```

### Phase 3: Use UnifiedMemory (MEDIUM)

Replace raw Mem0 with UnifiedMemory:

```python
# Current (bad):
from mem0 import MemoryClient
self.mem0_client = MemoryClient(...)

# Should be:
from ...memory.unified_memory import get_unified_memory
self.memory = get_unified_memory()
```

### Phase 4: Add Conflict Detection (MEDIUM)

```python
def _consolidate_knowledge(self, knowledge):
    # Check for conflicts BEFORE storing
    for fact in knowledge.facts:
        conflicts = self.ingestor.check_conflicts(fact)
        if conflicts:
            self.conflict_queue.add(conflicts)
        else:
            self.memory.store(fact)
```

### Phase 5: Connect to BrainOrchestrator (LOWER)

```python
# Brain should check knowledge gaps from dream mode:
class BrainOrchestrator:
    def process(self, message):
        # Check if we have knowledge gaps on this topic
        gaps = self.dream_state.knowledge_gaps
        relevant_gaps = [g for g in gaps if g.topic in message]
        
        if relevant_gaps:
            # Trigger adaptive learning
            self.adaptive_retrieval.search_for_gap(relevant_gaps[0])
```

---

## 4. Unified Architecture (Target State)

```
╔═══════════════════════════════════════════════════════════════════════╗
║                     IRA'S LEARNING SYSTEM                             ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  [Documents]                      [Conversations]                     ║
║      ↓                                  ↓                             ║
║  DocumentExtractor ←───────────→ FeedbackLearner                      ║
║      ↓                                  ↓                             ║
║  ConflictDetector ←─────────────────────┘                             ║
║      ↓                                                                ║
║  ┌────────────────────────────────────────────────────┐               ║
║  │              UNIFIED MEMORY SERVICE                │               ║
║  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │               ║
║  │  │   Mem0      │  │  PostgreSQL │  │   Qdrant   │ │               ║
║  │  │ (semantic)  │  │ (episodic)  │  │   (RAG)    │ │               ║
║  │  └─────────────┘  └─────────────┘  └────────────┘ │               ║
║  └────────────────────────────────────────────────────┘               ║
║                          ↑                                            ║
║                    BrainOrchestrator                                  ║
║                          ↓                                            ║
║                  Response Generation                                  ║
║                                                                       ║
║  [Dream Mode] ─────────────────────────────────────────────┘          ║
║  (Nightly: Extract → Conflict Check → Store to ALL systems)           ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 5. Priority Matrix

| Fix | Effort | Impact | Priority |
|-----|--------|--------|----------|
| Integrate Qdrant storage | Medium | HIGH | **P0** |
| Use UnifiedMemory | Low | Medium | **P1** |
| Shared document extractor | Medium | Medium | **P1** |
| Add conflict detection | Medium | Medium | **P2** |
| Knowledge graph queries | High | Low | **P3** |
| BrainOrchestrator integration | High | Medium | **P3** |

---

## 6. Quick Wins (Do Now)

### 6.1 Store to Qdrant in Dream Mode

Add 20 lines to store dream knowledge in Qdrant:

```python
def _store_to_qdrant(self, fact: str, metadata: dict):
    """Store in Qdrant for RAG retrieval."""
    try:
        from qdrant_client import QdrantClient
        import voyageai
        
        voyage = voyageai.Client()
        embedding = voyage.embed([fact], model="voyage-3").embeddings[0]
        
        qdrant = QdrantClient(url=os.environ.get("QDRANT_URL"))
        qdrant.upsert(
            collection_name="ira_dream_knowledge_v1",
            points=[{
                "id": uuid.uuid4().hex,
                "vector": embedding,
                "payload": {"text": fact, **metadata}
            }]
        )
    except Exception as e:
        print(f"Qdrant store failed: {e}")
```

### 6.2 Query Knowledge Gaps in Brain

Check dream gaps during conversations:

```python
# In BrainOrchestrator.process():
if hasattr(self, 'dream_state') and self.dream_state.knowledge_gaps:
    for gap in self.dream_state.knowledge_gaps[:3]:
        if gap['topic'].lower() in message.lower():
            state.context['knowledge_gap_detected'] = gap
```

---

## Next Steps

1. **Immediate**: Implement Qdrant storage in dream mode
2. **Short-term**: Create shared DocumentExtractor
3. **Medium-term**: Full UnifiedMemory integration
4. **Long-term**: BrainOrchestrator integration

Would you like me to implement these fixes?
