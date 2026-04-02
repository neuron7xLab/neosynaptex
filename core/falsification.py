"""Falsification shield — systematic method-sensitivity tests for γ ≈ 1.0.

Three independent falsification axes:
1. Estimator sensitivity: Theil-Sen vs OLS vs Huber — does γ change?
2. Null ensemble: shuffle + IAAFT + phase-randomized across ALL substrates
3. Method bias detector: inject known γ, measure recovery error per method

If γ ≈ 1.0 is an artifact of Theil-Sen on short series, Axis 1 will show it.
If γ ≈ 1.0 is spectral artifact, Axis 2 (IAAFT) will fail to destroy it.
If the method is biased toward 1.0, Axis 3 will expose the bias curve.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from scipy.stats import theilslopes

from core.iaaft import iaaft_surrogate, surrogate_p_value

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EstimatorResult:
    name: str
    gamma: float
    ci_low: float
    ci_high: float
    r2: float


@dataclass(frozen=True)
class NullEnsembleResult:
    substrate: str
    gamma_observed: float
    p_shuffle: float
    p_iaaft: float
    p_phase_rand: float
    significant: bool  # all three p < 0.05


@dataclass(frozen=True)
class BiasProbeResult:
    gamma_true: float
    gamma_theilsen: float
    gamma_ols: float
    gamma_huber: float
    bias_theilsen: float
    bias_ols: float
    bias_huber: float


@dataclass(frozen=True)
class FalsificationReport:
    estimator_sensitivity: list[dict[str, list[EstimatorResult]]]
    null_ensemble: list[NullEnsembleResult]
    bias_curve: list[BiasProbeResult]
    verdict: str  # ROBUST | FRAGILE | INCONCLUSIVE


# ─── Axis 1: Estimator Sensitivity ──────────────────────────────────────


def _ols_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """OLS regression. Returns (slope, intercept, r2)."""
    n = len(x)
    sx, sy = np.sum(x), np.sum(y)
    sxx = np.sum(x * x)
    sxy = np.sum(x * y)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-15:
        return float("nan"), float("nan"), 0.0
    slope = float((n * sxy - sx * sy) / denom)
    intercept = float((sy - slope * sx) / n)
    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0
    return slope, intercept, r2


def _huber_slope(x: np.ndarray, y: np.ndarray, delta: float = 1.345) -> tuple[float, float, float]:
    """Iteratively reweighted least squares with Huber loss. Returns (slope, intercept, r2)."""
    # Start with OLS
    slope, intercept, _ = _ols_slope(x, y)
    if np.isnan(slope):
        return float("nan"), float("nan"), 0.0

    for _ in range(20):
        residuals = y - (slope * x + intercept)
        weights = np.where(np.abs(residuals) <= delta, 1.0, delta / np.abs(residuals + 1e-10))
        w_sum = np.sum(weights)
        wx = np.sum(weights * x)
        wy = np.sum(weights * y)
        wxx = np.sum(weights * x * x)
        wxy = np.sum(weights * x * y)
        denom = w_sum * wxx - wx * wx
        if abs(denom) < 1e-15:
            break
        new_slope = float((w_sum * wxy - wx * wy) / denom)
        new_intercept = float((wy - new_slope * wx) / w_sum)
        if abs(new_slope - slope) < 1e-8:
            slope, intercept = new_slope, new_intercept
            break
        slope, intercept = new_slope, new_intercept

    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0
    return slope, intercept, r2


def estimate_gamma_multi(
    log_topo: np.ndarray,
    log_cost: np.ndarray,
    n_boot: int = 500,
    seed: int = 42,
) -> list[EstimatorResult]:
    """Estimate γ using three independent estimators with bootstrap CI."""
    rng = np.random.default_rng(seed)
    results: list[EstimatorResult] = []
    n = len(log_topo)

    def _est_ts(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
        s = theilslopes(y, x)
        return (-s[0], s[1])

    def _est_ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
        s, i, _ = _ols_slope(x, y)
        return (-s, i)

    def _est_huber(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
        s, i, _ = _huber_slope(x, y)
        return (-s, i)

    estimators = [("theilslopes", _est_ts), ("ols", _est_ols), ("huber", _est_huber)]

    for name, estimator_fn in estimators:
        gamma_point, _ = estimator_fn(log_topo, log_cost)

        # Bootstrap CI
        boot_gammas = np.empty(n_boot)
        for i in range(n_boot):
            idx = rng.integers(0, n, n)
            g, _ = estimator_fn(log_topo[idx], log_cost[idx])
            boot_gammas[i] = g

        ci_lo = float(np.percentile(boot_gammas, 2.5))
        ci_hi = float(np.percentile(boot_gammas, 97.5))

        # R2 from point estimate
        slope_ts = theilslopes(log_cost, log_topo)
        yhat = slope_ts[0] * log_topo + slope_ts[1]
        ss_res = float(np.sum((log_cost - yhat) ** 2))
        ss_tot = float(np.sum((log_cost - np.mean(log_cost)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0

        results.append(
            EstimatorResult(name=name, gamma=float(gamma_point), ci_low=ci_lo, ci_high=ci_hi, r2=r2)
        )

    return results


# ─── Axis 2: Null Ensemble ──────────────────────────────────────────────


def null_ensemble_test(
    log_topo: np.ndarray,
    log_cost: np.ndarray,
    n_surrogates: int = 199,
    seed: int = 42,
) -> NullEnsembleResult:
    """Three null models: shuffle, IAAFT, phase-randomization."""
    # Observed gamma
    slope_obs, *_ = theilslopes(log_cost, log_topo)
    gamma_obs = float(-slope_obs)

    rng = np.random.default_rng(seed)
    n = len(log_cost)

    # 1. Shuffle null
    shuffle_gammas = np.empty(n_surrogates)
    for i in range(n_surrogates):
        perm = rng.permutation(log_cost)
        s, *_ = theilslopes(perm, log_topo)
        shuffle_gammas[i] = -s
    p_shuffle = surrogate_p_value(gamma_obs, shuffle_gammas)

    # 2. IAAFT null (preserves spectrum, destroys nonlinear structure)
    iaaft_gammas = np.empty(n_surrogates)
    for i in range(n_surrogates):
        surr, _, _ = iaaft_surrogate(log_cost, n_iter=200, rng=np.random.default_rng(seed + i))
        s, *_ = theilslopes(surr, log_topo)
        iaaft_gammas[i] = -s
    p_iaaft = surrogate_p_value(gamma_obs, iaaft_gammas)

    # 3. Phase randomization (preserves amplitude spectrum, randomizes phase)
    phase_gammas = np.empty(n_surrogates)
    ft = np.fft.rfft(log_cost)
    amplitudes = np.abs(ft)
    for i in range(n_surrogates):
        random_phases = rng.uniform(0, 2 * np.pi, len(ft))
        random_phases[0] = 0  # preserve DC
        if n % 2 == 0:
            random_phases[-1] = 0  # preserve Nyquist
        surr_ft = amplitudes * np.exp(1j * random_phases)
        surr = np.fft.irfft(surr_ft, n=n)
        s, *_ = theilslopes(surr, log_topo)
        phase_gammas[i] = -s
    p_phase = surrogate_p_value(gamma_obs, phase_gammas)

    return NullEnsembleResult(
        substrate="",
        gamma_observed=gamma_obs,
        p_shuffle=float(p_shuffle),
        p_iaaft=float(p_iaaft),
        p_phase_rand=float(p_phase),
        significant=p_shuffle < 0.05 and p_iaaft < 0.05 and p_phase < 0.05,
    )


# ─── Axis 3: Method Bias Detector ──────────────────────────────────────


def bias_probe(
    gamma_values: list[float] | None = None,
    n_points: int = 128,
    noise: float = 0.05,
    n_trials: int = 50,
    seed: int = 42,
) -> list[BiasProbeResult]:
    """Inject known γ, measure recovery error per estimator."""
    if gamma_values is None:
        gamma_values = [0.0, 0.3, 0.5, 0.7, 0.85, 1.0, 1.15, 1.3, 1.5, 2.0]

    rng = np.random.default_rng(seed)
    results: list[BiasProbeResult] = []

    for gamma_true in gamma_values:
        ts_gammas, ols_gammas, hub_gammas = [], [], []

        for _ in range(n_trials):
            topo = np.linspace(1, 10, n_points)
            cost = 10.0 * topo ** (-gamma_true) + rng.normal(0, noise, n_points)
            cost = np.clip(cost, 1e-6, None)
            lt, lc = np.log(topo), np.log(cost)

            s_ts, *_ = theilslopes(lc, lt)
            ts_gammas.append(-s_ts)

            s_ols, _, _ = _ols_slope(lt, lc)
            ols_gammas.append(-s_ols)

            s_hub, _, _ = _huber_slope(lt, lc)
            hub_gammas.append(-s_hub)

        results.append(
            BiasProbeResult(
                gamma_true=gamma_true,
                gamma_theilsen=float(np.mean(ts_gammas)),
                gamma_ols=float(np.mean(ols_gammas)),
                gamma_huber=float(np.mean(hub_gammas)),
                bias_theilsen=float(np.mean(ts_gammas) - gamma_true),
                bias_ols=float(np.mean(ols_gammas) - gamma_true),
                bias_huber=float(np.mean(hub_gammas) - gamma_true),
            )
        )

    return results


# ─── Full Report ────────────────────────────────────────────────────────


def run_falsification(
    substrates: dict[str, tuple[np.ndarray, np.ndarray]],
    seed: int = 42,
) -> FalsificationReport:
    """Run complete falsification suite on all substrates.

    Args:
        substrates: {name: (log_topo, log_cost)} for each substrate.

    Returns:
        FalsificationReport with verdict.
    """
    # Axis 1: Estimator sensitivity per substrate
    estimator_results: list[dict[str, list[EstimatorResult]]] = []
    for name, (lt, lc) in substrates.items():
        est = estimate_gamma_multi(lt, lc, seed=seed)
        estimator_results.append({name: est})

    # Axis 2: Null ensemble per substrate
    null_results: list[NullEnsembleResult] = []
    for name, (lt, lc) in substrates.items():
        nr = null_ensemble_test(lt, lc, seed=seed)
        null_results.append(
            NullEnsembleResult(
                substrate=name,
                gamma_observed=nr.gamma_observed,
                p_shuffle=nr.p_shuffle,
                p_iaaft=nr.p_iaaft,
                p_phase_rand=nr.p_phase_rand,
                significant=nr.significant,
            )
        )

    # Axis 3: Bias curve
    bias_results = bias_probe(seed=seed)

    # Verdict
    all_nulls_sig = all(nr.significant for nr in null_results)
    max_bias = max(abs(b.bias_theilsen) for b in bias_results)
    estimator_spread = []
    for er_dict in estimator_results:
        for est_list in er_dict.values():
            gammas = [e.gamma for e in est_list]
            if len(gammas) >= 2:
                estimator_spread.append(max(gammas) - min(gammas))

    max_spread = max(estimator_spread) if estimator_spread else 0.0

    if all_nulls_sig and max_bias < 0.1 and max_spread < 0.15:
        verdict = "ROBUST"
    elif not all_nulls_sig:
        verdict = "FRAGILE"
    else:
        verdict = "INCONCLUSIVE"

    return FalsificationReport(
        estimator_sensitivity=estimator_results,
        null_ensemble=null_results,
        bias_curve=bias_results,
        verdict=verdict,
    )
