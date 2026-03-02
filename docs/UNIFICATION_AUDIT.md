# Ira System Unification Audit

**Date**: 2026-02-27  
**Status**: AUDIT COMPLETE - ACTION REQUIRED

---

## Executive Summary

The Ira codebase has grown across multiple development sessions, resulting in:
- **Inconsistent tech stack usage** (connection strings, API keys, imports)
- **Duplicate implementations** across channels
- **Unified agent exists but not used** by any channel

This audit identifies all issues and provides a unification plan.

---

## 1. Tech Stack Inconsistencies

### 1.1 PostgreSQL Connection Strings (CRITICAL)

| File | Connection String |
|------|------------------|
| `market_research/*.py` | `postgresql://postgres:ira@localhost:5432/ira` |
| `customer_enricher.py` | `postgresql://ira:ira_password@localhost:5432/ira_db` |
| `docker-compose.yml` | `ira:ira_password@localhost:5432/ira_db` |
| `memory/*.py` | Uses `DATABASE_URL` env var |

**Issue**: 3 different credentials exist, none standardized.

**Fix**: Standardize to `DATABASE_URL` environment variable everywhere.

### 1.2 Qdrant Collection Naming (HIGH)

| Collection Pattern | Files |
|-------------------|-------|
| `ira_chunks_voyage_v2` | unified_retriever.py |
| `ira_chunks_v4_voyage` | qdrant_retriever.py, reindex_docs.py |
| `ira_emails_voyage_v3` | email_reindex.py |
| `ira_emails_voyage_v2` | reindex_emails.py, unified_retriever.py |

**Issue**: Version suffixes inconsistent (v2, v3, v4).

**Fix**: Define canonical collection names in a config module.

### 1.3 API Client Initialization (MEDIUM)

```
# Pattern 1 (recommended)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Pattern 2 (some files)
client = OpenAI()  # relies on OPENAI_API_KEY env var

# Pattern 3 (some files)  
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
```

**Fix**: Standardize on Pattern 1.

### 1.4 Import Patterns (MEDIUM)

- Mix of relative (`from .module`) and direct (`from module`) imports
- Some files use try/except, others don't
- Mem0 imports vary: `mem0_memory` vs `from .mem0_memory`

**Fix**: All modules should use try/except pattern for both import styles.

---

## 2. Channel Integration Issues

### 2.1 Current State

| Channel | Uses IraAgent? | Uses BrainOrchestrator? | Uses Mem0? |
|---------|---------------|------------------------|-----------|
| telegram_channel | ❌ NO | ✅ YES | ✅ YES |
| email_channel | ❌ NO | ❌ NO | ✅ YES |

### 2.2 Duplicate Code

Both channels implement nearly identical:
- Memory retrieval (Mem0 + PostgreSQL fallback)
- Conversational enhancement (Replika integration)
- Entity extraction
- Coreference resolution
- Feedback learning
- Response generation

**This duplicates ~500+ lines of code across channels.**

### 2.3 email_channel Missing BrainOrchestrator

`email_handler.py` has a 15-step manual orchestration that should use `BrainOrchestrator`:

```python
# Current (manual orchestration)
def process_email(self, email_data):
    # 1. Correction detection
    # 2. Identity extraction  
    # 3. Coreference resolution
    # 4. Entity extraction
    # 5. Memory retrieval
    # ... 10 more steps manually wired

# Should be (unified)
def process_email(self, email_data):
    agent = get_agent()
    return agent.process_email(
        body=email_data.body,
        from_email=email_data.from_email,
        subject=email_data.subject
    )
```

### 2.4 gmail_intake Ghost References

Files referenced in `start_ira.sh` but don't exist:
- `gmail_intake/gmail_push.py`
- `gmail_intake/skill.py`

**Fix**: Either implement or remove references.

---

## 3. Unified Agent Analysis

### 3.1 What IraAgent Provides

```
IraAgent.process()
├── Identity resolution (cross-channel)
├── Conversation context
├── Coreference resolution
├── Entity extraction
├── BrainOrchestrator processing
│   ├── Memory trigger
│   ├── Semantic memory (Mem0)
│   ├── Episodic memory
│   ├── Procedural memory
│   ├── Meta-cognition
│   └── Attention filtering
├── RAG retrieval (Qdrant)
├── Response generation
├── Episode recording
└── State persistence
```

### 3.2 What Channels Should Do

