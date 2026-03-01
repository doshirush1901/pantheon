# Ira Unified Architecture

**Date**: 2026-02-27  
**Status**: IMPLEMENTED

---

## Overview

This document describes Ira's unified memory architecture that:

1. **Mem0 as Primary Memory** - All semantic memory in one place
2. **Unified Identity** - Single canonical ID per person across all channels
3. **Graph-like Relationships** - Entity relationships via metadata linking
4. **PostgreSQL Removal** - No longer required; Mem0 + Qdrant is sufficient

---

## Architecture Diagram

```
╔════════════════════════════════════════════════════════════════════════════╗
║                        IRA'S UNIFIED MEMORY SYSTEM                          ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  INPUTS                                                                    ║
║  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                          ║
║  │Telegram │ │  Email  │ │Documents│ │  Dream  │                          ║
║  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                          ║
║       │           │           │           │                                ║
║       └───────────┴───────────┴───────────┘                                ║
║                         │                                                  ║
║                         ▼                                                  ║
║  ╔══════════════════════════════════════════════════════════════════╗     ║
║  ║              UNIFIED IDENTITY RESOLVER                            ║     ║
║  ║  ┌─────────────────────────────────────────────────────────┐     ║     ║
║  ║  │  Email: john@abc.com  ────┐                              │     ║     ║
║  ║  │  Telegram: 123456789  ────┼──▶  canonical_id: id_abc123 │     ║     ║
║  ║  │  Phone: +1234567890   ────┘                              │     ║     ║
║  ║  └─────────────────────────────────────────────────────────┘     ║     ║
║  ╚══════════════════════════════════════════════════════════════════╝     ║
║                         │                                                  ║
║                         ▼                                                  ║
║  ╔══════════════════════════════════════════════════════════════════╗     ║
║  ║              UNIFIED MEM0 SERVICE                                 ║     ║
║  ║  ┌──────────────────────────────────────────────────────────┐    ║     ║
║  ║  │  User Memories: conversations, preferences, facts        │    ║     ║
║  ║  │  Entity Memories: products, companies, people            │    ║     ║
║  ║  │  Relationships: works_at, interested_in, knows          │    ║     ║
║  ║  │  Episodes: timestamped interaction records               │    ║     ║
║  ║  │  Procedures: learned workflows and skills                │    ║     ║
║  ║  └──────────────────────────────────────────────────────────┘    ║     ║
║  ╚══════════════════════════════════════════════════════════════════╝     ║
║                         │                                                  ║
║           ┌─────────────┼─────────────┐                                   ║
║           ▼             ▼             ▼                                   ║
║  ┌────────────┐ ┌────────────┐ ┌────────────┐                             ║
║  │   MEM0    │ │  QDRANT   │ │   LOCAL    │                              ║
║  │ (Cloud)   │ │ (Vectors) │ │   (JSON)   │                              ║
║  └────────────┘ └────────────┘ └────────────┘                             ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

## Components

### 1. Unified Identity Resolver

**Location**: `openclaw/agents/ira/skills/memory/unified_mem0.py`

Maps any identifier (email, telegram_id, phone) to a single canonical ID:

```python
from openclaw.agents.ira.skills.memory.unified_mem0 import IdentityResolver

resolver = IdentityResolver()

# Any identifier resolves to the same person
id1 = resolver.resolve("john@company.com")   # id_abc123
id2 = resolver.resolve("123456789")           # id_abc123 (if linked)

# Explicitly link identifiers
resolver.link("john@company.com", "123456789")

# Update identity fields
resolver.update("john@company.com", name="John Smith", company="ABC Corp")
```

**Storage**: `data/identities.json`

### 2. Unified Mem0 Service

**Location**: `openclaw/agents/ira/skills/memory/unified_mem0.py`

Handles all memory operations:

```python
from openclaw.agents.ira.skills.memory.unified_mem0 import get_unified_mem0

service = get_unified_mem0()

# Store a conversation (auto-resolves identity)
service.remember(
    user_message="I need a thermoforming machine",
    assistant_response="What size products...",
    user_id="john@company.com",  # or telegram ID
    channel="email",
)

# Search with relationship expansion
result = service.search(
    query="thermoforming requirements",
    user_id="john@company.com",
)
# Returns: {"memories": [...], "related": [...]}

# Get formatted context for LLM prompt
context = service.get_context_for_prompt(
    query="quote request",
    user_id="123456789",
)
```

### 3. Mem0 Storage (PostgreSQL Replacement)

**Location**: `openclaw/agents/ira/skills/memory/mem0_storage.py`

Provides PostgreSQL-like storage using Mem0 + JSON:

```python
from openclaw.agents.ira.skills.memory.mem0_storage import get_mem0_storage

