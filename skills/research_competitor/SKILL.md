---
name: research_competitor
description: Research competitor machines (ILLIG, Kiefel, etc.) and provide comparison data.
---

# Research Competitor

Use this skill when a customer mentions a competitor or asks for a comparison.

## How to use

    exec python src/brain/unified_retriever.py --query "<competitor question>" --json

The retriever will search across all collections including competitive intelligence. Add `--json` for structured output.

Note: There is no `--filter` flag. To focus on competitors, include competitor names (ILLIG, Kiefel, etc.) directly in the query text.
