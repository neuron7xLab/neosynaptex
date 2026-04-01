"""Wolfram Bridge — computational irreducibility detection for MFN fields.

Three principles from Wolfram's NKS (2002) that ground this system:

1. **Computational Irreducibility (CI)**: Some systems cannot be predicted
   faster than running them. When CI is detected, the system is at a point
   where analytical shortcuts fail — this is precisely where A_C activates.
   Ref: Wolfram (2002) A New Kind of Science, Ch.12

2. **Principle of Computational Equivalence (PCE)**: All sufficiently complex
   systems are computationally equivalent — neuron, hypha, agent have the same
   computational power. This grounds CCP substrate-independence (Theorem 3).
   Ref: Wolfram (2002) Ch.12, p.715-846

3. **Intrinsic Randomness Generation**: Natural systems generate their own
   randomness without external noise. MFN reaction-diffusion does this —
   validating why synthetic substrates in G3 produce genuine complexity.
   Ref: Wolfram (2002) Ch.7

Detection method:
   A field state is computationally irreducible when:
   - Algorithmic complexity is high (LZ76 incompressibility)
   - Dynamics are chaotic (Lyapunov lambda_1 > 0)
   - Prediction residual exceeds trivial baseline

   CI score = w_K * K_norm + w_L * L_norm + w_P * P_norm

   where:
     K_norm = LZ76 complexity / max_LZ76 (incompressibility)
     L_norm = clip(lambda_1, 0, 1)          (chaos indicator)
     P_norm = prediction_residual / field_var (unpredictability)

Ref: Vasylenko (2026), Wolfram (2002), Lempel & Ziv (1976)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from mycelium_fractal_net.types.field import FieldSequence

__all__ = [
    "ComputationalIrreducibilityReport",
    "compute_incompressibility",
    "compute_prediction_residual",
    "detect_computational_irreducibility",
]

_log = logging.getLogger(__name__)

# ── Thresholds ───────────────────────────────────────────────────────

CI_THRESHOLD = 0.6  # CI score above which system is irreducible
LAMBDA_CHAOS_THRESHOLD = 0.0  # Lyapunov > 0 = sensitive to IC
INCOMPRESSIBILITY_THRESHOLD = 0.5  # LZ76 normalized > 0.5 = complex

# Weights for CI composite score
W_COMPLEXITY = 0.4  # algorithmic complexity (LZ76)
W_LYAPUNOV = 0.3  # dynamical chaos
W_PREDICTION = 0.3  # prediction failure


# ── Types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ComputationalIrreducibilityReport:
    """Result of CI detection on a field state.

    Attributes
    ----------
    ci_score : float in [0, 1]
        Composite CI score. Higher = more irreducible.
    is_irreducible : bool
        True if ci_score > CI_THRESHOLD.
    incompressibility : float in [0, 1]
        Normalized Lempel-Ziv complexity. 1.0 = maximally incompressible.
    lyapunov_indicator : float
        Normalized chaos indicator. Positive = sensitive dependence on IC.
    prediction_residual : float
        Normalized prediction error. Higher = less predictable.
    pce_complexity_class : str
        Wolfram complexity class: "1_fixed", "2_periodic", "3_chaotic", "4_complex".
        Class 4 (edge of chaos) corresponds to CCP cognitive window.
    intrinsic_randomness : float in [0, 1]
        Fraction of field variance attributable to intrinsic dynamics (not noise).
    """

    ci_score: float
    is_irreducible: bool
    incompressibility: float
    lyapunov_indicator: float
    prediction_residual: float
    pce_complexity_class: str
    intrinsic_randomness: float

    def to_dict(self) -> dict[str, object]:
        """Serialise to plain dict (JSON-safe)."""
        return {
            "ci_score": self.ci_score,
            "is_irreducible": self.is_irreducible,
            "incompressibility": self.incompressibility,
            "lyapunov_indicator": self.lyapunov_indicator,
            "prediction_residual": self.prediction_residual,
            "pce_complexity_class": self.pce_complexity_class,
            "intrinsic_randomness": self.intrinsic_randomness,
        }

    def summary(self) -> str:
        return (
            f"[CI:{self.ci_score:.3f} {'IRREDUCIBLE' if self.is_irreducible else 'reducible'}] "
            f"K={self.incompressibility:.3f} λ={self.lyapunov_indicator:.3f} "
            f"P={self.prediction_residual:.3f} class={self.pce_complexity_class}"
        )


# ── Core computations ────────────────────────────────────────────────


def _lz76_complexity(binary_sequence: np.ndarray) -> int:
    """Lempel-Ziv 1976 complexity: count of distinct patterns.

    Ref: Lempel & Ziv (1976) IEEE Trans. Inform. Theory
    """
    s = binary_sequence.astype(np.int8)
    n = len(s)
    if n == 0:
        return 0

    complexity = 1
    i = 0
    k = 1
    k_max = 1
    while i + k <= n:
        # Check if s[i+1:i+k+1] appears in s[0:i+k]
        if k > k_max:
            complexity += 1
            i += k_max
            k = 1
            k_max = 1
        else:
            # Search for s[i+1:i+k+1] in s[0:i+k]
            found = False
            substr = s[i + 1:i + k + 1] if i + k + 1 <= n else s[i + 1:n]
            if len(substr) == 0:
                break
            for j in range(i + k):
                if j + len(substr) > i + k:
                    break
                if np.array_equal(s[j:j + len(substr)], substr):
                    found = True
                    break
            if found:
                k += 1
                k_max = max(k_max, k)
            else:
                complexity += 1
                i += k_max
                k = 1
                k_max = 1

    return complexity


def compute_incompressibility(field: np.ndarray) -> float:
    """Normalized algorithmic complexity via Lempel-Ziv 1976.

    Returns value in [0, 1]. Higher = more incompressible = more complex.
    Maximally random sequence → ~1.0.
    Constant/periodic → ~0.0.

    Ref: Lempel & Ziv (1976), Wolfram (2002) Ch.12
    """
    flat = field.flatten()
    median_val = np.median(flat)
    binary = (flat > median_val).astype(np.int8)

    n = len(binary)
    if n < 4:
        return 0.0

    c = _lz76_complexity(binary)

    # Normalize: random binary string of length n has
    # expected complexity ~ n / log2(n)
    log2_n = np.log2(n) if n > 1 else 1.0
    c_max = n / log2_n
    return float(np.clip(c / c_max, 0.0, 1.0))


def _estimate_lyapunov_from_field(field: np.ndarray, epsilon: float = 1e-4) -> float:
    """Estimate largest Lyapunov exponent from spatial field.

    Uses the Kantz method approximation: measure divergence of
    nearby trajectories in delay-embedded space.

    Returns normalized indicator in [-1, 1].
    Positive = chaotic. Zero = edge. Negative = stable.
    """
    flat = field.flatten()
    n = len(flat)
    if n < 50:
        return 0.0

    # Delay embedding (tau=1, dim=3)
    dim = 3
    embedded = np.column_stack([flat[i:n - dim + i + 1] for i in range(dim)])
    m = len(embedded)
    if m < 20:
        return 0.0

    # Find nearest neighbors and measure divergence
    rng = np.random.RandomState(42)
    sample_idx = rng.choice(m - 1, min(100, m - 1), replace=False)

    divergences = []
    for idx in sample_idx:
        point = embedded[idx]
        dists = np.linalg.norm(embedded - point, axis=1)
        dists[idx] = np.inf
        nn_idx = np.argmin(dists)
        nn_dist = dists[nn_idx]

        if nn_dist < epsilon or nn_idx >= m - 1 or idx >= m - 1:
            continue

        # One-step divergence
        next_dist = np.linalg.norm(embedded[idx + 1] - embedded[nn_idx + 1])
        if nn_dist > 1e-12:
            divergences.append(np.log(max(next_dist, 1e-12) / nn_dist))

    if not divergences:
        return 0.0

    lambda_1 = float(np.mean(divergences))
    return float(np.clip(lambda_1, -1.0, 1.0))


def compute_prediction_residual(
    field: np.ndarray,
    history: np.ndarray | None = None,
) -> float:
    """Normalized prediction error: how much worse than trivial is prediction?

    Trivial prediction = persistence (next state = current state).
    If actual dynamics deviate significantly → high residual → CI.

    Returns value in [0, 1]. Higher = less predictable.
    """
    if history is None or len(history) < 3:
        # Without history, use spatial predictability (each pixel from neighbors)
        # Laplacian residual: how different is each point from its neighborhood mean
        mean_field = (
            np.roll(field, 1, 0) + np.roll(field, -1, 0) +
            np.roll(field, 1, 1) + np.roll(field, -1, 1)
        ) / 4.0
        residual = np.mean((field - mean_field) ** 2)
        field_var = np.var(field) + 1e-12
        return float(np.clip(residual / field_var, 0.0, 1.0))

    # With history: compare persistence prediction vs actual
    predicted = history[-2]  # persistence: predict t from t-1
    actual = history[-1]
    residual = np.mean((actual - predicted) ** 2)
    field_var = np.var(history) + 1e-12
    return float(np.clip(residual / field_var, 0.0, 1.0))


def _classify_wolfram(
    incompressibility: float,
    lyapunov: float,
    prediction_residual: float,
) -> str:
    """Classify into Wolfram's 4 complexity classes.

    Class 1: Fixed point (low K, low λ, low P)
    Class 2: Periodic (low K, low λ, low P but structured)
    Class 3: Chaotic (high K, high λ, high P)
    Class 4: Complex/edge-of-chaos (medium K, λ ≈ 0, medium P)
             This is the CCP cognitive window.

    Ref: Wolfram (2002) Ch.6
    """
    if incompressibility < 0.2 and lyapunov < 0.05:
        return "1_fixed" if prediction_residual < 0.1 else "2_periodic"

    if lyapunov > 0.3 and incompressibility > 0.7:
        return "3_chaotic"

    if 0.1 <= incompressibility <= 0.8 and -0.1 <= lyapunov <= 0.3:
        return "4_complex"

    # Default classification by dominant feature
    if incompressibility > 0.6:
        return "3_chaotic"
    if lyapunov < -0.1:
        return "1_fixed"
    return "2_periodic"


def _estimate_intrinsic_randomness(field: np.ndarray) -> float:
    """Estimate fraction of variance from intrinsic dynamics vs noise.

    Uses spectral analysis: intrinsic dynamics produce structured spectra,
    noise produces flat spectra. Ratio of structured power to total power.
    """
    fft = np.fft.fft2(field)
    power = np.abs(fft) ** 2
    total_power = power.sum()
    if total_power < 1e-12:
        return 0.0

    # Sort power spectrum: intrinsic = concentrated in few modes
    sorted_power = np.sort(power.flatten())[::-1]
    n = len(sorted_power)

    # Fraction of power in top 10% of modes
    top_10_pct = int(max(1, n * 0.1))
    concentrated = sorted_power[:top_10_pct].sum() / total_power

    # High concentration = structured (intrinsic). Low = noise.
    # Random noise: concentrated ≈ 0.1. Pure signal: concentrated ≈ 1.0.
    intrinsic = float(np.clip((concentrated - 0.1) / 0.9, 0.0, 1.0))
    return intrinsic


# ── Main API ─────────────────────────────────────────────────────────


def detect_computational_irreducibility(
    seq: FieldSequence,
) -> dict[str, object]:
    """Detect computational irreducibility in a field state.

    Combines three signals:
    1. Algorithmic complexity (LZ76 incompressibility)
    2. Dynamical chaos (Lyapunov indicator from field structure)
    3. Prediction failure (how much dynamics resist forecasting)

    The CI score determines whether the system is at a point where
    analytical shortcuts fail — triggering the need for A_C.

    Parameters
    ----------
    seq : FieldSequence
        Output of mfn.simulate(). History improves prediction residual.

    Returns
    -------
    dict
        JSON-safe dictionary with CI metrics.
    """
    field = np.asarray(seq.field, dtype=np.float64)
    history = seq.history if hasattr(seq, "history") else None

    # 1. Algorithmic complexity (Wolfram Ch.12)
    K = compute_incompressibility(field)

    # 2. Lyapunov chaos indicator
    L = _estimate_lyapunov_from_field(field)
    L_norm = float(np.clip(L, 0.0, 1.0))  # only positive part for CI

    # 3. Prediction residual
    P = compute_prediction_residual(field, history)

    # Composite CI score
    ci_score = float(np.clip(
        W_COMPLEXITY * K + W_LYAPUNOV * L_norm + W_PREDICTION * P,
        0.0, 1.0,
    ))

    # Wolfram classification
    pce_class = _classify_wolfram(K, L, P)

    # Intrinsic randomness
    intrinsic = _estimate_intrinsic_randomness(field)

    return ComputationalIrreducibilityReport(
        ci_score=ci_score,
        is_irreducible=ci_score > CI_THRESHOLD,
        incompressibility=round(K, 6),
        lyapunov_indicator=round(L, 6),
        prediction_residual=round(P, 6),
        pce_complexity_class=pce_class,
        intrinsic_randomness=round(intrinsic, 6),
    ).to_dict()
