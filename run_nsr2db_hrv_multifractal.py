#!/usr/bin/env python3
"""HRV MFDFA + beat-interval null on 5 NSR2DB subjects.

Closes two methodology gaps left open by the n=1 pilot
(``run_nsr2db_hrv_replication.py``):

1. **MFDFA (Δh)** — multifractal width per subject. Narrow Δh
   means simple stable scaling regime; wide Δh means rich
   multi-regime dynamics. Determines whether the γ ≈ 1.09 we
   observed is a single-exponent (monofractal) signature or
   captures multiple co-existing scaling regimes.

2. **Beat-interval null** — shuffles the RR sequence ITSELF
   (before uniform resampling), then re-interpolates and refits.
   Destroys beat-to-beat dependencies but preserves the marginal
   distribution of RR intervals. Closes the IAAFT gap from the
   pilot: IAAFT preserves linear spectrum so γ matches by
   construction; beat-interval null does NOT preserve spectrum,
   so passing or failing it is informative about whether γ
   requires temporally-ordered beat-to-beat structure.

Per owner's prioritisation:
  MFDFA → beat-interval → contrast (later) → scale (later)
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import pathlib
import sys

import numpy as np
from scipy import signal
from scipy.stats import theilslopes

from substrates.physionet_hrv.hrv_gamma_fit import rr_to_uniform_4hz
from substrates.physionet_hrv.mfdfa import mfdfa
from substrates.physionet_hrv.nsr2db_client import fetch_rr_intervals

logger = logging.getLogger(__name__)


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


def beat_interval_null(rr_seconds: np.ndarray, seed: int) -> np.ndarray:
    """Shuffle RR sequence itself; preserve marginal, destroy beat-order.

    Returns the uniform-4Hz-resampled signal of the shuffled RR.
    Different from `_shuffled` on the uniform signal: this one
    operates on the BEAT level before interpolation, so it
    destroys any beat-to-beat memory without preserving the
    linear power spectrum (because the cumulative beat-time grid
    changes).
    """

    rng = np.random.default_rng(seed)
    rr_perm = rng.permutation(rr_seconds)
    return rr_to_uniform_4hz(rr_perm)


def per_subject_run(record_name: str, *, n_surrogates: int, rr_truncate: int, seed: int) -> dict:
    logger.info("=== %s ===", record_name)
    try:
        r = fetch_rr_intervals(record_name)
    except Exception as exc:
        logger.warning("fetch failed: %s", exc)
        return {"record": record_name, "error": f"fetch: {exc}"}
    logger.info("  raw n_rr=%d mean=%.3fs", r.n_rr_intervals, r.mean_rr_s)

    rr = r.rr_seconds[:rr_truncate]
    rr_uniform = rr_to_uniform_4hz(rr)
    logger.info("  truncated n_rr=%d → uniform n=%d", len(rr), len(rr_uniform))

    # γ-fit
    g, ci_lo, ci_hi, r2, nfreq = _fit_uniform(rr_uniform)
    logger.info("  γ=%.4f CI=[%.4f,%.4f] r²=%.3f", g, ci_lo, ci_hi, r2)

    # MFDFA on RR sequence (NOT uniform; classical HRV practice)
    try:
        m = mfdfa(rr, q_values=np.arange(-3.0, 3.5, 0.5), s_min=16, s_max=len(rr) // 4)
        logger.info(
            "  MFDFA: Δh=%.4f h(q=2)=%.4f n_samples=%d",
            m.delta_h,
            m.h_at_q2,
            m.n_samples,
        )
        mfdfa_summary = {
            "delta_h": m.delta_h,
            "delta_alpha": m.delta_alpha,
            "h_at_q2": m.h_at_q2,
            "h_at_q_neg3": float(m.hq[0]),
            "h_at_q_pos3": float(m.hq[-1]),
            "n_q_values": int(len(m.q_values)),
            "n_scales": int(len(m.scales)),
            "fit_order": m.fit_order,
        }
    except Exception as exc:
        logger.warning("  MFDFA failed: %s", exc)
        mfdfa_summary = {"error": str(exc)}

    # Beat-interval null
    logger.info("  beat_interval null: %d surrogates...", n_surrogates)
    surrogate_gammas = []
    for i in range(n_surrogates):
        try:
            surr_uniform = beat_interval_null(rr, seed + i)
            sg, _, _, _, _ = _fit_uniform(surr_uniform)
            surrogate_gammas.append(sg)
        except Exception:
            continue
    if len(surrogate_gammas) < 5:
        beat_null = {"family": "beat_interval", "error": "too few valid surrogates"}
        logger.warning("  beat_interval: only %d valid", len(surrogate_gammas))
    else:
        arr = np.array(surrogate_gammas)
        mu = float(arr.mean())
        sigma = float(arr.std(ddof=1))
        z = (g - mu) / sigma if sigma > 1e-10 else 0.0
        ci_l = float(np.percentile(arr, 2.5))
        ci_h = float(np.percentile(arr, 97.5))
        outside = not (ci_l <= g <= ci_h)
        sep = abs(z) >= 3.0 and outside
        logger.info("    μ=%.4f σ=%.4f z=%.3f sep=%s", mu, sigma, z, sep)
        beat_null = {
            "family": "beat_interval",
            "n_surrogates": len(surrogate_gammas),
            "mu": round(mu, 4),
            "sigma": round(sigma, 4),
            "z_score": round(z, 3),
            "null_ci_low": round(ci_l, 4),
            "null_ci_high": round(ci_h, 4),
            "real_outside_null_ci": outside,
            "separable_at_z3": sep,
        }

    return {
        "record": record_name,
        "provenance": r.as_provenance_dict()
        | {
            "rr_truncated_to": rr_truncate,
            "rr_truncated_duration_hours": round(float(rr.sum() / 3600), 2),
        },
        "gamma": {
            "value": round(g, 4),
            "ci_low": round(ci_lo, 4),
            "ci_high": round(ci_hi, 4),
            "r2": round(r2, 4),
            "n_frequencies_fit": nfreq,
        },
        "mfdfa": mfdfa_summary,
        "beat_interval_null": beat_null,
    }


def main():
    out_dir = pathlib.Path("evidence/replications/physionet_nsr2db_multifractal")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run.log"
    logging.basicConfig(
        level="INFO",
        format="[%(asctime)s] %(message)s",
        handlers=[logging.FileHandler(log_path, mode="w"), logging.StreamHandler(sys.stdout)],
    )

    records = ["nsr001", "nsr002", "nsr003", "nsr004", "nsr005"]
    n_surrogates = 30  # reduced — beat-interval is per-subject expensive
    rr_truncate = 20000
    seed = 42

    logger.info(
        "MFDFA + beat-interval pilot: %d records × %d surrogates each",
        len(records),
        n_surrogates,
    )

    runs = [
        per_subject_run(rec, n_surrogates=n_surrogates, rr_truncate=rr_truncate, seed=seed)
        for rec in records
    ]
    valid = [r for r in runs if "gamma" in r]
    n_ok = len(valid)
    if n_ok == 0:
        logger.error("no valid subjects")
        return 2

    gammas = np.array([v["gamma"]["value"] for v in valid])
    r2s = np.array([v["gamma"]["r2"] for v in valid])
    delta_hs = np.array([v["mfdfa"]["delta_h"] for v in valid if "delta_h" in v["mfdfa"]])
    h_q2s = np.array([v["mfdfa"]["h_at_q2"] for v in valid if "h_at_q2" in v["mfdfa"]])
    beat_sep = sum(1 for v in valid if v["beat_interval_null"].get("separable_at_z3", False))

    aggregate = {
        "substrate": "physionet_hrv_nsr2db_multifractal",
        "claim_status": "hypothesized",
        "n_subjects_ok": n_ok,
        "gamma": {
            "mean": round(float(gammas.mean()), 4),
            "std": round(float(gammas.std(ddof=1)) if n_ok > 1 else 0.0, 4),
            "min": round(float(gammas.min()), 4),
            "max": round(float(gammas.max()), 4),
        },
        "r2_mean": round(float(r2s.mean()), 4),
        "mfdfa_delta_h": {
            "n_subjects": int(len(delta_hs)),
            "mean": round(float(delta_hs.mean()), 4) if len(delta_hs) else None,
            "std": round(float(delta_hs.std(ddof=1)), 4) if len(delta_hs) > 1 else None,
            "min": round(float(delta_hs.min()), 4) if len(delta_hs) else None,
            "max": round(float(delta_hs.max()), 4) if len(delta_hs) else None,
        },
        "mfdfa_h_at_q2": {
            "n_subjects": int(len(h_q2s)),
            "mean": round(float(h_q2s.mean()), 4) if len(h_q2s) else None,
            "std": round(float(h_q2s.std(ddof=1)), 4) if len(h_q2s) > 1 else None,
        },
        "beat_interval_null": {
            "n_subjects_separable_z3": beat_sep,
            "n_subjects_total": n_ok,
        },
        "per_subject": runs,
        "config": {
            "n_surrogates_beat_null": n_surrogates,
            "rr_truncate": rr_truncate,
            "seed": seed,
            "mfdfa_q_range": [-3.0, 3.0],
            "mfdfa_q_step": 0.5,
            "mfdfa_fit_order": 1,
        },
        "interpretation_boundary": (
            "5-subject pilot. MFDFA Δh quantifies multifractality; "
            "narrow Δh = monofractal stable regime, wide Δh = rich "
            "multi-regime dynamics. Beat-interval null shuffles RR "
            "sequence itself (preserves marginal, destroys beat-order, "
            "does NOT preserve linear spectrum — closes the IAAFT gap). "
            "Does NOT license claims about pathological dynamics, "
            "exercise/stress regimes, or universal cross-substrate γ. "
            "Per docs/CLAIM_BOUNDARY.md §3.1."
        ),
        "fetched_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    out_path = out_dir / "result.json"
    out_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    logger.info("wrote %s", out_path)

    print()
    print("=" * 64)
    print(f"NSR2DB multifractal pilot — {n_ok} subjects")
    print("=" * 64)
    print(
        f"γ:  mean={gammas.mean():.4f} std={gammas.std(ddof=1) if n_ok > 1 else 0:.4f}  "
        f"min={gammas.min():.4f} max={gammas.max():.4f}"
    )
    print(f"r²: mean={r2s.mean():.4f}")
    if len(delta_hs):
        print(
            f"Δh (multifractal width):  mean={delta_hs.mean():.4f} std="
            f"{delta_hs.std(ddof=1) if len(delta_hs) > 1 else 0:.4f}"
        )
        print("  → narrow Δh ≈ monofractal stable; wide Δh ≈ rich multi-regime")
    if len(h_q2s):
        print(
            f"h(q=2) classical Hurst:   mean={h_q2s.mean():.4f} std="
            f"{h_q2s.std(ddof=1) if len(h_q2s) > 1 else 0:.4f}"
        )
    print(f"beat_interval null: {beat_sep}/{n_ok} subjects separable at |z|≥3")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
