---
name: qualify_lead
description: Score and qualify an incoming sales lead based on their inquiry.
---

# Qualify Lead

Use this skill when a new inquiry comes in and you need to assess lead quality.

## How to use

    exec python src/brain/inquiry_qualifier.py --inquiry "<the lead's message>"

Optional flags:
- `--thread-id "<thread_id>"` to link to a conversation thread
- `--user-id "<user_id>"` to associate with a known user
- `--json` to get structured JSON output
