---
name: draft_email
description: Draft a professional sales email for a lead or customer.
---

# Draft Email

Use this skill when you need to compose an email to a lead or customer.

## How to use

To draft an email for a specific lead:

    exec python src/brain/lead_email_drafter.py --lead "<lead name or ID>"

Optional flags:
- `--category "<category>"` to specify email type
- `--min-stars <number>` to filter by lead quality
- `--use-llm` to use LLM for enhanced personalization
- `--output "<path>"` to save the draft to a file
- `--list` to list available leads
- `--batch` to draft emails for all qualifying leads