storage = get_mem0_storage()

# Episodic memory (was PostgreSQL)
storage.episodes.store_episode(
    identity_id="id_abc123",
    summary="Discussed thermoforming requirements",
    topics=["thermoforming", "machinery"],
    channel="telegram",
)

# Procedural memory (was PostgreSQL)
storage.procedures.store_procedure(
    name="generate_quote",
    trigger_patterns=["quote", "pricing", "offer"],
    steps=[
        {"action": "check_inventory", "description": "..."},
        {"action": "calculate_price", "description": "..."},
    ]
)

# Relationships
storage.relationships.add_relationship(
    source="John Smith",
    relation="works_at",
    target="ABC Corp",
)
```

### 4. Dream Mode Integration

**Location**: `openclaw/agents/ira/skills/brain/dream_mode.py`

Now stores to both Mem0 AND Qdrant:

```
Documents → Extract → Store in Mem0 (semantic search)
                  → Index in Qdrant (RAG retrieval)
                  → Extract relationships
```

---

## Configuration

### Environment Variables

```bash
# Required
MEM0_API_KEY=your_key
VOYAGE_API_KEY=your_key
QDRANT_URL=http://localhost:6333

# Optional - Set to false to disable PostgreSQL (default: false)
USE_POSTGRES=false

# Enable unified identity (default: true)
USE_UNIFIED_IDENTITY=true
```

### Feature Flags

In `config.py`:

```python
FEATURES = {
    "use_postgres": False,       # Disabled by default
    "use_unified_identity": True,
    "use_mem0": True,
    "use_voyage": True,
}

STORAGE_BACKEND = "mem0"  # or "postgres" if USE_POSTGRES=true
```

---

## Data Storage

### Mem0 Platform (Cloud)
- User memories: `user_id=<canonical_id>`
- Entity memories: `agent_id=<entity_type>_<entity_name>`
- Relationships: `agent_id=ira_relationships`
- Procedures: `agent_id=ira_procedures`

### Local JSON Backup
- Identities: `data/identities.json`
- Episodes: `data/mem0_storage/episodes.json`
- Procedures: `data/mem0_storage/procedures.json`
- Relationships: `data/mem0_storage/relationships.json`

### Qdrant (Vector Search)
- Document chunks: `ira_chunks_v4_voyage`
- Email chunks: `ira_emails_voyage_v2`
- Dream knowledge: `ira_dream_knowledge_v1`
- Customer data: `ira_customers`

---

## Migration Guide

### From PostgreSQL to Mem0

1. **Set environment variable**:
   ```bash
   USE_POSTGRES=false
   ```

2. **Data migration** (if needed):
   ```python
   # Run migration script
   python scripts/migrate_postgres_to_mem0.py
   ```

3. **Verify**:
   ```python
   from openclaw.agents.ira.skills.memory.mem0_storage import get_mem0_storage
   storage = get_mem0_storage()
   print(storage.get_stats())
   ```

### Linking Existing Identities

```python
from openclaw.agents.ira.skills.memory.unified_mem0 import get_unified_mem0

service = get_unified_mem0()

# Link email to telegram ID
service.link_identity("john@company.com", "123456789")

