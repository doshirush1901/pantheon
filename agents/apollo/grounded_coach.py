"""
MINERVA ENGINE — Knowledge-Grounded Pre-Send Coach
===================================================
Reviews every email draft against the actual machine database.
Catches hallucinations, enforces specs, nudges Ira to the right source.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)

import sys
_brain_path = str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain")
if _brain_path not in sys.path:
    sys.path.insert(0, _brain_path)
from machine_database import MACHINE_SPECS

client = OpenAI()

# ============================================================================
# SERIES KNOWLEDGE — hard-coded critical facts per product line
# ============================================================================

SERIES_KNOWLEDGE: Dict[str, Dict] = {
    "PF1": {
        "type": "CLOSED CHAMBER",
        "key_features": [
            "Sag control", "Pre-blow", "VERSATILE", "Many automation options",
        ],
        "automation_options": [
            "Servo drives (PF1-X)", "Auto load/unload", "Plug assist",
            "Zone heater control", "Ball transfer tool slide",
        ],
        "variants": {
            "PF1-C": "Pneumatic cylinder driven (standard)",
            "PF1-X": "All-servo (premium, faster, more precise)",
            "PF1-R": "With integrated roll feeder",
        },
        "applications": [
            "Automotive interiors", "Luggage shells", "Refrigerator liners",
            "Truck bedliners", "Enclosures", "EV battery covers",
        ],
        "critical_rules": [
            "PF1 is the VERSATILE workhorse — recommend for most thick-gauge applications.",
            "PF1-C is pneumatic, PF1-X is all-servo. Do NOT confuse them.",
        ],
    },
    "PF2": {
        "type": "OPEN FRAME",
        "key_features": [
            "NO chamber", "NO sag control", "NO automation",
            "Air cylinder driven", "BASIC machine",
        ],
        "automation_options": [],
        "variants": {},
        "applications": [
            "Bathtubs", "Spas", "Shower trays",
        ],
        "critical_rules": [
            "PF2 is for the BATH INDUSTRY ONLY (bathtubs, spas, shower trays).",
            "NEVER claim PF2 has customization, advanced controls, or automation.",
            "PF2 has NO chamber, NO sag control. It is an OPEN FRAME, BASIC machine.",
            "If customer needs automation or precision → recommend PF1 instead.",
        ],
    },
    "AM": {
        "type": "THIN GAUGE ROLL-FED",
        "key_features": [
            "Roll-fed", "Multi-station", "Max thickness ≤1.5mm",
        ],
        "automation_options": ["Servo chain indexing", "PLC/HMI control"],
        "variants": {
            "AM-standard": "Vacuum forming",
            "AMP": "Pressure forming (up to 3 bar)",
            "AM-P": "With inline press for cut-and-stack",
        },
        "applications": [
            "Blister packaging", "Trays", "Clamshells",
            "Food containers", "Electronics housings",
        ],
        "critical_rules": [
            "AM series is THIN GAUGE ONLY — max ≤1.5mm. NEVER recommend for >1.5mm.",
            "If customer mentions thick sheets (>1.5mm), redirect to PF1/PF2.",
        ],
    },
    "IMG": {
        "type": "IN-MOLD GRAINING",
        "key_features": [
            "Vacuum lamination", "Grain transfer", "Soft-feel finish",
            "Precision temperature control",
        ],
        "automation_options": ["Servo positioning", "Hot-melt compatible"],
        "variants": {},
        "applications": [
            "Automotive dashboards", "Door panels", "Console covers",
            "Armrests", "Instrument panels", "Headliners",
        ],
        "critical_rules": [
            "IMG is REQUIRED for grain retention, Class-A surfaces, TPO automotive.",
            "If customer mentions grain/texture/TPO/Class-A → MUST recommend IMG.",
            "Do NOT recommend PF1 for grain/texture work — that requires IMG.",
        ],
    },
    "FCS": {
        "type": "INLINE FORM-CUT-STACK",
        "key_features": [
            "Inline production", "Form + Cut + Stack in one line",
            "Roll-fed", "High volume",
        ],
        "automation_options": ["Servo drives (7060 models)", "Recipe management"],
        "variants": {
            "3ST": "3-station (form, cut, stack)",
            "4ST": "4-station (form, cut, hole-punch, stack)",
        },
        "applications": [
            "Food packaging trays", "Disposable cups", "Containers",
            "Medical packaging",
        ],
        "critical_rules": [
            "FCS is for HIGH-VOLUME thin-gauge packaging production.",
        ],
    },
    "UNO": {
        "type": "SINGLE STATION BASIC",
        "key_features": [
            "Entry-level", "Manual loading", "Top heater (or sandwich)",
        ],
        "automation_options": [],
        "variants": {
            "single heater": "Top heater only (thinner sheets)",
            "2H": "Sandwich heaters top & bottom (thicker sheets, better uniformity)",
        },
        "applications": [
            "Signage", "Simple trays", "Prototyping", "Small batches",
        ],
        "critical_rules": [
            "UNO is entry-level. For serious production, recommend PF1.",
        ],
    },
    "DUO": {
        "type": "DOUBLE STATION",
        "key_features": [
            "Two forming stations", "Swing-over heater", "2x output vs UNO",
        ],
        "automation_options": [],
        "variants": {},
        "applications": [
            "Higher volume signage", "Batch production",
        ],
        "critical_rules": [
            "DUO doubles output over UNO with alternating stations.",
        ],
    },
    "PLAY": {
        "type": "DESKTOP",
        "key_features": [
            "Compact", "Single phase power", "Manual operation",
        ],
        "automation_options": [],
        "variants": {},
        "applications": [
            "Prototyping", "Education", "Hobbyist projects",
        ],
        "critical_rules": [
            "PLAY is desktop/educational only. Not for production.",
        ],
    },
}

# ============================================================================
# EMAIL LENGTH RULES — word-count targets by email category
# ============================================================================

EMAIL_LENGTH_RULES: Dict[str, Dict] = {
    "qualification": {
        "min_words": 80,
        "max_words": 200,
        "guidance": "Keep it short. Ask smart questions, don't lecture.",
    },
    "pricing": {
        "min_words": 300,
        "max_words": 600,
        "guidance": "Include specs table, price, lead time, payment terms. Be thorough but not verbose.",
    },
    "recommendation": {
        "min_words": 800,
        "max_words": 1500,
        "guidance": "Detailed comparison with specs, reasoning, and clear recommendation.",
    },
    "proposal": {
        "min_words": 1200,
        "max_words": 2000,
        "guidance": "Full proposal with executive summary, specs, pricing, timeline, terms.",
    },
}

# ============================================================================
# GROUND TRUTH EXTRACTION
# ============================================================================

_MODEL_PATTERN = re.compile(
    r"\b(PF1-[CXRA]-\d{4}|PF1-XL-\d{4}|PF2-P\d{4}|AM[P]?-\d{4}(?:-P)?|"
    r"IMG-\d{4}|FCS-\d{4}-\d+ST|UNO-\d{4}(?:-2H)?|DUO-\d{4}|PLAY-\d+-DT)\b",
    re.IGNORECASE,
)

_SERIES_PATTERN = re.compile(
    r"\b(PF1|PF2|AM|IMG|FCS|UNO|DUO|PLAY)\b", re.IGNORECASE,
)


def get_ground_truth(question: str, category: str = "recommendation") -> Dict:
    """
    Extract verifiable ground truth for a question from the machine database.

    Returns machines mentioned, series info, applicable business rules,
    and the email length rule for the category.
    """
    text = question.upper()

    machines_mentioned: Dict[str, Dict] = {}
    for match in _MODEL_PATTERN.finditer(question):
        model = match.group(0).upper()
        spec = MACHINE_SPECS.get(model)
        if spec:
            machines_mentioned[model] = {
                "series": spec.series,
                "forming_area": spec.forming_area_mm,
                "max_thickness": spec.max_sheet_thickness_mm,
                "price_inr": spec.price_inr,
                "price_usd": spec.price_usd,
                "heater_kw": spec.heater_power_kw,
                "features": spec.features,
                "applications": spec.applications,
            }

    series_info: Dict[str, Dict] = {}
    for match in _SERIES_PATTERN.finditer(text):
        series = match.group(0).upper()
        if series in SERIES_KNOWLEDGE:
            series_info[series] = SERIES_KNOWLEDGE[series]

    for spec_data in machines_mentioned.values():
        s = spec_data["series"]
        if s in SERIES_KNOWLEDGE and s not in series_info:
            series_info[s] = SERIES_KNOWLEDGE[s]

    relevant_rules: List[str] = []

    thickness_match = re.search(r"(\d+(?:\.\d+)?)\s*mm", question, re.IGNORECASE)
    if thickness_match:
        thickness = float(thickness_match.group(1))
        if thickness > 1.5:
            relevant_rules.append(
                f"THICKNESS {thickness}mm > 1.5mm — AM series is NOT suitable. "
                "Recommend PF1 or PF2."
            )

    grain_keywords = ["grain", "texture", "tpo", "class-a", "class a", "soft-touch", "lamination"]
    if any(kw in question.lower() for kw in grain_keywords):
        relevant_rules.append(
            "Customer mentions grain/texture/TPO/Class-A → MUST recommend IMG series."
        )

    if any(kw in question.lower() for kw in ["price", "cost", "quote", "budget", "pricing"]):
        relevant_rules.append(
            'All prices MUST include disclaimer: "subject to configuration and current pricing."'
        )

    if "PF2" in text:
        relevant_rules.append(
            "PF2 is OPEN FRAME, BASIC, bath-industry only. "
            "NEVER claim PF2 has automation, customization, or advanced controls."
        )

    email_length_rule = EMAIL_LENGTH_RULES.get(category, EMAIL_LENGTH_RULES["recommendation"])

    return {
        "machines_mentioned": machines_mentioned,
        "series_info": series_info,
        "relevant_rules": relevant_rules,
        "email_length_rule": email_length_rule,
    }


# ============================================================================
# NEAREST-NEIGHBOR HINTS
# ============================================================================

def find_nearest_neighbors(question: str, top_k: int = 3) -> List[Dict]:
    """
    Score every machine in the database against the question and return
    the top-k most relevant as hints.
    """
    q_lower = question.lower()
    scored: List[tuple] = []

    for model, spec in MACHINE_SPECS.items():
        score = 0.0

        if model.lower() in q_lower or spec.series.lower() in q_lower:
            score += 5.0

        for app in spec.applications:
            if any(word in q_lower for word in app.lower().split() if len(word) > 3):
                score += 2.0

        for feat in spec.features:
            if any(word in q_lower for word in feat.lower().split() if len(word) > 3):
                score += 1.0

        thickness_match = re.search(r"(\d+(?:\.\d+)?)\s*mm", question, re.IGNORECASE)
        if thickness_match:
            t = float(thickness_match.group(1))
            if spec.max_sheet_thickness_mm and spec.max_sheet_thickness_mm >= t:
                score += 1.5
            if spec.min_sheet_thickness_mm and t < spec.min_sheet_thickness_mm:
                score -= 2.0

        size_match = re.search(r"(\d{3,4})\s*[xX×]\s*(\d{3,4})", question)
        if size_match and spec.forming_area_raw:
            rw, rh = int(size_match.group(1)), int(size_match.group(2))
            sw, sh = spec.forming_area_raw
            if (sw >= rw and sh >= rh) or (sw >= rh and sh >= rw):
                score += 2.0

        if score > 0:
            scored.append((model, score, spec))

    scored.sort(key=lambda x: -x[1])

    hints = []
    for model, score, spec in scored[:top_k]:
        hints.append({
            "model": model,
            "relevance_score": round(score, 1),
            "series": spec.series,
            "forming_area": spec.forming_area_mm,
            "price_inr": spec.price_inr,
            "price_usd": spec.price_usd,
            "features": spec.features[:5],
            "applications": spec.applications[:5],
        })

    return hints


# ============================================================================
# COACH REVIEW — the main LLM-powered review function
# ============================================================================

_REVIEW_SYSTEM_PROMPT = """\
You are MINERVA, the toughest pre-send coach at Machinecraft Technologies.
Your job: review an email draft against GROUND TRUTH from the machine database.

