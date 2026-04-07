"""H_φγ Invariant — Core analysis module.

Tests whether ``attention_ratio(t) = energy_core(t) / energy_periphery(t)``
converges to φ ≈ 1.618 or φ⁻¹ ≈ 0.618 when γ(t) → 1.0 across neosynaptex
substrates.

Three parallel ratio definitions:
  R1 — topology-energy: core/periphery by graph centrality (weighted degree)
  R2 — spectral-core: core = dominant PSD modes (top 38.2% spectral energy)
  R3 — predictive-allocation: core = features with top 38.2% prediction weight
"""

from __future__ import annotations

import argparse
import json
from typing import Any

import numpy as np
from scipy import signal as sp_signal
from scipy.stats import theilslopes

from analysis.phi_gamma_nulls import (
    null_phase_randomization,
    null_temporal_shuffle,
    null_topology_shuffle,
)
from analysis.phi_gamma_report import build_report, build_substrate_entry, save_report

# ── Fixed Constants ──────────────────────────────────────────────────────────
PHI: float = 1.6180339887498949
PHI_INV: float = 0.6180339887498949


# ── Gamma Computation ────────────────────────────────────────────────────────
def compute_gamma_windows(
    signal_data: np.ndarray,
    window: int = 256,
    step: int = 32,
) -> np.ndarray:
    """Compute γ for each rolling window using PSD slope estimation.

    For each window the power spectral density is estimated via Welch's method,
    then the negative slope in log-log space gives the spectral exponent β.
    γ is defined as β (the spectral scaling exponent).

    Parameters
    ----------
    signal_data : np.ndarray
        1-D time series.
    window : int
        Window length in samples.
    step : int
        Step size between consecutive windows.

    Returns
    -------
    np.ndarray
        Array of γ values, one per window.
    """
    n = len(signal_data)
    gammas: list[float] = []
    for start in range(0, n - window + 1, step):
        seg = signal_data[start : start + window]
        freqs, psd = sp_signal.welch(seg, nperseg=min(64, window // 2))
        # Drop DC component
        mask = freqs > 0
        freqs = freqs[mask]
        psd = psd[mask]
        if len(freqs) < 4:
            gammas.append(np.nan)
            continue
        # Guard against zero PSD values
        valid = psd > 0
        if valid.sum() < 4:
            gammas.append(np.nan)
            continue
        log_f = np.log10(freqs[valid])
        log_p = np.log10(psd[valid])
        slope, _, _, _ = theilslopes(log_p, log_f)
        gammas.append(-slope)
    return np.array(gammas, dtype=np.float64)


# ── Core/Periphery Partition ─────────────────────────────────────────────────
def build_core_periphery(
    window_data: np.ndarray,
    method: str = "weighted_degree",
    core_fraction: float = 0.382,
) -> tuple[np.ndarray, np.ndarray]:
    """Partition nodes into core (top fraction by centrality) and periphery.

    Parameters
    ----------
    window_data : np.ndarray
        Shape ``(n_nodes, n_time)`` — multivariate window.
    method : str
        Centrality metric.  Only ``"weighted_degree"`` is currently supported.
    core_fraction : float
        Fraction of nodes assigned to the core.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        ``(core_indices, periphery_indices)`` — sorted integer arrays.
    """
    n_nodes = window_data.shape[0]
    if method != "weighted_degree":
        raise ValueError(f"Unsupported centrality method: {method}")

    # Weighted degree = sum of absolute pairwise correlations per node
    corr = np.corrcoef(window_data)
    np.fill_diagonal(corr, 0.0)
    centrality = np.nansum(np.abs(corr), axis=1)

    n_core = max(1, int(np.ceil(n_nodes * core_fraction)))
    ranked = np.argsort(centrality)[::-1]
    core_idx = np.sort(ranked[:n_core])
    periphery_idx = np.sort(ranked[n_core:])
    return core_idx, periphery_idx


# ── Energy Ratio ─────────────────────────────────────────────────────────────
def compute_energy_ratio(
    window_data: np.ndarray,
    core_idx: np.ndarray,
    periphery_idx: np.ndarray,
    delta: float = 1e-12,
) -> float:
    """Compute R(t) = Σ(x_core²) / (Σ(x_periphery²) + δ).

    Parameters
    ----------
    window_data : np.ndarray
        Shape ``(n_nodes, n_time)``.
    core_idx, periphery_idx : np.ndarray
        Index arrays for core and periphery nodes.
    delta : float
        Denominator guard against division by zero.

    Returns
    -------
    float
        Finite, non-negative energy ratio.
    """
    e_core = float(np.sum(window_data[core_idx] ** 2))
    e_periphery = float(np.sum(window_data[periphery_idx] ** 2))
    return e_core / (e_periphery + delta)


# ── Unity Window Selection ───────────────────────────────────────────────────
def select_unity_windows(
    gamma_series: np.ndarray,
    epsilon: float = 0.10,
) -> np.ndarray:
    """Return boolean mask where |γ − 1| < ε.

    Parameters
    ----------
    gamma_series : np.ndarray
        Array of γ values.
    epsilon : float
        Tolerance around unity.

    Returns
    -------
    np.ndarray
        Boolean mask of the same length as *gamma_series*.
    """
    return np.abs(gamma_series - 1.0) < epsilon


# ── Bootstrap Confidence Interval ────────────────────────────────────────────
def bootstrap_ratio_ci(
    ratios: np.ndarray,
    n_boot: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap confidence interval for the median ratio.

    Parameters
    ----------
    ratios : np.ndarray
        Observed ratio values.
    n_boot : int
        Number of bootstrap replicates.
    ci : float
        Confidence level (e.g. 0.95).
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    tuple[float, float]
        ``(lower, upper)`` bounds of the CI.
    """
    rng = np.random.default_rng(seed)
    n = len(ratios)
    if n == 0:
        return (np.nan, np.nan)
    medians = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(ratios, size=n, replace=True)
        medians[i] = np.median(sample)
    alpha = (1.0 - ci) / 2.0
    lower = float(np.percentile(medians, 100 * alpha))
    upper = float(np.percentile(medians, 100 * (1.0 - alpha)))
    return (lower, upper)


# ── Spectral-Core Ratio (R2) ────────────────────────────────────────────────
def compute_spectral_energy_ratio(
    window_data: np.ndarray,
    core_fraction: float = 0.382,
    delta: float = 1e-12,
) -> float:
    """R2 — spectral-core ratio.

    Core = dominant PSD modes whose cumulative energy reaches top ``core_fraction``
    of total spectral energy.  Periphery = remaining spectral energy.

    Parameters
    ----------
    window_data : np.ndarray
        Shape ``(n_nodes, n_time)`` or ``(n_time,)`` for 1-D.
    core_fraction : float
        Fraction of spectral energy considered *core*.
    delta : float
        Denominator guard.

    Returns
    -------
    float
        Spectral energy ratio.
    """
    sig = window_data[np.newaxis, :] if window_data.ndim == 1 else window_data

    total_core = 0.0
    total_periphery = 0.0
    for ch in range(sig.shape[0]):
        _, psd = sp_signal.welch(sig[ch], nperseg=min(64, sig.shape[1] // 2))
        sorted_psd = np.sort(psd)[::-1]
        cum = np.cumsum(sorted_psd)
        total = cum[-1] if len(cum) > 0 else 0.0
        if total <= 0:
            continue
        threshold = total * core_fraction
        core_mask = cum <= threshold
        # Always include at least the first mode
        if not core_mask.any():
            core_mask[0] = True
        e_core = float(sorted_psd[core_mask].sum())
        e_periph = float(sorted_psd[~core_mask].sum())
        total_core += e_core
        total_periphery += e_periph

    return total_core / (total_periphery + delta)


# ── Predictive-Allocation Ratio (R3) ────────────────────────────────────────
def compute_predictive_ratio(
    window_data: np.ndarray,
    core_fraction: float = 0.382,
    delta: float = 1e-12,
) -> float:
    """R3 — predictive-allocation ratio.

    Core = features with top ``core_fraction`` of next-step prediction weight
    (absolute auto-regression coefficient magnitude).

    Parameters
    ----------
    window_data : np.ndarray
        Shape ``(n_nodes, n_time)`` or ``(n_time,)`` for 1-D.
    core_fraction : float
        Fraction of prediction weight considered *core*.
    delta : float
        Denominator guard.

    Returns
    -------
    float
        Predictive energy ratio.
    """
    sig = window_data[np.newaxis, :] if window_data.ndim == 1 else window_data

    n_nodes, n_time = sig.shape
    if n_time < 3:
        return 1.0  # Not enough data for prediction

    # Simple AR(1) coefficient per node as prediction weight proxy
    weights = np.zeros(n_nodes)
    for i in range(n_nodes):
        x = sig[i, :-1]
        y = sig[i, 1:]
        var_x = np.var(x)
        if var_x > 0:
            weights[i] = abs(np.mean((x - np.mean(x)) * (y - np.mean(y))) / var_x)

    # Partition by prediction weight
    n_core = max(1, int(np.ceil(n_nodes * core_fraction)))
    ranked = np.argsort(weights)[::-1]
    core_idx = ranked[:n_core]
    periphery_idx = ranked[n_core:]

    e_core = float(np.sum(sig[core_idx] ** 2))
    if len(periphery_idx) == 0:
        return e_core / delta
    e_periphery = float(np.sum(sig[periphery_idx] ** 2))
    return e_core / (e_periphery + delta)


# ── Verdict Logic ────────────────────────────────────────────────────────────
def evaluate_phi_gamma(
    ratios: np.ndarray,
    null_ratios: np.ndarray,
    phi: float = PHI,
    phi_inv: float = PHI_INV,
    p_threshold: float = 0.05,
    min_windows: int = 30,
    ci_width_max: float = 0.5,
    seed: int = 42,
) -> dict[str, Any]:
    """Evaluate the H_φγ hypothesis for one substrate/ratio-method pair.

    Returns
    -------
    dict
        Keys: ``verdict``, ``median_ratio``, ``mean_ratio``, ``bootstrap_ci``,
        ``null_median``, ``p_value``, ``n_unity_windows``.
    """
    n = len(ratios)

    # Insufficient data
    if n < min_windows:
        return {
            "verdict": "insufficient",
            "median_ratio": float(np.median(ratios)) if n > 0 else 0.0,
            "mean_ratio": float(np.mean(ratios)) if n > 0 else 0.0,
            "bootstrap_ci": [0.0, 0.0],
            "null_median": float(np.median(null_ratios)) if len(null_ratios) > 0 else 0.0,
            "p_value": 1.0,
            "n_unity_windows": n,
        }

    median_r = float(np.median(ratios))
    mean_r = float(np.mean(ratios))
    ci_low, ci_high = bootstrap_ratio_ci(ratios, seed=seed)
    ci_width = ci_high - ci_low
    null_median = float(np.median(null_ratios)) if len(null_ratios) > 0 else 0.0

    # Permutation p-value: fraction of null medians as extreme as observed
    if len(null_ratios) > 0:
        # Compare observed median to null distribution of medians
        rng = np.random.default_rng(seed)
        n_null = len(null_ratios)
        null_medians = np.empty(2000)
        for i in range(2000):
            sample = rng.choice(null_ratios, size=min(n, n_null), replace=True)
            null_medians[i] = np.median(sample)
        # Two-sided test: distance from null_median
        obs_dist = abs(median_r - null_median)
        null_dists = np.abs(null_medians - null_median)
        p_value = float((np.sum(null_dists >= obs_dist) + 1) / (len(null_medians) + 1))
    else:
        p_value = 1.0

    # CI too wide → insufficient
    if ci_width > ci_width_max:
        return {
            "verdict": "insufficient",
            "median_ratio": median_r,
            "mean_ratio": mean_r,
            "bootstrap_ci": [ci_low, ci_high],
            "null_median": null_median,
            "p_value": p_value,
            "n_unity_windows": n,
        }

    # Distance to targets
    d_phi = abs(median_r - phi)
    d_phi_inv = abs(median_r - phi_inv)
    d_null = abs(median_r - null_median)
    near_phi = min(d_phi, d_phi_inv) < d_null

    verdict = "support" if near_phi and p_value < p_threshold else "reject"

    return {
        "verdict": verdict,
        "median_ratio": median_r,
        "mean_ratio": mean_r,
        "bootstrap_ci": [ci_low, ci_high],
        "null_median": null_median,
        "p_value": p_value,
        "n_unity_windows": n,
    }


# ── Full Pipeline ────────────────────────────────────────────────────────────
def _generate_null_ratios(
    signal_data: np.ndarray,
    window_data_fn,
    ratio_fn,
    n_surrogates: int = 200,
    seed: int = 42,
) -> np.ndarray:
    """Generate null distribution ratios using all three null models."""
    rng = np.random.default_rng(seed)
    null_ratios: list[float] = []

    for i in range(n_surrogates):
        child_seed = rng.integers(0, 2**31)
        child_rng = np.random.default_rng(child_seed)

        # Temporal shuffle
        shuffled = null_temporal_shuffle(signal_data, rng=child_rng)
        null_ratios.append(ratio_fn(shuffled))

        # Phase randomization
        phase_rand = null_phase_randomization(signal_data, rng=child_rng)
        null_ratios.append(ratio_fn(phase_rand))

    return np.array(null_ratios, dtype=np.float64)


def run_phi_gamma_experiment(config: dict[str, Any]) -> dict[str, Any]:
    """Execute the full H_φγ experiment pipeline.

    Parameters
    ----------
    config : dict
        Configuration dictionary (typically loaded from phi_gamma_config.yaml).

    Returns
    -------
    dict
        JSON-serializable report matching the H_φγ schema.
    """
    phi = config.get("phi", PHI)
    phi_inv = config.get("phi_inv", PHI_INV)
    epsilon = config.get("epsilon", 0.10)
    window = config.get("window", 256)
    step = config.get("step", 32)
    core_fraction = config.get("core_fraction", 0.382)
    delta = config.get("delta", 1e-12)
    min_unity = config.get("min_unity_windows", 30)
    p_thresh = config.get("p_value_threshold", 0.05)

    # Generate synthetic substrate data for demonstration
    # In production this would load real substrate recordings
    substrates = config.get("substrates", {})
    if not substrates:
        substrates = _generate_demo_substrates(seed=42)

    all_entries: list[dict[str, Any]] = []

    for name, data in substrates.items():
        signal_1d = data["signal_1d"]  # (n_time,)
        signal_mv = data["signal_mv"]  # (n_nodes, n_time)

        # Compute gamma windows from 1-D aggregate signal
        gamma_series = compute_gamma_windows(signal_1d, window=window, step=step)
        unity_mask = select_unity_windows(gamma_series, epsilon=epsilon)
        n_windows = len(gamma_series)
        n_unity = int(unity_mask.sum())

        # --- R1: topology-energy ---
        r1_ratios = _compute_ratios_for_unity(
            signal_mv, unity_mask, window, step,
            ratio_method="R1", core_fraction=core_fraction, delta=delta,
        )
        r1_null = _generate_null_ratios_r1(
            signal_mv, unity_mask, window, step,
            core_fraction=core_fraction, delta=delta, n_surrogates=50, seed=42,
        )
        r1_eval = evaluate_phi_gamma(
            r1_ratios, r1_null, phi=phi, phi_inv=phi_inv,
            p_threshold=p_thresh, min_windows=min_unity,
        )
        all_entries.append(build_substrate_entry(
            name=name, ratio_method="R1",
            n_windows=n_windows, n_unity_windows=n_unity,
            median_ratio=r1_eval["median_ratio"], mean_ratio=r1_eval["mean_ratio"],
            bootstrap_ci=tuple(r1_eval["bootstrap_ci"]),
            null_median=r1_eval["null_median"], p_value=r1_eval["p_value"],
            verdict=r1_eval["verdict"], phi=phi, phi_inv=phi_inv,
        ))

        # --- R2: spectral-core ---
        r2_ratios = _compute_ratios_for_unity(
            signal_mv, unity_mask, window, step,
            ratio_method="R2", core_fraction=core_fraction, delta=delta,
        )
        r2_null = _generate_null_ratios_spectral(
            signal_mv, unity_mask, window, step,
            core_fraction=core_fraction, delta=delta, n_surrogates=50, seed=42,
        )
        r2_eval = evaluate_phi_gamma(
            r2_ratios, r2_null, phi=phi, phi_inv=phi_inv,
            p_threshold=p_thresh, min_windows=min_unity,
        )
        all_entries.append(build_substrate_entry(
            name=name, ratio_method="R2",
            n_windows=n_windows, n_unity_windows=n_unity,
            median_ratio=r2_eval["median_ratio"], mean_ratio=r2_eval["mean_ratio"],
            bootstrap_ci=tuple(r2_eval["bootstrap_ci"]),
            null_median=r2_eval["null_median"], p_value=r2_eval["p_value"],
            verdict=r2_eval["verdict"], phi=phi, phi_inv=phi_inv,
        ))

        # --- R3: predictive-allocation ---
        r3_ratios = _compute_ratios_for_unity(
            signal_mv, unity_mask, window, step,
            ratio_method="R3", core_fraction=core_fraction, delta=delta,
        )
        r3_null = _generate_null_ratios_predictive(
            signal_mv, unity_mask, window, step,
            core_fraction=core_fraction, delta=delta, n_surrogates=50, seed=42,
        )
        r3_eval = evaluate_phi_gamma(
            r3_ratios, r3_null, phi=phi, phi_inv=phi_inv,
            p_threshold=p_thresh, min_windows=min_unity,
        )
        all_entries.append(build_substrate_entry(
            name=name, ratio_method="R3",
            n_windows=n_windows, n_unity_windows=n_unity,
            median_ratio=r3_eval["median_ratio"], mean_ratio=r3_eval["mean_ratio"],
            bootstrap_ci=tuple(r3_eval["bootstrap_ci"]),
            null_median=r3_eval["null_median"], p_value=r3_eval["p_value"],
            verdict=r3_eval["verdict"], phi=phi, phi_inv=phi_inv,
        ))

    return build_report(
        all_entries, epsilon=epsilon, window=window, step=step,
        phi=phi, phi_inv=phi_inv,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────
def _compute_ratios_for_unity(
    signal_mv: np.ndarray,
    unity_mask: np.ndarray,
    window: int,
    step: int,
    ratio_method: str,
    core_fraction: float,
    delta: float,
) -> np.ndarray:
    """Compute ratios for unity windows using the specified method."""
    n_time = signal_mv.shape[1]
    ratios: list[float] = []
    for win_idx, start in enumerate(range(0, n_time - window + 1, step)):
        if win_idx >= len(unity_mask):
            break
        if unity_mask[win_idx]:
            chunk = signal_mv[:, start : start + window]
            if ratio_method == "R1":
                core_idx, periph_idx = build_core_periphery(
                    chunk, core_fraction=core_fraction,
                )
                r = compute_energy_ratio(chunk, core_idx, periph_idx, delta=delta)
            elif ratio_method == "R2":
                r = compute_spectral_energy_ratio(
                    chunk, core_fraction=core_fraction, delta=delta,
                )
            elif ratio_method == "R3":
                r = compute_predictive_ratio(
                    chunk, core_fraction=core_fraction, delta=delta,
                )
            else:
                raise ValueError(f"Unknown ratio method: {ratio_method}")
            ratios.append(r)
    if ratios:
        return np.array(ratios, dtype=np.float64)
    return np.array([], dtype=np.float64)


def _generate_null_ratios_r1(
    signal_mv: np.ndarray,
    unity_mask: np.ndarray,
    window: int,
    step: int,
    core_fraction: float,
    delta: float,
    n_surrogates: int = 50,
    seed: int = 42,
) -> np.ndarray:
    """Generate null ratios for R1 using topology shuffle + temporal shuffle."""
    rng = np.random.default_rng(seed)
    n_nodes, n_time = signal_mv.shape
    null_ratios: list[float] = []
    for win_idx, start in enumerate(range(0, n_time - window + 1, step)):
        if win_idx >= len(unity_mask):
            break
        if unity_mask[win_idx]:
            chunk = signal_mv[:, start : start + window]
            core_idx, periph_idx = build_core_periphery(
                chunk, core_fraction=core_fraction,
            )
            for _ in range(n_surrogates):
                # Topology shuffle null
                nc, np_ = null_topology_shuffle(
                    core_idx, periph_idx, n_nodes, rng=rng,
                )
                null_ratios.append(
                    compute_energy_ratio(chunk, nc, np_, delta=delta),
                )
    if null_ratios:
        return np.array(null_ratios, dtype=np.float64)
    return np.array([], dtype=np.float64)


def _generate_null_ratios_spectral(
    signal_mv: np.ndarray,
    unity_mask: np.ndarray,
    window: int,
    step: int,
    core_fraction: float,
    delta: float,
    n_surrogates: int = 50,
    seed: int = 42,
) -> np.ndarray:
    """Generate null ratios for R2 using phase randomization."""
    rng = np.random.default_rng(seed)
    n_time = signal_mv.shape[1]
    null_ratios: list[float] = []
    for win_idx, start in enumerate(range(0, n_time - window + 1, step)):
        if win_idx >= len(unity_mask):
            break
        if unity_mask[win_idx]:
            chunk = signal_mv[:, start : start + window]
            for _ in range(n_surrogates):
                surrogate = null_phase_randomization(chunk, rng=rng)
                null_ratios.append(compute_spectral_energy_ratio(
                    surrogate, core_fraction=core_fraction, delta=delta,
                ))
    if null_ratios:
        return np.array(null_ratios, dtype=np.float64)
    return np.array([], dtype=np.float64)


def _generate_null_ratios_predictive(
    signal_mv: np.ndarray,
    unity_mask: np.ndarray,
    window: int,
    step: int,
    core_fraction: float,
    delta: float,
    n_surrogates: int = 50,
    seed: int = 42,
) -> np.ndarray:
    """Generate null ratios for R3 using temporal shuffle."""
    rng = np.random.default_rng(seed)
    n_time = signal_mv.shape[1]
    null_ratios: list[float] = []
    for win_idx, start in enumerate(range(0, n_time - window + 1, step)):
        if win_idx >= len(unity_mask):
            break
        if unity_mask[win_idx]:
            chunk = signal_mv[:, start : start + window]
            for _ in range(n_surrogates):
                surrogate = null_temporal_shuffle(chunk, rng=rng)
                null_ratios.append(compute_predictive_ratio(
                    surrogate, core_fraction=core_fraction, delta=delta,
                ))
    if null_ratios:
        return np.array(null_ratios, dtype=np.float64)
    return np.array([], dtype=np.float64)


def _generate_demo_substrates(seed: int = 42) -> dict[str, dict[str, np.ndarray]]:
    """Generate synthetic demo substrates for pipeline testing."""
    rng = np.random.default_rng(seed)
    n_nodes = 20
    n_time = 4096
    substrates: dict[str, dict[str, np.ndarray]] = {}

    for name in ["demo_substrate_A", "demo_substrate_B"]:
        # Generate correlated multivariate signal
        base = rng.standard_normal(n_time)
        signal_mv = np.empty((n_nodes, n_time))
        for i in range(n_nodes):
            mix = 0.5 + 0.5 * rng.random()
            signal_mv[i] = mix * base + (1 - mix) * rng.standard_normal(n_time)
        signal_1d = signal_mv.mean(axis=0)
        substrates[name] = {"signal_1d": signal_1d, "signal_mv": signal_mv}

    return substrates


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    """Command-line entry point for the H_φγ experiment."""
    parser = argparse.ArgumentParser(description="H_φγ Invariant Experiment")
    parser.add_argument(
        "--config", type=str, required=True,
        help="Path to phi_gamma_config.yaml",
    )
    parser.add_argument(
        "--out", type=str, required=True,
        help="Output path for JSON report",
    )
    args = parser.parse_args()

    # Load YAML config
    try:
        import yaml
        with open(args.config) as f:
            config = yaml.safe_load(f)
    except ImportError:
        # Fallback: parse simple YAML manually
        config = _parse_simple_yaml(args.config)

    report = run_phi_gamma_experiment(config)
    save_report(report, args.out)
    print(f"Report saved to {args.out}")
    print(json.dumps(report, indent=2))


def _parse_simple_yaml(path: str) -> dict[str, Any]:
    """Minimal YAML parser for flat key-value configs (no dependency on PyYAML)."""
    config: dict[str, Any] = {}
    with open(path) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                # List of values
                items = val[1:-1].split(",")
                config[key] = [_cast_value(v.strip()) for v in items]
            elif val.startswith('"') and val.endswith('"'):
                config[key] = val[1:-1]
            else:
                config[key] = _cast_value(val)
    return config


def _cast_value(val: str) -> int | float | str:
    """Try to cast a string to int, float, or leave as str."""
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


if __name__ == "__main__":
    main()
