# Knowledge Ingestion Architecture

## Overview

When scanning new documents for knowledge ingestion, Ira stores data in **four locations** to ensure complete accessibility and redundancy.

## Best Practices Implemented

| Practice | Description |
|----------|-------------|
| **Semantic Clustering** | Similar knowledge grouped together (Obsidian-style) |
| **Relationship Discovery** | Auto-link related knowledge items |
| **Topic Detection** | Auto-categorize by topic |
| **Deduplication** | Content hashes prevent duplicate entries |
| **Validation** | Data quality checks before ingestion |
| **Chunking** | Large texts (>2000 chars) split with overlap |
| **Audit Logging** | All operations logged to `data/knowledge/audit.jsonl` |
| **Source Fingerprinting** | File hashes detect document changes |
| **Sleep Consolidation** | Nightly graph reorganization based on usage |

## Storage Destinations

| Storage | Collection/Location | Purpose |
|---------|---------------------|---------|
| **Qdrant Main** | `ira_chunks_v4_voyage` | Primary semantic search |
| **Qdrant Discovered** | `ira_discovered_knowledge` | Dedicated knowledge store |
| **Mem0** | `machinecraft_*` users | Long-term memory |
| **JSON Backup** | `data/knowledge/*.json` | Disaster recovery |
| **Hash Registry** | `data/knowledge/ingested_hashes.json` | Deduplication |
| **Audit Log** | `data/knowledge/audit.jsonl` | Operation history |
| **Knowledge Graph** | `data/knowledge/knowledge_graph.json` | Relationships |
| **Clusters** | `data/knowledge/clusters.json` | Semantic groups |

## Quick Start

### Simple Ingestion

```python
from openclaw.agents.ira.skills.brain.knowledge_ingestor import ingest_knowledge

result = ingest_knowledge(
    text="PF1-C-2015 specifications: 72kW top heater, 50.4kW bottom heater...",
    knowledge_type="machine_spec",
    source_file="specs.xlsx",
    entity="PF1-C-2015",
    summary="PF1-C-2015: 72kW/50.4kW heaters, 3000 LPM vacuum",
    metadata={"series": "PF1", "variant": "C"}
)

print(result)  # ✓ Ingested 1 items | Qdrant-main: True | Qdrant-discovered: True | Mem0: True | JSON: True
```

### Document Ingestion

```python
from pathlib import Path
from openclaw.agents.ira.skills.brain.knowledge_ingestor import KnowledgeIngestor

def extract_specs(path: Path):
    """Custom extractor for your document format."""
    import pandas as pd
    df = pd.read_excel(path)
    
    items = []
    for _, row in df.iterrows():
        items.append({
            "text": f"Model {row['model']}: {row['description']}",
            "entity": row['model'],
            "summary": f"{row['model']}: {row['key_spec']}",
            "metadata": {"price": row.get('price')}
        })
    return items

ingestor = KnowledgeIngestor()
result = ingestor.ingest_document(
    file_path="data/imports/new_specs.xlsx",
    extractor_fn=extract_specs,
    knowledge_type="machine_spec"
)
```

## Knowledge Types

| Type | Mem0 User ID | Use For |
|------|--------------|---------|
| `machine_spec` | `machinecraft_knowledge` | Technical specifications |
| `pricing` | `machinecraft_pricing` | Prices, quotations |
| `customer` | `machinecraft_customers` | Customer data |
| `process` | `machinecraft_processes` | Manufacturing processes |
| `application` | `machinecraft_applications` | Use cases, industries |
| `general` | `machinecraft_general` | Everything else |

## Knowledge Graph (Obsidian-style)

The ingestor automatically organizes knowledge like a graph database:

### Semantic Clustering

Similar items are grouped together based on embedding similarity:

```python
# Example output:
# Cluster: "PF1-C-2015 & PF1-C-2020 & PF1-C-3020"
#   Topic: machine_specs
#   Coherence: 0.98 (very tight cluster)
```

### Relationship Types

| Type | Description | Strength |
|------|-------------|----------|
| `same_entity` | Same machine/entity | 1.0 |
| `same_cluster` | In same semantic cluster | 0.9 |
| `similar_content` | High semantic similarity | 0.75+ |
| `same_source` | From same document | 0.7 |

### Topic Detection

Items are auto-categorized by analyzing content:
- `machine_specs` - heater, vacuum, cylinder, kW
- `pricing` - price, cost, quote, INR, USD
- `materials` - ABS, HDPE, sheet, thickness
- `applications` - automotive, packaging, medical
- `processes` - thermoforming, lamination

### Using the Graph

```python
from openclaw.agents.ira.skills.brain.knowledge_graph import KnowledgeGraph

graph = KnowledgeGraph()

# Get related knowledge
related = graph.get_related("PF1-C-2015", depth=2)
for node, edge in related:
    print(f"{node.entity} --[{edge.relationship_type}]-- (strength: {edge.strength})")

# Get cluster members
members = graph.get_cluster_members("cluster_machine_specs_0")

# View stats
print(graph.visualize_stats())
```

## Retrieval Verification

After ingestion, verify the data is accessible:

```python
from openclaw.agents.ira.skills.brain.qdrant_retriever import retrieve

result = retrieve("What are the specs for PF1-C-2015?", top_k=5)

print(f"Found {result.total} results")
print(f"Top score: {result.citations[0].score}")
print(f"Doc types: {result.doc_type_counts}")
```

## Architecture Flow

