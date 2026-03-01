---
name: store_memory
description: Store a new fact or memory about a user or conversation in Mem0.
---

# Store Memory

Use this skill when the user tells you something important to remember, or after a significant conversation.

## How to use

    exec python src/memory/mem0_cli.py store --text "<fact to remember>" --user-id "<user_id>"

Stores the fact in Mem0 for future recall.
