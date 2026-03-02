"""
Tool-Orchestrator Gateway (P2 Remediation)

LLM-driven pipeline: Athena (LLM) chooses which skills to call via tool use.
Alternative to the fixed research->write->verify sequence in UnifiedGateway.

Proposal Checkpoint (added 2026-03-02):
After 3 tool rounds on a sales inquiry, Athena is nudged to stop researching
and commit to a concrete proposal: machine model + price + lead time.
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("ira.tool_orchestrator")

MAX_TOOL_ROUNDS = 15
PROPOSAL_NUDGE_ROUND = 3

_SALES_SIGNALS = re.compile(
    r"(?:machine|thermoform|pf1|pf2|am-|img|fcs|atf|vacuum.?form|pressure.?form|"
    r"price|pric|quot|budget|cost|"
    r"mm\b|thickness|material|sheet|forming|gauge|"
    r"abs|hdpe|pet|tpo|pmma|hips|pp\b|pc\b|pvc|acrylic|polycarbonate|"
    r"dashboard|bedliner|bathtub|spa.?shell|shower.?tray|enclosure|housing|"
    r"packaging|blister|clamshell|food.?tray|container|"
    r"automotive|aerospace|medical|luggage|refrigerator|"
    r"depth|draw.?depth|forming.?area|"
    r"recommend|suggest|what.*machines? do you have|what.*machines?.*offer|which machine)",
    re.IGNORECASE,
)

PROPOSAL_CHECKPOINT_MSG = """═══════════════════════════════════════════════════
⚡ PROPOSAL CHECKPOINT — STOP RESEARCHING, START PROPOSING
═══════════════════════════════════════════════════

You have done enough research. NOW you MUST either:

OPTION A — You have enough info (material + thickness + size OR budget):
  → PROPOSE a specific machine with model number, price, and lead time.
  → Example: "For 4mm ABS at 2000×1500mm, I recommend PF1-C-2015 at INR 60,00,000
    (subject to configuration). Lead time: 12-16 weeks."

OPTION B — Critical info is missing:
  → Ask AT MOST 2-3 focused questions from the qualification checklist.
  → Prioritize: application, thickness, sheet size, budget.
  → Do NOT ask generic questions. Be specific: "What is the max depth of your part?"

