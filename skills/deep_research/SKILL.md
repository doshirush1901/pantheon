---
name: deep_research
description: Thorough, multi-source research pipeline that takes time to find accurate answers using Mem0, Qdrant, and document analysis with self-validation.
---

# Deep Research

Use this skill when the user asks a question that requires thorough research - pricing queries, technical specifications, machine comparisons, or any question where accuracy matters more than speed.

**This skill takes time (30-60+ seconds) - quality over speed!**

## How to use

### Via Multi-Agent System (Recommended)

```python
from src.agents import get_chief_of_staff

cos = get_chief_of_staff()
response = await cos.process_message(query, user_id, channel)
```

### Direct ResearcherAgent Call

```python
from src.agents.researcher import get_researcher

researcher = get_researcher()
result = await researcher.research(query, user_id, verbose=True)
```

The ResearcherAgent will:
1. **Analyze** the query via QueryAnalyzer (intent, entities, complexity)
2. **Search in parallel** - Mem0, Qdrant, Machine Database, Competitor Intel (using asyncio)
3. **Cache results** - Redis caching for 60-80% hit rate
4. **Find documents** - Semantic search across all collections
5. **Return structured** - ResearchResult with sources, confidence, and context

## When to use this skill

Use for:
- Pricing questions (e.g., "What is the price of PF1-C-2015?")
- Technical specifications (e.g., "What are the specs of the FCS-6050-3ST?")
- Machine comparisons (e.g., "Compare PF1-C vs PF1-X series")
- Complex questions requiring multiple sources
- Any question where getting it RIGHT matters more than being FAST

Do NOT use for:
- Simple greetings or chitchat
- Questions you can answer from immediate context
- Urgent queries where speed is critical

## Important rules

- This skill is SLOW by design - it takes 30-60+ seconds to research thoroughly
- Always mention the confidence level in your response
- If confidence is low (<0.5), suggest asking Rushabh for clarification
- Follow-up questions are logged for Rushabh to review

## Example output

```
[DEEP RESEARCH] Processing query...
[STEP 1] Understanding: Intent=pricing, Complexity=simple
[STEP 2] Memory search: Found 5 results
[STEP 3] Document selection: Selected 2 documents
[STEP 4] Reasoning: Confidence=0.85
[STEP 5] Response generated: 450 chars
[STEP 6] Questions for Rushabh: 2 generated

RESPONSE:
The PF1-C-2015 is priced at ₹60 Lakhs (India market). This is a Standard Pneumatic PF1 with 2000x1500mm forming area...

QUESTIONS FOR RUSHABH:
- [medium] Should I include detailed specs for PF1-C-2015 in my response?
- [low] Would you like me to schedule a follow-up with the customer?
```
