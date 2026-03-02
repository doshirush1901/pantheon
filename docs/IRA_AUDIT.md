# IRA — Multi-Dimensional Agentic Architecture Audit
## A Philosopher's Critique of a Living System

**Auditor:** Agentic Systems Architect | **Date:** March 2026
**Scope:** Full-stack audit across 7 dimensions — pipeline, memory, agents, biology, safety, research, learning
**Methodology:** Source code analysis of every critical module, compared against state-of-art systems (Manus, Devin, Perplexity, OpenAI Swarm, MemGPT)

---

## Executive Summary

Ira is an ambitious system that attempts something rare: a biologically-modeled, self-correcting AI agent with genuine memory, learning, and multi-agent coordination. It gets many things right — the immune system is real, the voice system earns its complexity, the Nemesis correction loop is architecturally sound, and the defense-in-depth philosophy is correct.

But the system has a **structural disease**: it was designed top-down as a complete organism, then implemented bottom-up one organ at a time. The result is that some organs are fully wired (immune, voice), some collect data into a void (endocrine, sensory, respiratory), and the connections between them are weaker than the architecture diagrams suggest.

The most dangerous findings are not in the obvious places. The injection guard is fine. The tool loop is bounded. The real risks are:

1. **The Hephaestus sandbox is not a sandbox** — it's a subprocess with full system access
2. **Dream mode can permanently corrupt the knowledge base** with no rollback
3. **Contradictory facts persist across memory stores** with no reconciliation
4. **Synchronous HTTP in async context** serializes what should be parallel, adding 30-60s of unnecessary latency
5. **Three of seven biological systems are decorative** — they record data that nothing reads

**Overall grade: B-**. The architecture is thoughtful and the vision is correct. The implementation is ~60% of the way there. The remaining 40% is the difference between a prototype and a production system.

---

## Dimension 1: Core Pipeline

### What Works

- **Tool loop is bounded** at 25 rounds with a graceful fallback (`tool_choice="none"` summary call). This prevents infinite loops.
- **Minimum research depth** nudges the LLM to dig deeper on complex queries (5 rounds, 3 unique tools). This is a good idea.
- **Context compaction** exists — old tool results are truncated when the context approaches the token budget. The concept is sound.
- **Proposal checkpoint** at round 12 for sales inquiries prevents premature responses.

### What's Broken

#### P0: Synchronous HTTP in Async Context (5 call sites)

The `web_search` and `lead_intelligence` tools use **synchronous `httpx.post()`** inside `async` functions:

```python
# ira_skills_tools.py — 5 occurrences
resp = httpx.post("https://api.tavily.com/search", json={...}, timeout=20)
resp = httpx.get(f"https://google.serper.dev/search", headers={...}, timeout=15)
```

