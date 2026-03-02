# Pantheon Pricing

Pantheon is an **open-core** project. The framework is source-available under the
[Business Source License 1.1](LICENSE) and converts to Apache 2.0 after 4 years.

---

## Tiers

### Community (Free)
**For individuals, startups, and companies using Pantheon for their own business.**

- Full framework: orchestration, memory, RAG, feedback loops, training
- All 6 agents: Athena, Clio, Calliope, Vera, Sophia, Iris
- Telegram + Email channels
- Self-hosted (you run your own infra)
- Community support via GitHub Issues

**You can:** Build and run your own sales agent for your company at no cost.

**You cannot:** Resell Pantheon as a hosted service to others.

---

### Pro ($99/month)
**For teams that want to move fast.**

- Everything in Community
- Private Discord channel with the maintainers
- Priority bug fixes (48hr response)
- Monthly office hours / architecture review (30 min)
- Early access to new agents and features
- `examples/` for 5+ industries (SaaS, manufacturing, real estate, consulting, e-commerce)

---

### Enterprise ($499/month or custom)
**For companies building products on top of Pantheon.**

- Everything in Pro
- Commercial license (host Pantheon as a service for your customers)
- White-label rights (remove Pantheon branding)
- Dedicated Slack channel
- Custom agent development support
- SLA: 24hr response, 1-week fix for critical bugs
- Architecture consulting (2 hrs/month)

---

### Setup Service ($2,000 one-time)
**We set up Pantheon for your company.**

- We configure `agent.yaml` for your business
- Ingest your product catalog, pricing, and knowledge base
- Set up Telegram bot + Email channel
- Train the agent on your sales playbook
- 2 weeks of tuning and feedback
- Handoff with documentation

---

## What's Included in Each Tier

| Feature | Community | Pro | Enterprise |
|---------|:---------:|:---:|:----------:|
| Full framework source code | Yes | Yes | Yes |
| All 6 agents (Athena, Clio, Calliope, Vera, Sophia, Iris) | Yes | Yes | Yes |
| Telegram + Email channels | Yes | Yes | Yes |
| Deep Dive research | Yes | Yes | Yes |
| Memory system (Mem0, Qdrant, Neo4j) | Yes | Yes | Yes |
| Feedback loops + Dream Mode | Yes | Yes | Yes |
| Brain Trainer (/train) | Yes | Yes | Yes |
| Self-hosted deployment | Yes | Yes | Yes |
| Community support (GitHub) | Yes | Yes | Yes |
| Private Discord | - | Yes | Yes |
| Priority bug fixes | - | Yes | Yes |
| Monthly office hours | - | Yes | Yes |
| Industry-specific examples | - | Yes | Yes |
| Commercial hosting license | - | - | Yes |
| White-label rights | - | - | Yes |
| Dedicated Slack | - | - | Yes |
| Architecture consulting | - | - | Yes |
| SLA | - | - | Yes |

---

## FAQ

**Can I use Pantheon for free in production?**
Yes. The Community tier lets you run Pantheon for your own company at no cost.

**What counts as "hosted service"?**
If you charge customers to use a Pantheon-powered agent (e.g., "AI Sales Agent as a Service"),
that requires an Enterprise license. Using it internally for your own sales team is free.

**What are my infrastructure costs?**
Pantheon requires: OpenAI API (~$20-100/mo depending on volume), Qdrant (free self-hosted or
$25/mo cloud), Mem0 ($20/mo or self-hosted), and optionally Voyage AI ($10/mo for embeddings).
Total: ~$50-150/month for a typical deployment.

**Can I modify the source code?**
Yes. You can modify anything. You just can't resell the modified version as a hosted service
without an Enterprise license.

**When does it become fully open source?**
4 years after each version's release, it converts to Apache 2.0 automatically.

---

## Contact

- Email: rushabh@machinecraft.org
- GitHub: github.com/machinecraft/pantheon
