# Changelog

All notable changes to Ira will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open-source release
- GitHub issue and PR templates
- Security policy and code of conduct
- MIT License
- **Sphinx agent** — Gatekeeper of clarity: for complex but vague requests, asks 3–8 clarifying questions before Athena runs; user replies with numbered answers or "skip"; merges Q&A into enriched brief. Integrated in `tool_orchestrator.py`. (`openclaw/agents/ira/src/agents/sphinx/`)
- **Nemesis agent** — Correction-hungry learning: intercepts Telegram corrections, Sophia reflections, immune escalations; stores corrections in Mem0 and SQLite correction store; sleep trainer rewires truth hints, Qdrant, and system prompt. (`openclaw/agents/ira/src/agents/nemesis/` + `scripts/nap.py` Phase 0.5)
- **Manus-style agentic loop** — Single orchestrator (Athena), multi-step tool loop (up to 25 rounds), specialist agents; Sphinx pre-gate and Nemesis passive learning documented in README and AGENTS.md

### Changed
- Complete README rewrite with full Pantheon documentation (13 agents: Athena, Clio, Iris, Calliope, Vera, Sophia, Hermes, Prometheus, Plutus, Hephaestus, Mnemosyne, Sphinx, Nemesis)
- Added Hermes, Prometheus, Plutus, Hephaestus, Mnemosyne agent documentation
- Added Sphinx and Nemesis to README pantheon diagram and message flow (step 2.5 Sphinx gate; Sophia/immune → Nemesis)
- Added defense-in-depth documentation (injection guard, knowledge health, immune system)
- Added biological body systems documentation (immune, respiratory, endocrine, voice, metabolic, musculoskeletal, sensory, growth)
- Added metabolic cycle documentation (EAT → GROW)
- Added full technology stack with all 6 Qdrant collections
- Added detailed message flow walkthrough (8-layer pipeline including Sphinx)
- Updated project structure to reflect current codebase (60+ brain modules, 150+ scripts, 24 skills)
- Reorganized codebase for GitHub-ready structure
- Updated `.gitignore` to exclude sensitive files

---

## [1.0.0] - 2026-03-01

### Added
- **Pantheon Architecture**: Multi-agent system with Athena, Clio, Iris, Calliope, Vera, Sophia, Hermes, Prometheus, Plutus, Hephaestus, and Mnemosyne
- **Brain System**: Hybrid RAG with Voyage AI embeddings and FlashRank reranking
- **Memory System**: Episodic, semantic, and procedural memory with Mem0 integration
- **Telegram Channel**: Full-featured Telegram bot with rich formatting
- **Email Channel**: Gmail integration with smart reply and drafting
- **Iris Intelligence Agent**: Real-time company and market research
- **Dream Mode**: Nightly knowledge consolidation and learning
- **Unified Identity**: Cross-channel user recognition
- **Fact Checking**: Hallucination guard with source verification

### Infrastructure
- Qdrant vector database integration
- PostgreSQL support (optional)
- Neo4j knowledge graph (optional)
- Redis caching (optional)
- Docker Compose configuration

### Skills
- `research_skill` - Deep multi-source research
- `writing_skill` - Professional content creation
- `fact_checking_skill` - Accuracy verification
- `reflection_skill` - Learning from interactions
- `qualify_lead` - Lead scoring
- `generate_quote` - Quotation generation
- `draft_email` - Email composition
- `discover_knowledge` - Knowledge gap discovery
- 20+ additional skills

---

## Version History

### Pre-release Development

#### [0.9.0] - 2026-02-15
- OpenClaw framework integration
- Unified agent architecture
- Memory consolidation system

#### [0.8.0] - 2026-01-20
- Iris intelligence agent
- European drip campaign automation
- Lead intelligence system

#### [0.7.0] - 2025-12-10
- Dream mode implementation
- Pricing learner
- Customer enrichment

#### [0.6.0] - 2025-11-01
- Telegram channel launch
- Email handler integration
- Cross-channel identity

#### [0.5.0] - 2025-09-15
- Brain system v2 with hybrid search
- FlashRank reranking
- Knowledge graph

#### [0.4.0] - 2025-08-01
- Voyage AI embeddings
- Qdrant migration
- Memory system v1

#### [0.3.0] - 2025-06-15
- Initial RAG implementation
- Document ingestion pipeline
- Basic query answering

#### [0.2.0] - 2025-05-01
- Project structure
- Configuration system
- Basic CLI

#### [0.1.0] - 2025-04-01
- Initial project setup
- Proof of concept

---

[Unreleased]: https://github.com/machinecraft/ira/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/machinecraft/ira/releases/tag/v1.0.0
