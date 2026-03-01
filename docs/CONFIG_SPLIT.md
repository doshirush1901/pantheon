# IRA Configuration Split (P4)

## Overview

IRA uses multiple configuration sources. This document clarifies where each setting lives.

## Configuration Sources

| Source | Purpose | Location |
|--------|---------|----------|
| **openclaw.json** | OpenClaw workspace, bootstrap | `~/.openclaw/openclaw.json` (created by `setup_openclaw.sh`) |
| **config.py** | IRA runtime config: models, Mem0, Qdrant, features | `openclaw/agents/ira/config.py` |
| **.env** | Secrets, API keys, env-specific overrides | Project root `.env` |
| **AGENTS.md** | Agent persona, skills, rules | Project root |

## openclaw.json

Minimal config created by `setup_openclaw.sh`:
```json
{
  "agent": {
    "workspace": "/path/to/Ira",
    "skipBootstrap": true
  }
}
```

No model allowlist, channel adapters, or memory settings here.

## config.py

- `OPENAI_API_KEY`, `MEM0_API_KEY`, `QDRANT_URL`
- `FEATURES["use_mem0"]`, `FEATURES["use_postgres"]`
- Model names, collection names

## .env

- `OPENAI_API_KEY`, `JINA_API_KEY`, etc.
- Loaded by startup scripts and `run_with_env.sh` (for launchd/cron)