```
┌─────────────────┐
│ Source Document │
│ (Excel, PDF)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Custom Extractor│
│ (parse & format)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│KnowledgeIngestor│
└────────┬────────┘
         │
    ┌────┼────┬────────┐
    ▼    ▼    ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Qdrant│ │Qdrant│ │ Mem0 │ │ JSON │
│ Main │ │Discov│ │Memory│ │Backup│
└──────┘ └──────┘ └──────┘ └──────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `knowledge_ingestor.py` | Main ingestion module |
| `ingest_pf1_specs.py` | Example: PF1-C specs ingestion |
| `qdrant_retriever.py` | Retrieval (queries all collections) |
| `unified_retriever.py` | Advanced retrieval with synthesis |
| `config.py` | Collection names (COLLECTIONS dict) |

## Collections in config.py

```python
COLLECTIONS = {
    "chunks_voyage": "ira_chunks_v4_voyage",
    "discovered_knowledge": "ira_discovered_knowledge",
    "dream_knowledge": "ira_dream_knowledge_v1",
    # ...
}
```

## Example: PF1-C Specs Ingestion

See `openclaw/agents/ira/skills/brain/ingest_pf1_specs.py` for a complete example that:

1. Parses an Excel file with technical specifications
2. Structures data into knowledge items
3. Generates human-readable knowledge text
4. Ingests to all four storage locations
5. Verifies retrieval works

## Checklist for New Documents

- [ ] Identify document format (Excel, PDF, etc.)
- [ ] Create custom extractor function
- [ ] Map data to knowledge items (text, entity, summary, metadata)
- [ ] Use `KnowledgeIngestor` for ingestion
- [ ] Verify retrieval with test query
- [ ] Check JSON backup in `data/knowledge/`
- [ ] Review audit log for any issues

## Best Practices in Detail

### 1. Deduplication

Content hashes prevent re-ingesting the same data:

```python
# Hashes stored in data/knowledge/ingested_hashes.json
# Automatically checked on each ingestion
ingestor = KnowledgeIngestor(skip_duplicates=True)  # Default
```

### 2. Validation

Each `KnowledgeItem` is validated before ingestion:
- Text must be at least 10 characters
- `knowledge_type` and `source_file` are required
- Confidence must be between 0 and 1

### 3. Smart Chunking

Large texts (>2000 chars) are automatically split:
- Chunks break at paragraph or sentence boundaries
- 200-character overlap preserves context
- Each chunk tagged with `[Entity - Part N]`

### 4. Audit Logging

All operations logged to `data/knowledge/audit.jsonl`:

```json
{"timestamp": "2024-...", "action": "ingest_batch", "items_ingested": 15, ...}
{"timestamp": "2024-...", "action": "document_extraction_start", "file": "specs.xlsx", ...}
```

### 5. Source Fingerprinting

Document hashes detect when source files change:

```python
# Stored in metadata.source_fingerprint
# Compare to detect updates
```

### 6. Confidence Scores

Set confidence for uncertain extractions:

```python
KnowledgeItem(
    text="...",
    confidence=0.8,  # 80% confident in this data
    ...
)
```

## Sleep Consolidation (Graph Learning)

During Ira's nightly "dream mode", the knowledge graph is reorganized based on daily interactions:

### How It Works

1. **Interaction Analysis**: Reviews all queries and which knowledge was retrieved
2. **Relationship Tuning**: 
   - Strengthens edges between co-accessed knowledge (frequently retrieved together)
   - Weakens edges that weren't useful together
   - Creates new edges for strongly co-accessed pairs
3. **Cluster Reorganization**: Moves nodes between clusters based on actual usage patterns
4. **Stale Node Detection**: Flags knowledge that hasn't been accessed in 30+ days

### Analogy: Human Memory Consolidation

Like how humans consolidate memories during sleep:
- **LTP (Long-Term Potentiation)**: Useful connections are strengthened
- **Synaptic Pruning**: Unused connections decay over time
- **Memory Reorganization**: Related memories cluster together

### Usage

```python
# Run as part of dream mode (automatic)
python dream_mode.py

# Or run consolidation directly
python graph_consolidation.py --days 7  # Analyze last 7 days
```

### Files

| File | Purpose |
|------|---------|
| `data/knowledge/retrieval_log.jsonl` | Logs every query + retrieved chunks |
| `data/knowledge/consolidation_log.json` | History of consolidation runs |
| `data/knowledge/knowledge_graph.json` | Current graph state |

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DECAY_FACTOR` | 0.95 | Edge strength decay per sleep cycle |
| `REINFORCEMENT_BOOST` | 0.15 | Edge strength increase when co-accessed |
| `CO_ACCESS_THRESHOLD` | 3 | Min co-access count to strengthen edge |
| `STALE_DAYS` | 30 | Days before marking node as stale |

## Git Practices

When adding new ingestion scripts:

```bash
# 1. Create feature branch
git checkout -b feature/ingest-new-document

# 2. Add extractor and test
# 3. Run ingestion
# 4. Verify retrieval works
# 5. Commit with clear message
git add .
git commit -m "Add ingestion for [document type]

- Extract [N] items from [source]
- Store to Qdrant + Mem0
- Verified retrieval works"

# 6. PR with test evidence
```

## Monitoring

Check ingestion health:

```bash
# View recent audit entries
tail -20 data/knowledge/audit.jsonl | jq .

# Count ingested items by type
cat data/knowledge/ingested_hashes.json | jq '.count'

# List all knowledge backups
ls -la data/knowledge/*.json
```
