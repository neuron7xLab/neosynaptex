#!/usr/bin/env python3
"""STEP-1 / HRV IAAFT calibration — close the §3.2 apples-to-oranges gap.

Motivation
----------
The V3 cross-substrate comparison in PR #124 quoted HRV IAAFT separation
from literature (Ivanov et al. 1999), while the EEG separation was
measured with our own ``iaaft_surrogate`` + ``mfdfa`` pipeline. Any
reviewer would reject the comparison as apples-to-oranges. This script
closes that gap: it runs the EXACT SAME ``iaaft_surrogate`` (imported
verbatim from the V3 runner — INV-CAL-01) on 5 NSR2DB subjects at 4 Hz
uniform resampling, with q = [-5, 5] step 0.5 — matching EEG.

Gate
----
    sep_HRV (mean over 5 subjects) ≥ 0.05  →  CALIBRATION_PASS → STEP-2
    sep_HRV < 0.05                         →  CALIBRATION_FAIL → STOP
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import pathlib
import sys
from typing import Any

import numpy as np
import wfdb

from run_eegbci_dh_replication import (  # INV-CAL-01: verbatim import
    iaaft_surrogate,
)
from substrates.physionet_hrv.hrv_gamma_fit import rr_to_uniform_4hz
from substrates.physionet_hrv.mfdfa import mfdfa
from substrates.physionet_hrv.nsr2db_client import PN_DIR, fetch_rr_intervals

# ---------------------------------------------------------------------------
# Immutable configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = pathlib.Path("evidence/replications/hrv_iaaft_calibration")
LOG_PATH = OUTPUT_DIR / "run.log"
RESULTS_PATH = OUTPUT_DIR / "results.json"

# Record selection — dynamically discovered from PhysioNet, not hard-coded.
# Patch per Grok review: if the NSR2DB snapshot changes and a record is
# missing, the static list would crash on first fetch. Discovery via
# wfdb.get_record_list is the authoritative source.
_ALL_PHYSIONET_RECORDS = wfdb.get_record_list(PN_DIR)
NSR_RECORDS: tuple[str, ...] = tuple(
    sorted(r for r in _ALL_PHYSIONET_RECORDS if r.startswith("nsr"))[:5]
)
RR_TRUNCATE: int = 20000  # match PR #102

# 4 Hz uniform × [8 s, 256 s] → [32, 1024] samples
HRV_SCALE_RANGE: tuple[int, int] = (32, 1024)
HRV_Q_VALUES = np.arange(-5.0, 5.5, 0.5)  # matches EEG (apples-to-apples)
N_IAAFT: int = 20

# Gate — identical to EEG V3
SEP_THRESHOLD: float = 0.05

# V3 EEG reference (from PR #124)
EEG_SEP_REF: float = 0.020

logger = logging.getLogger("hrv_iaaft_cal")


def _mfdfa_delta_h(x: np.ndarray) -> tuple[float, float]:
    """Return (Δh, h(q=2)) from our MFDFA at the pre-registered HRV window."""
    res = mfdfa(
        x,
        q_values=HRV_Q_VALUES,
        s_min=HRV_SCALE_RANGE[0],
        s_max=HRV_SCALE_RANGE[1],
        n_scales=20,
        fit_order=1,
    )
    return float(res.delta_h), float(res.h_at_q2)


def per_record(record_name: str) -> dict[str, Any]:
    logger.info("=== %s ===", record_name)
    r = fetch_rr_intervals(record_name)
    rr_seconds = np.asarray(r.rr_seconds, dtype=np.float64)[:RR_TRUNCATE]
    rr_uniform = rr_to_uniform_4hz(rr_seconds)
    n_uniform = len(rr_uniform)
    logger.info("  n_rr=%d → uniform 4 Hz n=%d", len(rr_seconds), n_uniform)

    dh_real, hq2_real = _mfdfa_delta_h(rr_uniform)

    dh_iaaft: list[float] = []
    for k in range(N_IAAFT):
        # Deterministic seed per (record, surrogate) so re-runs match.
        seed = (abs(hash(record_name)) % 10_000_000) * 1000 + k
        surr = iaaft_surrogate(rr_uniform, seed=seed)
        dh_k, _ = _mfdfa_delta_h(surr)
        dh_iaaft.append(dh_k)
    dh_iaaft = np.asarray(dh_iaaft)

    dh_iaaft_med = float(np.median(dh_iaaft))
    sep = dh_iaaft_med - dh_real
    nonlinear = sep >= SEP_THRESHOLD

    logger.info(
        "  h(q=2)=%.4f  Δh=%.4f  Δh_IAAFT_med=%.4f  sep=%+.4f  nonlinear=%s",
        hq2_real,
        dh_real,
        dh_iaaft_med,
        sep,
        nonlinear,
    )

    return {
        "record": record_name,
        "n_rr_raw": len(rr_seconds),
        "n_uniform": n_uniform,
        "h_q2": hq2_real,
        "dh_real": dh_real,
        "dh_iaaft_median": dh_iaaft_med,
        "dh_iaaft_mean": float(dh_iaaft.mean()),
        "dh_iaaft_std": float(dh_iaaft.std()),
        "sep": float(sep),
        "nonlinear": bool(nonlinear),
        "dh_iaaft_all": dh_iaaft.tolist(),
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger.info(
        "HRV IAAFT calibration — %d records × %d surrogates — scale=%s q=[%s..%s]",
        len(NSR_RECORDS),
        N_IAAFT,
        HRV_SCALE_RANGE,
        HRV_Q_VALUES[0],
        HRV_Q_VALUES[-1],
    )

    per_record_results: list[dict[str, Any]] = []
    for rec in NSR_RECORDS:
        try:
            per_record_results.append(per_record(rec))
        except Exception as exc:  # noqa: BLE001 — continue on record failure
            logger.exception("%s failed: %s", rec, exc)
            per_record_results.append({"record": rec, "error": str(exc)})

    completed = [r for r in per_record_results if "error" not in r]
    if not completed:
        logger.error("no records completed — cannot compute verdict")
        return 3

    sep_arr = np.asarray([r["sep"] for r in completed])
    dh_arr = np.asarray([r["dh_real"] for r in completed])
    iaaft_arr = np.asarray([r["dh_iaaft_median"] for r in completed])
    hq2_arr = np.asarray([r["h_q2"] for r in completed])
    nonlinear_frac = float(sum(r["nonlinear"] for r in completed) / len(completed))

    sep_mean = float(sep_arr.mean())
    sep_std = float(sep_arr.std())

    if sep_mean >= SEP_THRESHOLD:
        verdict = "CALIBRATION_PASS"
        interpretation = (
            f"sep_HRV = {sep_mean:.3f} ± {sep_std:.3f} ≥ {SEP_THRESHOLD}. "
            "Our pipeline detects HRV nonlinearity. §3.2 apples-to-apples "
            "gap closed. STEP-2 (B1 alpha-band EEG) may proceed."
        )
    else:
        verdict = "CALIBRATION_FAIL"
        interpretation = (
            f"sep_HRV = {sep_mean:.3f} ± {sep_std:.3f} < {SEP_THRESHOLD}. "
            "Our MFDFA+IAAFT pipeline cannot detect HRV nonlinearity. "
            "STOP: both EEG and HRV FAIL_LINEAR are likely pipeline artefacts. "
            "Do NOT run B1. Review mfdfa Q range, scale window, iteration count."
        )

    output = {
        "protocol": "STEP-1 HRV IAAFT Calibration",
        "protocol_version": "v2.0.0",
        "execution_date": _dt.datetime.now(_dt.UTC).isoformat(),
        "pipeline_provenance": (
            "iaaft_surrogate imported verbatim from run_eegbci_dh_replication; "
            "mfdfa from substrates.physionet_hrv.mfdfa; "
            "rr_to_uniform_4hz from substrates.physionet_hrv.hrv_gamma_fit"
        ),
        "dataset": "PhysioNet NSR2DB",
        "records_used": list(NSR_RECORDS),
        "rr_truncate": RR_TRUNCATE,
        "config": {
            "scale_range": list(HRV_SCALE_RANGE),
            "q_range": [float(HRV_Q_VALUES[0]), float(HRV_Q_VALUES[-1])],
            "q_step": 0.5,
            "n_iaaft": N_IAAFT,
            "fs_uniform_hz": 4.0,
            "sep_threshold": SEP_THRESHOLD,
        },
        "n_records_attempted": len(per_record_results),
        "n_records_completed": len(completed),
        "h_q2": {"mean": float(hq2_arr.mean()), "std": float(hq2_arr.std())},
        "dh_real": {"mean": float(dh_arr.mean()), "std": float(dh_arr.std())},
        "dh_iaaft": {"mean": float(iaaft_arr.mean()), "std": float(iaaft_arr.std())},
        "sep": {
            "mean": sep_mean,
            "std": sep_std,
            "per_record": sep_arr.tolist(),
            "nonlinear_fraction": nonlinear_frac,
        },
        "VERDICT": verdict,
        "interpretation": interpretation,
        "eeg_sep_ref": EEG_SEP_REF,
        "delta_hrv_vs_eeg": float(sep_mean - EEG_SEP_REF),
        "records": per_record_results,
    }
    RESULTS_PATH.write_text(json.dumps(output, indent=2))

    logger.info("=" * 60)
    logger.info("[STEP-1 VERDICT] %s", verdict)
    logger.info("  sep_HRV = %.3f ± %.3f  (threshold %s)", sep_mean, sep_std, SEP_THRESHOLD)
    logger.info("  sep_EEG_ref = %.3f  (PR #124)", EEG_SEP_REF)
    logger.info("  Δ(sep_HRV − sep_EEG) = %+.3f", sep_mean - EEG_SEP_REF)
    logger.info("  %s", interpretation)
    logger.info("  Output: %s", RESULTS_PATH)
    logger.info("=" * 60)

    return 0 if verdict == "CALIBRATION_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
