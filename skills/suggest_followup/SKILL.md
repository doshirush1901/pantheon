---
name: suggest_followup
description: Suggest follow-up actions or messages when a conversation stalls or a lead goes cold.
---

# Suggest Follow-up

Use this skill when a conversation has stalled or you need to re-engage a lead.

## How to use

    exec python src/conversation/proactive_outreach.py suggest --user-id "<user_id>"

Returns suggested follow-up messages based on conversation history and lead status.
