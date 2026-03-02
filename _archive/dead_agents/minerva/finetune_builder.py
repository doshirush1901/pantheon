#!/usr/bin/env python3
"""
MINERVA — Fine-Tune Dataset Builder
=====================================

Formats all corrections, lessons, and machine knowledge into
OpenAI fine-tuning JSONL format.

Usage:
    python agents/minerva/finetune_builder.py --build
    python agents/minerva/finetune_builder.py --upload
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).parent.parent.parent

sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

_brain_path = str(PROJECT_ROOT / "openclaw" / "agents" / "ira" / "src" / "brain")
if _brain_path not in sys.path:
    sys.path.insert(0, _brain_path)

from machine_database import MACHINE_SPECS

_apollo_path = str(PROJECT_ROOT / "agents" / "apollo")
if _apollo_path not in sys.path:
    sys.path.insert(0, _apollo_path)

from grounded_coach import SERIES_KNOWLEDGE

logger = logging.getLogger("minerva.finetune_builder")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

SYSTEM_MSG = "You are Ira, Machinecraft Technologies' thermoforming expert."

LESSONS_PATH = PROJECT_ROOT / "data" / "learned_lessons" / "continuous_learnings.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "training"
OUTPUT_FILE = OUTPUT_DIR / "finetune_dataset.jsonl"


def _make_example(user_content: str, assistant_content: str) -> Dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ]
    }


# ============================================================================
# LESSON EXAMPLES
# ============================================================================

def _build_lesson_examples() -> List[Dict]:
    if not LESSONS_PATH.exists():
        logger.warning("No lessons file at %s — skipping lesson examples", LESSONS_PATH)
        return []

    data = json.loads(LESSONS_PATH.read_text())
    lessons = data.get("lessons", [])
    examples: List[Dict] = []

    for lesson in lessons:
        trigger = lesson.get("trigger", "")
        correct = lesson.get("correct_action", "")
        if not trigger or not correct:
            continue

        full_answer = correct
        incorrect = lesson.get("incorrect_action", "")
        if incorrect:
            full_answer += f"\n\nIMPORTANT: {incorrect}"

        examples.append(_make_example(trigger, full_answer))

    logger.info("Built %d examples from lessons", len(examples))
    return examples


# ============================================================================
# SERIES KNOWLEDGE EXAMPLES
# ============================================================================

def _build_series_examples() -> List[Dict]:
    examples: List[Dict] = []

    for series_name, info in SERIES_KNOWLEDGE.items():
        stype = info["type"]
        features = ", ".join(info["key_features"])
        apps = ", ".join(info["applications"])
        auto = info["automation_options"]

        examples.append(_make_example(
            f"What is {series_name} used for?",
            f"{series_name} is a {stype.lower()} machine for {apps.lower()}. "
            f"Key features: {features}."
            + (f" Automation options: {', '.join(auto)}." if auto else " It has NO automation options.")
        ))

        if auto:
            examples.append(_make_example(
                f"Does {series_name} have automation?",
                f"Yes. {series_name} automation options include: {', '.join(auto)}."
            ))
        else:
            examples.append(_make_example(
                f"Does {series_name} have automation?",
                f"No. {series_name} has NO automation options. "
                f"It is a {stype.lower()} machine. "
                "For automation, you need the PF1 series which offers servo drives, "
                "auto load/unload, and plug assist."
            ))

        for rule in info.get("critical_rules", []):
            examples.append(_make_example(
                f"Tell me about {series_name} capabilities.",
                f"CRITICAL RULE: {rule}"
            ))

    _build_comparison_examples(examples)

    logger.info("Built %d examples from series knowledge", len(examples))
    return examples


def _build_comparison_examples(examples: List[Dict]) -> None:
    """Add cross-series comparison examples."""
    if "PF1" in SERIES_KNOWLEDGE and "PF2" in SERIES_KNOWLEDGE:
        pf1 = SERIES_KNOWLEDGE["PF1"]
        pf2 = SERIES_KNOWLEDGE["PF2"]
        examples.append(_make_example(
            "What's the difference between PF1 and PF2?",
            f"PF1 has a {pf1['type']} with {', '.join(pf1['key_features'][:3])} "
            f"and many automation options. "
            f"PF2 is an {pf2['type']} with {', '.join(pf2['key_features'][:3])} — "
            f"it's for the bath industry only ({', '.join(pf2['applications'])})."
        ))

    if "AM" in SERIES_KNOWLEDGE:
        examples.append(_make_example(
            "Can AM handle 3mm thick sheets?",
            "No. The AM series is THIN GAUGE ONLY — max thickness ≤1.5mm. "
            "For 3mm sheets, you need the PF1 series (closed chamber, handles up to 10mm) "
            "or PF2 series (open frame, for bath industry)."
        ))

    if "IMG" in SERIES_KNOWLEDGE:
        examples.append(_make_example(
            "I need a machine for TPO dashboard lamination.",
            "For TPO dashboard lamination with grain retention, you MUST use the IMG series. "
            "IMG provides vacuum lamination, grain transfer, and soft-feel finish with "
            "precision temperature control. Do NOT use PF1 for grain/texture work."
        ))


# ============================================================================
# MACHINE PRICING EXAMPLES
# ============================================================================

def _build_pricing_examples() -> List[Dict]:
    examples: List[Dict] = []

    for model, spec in MACHINE_SPECS.items():
        if not spec.price_inr:
            continue

        features_str = ", ".join(spec.features[:4]) if spec.features else "standard configuration"
        answer = (
            f"The {model} is priced at INR {spec.price_inr:,} "
            "(subject to configuration and current pricing). "
            f"Key specs: Forming area: {spec.forming_area_mm}, "
            f"Heater: {spec.heater_power_kw}kW {spec.heater_type}, "
            f"Vacuum: {spec.vacuum_pump_capacity}. "
            f"Features: {features_str}."
        )
        if spec.price_usd:
            answer += f" USD equivalent: approximately ${spec.price_usd:,}."

        examples.append(_make_example(f"What's the price of {model}?", answer))

    logger.info("Built %d examples from machine pricing", len(examples))
    return examples


# ============================================================================
# BUILD DATASET
# ============================================================================

def build_finetune_dataset() -> str:
    """
    Build the complete fine-tuning dataset from all sources and write
    to data/training/finetune_dataset.jsonl.

    Returns the output file path.
    """
    all_examples: List[Dict] = []
    all_examples.extend(_build_lesson_examples())
    all_examples.extend(_build_series_examples())
    all_examples.extend(_build_pricing_examples())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    logger.info(
        "Wrote %d training examples to %s (%.1f KB)",
        len(all_examples),
        OUTPUT_FILE,
        OUTPUT_FILE.stat().st_size / 1024,
    )

    manifest = {
        "created_at": datetime.now().isoformat(),
        "total_examples": len(all_examples),
        "sources": {
            "lessons": len(_build_lesson_examples()),
            "series_knowledge": len([k for k in SERIES_KNOWLEDGE]),
            "machine_pricing": len([m for m in MACHINE_SPECS if MACHINE_SPECS[m].price_inr]),
        },
        "output_file": str(OUTPUT_FILE),
    }
    manifest_path = OUTPUT_DIR / "finetune_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Manifest written to %s", manifest_path)

    return str(OUTPUT_FILE)


# ============================================================================
# UPLOAD & FINE-TUNE (dry-run by default)
# ============================================================================

def upload_and_finetune(dataset_path: str) -> str:
    """
    Upload the JSONL file to OpenAI and create a fine-tuning job.

    NOTE: This function prints what it *would* do but does NOT call the API.
    Uncomment the API calls below to run for real, or trigger manually.

    Returns the (placeholder) job ID.
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    line_count = sum(1 for _ in open(path))
    size_kb = path.stat().st_size / 1024

    logger.info("=" * 60)
    logger.info("FINE-TUNE UPLOAD PLAN (DRY RUN)")
    logger.info("=" * 60)
    logger.info("  File:       %s", dataset_path)
    logger.info("  Examples:   %d", line_count)
    logger.info("  Size:       %.1f KB", size_kb)
    logger.info("  Model:      gpt-4o-mini-2024-07-18")
    logger.info("  Epochs:     3 (auto)")
    logger.info("")
    logger.info("To execute for real, uncomment the API calls in upload_and_finetune().")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Uncomment below to actually upload and start fine-tuning:
    #
    # from openai import OpenAI
    # client = OpenAI()
    #
    # upload_response = client.files.create(
    #     file=open(dataset_path, "rb"),
    #     purpose="fine-tune",
    # )
    # file_id = upload_response.id
    # logger.info("Uploaded file: %s", file_id)
    #
    # job = client.fine_tuning.jobs.create(
    #     training_file=file_id,
    #     model="gpt-4o-mini-2024-07-18",
    # )
    # logger.info("Fine-tuning job created: %s", job.id)
    # return job.id
    # ------------------------------------------------------------------

    return "dry-run-no-job-created"


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Minerva Fine-Tune Dataset Builder",
    )
    parser.add_argument(
        "--build", action="store_true",
        help="Build the JSONL dataset only",
    )
    parser.add_argument(
        "--upload", action="store_true",
        help="Build the dataset AND upload/start fine-tuning",
    )
    args = parser.parse_args()

    if not args.build and not args.upload:
        parser.print_help()
        return

    dataset_path = build_finetune_dataset()
    print(f"\nDataset written to: {dataset_path}")

    if args.upload:
        job_id = upload_and_finetune(dataset_path)
        print(f"Fine-tune job: {job_id}")


if __name__ == "__main__":
    main()
