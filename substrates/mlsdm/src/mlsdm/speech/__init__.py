"""
Speech governance module for MLSDM.

Provides core abstractions for implementing pluggable speech policies.
"""

from .governance import SpeechGovernanceResult, SpeechGovernor

__all__ = [
    "SpeechGovernanceResult",
    "SpeechGovernor",
]
