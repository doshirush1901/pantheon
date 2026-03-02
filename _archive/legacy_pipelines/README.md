# Legacy Pipelines (Archived 2024-02-28)

These pipeline files have been replaced by the new multi-agent architecture.

## Archived Files

| File | Replaced By |
|------|-------------|
| `query_analysis_pipeline.py` | `src/agents/researcher/agent.py` (QueryAnalyzer class) |
| `deep_research_pipeline.py` | `src/agents/researcher/agent.py` (ResearcherAgent) |
| `reply_packaging_pipeline.py` | `src/agents/writer/agent.py` (WriterAgent) |
| `feedback_processing_pipeline.py` | `src/agents/reflector/agent.py` (ReflectorAgent) |
| `ira_pipeline_orchestrator.py` | `src/agents/chief_of_staff/agent.py` (ChiefOfStaffAgent) |

## Why Archived

The old pipeline architecture was replaced with a multi-agent system that provides:

1. **Better Separation of Concerns**: Each agent has a single responsibility
2. **Async Parallel Execution**: Researcher uses asyncio for concurrent searches
3. **Redis Caching**: 60-80% cache hit rate reduces latency
4. **Adaptive Planning**: Chief of Staff adjusts based on lessons/errors
5. **Source Attribution**: Fact checker tags every claim with sources
6. **Continuous Learning**: Reflector logs errors and extracts lessons

## New Architecture

```
                    ┌─────────────────┐
                    │ CHIEF OF STAFF  │
                    │  (Orchestrator) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  RESEARCHER   │    │    WRITER     │    │ FACT_CHECKER  │
│  (Research)   │    │  (Content)    │    │ (Validation)  │
└───────────────┘    └───────────────┘    └───────────────┘
                             │
                             ▼
                    ┌───────────────┐
                    │   REFLECTOR   │
                    │  (Learning)   │
                    └───────────────┘
```

## Migration Notes

If you need to reference the old implementation:

- Query classification logic → `src/agents/researcher/agent.py::QueryAnalyzer`
- Memory search logic → `src/agents/researcher/agent.py::ResearcherAgent._parallel_search()`
- Reply formatting → `src/agents/writer/agent.py::WriterAgent.package()`
- Feedback handling → `src/agents/reflector/agent.py::ReflectorAgent.process_feedback()`

## Do Not Use

These files are kept for historical reference only. Do not import or use them.
The new agent-based system should be used via:

```python
from src.agents import get_chief_of_staff

cos = get_chief_of_staff()
response = await cos.process_message(message, user_id, channel)
```
