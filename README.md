# Pantheon

### An open-source AI sales agent framework with a pantheon of specialist agents.
### (and why your current "AI sales solution" is probably a goldfish in a suit)

---

## Part 1: The Problem Nobody Talks About

Let's say you run a company that sells... I don't know... industrial thermoforming machines. (Totally random example. Not autobiographical at all.)

A customer emails you:

> "Hi, we're looking at the PF1-C-2015 for our automotive interior line. Can you send specs and pricing? Also, what's your lead time to Germany?"

Now, a good sales response to this email requires you to:

1. Know what the PF1-C-2015 actually is (not make it up)
2. Pull the correct specs from your catalog
3. Look up the right price (and not accidentally quote last year's price)
4. Check if you've talked to this customer before
5. Remember that Germany has specific import requirements
6. Write a response that sounds like a human who cares, not a robot who was forced to care
7. NOT say something wrong that loses you a $200,000 deal

That's seven things. For one email. And you get forty of these a week.

So you think: "I'll use AI!"

---

## Part 2: The AI Sales Agent Spectrum of Sadness

Here's what happens when most people try to solve this with AI:

```
THE SPECTRUM OF AI SALES SOLUTIONS

Terrible                                                          Actually Good
   |                                                                    |
   v                                                                    v

[ChatGPT]----[Chatbot]----[RAG Bot]----[Agent]----[???]----[Pantheon]
   |             |            |            |                     |
   |             |            |            |                     |
"Who are      "I found     "Based on    "Let me              "I researched
 you again?"  a FAQ!"      document     search...             your company,
                           chunk #47,   *calls 3 tools*       checked the specs
                           here's a     *gets confused*       against our database,
                           paragraph"   *hallucinates*        verified the price,
                                        *gives up*            drafted a response in
                                                              your brand voice,
                                                              fact-checked it,
                                                              and learned from
                                                              your last correction.
                                                              
                                                              Here's the email.
                                                              Want me to send it?"
```

Let's walk through each one, because you've probably tried at least two of them.

### Level 1: The ChatGPT Window

You paste your product catalog into ChatGPT. It works great! For about 4 minutes.

Then a customer asks about pricing and ChatGPT confidently invents a number. Not a wrong number from your catalog — a number that has never existed in any universe. It just... made one up. With a straight face. And a smiley emoji.

```
Customer: "What's the price for the X-200?"
ChatGPT:  "The X-200 is priced at $34,750! Great choice! 😊"
You:       *checks catalog*
You:       "...we don't even have a product called the X-200"
```

This is what I call the **Confident Goldfish Problem**. ChatGPT has the memory of a goldfish (every conversation starts fresh) and the confidence of a CEO giving a TED talk. Dangerous combination.

### Level 2: The Chatbot Widget

You pay $49/month for a chatbot that sits on your website. It has your FAQ loaded. A customer asks a question that's 10% different from your FAQ and it says "I'm sorry, I didn't understand that. Would you like to speak to a human?"

Yes. Yes they would. That's why they came to your website in the first place.

### Level 3: The RAG Bot

Now you're getting technical. You chunk your documents, embed them in a vector database, and retrieve relevant passages before generating a response.

This actually works... sometimes. The problem is that RAG is like giving someone a library card and asking them to write a sales email. They can find information, but they can't:

- Remember that this customer asked about the same product last month
- Know that the price changed last week
- Understand that when someone says "the big one" they mean the machine you discussed 3 messages ago
- Fact-check their own response before sending it
- Learn from the correction you gave them yesterday

RAG gives you **retrieval**. Sales requires **judgment**.

### Level 4: The "Agent" (Air Quotes Intentional)

You build an agent with tool use. It can search your knowledge base! It can draft emails! It has a system prompt that says "You are a helpful sales assistant"!

And then it:

- Calls the search tool once, gets a mediocre result, and writes a response based on that
- Lists your business partners as "customers" because the word appeared near their name in a document
- Forgets everything the moment the conversation ends
- Has no way to learn from mistakes
- Confidently recommends a product that can't physically do what the customer needs

This is where 99% of "AI agent" projects end up. A tool-calling LLM with no memory, no verification, and no learning. It's a goldfish that learned to use a phone.

---

## Part 3: What Would Actually Work

Let's think about this differently. What does a *great* human sales engineer actually do?

```
WHAT A GREAT SALES ENGINEER DOES:

1. LISTENS    → Understands what the customer actually needs
                (not just what they said)

2. RESEARCHES → Pulls specs, checks inventory, looks up history
                (from multiple sources, not just one document)

3. THINKS     → "Wait, they said 4mm thickness — that rules out
                 our AM series. I should recommend PF1 instead."

4. WRITES     → Drafts a response in the right tone for this
                 specific customer relationship

5. CHECKS     → Re-reads the email. "Did I get the price right?
                 Did I include the disclaimer? Is this actually
                 true?"

6. LEARNS     → Boss says "Actually, that company shut down last year,
                 stop listing them as a customer." Never makes
                 that mistake again.

7. REMEMBERS  → Next time this customer writes, knows their name,
                 their project, their preferences, their timezone.
```

That's not one skill. That's seven different cognitive functions working together. And here's the key insight:

**No single LLM call can do all seven.**

You need a *team*. A team of specialists who each do one thing really well, coordinated by someone who knows when to call on whom.

You need... a pantheon.

---

## Part 4: How Pantheon Actually Works

Pantheon doesn't have one AI agent. It has six, each named after a figure from Greek mythology (because if you're going to build something ambitious, you might as well have fun with the naming).

