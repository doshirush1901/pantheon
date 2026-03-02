#!/usr/bin/env python3
"""
BENCHY — Self-Improving Test Agent for Ira
============================================

Like the 3D printing Benchy that stress-tests overhangs, bridging, and
retraction in a single print, this agent sends carefully crafted prompts
to Ira, scores the response against a rubric, diagnoses failures, applies
fixes, and loops until the score exceeds a threshold.

Usage:
    python scripts/benchy.py                          # Run all scenarios
    python scripts/benchy.py --scenario packright     # Run one scenario
    python scripts/benchy.py --max-iterations 5       # Cap iterations
    python scripts/benchy.py --threshold 0.85         # Lower pass bar
    python scripts/benchy.py --dry-run                # Score only, no fixes
"""

import asyncio
import json
import logging
import os
import py_compile
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("\"'")
            if not os.environ.get(key) or key.endswith(("_API_KEY", "_KEY", "_TOKEN", "_URL")):
                os.environ[key] = value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("benchy")

BENCHY_LOG = PROJECT_ROOT / "data" / "holistic" / "benchy_log.jsonl"

ALLOWED_FILES = [
    PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain" / "truth_hints.py",
    PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "core" / "tool_orchestrator.py",
    PROJECT_ROOT / "data" / "brain" / "hard_rules.txt",
    PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain" / "generate_answer.py",
    PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain" / "knowledge_health.py",
]


# =============================================================================
# SCENARIOS
# =============================================================================

@dataclass
class RubricItem:
    criterion: str
    description: str
    correct: str
    weight: float = 0.1


@dataclass
class BenchyScenario:
    id: str
    name: str
    prompt: str
    rubric: List[RubricItem]
    context: Dict[str, Any] = field(default_factory=dict)