# Update identity info
service.update_identity("john@company.com", 
    name="John Smith",
    company="ABC Corp"
)
```

---

## API Reference

### UnifiedMem0Service

| Method | Description |
|--------|-------------|
| `remember(user_msg, assistant_msg, user_id, channel)` | Store conversation |
| `search(query, user_id, limit)` | Search with relationships |
| `search_entities(query, limit)` | Search entity memories |
| `get_all(user_id)` | Get all memories for user |
| `link_identity(id1, id2)` | Link two identifiers |
| `get_identity(identifier)` | Get full identity info |
| `update_identity(id, **kwargs)` | Update identity fields |
| `get_context_for_prompt(query, user_id)` | Get formatted context |

### Mem0Storage

| Property | Methods |
|----------|---------|
| `episodes` | `store_episode()`, `get_episodes()`, `search_episodes()` |
| `procedures` | `store_procedure()`, `find_procedure()`, `get_all()`, `update_success/failure()` |
| `relationships` | `add_relationship()`, `get_relationships()`, `search_relationships()` |

---

## Benefits

1. **Simplified Architecture**: One memory system instead of 3
2. **Cost Reduction**: No PostgreSQL hosting costs
3. **Better Search**: Mem0's semantic search vs SQL queries
4. **Unified Identity**: No more duplicate user records
5. **Relationship Tracking**: Know who knows who, who uses what
6. **Portable Data**: JSON backup for critical data

---

## Limitations

1. **Graph Queries**: Not as powerful as Neo4j for deep traversals
2. **Transactions**: No ACID guarantees (eventual consistency)
3. **Complex Queries**: SQL-style joins not available

---

---

## Memory Controller (NEW)

The **Memory Controller** is an intelligent agent that orchestrates all memory updates.

### When Data Changes

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    MEMORY UPDATE FLOW                                      ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  Source: Telegram, Email, Dream, Correction                               ║
║                         │                                                 ║
║                         ▼                                                 ║
║  ┌─────────────────────────────────────────────────────────────────┐     ║
║  │               MEMORY CONTROLLER                                  │     ║
║  │  1. CLASSIFY - What type of memory?                             │     ║
║  │  2. CHECK - Duplicate? Conflict?                                │     ║
║  │  3. DECIDE - Create/Update/Reinforce/Ignore/Conflict            │     ║
║  │  4. EXECUTE - Store to appropriate targets                      │     ║
║  └─────────────────────────────────────────────────────────────────┘     ║
║                         │                                                 ║
║           ┌─────────────┼─────────────┬─────────────┐                    ║
║           ▼             ▼             ▼             ▼                    ║
║     ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐               ║
║     │  Mem0   │   │ Qdrant  │   │  JSON   │   │Conflict │               ║
║     │ (user/  │   │(vectors)│   │(backup) │   │ Queue   │               ║
║     │ agent)  │   │         │   │         │   │         │               ║
║     └─────────┘   └─────────┘   └─────────┘   └─────────┘               ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### Memory Types & Destinations

| Memory Type | Mem0 | Qdrant | JSON | Notes |
|-------------|------|--------|------|-------|
| User facts | ✓ user_id | - | - | Personal info |
| Entity facts | ✓ agent_id | ✓ | - | Products, companies |
| Episodes | ✓ user_id | - | ✓ | Conversations |
| Procedures | ✓ agent_id | - | ✓ | Workflows |
| Dream insights | ✓ agent_id | ✓ | - | Document learning |
| Relationships | ✓ agent_id | - | ✓ | Entity connections |
| Corrections | UPDATE | UPDATE | - | Overwrites existing |

### Update Actions

| Action | When | Result |
|--------|------|--------|
| **CREATE** | New information | Store to all targets |
| **UPDATE** | Explicit correction | Replace existing |
| **REINFORCE** | Duplicate seen | Boost confidence |
| **IGNORE** | Noise (greetings, etc.) | Do nothing |
| **CONFLICT** | Contradicts existing | Queue for human review |
| **CONSOLIDATE** | Multiple episodes | Merge into semantic fact |

### Usage

```python
from openclaw.agents.ira.skills.memory import remember, correct

# From any channel - controller decides where to store
remember(
    "John prefers email over phone",
    source="telegram",
    identity_id="john@example.com"
)
# → Classified as USER_FACT
# → Stored to Mem0 (user_id=john@example.com)

# Entity fact from dream learning
remember(
    "EcoForm 3220 has 3200mm forming width",
    source="dream",
    entity_name="EcoForm 3220"
)
# → Classified as ENTITY_FACT
# → Stored to Mem0 (agent_id) + Qdrant

# Explicit correction
correct(
    "Actually, the price is $50,000, not $45,000",
    identity_id="john@example.com"
)
# → Finds existing memory
# → Updates it (doesn't create duplicate)
```

### Conflict Detection

When new information contradicts existing:

1. Controller detects similarity + contradiction
2. Queues to `data/conflicts.json`
3. Waits for human resolution via Telegram
4. User chooses: Keep old / Accept new / Merge

### Integration Points

Update these files to use the Memory Controller:

| File | Current | Should Use |
|------|---------|------------|
| `telegram_gateway.py` | Direct Mem0 | `remember()` |
| `email_handler.py` | Direct storage | `remember()` |
| `dream_mode.py` | Dual storage | `remember()` |
| `feedback_learner.py` | Direct | `remember()` |

---

## Next Steps

1. [x] ~~Migrate existing PostgreSQL data to Mem0~~
2. [ ] Update channel handlers to use Memory Controller
3. [ ] Add graph visualization for relationships
4. [ ] Build Telegram UI for conflict resolution
5. [ ] Add memory consolidation scheduler
