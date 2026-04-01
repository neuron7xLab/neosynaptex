"""Canonical MFN type exports (lazy)."""

from __future__ import annotations

from typing import Any

__all__ = [
    "FEATURE_COUNT",
    "FEATURE_NAMES",
    "AnalysisReport",
    "AnomalyEvent",
    "BoundaryCondition",
    "ChangePointResult",
    "ComparisonResult",
    "ComplexityMetrics",
    "ConnectivityFeatures",
    "DatasetConfig",
    "DatasetMeta",
    "DatasetRow",
    "DatasetStats",
    "DetectionEvidence",
    "DriftSummary",
    "FeatureConfig",
    "FeatureVector",
    "FieldHistory",
    "FieldSequence",
    "FieldState",
    "ForecastResult",
    "GABAATonicSpec",
    "GridShape",
    "MorphologyDescriptor",
    "NeuromodulationFeatures",
    "NeuromodulationSpec",
    "NeuromodulationStateSnapshot",
    "ObservationNoiseSpec",
    "RegimeState",
    "ScenarioConfig",
    "ScenarioType",
    "SerotonergicPlasticitySpec",
    "SimulationConfig",
    "SimulationResult",
    "SimulationSpec",
    "StabilityMetrics",
    "TemporalFeatures",
    "TopologySummary",
]


def __getattr__(name: str) -> Any:
    if name in {
        "SimulationConfig",
        "SimulationResult",
        "FeatureConfig",
        "DatasetConfig",
    }:
        from .config import (
            DatasetConfig,
            FeatureConfig,
            SimulationConfig,
            SimulationResult,
        )

        return locals()[name]
    if name in {
        "FieldState",
        "FieldHistory",
        "FieldSequence",
        "SimulationSpec",
        "GridShape",
        "BoundaryCondition",
        "NeuromodulationSpec",
        "GABAATonicSpec",
        "SerotonergicPlasticitySpec",
        "ObservationNoiseSpec",
    }:
        from .field import (
            BoundaryCondition,
            FieldHistory,
            FieldSequence,
            FieldState,
            GABAATonicSpec,
            GridShape,
            NeuromodulationSpec,
            ObservationNoiseSpec,
            SerotonergicPlasticitySpec,
            SimulationSpec,
        )

        return locals()[name]
    if name in {
        "FeatureVector",
        "MorphologyDescriptor",
        "FEATURE_NAMES",
        "FEATURE_COUNT",
    }:
        from .features import (
            FEATURE_COUNT,
            FEATURE_NAMES,
            FeatureVector,
            MorphologyDescriptor,
        )

        return locals()[name]
    if name in {"AnomalyEvent", "RegimeState", "DetectionEvidence"}:
        from .detection import AnomalyEvent, DetectionEvidence, RegimeState

        return locals()[name]
    if name in {
        "TemporalFeatures",
        "StabilityMetrics",
        "ComplexityMetrics",
        "ConnectivityFeatures",
        "NeuromodulationFeatures",
        "ChangePointResult",
        "DriftSummary",
        "TopologySummary",
    }:
        from .analytics import (
            ChangePointResult,
            ComplexityMetrics,
            ConnectivityFeatures,
            DriftSummary,
            NeuromodulationFeatures,
            StabilityMetrics,
            TemporalFeatures,
            TopologySummary,
        )

        return locals()[name]
    if name == "NeuromodulationStateSnapshot":
        from .field import NeuromodulationStateSnapshot

        return NeuromodulationStateSnapshot
    if name in {"ForecastResult", "ComparisonResult"}:
        from .forecast import ComparisonResult, ForecastResult

        return locals()[name]
    if name == "AnalysisReport":
        from .report import AnalysisReport

        return AnalysisReport
    if name in {"ScenarioConfig", "ScenarioType"}:
        from .scenario import ScenarioConfig, ScenarioType

        return locals()[name]
    if name in {"DatasetRow", "DatasetMeta", "DatasetStats"}:
        from .dataset import DatasetMeta, DatasetRow, DatasetStats

        return locals()[name]
    raise AttributeError(name)
