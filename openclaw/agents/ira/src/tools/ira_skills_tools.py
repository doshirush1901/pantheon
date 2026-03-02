"""
IRA Skills as OpenAI-Compatible Tools (P2 Remediation)

Exposes research_skill, writing_skill, fact_checking_skill as function-calling tools.
Enables LLM-driven orchestration: Athena (LLM) chooses which skills to call and in what order.
"""

import json
import logging
import os
from typing import Any, Dict, List

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
            "description": "Look up a customer or company in our CRM/memory. Returns relationship history, past orders, communication history, and preferences.",
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

    elif tool_name == "customer_lookup":
        query = arguments.get("query", "")
        results = []
        try:
            from openclaw.agents.ira.src.memory.mem0_memory import get_mem0_service
            mem0 = get_mem0_service()
            for uid in ["machinecraft_customers", "machinecraft_knowledge"]:
                memories = mem0.search(query, uid, limit=10)
                for m in memories:
                    results.append(f"[{uid}] {m.memory}")
        except Exception as e:
            logger.warning(f"Customer lookup Mem0 error: {e}")
        try:
            result = await invoke_research(f"customer {query}", context)
            if result:
                results.append(f"[knowledge_base] {result[:2000]}")
        except Exception:
            pass
        if results:
            header = (
                "WARNING: These results come from memory and documents. "
                "Not every company mentioned is a CONFIRMED CUSTOMER. "
                "A company is only a confirmed customer if the data says they BOUGHT/ORDERED a machine. "
                "Companies that are agents, prospects, competitors, or just mentioned in passing are NOT customers. "
                "Label each as CONFIRMED CUSTOMER, PROSPECT, AGENT, or UNKNOWN based on the evidence.\n\n"
            )
            return header + "\n".join(results)
        return f"(No customer data found for '{query}')"

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

    elif tool_name == "ask_user":
        question = arguments.get("question", "")
        return f"ASK_USER:{question}"

    return f"Error: Unknown tool '{tool_name}'"


def parse_tool_arguments(arguments: str) -> Dict[str, Any]:
    """Parse tool arguments from LLM response (JSON string)."""
    if not arguments or not arguments.strip():
        return {}
    try:
        return json.loads(arguments)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse tool arguments: %s", e)
        return {}
