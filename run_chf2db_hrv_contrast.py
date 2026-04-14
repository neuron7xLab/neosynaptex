#!/usr/bin/env python3
"""HRV pathology contrast: CHF2DB (heart failure) vs NSR2DB (healthy).

Per owner's prioritisation step 3: 'без контрасту γ = 1.085 — просто
число. Якщо γ зсувається передбачувано — marker працює'.

Runs the same MFDFA + γ-fit + beat-interval-null pipeline on 5 CHF
subjects from PhysioNet chf2db. Compares the (h(q=2), Δh) cluster
against the n=5 NSR2DB result already in
``evidence/replications/physionet_nsr2db_multifractal/result.json``.

Hypothesis under test:
  Healthy and pathological cardiac substrates produce
  DIFFERENT (h(q=2), Δh) clusters.
  - If yes → 2D fingerprint is a working regime marker.
  - If no  → fingerprint is not pathology-discriminative;
             cardiac substrate's evidential candidacy narrows further.

This is the FIRST contrast experiment in the γ-program.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import pathlib
import sys

import numpy as np

import run_nsr2db_hrv_multifractal as _mf_runner
from run_nsr2db_hrv_multifractal import per_subject_run
from substrates.physionet_hrv.chf2db_client import fetch_rr_intervals as _chf_fetch

logger = logging.getLogger(__name__)


def main():
    out_dir = pathlib.Path("evidence/replications/physionet_chf2db_contrast")
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "run.log"
    logging.basicConfig(
        level="INFO",
        format="[%(asctime)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Monkey-patch the per_subject_run's fetcher to point at chf2db.
    # per_subject_run uses its OWN imported binding, so patch it
    # at the per_subject_run module's namespace.
    original_fetch = _mf_runner.fetch_rr_intervals
    _mf_runner.fetch_rr_intervals = _chf_fetch
    try:
        records = ["chf201", "chf202", "chf203", "chf204", "chf205"]
        n_surrogates = 30
        rr_truncate = 20000
        seed = 42

        logger.info(
            "CHF2DB pathology contrast: %d records × %d surrogates each",
            len(records),
            n_surrogates,
        )
        runs = [
            per_subject_run(
                rec,
                n_surrogates=n_surrogates,
                rr_truncate=rr_truncate,
                seed=seed,
            )
            for rec in records
        ]
    finally:
        _mf_runner.fetch_rr_intervals = original_fetch

    valid = [r for r in runs if "gamma" in r]
    n_ok = len(valid)
    if n_ok == 0:
        logger.error("no valid CHF subjects")
        return 2

    gammas = np.array([v["gamma"]["value"] for v in valid])
    r2s = np.array([v["gamma"]["r2"] for v in valid])
    delta_hs = np.array([v["mfdfa"]["delta_h"] for v in valid if "delta_h" in v["mfdfa"]])
    h_q2s = np.array([v["mfdfa"]["h_at_q2"] for v in valid if "h_at_q2" in v["mfdfa"]])
    beat_sep = sum(1 for v in valid if v["beat_interval_null"].get("separable_at_z3", False))

    # Load NSR healthy reference
    nsr_ref_path = pathlib.Path("evidence/replications/physionet_nsr2db_multifractal/result.json")
    nsr_ref = None
    if nsr_ref_path.exists():
        nsr_ref = json.loads(nsr_ref_path.read_text())

    # Welch t-test-style comparison on (h(q=2), Δh) clusters
    contrast = {}
    if nsr_ref is not None and len(h_q2s) > 0 and len(delta_hs) > 0:
        nsr_h = np.array(
            [
                r["mfdfa"]["h_at_q2"]
                for r in nsr_ref["per_subject"]
                if "mfdfa" in r and "h_at_q2" in r["mfdfa"]
            ]
        )
        nsr_dh = np.array(
            [
                r["mfdfa"]["delta_h"]
                for r in nsr_ref["per_subject"]
                if "mfdfa" in r and "delta_h" in r["mfdfa"]
            ]
        )

        def _welch_t(a, b):
            if len(a) < 2 or len(b) < 2:
                return float("nan"), float("nan")
            ma, mb = float(a.mean()), float(b.mean())
            va, vb = float(a.var(ddof=1)), float(b.var(ddof=1))
            na, nb = len(a), len(b)
            denom = (va / na + vb / nb) ** 0.5
            t = (ma - mb) / denom if denom > 0 else 0.0
            cohen_d = (ma - mb) / float(np.sqrt((va + vb) / 2)) if (va + vb) > 0 else 0.0
            return t, cohen_d

        t_h, d_h = _welch_t(h_q2s, nsr_h)
        t_dh, d_dh = _welch_t(delta_hs, nsr_dh)
        contrast = {
            "nsr_reference": "evidence/replications/physionet_nsr2db_multifractal/result.json",
            "nsr_h_at_q2_mean": round(float(nsr_h.mean()), 4) if len(nsr_h) else None,
            "nsr_h_at_q2_std": round(float(nsr_h.std(ddof=1)), 4) if len(nsr_h) > 1 else None,
            "nsr_delta_h_mean": round(float(nsr_dh.mean()), 4) if len(nsr_dh) else None,
            "nsr_delta_h_std": round(float(nsr_dh.std(ddof=1)), 4) if len(nsr_dh) > 1 else None,
            "chf_h_at_q2_mean": round(float(h_q2s.mean()), 4) if len(h_q2s) else None,
            "chf_h_at_q2_std": round(float(h_q2s.std(ddof=1)), 4) if len(h_q2s) > 1 else None,
            "chf_delta_h_mean": round(float(delta_hs.mean()), 4) if len(delta_hs) else None,
            "chf_delta_h_std": round(float(delta_hs.std(ddof=1)), 4) if len(delta_hs) > 1 else None,
            "welch_t_h_at_q2": round(float(t_h), 3),
            "cohen_d_h_at_q2": round(float(d_h), 3),
            "welch_t_delta_h": round(float(t_dh), 3),
            "cohen_d_delta_h": round(float(d_dh), 3),
        }

    aggregate = {
        "substrate": "physionet_hrv_chf2db_contrast",
        "claim_status": "hypothesized",
        "n_subjects_ok": n_ok,
        "chf_aggregate": {
            "gamma_mean": round(float(gammas.mean()), 4),
            "gamma_std": round(float(gammas.std(ddof=1)) if n_ok > 1 else 0.0, 4),
            "r2_mean": round(float(r2s.mean()), 4),
            "delta_h_mean": round(float(delta_hs.mean()), 4) if len(delta_hs) else None,
            "delta_h_std": round(float(delta_hs.std(ddof=1)), 4) if len(delta_hs) > 1 else None,
            "h_at_q2_mean": round(float(h_q2s.mean()), 4) if len(h_q2s) else None,
            "h_at_q2_std": round(float(h_q2s.std(ddof=1)), 4) if len(h_q2s) > 1 else None,
            "beat_null_separable_count": f"{beat_sep}/{n_ok}",
        },
        "contrast_vs_nsr2db": contrast,
        "per_subject": runs,
        "interpretation_boundary": (
            "5-subject CHF pilot vs n=5 NSR healthy reference. "
            "Welch t / Cohen's d on (h(q=2), Δh) cluster differences. "
            "Does NOT license clinical claims; n=5 vs n=5 is "
            "underpowered for diagnostic statements. A predictable "
            "shift in the 2D fingerprint between healthy and CHF "
            "would license 'cardiac regime marker is pathology-"
            "discriminative' as a working hypothesis worth scaling. "
            "Per docs/CLAIM_BOUNDARY.md §3.1."
        ),
        "fetched_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    out_path = out_dir / "result.json"
    out_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    logger.info("wrote %s", out_path)

    print()
    print("=" * 70)
    print(f"CHF2DB pathology contrast — {n_ok} CHF subjects vs n=5 NSR")
    print("=" * 70)
    print("CHF cluster:")
    g_std = gammas.std(ddof=1) if n_ok > 1 else 0
    dh_std = delta_hs.std(ddof=1) if len(delta_hs) > 1 else 0
    h_std = h_q2s.std(ddof=1) if len(h_q2s) > 1 else 0
    print(f"  γ:       mean={gammas.mean():.4f} std={g_std:.4f}")
    print(f"  Δh:      mean={delta_hs.mean():.4f} std={dh_std:.4f}")
    print(f"  h(q=2):  mean={h_q2s.mean():.4f} std={h_std:.4f}")
    print(f"  beat-null sep: {beat_sep}/{n_ok}")
    if contrast:
        print()
        print("Contrast vs NSR healthy:")
        nh = contrast["nsr_h_at_q2_mean"]
        nhs = contrast["nsr_h_at_q2_std"]
        ch = contrast["chf_h_at_q2_mean"]
        chs = contrast["chf_h_at_q2_std"]
        print(
            f"  h(q=2): NSR={nh:.4f}±{nhs:.4f} CHF={ch:.4f}±{chs:.4f} "
            f"t={contrast['welch_t_h_at_q2']:.3f} d={contrast['cohen_d_h_at_q2']:.3f}"
        )
        nd = contrast["nsr_delta_h_mean"]
        nds = contrast["nsr_delta_h_std"]
        cd = contrast["chf_delta_h_mean"]
        cds = contrast["chf_delta_h_std"]
        print(
            f"  Δh:     NSR={nd:.4f}±{nds:.4f} CHF={cd:.4f}±{cds:.4f} "
            f"t={contrast['welch_t_delta_h']:.3f} d={contrast['cohen_d_delta_h']:.3f}"
        )
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
