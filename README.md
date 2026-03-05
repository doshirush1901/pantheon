# Pantheon — Agentic Email Intelligence

An agentic email intelligence system that orchestrates 14 specialized AI agents for email triage, research, composition, and continuous learning.

## What It Does

- **Email triage & response** — Reads inbox, classifies intent, composes context-aware replies
- **Lead intelligence** — Enriches contacts with news, market context, and company data
- **Sales outreach** — Hermes runs drip campaigns with A/B subjects, reply detection, timezone-aware sending
- **Research & fact-checking** — Clio researches, Vera verifies, Sophia reflects on quality
- **Case studies & content** — Cadmus builds case studies, drafts LinkedIn posts, serves proof stories
- **Learning loop** — Nemesis tracks failures; Sophia extracts lessons; system improves over time

## Quick Start

```bash
# Clone
git clone https://github.com/doshirush1901/pantheon.git
cd pantheon

# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env: set OPENAI_API_KEY

# Gmail OAuth (required for email features)
python scripts/setup_gmail.py
# Follow prompts to authorize Gmail access

# Use from Cursor
# Reference .cursor/rules/ira-architecture.mdc for architecture
```

## Architecture

| Agent | Role |
|-------|------|
| Athena | Chief orchestrator, tool loop |
| Hermes | Sales outreach, drip campaigns |
| Iris | Lead intelligence |
| Delphi | Voice profile |
| Chiron | Sales coaching |
| Clio | Researcher |
| Calliope | Writer |
| Vera | Fact checker |
| Sophia | Reflector |
| Nemesis | Failure tracker |
| Sphinx | Input guard |
| Cadmus | CMO, case studies |
| Arachne | Web research |
| Hephaestus | Program builder |

## Project Structure

```
pantheon/
├── openclaw/
│   └── agents/
│       └── ira/
│           ├── src/
│           │   ├── agents/       # Athena, Hermes, Iris, Delphi, ...
│           │   ├── skills/       # invocation, tool orchestration
│           │   ├── tools/        # ira_skills_tools, google_tools
│           │   └── holistic/     # endocrine system (optional)
│           └── agent.py          # Main entry
├── scripts/
│   ├── setup_gmail.py
│   └── ...
├── data/
├── .cursor/rules/
├── AGENTS.md
├── .env.example
└── pyproject.toml
```

## Optional Enhancements

| Feature | Env Key | Description |
|---------|---------|-------------|
| Tavily search | `TAVILY_API_KEY` | Enhanced web research |
| Serper search | `SERPER_API_KEY` | Google search API |
| NewsData | `NEWSDATA_API_KEY` | News and headlines |
| Voyage embeddings | `VOYAGE_API_KEY` | Vector embeddings |
| Mem0 memory | `MEM0_API_KEY` | Long-term memory |
| Qdrant | `QDRANT_URL` | Vector store |
| Langfuse | `LANGFUSE_*` | Observability & tracing |

## License

MIT
