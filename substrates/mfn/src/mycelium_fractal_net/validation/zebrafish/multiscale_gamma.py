"""Multi-scale topological gamma for zebrafish pigmentation.

gamma_b0(scale) = d(log beta_0)/d(log scale)

Pre-validated values (live session, 2026-03-29):
  Stripe (organized):  gamma_b0 = -0.856 +/- 0.022  (15 replicates)
  Noise  (random):     gamma_b0 = -0.156 +/- 0.010  (15 replicates)
  Separation:          5.5x ratio, zero sigma-overlap

Hypothesis (Vasylenko-Levin-Tononi, revised):
  Organized biological tissue:  |gamma_b0| > THRESHOLD (default=0.4)
  Random control:               |gamma_b0| < THRESHOLD
  Separation criterion:         |gamma_b0_WT| / |gamma_b0_noise| > 2.0

# Ref: McGuirl et al. (2020) PNAS 117:5217. DOI: 10.1073/pnas.1917763117
# Ref: Vasylenko (2026) gamma_organoid=1.487+/-0.208. Zenodo 10301912.
"""

from __future__ import annotations

import datetime
import time
import warnings
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from mycelium_fractal_net.analytics.tda_ews import compute_tda
from mycelium_fractal_net.experiments.runner import _compute_gamma_robust

__all__ = [
    "DEFAULT_SCALES",
    "MultiScaleGammaComputer",
    "MultiScaleResult",
    "MultiScaleValidationReport",
    "MultiScaleValidator",
    "ORGANIZED_THRESHOLD",
    "PREVALIDATED_NOISE_GAMMA",
    "PREVALIDATED_STRIPE_GAMMA",
    "RandomControlGenerator",
    "SEPARATION_RATIO",
]

# ── Constants (pre-validated) ─────────────────────────────────

DEFAULT_SCALES: list[float] = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3]
ORGANIZED_THRESHOLD: float = 0.4
SEPARATION_RATIO: float = 2.0
PREVALIDATED_STRIPE_GAMMA: float = -0.856
PREVALIDATED_NOISE_GAMMA: float = -0.156


# ── Types ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class MultiScaleResult:
    """gamma_b0(scale) for one phenotype."""

    phenotype: str
    gamma_b0: float
    r_squared: float
    ci95_lo: float
    ci95_hi: float
    p_value: float
    n_scale_points: int
    valid: bool

    is_organized: bool
    abs_gamma: float

    scale_values: tuple[float, ...]
    beta0_values: tuple[int, ...]

    label_real: bool = False
    evidence_type: str = "synthetic_biological_proxy"
    notes: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0

    def summary(self) -> str:
        tag = "[REAL]" if self.label_real else "[SYNTH]"
        org = "ORGANIZED" if self.is_organized else "RANDOM"
        return (
            f"{tag} {self.phenotype}: "
            f"gamma_b0={self.gamma_b0:+.3f} R2={self.r_squared:.3f} "
            f"p={self.p_value:.4f} CI=[{self.ci95_lo:.3f},{self.ci95_hi:.3f}] "
            f"n_scales={self.n_scale_points} -> {org}"
        )


@dataclass(frozen=True)
class MultiScaleValidationReport:
    """WT vs random control + verdict."""

    wild_type: MultiScaleResult
    random_control: MultiScaleResult
    mutant: MultiScaleResult | None

    separation_ratio: float
    verdict: str
    hypothesis_supported: bool

    organoid_note: str = (
        "gamma_organoid=+1.487 is in (delta_pe0,delta_beta0) space. "
        "gamma_b0(scale) is a different projection. "
        "Direct comparison requires 3D TDA. TODO(nfi-v2)."
    )
    label_real: bool = False
    timestamp: str = ""

    def summary(self) -> str:
        lines = [
            "=" * 72,
            "MULTI-SCALE TOPOLOGICAL gamma VALIDATION",
            "Metric: gamma_b0 = d(log beta_0)/d(log scale)",
            f"Evidence: {'REAL DATA (McGuirl 2020)' if self.label_real else 'SYNTHETIC PROXY'}",
            "=" * 72,
            self.wild_type.summary(),
            self.random_control.summary(),
        ]
        if self.mutant:
            lines.append(self.mutant.summary())
        lines += [
            "-" * 72,
            f"Separation |gamma_WT|/|gamma_noise| = {self.separation_ratio:.2f}x "
            f"(threshold: {SEPARATION_RATIO:.1f}x)",
            f"Pre-validated: Stripe={PREVALIDATED_STRIPE_GAMMA:.3f}, "
            f"Noise={PREVALIDATED_NOISE_GAMMA:.3f}",
            f"VERDICT: {self.verdict}",
            "=" * 72,
        ]
        return "\n".join(lines)