You are NOT a cheerleader. You are a FACT CHECKER. Use the FULL score range:
- 1-3: Serious errors, wrong specs, hallucinated features
- 4-5: Multiple inaccuracies or missing critical info
- 6-7: Mostly correct but has gaps or minor errors
- 8-9: Accurate and well-written with minor polish needed
- 10: Perfect — every fact verified, nothing missing

SCORING DIMENSIONS (each 1-10):
1. factual_accuracy — Are specs, prices, features CORRECT per the database?
2. completeness — Does it answer the customer's question fully?
3. series_correctness — Is the right series recommended? Are series traits correct?
4. rule_compliance — Does it follow business rules (AM thickness, IMG requirement, pricing disclaimer)?
5. tone_and_length — Professional, warm, concise? Within word-count target?

VERDICT:
- APPROVE if overall >= 7.5 AND no factual errors AND no rule violations
- REVISE otherwise

Return ONLY valid JSON (no markdown fences):
{
  "verdict": "APPROVE" or "REVISE",
  "overall_score": <float>,
  "scores": {
    "factual_accuracy": <int>,
    "completeness": <int>,
    "series_correctness": <int>,
    "rule_compliance": <int>,
    "tone_and_length": <int>
  },
  "factual_errors": ["list of specific errors found"],
  "missing_information": ["list of things that should be included"],
  "correction_guidance": "specific instructions for fixing the draft",
  "wins": "what the draft does well",
  "lesson": "one-sentence takeaway for Ira to learn from"
}
"""


def coach_review(
    question: str,
    response: str,
    category: str = "recommendation",
) -> Dict:
    """
    Review an email draft against ground truth from the machine database.

    Returns a dict with verdict, scores, errors, guidance, and a lesson.
    """
    ground_truth = get_ground_truth(question, category)
    neighbors = find_nearest_neighbors(question)

    machines_block = ""
    if ground_truth["machines_mentioned"]:
        machines_block = "MACHINES MENTIONED (from database):\n"
        for model, data in ground_truth["machines_mentioned"].items():
            machines_block += f"  {model}: area={data['forming_area']}, "
            machines_block += f"max_thickness={data['max_thickness']}mm, "
            machines_block += f"price_inr={data['price_inr']}, "
            machines_block += f"heater={data['heater_kw']}kW, "
            machines_block += f"features={data['features']}\n"

    series_block = ""
    if ground_truth["series_info"]:
        series_block = "SERIES KNOWLEDGE:\n"
        for series, info in ground_truth["series_info"].items():
            series_block += f"  {series} ({info['type']}): "
            series_block += f"features={info['key_features']}, "
            series_block += f"applications={info['applications']}\n"
            if info["critical_rules"]:
                for rule in info["critical_rules"]:
                    series_block += f"    ⚠ RULE: {rule}\n"

    rules_block = ""
    if ground_truth["relevant_rules"]:
        rules_block = "BUSINESS RULES TRIGGERED:\n"
        for rule in ground_truth["relevant_rules"]:
            rules_block += f"  ⚠ {rule}\n"

    length_rule = ground_truth["email_length_rule"]
    length_block = (
        f"EMAIL LENGTH TARGET: {length_rule['min_words']}-{length_rule['max_words']} words. "
        f"{length_rule['guidance']}"
    )

    neighbor_block = ""
    if neighbors:
        neighbor_block = "NEAREST NEIGHBOR MACHINES (possibly relevant):\n"
        for n in neighbors:
            neighbor_block += (
                f"  {n['model']} (series={n['series']}, area={n['forming_area']}, "
                f"score={n['relevance_score']})\n"
            )

    user_prompt = f"""\