SCENARIOS: List[BenchyScenario] = [
    BenchyScenario(
        id="packright_dual_material",
        name="PackRight GmbH — Dual Material + Email + Research",
        prompt=(
            "Hi Ira,\n\n"
            "I just got off a call with a new lead — Hans Müller from PackRight GmbH "
            "in Stuttgart. They're a mid-size packaging company doing sustainable food "
            "trays. He wants to switch from a competitor (I think they use ILLIG machines "
            "currently) to us.\n\n"
            "Here's what he needs:\n"
            "1. They form 0.8mm rPET and 3mm HDPE — same machine if possible\n"
            "2. Sheet size around 1200 x 800 mm\n"
            "3. Budget is €120,000\n"
            "4. He asked specifically if our AM-5060 can handle both materials\n"
            "5. Needs delivery to Stuttgart within 4 months\n\n"
            "Can you research PackRight GmbH, recommend the right machine(s), give me "
            "the pricing in EUR, and draft a first-touch email to Hans? Make it warm but "
            "professional — reference their sustainability angle if you find anything "
            "about them online.\n\n"
            "Also, remind me — who else do we have as customers in Germany? I know there "
            "were a few."
        ),
        rubric=[
            RubricItem("am_rejected_for_thick", "AM-5060 explicitly rejected for 3mm HDPE", "Must state AM cannot handle 3mm HDPE (max 1.5mm)", 0.20),
            RubricItem("pf1_recommended_for_thick", "PF1-C or PF1-X recommended for 3mm HDPE", "Must recommend PF1-C (or PF1-X) for the 3mm HDPE line", 0.15),
            RubricItem("two_machines_stated", "Clearly states two separate machines needed", "Must say you cannot combine thin and thick on one machine", 0.15),
            RubricItem("pricing_in_eur", "Pricing given with specific numbers", "Must include specific INR prices and EUR conversion, not 'approximately' without a base number", 0.10),
            RubricItem("web_research_attempted", "Some research on PackRight or Stuttgart packaging", "Must show evidence of web search or company research (even if not found)", 0.10),
            RubricItem("email_drafted", "A draft email to Hans is included", "Must contain a draft email or message to Hans", 0.10),
            RubricItem("warm_tone", "Warm, conversational tone — Hi not Dear", "Email must start with Hi/Hey, not Dear. No 'I hope this finds you well'. Ends with CTA.", 0.10),
            RubricItem("german_customers", "German customers mentioned", "Must attempt to list German customers from memory", 0.10),
        ],
    ),
    BenchyScenario(
        id="terraform_brazil",
        name="TerraForm Brazil — Dual Material + WhatsApp + South America",
        prompt=(
            "Ira, quick brief:\n\n"
            "Maria Santos from TerraForm Packaging in São Paulo reached out. They make "
            "compostable takeaway containers for iFood (Brazil's biggest food delivery "
            "app). Currently running old Kiefel machines.\n\n"
            "Requirements:\n"
            "1. Primary line: 0.5mm PLA and 0.7mm rPET for food containers\n"
            "2. Secondary line: 4mm ABS for equipment housings (separate project)\n"
            "3. Forming area minimum 800 x 600 mm for both\n"
            "4. Total budget across both lines: USD 150,000\n"
            "5. She wants to know if one machine can do both — I said I'd check\n\n"
            "Look up TerraForm Packaging online, figure out the right machines for each "
            "line with pricing in USD, and write me a short WhatsApp-style message I can "
            "send Maria today. Keep it casual — she's very informal.\n\n"
            "Oh and what's our lead time to Brazil? Do we have any customers in South America?"
        ),
        rubric=[
            RubricItem("am_for_thin_line", "AM series (or PF1-R) recommended for 0.5-0.7mm line", "Must recommend AM or PF1-R for the thin gauge food container line", 0.15),
            RubricItem("pf1_for_abs", "PF1-C recommended for 4mm ABS", "Must recommend PF1-C (or PF1-X) for 4mm ABS housings", 0.15),
            RubricItem("two_machines_stated", "Two separate machines needed", "Must clearly state one machine cannot do both thin and thick", 0.15),
            RubricItem("pricing_in_usd", "Pricing in USD with specific numbers", "Must include specific prices with USD conversion", 0.10),
            RubricItem("web_research_attempted", "Research on TerraForm or iFood", "Must show evidence of web search attempt", 0.10),
            RubricItem("whatsapp_tone", "Casual WhatsApp-style message drafted", "Message must be casual, short, use Hi/Hey, not formal letter format", 0.15),
            RubricItem("south_america_customers", "South American customers or lead time mentioned", "Must attempt to answer about SA customers and/or Brazil lead time", 0.10),
            RubricItem("am_thickness_correct", "AM max thickness stated as 1.5mm (not 2mm)", "If AM thickness limit is mentioned, must say 1.5mm not 2mm", 0.10),
        ],
    ),
    BenchyScenario(
        id="simple_thickness_check",
        name="Simple AM Thickness — Core Business Rule",
        prompt="Can the AM-5060 handle 2.5mm thick polypropylene sheets for food packaging?",
        rubric=[
            RubricItem("am_rejected", "AM-5060 rejected for 2.5mm", "Must say AM cannot handle 2.5mm (max 1.5mm, or 1.8mm with duplex chain)", 0.40),
            RubricItem("pf1_recommended", "PF1 recommended instead", "Must recommend PF1-C or PF1-X as alternative", 0.30),
            RubricItem("thickness_limit_correct", "Correct thickness limit stated", "Must state AM limit as 1.5mm (not 2mm)", 0.30),
        ],
    ),
    BenchyScenario(
        id="pf1r_knowledge",
        name="PF1-R Roll-Fed Knowledge",
        prompt="We need a machine for 0.8mm rPET food trays, high volume, roll-fed. What do you have?",
        rubric=[
            RubricItem("am_mentioned", "AM series mentioned as option", "Must mention AM series as a thin-gauge option", 0.25),
            RubricItem("pf1r_mentioned", "PF1-R mentioned as roll-fed option", "Should mention PF1-R as the roll-fed variant on PF1 platform", 0.25),
            RubricItem("pricing_given", "Some pricing provided", "Must include at least one specific price", 0.20),
            RubricItem("not_pf1c", "Does NOT recommend PF1-C for 0.8mm", "PF1-C is for heavy gauge; should not be primary recommendation for 0.8mm", 0.30),
        ],
    ),
]


# =============================================================================
# SCORER
# =============================================================================

@dataclass
class ScoreResult:
    criterion: str
    score: float  # 0.0 or 1.0
    explanation: str
    weight: float


@dataclass
class ScoreCard:
    scenario_id: str
    overall_score: float
    results: List[ScoreResult]
    response_text: str
    iteration: int


def _get_openai_client():
    import openai
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return openai.OpenAI(api_key=api_key)


