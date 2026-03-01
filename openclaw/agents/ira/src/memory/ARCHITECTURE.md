# Ira Memory Architecture - Future Roadmap

## Current State (v1 - Implemented)

```
┌──────────────────────────────────────────────────────────────┐
│                     SEMANTIC MEMORY                          │
│  ├── User Facts (persistent_memory.py)                       │
│  ├── Entity Facts (companies, contacts)                      │
│  ├── Corrections                                             │
│  └── Themes & Importance Scoring                             │
├──────────────────────────────────────────────────────────────┤
│                     CONVERSATION MEMORY                      │
│  ├── Recent Messages (memory_service.py)                     │
│  ├── Rolling Summary                                         │
│  └── Key Entities                                            │
└──────────────────────────────────────────────────────────────┘
```

## Target State (v2 - Research-Informed)

Based on MemVerse, MemGen, CORPGEN, and Memory Bear architectures:

### 1. Hierarchical Memory Layers

```
LAYER 1: WORKING MEMORY (in-context)
├── Current turn context
├── Last 5-10 messages
└── Active entities being discussed

LAYER 2: EPISODIC MEMORY (new)
├── Event records: "Feb 27: Discussed PF1 pricing with John"
├── Conversation summaries per session
├── Key decisions/commitments made
└── Time-indexed for temporal queries ("what did we discuss last week?")

LAYER 3: SEMANTIC MEMORY (current)
├── User facts, preferences, context
├── Entity knowledge (companies, contacts)
├── Corrections and learned truths
└── Themed organization

LAYER 4: PROCEDURAL MEMORY (new)
├── Learned behaviors: "When user mentions price, check for approved pricing"
├── Response patterns that worked well
├── Failure patterns to avoid
└── Sales process stages that succeeded
```

### 2. Memory Trigger System (from MemGen)

Instead of always retrieving memories, implement intelligent triggering:

```python
class MemoryTrigger:
    """Decides WHEN to access memory."""
    
    def should_retrieve_user_memory(self, message: str, context: dict) -> bool:
        # Trigger on: personal questions, follow-ups, relationship building
        triggers = [
            "what do you know", "remember", "last time", "you mentioned",
            "my preference", "i told you", "we discussed"
        ]
        return any(t in message.lower() for t in triggers) or context.get("is_returning_user")
    
    def should_retrieve_entity_memory(self, message: str, entities: list) -> bool:
        # Trigger when entities are mentioned
        return len(entities) > 0
    
    def should_retrieve_episodic(self, message: str) -> bool:
        # Trigger on temporal references
        temporal = ["last time", "yesterday", "last week", "before", "earlier"]
        return any(t in message.lower() for t in temporal)
```

### 3. Memory Consolidation Pipeline (from MemVerse)

```python
# Run nightly or on threshold triggers

async def consolidate_memories():
    """
    1. Episodic → Semantic: Extract lasting facts from episodes
    2. Semantic → Procedural: Learn behavior patterns
    3. Decay: Reduce confidence of unused memories
    4. Merge: Combine similar memories
    5. Prune: Archive very old, unused memories
    """
    pass
```

### 4. Adaptive Forgetting (from research)

Current decay is time-based. Better approach:

```python
def calculate_retention(memory):
    """
    Factors:
    - Emotional salience (important moments)
    - Retrieval count (frequently accessed)
    - Recency (recently used)
    - Connections (linked to other memories)
    - Contradiction (conflicts with newer info → decay faster)
    """
    base = memory.confidence
    
    # Emotional salience - corrections and relationship moments persist
    if memory.type in ["correction", "relationship"]:
        base *= 1.2
    
    # Retrieval strengthens memory (spacing effect)
    retrieval_boost = min(memory.use_count * 0.05, 0.3)
    
    # Recency
    days_old = (now() - memory.last_used).days
    recency_factor = math.exp(-days_old / 60)  # Half-life ~60 days
    
    # Connections boost
    connections = count_related_memories(memory)
    connection_boost = min(connections * 0.02, 0.2)
    
    return min(1.0, base + retrieval_boost + connection_boost) * recency_factor
```

### 5. Multi-Horizon Planning Memory (from CORPGEN)

For sales agent use case:

```python
class MultiHorizonMemory:
    """
    SHORT TERM (minutes): Current conversation goal
    MEDIUM TERM (days): Active deal progression
    LONG TERM (months): Relationship building, account strategy
    """
    
    def get_relevant_horizon(self, message: str):
        if "right now" in message or "today" in message:
            return self.short_term
        elif "this week" in message or "follow up" in message:
            return self.medium_term
        else:
            return self.long_term
```

## Implementation Priority

### Phase 1: Quick Wins
- [ ] Memory Trigger system (don't retrieve every turn)
- [ ] Episodic memory for conversation summaries
- [ ] Temporal queries ("what did we discuss last week?")

### Phase 2: Intelligence
- [ ] Procedural memory (learned behaviors)
- [ ] Adaptive forgetting (not just time-based)
- [ ] Memory connections/graph

### Phase 3: Advanced
- [ ] Multi-horizon planning memory
- [ ] Automatic consolidation pipeline
- [ ] Memory Bear-style cognitive services

## References

1. MemVerse (2025): Hierarchical retrieval + consolidation
2. MemGen (2025): Memory trigger + weaver pattern
3. CORPGEN (2026): Multi-horizon task memory
4. Memory Bear (2025): Cognitive architecture benchmarks
5. Generative Agents (2023): Memory stream + reflection