CUSTOMER QUESTION:
{question}

EMAIL CATEGORY: {category}

DRAFT RESPONSE TO REVIEW:
{response}

--- GROUND TRUTH ---
{machines_block}
{series_block}
{rules_block}
{length_block}

{neighbor_block}

Review this draft. Be TOUGH. Check every fact against the database above.
If the draft claims a spec not in the ground truth, flag it.
If the draft misses a critical rule, flag it.
Score honestly — do NOT default to 7.5.
"""

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": _REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )

        raw = completion.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(raw)

    except json.JSONDecodeError:
        logger.error("Minerva: failed to parse LLM response as JSON: %s", raw[:300])
        result = {
            "verdict": "REVISE",
            "overall_score": 0.0,
            "scores": {
                "factual_accuracy": 0,
                "completeness": 0,
                "series_correctness": 0,
                "rule_compliance": 0,
                "tone_and_length": 0,
            },
            "factual_errors": ["Minerva review failed — could not parse LLM output."],
            "missing_information": [],
            "correction_guidance": "Re-run review. If persistent, check OpenAI API key.",
            "wins": "",
            "lesson": "Minerva parse failure — investigate.",
        }
    except Exception as exc:
        logger.error("Minerva: LLM call failed: %s", exc)
        result = {
            "verdict": "REVISE",
            "overall_score": 0.0,
            "scores": {
                "factual_accuracy": 0,
                "completeness": 0,
                "series_correctness": 0,
                "rule_compliance": 0,
                "tone_and_length": 0,
            },
            "factual_errors": [f"Minerva review failed: {exc}"],
            "missing_information": [],
            "correction_guidance": "Re-run review. Check API connectivity.",
            "wins": "",
            "lesson": f"Minerva call failure: {exc}",
        }

    if neighbors:
        result["nearest_neighbor_hint"] = (
            f"Closest match from database: {neighbors[0]['model']} "
            f"(series={neighbors[0]['series']}, area={neighbors[0]['forming_area']}, "
            f"relevance={neighbors[0]['relevance_score']})"
        )
    else:
        result["nearest_neighbor_hint"] = "No strong machine matches found in database."

    return result


# ============================================================================
# NUDGE FOR REVISION
# ============================================================================

def coach_nudge_for_revision(
    question: str,
    response: str,
    review: Dict,
) -> str:
    """
    Build a human-readable nudge string from a Minerva review,
    telling Ira exactly what to fix.
    """
    parts: List[str] = []

    verdict = review.get("verdict", "REVISE")
    score = review.get("overall_score", 0)
    parts.append(f"MINERVA VERDICT: {verdict} (score: {score}/10)")
    parts.append("")

    errors = review.get("factual_errors", [])
    if errors:
        parts.append("FACTUAL ERRORS — fix these before sending:")
        for i, err in enumerate(errors, 1):
            parts.append(f"  {i}. {err}")
        parts.append("")

    missing = review.get("missing_information", [])
    if missing:
        parts.append("MISSING INFORMATION — add these:")
        for i, m in enumerate(missing, 1):
            parts.append(f"  {i}. {m}")
        parts.append("")

    guidance = review.get("correction_guidance", "")
    if guidance:
        parts.append(f"CORRECTION GUIDANCE: {guidance}")
        parts.append("")

    hint = review.get("nearest_neighbor_hint", "")
    if hint:
        parts.append(f"DATABASE HINT: {hint}")
        parts.append("")

    wins = review.get("wins", "")
    if wins:
        parts.append(f"WHAT YOU DID WELL: {wins}")
        parts.append("")

    lesson = review.get("lesson", "")
    if lesson:
        parts.append(f"LESSON: {lesson}")

    return "\n".join(parts)
