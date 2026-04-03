#!/usr/bin/env python3
"""
Alternative model comparison for Tier 1 substrates.
Compares power-law scaling K=A*C^(-γ) against lognormal and exponential
fits in log-log space using AIC/BIC.

Output: evidence/alternative_model_tests.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SEED = 42
EVIDENCE_DIR = ROOT / "evidence"


def log_likelihood_linear(log_c: np.ndarray, log_k: np.ndarray):
    """Linear model in log-log space: log_k = a + b*log_c (power law)."""
    n = len(log_c)
    slope, intercept, _, _, _ = stats.linregress(log_c, log_k)
    residuals = log_k - (intercept + slope * log_c)
    sigma2 = np.sum(residuals**2) / n
    ll = -n / 2 * (np.log(2 * np.pi * sigma2) + 1)
    return ll, 2  # 2 parameters: slope, intercept


def log_likelihood_quadratic(log_c: np.ndarray, log_k: np.ndarray):
    """Quadratic in log-log space (lognormal-like curvature)."""
    n = len(log_c)
    coeffs = np.polyfit(log_c, log_k, 2)
    pred = np.polyval(coeffs, log_c)
    residuals = log_k - pred
    sigma2 = np.sum(residuals**2) / n
    ll = -n / 2 * (np.log(2 * np.pi * sigma2) + 1)
    return ll, 3  # 3 parameters: a, b, c


def log_likelihood_exponential(log_c: np.ndarray, log_k: np.ndarray):
    """Exponential decay in C-space: K = A*exp(-λC), fit in log space.
    log_k = log(A) - λ*C = log(A) - λ*exp(log_c)."""
    n = len(log_c)
    C = np.exp(log_c)

    def neg_ll(lam):
        pred = np.mean(log_k) + lam * (np.mean(C) - C)
        resid = log_k - pred
        s2 = np.sum(resid**2) / n
        if s2 <= 0:
            return 1e12
        return n / 2 * (np.log(2 * np.pi * s2) + 1)

    res = minimize_scalar(neg_ll, bounds=(1e-6, 100), method="bounded")
    lam = res.x
    pred = np.mean(log_k) + lam * (np.mean(C) - C)
    residuals = log_k - pred
    sigma2 = np.sum(residuals**2) / n
    ll = -n / 2 * (np.log(2 * np.pi * sigma2) + 1)
    return ll, 2  # 2 parameters: A, λ


def compute_aic_bic(ll: float, k: int, n: int):
    aic = 2 * k - 2 * ll
    bic = k * np.log(n) - 2 * ll
    return aic, bic


def test_substrate(name: str, topo: np.ndarray, cost: np.ndarray) -> dict:
    """Run model comparison for one substrate."""
    mask = np.isfinite(topo) & np.isfinite(cost) & (topo > 0) & (cost > 0)
    t, c = topo[mask], cost[mask]
    log_c = np.log(t)
    log_k = np.log(c)
    n = len(log_c)

    ll_pw, k_pw = log_likelihood_linear(log_c, log_k)
    ll_ln, k_ln = log_likelihood_quadratic(log_c, log_k)
    ll_ex, k_ex = log_likelihood_exponential(log_c, log_k)

    aic_pw, bic_pw = compute_aic_bic(ll_pw, k_pw, n)
    aic_ln, bic_ln = compute_aic_bic(ll_ln, k_ln, n)
    aic_ex, bic_ex = compute_aic_bic(ll_ex, k_ex, n)

    # Log-space range
    c_range = [round(float(np.min(log_c)), 3), round(float(np.max(log_c)), 3)]

    return {
        "substrate": name,
        "n_pairs": int(n),
        "log_C_range": c_range,
        "log_C_span": round(float(np.ptp(log_c)), 3),
        "models": {
            "power_law": {
                "description": "K = A * C^(-gamma), linear in log-log",
                "log_likelihood": round(ll_pw, 2),
                "n_params": k_pw,
                "AIC": round(aic_pw, 2),
                "BIC": round(bic_pw, 2),
            },
            "lognormal_curvature": {
                "description": "Quadratic in log-log (lognormal-like)",
                "log_likelihood": round(ll_ln, 2),
                "n_params": k_ln,
                "AIC": round(aic_ln, 2),
                "BIC": round(bic_ln, 2),
            },
            "exponential_decay": {
                "description": "K = A * exp(-lambda*C)",
                "log_likelihood": round(ll_ex, 2),
                "n_params": k_ex,
                "AIC": round(aic_ex, 2),
                "BIC": round(bic_ex, 2),
            },
        },
        "delta_AIC_vs_power_law": {
            "lognormal": round(aic_ln - aic_pw, 2),
            "exponential": round(aic_ex - aic_pw, 2),
        },
        "delta_BIC_vs_power_law": {
            "lognormal": round(bic_ln - bic_pw, 2),
            "exponential": round(bic_ex - bic_pw, 2),
        },
        "preferred_model": "power_law"
        if aic_pw <= min(aic_ln, aic_ex)
        else ("lognormal_curvature" if aic_ln < aic_ex else "exponential_decay"),
    }


def main():
    results = {"description": "Alternative model tests (AIC/BIC) for Tier 1 substrates", "substrates": {}}

    # --- Zebrafish ---
    print("  Zebrafish...", flush=True)
    from substrates.zebrafish.adapter import ZebrafishAdapter

    za = ZebrafishAdapter(phenotype="WT", seed=SEED)
    za._ensure_loaded()
    mask = (
        np.isfinite(za._densities)
        & np.isfinite(za._nn_cvs)
        & (za._densities > 0)
        & (za._nn_cvs > 0)
    )
    res_z = test_substrate("zebrafish", za._densities[mask], za._nn_cvs[mask])
    results["substrates"]["zebrafish"] = res_z
    print(f"    AIC power-law={res_z['models']['power_law']['AIC']}, "
          f"ΔAIC lognormal={res_z['delta_AIC_vs_power_law']['lognormal']}, "
          f"ΔAIC exponential={res_z['delta_AIC_vs_power_law']['exponential']}")

    # --- HRV PhysioNet (grand-average PSD) ---
    print("  HRV PhysioNet...", flush=True)
    from substrates.hrv_physionet.adapter import HRVPhysioNetAdapter

    hrv = HRVPhysioNetAdapter(n_subjects=10)
    freqs, psd = hrv.get_all_pairs()
    # Filter to VLF range used in gamma computation
    mask_f = (freqs >= 0.003) & (freqs <= 0.04) & (freqs > 0) & (psd > 0)
    res_h = test_substrate("hrv_physionet", freqs[mask_f], psd[mask_f])
    results["substrates"]["hrv_physionet"] = res_h
    print(f"    AIC power-law={res_h['models']['power_law']['AIC']}, "
          f"ΔAIC lognormal={res_h['delta_AIC_vs_power_law']['lognormal']}, "
          f"ΔAIC exponential={res_h['delta_AIC_vs_power_law']['exponential']}")

    # --- EEG PhysioNet (grand-average PSD) ---
    print("  EEG PhysioNet...", flush=True)
    from substrates.eeg_physionet.adapter import EEGPhysioNetAdapter

    eeg = EEGPhysioNetAdapter(n_subjects=20)
    freqs_e, psd_e = eeg.get_grand_average_psd()
    mask_e = (freqs_e >= 2.0) & (freqs_e <= 35.0) & (freqs_e > 0) & (psd_e > 0)
    res_e = test_substrate("eeg_physionet", freqs_e[mask_e], psd_e[mask_e])
    results["substrates"]["eeg_physionet"] = res_e
    print(f"    AIC power-law={res_e['models']['power_law']['AIC']}, "
          f"ΔAIC lognormal={res_e['delta_AIC_vs_power_law']['lognormal']}, "
          f"ΔAIC exponential={res_e['delta_AIC_vs_power_law']['exponential']}")

    # Save
    out = EVIDENCE_DIR / "alternative_model_tests.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {out}")

    return results


if __name__ == "__main__":
    main()
