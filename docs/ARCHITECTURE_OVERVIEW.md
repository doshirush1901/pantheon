# Ira Architecture Overview

This document provides a comprehensive overview of Ira's architecture, explaining how all the components work together to create an intelligent sales assistant.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [Deployment Architecture](#deployment-architecture)

---

## System Overview

Ira is a multi-channel AI sales assistant designed to help Machinecraft Technologies with:

- **Customer Communication**: Respond to inquiries via Telegram and Email
- **Knowledge Retrieval**: Find relevant information from company documents
- **Lead Management**: Qualify leads and track customer interactions
- **Email Drafting**: Generate professional sales emails with context

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    IRA SYSTEM                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                           INPUT CHANNELS                                     │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                    │   │
│  │  │   Telegram    │  │     Email     │  │      API      │                    │   │
│  │  │    Gateway    │  │    Handler    │  │    Server     │                    │   │
│  │  │  (Real-time)  │  │   (Polling)   │  │  (On-demand)  │                    │   │
│  │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘                    │   │
│  │          │                  │                  │                             │   │
│  │          └──────────────────┼──────────────────┘                             │   │
│  └─────────────────────────────┼───────────────────────────────────────────────┘   │
│                                │                                                    │
│                                ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         UNIFIED AGENT                                        │   │
│  │                                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │   │
│  │  │  Identity   │  │   State     │  │  Request    │  │   Config    │        │   │
│  │  │ Resolution  │  │  Manager    │  │   Router    │  │  Manager    │        │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │   │
│  │                                                                              │   │
│  └─────────────────────────────┬───────────────────────────────────────────────┘   │
│                                │                                                    │
│                                ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                      BRAIN ORCHESTRATOR                                      │   │
│  │                                                                              │   │
│  │  ┌───────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                     COGNITIVE PIPELINE                                 │  │   │
│  │  │                                                                        │  │   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │  │   │
│  │  │  │ Memory  │ │Episodic │ │Procedural│ │  Meta-  │ │Attention│         │  │   │
│  │  │  │ Trigger │→│ Memory  │→│  Memory │→│Cognition│→│ Manager │         │  │   │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘         │  │   │
│  │  │                                                                        │  │   │
│  │  └───────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                              │   │
│  │  ┌───────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                     RAG RETRIEVAL                                      │  │   │
│  │  │                                                                        │  │   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                      │  │   │
│  │  │  │ Vector  │ │  BM25   │ │  Fusion │ │ Rerank  │                      │  │   │
│  │  │  │ Search  │→│ Search  │→│  (RRF)  │→│FlashRank│                      │  │   │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘                      │  │   │
│  │  │                                                                        │  │   │
│  │  └───────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                              │   │
│  └─────────────────────────────┬───────────────────────────────────────────────┘   │
│                                │                                                    │
│                                ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                      RESPONSE GENERATION                                     │   │
│  │                                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │   │
│  │  │  Context    │  │    LLM      │  │    Fact     │  │  Response   │        │   │
│  │  │   Pack      │→ │  Generate   │→ │   Check     │→ │  Format     │        │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         INFRASTRUCTURE                                       │   │
│  │                                                                              │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                    │   │
│  │  │    Qdrant     │  │     Mem0      │  │  PostgreSQL   │                    │   │
│  │  │   (Vectors)   │  │   (Memory)    │  │  (Optional)   │                    │   │
│  │  │               │  │               │  │               │                    │   │
│  │  │ • Documents   │  │ • User facts  │  │ • Relations   │                    │   │
│  │  │ • Emails      │  │ • Entities    │  │ • Analytics   │                    │   │
│  │  │ • Memories    │  │ • Episodes    │  │ • Logs        │                    │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘                    │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Input Channels

#### Telegram Gateway (`telegram_gateway.py`)
- Real-time message handling via long polling
- Rich message formatting with inline buttons
- Conversation state management
- File upload/download support

