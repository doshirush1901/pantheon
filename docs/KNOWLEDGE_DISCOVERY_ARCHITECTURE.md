# Knowledge Discovery Architecture

## Overview

This document describes Ira's **Just-in-Time Learning** system - the ability to automatically discover missing knowledge when answering queries.

## Problem

When Ira receives a question but doesn't have the data in memory or database:
- ❌ Old behavior: "I don't have that information"
- ✅ New behavior: Search files → Extract data → Update memory → Answer

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KNOWLEDGE DISCOVERY WORKFLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Query: "What is the vacuum pump capacity for IMG-1350?"                   │
│                                                                              │
│                              ┌─────────────────┐                             │
│                              │   STEP 1        │                             │
│                              │   Check Known   │                             │
│                              │   Knowledge     │                             │
│                              └────────┬────────┘                             │
│                                       │                                      │
│                        ┌──────────────┴──────────────┐                       │
│                        ▼                              ▼                       │
│                   ┌─────────┐                   ┌─────────┐                  │
│                   │ Found   │                   │ GAP     │                  │
│                   │ Answer  │                   │ Detected│                  │
│                   └────┬────┘                   └────┬────┘                  │
│                        │                             │                       │
│                        ▼                             ▼                       │
│                   ┌─────────┐                   ┌─────────────────┐         │
│                   │ REPLY   │                   │ STEP 2          │         │
│                   │         │                   │ Nearest Neighbor │         │
│                   └─────────┘                   │ File Search      │         │
│                                                 └────────┬────────┘         │
│                                                          │                   │
│                                                          ▼                   │
│                                                 ┌─────────────────┐         │
│                                                 │ STEP 3          │         │
│                                                 │ Deep Scan Files │         │
│                                                 │ (PDF/Excel)     │         │
│                                                 └────────┬────────┘         │
│                                                          │                   │
│                                                          ▼                   │
│                                                 ┌─────────────────┐         │
│                                                 │ STEP 4          │         │
│                                                 │ LLM Extraction  │         │
│                                                 │ Find specific   │         │
│                                                 │ data point      │         │
│                                                 └────────┬────────┘         │
│                                                          │                   │
│                                                          ▼                   │
│                                                 ┌─────────────────┐         │
│                                                 │ STEP 5          │         │
│                                                 │ Store Knowledge │         │
│                                                 │ Qdrant + Mem0   │         │
│                                                 └────────┬────────┘         │
│                                                          │                   │
│                                                          ▼                   │
│                                                 ┌─────────────────┐         │
│                                                 │ STEP 6          │         │
│                                                 │ REPLY with      │         │
│                                                 │ discovered data │         │
│                                                 └─────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. KnowledgeGap Detection

Analyzes query and search results to detect what's missing:

```python
@dataclass
class KnowledgeGap:
    query: str           # Original question
    missing_data: str    # "vacuum pump capacity for IMG-1350"
    data_type: str       # "spec", "price", "feature", "application", "general"
    entity: str          # "IMG-1350"
    confidence: float    # 0.0-1.0
```

Uses LLM to analyze:
- What specific data point is being asked for?
- Is that data present in current search results?
- What exactly is missing?

### 2. Nearest Neighbor File Search

Finds candidate files most likely to contain the missing data:

**Scoring Factors:**
- **Entity match** (0.5): Filename contains machine model (e.g., "IMG-1350" in "Print IMG-1350 Catalogue.pdf")
- **Keyword match** (0.3 each): Relevant keywords in filename
- **Document type** (0.2-0.4): Catalogues > Specs > Quotations
- **Technology match** (0.3-0.4): FRIMO, technology docs for process questions
- **File format** (0.1): PDF for specs, Excel for prices

**Technology Expansions:**
```python
technology_expansions = {
    "hotmelt": ["frimo", "thermoforming", "lamination", "technology"],
    "lamination": ["frimo", "hotmelt", "vacuum", "technology"],
    "vacuum": ["frimo", "lamination", "thermoforming"],
    "img": ["inmold", "grain", "thermoforming", "soft", "touch"],
}
```

### 3. Deep File Scanning

Extracts full text from candidate files:

**PDF Scanning:**
- Uses pdfplumber for text extraction
- Processes up to 20 pages per file
- Maintains page references

**Excel Scanning:**
- Uses pandas for data extraction
- Processes up to 5 sheets
- Converts tables to text

### 4. LLM Data Extraction

Targeted extraction of the specific missing data point:

```python
prompt = f"""
WHAT WE'RE LOOKING FOR: {gap.missing_data}
ENTITY: {gap.entity}
DOCUMENT TEXT: {text[:8000]}

Find the exact value/data we're looking for.

Return JSON:
{
    "found": true/false,
    "data_point": "the exact value (e.g., '160 m³/hr')",
    "context": "surrounding text for verification",
    "confidence": 0.0-1.0
}
"""
```

### 5. Knowledge Storage

Discovered data is stored for future use:

**Qdrant** (for RAG):
- Collection: `ira_discovered_knowledge`
- Voyage-3 embeddings
- Includes source, confidence, entity metadata

**Mem0** (semantic memory):
- User: `system_ira_discoveries`
- Tagged with entity, data type
- Enables retrieval in future conversations

## Integration with Reply System

In `ira_auto_deep.py`:

```python
# Deep research
parsed = parse_query(query)
machines = find_machines(parsed)
context = search_qdrant(query)

# KNOWLEDGE DISCOVERY - Find missing data on-the-fly
discovered_data = check_and_discover_missing_data(query, machines, context)

if discovered_data:
    # Add discovered data to context
    for key, value in discovered_data.items():
        context.append({
            "text": f"DISCOVERED: {key}: {value}",
            "score": 0.95
        })

# Generate reply with discovered data included
reply = generate_reply(parsed, machines, context)
```

## Example Flow

**Query:** "What is the vacuum pump for IMG-1350?"

1. **Check database:** IMG-1350 found, but vacuum_pump_capacity = ""
2. **Detect gap:** Missing "vacuum pump capacity for IMG-1350"
3. **Search files:**
   - Score 1.00: Print IMG-1350 Machinecraft Catalogue.pdf
   - Score 0.90: Print PF1-A Machinecraft Catalogue.pdf
4. **Deep scan:** Extract text from IMG-1350 catalogue
5. **LLM extraction:** Find "2 x 100 m3/hr each"
6. **Store:** Save to Qdrant + Mem0
7. **Reply:** Include discovered data

## Performance Considerations

- File discovery: ~50ms
- PDF scanning: ~2-3s per file
- LLM extraction: ~2-3s
- Total discovery: ~5-8s per missing data point

**Optimization:** Only trigger for critical missing data (vacuum, heater, price).

## Files

| File | Purpose |
|------|---------|
| `knowledge_discovery.py` | Main discovery module |
| `ira_auto_deep.py` | Integration in reply loop |
| `machine_database.py` | Primary data (triggers discovery when empty) |

## Future Enhancements

1. **Parallel file scanning** - Scan multiple candidates simultaneously
2. **Caching** - Cache PDF text extraction for frequently accessed files
3. **Proactive discovery** - Pre-scan likely files during idle time
4. **Discovery confidence threshold** - Only use discovered data above 0.8 confidence
5. **Human validation queue** - Flag uncertain discoveries for review
