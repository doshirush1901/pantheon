"""
Holistic Body Systems for Ira
=============================

Inspired by "Beyond the Brain: The Surprising Bodily Systems That Contribute to Learning"
(Manus AI, March 2026), this package implements the non-brain systems that support
Ira's cognitive health:

1. Immune System    - Auto-remediation of chronic knowledge issues
2. Respiratory      - Operational heartbeat and daily rhythm
3. Endocrine        - Agent scoring with positive/negative reinforcement
4. Musculoskeletal  - Action-to-learning feedback loops
5. Sensory          - Cross-channel integration and perception
6. Metabolic        - Active knowledge hygiene and cleanup
"""

from .immune_system import ImmuneSystem, get_immune_system
from .respiratory_system import RespiratorySystem, get_respiratory_system
from .endocrine_system import EndocrineSystem, get_endocrine_system
from .musculoskeletal_system import MusculoskeletalSystem, get_musculoskeletal_system
from .sensory_system import SensoryIntegrator, get_sensory_integrator
from .metabolic_system import MetabolicSystem, get_metabolic_system
from .vital_signs import VitalSigns, collect_vital_signs

__all__ = [
    "ImmuneSystem", "get_immune_system",
    "RespiratorySystem", "get_respiratory_system",
    "EndocrineSystem", "get_endocrine_system",
    "MusculoskeletalSystem", "get_musculoskeletal_system",
    "SensoryIntegrator", "get_sensory_integrator",
    "MetabolicSystem", "get_metabolic_system",
    "VitalSigns", "collect_vital_signs",
]
