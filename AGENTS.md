# Pantheon — Agentic Email Intelligence

Pantheon is an agentic email intelligence system that orchestrates 14 specialized AI agents to handle email triage, research, composition, and learning.

## The 14 Kept Agents

| Agent | Role |
|-------|------|
| **Athena** | Chief orchestrator — intent analysis, planning, tool selection |
| **Hermes** | Pro sales outreach — drip campaigns, reply detection, context-rich emails |
| **Iris** | Lead intelligence — news, market context, company enrichment |
| **Delphi** | Voice profile — Rushabh's communication style calibration |
| **Chiron** | Sales coaching — stage-specific guidance and best practices |
| **Clio** | Researcher — knowledge retrieval, specs lookup |
| **Calliope** | Writer — content creation, brand voice |
| **Vera** | Fact checker — verification of claims and disclaimers |
| **Sophia** | Reflector — quality assessment, learning, lessons |
| **Nemesis** | Failure tracker — ingests issues for improvement |
| **Sphinx** | Input guard — classification, routing, guardrails |
| **Cadmus** | CMO — case studies, LinkedIn drafts, proof stories |
| **Arachne** | Web research — search, synthesis |
| **Hephaestus** | Program builder — forge and execute code when needed |

## How It Works

1. **Input** arrives via email or chat.
2. **Sphinx** classifies intent, applies guardrails, and routes the message.
3. **Athena** analyzes intent and enters a tool loop: she selects and invokes tools (research, write, verify, etc.) until the task is complete.
4. **Vera** fact-checks the draft for accuracy and compliance.
5. **Sophia** reflects on the interaction, scores quality, and extracts lessons.
6. **Nemesis** receives failures and issues for continuous improvement.
7. **Observer** (optional) logs traces and metrics.

## Tools Available

### Email
- `read_inbox`, `read_thread`, `send_email`, `search_emails`, `get_labels`
- Gmail OAuth integration for full inbox access

### Research
- `web_search`, `tavily_search`, `serper_search`, `newsdata_search`
- `qdrant_retrieve`, `voyage_embed`
- Clio: `research`, `get_machine_specs`, `list_machines`, `check_thickness_compatibility`

### Google Workspace
- Gmail API (messages, threads, send)
- Optional: Drive, Calendar, Sheets

### Composition
- Calliope: `write`, `write_streaming`, `format_for_channel`, `add_brand_voice`
- Cadmus: `find_case_studies`, `build_case_study`, `draft_linkedin_post`
- Hermes: `craft_email`, `run_outreach_batch`, `check_replies`

### Content
- Vera: `verify`, `generate_verification_report`
- Sophia: `reflect`, `get_recent_errors`, `get_recent_lessons`
- Delphi: `get_delphi_guidance`
- Chiron: `get_coaching_notes`

## Quick Start

1. Clone the repo and install: `pip install -e .`
2. Set `OPENAI_API_KEY` in `.env`
3. Run `python scripts/setup_gmail.py` for Gmail OAuth
4. Use from Cursor: reference `.cursor/rules/ira-architecture.mdc` for flow
5. Run `pantheon` CLI or integrate via OpenClaw gateway