def score_response(
    scenario: BenchyScenario, response: str, iteration: int
) -> ScoreCard:
    """Score Ira's response against the scenario rubric using LLM-as-judge."""
    client = _get_openai_client()

    rubric_text = "\n".join(
        f"- {r.criterion} (weight={r.weight}): {r.description}. "
        f"CORRECT ANSWER: {r.correct}"
        for r in scenario.rubric
    )

    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict test evaluator for an AI sales assistant called Ira. "
                    "You score responses against a rubric. For each criterion, output PASS (1) "
                    "or FAIL (0) with a brief explanation.\n\n"
                    "Output ONLY valid JSON: a list of objects with keys: "
                    '"criterion", "score" (0 or 1), "explanation".\n'
                    "Be strict. If the response is vague or partially correct, score 0."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"TEST PROMPT:\n{scenario.prompt}\n\n"
                    f"IRA'S RESPONSE:\n{response}\n\n"
                    f"RUBRIC:\n{rubric_text}\n\n"
                    "Score each criterion. Output JSON array only."
                ),
            },
        ],
        max_tokens=1500,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw = result.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            parsed = parsed.get("results", parsed.get("scores", list(parsed.values())[0]))
        if not isinstance(parsed, list):
            parsed = [parsed]
    except json.JSONDecodeError:
        logger.error(f"Scorer returned invalid JSON: {raw[:200]}")
        parsed = []

    rubric_map = {r.criterion: r for r in scenario.rubric}
    results = []
    for item in parsed:
        criterion = item.get("criterion", "")
        rubric_item = rubric_map.get(criterion)
        if not rubric_item:
            for key in rubric_map:
                if key.lower() in criterion.lower() or criterion.lower() in key.lower():
                    rubric_item = rubric_map[key]
                    criterion = key
                    break
        if not rubric_item:
            continue
        results.append(ScoreResult(
            criterion=criterion,
            score=float(item.get("score", 0)),
            explanation=item.get("explanation", ""),
            weight=rubric_item.weight,
        ))

    scored_criteria = {r.criterion for r in results}
    for r in scenario.rubric:
        if r.criterion not in scored_criteria:
            results.append(ScoreResult(
                criterion=r.criterion, score=0.0,
                explanation="Not evaluated by scorer", weight=r.weight,
            ))

    total_weight = sum(r.weight for r in results)
    overall = sum(r.score * r.weight for r in results) / max(total_weight, 0.01)

    return ScoreCard(
        scenario_id=scenario.id,
        overall_score=round(overall, 3),
        results=results,
        response_text=response,
        iteration=iteration,
    )


# =============================================================================
# DIAGNOSTICIAN
# =============================================================================

def diagnose_failures(
    scenario: BenchyScenario,
    score_card: ScoreCard,
    source_files: Dict[str, str],
) -> Optional[Dict]:
    """Analyze failures and recommend a specific code fix."""
    failures = [r for r in score_card.results if r.score < 1.0]
    if not failures:
        return None

    client = _get_openai_client()

    failures_text = "\n".join(
        f"- FAILED: {f.criterion} (weight={f.weight}): {f.explanation}"
        for f in failures
    )

    files_text = "\n\n".join(
        f"=== {name} (first 3000 chars) ===\n{content[:3000]}"
        for name, content in source_files.items()
    )

    result = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a code diagnostician for an AI sales assistant called Ira. "
                    "Given test failures and the relevant source files, identify the ROOT CAUSE "
                    "and recommend ONE specific, MINIMAL fix.\n\n"
                    "Output ONLY valid JSON with keys:\n"
                    '- "file": the file path to modify (must be one of the provided files)\n'
                    '- "old_string": the EXACT string to find and replace (copy verbatim from the file)\n'
                    '- "new_string": the replacement string\n'
                    '- "reasoning": why this fix addresses the failures\n\n'
                    "RULES:\n"
                    "- Fix ONE thing at a time. The most impactful fix first.\n"
                    "- The old_string must be an EXACT substring of the file content.\n"
                    "- KEEP CHANGES MINIMAL. Do not rewrite entire sections or bloat prompts.\n"
                    "- NEVER append long instructions to the first line of a system prompt.\n"
                    "- If adding a rule, add it as a NEW bullet point in the appropriate section.\n"
                    "- If the issue is a wrong fact in truth_hints.py, fix ONLY that fact.\n"
                    "- If the issue is a missing business rule, add ONE concise rule line.\n"
                    "- Prefer fixing truth_hints.py or hard_rules.txt over tool_orchestrator.py.\n"
                    "- NEVER remove safety checks or validation logic.\n"
                    "- AM Series max thickness is 1.5mm (1.8mm with duplex chain). NEVER change this.\n"
                    "- PF1-C/PF1-X is for heavy gauge (>1.5mm). PF1-R is roll-fed for thin gauge (0.2-1.5mm).\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"TEST PROMPT:\n{scenario.prompt}\n\n"
                    f"IRA'S RESPONSE:\n{score_card.response_text[:2000]}\n\n"
                    f"FAILURES:\n{failures_text}\n\n"
                    f"SOURCE FILES:\n{files_text}\n\n"
                    "Diagnose the root cause and output ONE fix as JSON."
                ),
            },
        ],
        max_tokens=2000,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    raw = result.choices[0].message.content.strip()
    try:
        diagnosis = json.loads(raw)
        if "file" in diagnosis and "old_string" in diagnosis and "new_string" in diagnosis:
            return diagnosis
        logger.warning(f"Diagnosis missing required keys: {list(diagnosis.keys())}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Diagnostician returned invalid JSON: {raw[:200]}")
        return None


