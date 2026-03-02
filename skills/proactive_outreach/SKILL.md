---
name: proactive_outreach
description: Scan for stale leads and draft proactive follow-up messages. Used by the heartbeat scheduler.
---

# Proactive Outreach

This skill is triggered by the heartbeat scheduler every 30 minutes.

## How to use

    exec python src/conversation/proactive_outreach.py run

Scans all active leads, identifies those that have gone cold, and drafts follow-up messages. This is the subcommand triggered by the heartbeat scheduler.
