"""
Vera - The Fact Checker

Verification and accuracy services.
"""

from .agent import (
    verify,
    generate_verification_report,
    VerificationReport,
)

__all__ = [
    "verify",
    "generate_verification_report",
    "VerificationReport",
]
