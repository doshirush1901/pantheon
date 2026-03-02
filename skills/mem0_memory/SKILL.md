---
name: mem0_memory
description: Direct interface to Mem0 memory system. Supports recall, search, and store operations.
---

# Mem0 Memory

Low-level memory interface. Prefer recall_memory and store_memory skills for most use cases.

## How to use

Recall memories:

    exec python src/memory/mem0_cli.py recall --query "<query>" --user-id "<user_id>"

Search memories:

    exec python src/memory/mem0_cli.py search --query "<query>" --user-id "<user_id>"

Store a memory:

    exec python src/memory/mem0_cli.py store --text "<text>" --user-id "<user_id>"
