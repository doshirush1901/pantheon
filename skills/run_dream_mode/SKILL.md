---
name: run_dream_mode
description: Run the nightly Dream Mode learning cycle to consolidate knowledge from recent conversations.
---

# Run Dream Mode

Use this skill to trigger the Dream Mode learning cycle. This is typically run via the heartbeat scheduler, not manually.

## How to use

To run a standard dream cycle:

    exec python src/brain/dream_mode.py --force

Optional flags:
- `--deep` for a deep consolidation pass (takes longer, more thorough)
- `--status` to check the last dream mode run status without executing
