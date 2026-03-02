# Ira Agent Architecture

## Overview

Ira is a unified AI agent for Machinecraft Technologies, providing intelligent assistance across multiple channels (Telegram, Email, API) with a sophisticated cognitive architecture.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              IRA AGENT v2.0                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐       │
│  │   TELEGRAM        │  │     EMAIL         │  │      API          │       │
│  │   Channel         │  │     Channel       │  │     Channel       │       │
│  └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘       │
│            │                      │                      │                  │
│            └──────────────────────┼──────────────────────┘                  │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         UNIFIED AGENT                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │  Identity   │  │   State     │  │   Config    │                  │   │
│  │  │  Resolution │  │   Manager   │  │   Manager   │                  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                  │   │
│  └─────────┼────────────────┼────────────────┼──────────────────────────┘   │
│            │                │                │                              │
│            └────────────────┼────────────────┘                              │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      BRAIN ORCHESTRATOR                              │   │
│  │                                                                      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ Memory   │ │ Episodic │ │Procedural│ │   Meta-  │ │ Conflict │  │   │
│  │  │ Trigger  │ │  Memory  │ │  Memory  │ │Cognition │ │ Resolver │  │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │   │
│  │       │            │            │            │            │         │   │
│  │       └────────────┴────────────┴────────────┴────────────┘         │   │
│  │                              │                                       │   │
│  │                              ▼                                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │   │
│  │  │ Memory   │  │ Memory   │  │Attention │  │ Feedback │             │   │
│  │  │ Weaver   │  │ Reasoner │  │ Manager  │  │ Learner  │             │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      RESPONSE GENERATION                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │   │
│  │  │   RAG    │  │Coreference│ │  Entity  │  │ Context  │             │   │
│  │  │Retrieval │  │Resolution │ │Extraction│  │  Pack    │             │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │   │
│  │                              │                                       │   │
│  │                              ▼                                       │   │
│  │                    ┌─────────────────┐                               │   │
│  │                    │ Generate Answer │                               │   │
│  │                    └─────────────────┘                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
openclaw/agents/ira/
├── __init__.py                 # Package exports
├── agent.py                    # Unified agent coordinator
├── core/
│   ├── __init__.py
│   └── state.py               # Agent state management
├── workspace/
│   └── agent_state.json       # Persistent state
└── skills/
    ├── brain/                 # Knowledge & RAG
    │   ├── generate_answer.py # Response generation
    │   ├── unified_retriever.py
    │   └── ...
    ├── memory/                # Cognitive memory
    │   ├── brain_orchestrator.py
    │   ├── persistent_memory.py
    │   ├── episodic_memory.py
    │   ├── procedural_memory.py
    │   ├── metacognition.py
    │   └── ...
    ├── conversation/          # Conversational AI
    │   ├── coreference.py
    │   ├── entity_extractor.py
    │   ├── emotional_intelligence.py
    │   └── ...
    ├── identity/              # Cross-channel identity
    │   └── unified_identity.py
    ├── telegram_channel/      # Telegram integration
    │   └── telegram_gateway.py
    └── email_channel/         # Email integration
        └── email_handler.py
```

## Core Components

### 1. IraAgent (`agent.py`)

The central coordinator that:
- Receives messages from all channels
- Resolves user identity across channels
- Coordinates brain processing
- Generates responses
- Records episodes

```python
from openclaw.agents.ira import get_agent

agent = get_agent()
response = agent.process(
    message="What's the price for PF1?",
    channel="telegram",
    user_id="123456"
)
```

### 2. BrainOrchestrator (`memory/brain_orchestrator.py`)

Unified cognitive pipeline that coordinates:
- **Memory Trigger**: When to retrieve memories
- **Semantic Memory**: Facts and preferences
- **Episodic Memory**: Past interactions
- **Procedural Memory**: Learned workflows
- **Meta-cognition**: Knowledge state assessment
- **Attention Manager**: Context prioritization
- **Feedback Learner**: Learning from outcomes

### 3. State Manager (`core/state.py`)

Persistent state management:
- Thread-safe updates
- Auto-save with debouncing
- Channel-specific state
- Cognitive state tracking

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_UNIFIED_AGENT` | Enable unified IraAgent for all channels | `false` |
| `VOYAGE_API_KEY` | Voyage AI embeddings key | - |
| `MEM0_API_KEY` | Mem0 memory service key | - |
| `OPENAI_API_KEY` | OpenAI API key for LLM | - |
| `QDRANT_URL` | Qdrant vector database URL | `localhost:6333` |

