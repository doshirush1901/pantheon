"""
Sophia - The Reflector

Learning and improvement services.
"""

from .agent import (
    reflect,
    get_recent_errors,
    get_recent_lessons,
    get_quality_trends,
    ReflectionResult,
    QualityScore,
)

__all__ = [
    "reflect",
    "get_recent_errors",
    "get_recent_lessons",
    "get_quality_trends",
    "ReflectionResult",
    "QualityScore",
]
