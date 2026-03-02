# Deep Reply System - Improvement Strategy

## Current State Analysis

| Metric | Current | Target |
|--------|---------|--------|
| Database completeness (vacuum specs) | 29% | 95% |
| Database completeness (heater type) | 34% | 95% |
| Database completeness (features) | 43% | 90% |
| Reply length | 800-1200 words | Dynamic |
| Response time | ~20 seconds | <30s OK |
| Accuracy | Good (database-backed) | Verified |

---

## STRATEGY 1: Complete the Machine Database

### Problem
Only 29% of machines have vacuum specs. Missing data = incomplete replies.

### Solution: Auto-Extract from PDFs

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PDF Catalogues │────▶│  LLM Extractor   │────▶│ Machine Database│
│  & Quotations   │     │  (structured)    │     │   (verified)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Implementation:**
1. Scan all PDFs in `data/imports/`
2. Use LLM to extract structured specs
3. Human review before adding to database
4. Version control changes

**Priority: HIGH** - Direct impact on reply quality

---

## STRATEGY 2: Multi-Stage Query Understanding

### Problem
Current parser uses regex patterns. Misses nuanced queries.

### Solution: Intent Classification + Entity Extraction

```
Query: "What's the best machine for making 2m x 1.5m truck bedliners in HDPE?"

Stage 1 - Intent: RECOMMENDATION_REQUEST
Stage 2 - Entities:
  - Size: 2000 x 1500 mm
  - Application: truck bedliners
  - Material: HDPE
Stage 3 - Constraints:
  - Material requires specific heating (HDPE melts at 130°C)
  - Deep draw likely needed for bedliner shape
```

**Implementation:**
```python
class QueryAnalyzer:
    def __init__(self):
        self.intents = [
            "SPEC_REQUEST",      # "What are the specs of X?"
            "COMPARISON",        # "Compare X and Y"
            "RECOMMENDATION",    # "Which machine for Z?"
            "PRICE_INQUIRY",     # "How much is X?"
            "TECHNICAL_QUESTION" # "How does vacuum affect..."
        ]
    
    def analyze(self, query: str) -> QueryIntent:
        # Use LLM for intent + entity extraction
        pass
```

**Priority: MEDIUM** - Improves relevance

---

## STRATEGY 3: Hybrid Search (Keyword + Semantic)

### Problem
Pure semantic search misses exact model numbers.

### Solution: Combine approaches

```
Query: "PF1-C-2015 vacuum pump size"

Keyword Search:
  - Exact match "PF1-C-2015" in database ✓
  - Exact match in Qdrant chunks

Semantic Search:
  - "vacuum pump specifications for thermoforming"
  - Related concepts

Final: Merge & deduplicate
```

**Implementation:**
```python
def hybrid_search(query: str):
    # 1. Keyword search (BM25 or exact match)
    keyword_results = bm25_search(query)
    
    # 2. Semantic search (embeddings)
    semantic_results = vector_search(query)
    
    # 3. Reciprocal Rank Fusion
    merged = rrf_merge(keyword_results, semantic_results)
    
    return merged
```

**Priority: MEDIUM** - Better retrieval accuracy

---

## STRATEGY 4: Multi-Pass Reply Generation

### Problem
Single LLM call can miss details or have inconsistencies.

### Solution: Draft → Review → Polish pipeline

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Draft  │────▶│  Fact   │────▶│  Style  │────▶│  Final  │
│  Reply  │     │  Check  │     │  Polish │     │  Reply  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
```

**Implementation:**
```python
def generate_reply_v2(query, machines, context):
    # Pass 1: Generate draft
    draft = llm_generate(query, machines, context)
    
    # Pass 2: Fact check against database
    facts = extract_facts(draft)
    verified = verify_against_database(facts, machines)
    if not verified.all_correct:
        draft = fix_facts(draft, verified.corrections)
    
    # Pass 3: Style polish (brand voice, tone)
    final = polish_style(draft, brand_guidelines)
    
    return final
```

**Priority: HIGH** - Prevents hallucinations

---

## STRATEGY 5: Dynamic Reply Length

### Problem
Fixed 800-1200 words is overkill for simple queries.

### Solution: Adapt length to query complexity

```
Simple: "What's the price of PF1-C-2015?"
→ 100-200 words (quick answer + context)

Medium: "Compare PF1-C-2015 and PF1-C-1812"
→ 500-800 words (table + analysis)

