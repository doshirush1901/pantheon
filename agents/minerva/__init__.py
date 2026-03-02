"""MINERVA - Knowledge-Grounded Pre-Send Coach"""
import sys
from pathlib import Path
_apollo = Path(__file__).parent.parent / "apollo"
if str(_apollo) not in sys.path:
    sys.path.insert(0, str(_apollo))
from grounded_coach import coach_review, coach_nudge_for_revision, SERIES_KNOWLEDGE
review_draft = coach_review
__all__ = ["review_draft", "coach_review", "coach_nudge_for_revision", "SERIES_KNOWLEDGE"]
