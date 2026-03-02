---
name: identify_user
description: Resolve a user's identity across channels (Telegram, Email) to maintain unified context.
---

# Identify User

Use this skill when you need to determine if a user on one channel is the same person you've spoken to on another channel.

## How to use

    exec python src/identity/unified_identity.py resolve --channel "<telegram|email>" --identifier "<email or telegram handle>"

This uses the `resolve` subcommand to look up the unified user profile.
