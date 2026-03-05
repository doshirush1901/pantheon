"""
Delphi — The Inner Voice (Rushabh's Oracle)
=============================================

Delphi is Ira's inner voice — the Oracle that whispers how Rushabh would
respond. She doesn't speak to customers directly. She shapes Ira's judgment
by injecting learned style patterns into the system prompt.

Three modes:
    1. BUILD     — Mine Gmail, build interaction map, extract style patterns
    2. SIMULATE  — Run customer personas through Ira, measure delta vs Rushabh
    3. GUIDANCE  — Generate system prompt injection from style profile + gap scores

Named after the Oracle at Delphi — the inner voice that guided heroes.
"""

from openclaw.agents.ira.src.agents.delphi.agent import (
    get_delphi,
    build_interaction_map,
    consult_rushabh_voice,
    run_shadow_simulation,
    get_delphi_guidance,
)

__all__ = [
    "get_delphi",
    "build_interaction_map",
    "consult_rushabh_voice",
    "run_shadow_simulation",
    "get_delphi_guidance",
]
