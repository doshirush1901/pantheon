---
name: check_health
description: Check the health of IRA's knowledge base, external services, and system components.
---

# Check Health

Use this skill when asked about system status or when you suspect a component is failing.

## How to use

    exec python src/brain/knowledge_health.py --check

Returns health status for: Qdrant, Mem0, Voyage AI, OpenAI, and the knowledge base coverage metrics.
