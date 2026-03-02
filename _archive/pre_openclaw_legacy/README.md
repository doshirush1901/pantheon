# Pre-OpenClaw Legacy Archive

These files were the original orchestration layer before IRA was migrated to the OpenClaw framework.

They are kept here for reference only. They are NOT used by the current system.

## Fully Archived (Archived 2026-02-28)

| File | Original Purpose | Replaced By |
|------|-----------------|-------------|
| `orchestrator.py` | Main entry point, started all services | OpenClaw CLI (`openclaw run ira`) + `ChiefOfStaffAgent` |
| `telegram_gateway.py` | Telegram bot connection and message handling | OpenClaw Telegram channel adapter |
| `email_handler.py` | Gmail IMAP polling and email processing | OpenClaw Email channel adapter |
| `config.py` | Centralized configuration and API keys | `openclaw/agents/ira/config.py` |

## Current Architecture (Multi-Agent System)

The system has evolved through multiple iterations:

1. **v1.0:** Monolithic `orchestrator.py` + channel handlers
2. **v2.0:** `BrainOrchestrator` (14 phases, 1600+ lines) - NOW DEPRECATED
3. **v3.0:** 4-Pipeline system - NOW ARCHIVED (see `_archive/legacy_pipelines/`)
4. **v4.0 (CURRENT):** Multi-Agent System

### Current Entry Point

```python
from src.agents import get_chief_of_staff

cos = get_chief_of_staff()
response = await cos.process_message(message, user_id, channel)
```

### Current Agent Architecture

| Agent | Location | Purpose |
|-------|----------|---------|
| `ChiefOfStaffAgent` | `src/agents/chief_of_staff/` | Orchestration & planning |
| `ResearcherAgent` | `src/agents/researcher/` | Knowledge retrieval |
| `WriterAgent` | `src/agents/writer/` | Content generation |
| `FactCheckerAgent` | `src/agents/fact_checker/` | Validation |
| `ReflectorAgent` | `src/agents/reflector/` | Learning & improvement |

---

## Technical Debt Notice

See `/TECHNICAL_DEBT.md` for a complete audit of architectural debt inherited from these legacy systems.
