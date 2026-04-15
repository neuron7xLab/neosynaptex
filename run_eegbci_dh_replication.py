#!/usr/bin/env python3
"""EEG resting-state Δh replication — V3 Δh invariant protocol.

Pre-registration : evidence/priors/eeg_resting_literature_prior.yaml
Dataset          : PhysioNet EEGBCI (Motor Movement/Imagery), S001-S020
Runs             : baseline run 1 (eyes-open rest)
Channels         : C3, Cz, C4
Pre-registered   :
    * Δh band              : [0.11, 0.59]   (2σ from Zorick 2013 prior)
    * IAAFT sep. threshold : 0.05           (Δh(IAAFT) - Δh(real) >= 0.05)
    * subject pass rate    : >= 70%
    * scale window         : (s_min=16, s_max=512)
    * q values             : np.arange(-5, 5.5, 0.5)

Hypothesis (V3 structural):
    Δh(real) < Δh(IAAFT)  AND  Δh(real) ∈ [0.11, 0.59]  on >= 70% of subjects.
    Directional homology with HRV (Δh_NSR < Δh_CHF) — NOT numerical identity.

Verdict logic is EVALUATED ONCE on the full result set and written into
``evidence/replications/eegbci_dh_replication/results.json``. No re-run
of the verdict after the first run is permitted (INV-MF-07).
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import pathlib
import sys
from typing import Any

import mne
import numpy as np
import yaml
from mne.datasets import eegbci

from substrates.physionet_hrv.mfdfa import mfdfa

# ---------------------------------------------------------------------------
# Immutable configuration (INV-MF-01, INV-MF-08)
# ---------------------------------------------------------------------------
PREREG_PATH = pathlib.Path("evidence/priors/eeg_resting_literature_prior.yaml")
OUTPUT_DIR = pathlib.Path("evidence/replications/eegbci_dh_replication")
LOG_PATH = OUTPUT_DIR / "run.log"
RESULTS_PATH = OUTPUT_DIR / "results.json"

SUBJECTS: list[int] = list(range(1, 21))  # S001-S020
RUNS_RESTING: list[int] = [1]  # EEGBCI run 1 = baseline eyes-open rest
CHANNELS: list[str] = ["C3", "Cz", "C4"]
FS_NOMINAL: float = 160.0
EPOCH_LEN_S: float = 30.0

Q_VALUES = np.arange(-5.0, 5.5, 0.5)
SCALE_RANGE: tuple[int, int] = (16, 512)
N_SCALES: int = 20
FIT_ORDER: int = 1

N_IAAFT: int = 20
IAAFT_ITERS: int = 20

# Pre-registered thresholds — MUST MATCH the YAML prior
DH_BAND: tuple[float, float] = (0.11, 0.59)
IAAFT_SEP_MIN: float = 0.05
PASS_RATE_THR: float = 0.70

# HRV reference (empirical, from evidence/replications/physionet_chf2db_contrast)
HRV_NSR_DH_MEAN: float = 0.19
HRV_NSR_DH_STD: float = 0.09
HRV_CHF_DH_MEAN: float = 0.66
HRV_CHF_DH_STD: float = 0.35

logger = logging.getLogger("eegbci_dh")


# ---------------------------------------------------------------------------
# IAAFT surrogate — thin wrapper around the canonical core path.
# ---------------------------------------------------------------------------
# The original in-file implementation (pre-2026-04-15) closed its loop on
# a spectrum-match step, so the returned surrogate had approximate
# amplitudes and SIGN-FLIP-DIAG-v1 T4 failed with KS p < 1e-12 on 3/5
# NSR records. The canonical core/iaaft.py path closes on amplitude
# rank-remap (Schreiber & Schmitz 1996) and satisfies the T4 exact-sort
# gate by construction. PR #124 (V3 EEG replication) was produced with
# the old in-file version; that numerical result is preserved in the
# evidence directory and is NOT retroactively re-computed by this
# canonicalisation — any re-run under the repaired IAAFT must be filed
# as a new artefact.
from core.iaaft import iaaft_surrogate as _canonical_iaaft  # noqa: E402


def iaaft_surrogate(signal: np.ndarray, seed: int, n_iter: int = IAAFT_ITERS) -> np.ndarray:
    """Backwards-compatible wrapper delegating to ``core.iaaft.iaaft_surrogate``.

    Kept so existing callers in this module and in the diagnostic
    scripts can continue to import ``iaaft_surrogate`` from here. The
    signature (``seed=<int>`` keyword) is the new-API shape and returns
    a bare surrogate array — no legacy 3-tuple.
    """

    return _canonical_iaaft(signal, seed=seed, n_iter=n_iter)


# ---------------------------------------------------------------------------
# MFDFA wrapper — single source of truth for (h(q=2), Δh) extraction
# ---------------------------------------------------------------------------
def extract_dh_metrics(signal: np.ndarray) -> dict[str, float]:
    """Return (h(q=2), Δh, α_min, α_max) via MFDFA at the pre-registered window."""
    res = mfdfa(
        signal,
        q_values=Q_VALUES,
        s_min=SCALE_RANGE[0],
        s_max=SCALE_RANGE[1],
        n_scales=N_SCALES,
        fit_order=FIT_ORDER,
    )
    alpha = np.asarray(res.alpha)
    alpha_valid = alpha[np.isfinite(alpha)]
    return {
        "h_q2": float(res.h_at_q2),
        "delta_h": float(res.delta_h),
        "alpha_min": float(alpha_valid.min()) if len(alpha_valid) else float("nan"),
        "alpha_max": float(alpha_valid.max()) if len(alpha_valid) else float("nan"),
    }


# ---------------------------------------------------------------------------
# Per-subject pipeline
# ---------------------------------------------------------------------------
def process_subject(subj: int) -> dict[str, Any]:
    logger.info("=== Subject S%03d ===", subj)

    raw_files = eegbci.load_data(subj, RUNS_RESTING, update_path=True)
    raws = [mne.io.read_raw_edf(f, preload=True, verbose="ERROR") for f in raw_files]
    raw = mne.io.concatenate_raws(raws)

    # EEGBCI channel names come with trailing dots (e.g. "C3..").
    eegbci.standardize(raw)
    # Bandpass + notch.
    raw.filter(0.5, 45.0, verbose="ERROR")
    # US grid → 60 Hz mains.
    raw.notch_filter(60.0, verbose="ERROR")
    raw.pick(CHANNELS, verbose="ERROR")

    epochs = mne.make_fixed_length_epochs(
        raw, duration=EPOCH_LEN_S, overlap=0.0, preload=True, verbose="ERROR"
    )
    data = epochs.get_data()  # shape: (n_epochs, n_channels, n_times)
    n_epochs, n_ch, n_times = data.shape
    logger.info(
        "  loaded: %d epochs × %d ch × %d samples  (fs=%.1f)",
        n_epochs,
        n_ch,
        n_times,
        raw.info["sfreq"],
    )

    # --- MFDFA on all real epoch × channel pairs ---
    real_metrics: list[dict[str, Any]] = []
    for ep_idx, ep in enumerate(data):
        for ch_idx, ch_name in enumerate(CHANNELS):
            try:
                m = extract_dh_metrics(ep[ch_idx])
            except Exception as exc:  # noqa: BLE001 — diagnostic
                logger.warning("    MFDFA failed on ep=%d ch=%s: %s", ep_idx, ch_name, exc)
                continue
            m["epoch"] = ep_idx
            m["channel"] = ch_name
            real_metrics.append(m)

    if not real_metrics:
        raise RuntimeError(f"S{subj:03d}: no successful MFDFA fits")

    dh_real = np.array([m["delta_h"] for m in real_metrics])
    hq2_real = np.array([m["h_q2"] for m in real_metrics])

    # --- IAAFT surrogates: on one representative epoch × channel ---
    ref_signal = data[0][0]  # epoch 0, channel C3
    iaaft_dh: list[float] = []
    for k in range(N_IAAFT):
        try:
            surr = iaaft_surrogate(ref_signal, seed=k + 1000 * subj)
            iaaft_dh.append(extract_dh_metrics(surr)["delta_h"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("    IAAFT #%d failed: %s", k, exc)
    iaaft_dh_arr = np.asarray(iaaft_dh)

    dh_real_med = float(np.median(dh_real))
    dh_iaaft_med = float(np.median(iaaft_dh_arr)) if len(iaaft_dh_arr) else float("nan")
    hq2_real_med = float(np.median(hq2_real))
    iaaft_sep = dh_iaaft_med - dh_real_med

    in_band = DH_BAND[0] <= dh_real_med <= DH_BAND[1]
    nonlinear = iaaft_sep >= IAAFT_SEP_MIN
    subj_pass = bool(in_band and nonlinear)

    logger.info(
        "  S%03d: h(q=2)=%.3f  Δh=%.3f  Δh_IAAFT=%.3f  sep=%+.3f  PASS=%s",
        subj,
        hq2_real_med,
        dh_real_med,
        dh_iaaft_med,
        iaaft_sep,
        subj_pass,
    )

    return {
        "subject": f"S{subj:03d}",
        "h_q2_median": hq2_real_med,
        "dh_median": dh_real_med,
        "dh_iaaft_median": dh_iaaft_med,
        "iaaft_separation": float(iaaft_sep),
        "in_dh_band": bool(in_band),
        "nonlinear": bool(nonlinear),
        "PASS": subj_pass,
        "n_epochs": int(n_epochs),
        "n_real_fits": int(len(real_metrics)),
        "n_iaaft_fits": int(len(iaaft_dh_arr)),
        "dh_real_all": dh_real.tolist(),
        "hq2_real_all": hq2_real.tolist(),
        "dh_iaaft_all": iaaft_dh_arr.tolist(),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
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

    if not PREREG_PATH.exists():
        logger.error("pre-reg missing: %s", PREREG_PATH)
        return 2
    prereg = yaml.safe_load(PREREG_PATH.read_text())
    logger.info("Loaded prereg: %s (version %s)", PREREG_PATH, prereg.get("prereg_version"))

    logger.info(
        "Config: n_subjects=%d  scale_range=%s  q=%s..%s (%d)  IAAFT=%d×%d iter",
        len(SUBJECTS),
        SCALE_RANGE,
        Q_VALUES[0],
        Q_VALUES[-1],
        len(Q_VALUES),
        N_IAAFT,
        IAAFT_ITERS,
    )

    subjects_results: list[dict[str, Any]] = []
    for subj in SUBJECTS:
        try:
            subjects_results.append(process_subject(subj))
        except Exception as exc:  # noqa: BLE001
            logger.exception("S%03d failed: %s", subj, exc)
            subjects_results.append({"subject": f"S{subj:03d}", "error": str(exc), "PASS": False})

    # --- Aggregate ---
    completed = [r for r in subjects_results if "error" not in r]
    dh_arr = np.asarray([r["dh_median"] for r in completed])
    hq2_arr = np.asarray([r["h_q2_median"] for r in completed])
    iaaft_arr = np.asarray([r["dh_iaaft_median"] for r in completed])
    sep_arr = np.asarray([r["iaaft_separation"] for r in completed])
    n_pass = sum(bool(r.get("PASS")) for r in subjects_results)
    pass_rate = n_pass / len(subjects_results) if subjects_results else 0.0

    # --- Verdict (pre-registered, evaluated ONCE) ---
    if pass_rate >= PASS_RATE_THR:
        verdict = "PASS"
        interpretation = (
            "H1 supported: Δh(real) < Δh(IAAFT) by >= 0.05 AND Δh ∈ [0.11, 0.59] "
            f"on {n_pass}/{len(subjects_results)} subjects. Directional homology "
            "with HRV (Δh_NSR < Δh_CHF) is preliminarily reproduced on resting EEG."
        )
    elif len(dh_arr) and dh_arr.mean() > 0.60:
        verdict = "FAIL_HIGH_DH"
        interpretation = (
            f"Δh too high (mean={dh_arr.mean():.3f} > 0.60). No critical-regime "
            "signature detected on resting EEG."
        )
    elif len(sep_arr) and sep_arr.mean() < IAAFT_SEP_MIN:
        verdict = "FAIL_LINEAR"
        interpretation = (
            f"IAAFT surrogates indistinguishable from real (mean sep="
            f"{sep_arr.mean():.3f} < {IAAFT_SEP_MIN}). No multifractal nonlinearity "
            "beyond linear spectrum + marginal."
        )
    else:
        verdict = "INCONCLUSIVE"
        interpretation = (
            f"Partial evidence: pass_rate={pass_rate:.2f} < {PASS_RATE_THR:.2f}. "
            "Inspect individual-subject separations before promotion."
        )

    output = {
        "protocol_version": "v3_delta_h_invariant",
        "prereg_ref": str(PREREG_PATH),
        "execution_date": _dt.datetime.now(_dt.UTC).isoformat(),
        "commit_sha": None,  # stamped at merge
        "n_subjects_attempted": len(subjects_results),
        "n_subjects_completed": len(completed),
        "n_subjects_failed": len(subjects_results) - len(completed),
        "h_q2": {
            "mean": float(hq2_arr.mean()) if len(hq2_arr) else None,
            "std": float(hq2_arr.std()) if len(hq2_arr) else None,
            "median": float(np.median(hq2_arr)) if len(hq2_arr) else None,
        },
        "delta_h": {
            "mean": float(dh_arr.mean()) if len(dh_arr) else None,
            "std": float(dh_arr.std()) if len(dh_arr) else None,
            "median": float(np.median(dh_arr)) if len(dh_arr) else None,
            "band": list(DH_BAND),
        },
        "delta_h_iaaft": {
            "mean": float(iaaft_arr.mean()) if len(iaaft_arr) else None,
            "std": float(iaaft_arr.std()) if len(iaaft_arr) else None,
            "median": float(np.median(iaaft_arr)) if len(iaaft_arr) else None,
        },
        "iaaft_separation": {
            "mean": float(sep_arr.mean()) if len(sep_arr) else None,
            "std": float(sep_arr.std()) if len(sep_arr) else None,
            "threshold": IAAFT_SEP_MIN,
        },
        "n_pass": n_pass,
        "pass_rate": pass_rate,
        "pass_rate_threshold": PASS_RATE_THR,
        "VERDICT": verdict,
        "interpretation": interpretation,
        "hrv_prior_reference": {
            "substrate_ref": "evidence/replications/physionet_chf2db_contrast",
            "NSR_dh_mean": HRV_NSR_DH_MEAN,
            "NSR_dh_std": HRV_NSR_DH_STD,
            "CHF_dh_mean": HRV_CHF_DH_MEAN,
            "CHF_dh_std": HRV_CHF_DH_STD,
            "cohen_d_dh": 1.85,
        },
        "config": {
            "channels": CHANNELS,
            "fs_nominal": FS_NOMINAL,
            "epoch_len_s": EPOCH_LEN_S,
            "q_range": [float(Q_VALUES[0]), float(Q_VALUES[-1])],
            "q_step": 0.5,
            "scale_range": list(SCALE_RANGE),
            "n_scales": N_SCALES,
            "fit_order": FIT_ORDER,
            "n_iaaft": N_IAAFT,
            "iaaft_iters": IAAFT_ITERS,
        },
        "subjects": subjects_results,
    }
    RESULTS_PATH.write_text(json.dumps(output, indent=2))

    # --- Final log banner ---
    logger.info("=" * 60)
    logger.info("[VERDICT] %s", verdict)
    if len(dh_arr):
        logger.info(
            "  Δh = %.3f ± %.3f (band %s)",
            dh_arr.mean(),
            dh_arr.std(),
            DH_BAND,
        )
        logger.info(
            "  Δh_IAAFT = %.3f ± %.3f  | separation = %+.3f",
            iaaft_arr.mean(),
            iaaft_arr.std(),
            sep_arr.mean(),
        )
    logger.info(
        "  pass_rate = %d/%d = %.1f%% (threshold %.0f%%)",
        n_pass,
        len(subjects_results),
        pass_rate * 100,
        PASS_RATE_THR * 100,
    )
    logger.info("  %s", interpretation)
    logger.info("  Results: %s", RESULTS_PATH)
    logger.info("=" * 60)

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