| Agent | Namesake | What They Do |
|-------|----------|-------------|
| **Athena** | Goddess of Strategy | Orchestrates everything. Decides which agents to call and in what order. |
| **Clio** | Muse of History | Researches. Searches your knowledge base, memory, and product database. |
| **Calliope** | Muse of Eloquence | Writes. Drafts responses in your brand voice, adapts tone per channel. |
| **Vera** | Latin for "Truth" | Fact-checks. Three-pass verification on every response before it ships. |
| **Sophia** | Goddess of Wisdom | Reflects. Learns from every interaction, logs errors, extracts patterns. |
| **Iris** | Goddess of Messages | Gathers intelligence. Company news, industry trends, web research. |

Here's what happens when a customer sends a message:

```
CUSTOMER: "What machine do you recommend for 4mm thick ABS sheets,
           1500x1000mm forming area?"

                            |
                            v
                    
                   ATHENA (The Strategist)
                   "This is a recommendation query involving
                    material thickness and size. Research first."
                            |
                            v
                    
                   CLIO (The Researcher)
                   *searches Qdrant, Mem0, product database*
                   "Found 3 matching machines. The mid-range
                    model is the best fit. Entry-level series
                    is ruled out — only handles thin gauge."
                            |
                            v
                    
                   CALLIOPE (The Writer)
                   "Here's a draft in the company's brand voice,
                    with specs as a table, warm greeting, clear CTA."
                            |
                            v
                    
                   VERA (The Fact Checker)
                   *checks every claim against the database*
                   "Draft looks good. Added product limitation
                    warning. Added pricing disclaimer. Verified
                    specs. 3 claims verified, 0 corrected."
                            |
                            v
                    
                   Response sent to customer.
                            |
                            v
                    
                   SOPHIA (The Reflector)
                   *quietly, in the background*
                   "Good interaction. Logging this as a
                    successful recommendation pattern."
```

And if the boss replies "Actually, the price went up last month" — the feedback handler stores that correction *immediately* in long-term memory. The next person who asks gets the right price. No retraining. No redeployment. It just... learns.

That's not a chatbot. That's a *colleague*.

---

## Part 5: "Cool, But I Don't Sell Thermoforming Machines"

Neither do most people! (Weird, right?)

Pantheon is a **framework**. The six agents, the memory system, the fact-checking pipeline, the feedback loops — all of that is the infrastructure. Your company, your products, your rules — that's the configuration.

Here's literally all you need to change:

```yaml
# agent.yaml — this is the ONLY file you customize

company:
  name: "Your Company"
  agent_name: "Whatever You Want To Call It"

products:
  specs_file: "your_products.json"
  rules_file: "your_rules.txt"
```

That's it. The entire 93,000-line framework reads from this one file.

### Scenario 1: You Sell SaaS

```yaml
company:
  name: "CloudMetrics Inc."
  agent_name: "Scout"
persona:
  role: "AI Sales Development Rep"
  tone: "Casual, technical, startup-friendly"
products:
  specs_file: "data/brain/plans.json"    # Your pricing tiers
  rules_file: "data/brain/rules.txt"     # "Enterprise plan requires annual commitment"
competitors:
  entries:
    - name: "Datadog"
    - name: "New Relic"
```

Scout now answers questions about your SaaS plans, compares you to Datadog, qualifies leads, and drafts follow-up emails — all fact-checked against your actual pricing.

### Scenario 2: You're a Real Estate Agency

```yaml
company:
  name: "Prestige Properties"
  agent_name: "Harper"
persona:
  role: "AI Property Advisor"
  tone: "Warm, knowledgeable, never pushy"
products:
  specs_file: "data/brain/listings.json"  # Your property listings
  rules_file: "data/brain/rules.txt"      # "Never quote a price without 'subject to market conditions'"
```

Harper remembers that the Johnsons are looking for a 3-bedroom in the school district, follows up when a matching listing comes in, and never accidentally shows them a property that's already under contract.

### Scenario 3: You Run a Manufacturing Company (Hey, That's Us)

