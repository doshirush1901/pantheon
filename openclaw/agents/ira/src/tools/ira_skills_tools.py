"""
IRA Skills as OpenAI-Compatible Tools (Generic Email Intelligence)

Exposes research_skill, writing_skill, fact_checking_skill as function-calling tools.
Enables LLM-driven orchestration: Athena (LLM) chooses which skills to call and in what order.
"""

import asyncio
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
            "description": "Search the knowledge base (Qdrant, Mem0, ingested data). Use for specs, customer history, and any internal knowledge.",
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
            "description": "Ask CRM to look up a customer, lead, or company. Returns relationship brief: contact details, email history, deal stage, conversation summary, and next action recommendation.",
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
            "description": "Search long-term memory (Mem0) for stored facts, preferences, past conversations, and ingested data about customers or operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in memory"},
                    "user_id": {"type": "string", "description": "Optional: specific user/category to search"},
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
            "description": "Verify a draft for accuracy. Always use before finalizing a response.",
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
            "description": "Read your Gmail inbox. Returns recent or unread emails with sender, subject, date, and preview. Use when asked about new emails, unread messages, or 'what's in my inbox'.",
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
            "name": "vendor_status",
            "description": "Ask Hera (Vendor/Procurement Manager) for the vendor dashboard — vendor count, top vendors by PO volume, component categories, data collection status from Ketan. Use when asked about vendors, suppliers, procurement, or 'who supplies our PLCs?'. RELAY VERBATIM.",
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
            "name": "vendor_lead_time",
            "description": "Ask Hera for lead time and vendor info for a specific component. Use when asked 'how long does a PLC take?', 'who supplies servo motors?', 'Festo lead time', or any vendor/component question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Component name, vendor name, or category (e.g. 'Mitsubishi PLC', 'Festo pneumatic', 'heater elements', 'Electrical')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_email",
            "description": "Search Gmail. Start with simple keyword searches. Plain keywords work best. Use advanced syntax (from:, subject:, after:) only to narrow down. Try broader keywords if first search returns nothing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query — use plain keywords first, add Gmail operators only to narrow down"},
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
            "description": "Actually send an email. Call after the user approves a draft. Supports HTML for rich formatting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body (plain text fallback)"},
                    "body_html": {"type": "string", "description": "Optional: HTML-formatted email body. If provided, recipient sees this; plain text body is the fallback."},
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
            "description": "Draft an email, auto-enriched with data from CRM, knowledge base, Google Contacts, and Mem0. Returns draft for review — does NOT send. Call customer_lookup and/or search_contacts to resolve recipient email first. Pass results from prior tool calls as 'context'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address (or name if email unknown — tool will try to resolve via Google Contacts)"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "intent": {"type": "string", "description": "What the email should convey"},
                    "context": {"type": "string", "description": "Pass results from prior tool calls (customer_lookup, research_skill, search_contacts). Grounds the email in real data."},
                },
                "required": ["to", "subject", "intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lead_intelligence",
            "description": "Gather deep company intelligence: recent news, expansions, acquisitions, industry trends, and website analysis. Use when researching a company before outreach or when you need external context about a prospect.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name to research"},
                    "context": {"type": "string", "description": "Additional context about why you're researching this company"},
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "latest_news",
            "description": "Search for the latest real-world news on any topic, company, industry, or region. Use for ice-breakers in sales emails or when you need current events context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "News search query"},
                    "country": {"type": "string", "description": "2-letter country code to filter (e.g. 'de', 'nl', 'in'). Leave empty for global."},
                    "category": {"type": "string", "description": "News category: business, technology, science, world, environment, politics. Comma-separated for multiple."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_website",
            "description": "Scrape a company's website to understand what they do, their products, and capabilities. Use when you need to know what a company actually makes.",
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
            "description": "Read your Gmail inbox. Returns recent or unread emails with sender, subject, date, and preview. Use when asked about new emails, unread messages, or 'what's in my inbox'.",
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
            "description": "Search Gmail. IMPORTANT: Start with simple keyword searches like 'customer name quote'. Plain keywords work best and match Gmail's natural search. Only use advanced syntax (from:, subject:, after:) if a simple search returns too many results. If the first search returns nothing, try broader keywords before giving up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query — use plain keywords first (e.g. 'customer name AM-P'), add Gmail operators only to narrow down"},
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
            "description": "Actually send an email. Call this after the user approves a draft. Supports HTML for rich formatting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body (plain text fallback)"},
                    "body_html": {"type": "string", "description": "Optional: HTML-formatted email body. Use <h2>, <strong>, <ul>, <table> for professional formatting. If provided, recipient sees this; plain text body is the fallback."},
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
            "description": "Draft an email, auto-enriched with real data from CRM, knowledge base, Google Contacts, and Mem0. Returns a draft for review — does NOT send. IMPORTANT: Before calling this, you SHOULD call customer_lookup and/or search_contacts to resolve the recipient's email address if you only have a name. Also call research_skill to gather relevant product/company data, then pass those results as 'context'. The tool also does its own enrichment, but explicit context from prior tool calls produces much better drafts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address (or name if email unknown — tool will try to resolve via Google Contacts)"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "intent": {"type": "string", "description": "What the email should convey"},
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
                    "company": {"type": "string", "description": "Company name to research (e.g. 'Acme Corp', 'Example GmbH', 'Sample Industries')"},
                    "context": {"type": "string", "description": "Additional context about why you're researching this company (e.g. 'preparing outreach for PF1-X quote', 'follow-up on trade show meeting')"},
                },
                "required": ["company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "latest_news",
            "description": "Search for the latest real-world news on any topic, company, industry, or region via NewsData.io. Use for ice-breakers in sales emails (e.g. 'congratulations on your expansion'), industry trend hooks, or when you need current events context. Complements lead_intelligence — use lead_intelligence for deep company dossiers, use latest_news for fresh headline-level news.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "News search query (e.g. 'thermoforming industry', 'EV battery manufacturing Germany', 'packaging company expansion')"},
                    "country": {"type": "string", "description": "2-letter country code to filter news (e.g. 'de' for Germany, 'nl' for Netherlands, 'in' for India). Leave empty for global."},
                    "category": {"type": "string", "description": "News category filter: business, technology, science, world, environment, politics. Comma-separated for multiple. Leave empty for default business+technology+science."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_website",
            "description": "Scrape a company's website to understand what they do, their products, and their capabilities. Use when you need to know what a company actually makes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Company website domain (e.g. 'example-company.com', 'sample-mfg.de'). Can also extract from email — just pass the part after @."},
                    "company": {"type": "string", "description": "Company name for context in the search query"},
                },
                "required": ["domain"],
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
    {
        "type": "function",
        "function": {
            "name": "log_sales_training",
            "description": "Log a new sales strategy or pattern when you observe a successful outreach pattern or when a deal interaction reveals a reusable strategy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short name for the strategy"},
                    "trigger": {"type": "string", "description": "When to use this strategy"},
                    "wrong_approach": {"type": "string", "description": "What NOT to do"},
                    "right_approach": {"type": "string", "description": "Step-by-step correct approach"},
                    "example": {"type": "string", "description": "Real example from a deal (optional)"},
                    "tool_chain": {"type": "string", "description": "Which tools to use in sequence (optional)"},
                },
                "required": ["title", "trigger", "wrong_approach", "right_approach"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "owner_voice",
            "description": "Ask how the owner would reply to a customer message. Returns owner-style draft based on real email patterns. Use when drafting emails to match the owner's tone and style.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_message": {"type": "string", "description": "The customer's message to respond to"},
                    "company": {"type": "string", "description": "Customer company name (helps match per-customer style)"},
                    "context": {"type": "string", "description": "Conversation context or background"},
                },
                "required": ["customer_message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_sales_training",
            "description": "Log a new sales strategy or pattern to Ira's sales training log. Use when Rushabh teaches you a new sales technique, when you observe a successful outreach pattern, or when a deal interaction reveals a reusable strategy. This is how you learn and remember sales approaches for future use.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short name for the strategy (e.g. 'News-Driven Follow-Up for Stale Deals')"},
                    "trigger": {"type": "string", "description": "When to use this strategy (e.g. 'Hot deal with no reply for 5+ days')"},
                    "wrong_approach": {"type": "string", "description": "What NOT to do (e.g. 'Generic follow-ups like just checking in')"},
                    "right_approach": {"type": "string", "description": "Step-by-step correct approach"},
                    "example": {"type": "string", "description": "Real example from a deal (optional but valuable)"},
                    "tool_chain": {"type": "string", "description": "Which tools to use in sequence (optional)"},
                },
                "required": ["title", "trigger", "wrong_approach", "right_approach"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_case_studies",
            "description": "Find relevant customer case studies. Returns documented success stories for use in emails, proposals, or conversations. Use when you need social proof or reference stories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Free-text search (e.g. 'bedliner', 'automotive HDPE', 'large machine Europe')"},
                    "industry": {"type": "string", "description": "Industry filter (e.g. 'automotive', 'packaging', 'sanitary')"},
                    "material": {"type": "string", "description": "Material filter (e.g. 'HDPE', 'ABS', 'PP', 'TPO')"},
                    "machine_type": {"type": "string", "description": "Machine series filter (e.g. 'PF1', 'PF2', 'IMG', 'AM')"},
                    "application": {"type": "string", "description": "Application filter (e.g. 'bedliner', 'bathtub', 'fridge liner')"},
                    "country": {"type": "string", "description": "Country filter (e.g. 'India', 'Germany', 'Netherlands')"},
                    "format": {"type": "string", "enum": ["one_liner", "paragraph", "full"], "description": "Output format: one_liner for email snippets, paragraph for proposals, full for complete case study"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_case_study",
            "description": "Build a new case study from existing project data. Synthesizes emails, project files, and specs into a structured, publishable case study.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Customer name and project description (e.g. 'Customer-H automotive project for OEM partner')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_linkedin_post",
            "description": "Draft a LinkedIn post. Can be based on a case study, product launch, event, or any topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "What the post is about (e.g. 'automotive project case study', 'K2025 recap', 'new PF1-X-1210 launch')"},
                    "case_study_id": {"type": "string", "description": "Optional: ID of a published case study to base the post on (e.g. 'customer-automotive-project')"},
                    "post_type": {"type": "string", "enum": ["customer_story", "product_launch", "teaser", "announcement", "india_pride", "event", "personal_story"], "description": "Type of post to draft"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "content_calendar",
            "description": "Ask Arachne (content scheduler) to view or manage the content calendar — LinkedIn posts, newsletters, and their schedule. Use when asked 'what's scheduled this month?', 'schedule a LinkedIn post', 'what content is coming up?', or 'populate the content calendar'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["view", "schedule", "approve", "skip", "populate"], "description": "Action: view (show calendar), schedule (add item), approve/skip (by ID), populate (auto-fill LinkedIn slots)"},
                    "channel": {"type": "string", "description": "Filter by channel: 'linkedin' or 'newsletter'"},
                    "scheduled_date": {"type": "string", "description": "Date in YYYY-MM-DD format. For 'view': start date. For 'schedule': target date."},
                    "title": {"type": "string", "description": "Title/topic for the content item (required for 'schedule')"},
                    "content_ref": {"type": "string", "description": "Path to the content draft file (for 'schedule')"},
                    "item_id": {"type": "string", "description": "Calendar item ID (for 'approve' or 'skip')"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assemble_newsletter",
            "description": "Assemble the monthly newsletter from multiple sources (case studies, product spotlights, events, industry news). By default shows a preview without sending.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Newsletter title"},
                    "sections": {"type": "string", "description": "Comma-separated sections: new_orders, case_study, product_spotlight, event, industry_insight"},
                    "dry_run": {"type": "boolean", "description": "If true (default), assemble and preview without sending. Set false to actually send."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "distribution_status",
            "description": "Ask Arachne for content distribution status — what's been sent, what's pending approval, recent activity. Use when asked 'did the newsletter go out?', 'what's pending?', 'content distribution report'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Filter by channel: 'linkedin' or 'newsletter'. Leave empty for all."},
                },
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
        except Exception as e:
            logger.debug("Progress callback failed: %s", e)

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
            except Exception as e:
                logger.debug("Qdrant fallback retrieval failed: %s", e)
        
        return "\n\n".join(results_parts) if results_parts else "(No results found in knowledge base)"

    elif tool_name == "web_search":
        import httpx

        query = arguments.get("query", "")
        company = arguments.get("company", "")
        results_parts = []
        search_query = f"{company} {query}".strip() if company else query

        tavily_key = os.environ.get("TAVILY_API_KEY", "")
        serper_key = os.environ.get("SERPER_API_KEY", "")

        async def _tavily_search(q: str) -> List[str]:
            if not tavily_key:
                return []
            parts = []
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": tavily_key,
                            "query": q,
                            "search_depth": "advanced",
                            "max_results": 5,
                            "include_answer": True,
                        },
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("answer"):
                        parts.append(f"[tavily_answer] {data['answer']}")
                    for r in data.get("results", [])[:5]:
                        title = r.get("title", "")
                        content = r.get("content", "")[:400]
                        url = r.get("url", "")
                        if content:
                            parts.append(f"[tavily] {title}: {content} ({url})")
            except Exception as e:
                logger.debug("Tavily search failed: %s", e)
            return parts

        async def _serper_search(q: str) -> List[str]:
            if not serper_key:
                return []
            parts = []
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        "https://google.serper.dev/search",
                        json={"q": q, "num": 5},
                        headers={"X-API-KEY": serper_key},
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    kg = data.get("knowledgeGraph", {})
                    if kg.get("description"):
                        parts.append(f"[google_kg] {kg.get('title', '')}: {kg['description']}")
                    for r in data.get("organic", [])[:5]:
                        title = r.get("title", "")
                        snippet = r.get("snippet", "")
                        if snippet:
                            parts.append(f"[google] {title}: {snippet}")
                    for paa in data.get("peopleAlsoAsk", [])[:2]:
                        parts.append(f"[google_paa] Q: {paa.get('question', '')} A: {paa.get('snippet', '')}")
            except Exception as e:
                logger.debug("Serper search failed: %s", e)
            return parts

        async def _jina_search(q: str) -> List[str]:
            parts = []
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.get(
                        f"https://s.jina.ai/{q}",
                        headers={"Accept": "application/json"},
                    )
                if resp.status_code == 200 and len(resp.text.strip()) > 50:
                    parts.append(f"[jina] {resp.text[:3000]}")
            except Exception as e:
                logger.debug("Jina search failed: %s", e)
            return parts

        # Run Tavily + Serper + Jina concurrently
        tavily_res, serper_res, jina_res = await asyncio.gather(
            _tavily_search(search_query),
            _serper_search(search_query),
            _jina_search(search_query),
            return_exceptions=True,
        )
        for batch in (tavily_res, serper_res):
            if isinstance(batch, list):
                results_parts.extend(batch)
        # Jina is a fallback — only use if primary sources returned nothing
        if not results_parts and isinstance(jina_res, list):
            results_parts.extend(jina_res)

        # Iris enrichment (company-specific intelligence)
        if company:
            try:
                from openclaw.agents.ira.src.agents.iris_skill import iris_enrich
                iris_ctx = {"company": company, "query": query}
                iris_result = await iris_enrich(iris_ctx)
                if iris_result:
                    for k, v in iris_result.items():
                        if v and len(str(v)) > 10:
                            results_parts.append(f"[iris:{k}] {v}")
            except Exception as e:
                logger.debug("Iris enrichment failed: %s", e)

        # Website scraping (when company specified and results still thin)
        if company and len(results_parts) < 3:
            try:
                domain = company.lower().replace(" ", "").replace(",", "")
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        f"https://r.jina.ai/https://www.{domain}.com",
                        headers={"Accept": "text/plain"},
                    )
                if resp.status_code == 200 and len(resp.text) > 100:
                    results_parts.append(f"[website:{domain}.com] {resp.text[:2000]}")
            except Exception as e:
                logger.debug("Website scrape failed for %s: %s", company, e)

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

        # NewsData.io for latest headlines
        try:
            from openclaw.agents.ira.src.tools.newsdata_client import search_news
            news_result = await search_news(query=company, max_results=3)
            if news_result and not news_result.startswith("("):
                results_parts.append(f"[newsdata] {news_result}")
        except Exception as e:
            logger.debug("Lead intelligence NewsData search failed: %s", e)

        # Tavily web search fallback
        if len(results_parts) < 3:
            tavily_key = os.environ.get("TAVILY_API_KEY", "")
            if tavily_key:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=20) as client:
                        resp = await client.post(
                            "https://api.tavily.com/search",
                            json={
                                "api_key": tavily_key,
                                "query": f"{company} latest news expansion manufacturing",
                                "search_depth": "advanced",
                                "max_results": 5,
                                "include_answer": True,
                            },
                        )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("answer"):
                            results_parts.append(f"[news_summary] {data['answer']}")
                        for r in data.get("results", [])[:3]:
                            content = r.get("content", "")[:300]
                            if content:
                                results_parts.append(f"[news] {r.get('title', '')}: {content}")
                except Exception as e:
                    logger.debug("Lead intelligence Tavily search failed: %s", e)

        # CRM history for this company
        try:
            from openclaw.agents.ira.src.skills.invocation import invoke_crm_lookup
            crm_result = await invoke_crm_lookup(company, context)
            if crm_result and "don't have anyone" not in crm_result:
                results_parts.append(f"[crm_history] {crm_result}")
        except Exception as e:
            logger.debug("CRM lookup failed for %s: %s", company, e)

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

        # 2. Mem0 fallback
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

    elif tool_name == "scrape_website":
        domain = arguments.get("domain", "")
        company = arguments.get("company", domain)
        try:
            from openclaw.agents.ira.src.agents.hermes.board_meeting import BoardMeetingResearcher
            researcher = BoardMeetingResearcher()
            result = researcher._scrape_website(f"info@{domain}", company)
            return result if result else f"(No content found on {domain}. Site may block scrapers or domain may be incorrect.)"
        except Exception as e:
            return f"(Website scrape error: {e})"

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
        body_html = arguments.get("body_html", "")
        thread_id = arguments.get("thread_id", "")
        if not to or not subject or not body:
            return "(Error: to, subject, and body are all required)"
        try:
            from openclaw.agents.ira.src.tools.google_tools import gmail_send
            return gmail_send(to=to, subject=subject, body=body, body_html=body_html, thread_id=thread_id)
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
                f"DRAFT EMAIL (not sent — needs approval):\n\n"
                f"To: {draft.to}\n"
                f"Subject: {draft.subject}\n\n"
                f"{draft.body}"
                f"{sources_note}"
            )
        except ImportError:
            return "(Email drafting not available.)"
        except Exception as e:
            return f"(Draft email error: {e})"

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

    elif tool_name == "latest_news":
        query = arguments.get("query", "")
        country = arguments.get("country", "")
        category = arguments.get("category", "")
        try:
            from openclaw.agents.ira.src.tools.newsdata_client import search_news
            return await search_news(
                query=query,
                country=country,
                category=category,
                max_results=5,
            )
        except Exception as e:
            logger.warning("latest_news failed: %s", e)
            return f"(News search error: {e})"

    elif tool_name == "log_sales_training":
        try:
            from openclaw.agents.ira.src.agents.chiron import get_chiron
            return get_chiron().log_pattern(
                title=arguments.get("title", ""),
                trigger=arguments.get("trigger", ""),
                wrong_approach=arguments.get("wrong_approach", ""),
                right_approach=arguments.get("right_approach", ""),
                example=arguments.get("example", ""),
                tool_chain=arguments.get("tool_chain", ""),
            )
        except Exception as e:
            logger.warning("log_sales_training failed: %s", e)
            return f"(Sales training log error: {e})"

    elif tool_name == "owner_voice":
        customer_message = arguments.get("customer_message", "")
        company = arguments.get("company", "")
        voice_context = arguments.get("context", "")
        try:
            from openclaw.agents.ira.src.agents.delphi import consult_rushabh_voice
            result = await consult_rushabh_voice(customer_message, company, voice_context)
            if result:
                return f"[Owner's voice] {result}"
            return "(Owner voice not trained yet. Run: python -m openclaw.agents.ira.src.agents.echo.agent build)"
        except ImportError as e:
            return f"(Owner voice agent not available: {e})"
        except Exception as e:
            logger.warning("owner_voice failed: %s", e)
            return f"(Owner voice error: {e})"

    elif tool_name == "find_case_studies":
        try:
            from openclaw.agents.ira.src.agents.cadmus import find_case_studies as _find_cs
            return await _find_cs(
                query=arguments.get("query", ""),
                industry=arguments.get("industry", ""),
                material=arguments.get("material", ""),
                machine_type=arguments.get("machine_type", ""),
                application=arguments.get("application", ""),
                country=arguments.get("country", ""),
                format=arguments.get("format", "paragraph"),
                context=context,
            )
        except Exception as e:
            logger.warning("find_case_studies failed: %s", e)
            return f"(Case study search error: {e})"

    elif tool_name == "build_case_study":
        query = arguments.get("query", "")
        try:
            from openclaw.agents.ira.src.agents.cadmus import build_case_study as _build_cs
            return await _build_cs(query, context)
        except Exception as e:
            logger.warning("build_case_study failed: %s", e)
            return f"(Case study build error: {e})"

    elif tool_name == "draft_linkedin_post":
        try:
            from openclaw.agents.ira.src.agents.cadmus import draft_linkedin_post as _draft_li
            return await _draft_li(
                topic=arguments.get("topic", ""),
                case_study_id=arguments.get("case_study_id", ""),
                post_type=arguments.get("post_type", "customer_story"),
                context=context,
            )
        except Exception as e:
            logger.warning("draft_linkedin_post failed: %s", e)
            return f"(LinkedIn post draft error: {e})"

    elif tool_name == "content_calendar":
        try:
            from openclaw.agents.ira.src.agents.arachne import content_calendar as _content_cal
            return await _content_cal(
                action=arguments.get("action", "view"),
                channel=arguments.get("channel", ""),
                scheduled_date=arguments.get("scheduled_date", ""),
                title=arguments.get("title", ""),
                content_ref=arguments.get("content_ref", ""),
                item_id=arguments.get("item_id", ""),
                context=context,
            )
        except Exception as e:
            logger.warning("content_calendar failed: %s", e)
            return f"(Content calendar error: {e})"

    elif tool_name == "assemble_newsletter":
        try:
            from openclaw.agents.ira.src.agents.arachne import assemble_newsletter_tool as _assemble_nl
            return await _assemble_nl(
                title=arguments.get("title", ""),
                sections=arguments.get("sections", ""),
                dry_run=arguments.get("dry_run", True),
                context=context,
            )
        except Exception as e:
            logger.warning("assemble_newsletter failed: %s", e)
            return f"(Newsletter assembly error: {e})"

    elif tool_name == "distribution_status":
        try:
            from openclaw.agents.ira.src.agents.arachne import distribution_status as _dist_status
            return await _dist_status(
                channel=arguments.get("channel", ""),
                context=context,
            )
        except Exception as e:
            logger.warning("distribution_status failed: %s", e)
            return f"(Distribution status error: {e})"

    return f"Error: Unknown tool '{tool_name}'"


