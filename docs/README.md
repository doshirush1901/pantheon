# Ira Documentation

Welcome to the Ira documentation. This directory contains all technical documentation, architecture references, and operational guides.

---

## Quick Navigation

| I want to... | Read this |
|--------------|-----------|
| Understand the architecture | [Agent Architecture](AGENT_ARCHITECTURE.md) |
| Learn about the memory system | [Unified Architecture](UNIFIED_ARCHITECTURE.md) |
| Configure email processing | [Email Audit](EMAIL_AUDIT.md) |
| Set up Telegram bot | [Telegram Bot Audit](TELEGRAM_BOT_AUDIT.md) |
| Understand knowledge retrieval | [Knowledge Discovery](KNOWLEDGE_DISCOVERY_ARCHITECTURE.md) |

---

## Documentation Index

### Architecture & Design

| Document | Description |
|----------|-------------|
| [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) | Core agent architecture, message flow, and component interactions |
| [UNIFIED_ARCHITECTURE.md](UNIFIED_ARCHITECTURE.md) | Unified memory system with Mem0, identity resolution, and storage |
| [KNOWLEDGE_DISCOVERY_ARCHITECTURE.md](KNOWLEDGE_DISCOVERY_ARCHITECTURE.md) | RAG system, knowledge retrieval, and document processing |
| [KNOWLEDGE_HEALTH_SYSTEM.md](KNOWLEDGE_HEALTH_SYSTEM.md) | Knowledge quality monitoring and maintenance |

### Channel Integrations

| Document | Description |
|----------|-------------|
| [TELEGRAM_BOT_AUDIT.md](TELEGRAM_BOT_AUDIT.md) | Telegram bot implementation and features |
| [TELEGRAM_BEST_PRACTICES.md](TELEGRAM_BEST_PRACTICES.md) | Guidelines for Telegram interactions |
| [EMAIL_AUDIT.md](EMAIL_AUDIT.md) | Email channel processing and Gmail integration |
| [EMAIL_BRAIN_INTEGRATION_PLAN.md](EMAIL_BRAIN_INTEGRATION_PLAN.md) | Email-brain system integration strategy |

### Feature Systems

| Document | Description |
|----------|-------------|
| [DREAM_MODE_AUDIT.md](DREAM_MODE_AUDIT.md) | Nightly learning and knowledge consolidation system |
| [DEEP_REPLY_IMPROVEMENT_STRATEGY.md](DEEP_REPLY_IMPROVEMENT_STRATEGY.md) | Response quality optimization |
| [CONVERSATIONAL_UPGRADE_PLAN.md](CONVERSATIONAL_UPGRADE_PLAN.md) | Conversational AI enhancements |
| [KNOWLEDGE_INGESTION.md](KNOWLEDGE_INGESTION.md) | Document ingestion pipeline |

### Audits & Analysis

| Document | Description |
|----------|-------------|
| [CODEBASE_AUDIT.md](CODEBASE_AUDIT.md) | Full codebase structure analysis |
| [UNIFICATION_AUDIT.md](UNIFICATION_AUDIT.md) | System unification assessment |
| [UNIFICATION_GAPS_AUDIT.md](UNIFICATION_GAPS_AUDIT.md) | Gap analysis for unified architecture |

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              IRA SYSTEM                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CHANNELS              BRAIN                    STORAGE                     │
│  ┌───────────┐        ┌───────────────┐        ┌───────────────┐           │
│  │ Telegram  │───────▶│ Orchestrator  │───────▶│    Qdrant     │           │
│  │ Email     │        │ RAG Retrieval │        │ (Vectors)     │           │
│  │ API       │        │ Answer Gen    │        ├───────────────┤           │
│  └───────────┘        └───────────────┘        │    Mem0       │           │
│                                                │ (Memory)      │           │
│  SKILLS               MEMORY                   ├───────────────┤           │
│  ┌───────────┐        ┌───────────────┐        │  PostgreSQL   │           │
│  │ Email     │        │ Episodic      │        │ (Optional)    │           │
│  │ Drafting  │        │ Semantic      │        └───────────────┘           │
│  │ Pricing   │        │ Procedural    │                                    │
│  │ Research  │        │ Consolidation │                                    │
│  └───────────┘        └───────────────┘                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### Brain System (`skills/brain/`)

The brain system handles knowledge retrieval and response generation:

- **unified_retriever.py** - Hybrid search with Voyage + BM25
- **knowledge_ingestor.py** - Document processing pipeline
- **generate_answer.py** - LLM response generation
- **fact_checker.py** - Hallucination detection
- **dream_mode.py** - Nightly learning

### Memory System (`skills/memory/`)

Persistent memory across conversations:

- **brain_orchestrator.py** - Memory pipeline coordinator
- **unified_mem0.py** - Mem0 integration and identity
- **episodic_memory.py** - Conversation history
- **procedural_memory.py** - Learned workflows

### Channels

- **telegram_gateway.py** - Full-featured Telegram bot
- **email_handler.py** - Gmail integration

---

## Data Storage

### Qdrant Collections

| Collection | Dimension | Purpose |
|------------|-----------|---------|
| `ira_chunks_v4_voyage` | 1024 | Document embeddings |
| `ira_emails_voyage_v2` | 1024 | Email embeddings |
| `ira_dream_knowledge_v1` | 1024 | Dream-learned facts |
| `ira_user_memories_v2` | 1024 | User memories |
| `ira_entity_memories_v2` | 1024 | Entity memories |

### Local Storage

| Path | Content |
|------|---------|
| `data/knowledge/` | Processed knowledge base |
| `data/mem0_storage/` | Local memory backup |
| `data/identities.json` | Cross-channel identity map |
| `crm/*.db` | SQLite databases |

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `VOYAGE_API_KEY` | Yes | - | Voyage AI embeddings |
| `MEM0_API_KEY` | No | - | Mem0 memory service |
| `TELEGRAM_BOT_TOKEN` | Yes* | - | Telegram bot token |
| `EXPECTED_CHAT_ID` | Yes* | - | Authorized chat ID |
| `DATABASE_URL` | No | localhost | PostgreSQL URL |
| `QDRANT_URL` | Yes | localhost:6333 | Qdrant URL |
| `IRA_LOG_LEVEL` | No | INFO | Log verbosity |

*Required for Telegram functionality

### Feature Flags

```python
FEATURES = {
    "use_mem0": True,              # Enable Mem0 memory
    "use_voyage": True,            # Use Voyage embeddings
    "use_brain_orchestrator": True, # Cognitive pipeline
    "enable_proactive": True,      # Proactive outreach
    "use_postgres": True,          # PostgreSQL storage
    "hybrid_mode": True,           # Read from both stores
}
```

---

## CLI Commands

```bash
# Core operations
python orchestrator.py           # Start all services
python orchestrator.py --telegram # Telegram only
python orchestrator.py --cli     # Interactive mode

# Document operations
python openclaw/agents/ira/skills/brain/reindex_docs.py
python scripts/ingest_doc.py <path>

# Testing
python openclaw/agents/ira/skills/brain/unified_retriever.py "query"
```

---

## Contributing to Documentation

When updating documentation:

1. **Keep examples current** - Test code snippets
2. **Update the index** - Add new docs to this README
3. **Cross-reference** - Link related documents
4. **Add dates** - Note when major changes occur

---

*Last updated: February 2026*