#### Email Handler (`email_handler.py`)
- Gmail API integration via OAuth2
- Thread-based conversation tracking
- Automatic email parsing and extraction
- Draft generation and sending

### 2. Unified Agent (`agent.py`)

The central coordinator that:

```python
class IraAgent:
    def process(self, message: str, channel: str, user_id: str) -> str:
        # 1. Resolve user identity across channels
        identity = self.resolve_identity(user_id, channel)
        
        # 2. Get conversation context
        context = self.get_context(identity)
        
        # 3. Process through brain orchestrator
        brain_output = self.brain.process(message, context)
        
        # 4. Generate response
        response = self.generate(brain_output)
        
        # 5. Record episode
        self.record_episode(identity, message, response)
        
        return response
```

### 3. Brain Orchestrator (`brain_orchestrator.py`)

Coordinates the cognitive pipeline:

| Stage | Module | Function |
|-------|--------|----------|
| Memory Trigger | `memory_trigger.py` | Decides when to retrieve memories |
| Episodic Memory | `episodic_memory.py` | Retrieves past conversations |
| Semantic Memory | `persistent_memory.py` | Retrieves facts and preferences |
| Procedural Memory | `procedural_memory.py` | Applies learned workflows |
| Meta-cognition | `metacognition.py` | Assesses knowledge confidence |
| Attention | `memory_weaver.py` | Prioritizes relevant context |

### 4. RAG System (`unified_retriever.py`)

Hybrid retrieval combining multiple strategies:

```
Query → [Vector Search] ─┐
                         ├→ [RRF Fusion] → [FlashRank Rerank] → Results
Query → [BM25 Search]  ──┘
```

**Vector Search**: Voyage AI embeddings (1024 dimensions) stored in Qdrant
**BM25 Search**: Keyword-based search for exact matches
**Fusion**: Reciprocal Rank Fusion combines results
**Reranking**: FlashRank cross-encoder improves relevance

### 5. Response Generation

```python
def generate_answer(query: str, context: List[str], memory: str) -> str:
    prompt = f"""
    You are Ira, the AI sales assistant for Machinecraft Technologies.
    
    MEMORY:
    {memory}
    
    CONTEXT:
    {context}
    
    USER QUERY: {query}
    
    Respond helpfully based on the context provided.
    """
    
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content
```

---

## Data Flow

### Message Processing Flow

```
1. User sends message (Telegram/Email)
           │
           ▼
2. Channel handler receives message
           │
           ▼
3. Identity resolution (cross-channel linking)
           │
           ▼
4. Context retrieval:
   ├── Conversation history
   ├── User memories
   └── Entity memories
           │
           ▼
5. Coreference resolution ("it" → "PF1-3020")
           │
           ▼
6. Entity extraction (machines, companies, materials)
           │
           ▼
7. RAG retrieval:
   ├── Vector search (semantic similarity)
   ├── BM25 search (keyword matching)
   └── Fusion + reranking
           │
           ▼
8. Context packing (memory + RAG results)
           │
           ▼
9. LLM generation (GPT-4o)
           │
           ▼
10. Fact checking (hallucination guard)
           │
           ▼
11. Response formatting (channel-specific)
           │
           ▼
12. Episode recording (for future memory)
           │
           ▼
13. Response sent to user
```

### Knowledge Ingestion Flow

```
1. Document placed in data/imports/
           │
           ▼
2. Document extraction:
   ├── PDF → pdfplumber
   ├── Excel → openpyxl
   └── Word → python-docx
           │
           ▼
3. Text chunking (semantic boundaries)
           │
           ▼
4. Embedding generation (Voyage AI)
           │
           ▼
5. Storage in Qdrant (with metadata)
           │
           ▼
6. Knowledge graph update (entities, relationships)
```

### Memory Consolidation Flow (Dream Mode)