Complex: "Which machine for 2m truck bedliners in HDPE, need detailed specs"
→ 800-1200 words (full technical analysis)
```

**Implementation:**
```python
def determine_reply_length(query_intent, num_machines, technical_depth):
    if query_intent == "PRICE_INQUIRY":
        return (100, 200)
    elif query_intent == "COMPARISON" and num_machines <= 2:
        return (500, 800)
    elif technical_depth == "HIGH":
        return (800, 1200)
    else:
        return (400, 600)
```

**Priority: MEDIUM** - Better UX

---

## STRATEGY 6: Learning from Feedback

### Problem
No mechanism to improve from corrections.

### Solution: Feedback loop with memory

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Ira sends  │────▶│  Rushabh    │────▶│  Store in   │
│  reply      │     │  corrects   │     │  Mem0       │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Future     │
                    │  replies    │
                    │  use this   │
                    └─────────────┘
```

**Implementation:**
```python
def process_feedback(original_reply, correction):
    # Extract what was wrong
    lesson = llm_extract_lesson(original_reply, correction)
    
    # Store in memory
    mem0.add(
        f"CORRECTION: When discussing {lesson.topic}, "
        f"remember that {lesson.correct_info}. "
        f"Previously said: {lesson.incorrect_info}",
        user_id="system_corrections"
    )
    
    # Update database if spec was wrong
    if lesson.is_spec_correction:
        update_machine_database(lesson)
```

**Priority: HIGH** - Continuous improvement

---

## STRATEGY 7: Customer Context Awareness

### Problem
Replies don't consider who's asking or their history.

### Solution: Customer profile integration

```python
def get_customer_context(email: str) -> CustomerContext:
    return CustomerContext(
        name="Rushabh Doshi",
        role="Director, Sales & Marketing",
        company="Machinecraft",
        relationship="internal",
        past_inquiries=[...],
        preferred_style="technical, detailed",
        known_applications=["automotive", "packaging"],
    )
```

**Implementation for external customers:**
```python
def generate_reply_with_context(query, machines, customer):
    context = f"""
    Customer: {customer.name} from {customer.company}
    Industry: {customer.industry}
    Previous machines: {customer.previous_purchases}
    Communication style: {customer.preferred_style}
    """
    # Adapt reply based on context
```

**Priority: LOW** (for now, internal use)

---

## STRATEGY 8: Competitive Intelligence

### Problem
Can't answer "How does this compare to ILLIG/Kiefel?"

### Solution: Competitor database

```python
COMPETITOR_DATA = {
    "ILLIG": {
        "country": "Germany",
        "price_range": "2-3x Machinecraft",
        "strengths": ["precision", "automation"],
        "weaknesses": ["price", "lead time"],
    },
    "Kiefel": {...},
    "GN Thermoforming": {...},
}
```

**Priority: LOW** - Nice to have

---

## STRATEGY 9: Pre-computed Recommendations

### Problem
Every query recalculates from scratch.

### Solution: Common query cache

```python
COMMON_RECOMMENDATIONS = {
    "truck_bedliner_2m": {
        "recommended": ["PF1-C-2015", "PF1-C-2020"],
        "reason": "Large forming area, deep draw capability",
        "generated": "2024-02-27",
    },
    "food_packaging_tray": {
        "recommended": ["AM-5060", "AM-6060"],
        "reason": "Roll-fed, fast cycles, food-safe",
    },
}
```

**Priority: LOW** - Optimization

---

## Implementation Roadmap

### Phase 1: Data Quality (Week 1)
- [ ] Auto-extract specs from all PDFs
- [ ] Fill missing vacuum/heater specs
- [ ] Verify prices against price list

### Phase 2: Accuracy (Week 2)
- [ ] Implement fact-checking pass
- [ ] Add verification against database
- [ ] Test with 20 sample queries

### Phase 3: Intelligence (Week 3)
- [ ] Better query understanding
- [ ] Dynamic reply length
- [ ] Hybrid search

### Phase 4: Learning (Week 4)
- [ ] Feedback loop implementation
- [ ] Correction storage in Mem0
- [ ] Database auto-update

---

## Quick Wins (Do Today)

1. **Fill database gaps** - Add vacuum specs to remaining PF1 machines
2. **Add heater type** - Mark all as "IR Quartz" or "IR Ceramic"
3. **Add more features** - From catalogue descriptions

## Metrics to Track

- Reply accuracy (spot-checked)
- Reply relevance (did it answer the question?)
- Customer response time (faster = working)
- Correction rate (fewer = better)
