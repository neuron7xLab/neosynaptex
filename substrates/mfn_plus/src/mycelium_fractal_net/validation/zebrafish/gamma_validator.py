"""Gamma-scaling validator for zebrafish pigmentation.

Hypothesis (Vasylenko-Levin-Tononi):
    Wild-type:  gamma ~ +1.0, R^2 > 0.8, p < 0.05, CI excludes 0
    Mutant:     gamma != 1.0 (or R^2 < 0.3 = no power law)

Reference:
    Vasylenko (2026): gamma_organoid = +1.487 +/- 0.208 (healthy brain organoids)
    McGuirl et al. (2020) PNAS: zebrafish stripe vs dot phenotype

# EVIDENCE_TYPE: synthetic_biological_proxy (until real data loaded)
# SYNTHETIC_PROXY: all results on synthetic data. Marked everywhere.
"""

from __future__ import annotations

import datetime
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mycelium_fractal_net.analytics.morphology import compute_morphology_descriptor
from mycelium_fractal_net.experiments.runner import _compute_gamma_robust
from mycelium_fractal_net.types.field import FieldSequence

__all__ = [
    "GammaValidationResult",
    "ZebrafishGammaValidator",
    "ZebrafishValidationReport",
]


# ── Types ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class GammaValidationResult:
    """Result of gamma-scaling validation for one phenotype."""

    phenotype: str
    gamma: float
    r_squared: float
    ci95_lo: float
    ci95_hi: float
    p_value: float
    n_points: int
    valid: bool

    # Hypothesis tests
    hypothesis_1_0: bool  # |gamma - 1.0| < tolerance
    ci_excludes_zero: bool

    # Metadata
    label_real: bool = False
    evidence_type: str = "synthetic_biological_proxy"
    elapsed_s: float = 0.0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        h1 = "gamma~1.0 YES" if self.hypothesis_1_0 else "gamma~1.0 NO"
        real_flag = "[REAL]" if self.label_real else "[SYNTHETIC]"
        return (
            f"{real_flag} {self.phenotype}: gamma={self.gamma:.3f} "
            f"R2={self.r_squared:.3f} p={self.p_value:.4f} "
            f"CI=[{self.ci95_lo:.3f},{self.ci95_hi:.3f}] "
            f"{h1} {status}"
        )


@dataclass(frozen=True)
class ZebrafishValidationReport:
    """Full validation report: wild-type vs mutant comparison."""

    wild_type: GammaValidationResult
    mutant: GammaValidationResult
    transition: GammaValidationResult | None

    # Falsification verdict
    hypothesis_supported: bool
    falsification_verdict: str  # "SUPPORTED" | "FALSIFIED" | "INCONCLUSIVE"

    # Organoid reference
    organoid_gamma: float = 1.487
    organoid_ci_lo: float = 1.279  # 1.487 - 0.208
    organoid_ci_hi: float = 1.695  # 1.487 + 0.208
    wt_in_organoid_ci: bool = False

    label_real: bool = False
    timestamp: str = ""

    def summary(self) -> str:
        lines = [
            "=" * 70,
            "ZEBRAFISH gamma-SCALING VALIDATION",
            f"Evidence: {'REAL DATA' if self.label_real else 'SYNTHETIC PROXY'}",
            "=" * 70,
            self.wild_type.summary(),
            self.mutant.summary(),
        ]
        if self.transition:
            lines.append(self.transition.summary())
        lines += [
            "-" * 70,
            f"Organoid reference: gamma_organoid = {self.organoid_gamma} +/- 0.208",
            f"WT gamma in organoid CI [{self.organoid_ci_lo:.3f}, {self.organoid_ci_hi:.3f}]: "
            f"{self.wt_in_organoid_ci}",
            f"VERDICT: {self.falsification_verdict}",
            "=" * 70,
        ]
        return "\n".join(lines)


# ── Validator ─────────────────────────────────────────────────


