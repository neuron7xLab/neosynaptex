"""Feature extraction from MFN internal states — read-only observer.

Decomposes simulation state into four interpretable feature groups:
thermodynamic, topological, fractal, causal. Each group is a dict[str, float].

Ref: Vasylenko (2026), Cross & Hohenberg (1993)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.causal import CausalValidationResult
    from mycelium_fractal_net.types.field import FieldSequence
    from mycelium_fractal_net.types.thermodynamics import ThermodynamicStabilityReport

__all__ = ["FeatureVector", "MFNFeatureExtractor"]


@dataclass
class FeatureVector:
    """Aggregated interpretable features from a single simulation step."""

    thermodynamic: dict[str, float] = field(default_factory=dict)
    topological: dict[str, float] = field(default_factory=dict)
    fractal: dict[str, float] = field(default_factory=dict)
    causal: dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0
    step: int = 0

    def to_array(self) -> np.ndarray:
        """Concatenate all features into a flat numpy vector."""
        vals: list[float] = []
        for group in (self.thermodynamic, self.topological, self.fractal, self.causal):
            vals.extend(group.values())
        return np.array(vals, dtype=np.float64)

    def feature_names(self) -> list[str]:
        """Feature names in same order as to_array()."""
        names: list[str] = []
        for prefix, group in [
            ("thermo", self.thermodynamic),
            ("topo", self.topological),
            ("fractal", self.fractal),
            ("causal", self.causal),
        ]:
            for k in group:
                names.append(f"{prefix}.{k}")
        return names

    def to_dict(self) -> dict[str, Any]:
        return {
            "thermodynamic": dict(self.thermodynamic),
            "topological": dict(self.topological),
            "fractal": dict(self.fractal),
            "causal": dict(self.causal),
            "step": self.step,
        }


class MFNFeatureExtractor:
    """Extract interpretable features from MFN internal states.

    Read-only: never modifies simulation state.
    """

    def extract_thermodynamic_features(
        self,
        report: ThermodynamicStabilityReport,
    ) -> dict[str, float]:
        """Extract from ThermodynamicStabilityReport."""
        traj = report.energy_trajectory
        features: dict[str, float] = {
            "free_energy_final": traj[-1] if traj else 0.0,
            "free_energy_mean": float(np.mean(traj)) if traj else 0.0,
            "free_energy_std": float(np.std(traj)) if len(traj) > 1 else 0.0,
            "lyapunov_lambda1": report.lyapunov_lambda1,
            "energy_drift_per_step": report.energy_drift_per_step,
            "adaptive_steps_taken": float(report.adaptive_steps_taken),
            "final_dt": report.final_dt,
        }

        # Thermodynamic phase classification
        lam1 = report.lyapunov_lambda1
        if lam1 < -0.05:
            phase = 0.0  # subcritical
        elif lam1 < 0.05:
            phase = 0.5  # critical (Turing zone)
        else:
            phase = 1.0  # supercritical
        features["thermodynamic_phase"] = phase

        # Energy monotonicity score (fraction of steps with dF <= 0)
        if len(traj) > 1:
            diffs = np.diff(traj)
            features["energy_monotonicity"] = float(np.mean(diffs <= 0))
        else:
            features["energy_monotonicity"] = 1.0

        # Curvature features
        cl = report.curvature_landscape
        features["curvature_mean"] = cl.mean_curvature
        features["curvature_std"] = cl.std_curvature
        features["saddle_point_count"] = float(cl.saddle_point_count)

        return features

    def extract_topological_features(
        self,
        seq: FieldSequence,
    ) -> dict[str, float]:
        """Extract topological features via persistence diagram."""
        field = np.asarray(seq.field, dtype=np.float64)
        features: dict[str, float] = {}

        try:
            from mycelium_fractal_net.analytics.tda import PersistenceTransformer

            pt = PersistenceTransformer(min_persistence=0.001)
            diagrams = pt.fit_transform([field])
            if diagrams and diagrams[0]:
                diag = diagrams[0]
                dims = [d for d, _ in diag]
                persists = [death - birth for _, (birth, death) in diag]

                features["betti_0"] = float(dims.count(0))
                features["betti_1"] = float(dims.count(1))
                features["betti_2"] = float(dims.count(2))

                if persists:
                    p_arr = np.array(persists)
                    features["persistence_total"] = float(np.sum(p_arr))
                    features["persistence_max"] = float(np.max(p_arr))
                    features["persistence_mean"] = float(np.mean(p_arr))

                    # Persistence entropy
                    p_norm = p_arr / (np.sum(p_arr) + 1e-12)
                    features["persistence_entropy"] = float(
                        -np.sum(p_norm * np.log(p_norm + 1e-12))
                    )
                else:
                    features.update(
                        {"persistence_total": 0.0, "persistence_max": 0.0,
                         "persistence_mean": 0.0, "persistence_entropy": 0.0}
                    )
            else:
                features.update(self._empty_topo_features())
        except Exception:
            features.update(self._empty_topo_features())

        return features

    def _empty_topo_features(self) -> dict[str, float]:
        return {
            "betti_0": 0.0, "betti_1": 0.0, "betti_2": 0.0,
            "persistence_total": 0.0, "persistence_max": 0.0,
            "persistence_mean": 0.0, "persistence_entropy": 0.0,
        }

    def extract_fractal_features(
        self,
        seq: FieldSequence,
    ) -> dict[str, float]:
        """Extract fractal features from field."""
        from mycelium_fractal_net.analytics.fractal_features import (
            _adaptive_threshold,
            compute_box_counting_dimension,
        )

        field = np.asarray(seq.field, dtype=np.float64)
        d_box = compute_box_counting_dimension(field)

        thr = _adaptive_threshold(field)
        active_frac = float(np.mean(field > thr))

        # Field spatial statistics
        grad_x = np.gradient(field, axis=1)
        grad_y = np.gradient(field, axis=0)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)

        return {
            "d_box": d_box,
            "d_box_deviation_from_golden": abs(d_box - 1.618),
            "active_fraction": active_frac,
            "gradient_mean": float(np.mean(grad_mag)),
            "gradient_max": float(np.max(grad_mag)),
            "field_std": float(np.std(field)),
            "field_range": float(np.ptp(field)),
        }

    def extract_causal_features(
        self,
        causal: CausalValidationResult,
    ) -> dict[str, float]:
        """Extract from CausalValidationResult."""
        rules = causal.rule_results

        # Stage activation vector
        stages = ["simulate", "extract", "detect", "forecast", "compare",
                   "cross-stage", "perturbation"]
        stage_pass_rate: dict[str, float] = {}
        for stage in stages:
            stage_rules = [r for r in rules if r.stage == stage]
            if stage_rules:
                stage_pass_rate[stage] = float(np.mean([r.passed for r in stage_rules]))
            else:
                stage_pass_rate[stage] = 1.0

        features: dict[str, float] = {}
        for i, stage in enumerate(stages):
            features[f"stage_{i}_pass_rate"] = stage_pass_rate[stage]

        features["total_rules"] = float(len(rules))
        features["rules_passed"] = float(sum(1 for r in rules if r.passed))
        features["rules_failed"] = float(sum(1 for r in rules if not r.passed))
        features["error_count"] = float(causal.error_count)
        features["warning_count"] = float(causal.warning_count)

        # Stage transition entropy
        activations = [stage_pass_rate[s] for s in stages]
        a_arr = np.array(activations)
        a_norm = a_arr / (np.sum(a_arr) + 1e-12)
        features["stage_activation_entropy"] = float(
            -np.sum(a_norm * np.log(a_norm + 1e-12))
        )

        # Overall causal health
        features["causal_ok"] = 1.0 if causal.ok else 0.0

        return features

    def extract_all(
        self,
        seq: FieldSequence,
        thermo_report: ThermodynamicStabilityReport | None = None,
        causal_result: CausalValidationResult | None = None,
        step: int = 0,
    ) -> FeatureVector:
        """Aggregate all features from a simulation snapshot."""
        thermo = (
            self.extract_thermodynamic_features(thermo_report)
            if thermo_report is not None
            else {}
        )
        topo = self.extract_topological_features(seq)
        fractal = self.extract_fractal_features(seq)
        causal = (
            self.extract_causal_features(causal_result)
            if causal_result is not None
            else {}
        )

        return FeatureVector(
            thermodynamic=thermo,
            topological=topo,
            fractal=fractal,
            causal=causal,
            step=step,
        )