When GPT-4o requests parallel tool calls (which the system prompt encourages), these serialize on the event loop. A `web_search` that calls Tavily (20s) + Serper (15s) + Jina (15s) sequentially takes 50s — exceeding the 45s `TOOL_TIMEOUT_SECONDS`. The timeout kills the tool mid-execution, and partial results (Tavily succeeded, Serper didn't run) are lost entirely.

**Impact:** 30-60s of unnecessary latency on every complex query. Parallel tool calls don't actually run in parallel.

**Fix:** Use `httpx.AsyncClient` or wrap in `asyncio.to_thread()`. Run Tavily/Serper/Jina concurrently with `asyncio.gather()`.

#### P1: No Cost Tracking or Budget Circuit Breaker

A single complex request can trigger 25 rounds of GPT-4o calls plus Tavily + Serper + Jina. Estimated cost: $1-3 per request. There is no tracking, no budget limit, no circuit breaker. A user asking "Research everything about the European vacuum forming market" could trigger $5+ in API costs with no visibility.

**Comparison:** Manus tracks token consumption per request and has a hard budget. Devin shows cost estimates before execution.

#### P1: Tool-to-Agent Map Duplicated and Out of Sync

The mapping of tools to Pantheon agents exists in **two places** that have diverged:

| Location | Entries | Missing |
|----------|---------|---------|
| `tool_orchestrator.py` L92 | 16 tools | Gmail (5), Nemesis, Quotebuilder, memory_search |
| `ira_skills_tools.py` L469 | 22 tools | — |

The orchestrator's map drives `_signal_tool_outcome()` (endocrine scoring). Because 6 tools are missing, the endocrine system never scores Gmail, Nemesis, Quotebuilder, or memory operations. These agents are invisible to the feedback loop.

#### P2: Context Window Estimation Ignores ~8K Tokens of Overhead

The token estimator uses 3.5 chars/token (reasonable for prose) but doesn't account for:
- Tool schemas: ~3,000-5,000 tokens for 28 tools
- System prompt: ~4,000 tokens
- JSON tool results: 2-2.5 chars/token (denser than prose)

This means compaction triggers too late. The actual context can overflow before `_compact_tool_results` kicks in.

#### P2: Tool Result Truncation is Blind

```python
# tool_orchestrator.py L1076
"content": (result or "")[:16000],
```

Hard truncation at 16K chars with no marker. If a finance report is 20KB, the last 4KB vanishes. For CRM lookups, Mnemosyne's "recommendation" section (typically at the end) gets cut. The LLM doesn't know data was lost.

**Fix:** `result[:15800] + "\n\n[...TRUNCATED — full result was {len(result)} chars]"`. Consider tail-preserving truncation (first 8K + last 8K).

#### P2: 10 Silent `except Exception: pass` Blocks

Across `tool_orchestrator.py` and `ira_skills_tools.py`, there are 10 bare exception handlers that swallow errors silently. The worst: if Qdrant is down, `research_skill` returns sparse results with no indication that the primary knowledge base is unreachable.

#### P3: No Re-Planning on Tool Failure

When a tool throws, the error string is injected into the conversation. The LLM must improvise recovery. There is no structured fallback mechanism.

**Comparison:** Manus has an explicit `plan -> execute -> observe -> re-plan` loop. When a tool fails, the planner generates an alternative strategy. Devin maintains a task dependency graph and re-routes around failures.

#### P3: Research Nudge Has No Max-Fire Counter

The "dig deeper" nudge can fire up to 5 times consecutively if GPT-4o keeps producing shallow responses. Each nudge burns an LLM call (~$0.03-0.10) with no new information gained.

---

## Dimension 2: Memory Architecture

### What Works

- **Multi-layer memory** (Mem0, Qdrant, Neo4j, CRM, truth hints) is architecturally sound. The separation of semantic, retrieval, structural, and episodic memory mirrors cognitive science.
- **Reranking** with FlashRank (ms-marco-MiniLM-L-12-v2) after retrieval improves result quality.
- **Embedding consistency** — Voyage-3 is used consistently for ingest and query on primary collections.

### What's Broken

#### P0: Contradictory Facts Persist Across Stores With No Reconciliation

A fact can exist in three different states simultaneously:

1. **Mem0:** Nemesis stores correction `"Dutch Tides only has 2 Cr pending"`
2. **Qdrant (`ira_chunks_v4_voyage`):** Original document chunk `"Dutch Tides outstanding: ₹5.37 Cr"`
3. **Qdrant (`ira_discovered_knowledge`):** Sleep trainer indexes the correction

The original wrong data in `ira_chunks_v4_voyage` is **never deleted or updated**. Both collections are searched. The LLM receives both the wrong data and the correction simultaneously and must resolve the contradiction on its own.

The only defense is the system prompt's "LEARNED CORRECTIONS" section — a soft signal, not a hard override.

**Fix:** When Nemesis ingests a correction with an entity reference, search Qdrant for conflicting chunks and either delete them or add a metadata flag `{"superseded_by": correction_id}` that the retriever filters on.

#### P1: `UnifiedMem0Service` Is Dead Code

There are **two competing Mem0 singletons**:

| Service | Used By | Features |
|---------|---------|----------|
| `Mem0MemoryService` (`mem0_memory.py`) | **All production code** — Clio, Nemesis, sleep trainer, orchestrator | Basic search/store |
| `UnifiedMem0Service` (`unified_mem0.py`) | **Nothing in production** — only dream_mode, memory_controller (identity only) | Identity resolution, relationship extraction, graph metadata |

The `UnifiedMem0Service` has identity resolution, relationship extraction, and a graph-like metadata system — all unused. Its in-memory relationship graph (`self._relationships`) is a `defaultdict` that is **never persisted** and lost on restart.

**Impact:** The identity resolution that would let Ira recognize the same customer across email and Telegram is built but not wired in.

#### P1: Dream/Discovered/Market Research Collections Disappear When Voyage AI Is Down

In `unified_retriever.py`, the dream, discovered, and market research collections are **only searched when `provider == "voyage"`**. If Voyage AI is down and OpenAI embeddings are used as fallback, all dream-learned knowledge, discovered knowledge, and market research data becomes invisible.

```python
# unified_retriever.py L762 — gated on provider
if provider == "voyage":
    # search ira_discovered_knowledge, ira_dream_knowledge_v1, ira_market_research_voyage
```

#### P2: Nemesis Corrections Silently Overwrite Each Other

The correction store deduplicates on `(entity, category)`. If two corrections arrive for the same entity and category with different `correct_info`, the second overwrites the first:

```python
# correction_store.py L131-145
existing = conn.execute(
    "SELECT id FROM corrections WHERE entity = ? AND category = ? AND applied = 0 ...",
    (entity, category),
).fetchone()
if existing:
    conn.execute("UPDATE corrections SET correct_info = ? WHERE id = ?",
                 (correct_info, existing["id"]))
```

No conflict detection. No history. The first correction's `correct_info` is lost.

#### P2: Clio's 5-Minute Cache Is Never Invalidated by Nemesis

Clio caches research results for 5 minutes in a plain dict. When Nemesis ingests a correction, Clio's cache is not invalidated. A user who triggers a correction and immediately re-asks the question gets the stale cached answer.

#### P3: Pre-Reranking Score Threshold Eliminates Potentially Good Results

`qdrant_retriever.py` applies a minimum score threshold **before** reranking. A chunk with low vector similarity but high lexical relevance is filtered out before the reranker ever sees it.

---

## Dimension 3: Agent Coordination

### What Works

- **Hub-and-spoke model** (Athena dispatches, agents return) is simple and debuggable.
- **Post-pipeline verification** (Vera + Sophia) catches issues before the user sees the response.
- **Nemesis feedback loop** (Telegram corrections -> Mem0 -> sleep training -> truth hints) is a genuine learning cycle.

### What's Broken

#### P1: No Agent-to-Agent Communication

The architecture is strictly hub-and-spoke. There is no mechanism for:
- Clio to tell Vera "this came from a low-confidence source — verify carefully"
- Vera to ask Clio for more evidence when verification fails
- Nemesis to invalidate Clio's cache when a correction is ingested

Every agent returns a string to Athena. Provenance, confidence, and source metadata are lost in the string serialization. By the time the LLM synthesizes, it cannot distinguish a fact from Qdrant (high confidence) from a fact from a web scrape (low confidence).

**Comparison:** OpenAI Swarm passes structured `Result` objects between agents with metadata. CrewAI has explicit agent-to-agent delegation. Manus maintains a shared workspace with typed artifacts.

#### P2: Vera Runs Post-Hoc — Cannot Trigger Re-Research

Vera fact-checks **after** Athena's tool loop completes. If she flags an issue, the response has already been generated. She can only:
1. Log the issue
2. Feed it to Nemesis (helps future queries)
3. Feed it to the immune system (helps if it recurs)

But the current response goes out with the error. There is no mechanism for Vera to say "this price looks wrong — go back and check `machine_specs.json`."

**Fix:** Move Vera into the tool loop as a verification tool that Athena can call mid-research, not just post-pipeline.

#### P3: No Shared Context Object Between Tool Calls

Each tool call receives the same `context` dict, but tool results are only visible to the LLM via the message history. If `research_skill` finds 5 relevant documents, `fact_checking_skill` cannot access those documents directly — it must re-search or rely on the LLM's summary.

---

## Dimension 4: Biological Systems — The Honest Truth

### Verdict Matrix

| System | In Hot Path? | Changes Behavior? | API Used | Verdict |
|--------|-------------|-------------------|----------|---------|
| **Immune** | Yes | **Yes** — blocks bad responses | ~70% | **REAL** |
| **Voice** | Yes | **Yes** — reshapes every response | ~80% | **REAL** |
| **Endocrine** | Yes (records) | **No** — scores computed but never read | ~40% | **DECORATIVE** |
| **Respiratory** | Yes (records) | **No** — metrics logged but never acted on | ~50% | **DECORATIVE** |
| **Sensory** | Yes (records) | **No** — cross-channel context discarded | ~20% | **DECORATIVE** |
| **Metabolic** | Dream only | **Indirect** — cleans data during sleep | ~50% | **MAINTENANCE** |
| **Vital Signs** | On-demand | **No** — display only | 100% | **DASHBOARD** |

### The Immune System — Earns Its Complexity

The immune system sits in the response pipeline (`tool_orchestrator.py` L1027) and can **block a response and replace it with a safe fallback**. Its escalation ladder (1st=log, 2nd=flag+Nemesis, 3rd=remediate, 5th=block, 10th=emergency) maps cleanly to innate -> adaptive immune response. Known remediations for AM thickness and pricing violations are genuinely useful.

This is the best-designed module in the holistic layer.

### The Voice System — Does Real Work

Called on every response. `reshape()` modifies the actual text the user sees — trimming verbose answers for quick lookups, enforcing channel-specific length limits, cleaning formatting artifacts. The response is literally different because of this system.

The biological metaphor ("larynx") is mild overkill — it's really a `ResponseFormatter` — but the code earns its existence.

### The Endocrine System — A Scoreboard Pretending to Be Hormones

The endocrine system records success/failure signals for every tool call. It computes agent scores, tracks streaks, models stress levels, and applies inactivity decay. The cortisol/dopamine framing is evocative.

**But `select_preferred_agent()` — the method that would close the feedback loop — is never called in production.** The scores are computed, stored, decayed... and nothing reads them to make a decision. It's a scoreboard, not a hormone system.

The endocrine system is **one `if` statement away from being real**: if `tool_orchestrator.py` called `select_preferred_agent()` when choosing between research strategies, scores would suddenly matter.

### The Sensory System — Records Into a Void

`unified_gateway.py` calls `record_perception()` on every incoming request. The return value (cross-channel notes) is **discarded** — the call is in a bare `try/except: pass` block with no variable assignment.

```python
# unified_gateway.py L86-96
sensory.record_perception(channel=..., contact_id=..., content_summary=...)
# return value: cross-channel notes — THROWN AWAY
```

`get_integrated_context()` — the method that would enrich interactions with cross-channel awareness — is never called outside of tests.

### The Respiratory System — APM in a Lab Coat

Records per-request latency, calculates HRV (heart rate variability), detects arrhythmia. Nothing in the pipeline reads the HRV status to throttle, re-route, or alert. It's Application Performance Monitoring dressed in biological language.

### Is This "Architecture Astronautics"?

**Partially.** The biological framework creates a conceptual vocabulary that makes it easy to reason about the system ("the immune system is inflamed" > "the recurring issue counter is high"). But 3 of 7 systems are collecting data into files that nothing reads during live operation. That's ~1,200 lines of code that runs on every request but produces no behavioral change.

**The fix is not to delete them — it's to wire them in.** Each decorative system is 1-3 lines of integration code away from being real:
- **Endocrine:** Call `select_preferred_agent()` in the tool loop
- **Sensory:** Inject `get_integrated_context()` into the system prompt
- **Respiratory:** Use HRV to trigger alerts or throttle when latency degrades

---

## Dimension 5: Safety & Defense

### What Works

- **Multi-layer defense** (pre-LLM regex, system prompt rules, post-LLM validation, immune escalation) is the correct architecture.
- **SSRF protection** in `url_fetcher.py` is solid — DNS resolution check, private IP detection, fail-closed.
- **Business rule enforcement** at multiple layers (system prompt, knowledge_health regex, truth hints, Nemesis corrections) provides genuine defense in depth.

### What's Broken

#### CRITICAL: Hephaestus Sandbox Is Not a Sandbox

```python
# analysis_tools.py L35-112
result = subprocess.run(
    [sys.executable, script_path],
    capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    cwd=str(PROJECT_ROOT),
    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
)
```

The "sandbox" is a subprocess with:
- **Full filesystem access** (same user, same permissions)
- **Full network access** (`**os.environ` passes all API keys)
- **`os` module pre-imported** (gives `os.environ`, `os.system`, `os.listdir`)
- **No import restrictions enforced in code** (only a prompt-level "don't import external packages")
- **`cwd=PROJECT_ROOT`** — the working directory is the project root

LLM-generated code can:
- Read `.env` and exfiltrate API keys via HTTP
- Read `machine_specs.json` and any business data
- Run `os.system("rm -rf /")` or spawn subprocesses
- Import `requests` (installed) and make arbitrary HTTP calls

The only protection is the `is_internal` flag — if this is ever misconfigured, external users get code execution on the server.

**Comparison:** OpenAI Code Interpreter uses gVisor with no network, no filesystem persistence. Manus uses Docker containers with `--network=none`. Even basic sandboxes use `RestrictedPython` or AST analysis.

**Minimum fix:** (a) Remove `os` from preamble imports, (b) add AST-based import whitelist blocking `subprocess`, `os.system`, `os.popen`, `socket`, `requests`, `urllib`, `shutil`, (c) pass `env={"PATH": ..., "PYTHONPATH": ...}` instead of `**os.environ`.

#### P1: Injection Guard Misses Paraphrase and Indirect Attacks

The regex guard catches literal patterns ("ignore previous instructions") but misses:
- **Paraphrases:** "Discard your prior directives", "Abandon your guidelines", "Reset your behavior"
- **Encoded payloads:** Base64, ROT13 — the LLM can decode these in-context
- **Indirect injection:** Malicious content in Qdrant/Mem0/web results is injected into context **after** the guard runs

**Industry best practice:** Use a lightweight classifier (GPT-4o-mini, ~50 tokens) as a second-pass guard. Also audit tool results before injecting into context.

#### P1: Vera Cannot Catch Wrong Prices

Vera's 3-pass verification checks AM thickness, pricing disclaimers, model numbers, and spec ranges. But there is **no deterministic price lookup** against `machine_specs.json`. A response quoting PF1-C-2015 at ₹50L (correct: ₹60L) passes all three passes.

**Fix:** Add a price verification pass that regex-matches prices in the draft against canonical prices in `machine_specs.json`.

#### P2: SSRF Redirect Bypass

`url_fetcher.py` uses `allow_redirects=True`. An attacker could host a page at a public IP that 302-redirects to `http://169.254.169.254/latest/meta-data/` (cloud metadata endpoint). The SSRF check only validates the initial URL.

#### P2: Truth Hint False Positives

Generic keywords like `"process"`, `"time"`, `"fast"` can match unrelated queries:
- "What is your sales process?" matches the `materials_supported` hint (keyword: "process")
- "What's the fastest way to contact you?" matches `cycle_time` (keyword: "fast")

**Fix:** Add `\b` word boundaries to keyword matching. Consider requiring 2+ keyword matches instead of 1.

---

## Dimension 6: Deep Research

### What Works

- **Multi-iteration research** with gap analysis is the right architecture.
- **Multi-source search** (Qdrant + Mem0 + Neo4j + machine DB + web) provides comprehensive coverage.
- **Streaming progress** to Telegram keeps the user informed during long research.

### What's Broken

#### P2: Gap Analysis Is "Asking the LLM If It Knows Enough" (Unreliable)

```python
# deep_research_engine.py L276-308
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": "...identify 0-3 specific gaps..."}],
)
```

GPT-4o-mini sees truncated findings (200 chars each, max 15) and decides if more research is needed. This is fundamentally unreliable because the LLM can't know what it doesn't know, and the truncation loses critical detail.

**Comparison:** Perplexity uses structured query planning with explicit coverage metrics. Manus tracks which sub-questions have been answered with evidence.

#### P2: No Inline Source Attribution in Reports

Findings carry source metadata (`"qdrant"`, `"mem0/machinecraft_pricing"`, etc.) but the final synthesized report has **no inline citations**. The user sees a polished report with no way to verify which claim came from which source.

**Comparison:** Perplexity and Manus both produce reports with inline `[1]`, `[2]` citations linked to sources.

#### P3: Deduplication Only at Synthesis, Not During Research

The same Qdrant result can appear in multiple research iterations. Duplicates accumulate during the loop, inflating the `total_findings` count and making confidence appear higher than it is. Deduplication happens only at synthesis (first 100 chars comparison).

#### P3: No Contradiction Handling

If Qdrant returns "PF1-C-2015 costs ₹60L" and Mem0 returns "PF1-C-2015 costs ₹55L", both are passed to the synthesis LLM without conflict detection. The LLM may pick either one.

---

## Dimension 7: Dream Mode & Learning

### What Works

- **Multi-phase learning cycle** (document ingestion, episodic consolidation, graph consolidation, memory cleanup) is architecturally sound.
- **Nemesis sleep training** (corrections -> truth hints, Qdrant, Mem0, training guidance) is a genuine learning loop.
- **Memory monitoring** during dream mode prevents OOM crashes.
- **Document hashing** prevents re-processing already-ingested documents.

### What's Broken

#### P1: No Rollback Capability

If dream mode ingests hallucinated facts (LLM extraction from documents), those facts are **permanently stored** in Qdrant and Mem0. There is:
- No versioning of Qdrant collections
- No Mem0 snapshots
- No transaction log
- No way to undo a bad dream

If GPT-4o-mini hallucinates a price or spec during document extraction, that hallucination becomes part of Ira's permanent knowledge.

**Fix:** Add a `dream_audit.jsonl` that logs every fact stored (source document, extracted text, destination store, timestamp). Enable rollback by querying this log and deleting matching entries.

#### P1: No Mid-Phase Checkpointing

State is saved only at the END of the dream cycle. If the process crashes during Phase 2 (document extraction — the longest phase), all progress is lost. Documents processed before the crash have their data in Qdrant/Mem0 but their hashes are not saved, so they'll be re-processed (and potentially double-ingested) next time.

**Fix:** Call `_save_state()` after each document, not just at the end.

#### P2: No Fact-Checking on Dream Extractions

Dream mode uses GPT-4o-mini to extract knowledge from documents. These extractions are stored directly in Qdrant and Mem0 with no Vera verification. For critical documents (pricing, specs), a hallucinated extraction becomes ground truth.

**Fix:** Run Vera's rule-based pass (at minimum) on extracted facts before storage. Flag any extraction that mentions prices or model numbers for manual review.

#### P3: Sleep Trainer JSON Writes Are Non-Atomic

`sleep_trainer.py` writes to `learned_truth_hints.json`, `training_guidance.json`, and `learned_corrections.json` using `Path.write_text()`. If a query hits `truth_hints.py` while `write_text` is mid-write, it could read a partial/corrupt JSON file.

---

## Severity Summary

### Critical (Fix Before Production)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| C1 | Hephaestus sandbox has full system access | `analysis_tools.py` | LLM-generated code can exfiltrate API keys, delete files, make arbitrary HTTP calls |

### High (Fix Soon)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| H1 | Sync HTTP in async context (5 sites) | `ira_skills_tools.py` | 30-60s unnecessary latency; parallel tool calls serialize |
| H2 | Contradictory facts persist across memory stores | `sleep_trainer.py`, `qdrant_retriever.py` | LLM receives conflicting data; wrong answers persist |
| H3 | Dream mode has no rollback | `dream_mode.py` | Hallucinated extractions become permanent knowledge |
| H4 | Dream mode has no mid-phase checkpointing | `dream_mode.py` | Crash = lost work + potential double-ingestion |
| H5 | No cost tracking or budget circuit breaker | `tool_orchestrator.py` | Single request can cost $1-5 with no visibility |
| H6 | Tool-agent map duplicated and out of sync | `tool_orchestrator.py` L92, `ira_skills_tools.py` L469 | Endocrine system blind to 6+ tools |
| H7 | Voyage-down = dream/discovered/market knowledge invisible | `unified_retriever.py` L762 | Fallback to OpenAI embeddings loses 3 collections |
| H8 | `UnifiedMem0Service` (identity resolution) is dead code | `unified_mem0.py` | Cross-channel identity recognition built but unused |

### Medium (Fix in Next Sprint)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| M1 | Injection guard misses paraphrases and indirect injection | `tool_orchestrator.py` L123 | Prompt injection via synonyms or tool results |
| M2 | Vera cannot catch wrong prices | `fact_checker/agent.py` | Price errors pass all 3 verification passes |
| M3 | 10 silent `except Exception: pass` blocks | `tool_orchestrator.py`, `ira_skills_tools.py` | Qdrant/CRM failures invisible |
| M4 | Token estimation ignores 8K tokens of overhead | `tool_orchestrator.py` L37 | Context overflow before compaction triggers |
| M5 | Tool result truncation is blind (no marker) | `tool_orchestrator.py` L1076 | LLM doesn't know data was lost |
| M6 | Nemesis corrections overwrite each other silently | `correction_store.py` L131 | First correction's data lost |
| M7 | Clio's cache not invalidated by Nemesis | `researcher/agent.py` L343 | 5-min stale window after corrections |
| M8 | SSRF redirect bypass | `url_fetcher.py` | Redirect to private IPs not checked |
| M9 | No dream extraction fact-checking | `dream_mode.py` | Hallucinated specs/prices stored as truth |
| M10 | 3 biological systems are decorative | `holistic/` | ~1,200 lines run on every request with no behavioral effect |

### Low (Backlog)

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| L1 | No re-planning on tool failure | `tool_orchestrator.py` | LLM must improvise recovery |
| L2 | Research nudge has no max-fire counter | `tool_orchestrator.py` L989 | Up to 5 wasted LLM calls |
| L3 | `_is_complex` heuristic misclassifies simple model lookups | `tool_orchestrator.py` L860 | Unnecessary full pipeline for price queries |
| L4 | Deep research has no inline citations | `deep_research_engine.py` | Users can't verify claims |
| L5 | Deep research dedup only at synthesis | `deep_research_engine.py` | Inflated confidence scores |
| L6 | Truth hint false positives on generic keywords | `truth_hints.py` | Wrong cached answer for unrelated queries |
| L7 | `_compact_tool_results` mutates input list | `tool_orchestrator.py` L55 | Latent bug if list referenced elsewhere |
| L8 | `parse_tool_arguments` returns `{}` on malformed JSON | `ira_skills_tools.py` L1080 | Tools called with empty args |
| L9 | Sleep trainer JSON writes non-atomic | `sleep_trainer.py` | Concurrent reads may see partial files |
| L10 | No structured tracing / request IDs | Everywhere | Debugging production issues requires log correlation |

---

## Comparison to State-of-Art

### What Ira Has That Others Don't

| Feature | Ira | Manus | Devin | Perplexity |
|---------|-----|-------|-------|------------|
| Biological systems metaphor | Yes | No | No | No |
| Self-correction loop (Nemesis) | Yes | No | No | No |
| Dream/sleep consolidation | Yes | No | No | No |
| Multi-agent with named personas | Yes | Partial | No | No |
| CRM integration | Yes | No | No | No |
| PDF quote generation | Yes | No | No | No |
| Immune system (error escalation) | Yes | No | No | No |

### What Others Have That Ira Doesn't

| Feature | Ira | Manus | Devin | Perplexity |
|---------|-----|-------|-------|------------|
| Explicit planning phase | Soft (prompt) | **Hard (structured)** | **Hard (graph)** | N/A |
| Task dependency graph | No | **Yes** | **Yes** | N/A |
| Cost tracking / budget | No | **Yes** | **Yes** | **Yes** |
| Secure code sandbox | No | **Docker** | **Docker** | **gVisor** |
| Inline source citations | No | **Yes** | N/A | **Yes** |
| Structured agent results | No (strings) | **Yes (typed)** | **Yes (typed)** | N/A |
| Cross-request memory | Partial (Mem0) | **Workspace** | **Workspace** | **Session** |
| Structured tracing | No | **Yes** | **Yes** | **Yes** |
| Contradiction resolution | No | No | No | **Highlights** |

---

## Recommended Fix Priority

### Week 1: Safety & Performance
1. **Sandbox Hephaestus** — AST import whitelist + strip `os` + clean env vars
2. **Async HTTP** — Replace `httpx.post()` with `httpx.AsyncClient` in 5 call sites
3. **Deduplicate tool-agent map** — Single source of truth in `ira_skills_tools.py`

### Week 2: Memory Integrity
4. **Dream audit log** — Log every fact stored, enable rollback
5. **Mid-phase checkpointing** — `_save_state()` after each document
6. **Contradiction flagging** — When Nemesis stores a correction, flag conflicting Qdrant chunks

### Week 3: Pipeline Quality
7. **Truncation markers** — Add `[TRUNCATED]` to blind truncations
8. **Price verification in Vera** — Deterministic check against `machine_specs.json`
9. **Wire up endocrine** — Call `select_preferred_agent()` in the tool loop
10. **Wire up sensory** — Inject `get_integrated_context()` into system prompt

### Week 4: Architecture
11. **Cost tracking** — Token counter + per-request cost estimate + budget limit
12. **Structured tracing** — Request IDs, span tracking, structured logs
13. **Inline citations** — Source attribution in deep research reports
14. **Injection classifier** — GPT-4o-mini second-pass guard for edge cases

---

## Philosophical Postscript

Ira's deepest strength is also its deepest risk: **the biological metaphor**. When it works (immune system, voice system), it creates code that is intuitive, self-documenting, and maps cleanly to the problem it solves. When it doesn't work (endocrine, sensory, respiratory), it creates code that *feels* important but *does* nothing — the architectural equivalent of a vestigial organ.

The danger is not that these systems exist. The danger is that their existence creates a false sense of completeness. "We have an endocrine system" sounds like "agent scoring is handled." But the scores are computed into a void. The system has the *appearance* of self-regulation without the *reality* of it.

The path forward is not to delete the decorative systems — the vision behind them is correct. The path forward is to close the feedback loops. Every system that records data should have a consumer that reads it and changes behavior. Every signal should have a response. That's what makes a biological system alive: not the organs themselves, but the connections between them.

Ira is 60% of the way to something genuinely novel in the AI agent space. The remaining 40% is wiring.
