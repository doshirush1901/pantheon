#!/usr/bin/env python3
"""
Entity Extractor - Extract key entities from conversations
==========================================================

Extracts:
- Machine models (PF1, AM, RE series)
- Applications/Industries
- Materials
- Dimensions
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

# Use centralized config for path setup
SKILLS_DIR = Path(__file__).parent.parent
AGENT_DIR = SKILLS_DIR.parent

try:
    sys.path.insert(0, str(AGENT_DIR))
    from config import setup_import_paths
    setup_import_paths()
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    sys.path.insert(0, str(SKILLS_DIR / "common"))

try:
    from patterns import MACHINE_QUICK_PATTERNS, extract_machine_models
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False
    MACHINE_QUICK_PATTERNS = None


@dataclass
class ExtractedEntities:
    """Container for extracted entities."""
    machines: List[str] = field(default_factory=list)
    applications: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)
    dimensions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "machines": self.machines,
            "applications": self.applications,
            "materials": self.materials,
            "dimensions": self.dimensions,
        }
    
    def is_empty(self) -> bool:
        return not any([
            self.machines, self.applications,
            self.materials, self.dimensions
        ])


# Machinecraft product patterns - use centralized patterns when available
if PATTERNS_AVAILABLE and MACHINE_QUICK_PATTERNS:
    MACHINE_PATTERNS_COMPILED = MACHINE_QUICK_PATTERNS
else:
    # Fallback patterns
    MACHINE_PATTERNS_COMPILED = [
        re.compile(r'\bPF[-\s]?1[-\s]?\d*[A-Z]?\b', re.IGNORECASE),
        re.compile(r'\bPF[-\s]?2[-\s]?\d*[A-Z]?\b', re.IGNORECASE),
        re.compile(r'\bAM[-\s]?\d+[A-Z]?\b', re.IGNORECASE),
        re.compile(r'\bRE[-\s]?\d+[A-Z]?\b', re.IGNORECASE),
    ]

APPLICATION_KEYWORDS = [
    "automotive", "packaging", "medical", "aerospace", "refrigerator",
    "bathtub", "car mat", "interior trim", "food container", "tray",
]

MATERIAL_KEYWORDS = [
    "abs", "hips", "pp", "pe", "hdpe", "pet", "petg",
    "polycarbonate", "pc", "pmma", "acrylic", "pvc",
]

DIMENSION_PATTERNS = [
    r'\d{3,4}\s*[xX×]\s*\d{3,4}(?:\s*mm)?',
]


class EntityExtractor:
    """Extract entities from text."""
    
    def __init__(self):
        self._machine_re = MACHINE_PATTERNS_COMPILED
        self._dimension_re = [re.compile(p, re.IGNORECASE) for p in DIMENSION_PATTERNS]
    
    def extract(self, text: str) -> ExtractedEntities:
        """Extract all entities from text."""
        text_lower = text.lower()
        result = ExtractedEntities()
        
        # Extract machines
        machines_found: Set[str] = set()
        for pattern in self._machine_re:
            matches = pattern.findall(text)
            for m in matches:
                normalized = self._normalize_machine(m)
                if normalized:
                    machines_found.add(normalized)
        result.machines = sorted(machines_found)
        
        # Extract applications
        for app in APPLICATION_KEYWORDS:
            if app in text_lower:
                result.applications.append(app)
        
        # Extract materials
        for mat in MATERIAL_KEYWORDS:
            if re.search(rf'\b{mat}\b', text_lower):
                result.materials.append(mat.upper())
        
        # Extract dimensions
        for pattern in self._dimension_re:
            matches = pattern.findall(text)
            result.dimensions.extend(matches)
        
        return result
    
    def _normalize_machine(self, machine: str) -> str:
        """Normalize machine name."""
        m = machine.upper().strip()
        m = re.sub(r'\s+', '', m)
        m = re.sub(r'^PF-?', 'PF', m)
        return m


_extractor = None


def get_extractor() -> EntityExtractor:
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor


def extract_entities(text: str) -> ExtractedEntities:
    """Extract entities from text."""
    return get_extractor().extract(text)


if __name__ == "__main__":
    test_texts = [
        "What is the PF1-1510?",
        "I need a machine for automotive interior trim, using ABS material",
        "The forming area should be 2000x1500mm",
    ]
    
    for text in test_texts:
        result = extract_entities(text)
        print(f"Text: {text}")
        print(f"  Machines: {result.machines}")
        print(f"  Applications: {result.applications}")
        print(f"  Materials: {result.materials}")
        print(f"  Dimensions: {result.dimensions}")
        print()
