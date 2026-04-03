"""Power analysis for gamma detection at small sample sizes.

Addresses Hole 8: zebrafish n=47 and neosynaptex_cross n=40 are small.

Uses fast OLS approximation for Monte Carlo (Theil-Sen too slow for 1000s of runs).
Final gamma values in proof bundle use Theil-Sen; this script estimates power bounds.

Usage:
    python scripts/power_analysis.py

Output:
    evidence/power_analysis.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _fast_gamma(log_t: np.ndarray, log_c: np.ndarray) -> tuple[float, float]:
    """Fast gamma via OLS (for power simulation speed)."""
    x_mean = np.mean(log_t)
    y_mean = np.mean(log_c)
    ss_xy = np.sum((log_t - x_mean) * (log_c - y_mean))
    ss_xx = np.sum((log_t - x_mean) ** 2)
    if ss_xx < 1e-12:
        return float("nan"), float("nan")
    slope = ss_xy / ss_xx
    gamma = -slope
    yhat = slope * log_t + (y_mean - slope * x_mean)
    ss_res = np.sum((log_c - yhat) ** 2)
    ss_tot = np.sum((log_c - y_mean) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0
    return gamma, r2


def _fast_bootstrap_ci(log_t: np.ndarray, log_c: np.ndarray, rng, n_boot: int = 100):
    """Fast bootstrap CI using OLS."""
    n = len(log_t)
    gammas = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        g, _ = _fast_gamma(log_t[idx], log_c[idx])
        gammas[i] = g
    return float(np.percentile(gammas, 2.5)), float(np.percentile(gammas, 97.5))


def power_analysis(
    true_gamma: float,
    n: int,
    r2_target: float,
    n_simulations: int = 500,
    seed: int = 42,
) -> dict:
    """Monte Carlo power analysis at given n and noise level."""
    rng = np.random.default_rng(seed)
    noise_scale = np.sqrt(max(0.01, (1 - r2_target) / max(r2_target, 0.01)))

    ci_contains_unity = 0
    gammas = []
    ci_widths = []

    log_topo = np.log(np.linspace(1.0, 10.0, n))

    for i in range(n_simulations):
        noise = noise_scale * rng.standard_normal(n)
        log_cost = np.log(10.0) - true_gamma * log_topo + noise

        gamma, r2 = _fast_gamma(log_topo, log_cost)
        if not np.isfinite(gamma) or r2 < 0.3:
            continue

        ci_lo, ci_hi = _fast_bootstrap_ci(log_topo, log_cost, rng, n_boot=100)
        gammas.append(gamma)
        ci_widths.append(ci_hi - ci_lo)
        if ci_lo <= 1.0 <= ci_hi:
            ci_contains_unity += 1

    n_valid = len(gammas)
    if n_valid == 0:
        return {"n": n, "true_gamma": true_gamma, "r2_target": r2_target, "n_valid": 0}

    return {
        "n": n,
        "true_gamma": true_gamma,
        "r2_target": r2_target,
        "n_valid": n_valid,
        "n_simulations": n_simulations,
        "mean_gamma": round(float(np.mean(gammas)), 4),
        "std_gamma": round(float(np.std(gammas)), 4),
        "mean_ci_width": round(float(np.mean(ci_widths)), 4),
        "p_ci_contains_unity": round(ci_contains_unity / n_valid, 4),
        "bias": round(float(np.mean(gammas)) - true_gamma, 4),
    }


def minimum_detectable_effect(n: int, r2_target: float, power_target: float = 0.80) -> float:
    """Find minimum |gamma - 1.0| detectable at given power."""
    for delta in np.arange(0.05, 2.0, 0.05):
        result = power_analysis(1.0 + delta, n, r2_target, n_simulations=200)
        if result.get("n_valid", 0) == 0:
            continue
        detection_rate = 1.0 - result["p_ci_contains_unity"]
        if detection_rate >= power_target:
            return round(delta, 2)
    return float("nan")


def main():
    results = {}
    configs = [
        {"label": "zebrafish", "n": 47, "r2": 0.82},
        {"label": "neosynaptex_cross", "n": 40, "r2": 0.85},
        {"label": "bnsyn", "n": 200, "r2": 0.71},
        {"label": "kuramoto", "n": 120, "r2": 0.61},
        {"label": "mfn", "n": 200, "r2": 0.47},  # capped n for speed
    ]

    for cfg in configs:
        label = cfg["label"]
        print(f"  Power analysis: {label} (n={cfg['n']}, R2={cfg['r2']})...")
        true_1 = power_analysis(1.0, cfg["n"], cfg["r2"], n_simulations=500)
        false_pos = power_analysis(0.5, cfg["n"], cfg["r2"], n_simulations=500)
        mde = minimum_detectable_effect(cfg["n"], cfg["r2"])

        results[label] = {
            "n": cfg["n"],
            "r2_target": cfg["r2"],
            "sensitivity_at_gamma_1": true_1,
            "false_positive_at_gamma_05": false_pos,
            "minimum_detectable_effect": mde,
        }

    output = {
        "version": "1.0.0",
        "date": "2026-04-03",
        "description": "Power analysis for gamma detection at observed sample sizes",
        "method": "Monte Carlo simulation with OLS gamma estimation and bootstrap CI (n_boot=100)",
        "note": "OLS used for speed; canonical pipeline uses Theil-Sen. "
        "Power estimates are approximate.",
        "substrates": results,
    }

    out_path = Path(__file__).resolve().parent.parent / "evidence" / "power_analysis.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n")
    print(f"\nWritten to {out_path}")

    print("\n=== POWER ANALYSIS SUMMARY ===")
    for label, r in results.items():
        s = r["sensitivity_at_gamma_1"]
        fp = r["false_positive_at_gamma_05"]
        print(
            f"  {label}: n={r['n']}, "
            f"CI_width={s.get('mean_ci_width', '?')}, "
            f"P(CI contains 1|gamma=1)={s.get('p_ci_contains_unity', '?')}, "
            f"P(CI contains 1|gamma=0.5)={fp.get('p_ci_contains_unity', '?')}, "
            f"MDE={r['minimum_detectable_effect']}"
        )


if __name__ == "__main__":
    main()
