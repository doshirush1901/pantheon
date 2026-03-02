# Pantheon

**An AI sales agent framework with a pantheon of specialist agents.**

Pantheon gives you a production-ready AI sales assistant that researches, writes, fact-checks, and learns from every interaction. Configure it for your company in 10 minutes.

Built by [Machinecraft Technologies](https://machinecraft.org) and battle-tested on real B2B sales conversations.

> **New here?** Read [WHY.md](WHY.md) for the full story — why most AI sales solutions are goldfish in suits, and how Pantheon is different.

---

## What You Get

A single agent with 6 specialist roles that work together:

| Agent | Role | What It Does |
|-------|------|-------------|
| **Athena** | Orchestrator | Analyzes intent, plans which skills to use, synthesizes responses |
| **Clio** | Researcher | Searches your knowledge base (Qdrant + Mem0 + Neo4j) |
| **Calliope** | Writer | Drafts responses in your brand voice |
| **Vera** | Fact Checker | Verifies every claim before it reaches the customer |
| **Sophia** | Reflector | Learns from every interaction, logs errors and lessons |
| **Iris** | Intelligence | Gathers external company news, industry trends, web research |

Plus:
- **Memory system** with long-term recall, episodic memory, and cross-channel identity
- **Feedback loops** that learn from corrections in real-time
- **Deep Dive** mode for multi-phase research projects
- **Brain Trainer** (Duolingo-style quizzes to strengthen weak knowledge areas)
- **Dream Mode** (nightly knowledge consolidation)
- **Telegram + Email** channels out of the box

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/doshirush1901/pantheon.git
cd pantheon
pip install -r requirements.txt
```

### 2. Configure your agent

```bash
cp agent.yaml.example agent.yaml
cp .env.example .env
```

Edit `agent.yaml` with your company info:

```yaml
company:
  name: "Your Company"
  agent_name: "Your Agent Name"
  agent_email: "agent@yourcompany.com"

persona:
  role: "AI Sales Assistant"
  tone: "Professional, warm, data-driven"
```

Edit `.env` with your API keys:

```bash
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
ADMIN_TELEGRAM_ID=...
```

### 3. Add your product knowledge

Create `data/brain/product_specs.json` with your products (see `examples/sales_agent/products.json` for the schema).

Create `data/brain/rules.txt` with your business rules.

### 4. Run

```bash
python -m openclaw.agents.ira.run
```

Your agent is now live on Telegram, ready to answer questions about your products.

## Architecture

```
User message (Telegram / Email)
        |
        v
+-- Pre-processing --------------------------+
|  Memory context, coreference resolution,    |
|  RAG retrieval, identity resolution         |
+---------------------------------------------+
        |
        v
+-- Tool Orchestrator (Athena) ---------------+
|  LLM decides which tools to call:           |
|  research -> web_search -> write -> verify  |
|  Up to 15 rounds of tool use               |
+---------------------------------------------+
        |
        v
+-- Post-processing --------------------------+
|  Fact checking, business rules,             |
|  personality, confidence scoring            |
+---------------------------------------------+
        |
        v
     Response
```

## Configuration

Everything is configured through `agent.yaml`:

| Section | What It Controls |
|---------|-----------------|
| `company` | Name, domain, emails, admin ID |
| `persona` | Tone, style, role description |
| `memory.namespaces` | Mem0 namespace prefixes for your data |
| `products` | Path to your product specs and business rules |
| `competitors` | Competitor names and positioning |

See `agent.yaml.example` for the full schema with comments.

## Infrastructure

Pantheon uses these services (all self-hostable):

| Service | Purpose | Cost |
|---------|---------|------|
| **OpenAI** | LLM (GPT-4o) | ~$20-100/mo |
| **Qdrant** | Vector search | Free (self-hosted) or $25/mo |
| **Mem0** | Long-term memory | $20/mo or self-hosted |
| **Voyage AI** | Embeddings | ~$10/mo |
| **Jina** | Web research | Free tier available |

Optional: PostgreSQL, Neo4j, Redis, Langfuse (observability).

## Examples

See `examples/` for complete working configurations:

- `examples/sales_agent/` — Generic industrial equipment sales agent

## Project Structure

```
openclaw/agents/ira/src/
  core/           # Orchestration, config, health, streaming
  agents/         # The 6 specialist agents
  brain/          # Response generation, RAG, product database
  memory/         # Mem0, identity, episodic memory
  conversation/   # Chat log, coreference, entity extraction
  tools/          # Tool schemas and execution
  skills/         # Skill invocation layer
  crm/            # Lead tracking, follow-ups, campaigns
  sales/          # Quote generation, outreach
```

## License

[Business Source License 1.1](LICENSE) — free for your own use, converts to Apache 2.0 after 4 years. See [PRICING.md](PRICING.md) for commercial licensing.

## Built With

93,000 lines of Python, $2,000 of Cursor, and a lot of real sales conversations.
