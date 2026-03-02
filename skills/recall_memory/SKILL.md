---
name: recall_memory
description: Recall relevant memories about a user or topic from Mem0.
---

# Recall Memory

Use this skill before responding to a returning customer, or when you need context from past conversations.

## How to use

    exec python src/memory/mem0_cli.py recall --query "<what to recall>" --user-id "<user_id>"

Returns relevant memories from Mem0's semantic search.
