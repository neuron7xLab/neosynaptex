"""ensemble_diagnose() — statistically hardened diagnosis across multiple seeds."""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

import numpy as np

from mycelium_fractal_net.core.diagnose import diagnose
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.types.ensemble import EnsembleDiagnosisReport

if TYPE_CHECKING:
    from mycelium_fractal_net.types.diagnosis import DiagnosisReport
    from mycelium_fractal_net.types.field import SimulationSpec

logger = logging.getLogger(__name__)

__all__ = ["ensemble_diagnose"]


def ensemble_diagnose(
    spec: SimulationSpec,
    *,
    n_runs: int = 7,
    seeds: list[int] | None = None,
    forecast_horizon: int = 8,
    skip_intervention: bool = True,
    causal_mode: str = "strict",
) -> EnsembleDiagnosisReport:
    """Run diagnose() across multiple seeds and aggregate statistically.

    Parameters
    ----------
    spec : SimulationSpec
        Base simulation spec.
    n_runs : int
        Number of independent runs. Default 7.
    seeds : list[int] | None
        Explicit seed list. Default: [spec.seed + i for i in range(n_runs)].
    forecast_horizon : int
        Forecast steps per run.
    skip_intervention : bool
        Skip intervention planning (default True for speed).
    causal_mode : str
        Causal validation mode.

    Returns
    -------
    EnsembleDiagnosisReport
        Aggregated result with majority voting, CI, and robustness flag.
    """
    from mycelium_fractal_net.types.field import SimulationSpec as _SS

    base_seed = spec.seed if spec.seed is not None else 42
    if seeds is None:
        seeds = [base_seed + i for i in range(n_runs)]

    reports: list[DiagnosisReport] = []
    for s in seeds:
        try:
            tick_spec = _SS(
                grid_size=spec.grid_size,
                steps=spec.steps,
                alpha=spec.alpha,
                spike_probability=spec.spike_probability,
                turing_enabled=spec.turing_enabled,
                turing_threshold=spec.turing_threshold,
                quantum_jitter=spec.quantum_jitter,
                jitter_var=spec.jitter_var,
                seed=s,
                neuromodulation=spec.neuromodulation,
            )
            seq = simulate_history(tick_spec)
            report = diagnose(
                seq,
                mode="fast" if skip_intervention else "full",
                forecast_horizon=forecast_horizon,
                skip_intervention=skip_intervention,
                causal_mode=causal_mode,
            )
            reports.append(report)
        except Exception:
            logger.warning("Ensemble run seed=%d failed", s, exc_info=True)

    if not reports:
        return EnsembleDiagnosisReport(
            majority_severity="unknown",
            majority_anomaly_label="unknown",
            dominant_transition_type="unknown",
            ews_score_mean=0.0,
            ews_score_std=0.0,
            ews_score_ci95=(0.0, 0.0),
            causal_pass_rate=0.0,
            confidence_boosted=False,
            n_runs=0,
            seeds_used=tuple(seeds),
        )

    n = len(reports)

    # Severity votes
    sev_counter = Counter(r.severity for r in reports)
    majority_severity = sev_counter.most_common(1)[0][0]

    # Anomaly label votes
    anom_counter = Counter(r.anomaly.label for r in reports)
    majority_anomaly = anom_counter.most_common(1)[0][0]

    # Transition type votes
    trans_counter = Counter(r.warning.transition_type for r in reports)
    dominant_transition = trans_counter.most_common(1)[0][0]

    # EWS statistics
    ews_scores = np.array([r.warning.ews_score for r in reports])
    ews_mean = float(np.mean(ews_scores))
    ews_std = float(np.std(ews_scores, ddof=1)) if n > 1 else 0.0
    margin = 1.96 * ews_std / max(1.0, np.sqrt(n))
    ews_ci95 = (round(max(0.0, ews_mean - margin), 4), round(min(1.0, ews_mean + margin), 4))

    # Causal pass rate
    causal_pass = sum(1 for r in reports if r.causal.decision.value == "pass")
    causal_pass_rate = causal_pass / n

    # Confidence boosted
    confidence_boosted = ews_std < 0.05

    return EnsembleDiagnosisReport(
        majority_severity=majority_severity,
        majority_anomaly_label=majority_anomaly,
        dominant_transition_type=dominant_transition,
        ews_score_mean=round(ews_mean, 4),
        ews_score_std=round(ews_std, 4),
        ews_score_ci95=ews_ci95,
        causal_pass_rate=round(causal_pass_rate, 4),
        confidence_boosted=confidence_boosted,
        severity_votes=dict(sev_counter),
        anomaly_label_votes=dict(anom_counter),
        transition_type_votes=dict(trans_counter),
        n_runs=n,
        seeds_used=tuple(seeds),
        individual_reports=tuple(reports),
    )
