---
name: answer_query
description: Answer questions about Machinecraft machines, specs, pricing, and capabilities using deep research or quick RAG lookup.
---

# Answer Query

Use this skill when the user asks about Machinecraft machines, specifications, pricing, or capabilities.

## How to use

### Option 1: Multi-Agent System (Recommended)
The ChiefOfStaffAgent automatically routes to ResearcherAgent for knowledge retrieval:

```python
from src.agents import get_chief_of_staff

cos = get_chief_of_staff()
response = await cos.process_message(query, user_id, channel)
```

The agent system:
1. Plans the research approach using `planner.py`
2. Delegates to ResearcherAgent for parallel Mem0/Qdrant/Machine DB search
3. Routes to WriterAgent for response formatting
4. Validates through FactCheckerAgent
5. Learns via ReflectorAgent

### Option 2: Direct Researcher Call
For direct research without orchestration:

```python
from src.agents.researcher import get_researcher

researcher = get_researcher()
result = await researcher.research(query, user_id)
```

### Option 3: Quick RAG Lookup (For simple queries)
For simple, time-sensitive questions:

```python
from openclaw.agents.ira.src.brain.unified_retriever import UnifiedRetriever

retriever = UnifiedRetriever()
results = retriever.search(query)
```

## When to use which

**Use Deep Research for:**
- Pricing questions ("What's the price of...?")
- Technical specifications ("What are the specs...?")
- Machine comparisons ("Compare X vs Y")
- Complex multi-part questions
- When accuracy matters more than speed

**Use Quick RAG for:**
- Simple factual lookups
- Follow-up questions in a conversation
- Time-critical responses

## Important rules
- Never fabricate specifications. If confidence is low, say so.
- For AM series machines, thickness is ALWAYS ≤1.5mm.
- Always add "subject to configuration and current pricing" when quoting prices.
- Prefer Deep Research for pricing - it accesses the Plastindia Price List directly.