class ZebrafishGammaValidator:
    """Validate gamma-scaling hypothesis on zebrafish pigmentation data.

    Algorithm:
      1. For each phenotype: list of FieldSequence (timepoints)
      2. Extract morphology descriptors: H (entropy), W2 (complexity), I (instability)
      3. Compute gamma via Theil-Sen + bootstrap CI95 + permutation p-value
         (same _compute_gamma_robust as experiments/runner.py)
      4. Compare WT vs Mutant: verify hypothesis

    # ASSUMPTION: morphology descriptors are valid proxies for
    # real biophysical pigmentation parameters.
    # Calibration on real McGuirl 2020 data — TODO(nfi-v2).
    """

    def __init__(
        self,
        gamma_1_0_tolerance: float = 0.5,
        min_r2_for_power_law: float = 0.3,
        n_bootstrap: int = 1000,
    ) -> None:
        self.gamma_1_0_tolerance = gamma_1_0_tolerance
        self.min_r2_for_power_law = min_r2_for_power_law
        self.n_bootstrap = n_bootstrap

    def validate(
        self,
        wt_sequences: list[FieldSequence],
        mutant_sequences: list[FieldSequence],
        transition_sequences: list[FieldSequence] | None = None,
        label_real: bool = False,
    ) -> ZebrafishValidationReport:
        """Full validation: WT vs Mutant (+ transition if provided)."""
        wt_result = self._validate_phenotype(wt_sequences, "wild_type", label_real)
        mut_result = self._validate_phenotype(mutant_sequences, "mutant", label_real)
        trans_result = None
        if transition_sequences:
            trans_result = self._validate_phenotype(
                transition_sequences, "transition", label_real
            )

        # Falsification verdict
        wt_passes = (
            wt_result.valid
            and wt_result.hypothesis_1_0
            and wt_result.ci_excludes_zero
            and wt_result.p_value < 0.05
        )
        mut_differs = (
            not mut_result.hypothesis_1_0
            or mut_result.r_squared < self.min_r2_for_power_law
        )

        if wt_passes and mut_differs:
            verdict = "SUPPORTED"
            supported = True
        elif not wt_result.valid or not mut_result.valid:
            verdict = "INCONCLUSIVE"
            supported = False
        else:
            verdict = "FALSIFIED"
            supported = False

        organoid_ci_lo = 1.487 - 0.208
        organoid_ci_hi = 1.487 + 0.208
        wt_in_ci = organoid_ci_lo <= wt_result.gamma <= organoid_ci_hi

        return ZebrafishValidationReport(
            wild_type=wt_result,
            mutant=mut_result,
            transition=trans_result,
            hypothesis_supported=supported,
            falsification_verdict=verdict,
            wt_in_organoid_ci=wt_in_ci,
            label_real=label_real,
            timestamp=datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        )

    def _validate_phenotype(
        self,
        sequences: list[FieldSequence],
        phenotype: str,
        label_real: bool,
    ) -> GammaValidationResult:
        """Compute gamma for one phenotype via morphology descriptors."""
        t0 = time.perf_counter()
        notes: list[str] = []

        if len(sequences) < 5:
            notes.append(
                f"# APPROXIMATION: only {len(sequences)} sequences, need >= 5"
            )

        # Extract morphology descriptors
        descriptors = []
        for seq in sequences:
            try:
                d = compute_morphology_descriptor(seq)
                descriptors.append(d)
            except Exception as e:
                notes.append(f"# WARNING: descriptor failed: {e}")

        if len(descriptors) < 3:
            return self._insufficient_result(
                phenotype, label_real, t0, notes + ["INSUFFICIENT_DATA: < 3 descriptors"]
            )

        # Build log-log series: log(dH) vs log(complexity)
        entropies = [d.complexity.get("temporal_lzc", 0.0) for d in descriptors]
        complexities = [d.stability.get("instability_index", 0.0) for d in descriptors]

        log_x: list[float] = []
        log_y: list[float] = []

        for i in range(len(entropies)):
            for j in range(i + 2, min(i + 6, len(entropies))):
                dH = abs(entropies[j] - entropies[i])
                c_sum = abs(complexities[j]) + abs(complexities[i]) + 1e-12
                if dH > 1e-6:
                    log_x.append(np.log(c_sum))
                    log_y.append(np.log(dH))

        if len(log_x) < 3:
            notes.append(
                "# APPROXIMATION: insufficient log-log spread. "
                "Larger grid or longer series needed for EMERGENT detection."
            )
            # Fallback: direct polyfit on raw values
            if len(entropies) >= 3 and len(set(complexities)) >= 2:
                x_arr = np.array(complexities)
                y_arr = np.array(entropies)
                gamma_result = _compute_gamma_robust(
                    x_arr, y_arr, self.n_bootstrap, rng_seed=42
                )
                notes.append(
                    "# APPROXIMATION: fallback to direct polyfit (not log-log)"
                )
            else:
                return self._insufficient_result(
                    phenotype, label_real, t0,
                    notes + ["INSUFFICIENT_LOG_LOG_SPREAD"],
                )
        else:
            gamma_result = _compute_gamma_robust(
                np.array(log_x), np.array(log_y), self.n_bootstrap, rng_seed=42
            )

        gamma = gamma_result.get("gamma", 0.0)
        r2 = gamma_result.get("r2", 0.0)
        ci_lo = gamma_result.get("ci95_lo", 0.0)
        ci_hi = gamma_result.get("ci95_hi", 0.0)
        p_val = gamma_result.get("p_value", 1.0)
        n_pts = gamma_result.get("n_points", len(log_x))
        valid = gamma_result.get("valid", r2 >= self.min_r2_for_power_law)

        hypothesis_1_0 = abs(gamma - 1.0) < self.gamma_1_0_tolerance
        ci_excludes_zero = not (ci_lo <= 0.0 <= ci_hi)

        return GammaValidationResult(
            phenotype=phenotype,
            gamma=gamma,
            r_squared=r2,
            ci95_lo=ci_lo,
            ci95_hi=ci_hi,
            p_value=p_val,
            n_points=n_pts,
            valid=valid,
            hypothesis_1_0=hypothesis_1_0,
            ci_excludes_zero=ci_excludes_zero,
            label_real=label_real,
            evidence_type="real" if label_real else "synthetic_biological_proxy",
            elapsed_s=time.perf_counter() - t0,
            notes=notes,
        )

    def _insufficient_result(
        self,
        phenotype: str,
        label_real: bool,
        t0: float,
        notes: list[str],
    ) -> GammaValidationResult:
        return GammaValidationResult(
            phenotype=phenotype,
            gamma=0.0,
            r_squared=0.0,
            ci95_lo=0.0,
            ci95_hi=0.0,
            p_value=1.0,
            n_points=0,
            valid=False,
            hypothesis_1_0=False,
            ci_excludes_zero=False,
            label_real=label_real,
            evidence_type="real" if label_real else "synthetic_biological_proxy",
            elapsed_s=time.perf_counter() - t0,
            notes=notes,
        )
