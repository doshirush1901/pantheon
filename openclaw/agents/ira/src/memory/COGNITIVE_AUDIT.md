# Cognitive Architecture Audit
## Ira's Brain - Gap Analysis from Neuroscience Perspective

**Auditor**: Neuro-AI Analysis  
**Date**: 2026-02-27  
**Framework**: Atkinson-Shiffrin Memory Model + Modern Cognitive Architectures

---

## 1. CURRENT ARCHITECTURE MAP

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CURRENT IRA BRAIN                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  SEMANTIC   │    │ PROCEDURAL  │    │ RELATIONSHIP│             │
│  │   MEMORY    │    │   MEMORY    │    │   MEMORY    │             │
│  │  (facts)    │    │  (skills)   │    │  (social)   │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                  │                  │                     │
│         └──────────────────┼──────────────────┘                     │
│                            │                                        │
│                    ┌───────▼───────┐                               │
│                    │    TRIGGER    │  ← Attention Gate             │
│                    └───────┬───────┘                               │
│                            │                                        │
│                    ┌───────▼───────┐                               │
│                    │    WEAVER     │  ← Context Format             │
│                    └───────┬───────┘                               │
│                            │                                        │
│                    ┌───────▼───────┐                               │
│                    │   REASONER    │  ← Inner Monologue            │
│                    └───────┬───────┘                               │
│                            │                                        │
│                    ┌───────▼───────┐                               │
│                    │   EMOTIONAL   │  ← Affect Detection           │
│                    │ INTELLIGENCE  │                               │
│                    └───────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. GAP ANALYSIS

### 2.1 EPISODIC MEMORY ✅ [IMPLEMENTED]

**What it is**: Memory for specific events with temporal-spatial context.

**Current state**: We store FACTS ("John works at ABC Corp") but not EVENTS ("On Tuesday Feb 20 at 3pm, John called frustrated about a shipping delay").

**Neuroscience**: Hippocampus binds what/where/when into episodes. These episodes later consolidate into semantic memory.

**Impact**:
- Cannot answer "When did we last discuss this?"
- Cannot track conversation history as events
- Cannot learn from temporal patterns

**Missing file**: `episodic_memory.py`

```python
# What we need:
@dataclass
class Episode:
    event_id: str
    timestamp: datetime
    participants: List[str]
    location: str  # channel/context
    summary: str
    emotional_valence: float
    linked_entities: List[str]
    retrieval_cues: List[str]
```

---

### 2.2 META-COGNITION ✅ [IMPLEMENTED]

**What it is**: Awareness of one's own knowledge and knowledge gaps.

**Current state**: Ira doesn't know what it doesn't know. It can hallucinate confidently.

**Neuroscience**: Prefrontal cortex monitors confidence. "Tip of tongue" feeling = partial retrieval.

**Impact**:
- Cannot say "I'm not sure, let me check"
- Cannot express uncertainty calibrated to actual knowledge
- Cannot ask targeted clarifying questions

**Missing file**: `metacognition.py`

```python
# What we need:
class MetaCognition:
    def assess_knowledge(self, query: str) -> KnowledgeState:
        """
        Returns:
        - KNOW_CONFIDENT: Have verified info
        - KNOW_UNCERTAIN: Have info, low confidence
        - PARTIAL: Have related info, not exact
        - UNKNOWN: No relevant knowledge
        - CONFLICTING: Have contradictory info
        """
```

---

### 2.3 PREDICTIVE PROCESSING ❌ [HIGH]

**What it is**: Brain constantly predicts what comes next, updates on prediction error.

**Current state**: Purely reactive. Waits for input, then responds.

**Neuroscience**: Predictive coding is fundamental - brain is a prediction machine.

**Impact**:
- Cannot anticipate user needs
- Cannot prepare relevant context in advance
- Cannot learn from prediction errors

**Missing file**: `predictive_engine.py`

```python
# What we need:
class PredictiveEngine:
    def predict_next(self, context: Context) -> List[Prediction]:
        """
        Based on:
        - User's typical patterns
        - Time of day/week
        - Current conversation flow
        - Recent events
        
        Returns probable next queries/needs.
        """
    
    def record_prediction_error(self, predicted: Prediction, actual: Event):
        """Learn from wrong predictions."""
```

---

### 2.4 SOURCE MONITORING ❌ [MEDIUM]

**What it is**: Tracking WHERE knowledge came from.

**Current state**: All memories treated equally regardless of source.

**Neuroscience**: Source memory (reality monitoring) distinguishes:
- Self-generated vs externally-provided
- Perceived vs imagined
- Said vs thought

**Impact**:
- Cannot cite sources properly
- Cannot distinguish "user told me" vs "I inferred"
- Cannot weight reliability by source

**Missing field in memories**: `source_type`, `source_confidence`

```python
class SourceType(Enum):
    USER_STATED = "user_stated"      # User explicitly said
    DOCUMENT = "document"            # Read from knowledge base
    INFERRED = "inferred"            # Deduced from context
    CORRECTED = "corrected"          # User corrected previous belief
    EXTERNAL = "external"            # External system provided
```

---

### 2.5 EMOTIONAL MEMORY MODULATION ❌ [MEDIUM]

**What it is**: Emotions affect memory encoding strength.

