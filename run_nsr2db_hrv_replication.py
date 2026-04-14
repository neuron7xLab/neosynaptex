#!/usr/bin/env python3
"""PhysioNet NSR2DB HRV γ-replication — minimal pilot.

Final-fallback configuration:
* 1 subject (nsr001)
* RR truncated to first 20000 beats (~4h)
* 50 surrogates per null family
* IAAFT 10 iterations (was 50)

Tight enough to complete in <2 minutes. Honest scope: n=1 subject
is a PILOT, not statistically powered. Per CLAIM_BOUNDARY.md §3.1
the result is exploratory and capped at hypothesized.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import math
import pathlib
import sys

import numpy as np
from scipy import signal
from scipy.stats import theilslopes

from substrates.physionet_hrv.hrv_gamma_fit import rr_to_uniform_4hz
from substrates.physionet_hrv.nsr2db_client import fetch_rr_intervals

logger = logging.getLogger(__name__)


def _shuffled(x, seed):
    return np.random.default_rng(seed).permutation(x)


def _ar1(x, seed):
    xc = x - np.mean(x)
    num = float(np.dot(xc[:-1], xc[1:]))
    den = float(np.dot(xc[:-1], xc[:-1]))
    phi = max(min(num / den if den > 0 else 0.0, 0.99), -0.99)
    resid = xc[1:] - phi * xc[:-1]
    sigma = float(np.std(resid))
    rng = np.random.default_rng(seed)
    y = np.zeros(len(x))
    y[0] = rng.normal(0, sigma / math.sqrt(max(1 - phi * phi, 1e-6)))
    for i in range(1, len(y)):
        y[i] = phi * y[i - 1] + rng.normal(0, sigma)
    return y + float(np.mean(x))


def _iaaft(x, seed, n_iter=10):
    rng = np.random.default_rng(seed)
    x_sorted = np.sort(x)
    x_mag = np.abs(np.fft.rfft(x))
    y = rng.permutation(x)
    for _ in range(n_iter):
        y_phase = np.angle(np.fft.rfft(y))
        y_spec = np.fft.irfft(x_mag * np.exp(1j * y_phase), n=len(x))
        ranks = np.argsort(np.argsort(y_spec))
        y = x_sorted[ranks]
    return y


def _fit_uniform(rr_uniform, fs=4.0, lo=0.003, hi=0.04, nperseg=1024):
    nperseg = min(nperseg, len(rr_uniform))
    f, p = signal.welch(rr_uniform, fs=fs, nperseg=nperseg, detrend="constant")
    mask = (f >= lo) & (f <= hi) & (p > 0)
    f_fit = f[mask]
    p_fit = p[mask]
    if len(f_fit) < 5:
        raise ValueError(f"too few VLF bins: {len(f_fit)}")
    log_f = np.log(f_fit)
    log_p = np.log(p_fit)
    slope, intercept, lo_s, hi_s = theilslopes(log_p, log_f)
    yhat = slope * log_f + intercept
    ss_r = float(np.sum((log_p - yhat) ** 2))
    ss_t = float(np.sum((log_p - log_p.mean()) ** 2))
    r2 = 1.0 - ss_r / ss_t if ss_t > 1e-12 else 0.0
    return float(-slope), float(-hi_s), float(-lo_s), float(r2), len(f_fit)


def main():
    out_dir = pathlib.Path("evidence/replications/physionet_nsr2db")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run.log"
    logging.basicConfig(
        level="INFO",
        format="[%(asctime)s] %(message)s",
        handlers=[logging.FileHandler(log_path, mode="w"), logging.StreamHandler(sys.stdout)],
    )

    record = "nsr001"
    n_surrogates = 50
    rr_truncate = 20000
    seed = 42

    logger.info("=== fetch %s ===", record)
    r = fetch_rr_intervals(record)
    logger.info("  raw n_rr=%d mean=%.3fs std=%.3fs", r.n_rr_intervals, r.mean_rr_s, r.std_rr_s)

    rr = r.rr_seconds[:rr_truncate]
    logger.info("  truncated to %d RR (~%.1fh)", len(rr), float(rr.sum() / 3600))

    rr_uniform = rr_to_uniform_4hz(rr)
    logger.info("  uniform 4Hz: n=%d", len(rr_uniform))

    g, ci_lo, ci_hi, r2, nfreq = _fit_uniform(rr_uniform)
    logger.info("  REAL: γ=%.4f CI=[%.4f,%.4f] r²=%.4f nfreq=%d", g, ci_lo, ci_hi, r2, nfreq)

    nulls = []
    gens = {"shuffled": _shuffled, "ar1": _ar1, "iaaft": _iaaft}
    for fam, gen in gens.items():
        logger.info("  null %s: running %d surrogates...", fam, n_surrogates)
        gammas = []
        for i in range(n_surrogates):
            try:
                surr = gen(rr_uniform, seed + i)
                sg, _, _, _, _ = _fit_uniform(surr)
                gammas.append(sg)
            except Exception:
                continue
        if len(gammas) < 10:
            logger.warning("  null %s: only %d valid", fam, len(gammas))
            nulls.append({"family": fam, "n": len(gammas), "error": "too few valid"})
            continue
        arr = np.array(gammas)
        mu = float(arr.mean())
        sigma = float(arr.std(ddof=1))
        z = (g - mu) / sigma if sigma > 1e-10 else 0.0
        ci_l = float(np.percentile(arr, 2.5))
        ci_h = float(np.percentile(arr, 97.5))
        outside = not (ci_l <= g <= ci_h)
        sep = abs(z) >= 3.0 and outside
        logger.info("    μ=%.4f σ=%.4f z=%.3f sep=%s", mu, sigma, z, sep)
        nulls.append(
            {
                "family": fam,
                "n_surrogates": len(gammas),
                "mu": round(mu, 4),
                "sigma": round(sigma, 4),
                "z_score": round(z, 3),
                "null_ci_low": round(ci_l, 4),
                "null_ci_high": round(ci_h, 4),
                "real_outside_null_ci": outside,
                "separable_at_z3": sep,
            }
        )

    n_sep = sum(1 for n in nulls if n.get("separable_at_z3", False))
    n_total = sum(1 for n in nulls if "n_surrogates" in n)

    result = {
        "substrate": "physionet_hrv_nsr2db",
        "record": record,
        "claim_status": "hypothesized",
        "verdict": (
            "separable_from_all_nulls"
            if n_sep == n_total
            else f"separable_from_{n_sep}_of_{n_total}_nulls"
        ),
        "gamma": {
            "value": round(g, 4),
            "ci_low": round(ci_lo, 4),
            "ci_high": round(ci_hi, 4),
            "r2": round(r2, 4),
            "n_frequencies_fit": nfreq,
            "fit_band_hz": [0.003, 0.04],
            "method": "welch_psd_theilsen_vlf",
        },
        "nulls": nulls,
        "provenance": r.as_provenance_dict()
        | {
            "rr_truncated_to": rr_truncate,
            "rr_truncated_duration_hours": round(float(rr.sum() / 3600), 2),
            "n_uniform_samples": int(len(rr_uniform)),
        },
        "config": {
            "n_surrogates_per_null": n_surrogates,
            "iaaft_iter": 10,
            "fs_uniform_hz": 4.0,
            "nperseg": 1024,
        },
        "method_hierarchy_cite": "docs/MEASUREMENT_METHOD_HIERARCHY.md §2.3 (bounded secondary)",
        "null_hierarchy_cite": "docs/NULL_MODEL_HIERARCHY.md §2.1–2.3",
        "interpretation_boundary": (
            "PILOT n=1 subject from PhysioNet NSR2DB. RR truncated to "
            "20000 beats (~4h) for compute tractability. Measures VLF "
            "(0.003-0.04 Hz) aperiodic slope on uniform-4Hz-interpolated "
            "RR. Does NOT license claims about cardiac criticality, "
            "pathological rhythms, or cross-substrate γ. Single subject "
            "is INSUFFICIENT statistical power; multi-subject + full-record "
            "run is the next step. Per docs/CLAIM_BOUNDARY.md §3.1."
        ),
        "claim_boundary_pointer": "docs/CLAIM_BOUNDARY.md",
        "fetched_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    out_path = out_dir / "result.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info("wrote %s", out_path)

    print()
    print("=" * 60)
    print(f"PhysioNet NSR2DB HRV γ-replication — {record} pilot")
    print("=" * 60)
    print(f"γ = {g:.4f}  CI95 = [{ci_lo:.4f}, {ci_hi:.4f}]  r² = {r2:.4f}")
    print(f"VLF band: 0.003-0.04 Hz, {nfreq} frequency bins")
    for n in nulls:
        if "n_surrogates" in n:
            print(
                f"  {n['family']}: μ={n['mu']:.4f} σ={n['sigma']:.4f} "
                f"z={n['z_score']:.3f} sep={n['separable_at_z3']}"
            )
        else:
            print(f"  {n['family']}: ERROR ({n.get('error', '?')})")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
