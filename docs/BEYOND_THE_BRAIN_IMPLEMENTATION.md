# Beyond the Brain: Implementation Status

This document tracks the implementation of the six-phase plan inspired by the article *"Beyond the Brain: The Surprising Bodily Systems That Contribute to Learning."*

---

## Completed Phases

### Phase 1: Immune System – Auto-Remediation ✅

**What was built:**
- **AM thickness fix**: Updated BUSINESS_RULES and truth_hints from ≤2mm to **≤1.5mm** (per Rushabh's correction)
- **Recurring issue detection**: `analyze_recurring_issues(threshold=3)` groups validation_issues by warning type
- **Auto-remediation loop**: When same issue appears 3+ times:
  - Adds canonical corrections to `correction_learner` (e.g. AM thickness)
  - Appends to `data/feedback_backlog.jsonl` for dream mode
  - Sends Telegram alert for urgent attention
  - Prunes validation_issues to last 50
- **Dream mode integration**: Phase 6.5 runs immune remediation nightly
- **CLI**: `python knowledge_health.py --remediate`

**Files changed:**
- `openclaw/agents/ira/src/brain/knowledge_health.py`
- `openclaw/agents/ira/src/brain/truth_hints.py`
- `openclaw/agents/ira/src/brain/dream_mode.py`

---

### Phase 2: Respiratory System – Heartbeat & Vital Signs ✅

**What was built:**
- **Vital signs script**: `scripts/ira_vital_signs.py` – aggregates:
  - Metabolic: Qdrant, OpenAI, Voyage, Mem0, Telegram status
  - Respiratory: Last dream run (from logs), age in hours
  - Immune: Knowledge health score, recurring issue count
  - Endocrine: Agent scores with success/failure counts
  - Musculoskeletal: Outreach sent today, queued count
- **Cron heartbeat**: `--alert-if-stale 36` exits 1 if dream hasn't run in 36 hours
- **Telegram report**: `--telegram` sends formatted report

**Usage:**
```bash
python scripts/ira_vital_signs.py
python scripts/ira_vital_signs.py --telegram
python scripts/ira_vital_signs.py --alert-if-stale 36  # For cron
```

---

### Phase 3: Endocrine System – Agent Scoring ✅

**What was built:**
- **Expanded `_identify_agents_used`** in feedback_handler.py:
  - Iris: triggered by "iris", "web", "lead", "enrich" in generation_path
  - Sophia: triggered by "reflect", "sophia", "lesson"
  - Full pipeline ("agent", "tool", "pipeline"): credits all agents including Iris, Sophia
- Positive/negative feedback now correctly attributes to Iris and Sophia when they participate

**Files changed:**
- `openclaw/agents/ira/src/brain/feedback_handler.py`

---

### Phase 4: Musculoskeletal – Action → Learning ✅

**What was built:**
- **Outreach action logging**: When proactive outreach sends successfully, appends to `data/feedback_backlog.jsonl` with `source: "outreach_sent"`
- Dream mode can consume these entries to learn which outreach patterns lead to engagement
- Extensible pattern: any CRM action (quote sent, follow-up made) can follow the same pattern

**Files changed:**
- `openclaw/agents/ira/src/conversation/proactive_outreach.py`

---

### Phase 5: Multisensory – Iris Activation ✅ (Partial)

**What was built:**
- **Identity → Iris bridge**: When the gateway resolves identity (contact_id), it now fetches the contact and passes `company` + `lead_id` to Iris. Iris can now enrich with lead intelligence when replying to known contacts (email, Telegram).
- **Files changed:** `unified_gateway.py` – populate context["company"] from identity before Iris enrich
- **Remaining (large):** Full Telegram migration off legacy gateway (~7k lines)

---

### Phase 6: Active Metabolism – Knowledge Hygiene ✅

**What was built:**
- **`knowledge_hygiene.py`**: Scans Qdrant chunks for hard rule violations (AM 2mm, PF1 thin, PF2 non-bath). Checks correction_learner consistency. Queues issues to feedback_backlog for dream mode / human review.
- **Dream mode integration**: Phase 6.6 runs knowledge hygiene nightly
- **CLI**: `python openclaw/agents/ira/src/brain/knowledge_hygiene.py`
- **Files:** `knowledge_hygiene.py`, `dream_mode.py`

---

## Quick Reference

| Phase | Status | Key Command / Location |
|-------|--------|------------------------|
| 1. Immune | ✅ | `knowledge_health.py --remediate` |
| 2. Respiratory | ✅ | `scripts/ira_vital_signs.py` |
| 3. Endocrine | ✅ | `feedback_handler.py` |
| 4. Musculoskeletal | ✅ | `proactive_outreach.py` → feedback_backlog |
| 5. Multisensory | ✅ (partial) | Iris gets company from identity; Telegram migration pending |
| 6. Metabolic | ✅ | `knowledge_hygiene.py` (Dream Phase 6.6) |

---

## Max Mode Extensions (2026-03-02)

| Extension | What |
|-----------|------|
| **hard_rules_hygiene.json** | Rules file at `data/brain/hard_rules_hygiene.json` – hygiene reads from here (fake IMG models, Batelaan, FRIMO). Sync when hard_rules.txt changes. |
| **Hygiene auto-remediation** | When AM thickness violations found, injects canonical fact into Mem0 (`machinecraft_knowledge`) so retrieval prefers correct answer. |
| **Memory decay in dream** | Phase 6.7 runs `unified_decay.decay_memories()` – PostgreSQL episodic/semantic memory decay. |
| **Company extraction for Iris** | `iris_skill._extract_company_from_message()` – when identity has no company, heuristically extracts from "to X", "at X", "for X" patterns. |
| **Agent scores in tool prompt** | `tool_orchestrator` injects agent confidence scores into Athena's system prompt – prefer higher-scoring agents for ambiguous tasks. |
| **Vague language filter** | `generate_answer.py` strips "approximately", "around", "typically" from pricing/spec contexts at generation time. Addresses the 27x hallucination_vague pattern. |
| **Telegram identity bridge** | Legacy `telegram_gateway.py` now resolves identity and passes `company` to agent context before calling `process_with_tools`. |
| **European drip in scheduler** | `scheduler.py` now runs `run_european_drip()` at 09:30 daily. Sends Telegram notification of leads ready for next drip email. |
| **Vital signs in scheduler** | `scheduler.py` runs `run_vital_signs()` at 07:30 daily. |
| **Launchd plists** | `scripts/com.machinecraft.ira-{dream,vitals,scheduler}.plist` + `install_schedules.sh` for macOS scheduling. |

## Launchd Schedule

| Time | Job | Plist |
|------|-----|-------|
| 2:00 AM | Dream mode (nightly learning) | `com.machinecraft.ira-dream.plist` |
| 7:30 AM | Vital signs (Telegram report) | `com.machinecraft.ira-vitals.plist` |
| 9:00 AM | Sales scheduler (outreach + drip + follow-up) | `com.machinecraft.ira-scheduler.plist` |

Install: `bash scripts/install_schedules.sh`
Remove: `bash scripts/install_schedules.sh remove`

---

## Testing

```bash
# Phase 1
cd /path/to/Ira
python openclaw/agents/ira/src/brain/knowledge_health.py --remediate

# Phase 2
python scripts/ira_vital_signs.py

# Phase 2 (cron heartbeat – fails if dream stale)
python scripts/ira_vital_signs.py --alert-if-stale 36
echo $?  # 1 if dream didn't run in 36h
```