_TOOL_SCHEMAS: Dict[str, Dict[str, type]] = {
    "research_skill": {"query": str},
    "web_search": {"query": str, "company": str},
    "customer_lookup": {"query": str},
    "memory_search": {"query": str, "user_id": str},
    "writing_skill": {"query": str, "research_summary": str},
    "fact_checking_skill": {"draft": str, "original_query": str},
    "read_spreadsheet": {"spreadsheet_id": str, "range": str},
    "search_drive": {"query": str},
    "check_calendar": {"days": int},
    "search_contacts": {"query": str},
    "read_inbox": {"max_results": int, "unread_only": bool},
    "search_email": {"query": str, "max_results": int},
    "read_email_message": {"message_id": str},
    "read_email_thread": {"thread_id": str, "max_messages": int},
    "send_email": {"to": str, "subject": str, "body": str, "body_html": str, "thread_id": str},
    "draft_email": {"to": str, "subject": str, "intent": str, "context": str},
    "lead_intelligence": {"company": str, "context": str},
    "latest_news": {"query": str, "country": str, "category": str},
    "scrape_website": {"domain": str, "company": str},
    "run_analysis": {"task": str, "code": str, "data": str},
    "ask_user": {"question": str},
    "correction_report": {},
    "log_sales_training": {"title": str, "trigger": str, "wrong_approach": str, "right_approach": str, "example": str, "tool_chain": str},
    "owner_voice": {"customer_message": str, "company": str, "context": str},
    "find_case_studies": {"query": str, "industry": str, "material": str, "machine_type": str, "application": str, "country": str, "format": str},
    "build_case_study": {"query": str},
    "draft_linkedin_post": {"topic": str, "case_study_id": str, "post_type": str},
    "content_calendar": {"action": str, "channel": str, "scheduled_date": str, "title": str, "content_ref": str, "item_id": str},
    "assemble_newsletter": {"title": str, "sections": str, "dry_run": bool},
    "distribution_status": {"channel": str},
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
        logger.warning("Failed to parse tool arguments (len=%d): %s — raw: %.200s", len(arguments), e, arguments)
        return {"_parse_error": str(e)}
