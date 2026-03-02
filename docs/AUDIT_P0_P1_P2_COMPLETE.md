# P0 / P1 / P2 Audit — Completion Checklist

**Status:** All items implemented.  
**Last updated:** 2026-03-03.

Use this to confirm nothing is left and all connections are in place.

---

## P0 — Critical (all done)

| # | Item | Where | Connection |
|---|------|--------|------------|
| 1 | Sync OpenAI → AsyncOpenAI + await | `tool_orchestrator.py` | All LLM calls use `await client.chat.completions.create` |
| 2 | Silent validation failure → log | `tool_orchestrator.py` | `logger.error` for knowledge_health, immune_system, voice_system |
| 3 | Tool execution timeout | `tool_orchestrator.py` | `asyncio.wait_for(execute_tool_call, timeout=TOOL_TIMEOUT_SECONDS)` |
| 4 | Hephaestus sandbox env leak | `analysis_tools.py` | Whitelist env for subprocess; `shutil.rmtree` for temp dir |
| 5 | Lock init race | `config.py` | `_pool_lock` and `_client_lock` initialized at module load |

---

## P1 — Fix soon (all done)

| # | Item | Where | Connection |
|---|------|--------|------------|
| 6 | Sync httpx → AsyncClient | `ira_skills_tools.py` | `_get_httpx_client()`, await in web_search + lead_intelligence |
| 7 | Messages list cap | `tool_orchestrator.py` | `MAX_MESSAGE_HISTORY`, trim at loop start |
| 8 | Postgres+Qdrant dual-write | `persistent_memory.py` | `_append_pending_embed()` on embed fail; **reconcile:** `reconcile_pending_qdrant_embeds.py` + `run_scheduled_tasks.py --task reconcile_embeds` / `--all` |
| 9 | SSRF via company/URL | `ira_skills_tools.py` | `_safe_domain()` before Jina URL |
| 10 | Qdrant client singleton | `ira_skills_tools.py`, `persistent_memory.py` | `get_qdrant_client()` from config |
| 11 | PersistentMemory pool | `persistent_memory.py` | `_with_db()` uses `get_db_connection()`; all DB ops use it |
| 12 | parse_tool_arguments on bad JSON | `ira_skills_tools.py` | `__parse_error__` dict; `execute_tool_call` returns error string |
| 13 | Atomic holistic state | All holistic modules | `atomic_write_json` / `append_jsonl` from config |
| 14 | Mem0 circuit breaker | `mem0_memory.py` | All client calls via `mem0_breaker.execute(..., fallback_result=...)` |

---

## P2 — Fix later (all done)

| # | Item | Where | Connection |
|---|------|--------|------------|
| 1 | Price table from machine_specs | `tool_orchestrator.py` | `_get_price_table_from_specs()` in system prompt; single source of truth |
| 2 | hard_rules in tool pipeline | `tool_orchestrator.py` | `_get_hard_rules()` appended to system prompt |
| 3 | Pending embeds reconciliation | `scripts/reconcile_pending_qdrant_embeds.py` | **Wired:** `run_scheduled_tasks.py --task reconcile_embeds` and run as first task in `--all` |
| 4 | Request ID in logs | `tool_orchestrator.py` | `request_id` in context; `log_prefix` in key log lines |

---

## Connections verified

- **Pending embeds path:** `persistent_memory._PENDING_EMBEDS_PATH` uses 6 parents (repo root) so it matches `data/brain/` next to `machine_specs.json`.
- **Reconciliation:** Run manually (`python3 scripts/reconcile_pending_qdrant_embeds.py`) or via scheduler (`run_scheduled_tasks.py --task reconcile_embeds` or `--all`).
- **Architecture rule:** `.cursor/rules/ira-architecture.mdc` updated for price table, hard_rules, and reconcile_embeds.

---

## What to run after changes

```bash
python3 scripts/benchy_deep.py --quick --telegram
```

(Requires `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.)
