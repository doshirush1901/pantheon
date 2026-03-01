#!/usr/bin/env python3
"""
Deterministic Series Router
============================

Rule-based series selection engine that runs BEFORE the LLM.
Uses keyword matching and threshold logic to determine the correct
machine series with 100% accuracy for clear-cut cases.

Priority order:
  1. IMG  (in-mold graining — highest priority)
  2. PF2  (bathtub / negative-cavity forming)
  3. AM   (thin-gauge / roll-fed packaging)
  4. PF1  (thick-gauge default with advanced features)

If no rule fires with sufficient confidence the function returns None
and the LLM handles routing as before.
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger("ira.deterministic_router")

# ---------------------------------------------------------------------------
# Keyword banks (all lowercase)
# ---------------------------------------------------------------------------

IMG_KEYWORDS: List[str] = [
    "grain retention",
    "in-mold grain",
    "in mold grain",
    "img",
    "class-a surface",
    "class a surface",
    "grain texture",
    "texture preservation",
    "grain transfer",
]

IMG_COMPOUND_PAIRS: List[tuple] = [
    ("tpo", "automotive"),
    ("vacuum lamination", "grain"),
]

PF2_KEYWORDS: List[str] = [
    "bathtub",
    "bath tub",
    "spa shell",
    "shower tray",
    "hot tub",
    "jacuzzi",
    "negative cavity",
    "female cavity",
    "gravity sag",
    "drape into mold",
]

PF2_COMPOUND_PAIRS: List[tuple] = [
    ("open frame", "bath"),
    ("acrylic", "bathtub"),
]

PF1_HEAVY_GAUGE_MATERIALS: List[str] = [
    "abs", "hdpe", "polycarbonate", "pmma", "acrylic", "hips", "tpo",
]

# Short tokens that need word-boundary matching to avoid false positives
# ("pc" matches "space", "piece", etc.)
_PF1_MATERIAL_SHORT_RE = re.compile(r"\bpc\b", re.IGNORECASE)

PF1_COMPOUND_PAIRS: List[tuple] = [
    ("abs", "automotive"),
    ("hdpe", "forming"),
    ("abs", "forming"),
    ("abs", "vacuum"),
    ("pmma", "forming"),
    ("hips", "forming"),
]

# Compound pairs where one token needs word-boundary regex
PF1_COMPOUND_PAIRS_REGEX: List[tuple] = [
    (_PF1_MATERIAL_SHORT_RE, "thermoform"),
]


def _has_heavy_gauge_material(query_lower: str) -> bool:
    """Check if query mentions a known heavy-gauge material."""
    if any(mat in query_lower for mat in PF1_HEAVY_GAUGE_MATERIALS):
        return True
    if _PF1_MATERIAL_SHORT_RE.search(query_lower):
        return True
    return False

AM_KEYWORDS: List[str] = [
    "thin gauge",
    "roll-fed",
    "roll fed",
    "blister pack",
    "clamshell",
    "food tray",
    "food packaging",
]

AM_THIN_THICKNESSES: List[str] = [
    "0.3mm", "0.3 mm",
    "0.5mm", "0.5 mm",
    "0.8mm", "0.8 mm",
    "1.0mm", "1.0 mm",
    "1.2mm", "1.2 mm",
]

PF1_KEYWORDS: List[str] = [
    "closed chamber",
    "sag control",
    "pre-blow",
    "pre blow",
    "servo",
    "auto load",
    "plug assist",
    "zone heating",
    "heavy gauge",
    "heavy-gauge",
    "thick sheet",
    "thick abs",
    "thick hdpe",
    "thick pc",
    "thick pmma",
    "thick hips",
    "refrigerator liner",
    "fridge liner",
    "truck bedliner",
    "bed liner",
    "luggage shell",
    "ev battery",
    "ev enclosure",
    "industrial enclosure",
    "automotive interior",
]

# Maximum sheet thickness for AM series (mm)
AM_MAX_THICKNESS = 1.5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_THICKNESS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:mm|millimeter|millimetre)\b",
    re.IGNORECASE,
)


def extract_thickness_from_query(query: str) -> Optional[float]:
    """Return the first explicit thickness value (in mm) found in *query*, or None."""
    match = _THICKNESS_RE.search(query)
    if match:
        return float(match.group(1))
    return None


def extract_keywords(query: str) -> Dict[str, List[str]]:
    """Return a dict mapping each series to the routing keywords found in *query*."""
    q = query.lower()
    found: Dict[str, List[str]] = {
        "IMG": [],
        "PF2": [],
        "AM": [],
        "PF1": [],
    }

    for kw in IMG_KEYWORDS:
        if kw in q:
            found["IMG"].append(kw)
    for a, b in IMG_COMPOUND_PAIRS:
        if a in q and b in q:
            found["IMG"].append(f"{a}+{b}")

    for kw in PF2_KEYWORDS:
        if kw in q:
            found["PF2"].append(kw)
    for a, b in PF2_COMPOUND_PAIRS:
        if a in q and b in q:
            found["PF2"].append(f"{a}+{b}")

    for kw in AM_KEYWORDS:
        if kw in q:
            found["AM"].append(kw)
    for thin in AM_THIN_THICKNESSES:
        if thin in q:
            found["AM"].append(thin)

    for kw in PF1_KEYWORDS:
        if kw in q:
            found["PF1"].append(kw)
    for a, b in PF1_COMPOUND_PAIRS:
        if a in q and b in q:
            found["PF1"].append(f"{a}+{b}")
    for pattern, b in PF1_COMPOUND_PAIRS_REGEX:
        if pattern.search(q) and b in q:
            found["PF1"].append(f"pc+{b}")

    return found


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

def route_to_series(query: str) -> Optional[Dict]:
    """Deterministic series selection.

    Returns a dict like::

        {"series": "PF2", "confidence": 0.95,
         "reason": "bathtub + negative cavity keywords",
         "bypass_llm_routing": True}

    or ``None`` when no rule fires with high enough confidence (>0.8).
    """
    q = query.lower()
    found = extract_keywords(query)
    thickness = extract_thickness_from_query(query)

    # ------------------------------------------------------------------
    # 1. IMG — highest priority
    # ------------------------------------------------------------------
    if found["IMG"]:
        reason = f"IMG keywords: {', '.join(found['IMG'])}"
        confidence = min(0.98, 0.90 + 0.02 * len(found["IMG"]))
        logger.info(f"[DET-ROUTER] IMG route → {reason} (conf={confidence:.2f})")
        return {
            "series": "IMG",
            "confidence": confidence,
            "reason": reason,
            "bypass_llm_routing": True,
            "matched_keywords": found["IMG"],
        }

    # ------------------------------------------------------------------
    # 2. PF2 — bathtub / negative-cavity forming
    # ------------------------------------------------------------------
    if found["PF2"]:
        reason = f"PF2 keywords: {', '.join(found['PF2'])}"
        confidence = min(0.98, 0.90 + 0.02 * len(found["PF2"]))
        logger.info(f"[DET-ROUTER] PF2 route → {reason} (conf={confidence:.2f})")
        return {
            "series": "PF2",
            "confidence": confidence,
            "reason": reason,
            "bypass_llm_routing": True,
            "matched_keywords": found["PF2"],
        }

    # ------------------------------------------------------------------
    # 3. AM — thin-gauge / roll-fed / packaging
    # ------------------------------------------------------------------
    am_keyword_hit = bool(found["AM"])
    am_thickness_hit = thickness is not None and thickness <= AM_MAX_THICKNESS

    if am_keyword_hit and am_thickness_hit:
        reason = f"AM keywords ({', '.join(found['AM'])}) + thickness {thickness}mm ≤ {AM_MAX_THICKNESS}mm"
        logger.info(f"[DET-ROUTER] AM route (high) → {reason}")
        return {
            "series": "AM",
            "confidence": 0.97,
            "reason": reason,
            "bypass_llm_routing": True,
            "matched_keywords": found["AM"],
        }

    if am_keyword_hit:
        reason = f"AM keywords: {', '.join(found['AM'])}"
        confidence = min(0.95, 0.85 + 0.02 * len(found["AM"]))
        logger.info(f"[DET-ROUTER] AM route → {reason} (conf={confidence:.2f})")
        return {
            "series": "AM",
            "confidence": confidence,
            "reason": reason,
            "bypass_llm_routing": True,
            "matched_keywords": found["AM"],
        }

    if am_thickness_hit and thickness <= 1.0:
        # Very thin sheet with no other series cues → almost certainly AM
        reason = f"thickness {thickness}mm (≤1.0mm, strongly suggests thin-gauge AM)"
        logger.info(f"[DET-ROUTER] AM route (thickness only) → {reason}")
        return {
            "series": "AM",
            "confidence": 0.85,
            "reason": reason,
            "bypass_llm_routing": True,
            "matched_keywords": [],
        }

    # ------------------------------------------------------------------
    # 4. PF1 — thick-gauge default with advanced features
    # ------------------------------------------------------------------
    if found["PF1"]:
        reason = f"PF1 feature keywords: {', '.join(found['PF1'])}"
        confidence = min(0.95, 0.85 + 0.02 * len(found["PF1"]))
        logger.info(f"[DET-ROUTER] PF1 route → {reason} (conf={confidence:.2f})")
        return {
            "series": "PF1",
            "confidence": confidence,
            "reason": reason,
            "bypass_llm_routing": True,
            "matched_keywords": found["PF1"],
        }

    # Thickness > 1.5mm with no bath/spa cues → default to PF1
    if thickness is not None and thickness > AM_MAX_THICKNESS and not found["PF2"]:
        # Higher confidence when a known heavy-gauge material is also mentioned
        material_match = _has_heavy_gauge_material(q)
        confidence = 0.92 if material_match else 0.82
        material_note = f" + heavy-gauge material detected" if material_match else ""
        reason = f"thickness {thickness}mm > {AM_MAX_THICKNESS}mm (thick-gauge → PF1 default{material_note})"
        logger.info(f"[DET-ROUTER] PF1 route (thickness default) → {reason}")
        return {
            "series": "PF1",
            "confidence": confidence,
            "reason": reason,
            "bypass_llm_routing": True,
            "matched_keywords": [],
        }

    # Heavy-gauge material mentioned without explicit thickness → likely PF1
    material_hits = [mat for mat in PF1_HEAVY_GAUGE_MATERIALS if mat in q]
    if _PF1_MATERIAL_SHORT_RE.search(q):
        material_hits.append("pc")
    if material_hits and not found["PF2"] and not found["AM"] and not found["IMG"]:
        forming_cues = any(cue in q for cue in ["forming", "thermoform", "vacuum", "machine", "mold", "mould"])
        if forming_cues:
            reason = f"heavy-gauge material ({', '.join(material_hits)}) + forming context → PF1"
            logger.info(f"[DET-ROUTER] PF1 route (material) → {reason}")
            return {
                "series": "PF1",
                "confidence": 0.80,
                "reason": reason,
                "bypass_llm_routing": True,
                "matched_keywords": material_hits,
            }

    # ------------------------------------------------------------------
    # No confident match — let the LLM decide
    # ------------------------------------------------------------------
    logger.debug("[DET-ROUTER] No deterministic match — deferring to LLM")
    return None