# =============================================================================
# FIXER
# =============================================================================

def apply_fix(diagnosis: Dict) -> bool:
    """Apply a diagnosed fix with compilation check and revert safety."""
    file_path_str = diagnosis.get("file", "")
    old_string = diagnosis.get("old_string", "")
    new_string = diagnosis.get("new_string", "")
    reasoning = diagnosis.get("reasoning", "")

    if not file_path_str or not old_string or old_string == new_string:
        logger.warning("Invalid fix: missing file, old_string, or no change")
        return False

    file_path = Path(file_path_str)
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path

    allowed = False
    for af in ALLOWED_FILES:
        try:
            if file_path.resolve() == af.resolve():
                allowed = True
                break
        except Exception:
            pass
    if not allowed:
        logger.warning(f"Fix rejected: {file_path} not in allowed files list")
        return False

    if not file_path.exists():
        logger.warning(f"Fix rejected: {file_path} does not exist")
        return False

    original_content = file_path.read_text()

    if old_string not in original_content:
        logger.warning(f"Fix rejected: old_string not found in {file_path.name}")
        logger.debug(f"old_string (first 100): {old_string[:100]}")
        return False

    new_content = original_content.replace(old_string, new_string, 1)
    file_path.write_text(new_content)

    if file_path.suffix == ".py":
        try:
            py_compile.compile(str(file_path), doraise=True)
            logger.info(f"Fix applied and compiled: {file_path.name}")
        except py_compile.PyCompileError as e:
            logger.error(f"Fix caused syntax error, reverting: {e}")
            file_path.write_text(original_content)
            return False

    logger.info(f"Fix applied to {file_path.name}: {reasoning[:100]}")
    return True


# =============================================================================
# LOOP CONTROLLER
# =============================================================================

def _load_source_files() -> Dict[str, str]:
    """Load the content of all allowed files for the diagnostician."""
    sources = {}
    for f in ALLOWED_FILES:
        if f.exists():
            try:
                sources[str(f.relative_to(PROJECT_ROOT))] = f.read_text()
            except Exception:
                pass
    return sources


