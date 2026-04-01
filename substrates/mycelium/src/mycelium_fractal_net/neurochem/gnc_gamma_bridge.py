"""GNC+ ↔ γ-Scaling Bridge — correlating neuromodulatory state with scaling exponents.

Hypothesis (Vasylenko 2026):
    - Coherence > 0.7 → γ ∈ [1.0, 1.5] (healthy scaling, economies of scale)
    - Coherence < 0.4 → R² < 0.3 (no power law = pathological noise)
    - Dominant=Dopamine + high eta → γ > 1.5 (accelerating complexity)
    - Dominant=GABA + low alpha → γ < 0.5 (rigid, brittle)

Ref: Vasylenko (2026) γ-scaling on brain organoids: γ_WT2D = +1.487 ± 0.208
"""

from __future__ import annotations

from dataclasses import dataclass

from .gnc import GNCState, gnc_diagnose

__all__ = ["GNCGammaCorrelation", "correlate_gnc_gamma", "predict_gamma_regime"]


@dataclass
class GNCGammaCorrelation:
    """Result of GNC+ ↔ γ correlation analysis."""

    predicted_gamma_range: tuple[float, float]
    actual_gamma: float
    actual_r2: float
    match: bool
    gnc_regime: str
    gnc_coherence: float
    dominant_axis: str
    interpretation: str

    def summary(self) -> str:
        status = "MATCH" if self.match else "MISMATCH"
        return (
            f"[GNC+↔γ] {status}: predicted γ∈[{self.predicted_gamma_range[0]:.1f},"
            f"{self.predicted_gamma_range[1]:.1f}] actual={self.actual_gamma:.3f} "
            f"R²={self.actual_r2:.3f} regime={self.gnc_regime}"
        )


def predict_gamma_regime(state: GNCState) -> tuple[float, float, str]:
    """Predict γ range from GNC+ state. Returns (gamma_low, gamma_high, reason)."""
    diag = gnc_diagnose(state)

    if diag.coherence > 0.7 and diag.theta_imbalance < 0.12:
        return (1.0, 1.5, "high coherence → healthy scaling")

    if diag.coherence < 0.4:
        return (-1.0, 0.5, "low coherence → pathological or absent scaling")

    if diag.dominant_axis == "Dopamine" and state.theta["eta"] > 0.6:
        return (1.5, 3.0, "DA-dominant + high persistence → accelerating")

    if diag.dominant_axis == "GABA" and state.theta["alpha"] < 0.35:
        return (0.0, 0.5, "GABA-dominant + low plasticity → rigid")

    if diag.dominant_axis == "Noradrenaline":
        return (0.5, 1.5, "NA-dominant → variable scaling")

    return (0.5, 2.0, "mixed regime → broad prediction range")


def correlate_gnc_gamma(
    gnc_state: GNCState,
    gamma_result: float,
    r_squared: float,
) -> GNCGammaCorrelation:
    """Check correlation between GNC+ state and γ-scaling result.

    Args:
        gnc_state: current GNC+ state
        gamma_result: measured γ exponent
        r_squared: R² of the log-log fit
    """
    diag = gnc_diagnose(gnc_state)
    low, high, reason = predict_gamma_regime(gnc_state)

    # Match check
    gamma_in_range = low <= gamma_result <= high
    r2_consistent = True

    if diag.coherence < 0.4 and r_squared > 0.7:
        r2_consistent = False
        reason += " | but R² unexpectedly high"

    match = gamma_in_range and r2_consistent

    if match:
        interpretation = f"GNC+ prediction confirmed: {reason}"
    elif not gamma_in_range:
        interpretation = (
            f"γ={gamma_result:.3f} outside predicted [{low:.1f},{high:.1f}]. "
            f"GNC+ says {reason}, but data disagrees."
        )
    else:
        interpretation = f"R² inconsistency: coherence={diag.coherence:.2f} but R²={r_squared:.2f}"

    return GNCGammaCorrelation(
        predicted_gamma_range=(low, high),
        actual_gamma=gamma_result,
        actual_r2=r_squared,
        match=match,
        gnc_regime=diag.regime,
        gnc_coherence=diag.coherence,
        dominant_axis=diag.dominant_axis,
        interpretation=interpretation,
    )
