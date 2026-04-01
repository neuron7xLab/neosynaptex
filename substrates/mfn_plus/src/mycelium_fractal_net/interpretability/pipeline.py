"""Full interpretability pipeline — MFNSnapshot → GammaDiagnosticReport.

Runs on real simulation snapshots. All components are READ-ONLY.

# EVIDENCE TYPE: real_simulation
# IMPLEMENTED TRUTH: feature extraction from real R-D fields
# APPROXIMATION: attribution via Pearson correlation, not interventional
# GAP: interventional attribution requires perturbation experiments

Ref: Vasylenko (2026) NFI Platform
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from .attribution_graph import AttributionGraphBuilder
from .causal_tracer import CausalTracer
from .feature_extractor import MFNFeatureExtractor
from .gamma_diagnostics import GammaDiagnosticReport, GammaDiagnostics

__all__ = ["ComparisonReport", "InterpretabilityPipeline"]


@dataclass
class ComparisonReport:
    """Statistical comparison of healthy vs pathological scenarios.

    # EVIDENCE TYPE: real_simulation, N runs each condition
    """

    feature_stats: dict[str, dict[str, float]] = field(default_factory=dict)
    deviation_origins: dict[str, dict[str, float]] = field(default_factory=dict)
    gamma_separation: float = 0.0
    top_discriminating: list[tuple[str, float]] = field(default_factory=list)
    friston_gap_status: str = "PARTIAL"

    # Statistical tests
    t_stat: float = 0.0
    p_value: float = 1.0
    p_value_bonferroni: float = 1.0
    cohens_d: float = 0.0
    wasserstein: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "gamma_separation": self.gamma_separation,
            "t_stat": self.t_stat,
            "p_value": self.p_value,
            "p_value_bonferroni": self.p_value_bonferroni,
            "cohens_d": self.cohens_d,
            "wasserstein": self.wasserstein,
            "top_discriminating": self.top_discriminating,
            "friston_gap_status": self.friston_gap_status,
            "n_deviation_origins": len(self.deviation_origins),
        }


class InterpretabilityPipeline:
    """Full pipeline: simulation results → GammaDiagnosticReport + comparison.

    Read-only. Does not modify simulation state.
    """

    def __init__(self) -> None:
        self.extractor = MFNFeatureExtractor()
        self.builder = AttributionGraphBuilder()
        self.tracer = CausalTracer()
        self.diagnostics = GammaDiagnostics(
            extractor=self.extractor,
            graph_builder=self.builder,
            tracer=self.tracer,
        )

    def diagnose_sequences(
        self,
        sequences: list[Any],
        gamma_values: list[float],
    ) -> GammaDiagnosticReport:
        """Single diagnostic from pre-computed sequences.

        # EVIDENCE TYPE: real_simulation
        Does not import core.simulate — receives sequences from caller.
        """
        return self.diagnostics.diagnose(sequences, gamma_values)

    def compare(
        self,
        healthy_result: Any,
        pathological_result: Any,
    ) -> ComparisonReport:
        """Statistical comparison of healthy vs pathological scenarios.

        # EVIDENCE TYPE: real_simulation, N runs each condition
        Includes: t-test, Cohen's d, Bonferroni correction, Wasserstein distance.
        """
        g_h = np.array([r.gamma for r in healthy_result.runs])
        g_p = np.array([r.gamma for r in pathological_result.runs])

        # Core gamma statistics
        if len(g_h) >= 2 and len(g_p) >= 2:
            t_stat, p_val = stats.ttest_ind(g_h, g_p, equal_var=False)
            pooled_std = float(np.sqrt((np.var(g_h) + np.var(g_p)) / 2))
            cohens_d = float(abs(np.mean(g_h) - np.mean(g_p)) / (pooled_std + 1e-12))
            w_dist = float(stats.wasserstein_distance(g_h, g_p))
            # Bonferroni: 4 comparison families (gamma, features, origins, V)
            p_bonf = min(float(p_val) * 4, 1.0)
        else:
            t_stat = p_val = cohens_d = w_dist = p_bonf = 0.0

        gamma_sep = cohens_d

        # Deviation origin distribution
        origins: dict[str, dict[str, float]] = {}
        for label, result in [("healthy", healthy_result), ("pathological", pathological_result)]:
            counts: dict[str, int] = {}
            for r in result.runs:
                counts[r.deviation_origin] = counts.get(r.deviation_origin, 0) + 1
            n = max(len(result.runs), 1)
            origins[label] = {k: v / n for k, v in counts.items()}

        # Per-feature comparison (Cohen's d per feature group)
        feature_stats: dict[str, dict[str, float]] = {}
        top_disc: list[tuple[str, float]] = []

        h_features = _collect_feature_arrays(healthy_result)
        p_features = _collect_feature_arrays(pathological_result)

        common_keys = set(h_features.keys()) & set(p_features.keys())
        for key in common_keys:
            h_arr = np.array(h_features[key])
            p_arr = np.array(p_features[key])
            if len(h_arr) >= 2 and len(p_arr) >= 2:
                ps = float(np.sqrt((np.var(h_arr) + np.var(p_arr)) / 2))
                d = float(abs(np.mean(h_arr) - np.mean(p_arr)) / (ps + 1e-12))
                feature_stats[key] = {"cohens_d": d, "h_mean": float(np.mean(h_arr)),
                                      "p_mean": float(np.mean(p_arr))}
                top_disc.append((key, d))

        top_disc.sort(key=lambda x: x[1], reverse=True)

        # Friston gap: F available from FreeEnergyTracker (real), but not variational F
        friston = "PARTIAL"
        if healthy_result.runs and healthy_result.runs[0].free_energy_trajectory:
            friston = "PARTIAL"  # Thermo F available, not Friston variational F

        return ComparisonReport(
            feature_stats=feature_stats,
            deviation_origins=origins,
            gamma_separation=gamma_sep,
            top_discriminating=top_disc[:10],
            friston_gap_status=friston,
            t_stat=float(t_stat),
            p_value=float(p_val),
            p_value_bonferroni=p_bonf,
            cohens_d=cohens_d,
            wasserstein=w_dist,
        )


def _collect_feature_arrays(result: Any) -> dict[str, list[float]]:
    """Flatten per-run features into {feature_name: [values]}."""
    out: dict[str, list[float]] = {}
    for run in result.runs:
        for fd in run.features:
            for group in ("topological", "fractal", "causal", "thermodynamic"):
                for k, v in fd.get(group, {}).items():
                    key = f"{group}.{k}"
                    out.setdefault(key, []).append(float(v))
    return out
