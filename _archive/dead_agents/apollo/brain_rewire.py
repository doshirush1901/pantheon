#!/usr/bin/env python3
"""
BRAIN REWIRE
============

Analyzes all mistakes from training, extracts patterns, and hardwires
corrections directly into Ira's brain.

Pipeline:
    1. Load mistakes + lessons
    2. Analyze patterns (hallucinations, routing errors, confusion)
    3. Generate hard rules (immutable guardrails)
    4. Build correction map (wrong claim → right answer)
    5. Write brain config files
    6. Inject hard_rules.txt into generate_answer.py's system prompt

Usage:
    python brain_rewire.py                  # Full rewire
    python brain_rewire.py --dry-run        # Preview without writing
    python brain_rewire.py --analyze-only   # Pattern analysis only
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent

MISTAKE_LOG = PROJECT_ROOT / "data" / "training" / "mistake_log.json"
LESSONS_FILE = PROJECT_ROOT / "data" / "learned_lessons" / "continuous_learnings.json"
BRAIN_DIR = PROJECT_ROOT / "data" / "brain"
GENERATE_ANSWER = PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain" / "generate_answer.py"

SERIES_IDENTITY = {
    "PF1": "Positive-forming, CLOSED CHAMBER, 1-8mm thickness, automotive interiors",
    "PF2": "Large format positive-forming, OPEN FRAME, heavy gauge",
    "AM": "Multi-station, THIN GAUGE ONLY, ≤1.5mm, high-volume packaging",
    "IMG": "In-mold graining, TEXTURED PARTS, TPO/PVC skins",
    "ATF": "Automatic thermoforming, high-volume production",
    "FCS": "Form-cut-stack, packaging lines",
}

INJECTION_MARKER = "# BRAIN REWIRE INJECTION"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def _write_json(path: Path, data, indent: int = 2):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent, default=str)


def load_mistakes() -> List[dict]:
    data = _load_json(MISTAKE_LOG)
    return data.get("mistakes", data if isinstance(data, list) else [])


def load_lessons() -> List[dict]:
    data = _load_json(LESSONS_FILE)
    return data.get("lessons", [])


# =========================================================================
# PATTERN ANALYSIS
# =========================================================================

def analyze_patterns(mistakes: List[dict]) -> dict:
    """Group mistakes into actionable categories."""
    patterns = {
        "hallucinated_models": [],
        "wrong_model_routing": [],
        "series_confusion": [],
        "spec_hallucination": [],
        "missing_disclaimer": 0,
        "deflection": 0,
        "total_mistakes": len(mistakes),
    }

    known_prefixes = {"PF1", "PF2", "AM", "IMG", "ATF", "FCS"}

    for m in mistakes:
        mtype = (m.get("type") or m.get("category") or "").lower()
        desc = (m.get("description") or m.get("mistake") or m.get("error") or "").lower()
        wrong = m.get("wrong_answer", "")
        right = m.get("correct_answer", "")

        if "hallucinated" in mtype or "hallucinated" in desc or "invented" in desc:
            model_nums = re.findall(r"[A-Z]{2,3}-?\d[\w-]*", wrong or desc)
            for num in model_nums:
                prefix = num.split("-")[0]
                if prefix not in known_prefixes:
                    patterns["hallucinated_models"].append(num)
                    continue
            if not model_nums and ("model" in desc or "machine" in desc):
                patterns["hallucinated_models"].append(wrong or desc[:80])

        if "routing" in mtype or "wrong series" in desc or "wrong model" in desc:
            patterns["wrong_model_routing"].append({
                "wrong": wrong,
                "correct": right,
                "context": desc[:120],
            })

        if "confusion" in mtype or "series" in desc:
            for s1 in known_prefixes:
                for s2 in known_prefixes:
                    if s1 != s2 and s1.lower() in desc and s2.lower() in desc:
                        patterns["series_confusion"].append(f"{s1} confused with {s2}")

        if "spec" in mtype and ("hallucin" in desc or "wrong" in desc or "fabricat" in desc):
            patterns["spec_hallucination"].append({
                "claim": wrong,
                "truth": right,
                "context": desc[:120],
            })

        if "disclaimer" in desc or "pricing disclaimer" in mtype:
            patterns["missing_disclaimer"] += 1

        if "deflect" in desc or "deflection" in mtype or "refused" in desc:
            patterns["deflection"] += 1

    patterns["hallucinated_models"] = list(set(patterns["hallucinated_models"]))
    patterns["series_confusion"] = list(set(patterns["series_confusion"]))

    return patterns


# =========================================================================
# HARD RULES GENERATION
# =========================================================================

def generate_hard_rules(patterns: dict) -> str:
    """Create immutable guardrails from observed failure patterns."""
    lines = [
        "=" * 70,
        "HARD RULES — NEVER VIOLATE THESE",
        f"Generated: {datetime.now().isoformat()}",
        f"Based on {patterns.get('total_mistakes', 0)} analyzed mistakes",
        "=" * 70,
        "",
    ]

    # RULE 1: Series identity
    lines.append("RULE 1: SERIES IDENTITY (memorize this)")
    lines.append("-" * 40)
    for series, identity in SERIES_IDENTITY.items():
        lines.append(f"  {series}: {identity}")
    lines.append("")
    lines.append("  PF1 = CLOSED CHAMBER.  PF2 = OPEN FRAME.  AM = THIN GAUGE ≤1.5mm.  IMG = GRAIN/TEXTURE.")
    lines.append("  NEVER confuse these. They are fundamentally different machines.")
    if patterns["series_confusion"]:
        lines.append(f"  Past confusions: {', '.join(patterns['series_confusion'][:10])}")
    lines.append("")

    # RULE 2: Blocked hallucinated model numbers
    lines.append("RULE 2: BLOCKED MODEL NUMBERS (these do NOT exist)")
    lines.append("-" * 40)
    if patterns["hallucinated_models"]:
        for model in sorted(set(patterns["hallucinated_models"]))[:30]:
            lines.append(f"  BLOCKED: {model}")
    else:
        lines.append("  No hallucinated models detected yet.")
    lines.append("  If you are unsure whether a model exists, say so. NEVER invent model numbers.")
    lines.append("")

    # RULE 3: Model routing corrections
    lines.append("RULE 3: MODEL ROUTING CORRECTIONS (wrong → right)")
    lines.append("-" * 40)
    if patterns["wrong_model_routing"]:
        for entry in patterns["wrong_model_routing"][:20]:
            lines.append(f"  WRONG: {entry['wrong']}  →  CORRECT: {entry['correct']}")
    else:
        lines.append("  No routing corrections recorded yet.")
    lines.append("")

    # RULE 4: Mandatory elements
    lines.append("RULE 4: MANDATORY ELEMENTS IN EVERY RESPONSE")
    lines.append("-" * 40)
    lines.append("  • Pricing: ALWAYS include \"subject to configuration and current pricing\"")
    lines.append("  • Specs: Provide FULL specs when recommending a machine (area, depth, heater, movement, price range)")
    lines.append("  • Minimum detail: Technical responses must be at least 3 sentences with concrete numbers")
    if patterns["missing_disclaimer"] > 0:
        lines.append(f"  ⚠ Pricing disclaimer was missing {patterns['missing_disclaimer']} times in training")
    lines.append("")

    # RULE 5: No deflection
    lines.append("RULE 5: DO NOT DEFLECT WHEN YOU HAVE ENOUGH INFO")
    lines.append("-" * 40)
    lines.append("  If the customer has given application, material, and thickness — RECOMMEND A MACHINE.")
    lines.append("  Do NOT say \"I need more information\" when you already have what you need.")
    lines.append("  Ask qualification questions ONLY for genuinely missing info.")
    if patterns["deflection"] > 0:
        lines.append(f"  ⚠ Deflected {patterns['deflection']} times when answer was possible")
    lines.append("")

    # RULE 6: No guessing
    lines.append("RULE 6: NEVER GUESS SPECS / LEAD TIME ALWAYS 12-16 WEEKS")
    lines.append("-" * 40)
    lines.append("  • If you don't know a spec, say \"I'll confirm the exact figure and get back to you.\"")
    lines.append("  • Lead time is ALWAYS 12-16 weeks plus shipping. No exceptions.")
    lines.append("  • Never fabricate dimensions, weights, power ratings, or cycle times.")
    if patterns["spec_hallucination"]:
        lines.append(f"  ⚠ Fabricated specs {len(patterns['spec_hallucination'])} times in training")
    lines.append("")

    return "\n".join(lines)


# =========================================================================
# CORRECTION MAP
# =========================================================================

def build_correction_map(mistakes: List[dict]) -> Dict[str, str]:
    """Map wrong claims to their correct answers."""
    corrections = {}
    for m in mistakes:
        wrong = (m.get("wrong_answer") or "").strip()
        right = (m.get("correct_answer") or "").strip()
        if wrong and right and wrong != right:
            corrections[wrong] = right
    return corrections


# =========================================================================
# BRAIN CONFIG WRITER
# =========================================================================

def write_brain_config(
    hard_rules: str,
    correction_map: Dict[str, str],
    patterns: dict,
    lessons: List[dict],
    dry_run: bool = False,
) -> dict:
    """Write all brain config files to data/brain/."""
    outputs = {}

    # hard_rules.txt
    rules_path = BRAIN_DIR / "hard_rules.txt"
    outputs["hard_rules"] = str(rules_path)
    if not dry_run:
        BRAIN_DIR.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(hard_rules)

    # correction_map.json
    cmap_path = BRAIN_DIR / "correction_map.json"
    outputs["correction_map"] = str(cmap_path)
    if not dry_run:
        _write_json(cmap_path, correction_map)

    # mistake_patterns.json
    patterns_path = BRAIN_DIR / "mistake_patterns.json"
    outputs["mistake_patterns"] = str(patterns_path)
    if not dry_run:
        _write_json(patterns_path, patterns)

    # top_lessons.json — deduped, Rushabh corrections first, max 30
    deduped = _dedupe_lessons(lessons)
    rushabh_first = sorted(
        deduped,
        key=lambda l: (
            0 if "rushabh" in (l.get("learned_from") or "").lower()
                     or "rushabh" in (l.get("source") or "").lower()
            else 1,
            l.get("timestamp") or "",
        ),
    )
    top = rushabh_first[:30]
    top_path = BRAIN_DIR / "top_lessons.json"
    outputs["top_lessons"] = str(top_path)
    if not dry_run:
        _write_json(top_path, top)

    # Mark all mistakes as fixed
    if not dry_run and MISTAKE_LOG.exists():
        data = _load_json(MISTAKE_LOG)
        raw = data.get("mistakes", data if isinstance(data, list) else [])
        for m in raw:
            m["fixed"] = True
            m["fixed_at"] = datetime.now().isoformat()
        if isinstance(data, dict):
            data["mistakes"] = raw
            _write_json(MISTAKE_LOG, data)
        else:
            _write_json(MISTAKE_LOG, raw)

    return outputs


def _dedupe_lessons(lessons: List[dict]) -> List[dict]:
    """Remove duplicate lessons by content similarity."""
    seen_keys = set()
    unique = []
    for lesson in lessons:
        text = (lesson.get("lesson") or lesson.get("feedback") or "").strip().lower()
        key = re.sub(r"\s+", " ", text)[:120]
        if key and key not in seen_keys:
            seen_keys.add(key)
            unique.append(lesson)
    return unique


# =========================================================================
# INJECTION INTO generate_answer.py
# =========================================================================

def inject_into_brain(dry_run: bool = False) -> dict:
    """
    Modify generate_answer.py to load hard_rules.txt into the system prompt.
    Inserts right before the CONTINUOUS LEARNING INJECTION comment.
    Idempotent — checks if already injected first.
    """
    result = {"already_injected": False, "injected": False, "error": None}

    if not GENERATE_ANSWER.exists():
        result["error"] = f"generate_answer.py not found at {GENERATE_ANSWER}"
        return result

    source = GENERATE_ANSWER.read_text()

    if INJECTION_MARKER in source:
        result["already_injected"] = True
        return result

    injection_block = f'''
    {INJECTION_MARKER}
    # Load hard rules from brain rewire analysis
    _hard_rules_path = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "brain" / "hard_rules.txt"
    if _hard_rules_path.exists():
        try:
            _hard_rules = _hard_rules_path.read_text().strip()
            if _hard_rules:
                base_prompt += "\\n\\n" + _hard_rules
                logger.debug("Injected hard rules from brain rewire")
        except Exception as _e:
            logger.warning("Failed to load hard rules: %s", _e, exc_info=True)

'''

    target_comment = "    # =========================================================================\n    # CONTINUOUS LEARNING INJECTION"

    if target_comment not in source:
        result["error"] = "Could not find CONTINUOUS LEARNING INJECTION anchor in generate_answer.py"
        return result

    if dry_run:
        result["injected"] = True
        result["preview"] = injection_block.strip()
        return result

    new_source = source.replace(target_comment, injection_block + target_comment)
    GENERATE_ANSWER.write_text(new_source)
    result["injected"] = True
    return result


# =========================================================================
# MAIN PIPELINE
# =========================================================================

def rewire_brain(dry_run: bool = False, analyze_only: bool = False) -> dict:
    """Run the full brain rewire pipeline."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "analyze_only": analyze_only,
    }

    print("=" * 60)
    print("BRAIN REWIRE — Hardwiring corrections into Ira")
    print("=" * 60)

    # Step 1: Load data
    print("\n[1/6] Loading mistakes...")
    mistakes = load_mistakes()
    report["mistakes_loaded"] = len(mistakes)
    print(f"  Found {len(mistakes)} mistakes")

    print("\n[2/6] Loading lessons...")
    lessons = load_lessons()
    report["lessons_loaded"] = len(lessons)
    print(f"  Found {len(lessons)} lessons")

    # Step 2: Analyze patterns
    print("\n[3/6] Analyzing patterns...")
    patterns = analyze_patterns(mistakes)
    report["patterns"] = {
        "hallucinated_models": len(patterns["hallucinated_models"]),
        "wrong_model_routing": len(patterns["wrong_model_routing"]),
        "series_confusion": len(patterns["series_confusion"]),
        "spec_hallucination": len(patterns["spec_hallucination"]),
        "missing_disclaimer": patterns["missing_disclaimer"],
        "deflection": patterns["deflection"],
    }
    print(f"  Hallucinated models: {len(patterns['hallucinated_models'])}")
    print(f"  Wrong model routing: {len(patterns['wrong_model_routing'])}")
    print(f"  Series confusion:    {len(patterns['series_confusion'])}")
    print(f"  Spec hallucination:  {len(patterns['spec_hallucination'])}")
    print(f"  Missing disclaimer:  {patterns['missing_disclaimer']}")
    print(f"  Deflection:          {patterns['deflection']}")

    if analyze_only:
        print("\n[analyze_only] Stopping here.")
        return report

    # Step 3: Generate hard rules
    print("\n[4/6] Generating hard rules...")
    hard_rules = generate_hard_rules(patterns)
    report["hard_rules_lines"] = hard_rules.count("\n") + 1
    print(f"  Generated {report['hard_rules_lines']} lines of hard rules")

    if dry_run:
        print("\n--- HARD RULES PREVIEW ---")
        print(hard_rules[:1500])
        if len(hard_rules) > 1500:
            print(f"  ... ({len(hard_rules) - 1500} more chars)")

    # Step 4: Build correction map
    print("\n[5/6] Building correction map...")
    correction_map = build_correction_map(mistakes)
    report["corrections"] = len(correction_map)
    print(f"  {len(correction_map)} wrong→right corrections")

    # Step 5: Write brain config
    print("\n[6/6] Writing brain config...")
    outputs = write_brain_config(hard_rules, correction_map, patterns, lessons, dry_run=dry_run)
    report["outputs"] = outputs
    if dry_run:
        print("  [DRY RUN] Would write to:")
    else:
        print("  Written to:")
    for name, path in outputs.items():
        print(f"    {name}: {path}")

    # Step 6: Inject into generate_answer.py
    print("\n[INJECT] Injecting hard rules loader into generate_answer.py...")
    inject_result = inject_into_brain(dry_run=dry_run)
    report["injection"] = inject_result
    if inject_result.get("already_injected"):
        print("  Already injected — skipping.")
    elif inject_result.get("injected"):
        status = "[DRY RUN] Would inject" if dry_run else "Injected"
        print(f"  {status} hard rules loader into system prompt.")
    elif inject_result.get("error"):
        print(f"  ERROR: {inject_result['error']}")

    print("\n" + "=" * 60)
    print("BRAIN REWIRE COMPLETE" + (" (dry run)" if dry_run else ""))
    print("=" * 60)

    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Brain Rewire — hardwire corrections into Ira")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze patterns, don't generate rules")
    args = parser.parse_args()

    result = rewire_brain(dry_run=args.dry_run, analyze_only=args.analyze_only)

    if args.dry_run or args.analyze_only:
        print("\n[REPORT]")
        print(json.dumps(result, indent=2, default=str))