```yaml
company:
  name: "Machinecraft Technologies"
  agent_name: "Ira"
persona:
  role: "Intelligent Revenue Assistant"
products:
  specs_file: "data/brain/machine_specs.json"
  rules_file: "data/brain/hard_rules.txt"
```

This is literally what we run in production. Every day. On real customer inquiries. The same codebase you're looking at right now.

### Scenario 4: You're a Consulting Firm

```yaml
company:
  name: "Meridian Strategy Group"
  agent_name: "Atlas"
persona:
  role: "AI Business Development Associate"
  tone: "McKinsey-polished but human"
products:
  specs_file: "data/brain/services.json"   # Your service offerings
  rules_file: "data/brain/rules.txt"       # "Never discuss pricing before qualification"
```

Atlas researches prospect companies using Iris (the intelligence agent), drafts personalized outreach based on their recent news, and qualifies inbound leads by asking the right questions.

### Scenario 5: You Sell Literally Anything B2B

If you have:
- Products or services with specs
- Customers who ask questions before buying
- A sales process that involves more than "click buy now"

Then Pantheon works for you. The agents don't care what you sell. They care about the *pattern*: research, write, verify, learn, remember.

---

## Part 6: The Stuff That's Hard to Build (That You Get for Free)

Here's what took us 6 months and $2,000 of Cursor time to build. You get it by running `git clone`:

**Memory that actually works.** Not "I'll remember this for the next 4 messages." Real long-term memory. Pantheon remembers customer preferences, past conversations, corrections, and relationship context across Telegram AND email. If a customer emails you on Monday and Telegrams you on Thursday, the agent knows it's the same person.

**Fact-checking that catches hallucinations.** Vera (the fact checker) runs three passes on every response: rule-based checks, LLM-powered claim verification against your knowledge base, and entity cross-referencing. She's the reason your agent doesn't confidently quote a product that doesn't exist.

**Learning from corrections.** When you tell the agent "No, that's wrong — the price changed last week," it stores the correction in long-term memory *immediately*. Not in a fine-tuning queue. Not in a "we'll update the model next quarter" pipeline. Right now. The next question uses the corrected data.

**Dream Mode.** Yes, really. Every night, Sophia (the reflector) consolidates the day's interactions, extracts patterns, and strengthens weak knowledge areas. Like how your brain consolidates memories during sleep. Except this one actually works on a schedule.

**Service health monitoring.** If Qdrant goes down, your agent doesn't silently start hallucinating (which is what most RAG systems do). It knows its retrieval failed and tells you.

---

## Part 7: Get Started in 10 Minutes

Okay, you're convinced (or at least curious). Here's how to get it running:

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

---

## Part 8: Under the Hood (For the Engineers)

### Architecture

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

### Configuration

Everything is configured through `agent.yaml`:

| Section | What It Controls |
|---------|-----------------|
| `company` | Name, domain, emails, admin ID |
| `persona` | Tone, style, role description |
| `memory.namespaces` | Mem0 namespace prefixes for your data |
| `products` | Path to your product specs and business rules |
| `competitors` | Competitor names and positioning |

See `agent.yaml.example` for the full schema with comments.

### Infrastructure

Pantheon uses these services (all self-hostable):

| Service | Purpose | Cost |
|---------|---------|------|
| **OpenAI** | LLM (GPT-4o) | ~$20-100/mo |
| **Qdrant** | Vector search | Free (self-hosted) or $25/mo |
| **Mem0** | Long-term memory | $20/mo or self-hosted |
| **Voyage AI** | Embeddings | ~$10/mo |
| **Jina** | Web research | Free tier available |

Optional: PostgreSQL, Neo4j, Redis, Langfuse (observability).

### Project Structure

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

### Examples

See `examples/` for complete working configurations:

- `examples/sales_agent/` — Generic industrial equipment sales agent with products, rules, and full agent.yaml

---

## Part 9: The Part Where I Ask You to Star the Repo

Look, I'm a manufacturing guy who spent $2,000 on an AI coding assistant to build an AI sales assistant. The irony is not lost on me.

But the thing works. It handles real customer inquiries for our thermoforming machine company. It's caught pricing errors that would have cost us deals. It's drafted emails that customers responded to thinking they were talking to a human.

And now it's yours.

If you find it useful, star the repo. If you build something cool with it, tell me about it. If you find a bug, open an issue.

If you want us to set it up for you, [that's an option too](PRICING.md).

Welcome to the Pantheon.

---

## License

[Business Source License 1.1](LICENSE) — free for your own use, converts to Apache 2.0 after 4 years. See [PRICING.md](PRICING.md) for details.

---

*Built by [Rushabh Doshi](https://github.com/doshirush1901) at [Machinecraft Technologies](https://machinecraft.org). 93,000 lines of Python. $2,000 of Cursor. A lot of real sales conversations. Powered by stubbornness.*
