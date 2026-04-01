"""MFN Interpretability Engine — mechanistic auditor for gamma-scaling hypothesis.

Read-only observer of MFN internal states. Does not modify simulation.
Extracts features, builds attribution graphs, traces causal rules,
and diagnoses gamma deviations from +1.0.

Ref: Vasylenko (2026) NFI Platform
     Sundararajan et al. (2017) Axiomatic Attribution for Deep Networks
"""

from .attribution_graph import (
    AttributionEdge,
    AttributionGraph,
    AttributionGraphBuilder,
    AttributionNode,
)
from .causal_tracer import CausalRuleTrace, CausalTracer, StageTransitionTrace
from .feature_extractor import FeatureVector, MFNFeatureExtractor
from .gamma_diagnostics import GammaDiagnosticReport, GammaDiagnostics
from .pipeline import ComparisonReport, InterpretabilityPipeline
from .report import MFNInterpretabilityReport
from .state_probe import LinearStateProbe

__all__ = [
    "AttributionEdge",
    "AttributionGraph",
    "AttributionGraphBuilder",
    "AttributionNode",
    "CausalRuleTrace",
    "CausalTracer",
    "ComparisonReport",
    "FeatureVector",
    "GammaDiagnosticReport",
    "GammaDiagnostics",
    "InterpretabilityPipeline",
    "LinearStateProbe",
    "MFNFeatureExtractor",
    "MFNInterpretabilityReport",
    "StageTransitionTrace",
]
