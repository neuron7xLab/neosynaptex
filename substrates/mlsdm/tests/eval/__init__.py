"""
Evaluation suite for NeuroCognitiveEngine.

This module provides cognitive safety evaluation tools, including the
SapolskyValidationSuite for measuring coherence, derailment prevention,
and moral safety.
"""

from .sapolsky_validation_suite import SapolskyValidationSuite

__all__ = ["SapolskyValidationSuite"]