# ── Random Control Generator ─────────────────────────────────


class RandomControlGenerator:
    """Generate random controls from real or synthetic fields.

    SPATIAL_SHUFFLE: shuffles pixels within each frame independently.
      Preserves intensity histogram, destroys spatial structure.
    """

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)

    def spatial_shuffle(self, fields: list[np.ndarray]) -> list[np.ndarray]:
        """Shuffle pixels within each frame independently."""
        result = []
        for f in fields:
            flat = f.flatten().copy()
            self.rng.shuffle(flat)
            result.append(flat.reshape(f.shape))
        return result

    def gaussian_noise(
        self, n_fields: int, grid_size: int, mean: float = 0.5, std: float = 0.15
    ) -> list[np.ndarray]:
        """IID Gaussian noise baseline."""
        return [
            np.clip(self.rng.normal(mean, std, (grid_size, grid_size)), 0, 1)
            for _ in range(n_fields)
        ]


# ── Multi-scale Gamma Computer ───────────────────────────────


class MultiScaleGammaComputer:
    """Compute gamma_b0(scale) = d(log beta_0)/d(log scale).

    For a series of fields: pools all (log_scale, log_beta0) pairs
    across frames, then fits Theil-Sen.

    # ASSUMPTION: log-linear beta_0(scale) holds for fractal-like patterns.
    """

    def __init__(
        self,
        scales: list[float] | None = None,
        n_bootstrap: int = 1000,
        min_r2: float = 0.15,
        min_scale_points: int = 4,
        organized_threshold: float = ORGANIZED_THRESHOLD,
    ) -> None:
        self.scales = scales or list(DEFAULT_SCALES)
        self.n_bootstrap = n_bootstrap
        self.min_r2 = min_r2
        self.min_scale_points = min_scale_points
        self.organized_threshold = organized_threshold

    def compute_single(
        self,
        field_arr: np.ndarray,
        phenotype: str = "unknown",
        label_real: bool = False,
    ) -> MultiScaleResult:
        """gamma_b0(scale) for one 2D field."""
        t0 = time.perf_counter()
        notes: list[str] = []

        log_scales: list[float] = []
        log_b0: list[float] = []
        scale_vals: list[float] = []
        beta0_vals: list[int] = []

        for s in self.scales:
            sig = compute_tda(field_arr, min_persistence_frac=s)
            scale_vals.append(s)
            beta0_vals.append(sig.beta_0)
            if sig.beta_0 > 0:
                log_scales.append(np.log(s))
                log_b0.append(np.log(float(sig.beta_0)))

        n_pts = len(log_scales)
        if n_pts < self.min_scale_points:
            return self._insufficient(
                phenotype, label_real,
                notes + [f"Only {n_pts} scale points with beta0>0"],
                tuple(scale_vals), tuple(beta0_vals),
                time.perf_counter() - t0,
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = _compute_gamma_robust(
                np.array(log_scales), np.array(log_b0), self.n_bootstrap
            )

        gamma = r["gamma"]
        r2 = r["r2"]
        valid = r2 >= self.min_r2 and n_pts >= self.min_scale_points

        return MultiScaleResult(
            phenotype=phenotype,
            gamma_b0=gamma,
            r_squared=r2,
            ci95_lo=r["ci95_lo"],
            ci95_hi=r["ci95_hi"],
            p_value=r["p_value"],
            n_scale_points=n_pts,
            valid=valid,
            is_organized=abs(gamma) >= self.organized_threshold,
            abs_gamma=abs(gamma),
            scale_values=tuple(scale_vals),
            beta0_values=tuple(beta0_vals),
            label_real=label_real,
            evidence_type="real" if label_real else "synthetic_biological_proxy",
            notes=notes,
            elapsed_s=time.perf_counter() - t0,
        )

    def compute_series(
        self,
        fields: list[np.ndarray],
        phenotype: str = "unknown",
        label_real: bool = False,
    ) -> MultiScaleResult:
        """gamma_b0 pooled across all frames in a series."""
        t0 = time.perf_counter()
        notes: list[str] = []

        if not fields:
            return self._insufficient(
                phenotype, label_real, ["NO_FIELDS"], (), (), 0.0
            )

        all_log_s: list[float] = []
        all_log_b: list[float] = []
        first_scale_vals: list[float] = []
        first_b0_vals: list[int] = []

        for fi, f in enumerate(fields):
            for s in self.scales:
                sig = compute_tda(f, min_persistence_frac=s)
                if fi == 0:
                    first_scale_vals.append(s)
                    first_b0_vals.append(sig.beta_0)
                if sig.beta_0 > 0:
                    all_log_s.append(np.log(s))
                    all_log_b.append(np.log(float(sig.beta_0)))

        n_pts = len(all_log_s)
        min_needed = self.min_scale_points * 2

        if n_pts < min_needed:
            return self._insufficient(
                phenotype, label_real,
                notes + [f"Only {n_pts} pooled points, need >= {min_needed}"],
                tuple(first_scale_vals), tuple(first_b0_vals),
                time.perf_counter() - t0,
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = _compute_gamma_robust(
                np.array(all_log_s), np.array(all_log_b), self.n_bootstrap
            )

        gamma = r["gamma"]
        r2 = r["r2"]
        valid = r2 >= self.min_r2 and n_pts >= min_needed

        notes.append(
            f"# Series: {len(fields)} frames x {len(self.scales)} scales = {n_pts} points"
        )

        return MultiScaleResult(
            phenotype=phenotype,
            gamma_b0=gamma,
            r_squared=r2,
            ci95_lo=r["ci95_lo"],
            ci95_hi=r["ci95_hi"],
            p_value=r["p_value"],
            n_scale_points=n_pts,
            valid=valid,
            is_organized=abs(gamma) >= self.organized_threshold,
            abs_gamma=abs(gamma),
            scale_values=tuple(first_scale_vals),
            beta0_values=tuple(first_b0_vals),
            label_real=label_real,
            evidence_type="real" if label_real else "synthetic_biological_proxy",
            notes=notes,
            elapsed_s=time.perf_counter() - t0,
        )

    def _insufficient(
        self, phenotype: str, label_real: bool, notes: list[str],
        sv: tuple, bv: tuple, elapsed: float,
    ) -> MultiScaleResult:
        return MultiScaleResult(
            phenotype=phenotype, gamma_b0=0.0, r_squared=0.0,
            ci95_lo=0.0, ci95_hi=0.0, p_value=1.0, n_scale_points=0,
            valid=False, is_organized=False, abs_gamma=0.0,
            scale_values=sv, beta0_values=bv,
            label_real=label_real, notes=notes, elapsed_s=elapsed,
        )


# ── Full Validator ────────────────────────────────────────────


class MultiScaleValidator:
    """Full pipeline: density fields -> gamma_b0 -> verdict.

    1. WT fields -> compute_series
    2. Random control (spatial shuffle of WT) -> compute_series
    3. Mutant fields (if provided) -> compute_series
    4. separation_ratio = |gamma_WT| / |gamma_noise|
    5. Verdict
    """

    def __init__(
        self,
        scales: list[float] | None = None,
        n_bootstrap: int = 1000,
        verbose: bool = False,
    ) -> None:
        self.computer = MultiScaleGammaComputer(
            scales=scales, n_bootstrap=n_bootstrap
        )
        self.control_gen = RandomControlGenerator(seed=42)
        self.verbose = verbose

    def validate(
        self,
        wt_fields: list[np.ndarray],
        mut_fields: list[np.ndarray] | None = None,
        label_real: bool = False,
    ) -> MultiScaleValidationReport:
        print(
            f"\n[MULTI-SCALE gamma] {len(wt_fields)} WT frames, "
            f"scales={list(DEFAULT_SCALES)}"
        )

        control_fields = self.control_gen.spatial_shuffle(wt_fields)

        wt_result = self.computer.compute_series(
            wt_fields, "wild_type", label_real
        )
        ctrl_result = self.computer.compute_series(
            control_fields, "random_control", label_real
        )

        mut_result = None
        if mut_fields:
            mut_result = self.computer.compute_series(
                mut_fields, "mutant", label_real
            )

        sep = wt_result.abs_gamma / max(ctrl_result.abs_gamma, 1e-6)

        wt_org = wt_result.is_organized
        ctrl_not = not ctrl_result.is_organized
        sep_ok = sep >= SEPARATION_RATIO

        if (
            wt_result.valid
            and ctrl_result.valid
            and wt_org
            and ctrl_not
            and sep_ok
        ):
            verdict = "SUPPORTED"
        elif not wt_result.valid or not ctrl_result.valid:
            verdict = "INCONCLUSIVE"
        elif wt_org and not sep_ok:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "FALSIFIED"

        report = MultiScaleValidationReport(
            wild_type=wt_result,
            random_control=ctrl_result,
            mutant=mut_result,
            separation_ratio=sep,
            verdict=verdict,
            hypothesis_supported=(verdict == "SUPPORTED"),
            label_real=label_real,
            timestamp=datetime.datetime.now(
                tz=datetime.timezone.utc
            ).isoformat(),
        )

        print(report.summary())
        return report