```python
# Telegram (ideal)
from openclaw.agents.ira import get_agent

agent = get_agent()
response = agent.process_telegram(message, chat_id)
send_telegram_message(response.message)

# Email (ideal)
response = agent.process_email(body, from_email, subject)
send_email_response(response.message)
```

---

## 4. Missing Integrations

### 4.1 SOUL.md Not Integrated

`/Users/rushabhdoshi/.openclaw/workspace/SOUL.md` defines Ira's:
- Identity and role
- Communication style
- Knowledge domain
- Safety guidelines

**Issue**: This is not loaded into the agent or system prompt.

**Fix**: Load SOUL.md into response generation context.

### 4.2 OpenClaw Integration

No evidence of OpenClaw framework integration beyond:
- Path: `openclaw/agents/ira/`
- Some tool references in SOUL.md (`ira_query`, `ira_pricing`)

**Issue**: OpenClaw tools not implemented.

---

## 5. Unification Plan

### Phase 1: Config Standardization (Quick Wins)

1. Create `openclaw/agents/ira/config.py`:
   ```python
   # Centralized configuration
   DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ira:ira_password@localhost:5432/ira_db")
   QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
   
   # Collection names
   COLLECTIONS = {
       "chunks_voyage": "ira_chunks_voyage_v3",
       "emails_voyage": "ira_emails_voyage_v3",
       "market_research": "ira_market_research_voyage",
   }
   ```

2. Update all files to import from config

### Phase 2: Channel Unification

1. Update `telegram_gateway.py`:
   - Replace direct module calls with `IraAgent.process_telegram()`
   - Keep Telegram-specific UI handling

2. Update `email_handler.py`:
   - Replace 15-step manual orchestration with `IraAgent.process_email()`
   - Keep email-specific formatting

### Phase 3: SOUL Integration

1. Load SOUL.md at agent initialization
2. Include in system prompt generation
3. Use for identity verification

### Phase 4: OpenClaw Tools

1. Implement `ira_query` tool
2. Implement `ira_pricing` tool
3. Implement `ira_company_lookup` tool
4. Implement `ira_draft_email` tool

---

## 6. Files Requiring Changes

### High Priority (Config Standardization)
- [x] `CREATE: openclaw/agents/ira/config.py` ✅ DONE
- [x] `UPDATE: scripts/store_market_research.py` - use config ✅
- [x] `UPDATE: customer_enricher.py` - use config ✅
- [x] `UPDATE: unified_retriever.py` - use config ✅
- [x] `UPDATE: qdrant_retriever.py` - use config ✅

### Medium Priority (Channel Unification) ✅ COMPLETED
- [x] `UPDATE: telegram_gateway.py` - use IraAgent (via USE_UNIFIED_AGENT flag)
- [x] `UPDATE: email_handler.py` - use IraAgent + BrainOrchestrator (via USE_UNIFIED_AGENT flag)
- [x] `UPDATE: email_conversation_loop.py` - use IraAgent (via USE_UNIFIED_AGENT flag)

### Lower Priority (Feature Completion) ✅ COMPLETED
- [x] `UPDATE: agent.py` - load SOUL.md ✅ DONE
- [x] `UPDATE: generate_answer.py` - use SOUL.md ✅ DONE
- [x] `CREATE: openclaw/agents/ira/tools/` - OpenClaw tools ✅ (query, email, research, customer)
- [x] `CLEANUP: start_ira.sh` - updated gmail_intake → email_channel ✅

---

## 7. Recommended Tech Stack

| Component | Technology | Status |
|-----------|------------|--------|
| **Embeddings** | Voyage AI (voyage-3) | ✅ Primary |
| **Vector DB** | Qdrant | ✅ Implemented |
| **User Memory** | Mem0 | ✅ Primary |
| **Episodic Memory** | PostgreSQL | ✅ Implemented |
| **LLM** | OpenAI (gpt-4) | ✅ Implemented |
| **Orchestration** | BrainOrchestrator | ⚠️ Partial (email missing) |
| **Agent Interface** | IraAgent | ⚠️ Not used by channels |
| **State** | AgentStateManager | ✅ Implemented |

---

## Appendix: Environment Variables

Standardized `.env` template:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Voyage AI (embeddings)
VOYAGE_API_KEY=pa-...

# Mem0 (user memory)
MEM0_API_KEY=m0-...

# PostgreSQL
DATABASE_URL=postgresql://ira:ira_password@localhost:5432/ira_db

# Qdrant
QDRANT_URL=http://localhost:6333

# Telegram
TELEGRAM_BOT_TOKEN=...
EXPECTED_CHAT_ID=...
```
