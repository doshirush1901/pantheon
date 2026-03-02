---
name: discover_knowledge
description: Discover new knowledge by scanning source PDFs when the existing knowledge base cannot answer a question.
---

# Discover Knowledge

Use this skill when you cannot find an answer in the existing knowledge base and need to learn something new.

## How to use

    exec python src/brain/knowledge_discovery.py --query "<the unanswered question>"

The script will:
1. Identify which source PDFs might contain the answer
2. Extract relevant sections from those PDFs
3. Ingest the new knowledge into Qdrant
4. Return the discovered answer
