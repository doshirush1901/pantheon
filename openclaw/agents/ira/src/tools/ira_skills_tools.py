"""
IRA Skills as OpenAI-Compatible Tools (P2 Remediation)

Exposes research_skill, writing_skill, fact_checking_skill as function-calling tools.
Enables LLM-driven orchestration: Athena (LLM) chooses which skills to call and in what order.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ira.tools.skills")

IRA_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "research_skill",
            "description": "Search Machinecraft's knowledge base (Qdrant, Mem0, Neo4j, machine database). Use for product specs, customer history, order data, pricing, and any internal knowledge.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The question or topic to research"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for external information. Use for company research, industry news, competitor analysis, market trends, or any information not in our internal knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "company": {"type": "string", "description": "Company name if researching a specific company"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "customer_lookup",
            "description": "Ask Mnemosyne (CRM agent) to look up a customer, lead, or company. Returns full relationship brief: contact details, email history, deal stage, conversation summary, and Mnemosyne's recommendation for next action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Customer name, company name, or email to look up"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_list_customers",
            "description": "List CONFIRMED Machinecraft customers — companies that actually BOUGHT machines. Pulls from order history (2014-2025), NOT from leads or prospects. Use when asked for 'customers', 'customer list', 'who bought machines', 'latest customers', or 'how many customers'. Do NOT use this for leads/prospects — use crm_pipeline for that.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_pipeline",
            "description": "Ask Mnemosyne for a full sales pipeline overview: leads by stage, by priority, reply rates, drip status. Use when Rushabh asks about pipeline health or sales performance.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_drip_candidates",
            "description": "Ask Mnemosyne which leads are ready for the next drip email. Returns a prioritized list with her recommendations for each lead.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finance_overview",
            "description": "Ask Plutus (Chief of Finance) any financial question. Returns a pre-formatted CFO report with KPIs, visual bars, risk register, and recommendations. IMPORTANT: relay the output VERBATIM to the user without summarizing or reformatting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The financial question to answer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "order_book_status",
            "description": "Ask Plutus for the current order book with per-project breakdown. Returns pre-formatted report. RELAY VERBATIM to user.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cashflow_forecast",
            "description": "Ask Plutus for week-by-week cashflow projections from payment schedule. Returns pre-formatted report. RELAY VERBATIM to user.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "revenue_history",
            "description": "Ask Plutus for historical revenue by year and export breakdown. Returns pre-formatted report. RELAY VERBATIM to user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Specific revenue question or period (e.g. 'FY2024', 'last 5 years', 'export revenue')"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_search",
            "description": "Search Ira's long-term memory (Mem0) for stored facts, preferences, past conversations, and ingested data about customers, orders, or Machinecraft operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in memory"},
                    "user_id": {"type": "string", "description": "Optional: specific user/category to search (e.g. 'machinecraft_customers', 'machinecraft_knowledge')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "writing_skill",
            "description": "Draft a response, email, or document based on research findings. Use after gathering information with other tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The original user query"},
                    "research_summary": {"type": "string", "description": "All research findings to base the draft on"},
                },
                "required": ["query", "research_summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fact_checking_skill",
            "description": "Verify a draft for accuracy against the machine database, AM series thickness rules, and pricing disclaimers. Always use before finalizing a response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft": {"type": "string", "description": "The draft response to verify"},
                    "original_query": {"type": "string", "description": "The original user question"},
                },
                "required": ["draft", "original_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_spreadsheet",
            "description": "Read data from a Google Sheet. Use for order books, pricing lists, lead lists, or any tabular data stored in Google Sheets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "The spreadsheet ID from the Google Sheets URL (the long string between /d/ and /edit)"},
                    "range": {"type": "string", "description": "Sheet name and cell range, e.g. 'Sheet1!A1:Z100' or just 'Sheet1'"},
                },
                "required": ["spreadsheet_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_drive",
            "description": "Search Google Drive for files by name or content. Use when asked to find documents, presentations, spreadsheets, or PDFs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (file name, keywords, or content to find)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_calendar",
            "description": "Check upcoming calendar events. Use for scheduling questions, meeting lookups, or availability checks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Number of days to look ahead (default 7)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_contacts",
            "description": "Search Google Contacts for a person, company, or email address. Returns names, emails, phone numbers, and organizations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Name, company, or email to search for"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_inbox",
            "description": "Read Rushabh's Gmail inbox. Returns recent or unread emails with sender, subject, date, and preview. Use when asked about new emails, unread messages, or 'what's in my inbox'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Number of emails to fetch (default 10, max 20)"},
                    "unread_only": {"type": "boolean", "description": "If true, only return unread emails (default true)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_email",
            "description": "Search Rushabh's Gmail using Gmail search syntax. Use for finding specific emails by sender, subject, date range, attachments, etc. Examples: 'from:john@example.com', 'subject:invoice after:2026/01/01', 'has:attachment from:customer'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query (same syntax as Gmail search bar)"},
                    "max_results": {"type": "integer", "description": "Max results to return (default 10, max 20)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_email_message",
            "description": "Read the full content of a specific email by its message ID. Use after read_inbox or search_email to get the complete email body.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The Gmail message ID (from read_inbox or search_email results)"},
                },
                "required": ["message_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_email_thread",
            "description": "Read a full email conversation thread. Use to see the complete back-and-forth in a conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "The Gmail thread ID"},
                    "max_messages": {"type": "integer", "description": "Max messages to include (default 10)"},
                },
                "required": ["thread_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email from Rushabh's Gmail. IMPORTANT: Always confirm with Rushabh before sending. Never send without explicit approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body (plain text)"},
                    "thread_id": {"type": "string", "description": "Optional: thread ID to reply in an existing conversation"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_email",
            "description": "Draft an email using Ira's voice, auto-enriched with real data from CRM, knowledge base, Google Contacts, and Mem0. Returns a draft for review — does NOT send. IMPORTANT: Before calling this, you SHOULD call customer_lookup and/or search_contacts to resolve the recipient's email address if you only have a name. Also call research_skill to gather relevant product/company data, then pass those results as 'context'. The tool also does its own enrichment, but explicit context from prior tool calls produces much better drafts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address (or name if email unknown — tool will try to resolve via Google Contacts)"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "intent": {"type": "string", "description": "What the email should convey (e.g. 'follow up on PF1 quote', 'introduce Machinecraft')"},
                    "context": {"type": "string", "description": "IMPORTANT: Pass results from prior tool calls here (customer_lookup, research_skill, search_contacts results). This grounds the email in real data instead of hallucinating."},
                },
                "required": ["to", "subject", "intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lead_intelligence",
            "description": "Ask Iris (intelligence agent) to gather deep company intelligence: recent news, expansions, acquisitions, industry trends, geopolitical context, and website analysis. Use when researching a specific company before outreach, or when you need real-time external context about a prospect or customer. Returns structured intelligence hooks for sales conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name to research (e.g. 'TSN', 'Parat Halvorsen', 'VDL Roden')"},
                    "context": {"type": "string", "description": "Additional context about why you're researching this company (e.g. 'preparing outreach for PF1-X quote', 'follow-up on trade show meeting')"},
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discovery_scan",
            "description": "Ask Prometheus (the market discovery agent) to find new products and industries where vacuum forming can be applied. Scans emerging sectors like battery storage, EV, drones, renewable energy, medical devices, modular construction. Can scan a specific industry, evaluate a product idea, or run a full sweep across all tracked industries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Industry to scan (e.g. 'battery storage', 'drone manufacturing'), product idea to evaluate (e.g. 'EV battery enclosures'), or 'sweep' for full multi-industry scan"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_analysis",
            "description": "Ask Hephaestus (the program builder) to forge and execute a Python program. Use when you need to compute, aggregate, count, rank, filter, or transform data from previous tool calls. You can either describe the TASK in plain English (Hephaestus writes the code) OR provide the code directly. Pass data from previous tool calls via the 'data' parameter. The script runs in a sandboxed subprocess with a 60s timeout. If the first attempt fails, Hephaestus auto-retries with a fix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Natural-language description of what to compute (e.g. 'group emails by sender domain, count per company, rank top 10'). Hephaestus will write the code."},
                    "code": {"type": "string", "description": "Pre-written Python code to execute directly. Use print() to output results. If both task and code are provided, code takes priority."},
                    "data": {"type": "string", "description": "Data from previous tool calls to make available as the variable DATA in the script"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "Ask the user a clarifying question when you need more information to complete a task. Use this instead of guessing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The clarifying question to ask the user"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "correction_report",
            "description": "Ask Nemesis (the correction-hungry learning agent) for a report on logged mistakes and pending corrections. Use when the user asks 'what mistakes have you made?', 'show correction report', 'what have you learned from corrections?', or 'Nemesis report'. Returns total corrections, unapplied count, repeat offenders, and recent pending corrections.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


def get_ira_tools_schema() -> List[Dict[str, Any]]:
    """Return OpenAI-compatible tools list for chat.completions.create(tools=...)."""
    return IRA_TOOLS_SCHEMA


async def execute_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    context: Dict[str, Any],
) -> str:
    """Execute an IRA skill by name. Called when LLM returns tool_calls."""
    validation_err = _validate_tool_args(tool_name, arguments)
    if validation_err:
        logger.warning(f"[Security] Tool arg validation failed for {tool_name}: {validation_err}")
        return f"(Error: {validation_err})"

    try:
        from openclaw.agents.ira.src.skills.invocation import (
            invoke_research,
            invoke_verify,
            invoke_write,
        )
    except ImportError:
        return "Error: Skill invocation unavailable."

    # Notify progress callback if available
    progress_fn = context.get("_progress_callback")
    if progress_fn:
        try:
            progress_fn(tool_name)
        except Exception:
            pass

    # Holistic: track agent invocation in endocrine system
    _tool_agent_map = {
        "research_skill": "clio",
        "writing_skill": "calliope",
        "fact_checking_skill": "vera",
        "web_search": "iris",
        "lead_intelligence": "iris",
        "customer_lookup": "mnemosyne",
        "crm_list_customers": "mnemosyne",
        "crm_pipeline": "mnemosyne",
        "crm_drip_candidates": "mnemosyne",
        "discovery_scan": "prometheus",
        "finance_overview": "plutus",
        "order_book_status": "plutus",
        "cashflow_forecast": "plutus",
        "revenue_history": "plutus",
        "read_inbox": "hermes",
        "search_email": "hermes",
        "read_email_message": "hermes",
        "read_email_thread": "hermes",
        "send_email": "hermes",
        "draft_email": "hermes",
        "run_analysis": "hephaestus",
        "correction_report": "nemesis",
    }
    _agent_name = _tool_agent_map.get(tool_name)
    if _agent_name:
        try:
            from openclaw.agents.ira.src.holistic.endocrine_system import get_endocrine_system
            get_endocrine_system().signal_invocation(_agent_name)
        except Exception:
            pass

    if tool_name == "research_skill":
        query = arguments.get("query", "")
        results_parts = []
        
        # Primary search
        result = await invoke_research(query, context)
        if result:
            results_parts.append(f"[primary] {result}")
        
        # If primary search returned little, try Qdrant directly with the raw query
        if not result or len(result) < 100:
            try:
                from openclaw.agents.ira.src.brain.qdrant_retriever import retrieve as qdrant_retrieve
                rag = qdrant_retrieve(query, top_k=8)
                if hasattr(rag, 'citations') and rag.citations:
                    for c in rag.citations[:5]:
                        results_parts.append(f"[qdrant:{c.filename}] {c.text[:400]}")
            except Exception:
                pass
        
        return "\n\n".join(results_parts) if results_parts else "(No results found in knowledge base)"

    elif tool_name == "web_search":
        query = arguments.get("query", "")
        company = arguments.get("company", "")
        results_parts = []
        search_query = f"{company} {query}".strip() if company else query
        
        # 1. Tavily AI search (best for agent queries, returns clean content)
        tavily_key = os.environ.get("TAVILY_API_KEY", "")
        if tavily_key:
            try:
                import httpx
                resp = httpx.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": search_query,
                        "search_depth": "advanced",
                        "max_results": 5,
                        "include_answer": True,
                    },
                    timeout=20,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("answer"):
                        results_parts.append(f"[tavily_answer] {data['answer']}")
                    for r in data.get("results", [])[:5]:
                        title = r.get("title", "")
                        content = r.get("content", "")[:400]
                        url = r.get("url", "")
                        if content:
                            results_parts.append(f"[tavily] {title}: {content} ({url})")
            except Exception as e:
                logger.debug(f"Tavily search failed: {e}")
        
        # 2. Serper Google search (structured Google results)
        serper_key = os.environ.get("SERPER_API_KEY", "")
        if serper_key:
            try:
                import httpx
                resp = httpx.post(
                    "https://google.serper.dev/search",
                    json={"q": search_query, "num": 5},
                    headers={"X-API-KEY": serper_key},
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Knowledge graph
                    kg = data.get("knowledgeGraph", {})
                    if kg.get("description"):
                        results_parts.append(f"[google_kg] {kg.get('title', '')}: {kg['description']}")
                    # Organic results
                    for r in data.get("organic", [])[:5]:
                        title = r.get("title", "")
                        snippet = r.get("snippet", "")
                        if snippet:
                            results_parts.append(f"[google] {title}: {snippet}")
                    # People Also Ask
                    for paa in data.get("peopleAlsoAsk", [])[:2]:
                        results_parts.append(f"[google_paa] Q: {paa.get('question', '')} A: {paa.get('snippet', '')}")
            except Exception as e:
                logger.debug(f"Serper search failed: {e}")
        
        # 3. Jina fallback (if Tavily and Serper both unavailable)
        if not results_parts:
            try:
                import httpx
                resp = httpx.get(
                    f"https://s.jina.ai/{search_query}",
                    timeout=20,
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200 and len(resp.text.strip()) > 50:
                    results_parts.append(f"[jina] {resp.text[:3000]}")
            except Exception:
                pass
        
        # 4. Iris enrichment (company-specific intelligence)
        if company:
            try:
                from openclaw.agents.ira.src.agents.iris_skill import iris_enrich
                iris_ctx = {"company": company, "query": query}
                iris_result = await iris_enrich(iris_ctx)
                if iris_result:
                    for k, v in iris_result.items():
                        if v and len(str(v)) > 10:
                            results_parts.append(f"[iris:{k}] {v}")
            except Exception:
                pass
        
        # 5. Website scraping (when company specified)
        if company and len(results_parts) < 3:
            try:
                import httpx
                domain = company.lower().replace(" ", "").replace(",", "")
                resp = httpx.get(
                    f"https://r.jina.ai/https://www.{domain}.com",
                    timeout=15,
                    headers={"Accept": "text/plain"},
                )
                if resp.status_code == 200 and len(resp.text) > 100:
                    results_parts.append(f"[website:{domain}.com] {resp.text[:2000]}")
            except Exception:
                pass
        
        return "\n\n".join(results_parts) if results_parts else "(No web results found)"

    elif tool_name == "lead_intelligence":
        company = arguments.get("company", "")
        extra_context = arguments.get("context", "")
        results_parts = []

        # Iris enrichment (primary)
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_iris_enrich
            iris_ctx = {"company": company, "query": extra_context or company}
            iris_result = await invoke_iris_enrich(iris_ctx)
            if iris_result:
                for k, v in iris_result.items():
                    if v and len(str(v)) > 10:
                        results_parts.append(f"[iris:{k}] {v}")
        except Exception as e:
            logger.debug(f"Iris enrichment failed: {e}")

        # Web search for latest news
        if not results_parts or len(results_parts) < 3:
            tavily_key = os.environ.get("TAVILY_API_KEY", "")
            if tavily_key:
                try:
                    import httpx
                    resp = httpx.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": tavily_key,
                            "query": f"{company} latest news expansion manufacturing",
                            "search_depth": "advanced",
                            "max_results": 5,
                            "include_answer": True,
                        },
                        timeout=20,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("answer"):
                            results_parts.append(f"[news_summary] {data['answer']}")
                        for r in data.get("results", [])[:3]:
                            content = r.get("content", "")[:300]
                            if content:
                                results_parts.append(f"[news] {r.get('title', '')}: {content}")
                except Exception:
                    pass

        # CRM history for this company
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_crm_lookup
            crm_result = await invoke_crm_lookup(company, context)
            if crm_result and "don't have anyone" not in crm_result:
                results_parts.append(f"[crm_history] {crm_result}")
        except Exception:
            pass

        return "\n\n".join(results_parts) if results_parts else f"(No intelligence found for '{company}')"

    elif tool_name == "customer_lookup":
        query = arguments.get("query", "")
        results_parts = []

        # 1. Mnemosyne CRM lookup (primary)
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_crm_lookup
            crm_result = await invoke_crm_lookup(query, context)
            if crm_result and "don't have anyone" not in crm_result:
                results_parts.append(f"[CRM]\n{crm_result}")
        except Exception as e:
            logger.debug(f"Mnemosyne lookup failed: {e}")

        # 2. Qdrant ira_customers collection
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchText
            qdrant = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
            qdrant_filter = Filter(
                should=[
                    FieldCondition(key="company", match=MatchText(text=query)),
                    FieldCondition(key="name", match=MatchText(text=query)),
                    FieldCondition(key="country", match=MatchText(text=query)),
                ]
            )
            hits, _ = qdrant.scroll(
                collection_name="ira_customers",
                scroll_filter=qdrant_filter,
                limit=5,
                with_payload=True,
            )
            for hit in hits:
                p = hit.payload or {}
                name = p.get("name", "")
                company = p.get("company", "")
                country = p.get("country", "")
                machines = p.get("machines", [])
                parts = [f"{name} at {company} ({country})"]
                if machines:
                    parts.append(f"Machines: {', '.join(machines)}")
                results_parts.append(f"[qdrant_customers] {' | '.join(parts)}")
        except Exception as e:
            logger.debug(f"Qdrant customer lookup failed: {e}")

        # 3. Mem0 fallback
        if not results_parts:
            try:
                from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
                mem0 = get_mem0_service()
                for uid in ["machinecraft_customers", "machinecraft_knowledge"]:
                    memories = mem0.search(query, uid, limit=10)
                    for m in memories:
                        results_parts.append(f"[{uid}] {m.memory}")
            except Exception as e:
                logger.warning(f"Customer lookup Mem0 error: {e}")

        if results_parts:
            return "\n\n".join(results_parts)
        return f"(No customer data found for '{query}')"

    elif tool_name == "crm_list_customers":
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_crm_list_customers
            return await invoke_crm_list_customers(context)
        except Exception as e:
            return f"(Customer list error: {e})"

    elif tool_name == "crm_pipeline":
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_crm_pipeline
            return await invoke_crm_pipeline(context)
        except Exception as e:
            return f"(Mnemosyne pipeline error: {e})"

    elif tool_name == "crm_drip_candidates":
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_crm_drip
            return await invoke_crm_drip(context)
        except Exception as e:
            return f"(Mnemosyne drip error: {e})"

    elif tool_name == "finance_overview":
        query = arguments.get("query", "")
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_finance_overview
            return await invoke_finance_overview(query, context)
        except Exception as e:
            return f"(Finance overview error: {e})"

    elif tool_name == "order_book_status":
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_order_book_status
            return await invoke_order_book_status(context)
        except Exception as e:
            return f"(Order book error: {e})"

    elif tool_name == "cashflow_forecast":
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_cashflow_forecast
            return await invoke_cashflow_forecast(context)
        except Exception as e:
            return f"(Cashflow forecast error: {e})"

    elif tool_name == "revenue_history":
        query = arguments.get("query", "")
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_revenue_history
            return await invoke_revenue_history(query, context)
        except Exception as e:
            return f"(Revenue history error: {e})"

    elif tool_name == "memory_search":
        query = arguments.get("query", "")
        user_id = arguments.get("user_id", "")
        results = []
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            search_ids = [user_id] if user_id else [
                "machinecraft_knowledge", "machinecraft_customers",
                "machinecraft_pricing", "machinecraft_processes",
                "machinecraft_general",
            ]
            for uid in search_ids:
                memories = mem0.search(query, uid, limit=10)
                for m in memories:
                    results.append(f"[{uid}] {m.memory}")
        except Exception as e:
            logger.warning(f"Memory search error: {e}")
        return "\n".join(results) if results else f"(No memories found for '{query}')"

    elif tool_name == "writing_skill":
        query = arguments.get("query", "")
        research_summary = arguments.get("research_summary", "")
        ctx = dict(context)
        ctx["research_output"] = research_summary
        result = await invoke_write(query, ctx)
        return result or "(Draft empty)"

    elif tool_name == "fact_checking_skill":
        draft = arguments.get("draft", "")
        original_query = arguments.get("original_query", "")
        result = await invoke_verify(draft, original_query, context)
        return result or draft

    elif tool_name == "read_spreadsheet":
        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_name = arguments.get("range", "Sheet1")
        try:
            from openclaw.agents.ira.src.tools.google_tools import sheets_read
            return sheets_read(spreadsheet_id, range_name)
        except ImportError:
            return "(Google Sheets not available. Install: pip install google-api-python-client)"
        except Exception as e:
            return f"(Spreadsheet error: {e})"

    elif tool_name == "search_drive":
        query = arguments.get("query", "")
        try:
            from openclaw.agents.ira.src.tools.google_tools import drive_list
            return drive_list(query)
        except ImportError:
            return "(Google Drive not available.)"
        except Exception as e:
            return f"(Drive error: {e})"

    elif tool_name == "check_calendar":
        days = arguments.get("days", 7)
        try:
            from openclaw.agents.ira.src.tools.google_tools import calendar_upcoming
            return calendar_upcoming(days)
        except ImportError:
            return "(Google Calendar not available.)"
        except Exception as e:
            return f"(Calendar error: {e})"

    elif tool_name == "search_contacts":
        query = arguments.get("query", "")
        try:
            from openclaw.agents.ira.src.tools.google_tools import contacts_search
            return contacts_search(query)
        except ImportError:
            return "(Google Contacts not available.)"
        except Exception as e:
            return f"(Contacts error: {e})"

    elif tool_name == "read_inbox":
        max_results = arguments.get("max_results", 10)
        unread_only = arguments.get("unread_only", True)
        try:
            from openclaw.agents.ira.src.tools.google_tools import gmail_read_inbox
            return gmail_read_inbox(max_results=max_results, unread_only=unread_only)
        except ImportError:
            return "(Gmail not available. Install: pip install google-api-python-client google-auth-oauthlib)"
        except Exception as e:
            return f"(Inbox error: {e})"

    elif tool_name == "search_email":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)
        try:
            from openclaw.agents.ira.src.tools.google_tools import gmail_search
            return gmail_search(query=query, max_results=max_results)
        except ImportError:
            return "(Gmail not available.)"
        except Exception as e:
            return f"(Email search error: {e})"

    elif tool_name == "read_email_message":
        message_id = arguments.get("message_id", "")
        if not message_id:
            return "(Error: message_id is required)"
        try:
            from openclaw.agents.ira.src.tools.google_tools import gmail_read_message
            return gmail_read_message(message_id=message_id)
        except ImportError:
            return "(Gmail not available.)"
        except Exception as e:
            return f"(Read message error: {e})"

    elif tool_name == "read_email_thread":
        thread_id = arguments.get("thread_id", "")
        max_messages = arguments.get("max_messages", 10)
        if not thread_id:
            return "(Error: thread_id is required)"
        try:
            from openclaw.agents.ira.src.tools.google_tools import gmail_get_thread
            return gmail_get_thread(thread_id=thread_id, max_messages=max_messages)
        except ImportError:
            return "(Gmail not available.)"
        except Exception as e:
            return f"(Thread read error: {e})"

    elif tool_name == "send_email":
        to = arguments.get("to", "")
        subject = arguments.get("subject", "")
        body = arguments.get("body", "")
        thread_id = arguments.get("thread_id", "")
        if not to or not subject or not body:
            return "(Error: to, subject, and body are all required)"
        try:
            from openclaw.agents.ira.src.tools.google_tools import gmail_send
            return gmail_send(to=to, subject=subject, body=body, thread_id=thread_id)
        except ImportError:
            return "(Gmail not available.)"
        except Exception as e:
            return f"(Send email error: {e})"

    elif tool_name == "draft_email":
        to = arguments.get("to", "")
        subject = arguments.get("subject", "")
        intent = arguments.get("intent", "")
        email_context = arguments.get("context", "")
        if not to or not subject or not intent:
            return "(Error: to, subject, and intent are all required)"
        try:
            from openclaw.agents.ira.tools.email import ira_email_draft
            draft = ira_email_draft(to=to, subject=subject, intent=intent, context=email_context)
            sources_note = ""
            if draft.context_used:
                sources_note = f"\n[Data sources used: {', '.join(draft.context_used)}]"
            return (
                f"DRAFT EMAIL (not sent — needs Rushabh's approval):\n\n"
                f"To: {draft.to}\n"
                f"Subject: {draft.subject}\n\n"
                f"{draft.body}"
                f"{sources_note}"
            )
        except ImportError:
            return "(Email drafting not available.)"
        except Exception as e:
            return f"(Draft email error: {e})"

    elif tool_name == "discovery_scan":
        query = arguments.get("query", "")
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_discovery_scan
            return await invoke_discovery_scan(query, context)
        except Exception as e:
            return f"(Discovery scan error: {e})"

    elif tool_name == "run_analysis":
        task = arguments.get("task", "")
        code = arguments.get("code", "")
        data = arguments.get("data", "")
        if not task and not code:
            return "(Error: provide either a 'task' description or 'code' to execute)"
        is_internal = context.get("is_internal", False)
        if not is_internal:
            return "(Hephaestus is only available for internal users.)"
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_hephaestus
            return await invoke_hephaestus(task=task, code=code, data=data, context=context)
        except ImportError:
            return "(Hephaestus not available.)"
        except Exception as e:
            return f"(Hephaestus error: {e})"

    elif tool_name == "ask_user":
        question = arguments.get("question", "")
        return f"ASK_USER:{question}"

    elif tool_name == "correction_report":
        try:
            from openclaw.agents.ira.src.agents.nemesis.agent import get_nemesis
            return get_nemesis().get_hungry_report()
        except Exception as e:
            logger.warning(f"correction_report failed: {e}")
            return f"(Nemesis report unavailable: {e})"

    return f"Error: Unknown tool '{tool_name}'"


_TOOL_SCHEMAS: Dict[str, Dict[str, type]] = {
    "send_email": {"to": str, "subject": str, "body": str, "thread_id": str},
    "draft_email": {"to": str, "subject": str, "intent": str, "context": str},
    "run_analysis": {"task": str, "code": str, "data": str},
    "read_spreadsheet": {"spreadsheet_id": str, "range": str},
    "search_email": {"query": str, "max_results": int},
    "customer_lookup": {"query": str},
    "search_contacts": {"query": str},
    "lead_intelligence": {"company": str, "context": str},
}

_MAX_ARG_LENGTH = 16000


def _validate_tool_args(tool_name: str, args: Dict[str, Any]) -> Optional[str]:
    """Validate tool arguments against schemas. Returns error string or None."""
    schema = _TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return None
    for key, val in args.items():
        if key not in schema:
            continue
        expected = schema[key]
        if not isinstance(val, expected):
            return f"Argument '{key}' must be {expected.__name__}, got {type(val).__name__}"
        if isinstance(val, str) and len(val) > _MAX_ARG_LENGTH:
            return f"Argument '{key}' exceeds max length ({len(val)} > {_MAX_ARG_LENGTH})"
    return None


def parse_tool_arguments(arguments: str) -> Dict[str, Any]:
    """Parse tool arguments from LLM response (JSON string)."""
    if not arguments or not arguments.strip():
        return {}
    try:
        return json.loads(arguments)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse tool arguments: %s", e)
        return {}