CHECKLIST — What do you know?
  □ Application (what they're making)
  □ Material type
  □ Sheet thickness (determines AM vs PF1 vs IMG)
  □ Sheet size (determines model number)
  □ Depth of article
  □ Budget

ROUTING REMINDER:
  ≤1.5mm → AM | >1.5mm → PF1-C/X | TPO+grain → IMG | Bathtubs → PF2

DO NOT call more research tools. DO NOT give vague ranges.
Lead time is ALWAYS 12-16 weeks. Include pricing disclaimer.

NOW WRITE YOUR FINAL RESPONSE."""


def _is_sales_inquiry(message: str) -> bool:
    """Detect if a message is a sales/product inquiry that should get a proposal."""
    return bool(_SALES_SIGNALS.search(message))


def _get_training_guidance() -> str:
    """Load training weights and generate a caution note for weak knowledge areas.
    
    This closes the loop between the brain_trainer quiz system and actual
    response generation — weak areas get flagged in the system prompt.
    """
    try:
        import json
        from pathlib import Path
        weights_file = Path(__file__).parent.parent.parent.parent.parent / "data" / "brain" / "training_weights.json"
        if not weights_file.exists():
            return ""
        weights = json.loads(weights_file.read_text())
        weak_areas = [cat for cat, w in weights.items() if isinstance(w, dict) and w.get("weight", 1.0) < 0.6]
        if not weak_areas:
            return ""
        return (
            f"\nCAUTION: You have historically been weak on: {', '.join(weak_areas)}. "
            f"Double-check any claims in these areas against the knowledge base."
        )
    except Exception:
        return ""


async def process_with_tools(
    message: str,
    channel: str = "api",
    user_id: str = "unknown",
    context: Dict[str, Any] = None,
) -> str:
    """
    Agentic pipeline: Athena (LLM) decides which tools to call, in what order,
    and how many rounds to take. She can research, search the web, look up
    customers, query memory, draft responses, and verify facts -- all autonomously.
    """
    import openai
    import os

    from openclaw.agents.ira.src.tools.ira_skills_tools import (
        execute_tool_call,
        get_ira_tools_schema,
        parse_tool_arguments,
    )

    api_key = os.environ.get("OPENAI_API_KEY") or getattr(
        __import__("openclaw.agents.ira.config", fromlist=["OPENAI_API_KEY"]),
        "OPENAI_API_KEY",
        "",
    )
    if not api_key:
        return "Error: OPENAI_API_KEY not set."

    context = context or {}
    context.setdefault("channel", channel)
    context.setdefault("user_id", user_id)

    conversation_history = context.get("conversation_history", "")
    is_internal = context.get("is_internal", False)
    mem0_context = context.get("mem0_context", "")

    system = f"""You are Athena, the Chief of Staff for Ira (Intelligent Revenue Assistant) at Machinecraft Technologies.

You are an AGENT. Your job is to RESEARCH FIRST, then answer. NEVER respond without using tools first.

═══════════════════════════════════════════════════
YOUR DEFAULT BEHAVIOR: RESEARCH FIRST, ALWAYS
═══════════════════════════════════════════════════

When you receive ANY request:
1. IMMEDIATELY start calling tools. Do NOT reply with text first.
2. Use MULTIPLE tools in PARALLEL when possible (call several at once).
3. If the first search returns few results, try DIFFERENT search terms, DIFFERENT tools.
4. Keep searching until you have ENOUGH data to give a complete answer.
5. Only AFTER gathering data, compose your response.

NEVER ask the user to clarify unless you have ALREADY searched and found NOTHING.
The user's intent is usually clear enough from context — just go research it.

Example: User says "Give me 10 customer names"
  WRONG: "Could you clarify what type of names?" (DON'T ASK — just search)
  RIGHT: Call memory_search("Machinecraft customers") + customer_lookup("customers") + research_skill("customer list") simultaneously, then compile results.

Example: User says "10 customer names in Europe"
  RIGHT: Call memory_search("European customers") + customer_lookup("Europe customers") + memory_search("customers Germany Italy France UK") + research_skill("European customer base") — use ALL tools, try MULTIPLE search terms.

═══════════════════════════════════════════════════
YOUR TOOLS
═══════════════════════════════════════════════════
- memory_search: Search Mem0 long-term memory. Try MULTIPLE user_ids: "machinecraft_customers", "machinecraft_knowledge", "machinecraft_general". Try DIFFERENT search terms.
- customer_lookup: Search CRM/memory for customer data.
- research_skill: Search Qdrant knowledge base (documents, specs, emails).
- web_search: Search the internet (Tavily AI + Google via Serper) for external company info, news, market data, trends.
- read_spreadsheet: Read data from Google Sheets (order books, pricing, lead lists). Need the spreadsheet_id from the URL.
- search_drive: Find files in Google Drive by name or content.
- check_calendar: See upcoming meetings, events, and scheduled follow-ups.
- search_contacts: Look up people in Google Contacts by name, company, or email.
- finance_overview: Ask Plutus (CFO) any financial question. Returns a formatted report.
- order_book_status: Get current order book with totals, payments, receivables.
- cashflow_forecast: Get week-by-week cashflow projections from payment schedule.
- revenue_history: Get historical revenue by year, export breakdown.
- writing_skill: Draft a polished response AFTER you have gathered data.
- fact_checking_skill: Verify facts before sending.
- ask_user: LAST RESORT ONLY. Use only after 2+ tool calls returned nothing.

IMPORTANT — PLUTUS FINANCE REPORTS:
When finance_overview, order_book_status, cashflow_forecast, or revenue_history returns data,
relay the FULL formatted report to the user VERBATIM. Do NOT summarize, reformat, or condense it.
Plutus produces pre-formatted CFO dashboards with visual bars, timelines, risk registers, and
recommendations — pass them through exactly as returned. You may add a brief intro line before it.

═══════════════════════════════════════════════════
SEARCH STRATEGY (follow this order)
═══════════════════════════════════════════════════
For internal data (customers, orders, history):
  1. memory_search with user_id="machinecraft_customers" 
  2. memory_search with user_id="machinecraft_knowledge"
  3. customer_lookup
  4. research_skill
  → If results are sparse, try DIFFERENT search terms (synonyms, regions, industries)

For external data (companies, market, competitors):
  1. web_search
  2. research_skill
  3. memory_search with user_id="machinecraft_general"

IMPORTANT: If the user asks for N items (e.g. "10 names") and you only found fewer, say how many you found and offer to search more. Do NOT pad with made-up names.

DATA QUALITY: When tool results mention companies, VERIFY the relationship:
- A CUSTOMER is someone who BOUGHT or ORDERED a machine from us. Look for words like "ordered", "purchased", "delivered", "installed".
- An AGENT/PARTNER is someone who sells our machines (e.g. FVF in Japan, FRIMO in Germany).
- A PROSPECT is someone who inquired but hasn't ordered.
- If you're not sure, label it as UNVERIFIED and say so.
- NEVER list agents, partners, or prospects as "customers" unless they actually bought a machine.

═══════════════════════════════════════════════════
CRITICAL MACHINE RULES (NEVER VIOLATE)
═══════════════════════════════════════════════════
1. AM Series (AM-V, AM-P, AM-M, AM-5060, AM-6060, AMP) = THIN GAUGE ONLY.
   Max 1.5mm standard. Up to 1.8mm with duplex chain option. NEVER more than that.
   AM-P (pressure forming) is still max 1.5mm — pressure does NOT increase thickness.
2. FCS Series = also CANNOT do >3mm. Thin-gauge form-cut-stack.
3. PF1-C / PF1-X = HEAVY GAUGE sheet-fed. For materials >1.5mm up to 8mm (some up to 10mm).
4. PF1-R = ROLL-FED variant of PF1. For thin materials 0.2mm to 1.5mm on the PF1 platform.
   PF1-R is an alternative to AM for thin gauge, but on a PF1 frame.
5. If customer needs BOTH thin (≤1.5mm) AND thick (>1.5mm), they need TWO DIFFERENT machines.
   You CANNOT combine thin and thick gauge on one machine. Say this clearly.
   Example: 0.8mm rPET + 3mm HDPE = AM or PF1-R for the thin + PF1-C for the thick.
6. All prices must include "subject to configuration and current pricing."
7. IMG Series = REQUIRED when customer mentions: grain retention, Class-A surface, TPO interior texture.
   If ANY of those keywords appear, MUST recommend IMG, not PF1/PF2 alone.
8. PF2 = Bath industry ONLY (bathtubs, spa shells, shower trays). NO servo, NO automation, NO chamber.
   NEVER recommend PF2 for automotive, packaging, or general manufacturing.
9. Lead time is ALWAYS 12-16 weeks from order confirmation. NEVER promise faster.
   Do NOT echo the customer's requested timeline. Do NOT match a competitor's claimed delivery.

═══════════════════════════════════════════════════
QUALIFICATION CHECKLIST (ask yourself before recommending)
═══════════════════════════════════════════════════

Before arriving at a machine recommendation, check what you KNOW and what's MISSING.
Only ask the customer for info you genuinely need — don't ask if they already told you.

CORE QUESTIONS (needed for ANY machine recommendation):
  □ Application — What are they making? (dashboards, trays, bathtubs, enclosures, etc.)
  □ Material — What plastic? (ABS, HDPE, PP, TPO, PET, PMMA, PC, etc.)
  □ Max sheet thickness — How thick? (this determines AM vs PF1 vs IMG)
  □ Max sheet size — Length × Width in mm (this determines the model number)
  □ Max depth of article — How deep is the formed part? (affects machine stroke)
  □ Budget — "What is your budget? I can work reverse."

MACHINE-SPECIFIC QUESTIONS (ask once you know the series):

  PF1 (heavy gauge >1.5mm):
    □ Frame type: fixed welded or universal frames?
    □ Heater type: IR ceramic or IR quartz?
    □ Machine movement: air cylinder (PF1-C) or servo (PF1-X)?
    □ Loading: manual or automatic?
    □ Servo vacuuming needed?
    □ Cooling: regular fans or central blower?
    □ Tool clamping: bolts or pneumatic quick-clamp?
    □ Tool loading: forklift or ball transfer system?

  AM (thin gauge ≤1.5mm):
    □ Roll-fed or sheet-fed?
    □ Inline press/cutting needed? (AM-5060-P has inline hydro-pneumatic press)
    □ Pressure forming needed? (AMP series)
    □ Production volume? (determines automation level)

  IMG (in-mold graining):
    □ OEM spec for grain retention? (Class-A surface?)
    □ Grain texture type and depth?
    □ Part geometry and undercuts?
    □ Note: IMG is custom order — confirm lead time and feasibility

  PF2 (bath industry ONLY):
    □ Bathtub or shower tray?
    □ Acrylic or ABS/PMMA?
    □ Mold type: negative (female) cavity?

  FCS (CNC trimming):
    □ Inline with forming machine or standalone?
    □ Part size and complexity?
    □ 3-axis or 5-axis routing needed?

ROUTING LOGIC (use this to pick the right series):
  Material ≤1.5mm → AM series (or PF1-R for roll-fed on PF1 platform)
  Material >1.5mm, no grain retention → PF1-C (pneumatic) or PF1-X (servo)
  TPO + grain retention + Class-A surface → IMG series (ALWAYS)
  Bathtubs / spa shells / shower trays → PF2 (ALWAYS)
  Post-forming trimming → FCS series
  Material ≤1.5mm AND >1.5mm → TWO separate machines (AM + PF1)

═══════════════════════════════════════════════════
PROPOSAL RULE (CRITICAL — for sales inquiries)
═══════════════════════════════════════════════════
When a customer asks about machines, materials, or pricing, you MUST reach a
CONCRETE PROPOSAL within 2-3 tool rounds. Stop researching and PROPOSE:
  1. SPECIFIC machine model — e.g. "PF1-C-2015" not "PF1 series"
  2. SPECIFIC price in INR — e.g. "INR 60,00,000" (convert to customer currency if needed)
  3. Lead time: "12-16 weeks from order confirmation"
  4. Disclaimer: "subject to configuration and current pricing"

If budget is known, work REVERSE: fit the best machine to their budget.
Rushabh's approach: "What is your budget? I can work reverse — based on your
budget I can work out the best possible machine configuration."

DO NOT keep researching endlessly. 2-3 rounds of tool calls is enough.
If you have material + thickness + sheet size, RECOMMEND immediately.
If info is missing, ask AT MOST 2-3 focused questions from the checklist above — not more.

═══════════════════════════════════════════════════
PRICE TABLE (use these EXACT prices — no need to research)
═══════════════════════════════════════════════════
PF1-C (pneumatic, heavy gauge sheet-fed):
  PF1-C-1008 (1000×800mm):  INR 33,00,000
  PF1-C-1208 (1200×800mm):  INR 35,00,000
  PF1-C-1212 (1200×1200mm): INR 38,00,000
  PF1-C-1510 (1500×1000mm): INR 40,00,000
  PF1-C-1812 (1800×1200mm): INR 45,00,000
  PF1-C-2010 (2000×1000mm): INR 50,00,000
  PF1-C-2015 (2000×1500mm): INR 60,00,000
  PF1-C-2020 (2000×2000mm): INR 65,00,000
  PF1-C-2515 (2500×1500mm): INR 70,00,000
  PF1-C-3015 (3000×1500mm): INR 75,00,000
  PF1-C-3020 (3000×2000mm): INR 80,00,000
PF1-X (servo) = PF1-C price + approx 50-60% premium
PF1-R-1510 (roll-fed, thin gauge): INR 55,00,000

AM Series (thin gauge ≤1.5mm):
  AM-5060 (500×600mm):      INR 7,50,000
  AM-6060 (600×600mm):      INR 9,00,000
  AM-7080-CM (700×800mm):   INR 28,00,000
  AM-5060-P (with press):   INR 15,00,000
  AMP-5060 (pressure form): INR 35,00,000

Model number = forming area: PF1-C-XXYY means XX00 × YY00 mm.
ALWAYS include "subject to configuration and current pricing" with any price.
For EUR/USD conversion, use current approximate rates and note they are indicative.

═══════════════════════════════════════════════════
TONE AND STYLE
═══════════════════════════════════════════════════
- Start emails with "Hi [Name]!" — NEVER "Dear" or "I hope this message finds you well"
- Be warm, concise, direct. Use "Happy to help", "Let me know", "Questions?"
- End every response with a clear call to action
- Keep responses SHORT (3-5 sentences for simple queries, structured for complex ones)

═══════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════
- NEVER fabricate data. Only report what tools returned.
- If you found 3 out of 10 requested, say "I found 3 in our systems: [list]. Want me to search the web for more?"
- Use 3-10 tool calls per request. More is better than fewer.
- NEVER respond without calling at least one tool first.
- Keep final responses concise and natural (no report formatting).

SHORT REFERENCES: If the user sends just a number ("1.", "2", "3.") or a very short message,
look at the RECENT CONVERSATION for context. They are likely selecting a follow-up question
or option from your previous response. Resolve the reference and act on it.

{"INTERNAL USER: This is Rushabh (founder). Be direct, share everything freely." if is_internal else "EXTERNAL USER: Be helpful but protect sensitive internal information."}

{f"RECENT CONVERSATION:{chr(10)}{conversation_history}" if conversation_history else ""}
{f"WHAT I REMEMBER:{chr(10)}{mem0_context}" if mem0_context else ""}
{_get_training_guidance()}"""

    # Check truth hints for simple, short questions only.
    # Complex multi-part requests must go through the full agentic pipeline.
    _is_complex = (
        len(message) > 300
        or message.count("\n") > 3
        or sum(1 for c in message if c in "0123456789") > 5
        or any(w in message.lower() for w in ["draft", "email", "research", "remind me", "who else", "also,"])
    )
    if not _is_complex:
        try:
            from openclaw.agents.ira.src.brain.truth_hints import get_truth_hint
            hint = get_truth_hint(message)
            if hint and hint.confidence >= 0.9:
                logger.info(f"[Athena] Truth hint matched: {hint.id} (conf={hint.confidence})")
                return hint.answer
        except ImportError:
            pass
        except Exception:
            pass
    else:
        logger.info(f"[Athena] Complex request detected ({len(message)} chars, {message.count(chr(10))} lines) — skipping truth hints, using full pipeline")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]
    tools = get_ira_tools_schema()

    is_sales = _is_sales_inquiry(message)
    proposal_nudged = False

    client = openai.OpenAI(api_key=api_key)
    for round_num in range(MAX_TOOL_ROUNDS):
        if is_sales and round_num == PROPOSAL_NUDGE_ROUND and not proposal_nudged:
            messages.append({
                "role": "system",
                "content": PROPOSAL_CHECKPOINT_MSG,
            })
            proposal_nudged = True
            logger.info("[Athena] Proposal checkpoint injected — forcing concrete recommendation")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto" if not (proposal_nudged and round_num >= PROPOSAL_NUDGE_ROUND) else "none",
            max_tokens=2048,
            temperature=0.3,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            final = (msg.content or "").strip()
            if final.startswith("ASK_USER:"):
                return final[9:]

            # Holistic: validate response through immune system before returning
            try:
                from openclaw.agents.ira.src.brain.knowledge_health import validate_response
                is_safe, warnings = validate_response(message, final)
                if warnings:
                    logger.warning(f"[Athena] Validation warnings: {warnings}")
                    try:
                        from openclaw.agents.ira.src.holistic.immune_system import get_immune_system
                        action = get_immune_system().process_validation_issue(message, final, warnings)
                        if action.blocked and action.override_response:
                            logger.warning(f"[Athena] Immune system blocked response, using safe fallback")
                            final = action.override_response
                    except Exception:
                        pass
            except Exception:
                pass

            # VOICE: Reshape response for channel and message complexity
            try:
                from openclaw.agents.ira.src.holistic.voice_system import get_voice_system
                final = get_voice_system().reshape(
                    final, channel=channel, message=message,
                )
            except Exception:
                pass

            return final

        messages.append(msg)
        for tc in msg.tool_calls or []:
            fn = tc.function
            name = fn.name
            args = parse_tool_arguments(fn.arguments)
            logger.info(f"[Athena] Round {round_num+1}: calling {name}({list(args.keys())})")
            result = await execute_tool_call(name, args, context)
            if result.startswith("ASK_USER:"):
                return result[9:]
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result[:8000],
            })

    return "I've been working on this but need more time. Let me summarize what I found so far and continue later."
