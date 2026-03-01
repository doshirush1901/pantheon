# Ira - Intelligent Revenue Assistant

<p align="center">
  <img src="docs/assets/ira-logo.png" alt="Ira Logo" width="200" />
</p>

<p align="center">
  <strong>AI-Powered Sales Intelligence Platform for Manufacturing</strong>
</p>

<p align="center">
  <a href="#about">About</a> •
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#usage">Usage</a> •
  <a href="#api-reference">API</a> •
  <a href="#contributing">Contributing</a>
</p>

<p align="center">
  <a href="https://github.com/machinecraft/ira/actions/workflows/ci.yml">
    <img src="https://github.com/machinecraft/ira/actions/workflows/ci.yml/badge.svg" alt="CI Status" />
  </a>
  <a href="https://codecov.io/gh/machinecraft/ira">
    <img src="https://codecov.io/gh/machinecraft/ira/branch/main/graph/badge.svg" alt="Coverage" />
  </a>
  <a href="https://github.com/machinecraft/ira/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" />
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python Version" />
  </a>
</p>

---

## About

**Ira** (Intelligent Revenue Assistant) is a sophisticated AI sales assistant built for [Machinecraft Technologies](https://machinecraft.in), a leading manufacturer of thermoforming machinery. Ira transforms how sales teams interact with product knowledge, customer history, and market intelligence.

### What Makes Ira Different?

Unlike generic chatbots, Ira is purpose-built for B2B industrial sales with:

- **Domain Expertise**: Deep knowledge of thermoforming machinery, applications, and industry terminology
- **Persistent Memory**: Remembers customer conversations, preferences, and history across channels
- **Multi-Agent Architecture**: A "Pantheon" of specialized agents working together for optimal results
- **Fact Verification**: Built-in hallucination guards and source verification
- **Multi-Channel**: Unified experience across Telegram, Email, and API

### The Pantheon Architecture

Ira operates as a coordinated team of specialist agents:

| Agent | Role | Responsibility |
|-------|------|----------------|
| **Athena** | Strategist | Orchestrates all requests, plans execution |
| **Clio** | Researcher | Retrieves knowledge from documents, emails, and memory |
| **Iris** | Intelligence | Gathers real-time external data (news, company info) |
| **Calliope** | Writer | Crafts professional communications |
| **Vera** | Auditor | Verifies facts, enforces accuracy rules |
| **Sophia** | Mentor | Learns from interactions, improves over time |

```
User Query → Athena (plans) → Clio (researches) → Calliope (writes) → Vera (verifies) → Response
                                                                              ↓
                                                                      Sophia (learns)
```

### Who Is This For?

- **Sales Teams**: Get instant answers about products, pricing, and customer history
- **Customer Support**: Provide accurate technical information quickly
- **Sales Managers**: Monitor customer relationships and pipeline
- **Developers**: Build custom integrations via the API

---

## Features

### 🧠 Knowledge & RAG System

| Feature | Description |
|---------|-------------|
| **Hybrid Search** | Vector (Voyage AI) + BM25 keyword search with FlashRank reranking |
| **Document Ingestion** | PDF, Excel, Word, and text document processing |
| **Knowledge Graph** | Entity relationships and fact tracking |
| **Fact Checking** | Automatic hallucination detection with source verification |
| **Dream Mode** | Nightly knowledge consolidation and learning |

### 💬 Communication Channels

| Channel | Features |
|---------|----------|
| **Telegram Bot** | Rich formatting, inline actions, conversation threading |
| **Email Handler** | Gmail integration, automatic processing, smart replies |
| **API Server** | RESTful API for custom integrations |
| **CLI Mode** | Interactive command-line interface |

### 🗄️ Memory System

| Type | Purpose |
|------|---------|
| **Episodic** | Conversation history and interaction records |
| **Semantic** | Facts, preferences, and learned knowledge |
| **Procedural** | Learned workflows and response patterns |
| **Unified Identity** | Cross-channel user recognition |

### 📧 Email Intelligence

- **Smart Drafting**: Context-aware email composition
- **Lead Qualification**: Automatic scoring and prioritization
- **Drip Campaigns**: Automated follow-up sequences
- **Thread Management**: Intelligent conversation threading

### 🔍 Market Intelligence (Iris)

- **Company Research**: Real-time news and updates
- **Industry Trends**: Market analysis and insights
- **Competitive Intelligence**: Competitor monitoring
- **Geopolitical Context**: Regional business factors

---

## Quick Start

### Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Docker** (for Qdrant and PostgreSQL)
- **API Keys**: OpenAI, Voyage AI

### 1. Clone the Repository

```bash
git clone https://github.com/machinecraft/ira.git
cd ira
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install in editable mode (recommended for development)
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
# Required: OPENAI_API_KEY, VOYAGE_API_KEY
# Optional: TELEGRAM_BOT_TOKEN, MEM0_API_KEY
```

### 5. Start Infrastructure

```bash
# Start Qdrant (vector database) and PostgreSQL
docker-compose up -d

# Verify services
docker-compose ps
```

### 6. Index Your Documents

```bash
# Place documents in data/imports/
# Supported: PDF, Excel, Word, TXT

# Run document ingestion
python scripts/ingest_doc.py data/imports/your_document.pdf
```

### 7. Start Ira

```bash
# Start all services
./start_ira.sh

# Or start specific modes:
./start_ira.sh cli       # Interactive CLI mode
./start_ira.sh telegram  # Telegram bot only
./start_ira.sh status    # Check service status
```

### 8. Test It Out

```bash
# Test document retrieval
python -c "
from openclaw.agents.ira.src.brain.unified_retriever import UnifiedRetriever
retriever = UnifiedRetriever()
results = retriever.search('your test query', top_k=3)
for r in results:
    print(f'Score: {r[\"score\"]:.3f} - {r[\"text\"][:100]}...')
"
```

---

## Architecture

### System Overview

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           IRA SYSTEM ARCHITECTURE                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  CHANNELS                                                                     ║
║  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         ║
║  │  Telegram   │  │    Email    │  │     API     │  │     CLI     │         ║
║  │   Gateway   │  │   Handler   │  │   Server    │  │   Console   │         ║
║  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         ║
║         │                │                │                │                  ║
║         └────────────────┴────────────────┴────────────────┘                  ║
║                                    │                                          ║
║                                    ▼                                          ║
║  ┌────────────────────────────────────────────────────────────────────────┐  ║
║  │                    UNIFIED AGENT COORDINATOR                            │  ║
║  │  • Identity Resolution  • State Management  • Request Routing          │  ║
║  └─────────────────────────────────┬──────────────────────────────────────┘  ║
║                                    │                                          ║
║  ┌─────────────────────────────────┼──────────────────────────────────────┐  ║
║  │                         PANTHEON AGENTS                                 │  ║
║  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  ║
║  │  │  Athena  │ │   Clio   │ │   Iris   │ │ Calliope │ │   Vera   │     │  ║
║  │  │ Strategy │ │ Research │ │  Intel   │ │  Writer  │ │ Auditor  │     │  ║
║  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │  ║
║  └─────────────────────────────────┬──────────────────────────────────────┘  ║
║                                    │                                          ║
║  ┌─────────────────────────────────┼──────────────────────────────────────┐  ║
║  │                          CORE SYSTEMS                                   │  ║
║  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │  ║
║  │  │   Brain System   │  │  Memory System   │  │ Identity System  │     │  ║
║  │  │  RAG, Retrieval  │  │ Episodic/Semantic│  │ Cross-channel ID │     │  ║
║  │  └──────────────────┘  └──────────────────┘  └──────────────────┘     │  ║
║  └────────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║  INFRASTRUCTURE                                                               ║
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     ║
║  │    Qdrant    │  │     Mem0     │  │  PostgreSQL  │  │    Neo4j     │     ║
║  │  (Vectors)   │  │   (Memory)   │  │  (Relational)│  │   (Graph)    │     ║
║  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | OpenAI GPT-4o | Response generation, analysis |
| **Embeddings** | Voyage AI (voyage-3) | 1024-dim semantic embeddings |
| **Vector DB** | Qdrant | Document and memory storage |
| **Memory** | Mem0 | Long-term semantic memory |
| **Graph DB** | Neo4j | Entity relationships |
| **Reranking** | FlashRank | Result relevance optimization |
| **Messaging** | python-telegram-bot | Telegram integration |
| **Email** | Gmail API | Email processing |
| **Database** | PostgreSQL | Relational data |

### Directory Structure

```
ira/
├── 📄 README.md                    # This file
├── 📄 pyproject.toml               # Modern Python package config
├── 📄 requirements.txt             # Core dependencies
├── 📄 docker-compose.yml           # Infrastructure services
├── 📄 .env.example                 # Environment template
│
├── 📁 openclaw/agents/ira/         # Main application
│   ├── 📄 agent.py                 # Unified agent coordinator
│   ├── 📄 config.py                # Centralized configuration
│   ├── 📁 src/                     # Source modules
│   │   ├── 📁 brain/               # RAG & knowledge (38 modules)
│   │   ├── 📁 memory/              # Persistent memory (20+ modules)
│   │   ├── 📁 conversation/        # Conversation intelligence
│   │   ├── 📁 identity/            # Cross-channel identity
│   │   └── 📁 crm/                 # CRM integration
│   ├── 📁 skills/                  # Modular capabilities
│   │   ├── 📁 email_channel/       # Email processing
│   │   ├── 📁 telegram_channel/    # Telegram bot
│   │   └── 📁 market_research/     # Research automation
│   └── 📁 tools/                   # External integrations
│
├── 📁 agents/                      # Specialist agents
│   ├── 📁 iris/                    # Intelligence agent
│   ├── 📁 apollo/                  # Learning agent
│   ├── 📁 athena/                  # Strategy agent
│   └── 📁 nemesis/                 # QA agent
│
├── 📁 skills/                      # Cursor/OpenClaw skills (20+)
│
├── 📁 scripts/                     # Utility scripts (34 files)
│   ├── 📄 ingest_doc.py            # Document ingestion
│   ├── 📄 run_dream_mode.py        # Nightly learning
│   └── 📄 ira_smart_reply.py       # Smart email replies
│
├── 📁 data/                        # Data storage
│   ├── 📁 imports/                 # Source documents
│   ├── 📁 knowledge/               # Processed knowledge
│   └── 📁 mem0_storage/            # Memory backup
│
├── 📁 docs/                        # Documentation (20+ files)
├── 📁 tests/                       # Test suite (263+ tests)
└── 📁 crm/                         # CRM databases
```

---

## Usage

### Interactive CLI Mode

Start an interactive session:

```bash
./start_ira.sh cli
```

Example interaction:

```
You: What machine do you recommend for 4mm thick ABS sheets?

Ira: For 4mm ABS sheets, I recommend the **PF1-C-2015** with the following specs:

Machine Specifications:
1. Max forming area: 2000 x 1500 mm
2. Max depth: 400 mm
3. Material thickness: 1-8mm
4. Heater: Dual-zone IR ceramic
5. Base price: Subject to configuration

**Note:** The AM series was not recommended as it only supports materials ≤1.5mm thick.

Would you like a formal quotation?
```

### Telegram Bot

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Add `TELEGRAM_BOT_TOKEN` and `EXPECTED_CHAT_ID` to `.env`
3. Start: `./start_ira.sh telegram`

Commands:
- `/start` - Initialize bot
- `/help` - Show available commands
- `/search <query>` - Search knowledge base
- `/customer <name>` - Lookup customer info
- `/draft <context>` - Draft an email

### Email Integration

1. Set up Gmail API credentials (see [docs/EMAIL_SETUP.md](docs/EMAIL_SETUP.md))
2. Configure in `.env`
3. Start: `./start_ira_openclaw.sh email`

### Python API

```python
from openclaw.agents.ira import get_agent

# Initialize agent
agent = get_agent()

# Process a message
response = agent.process(
    message="What's the price for PF1-3020?",
    channel="api",
    user_id="user@example.com"
)

print(response)
```

### Direct Retrieval

```python
from openclaw.agents.ira.src.brain.unified_retriever import UnifiedRetriever

retriever = UnifiedRetriever()

# Search with hybrid retrieval
results = retriever.search(
    query="thermoforming machine specifications",
    top_k=5,
    filters={"category": "product"}
)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Source: {result['metadata'].get('source', 'Unknown')}")
    print(f"Content: {result['text'][:200]}...")
    print("---")
```

### Memory Operations

```python
from openclaw.agents.ira.src.memory.unified_mem0 import get_unified_mem0

mem0 = get_unified_mem0()

# Store a conversation
mem0.remember(
    user_message="I need a large thermoforming machine",
    assistant_response="I recommend the PF1-3520...",
    user_id="customer@example.com",
    channel="email"
)

# Search memories
memories = mem0.search(
    query="thermoforming requirements",
    user_id="customer@example.com"
)

# Get user context
context = mem0.get_user_context(user_id="customer@example.com")
```

### Market Intelligence (Iris)

```python
from agents.iris import Iris

iris = Iris()

# Research a company
intel = await iris.research_company("Tata AutoComp")
print(intel.summary)
print(intel.recent_news)
print(intel.key_hooks)  # Sales conversation hooks
```

---

## API Reference

### Core Classes

#### `UnifiedAgent`

Main entry point for all interactions.

```python
class UnifiedAgent:
    def process(
        self,
        message: str,
        channel: str = "api",
        user_id: str = None,
        metadata: dict = None
    ) -> str:
        """Process a message and return response."""
```

#### `UnifiedRetriever`

Hybrid search with vector + BM25.

```python
class UnifiedRetriever:
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict = None,
        include_sources: bool = True
    ) -> List[Dict]:
        """Search documents with hybrid retrieval."""
```

#### `UnifiedMem0`

Persistent memory operations.

```python
class UnifiedMem0:
    def remember(self, user_message: str, assistant_response: str, ...) -> str
    def search(self, query: str, user_id: str, ...) -> List[Dict]
    def get_user_context(self, user_id: str, ...) -> Dict
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `VOYAGE_API_KEY` | Yes | Voyage AI embeddings key |
| `TELEGRAM_BOT_TOKEN` | For Telegram | Telegram bot token |
| `EXPECTED_CHAT_ID` | For Telegram | Authorized Telegram chat ID |
| `QDRANT_URL` | Yes | Qdrant vector database URL |
| `MEM0_API_KEY` | Optional | Mem0 memory service key |
| `DATABASE_URL` | Optional | PostgreSQL connection string |
| `IRA_LOG_LEVEL` | Optional | Log level (DEBUG, INFO, WARNING) |

See [.env.example](.env.example) for complete list.

---

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=openclaw --cov-report=html

# Run specific test file
pytest tests/test_unified_retriever.py -v

# Run tests matching pattern
pytest tests/ -k "memory" -v
```

### Code Quality

```bash
# Format with Black
black openclaw/ scripts/ tests/

# Sort imports
isort openclaw/ scripts/ tests/

# Lint with Ruff
ruff check openclaw/ scripts/

# Type check
mypy openclaw/
```

### Adding Documents

```bash
# Single document
python scripts/ingest_doc.py path/to/document.pdf

# Batch ingestion
python scripts/batch_ingest.py data/imports/

# Verify indexing
python -c "from openclaw.agents.ira.src.brain.unified_retriever import UnifiedRetriever; print(UnifiedRetriever().stats())"
```

### Creating Skills

Skills are modular capabilities in `skills/`:

```python
# skills/custom_skill/SKILL.md
---
name: custom_skill
description: Description of what this skill does
---

# Skill Name

Instructions for using this skill...
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Overview](docs/ARCHITECTURE_OVERVIEW.md) | System architecture |
| [Agent Architecture](docs/AGENT_ARCHITECTURE.md) | Detailed agent design |
| [Memory System](docs/UNIFIED_ARCHITECTURE.md) | Memory architecture |
| [Knowledge System](docs/KNOWLEDGE_DISCOVERY_ARCHITECTURE.md) | RAG and retrieval |
| [Email Setup](docs/EMAIL_AUDIT.md) | Email integration guide |
| [Telegram Setup](docs/TELEGRAM_BOT_AUDIT.md) | Telegram bot guide |
| [Contributing](CONTRIBUTING.md) | Contribution guidelines |

---

## Troubleshooting

### Common Issues

**Qdrant connection failed:**
```bash
docker-compose up -d qdrant
curl http://localhost:6333/health
```

**Import errors:**
```bash
pip install -e .  # Reinstall in editable mode
```

**Missing embeddings:**
```bash
# Check Voyage API key
python -c "from openclaw.agents.ira.config import get_voyage_client; print(get_voyage_client())"
```

**Memory issues:**
```bash
# Check Mem0 connection
python -c "from openclaw.agents.ira.src.memory.unified_mem0 import get_unified_mem0; print(get_unified_mem0().health())"
```

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/machinecraft/ira/issues)
- **Discussions**: [GitHub Discussions](https://github.com/machinecraft/ira/discussions)
- **Security**: See [SECURITY.md](SECURITY.md)

---

## Roadmap

- [ ] Web dashboard for analytics
- [ ] WhatsApp channel integration
- [ ] Voice interface (Whisper)
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] CRM integrations (Salesforce, HubSpot)

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/ -v`)
5. Commit (`git commit -m 'feat: add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built with [OpenAI GPT-4](https://openai.com)
- Embeddings by [Voyage AI](https://voyageai.com)
- Vector search by [Qdrant](https://qdrant.tech)
- Memory by [Mem0](https://mem0.ai)

---

<p align="center">
  <strong>Built with ❤️ for Machinecraft Technologies</strong>
  <br>
  <sub>Empowering industrial sales with AI intelligence</sub>
</p>