### Enabling Unified Agent Mode

To use the new unified IraAgent pipeline instead of legacy per-channel logic:

```bash
export USE_UNIFIED_AGENT=true
./ira start
```

When enabled, both Telegram and Email channels route through `IraAgent.process()` which provides:
- Consistent behavior across channels
- Shared cognitive state
- Unified memory and RAG retrieval
- SOUL.md identity integration

### 4. Unified Identity (`identity/unified_identity.py`)

Cross-channel identity resolution:
- Links telegram_id ↔ email ↔ phone
- Maintains contact metadata
- Enables unified memory across channels

## Message Processing Pipeline

```
1. RECEIVE MESSAGE
   ↓
2. RESOLVE IDENTITY
   - Look up cross-channel identity
   - Create new contact if needed
   ↓
3. GET CONVERSATION CONTEXT
   - Recent messages
   - Rolling summary
   - Key entities
   ↓
4. RESOLVE COREFERENCES
   - "it" → "PF1-1510"
   - "that machine" → "AM2500"
   ↓
5. EXTRACT ENTITIES
   - Machines, applications, materials
   ↓
6. BRAIN PROCESSING
   - Memory trigger (should retrieve?)
   - Semantic memory (facts)
   - Episodic memory (past events)
   - Procedural memory (workflows)
   - Meta-cognition (confidence)
   - Attention filtering
   ↓
7. RAG RETRIEVAL
   - Query knowledge base
   - Get relevant documents
   ↓
8. GENERATE RESPONSE
   - Build context pack
   - Call LLM with full context
   ↓
9. RECORD EPISODE
   - Store interaction in episodic memory
   ↓
10. RETURN RESPONSE
```

## Running Ira

### Using the Orchestrator (Recommended)

```bash
# Start all services
python orchestrator.py

# Telegram only
python orchestrator.py --telegram

# Interactive CLI
python orchestrator.py --cli

# Check status
python orchestrator.py --status
```

### Using the Agent Directly

```python
from openclaw.agents.ira import get_agent

agent = get_agent()

# Process message
response = agent.process(
    message="Tell me about PF1",
    channel="telegram",
    user_id="123"
)

# Check status
status = agent.get_status()

# Link identities
agent.link_identity("telegram", "123", "email", "user@example.com")
```

## Background Jobs

The orchestrator manages background jobs:

1. **Consolidation** (every 6 hours)
   - Episodic → Semantic memory transfer
   - Memory decay

2. **Proactive** (every 30 minutes)
   - Check for outreach candidates
   - Schedule follow-ups

## Configuration

Agent configuration via `AgentConfig`:

```python
from openclaw.agents.ira import AgentConfig, IraAgent

config = AgentConfig(
    name="Ira",
    version="2.0.0",
    enable_brain=True,
    enable_memory=True,
    enable_conversation=True,
    enable_rag=True,
    max_response_length=4000,
)

agent = IraAgent(config)
```

## Module Availability

The agent gracefully handles missing modules:

| Module | Purpose | Fallback |
|--------|---------|----------|
| Brain | Cognitive processing | Individual module calls |
| Memory | Persistent facts | No personalization |
| RAG | Knowledge retrieval | No document context |
| Conversation | Coreference, entities | Raw message |
| Identity | Cross-channel linking | Per-channel identity |

## Health Monitoring

```python
health = agent.get_health()
# AgentHealth(
#   state=ready,
#   uptime_seconds=3600,
#   requests_processed=150,
#   errors_count=2,
#   brain_healthy=True,
#   memory_healthy=True,
#   avg_response_time_ms=1200
# )
```

## Version History

- **v2.0.0** (2026-02-27)
  - Unified agent coordinator
  - Brain orchestrator integration
  - State management
  - Cross-channel identity
  
- **v1.x** (Legacy)
  - Separate telegram/email handlers
  - No unified cognitive pipeline