```
1. Nightly trigger (scheduled or manual)
           │
           ▼
2. Review recent episodes
           │
           ▼
3. Extract key facts and patterns
           │
           ▼
4. Check for conflicts with existing knowledge
           │
           ▼
5. Consolidate into semantic memory
           │
           ▼
6. Apply decay to old memories
           │
           ▼
7. Update knowledge graph
```

---

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Language** | Python | 3.10+ | Core runtime |
| **LLM** | OpenAI GPT-4o | - | Response generation |
| **Embeddings** | Voyage AI | voyage-3 | 1024-dim vectors |
| **Vector DB** | Qdrant | 1.7+ | Similarity search |
| **Memory** | Mem0 | - | Long-term memory |
| **Reranking** | FlashRank | 0.2+ | Result optimization |
| **Database** | PostgreSQL | 15+ | Relational data (optional) |

### Integration Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Telegram** | python-telegram-bot 20+ | Bot framework |
| **Email** | Gmail API + OAuth2 | Email integration |
| **Documents** | pdfplumber, openpyxl | Document extraction |
| **NLP** | scikit-learn | BM25 implementation |
| **API** | FastAPI | REST API server |

### Infrastructure

```yaml
# docker-compose.yml services
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ira_db
      POSTGRES_USER: ira
      POSTGRES_PASSWORD: ira_password
    ports:
      - "5432:5432"
```

---

## Deployment Architecture

### Local Development

```
┌─────────────────────────────────────────────┐
│              Local Machine                   │
│                                             │
│  ┌─────────────┐    ┌─────────────┐        │
│  │   Python    │    │   Docker    │        │
│  │   (.venv)   │    │  Compose    │        │
│  │             │    │             │        │
│  │ orchestrator│    │ • Qdrant    │        │
│  │ telegram_gw │    │ • Postgres  │        │
│  │ email_hdlr  │    │             │        │
│  └─────────────┘    └─────────────┘        │
│                                             │
└─────────────────────────────────────────────┘
          │
          │ API Calls
          ▼
┌─────────────────────────────────────────────┐
│           External Services                  │
│                                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ OpenAI  │ │ Voyage  │ │  Mem0   │       │
│  └─────────┘ └─────────┘ └─────────┘       │
│                                             │
│  ┌─────────┐ ┌─────────┐                   │
│  │Telegram │ │  Gmail  │                   │
│  │   API   │ │   API   │                   │
│  └─────────┘ └─────────┘                   │
└─────────────────────────────────────────────┘
```

### Production Deployment

For production, consider:

1. **Process Management**: systemd or supervisor for service reliability
2. **Monitoring**: Application logs + health endpoints
3. **Secrets**: Environment variables or secrets manager
4. **Backup**: Regular Qdrant snapshots and database backups
5. **Scaling**: Single instance is typically sufficient for this use case

---

## Key Design Decisions

### 1. Hybrid Search over Pure Vector
**Reason**: Vector search alone misses exact keyword matches (e.g., model numbers like "PF1-3020"). BM25 complements with keyword precision.

### 2. Voyage over OpenAI Embeddings
**Reason**: Voyage-3 provides better retrieval quality at lower cost with no rate limits. 1024 dimensions is sufficient for this domain.

### 3. Mem0 for Memory
**Reason**: Purpose-built for conversational memory with automatic deduplication and semantic search. Reduces complexity vs. custom implementation.

### 4. FlashRank for Reranking
**Reason**: Lightweight cross-encoder that runs locally (no API calls). Significantly improves result relevance without latency penalty.

### 5. Modular Skill Architecture
**Reason**: Each capability (email drafting, pricing, research) is a separate module. Enables independent testing and deployment.

---

## Future Considerations

1. **Multi-tenant Support**: Currently single-user; could add organization isolation
2. **Streaming Responses**: For long responses in chat interfaces
3. **Voice Channel**: Integration with phone/voice systems
4. **Analytics Dashboard**: Web UI for monitoring and insights
5. **Fine-tuned Models**: Domain-specific models for better performance

---

*Last updated: February 2026*