def _log_iteration(entry: Dict):
    """Append an iteration record to the benchy log."""
    BENCHY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(BENCHY_LOG, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


async def run_scenario(
    scenario: BenchyScenario,
    max_iterations: int = 15,
    threshold: float = 0.9,
    dry_run: bool = False,
) -> ScoreCard:
    """Run a single scenario through the improve loop."""
    from openclaw.agents.ira.src.core.tool_orchestrator import process_with_tools

    logger.info(f"\n{'='*60}")
    logger.info(f"BENCHY: {scenario.name}")
    logger.info(f"{'='*60}")

    best_score = 0.0
    best_card = None

    for iteration in range(max_iterations):
        logger.info(f"\n--- Iteration {iteration + 1}/{max_iterations} ---")

        # Disable immune system blocking during test (Benchy has its own scoring)
        try:
            from openclaw.agents.ira.src.holistic.immune_system import get_immune_system
            _immune = get_immune_system()
            _immune._chronic_issues.clear()
        except Exception:
            pass

        t0 = time.time()
        try:
            response = await process_with_tools(
                message=scenario.prompt,
                channel="benchy",
                user_id="benchy_agent",
                context={
                    "is_internal": True,
                    "conversation_history": "",
                    "mem0_context": "",
                },
            )
        except Exception as e:
            logger.error(f"Ira failed to respond: {e}")
            response = f"ERROR: {e}"
        elapsed = time.time() - t0

        logger.info(f"Response ({elapsed:.1f}s, {len(response)} chars): {response[:200]}...")

        card = score_response(scenario, response, iteration)
        logger.info(f"Score: {card.overall_score:.0%}")
        for r in card.results:
            status = "PASS" if r.score >= 1.0 else "FAIL"
            logger.info(f"  [{status}] {r.criterion} ({r.weight:.0%}): {r.explanation[:80]}")

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "scenario": scenario.id,
            "iteration": iteration + 1,
            "score": card.overall_score,
            "response_length": len(response),
            "elapsed_s": round(elapsed, 1),
            "results": [
                {"criterion": r.criterion, "score": r.score, "explanation": r.explanation[:200]}
                for r in card.results
            ],
        }

        if card.overall_score > best_score:
            best_score = card.overall_score
            best_card = card

        if card.overall_score >= threshold:
            logger.info(f"\nPASS! Score {card.overall_score:.0%} >= {threshold:.0%}")
            log_entry["status"] = "PASS"
            _log_iteration(log_entry)
            break

        if dry_run:
            logger.info("Dry run — skipping fix")
            log_entry["status"] = "DRY_RUN"
            _log_iteration(log_entry)
            break

        source_files = _load_source_files()
        diagnosis = diagnose_failures(scenario, card, source_files)

        if diagnosis:
            logger.info(f"Diagnosis: {diagnosis.get('reasoning', '')[:150]}")
            fixed = apply_fix(diagnosis)
            log_entry["fix_applied"] = fixed
            log_entry["fix_file"] = diagnosis.get("file", "")
            log_entry["fix_reasoning"] = diagnosis.get("reasoning", "")[:300]

            if not fixed:
                logger.warning("Fix could not be applied — trying next iteration anyway")
        else:
            logger.warning("No diagnosis produced — cannot fix")
            log_entry["fix_applied"] = False

        log_entry["status"] = "ITERATING"
        _log_iteration(log_entry)
    else:
        logger.warning(
            f"\nDid not reach {threshold:.0%} after {max_iterations} iterations. "
            f"Best: {best_score:.0%}"
        )

    return best_card or card


async def run_all_scenarios(
    scenario_ids: Optional[List[str]] = None,
    max_iterations: int = 15,
    threshold: float = 0.9,
    dry_run: bool = False,
) -> Dict[str, ScoreCard]:
    """Run multiple scenarios and return results."""
    results = {}

    scenarios = SCENARIOS
    if scenario_ids:
        scenarios = [s for s in SCENARIOS if s.id in scenario_ids]
        if not scenarios:
            available = [s.id for s in SCENARIOS]
            logger.error(f"No matching scenarios. Available: {available}")
            return results

    for scenario in scenarios:
        card = await run_scenario(scenario, max_iterations, threshold, dry_run)
        results[scenario.id] = card

    logger.info(f"\n{'='*60}")
    logger.info("BENCHY REPORT CARD")
    logger.info(f"{'='*60}")
    for sid, card in results.items():
        status = "PASS" if card.overall_score >= threshold else "FAIL"
        logger.info(f"  [{status}] {sid}: {card.overall_score:.0%}")

    return results


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchy — Self-Improving Test Agent for Ira")
    parser.add_argument("--scenario", type=str, help="Run a specific scenario by ID")
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    parser.add_argument("--max-iterations", type=int, default=15, help="Max iterations per scenario")
    parser.add_argument("--threshold", type=float, default=0.9, help="Pass threshold (0-1)")
    parser.add_argument("--dry-run", action="store_true", help="Score only, don't apply fixes")
    parser.add_argument("--reset-immune", action="store_true", help="Reset immune system state before run")
    args = parser.parse_args()

    if args.reset_immune:
        immune_file = PROJECT_ROOT / "data" / "holistic" / "immune_state.json"
        immune_file.parent.mkdir(parents=True, exist_ok=True)
        immune_file.write_text('{"chronic_issues": {}, "total_remediations": 0, "total_blocks": 0, "last_sweep": null}')
        logger.info("Immune state reset")

    if args.list:
        print("\nAvailable Benchy scenarios:")
        for s in SCENARIOS:
            criteria = ", ".join(r.criterion for r in s.rubric)
            print(f"  {s.id}: {s.name}")
            print(f"    Criteria: {criteria}")
        sys.exit(0)

    scenario_ids = [args.scenario] if args.scenario else None

    results = asyncio.run(run_all_scenarios(
        scenario_ids=scenario_ids,
        max_iterations=args.max_iterations,
        threshold=args.threshold,
        dry_run=args.dry_run,
    ))

    all_passed = all(c.overall_score >= args.threshold for c in results.values())
    sys.exit(0 if all_passed else 1)