**Current state**: Emotional state is detected but doesn't affect memory storage.

**Neuroscience**: Amygdala modulates hippocampal encoding. High-emotion events are remembered better.

**Impact**:
- Important emotional moments treated same as routine ones
- Complaints and praises stored with equal weight
- Missing "flashbulb memory" effect

**Fix**: Connect emotional_intelligence.py → persistent_memory.py

```python
def store_memory(self, ..., emotional_context: EmotionalReading = None):
    if emotional_context:
        # Strong emotions boost confidence
        if emotional_context.intensity == EmotionalIntensity.STRONG:
            confidence *= 1.3
```

---

### 2.6 RECONSOLIDATION ❌ [MEDIUM]

**What it is**: Memories change when recalled - they're reconstructed, not replayed.

**Current state**: Retrieving a memory doesn't update it (except use_count).

**Neuroscience**: Each recall is a reconstruction. Memory is malleable during reconsolidation window.

**Impact**:
- Memories don't get refined with new context
- Cannot update memory with new information during recall
- Missing "living memory" effect

**Fix**: Update memory confidence/content when retrieved with new context.

---

### 2.7 INTERFERENCE EFFECTS ❌ [LOW]

**What it is**: New learning can disrupt old memories (retroactive) and old memories can block new learning (proactive).

**Current state**: Memories are independent. New memory doesn't affect old ones.

**Neuroscience**: Interference is a primary cause of forgetting. Similar memories compete.

**Impact**:
- Conflicting memories can coexist without detection
- No mechanism for resolving contradictions automatically

---

### 2.8 WORKING MEMORY CAPACITY ❌ [LOW]

**What it is**: Limited capacity (~4 items) for active manipulation.

**Current state**: No limit on context injected into prompt.

**Neuroscience**: Cowan's 4±1 chunks. Exceeding capacity causes errors.

**Impact**:
- Context overload possible
- No prioritization under constraint

---

## 3. PRIORITY IMPLEMENTATION ROADMAP

| Priority | Component | Impact | Effort |
|----------|-----------|--------|--------|
| 🔴 P0 | Episodic Memory | High | Medium |
| 🔴 P0 | Meta-cognition | High | Low |
| 🟡 P1 | Predictive Engine | Medium | High |
| 🟡 P1 | Source Monitoring | Medium | Low |
| 🟡 P1 | Emotional Modulation | Medium | Low |
| 🟢 P2 | Reconsolidation | Low | Low |
| 🟢 P2 | Interference | Low | Medium |
| 🟢 P2 | WM Capacity | Low | Low |

---

## 4. RECOMMENDED NEXT STEPS

### Immediate (This Week):
1. **Add source_type field** to all memories
2. **Connect emotional detection to memory encoding**
3. **Create KnowledgeState assessment** for meta-cognition

### Short-term (This Month):
4. **Build Episode schema** in PostgreSQL
5. **Create EpisodicMemory class** for event storage/retrieval
6. **Implement basic prediction** based on user patterns

### Medium-term:
7. **Temporal pattern learning** for prediction
8. **Reconsolidation hooks** on memory retrieval
9. **Working memory capacity management**

---

## 5. ARCHITECTURE VISION

```
┌─────────────────────────────────────────────────────────────────────┐
│                      TARGET IRA BRAIN 2.0                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  PREDICTIVE LAYER                           │   │
│  │    "What will user need next?"                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                            │                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  EPISODIC   │───▶│  SEMANTIC   │───▶│ PROCEDURAL  │             │
│  │  (events)   │    │  (facts)    │    │  (skills)   │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                  │                  │                     │
│         │   ┌──────────────┼──────────────┐   │                     │
│         │   │     SOURCE MONITORING       │   │                     │
│         │   │  (where did this come from?)│   │                     │
│         │   └──────────────┬──────────────┘   │                     │
│         │                  │                  │                     │
│         └──────────────────┼──────────────────┘                     │
│                            │                                        │
│                    ┌───────▼───────┐                               │
│                    │ META-COGNITION│  ← "Do I know this?"          │
│                    └───────┬───────┘                               │
│                            │                                        │
│                    ┌───────▼───────┐                               │
│                    │   EMOTIONAL   │  ← Modulates encoding         │
│                    │   AMYGDALA    │                               │
│                    └───────┬───────┘                               │
│                            │                                        │
│                    ┌───────▼───────┐                               │
│                    │   WORKING     │  ← 4-item capacity            │
│                    │    MEMORY     │                               │
│                    └───────┬───────┘                               │
│                            │                                        │
│                    ┌───────▼───────┐                               │
│                    │   RESPONSE    │                               │
│                    │  GENERATION   │                               │
│                    └───────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. KEY INSIGHT

The biggest gap isn't any single component - it's the **lack of temporal grounding**.

Human memory is fundamentally about TIME:
- WHEN did this happen?
- WHAT happened BEFORE/AFTER?
- HOW LONG AGO?
- WHAT TYPICALLY HAPPENS at this time?

Ira currently exists in an eternal present with facts but no timeline.

**Implementing episodic memory would be the single highest-impact improvement.**

---

*"Memory is not a recording. It's a reconstruction. Every time you remember, you're creating a new memory."*
— Neuroscience principle that Ira doesn't yet embody.
