#!/usr/bin/env python3
"""TASK-DIAG / Calibration Diagnostic v3.0.0.

Resolves the CALIBRATION_FAIL from `run_hrv_iaaft_calibration.py`. Two
mutually-exclusive root causes are tested in order:

    D1 (sign-flip)         — `sep = dh_iaaft - dh_real` has the WRONG
                             sign for a nonlinearly-multifractal system.
                             Physical expectation (Ivanov 1999): nonlinear
                             HRV has a WIDER f(α) spectrum than its IAAFT
                             linear-spectrum surrogate, so
                             `Δh(real) > Δh(IAAFT) ⇒ sep_corrected > 0`.
    D2 (pipeline sensitivity) — `mfdfa()` or `iaaft_surrogate()` cannot
                             detect KNOWN multifractality on controlled
                             synthetic signals (fBm + binomial cascade).

Gates:
    DIAG-1+2  — sign analysis on existing STEP-1 results.json
    DIAG-3    — synthetic fBm (monofractal) and binomial multifractal
                cascade validation
    DIAG-4+5  — Q / scale-range sensitivity on a real NSR record (only if
                DIAG-3 says the pipeline is valid or partial)

Verdict decides whether Patch D1 may be applied to `run_hrv_iaaft_calibration.py`.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

from run_eegbci_dh_replication import iaaft_surrogate  # INV-CAL-01
from substrates.physionet_hrv.hrv_gamma_fit import rr_to_uniform_4hz
from substrates.physionet_hrv.mfdfa import mfdfa
from substrates.physionet_hrv.nsr2db_client import PN_DIR, fetch_rr_intervals

STEP1_RESULTS_PATH = pathlib.Path("evidence/replications/hrv_iaaft_calibration/results.json")
OUTPUT_PATH = pathlib.Path("evidence/replications/hrv_iaaft_calibration/diagnostic.json")

# Matches the calibration run (INV-CAL-08 / INV-CAL-07 style).
Q_VALUES_DEFAULT = np.arange(-5.0, 5.5, 0.5)
SCALE_RANGE_HRV = (32, 1024)
N_SURROGATES_SYNTH = 10


# ---------------------------------------------------------------------------
# MFDFA wrapper — matches API in run_hrv_iaaft_calibration + run_eegbci_dh_replication
# ---------------------------------------------------------------------------
def _mfdfa_dh(signal: np.ndarray, q_values: np.ndarray, scale_range: tuple[int, int]):
    res = mfdfa(
        signal,
        q_values=q_values,
        s_min=scale_range[0],
        s_max=scale_range[1],
        n_scales=20,
        fit_order=1,
    )
    return float(res.delta_h), float(res.h_at_q2)


# ===========================================================================
# DIAG-1 + DIAG-2 : sign-flip check on existing STEP-1 results
# ===========================================================================
def diag_sign_flip() -> dict[str, Any]:
    data = json.loads(STEP1_RESULTS_PATH.read_text())
    recs = [r for r in data["records"] if "dh_real" in r and "dh_iaaft_median" in r]
    if not recs:
        return {
            "diag": "DIAG-1+2",
            "error": "no usable records in STEP-1 results.json",
            "diagnosis": "INCOMPLETE_STEP1",
        }

    dh_real = np.asarray([r["dh_real"] for r in recs])
    dh_iaaft = np.asarray([r["dh_iaaft_median"] for r in recs])
    sep_original = dh_iaaft - dh_real  # formula used in STEP-1
    sep_corrected = dh_real - dh_iaaft  # physical convention (Ivanov 1999)

    pooled_std = float(np.sqrt((dh_real.std() ** 2 + dh_iaaft.std() ** 2) / 2) + 1e-10)
    cohens_d = float((dh_real.mean() - dh_iaaft.mean()) / pooled_std)

    print("\n=== DIAG-1 + DIAG-2 : sign analysis on STEP-1 records ===")
    for r, so, sc in zip(recs, sep_original, sep_corrected, strict=True):
        print(
            f"  {r['record']}: dh_real={r['dh_real']:.3f}  "
            f"dh_iaaft={r['dh_iaaft_median']:.3f}  "
            f"sep_orig={so:+.3f}  sep_corr={sc:+.3f}"
        )
    print(
        f"\n  sep_original  mean = {sep_original.mean():+.3f}  "
        "(formula IAAFT − real, used in STEP-1)"
    )
    print(
        f"  sep_corrected mean = {sep_corrected.mean():+.3f}  "
        "(formula real − IAAFT, physical convention)"
    )
    print(f"  Cohen's d (real vs IAAFT) = {cohens_d:+.3f}")

    if sep_corrected.mean() >= 0.05:
        diagnosis = "D1_SIGN_FLIP"
        action = (
            "sep formula has the wrong sign for a nonlinearly-multifractal substrate. "
            "Apply Patch D1 (`sep = dh_real - dh_iaaft`) to both runners, "
            "re-run STEP-1, unlock STEP-2 scaffold on CALIBRATION_PASS."
        )
    elif abs(sep_original.mean()) < 0.03 and abs(sep_corrected.mean()) < 0.03:
        diagnosis = "D2_PIPELINE_SENSITIVITY"
        action = (
            "Neither sign convention exceeds gate magnitude. "
            "Continue to DIAG-3 (synthetic cascade validation)."
        )
    else:
        diagnosis = "AMBIGUOUS"
        action = "Proceed to DIAG-3; combine with DIAG-1+2 for final verdict."

    print(f"  DIAGNOSIS: {diagnosis}")
    print(f"  ACTION:    {action}")

    return {
        "diag": "DIAG-1+2",
        "sep_original_mean": float(sep_original.mean()),
        "sep_original_std": float(sep_original.std()),
        "sep_corrected_mean": float(sep_corrected.mean()),
        "sep_corrected_std": float(sep_corrected.std()),
        "cohens_d_real_vs_iaaft": cohens_d,
        "n_records": len(recs),
        "diagnosis": diagnosis,
        "action": action,
    }


# ===========================================================================
# DIAG-3 : synthetic fBm (monofractal) + binomial multifractal cascade
# ===========================================================================
def _fbm_spectral(n: int, hurst: float, seed: int = 42) -> np.ndarray:
    """Approximate fBm via spectral synthesis (same method as tests/).

    PSD ~ 1/f^{2H+1} for fBm; for fGn ~ 1/f^{2H-1}. We synthesise the
    fGn here so the MFDFA profile Y = cumsum(X) is fBm with Hurst ≈ H.
    """
    rng = np.random.default_rng(seed)
    if abs(hurst - 0.5) < 1e-9:
        return rng.standard_normal(n)
    freqs = np.fft.rfftfreq(n, d=1.0)
    freqs_nz = np.where(freqs == 0.0, 1.0, freqs)
    beta = 2.0 * hurst - 1.0
    amp = freqs_nz ** (-beta / 2.0)
    amp[0] = 0.0
    phases = rng.uniform(0.0, 2.0 * np.pi, len(freqs))
    phases[0] = 0.0
    spectrum = amp * np.exp(1j * phases)
    x = np.fft.irfft(spectrum, n=n)
    x = (x - x.mean()) / (x.std() + 1e-12)
    return x


def _binomial_cascade(n_levels: int, p: float, seed: int = 42) -> np.ndarray:
    """Binomial multiplicative p-cascade (Meneveau & Sreenivasan 1987).

    Known-multifractal benchmark: the singularity spectrum has width
    Δα = |log2(p) − log2(1 − p)|. For p=0.3 this is ≈ 1.22, well above
    any reasonable detection threshold.
    """
    rng = np.random.default_rng(seed)
    size = 2**n_levels
    signal = np.ones(size)
    for level in range(n_levels):
        step = 2 ** (n_levels - level - 1)
        for i in range(0, size, 2 * step):
            # Random choice of which half gets p and which gets (1-p).
            if rng.uniform() < 0.5:
                signal[i : i + step] *= p
                signal[i + step : i + 2 * step] *= 1.0 - p
            else:
                signal[i : i + step] *= 1.0 - p
                signal[i + step : i + 2 * step] *= p
    # Integrate to a multifractal walk (same input shape as HRV uniform RR).
    return np.cumsum(signal - signal.mean())


def diag_synthetic() -> dict[str, Any]:
    print("\n=== DIAG-3 : synthetic validation ===")
    print("  Generating fBm (H=0.7, monofractal) and binomial p-cascade (p=0.3)…")

    fbm = _fbm_spectral(n=8192, hurst=0.7, seed=42)
    mf = _binomial_cascade(n_levels=13, p=0.3, seed=42)

    dh_fbm, hq2_fbm = _mfdfa_dh(fbm, Q_VALUES_DEFAULT, SCALE_RANGE_HRV)
    dh_fbm_surr = [
        _mfdfa_dh(iaaft_surrogate(fbm, seed=k), Q_VALUES_DEFAULT, SCALE_RANGE_HRV)[0]
        for k in range(N_SURROGATES_SYNTH)
    ]
    dh_fbm_iaaft_med = float(np.median(dh_fbm_surr))

    dh_mf, hq2_mf = _mfdfa_dh(mf, Q_VALUES_DEFAULT, SCALE_RANGE_HRV)
    dh_mf_surr = [
        _mfdfa_dh(iaaft_surrogate(mf, seed=k), Q_VALUES_DEFAULT, SCALE_RANGE_HRV)[0]
        for k in range(N_SURROGATES_SYNTH)
    ]
    dh_mf_iaaft_med = float(np.median(dh_mf_surr))

    sep_fbm_orig = dh_fbm_iaaft_med - dh_fbm
    sep_fbm_corr = dh_fbm - dh_fbm_iaaft_med
    sep_mf_orig = dh_mf_iaaft_med - dh_mf
    sep_mf_corr = dh_mf - dh_mf_iaaft_med

    print(
        f"  fBm H=0.7  : Δh_real={dh_fbm:.3f}  h(q=2)={hq2_fbm:.3f}  "
        f"Δh_IAAFT={dh_fbm_iaaft_med:.3f}  sep_orig={sep_fbm_orig:+.3f}  "
        f"sep_corr={sep_fbm_corr:+.3f}  (expected |sep| ≈ 0)"
    )
    print(
        f"  Binom p=0.3: Δh_real={dh_mf:.3f}  h(q=2)={hq2_mf:.3f}  "
        f"Δh_IAAFT={dh_mf_iaaft_med:.3f}  sep_orig={sep_mf_orig:+.3f}  "
        f"sep_corr={sep_mf_corr:+.3f}  (expected Δh>0.2, |sep|>0.05)"
    )

    pipeline_detects_mf = dh_mf > 0.15
    sep_strong = max(abs(sep_mf_orig), abs(sep_mf_corr)) > 0.05
    direction_agrees_with_physics = sep_mf_corr > abs(sep_mf_orig) * 0.5

    if pipeline_detects_mf and sep_strong:
        if direction_agrees_with_physics:
            diag = "PIPELINE_VALID_PHYSICS_SIGN"
            note = (
                "Pipeline detects multifractality AND the physically-correct "
                "sign is `sep = real - IAAFT` (positive for nonlinear cascade). "
                "This corroborates D1 sign-flip on HRV."
            )
        else:
            diag = "PIPELINE_VALID_OPPOSITE_SIGN"
            note = (
                "Pipeline detects multifractality but the direction sep > 0 holds "
                "for the STEP-1 convention (IAAFT − real). Signs on HRV and "
                "synthetic cascade agree — D1 may not apply."
            )
    elif pipeline_detects_mf and not sep_strong:
        diag = "IAAFT_INSUFFICIENT"
        note = (
            "Pipeline detects Δh on a known multifractal, but IAAFT sep is ≈ 0 "
            "in either sign. Surrogate is too close to the real cascade. "
            "Increase N_IAAFT or iterate count."
        )
    else:
        diag = "PIPELINE_INVALID"
        note = (
            "Pipeline does NOT detect multifractality on a known benchmark "
            f"(Δh={dh_mf:.3f} < 0.15). Review Q range, scale range, fit order."
        )

    print(f"  DIAGNOSIS: {diag}")
    print(f"  NOTE:      {note}")

    return {
        "diag": "DIAG-3",
        "fbm_H": 0.7,
        "fbm_dh_real": dh_fbm,
        "fbm_dh_iaaft_median": dh_fbm_iaaft_med,
        "fbm_sep_original": float(sep_fbm_orig),
        "fbm_sep_corrected": float(sep_fbm_corr),
        "binom_p": 0.3,
        "binom_dh_real": dh_mf,
        "binom_dh_iaaft_median": dh_mf_iaaft_med,
        "binom_sep_original": float(sep_mf_orig),
        "binom_sep_corrected": float(sep_mf_corr),
        "diagnosis": diag,
        "note": note,
    }


# ===========================================================================
# DIAG-4 + DIAG-5 : parameter sensitivity on first NSR record
# ===========================================================================
def diag_parameters(first_nsr_record: str = "nsr001") -> dict[str, Any]:
    print(f"\n=== DIAG-4 + DIAG-5 : parameter sweep on {first_nsr_record} ===")
    r = fetch_rr_intervals(first_nsr_record)
    rr = np.asarray(r.rr_seconds, dtype=np.float64)[:20000]
    rr_u = rr_to_uniform_4hz(rr)

    configs = {
        "Q_narrow_SR_HRV": (np.arange(-5, 5.5, 0.5), (32, 1024)),
        "Q_wide_SR_HRV": (np.arange(-10, 10.5, 0.5), (32, 1024)),
        "Q_narrow_SR_short": (np.arange(-5, 5.5, 0.5), (16, 512)),
        "Q_narrow_SR_long": (np.arange(-5, 5.5, 0.5), (64, 2048)),
    }
    out: dict[str, Any] = {}
    for name, (q, sr) in configs.items():
        dh_r, _ = _mfdfa_dh(rr_u, q, sr)
        dh_surr = float(
            np.median([_mfdfa_dh(iaaft_surrogate(rr_u, seed=k), q, sr)[0] for k in range(10)])
        )
        sep_orig = dh_surr - dh_r
        sep_corr = dh_r - dh_surr
        print(
            f"  {name:<22}: Δh_real={dh_r:.3f}  Δh_IAAFT={dh_surr:.3f}  "
            f"sep_orig={sep_orig:+.3f}  sep_corr={sep_corr:+.3f}"
        )
        out[name] = {
            "q_range": [float(q[0]), float(q[-1])],
            "scale_range": list(sr),
            "dh_real": dh_r,
            "dh_iaaft_median": dh_surr,
            "sep_original": float(sep_orig),
            "sep_corrected": float(sep_corr),
        }
    return {"diag": "DIAG-4+5", "record": first_nsr_record, "configs": out}


# ===========================================================================
# Orchestration
# ===========================================================================
def _select_first_nsr() -> str:
    import wfdb

    recs = wfdb.get_record_list(PN_DIR)
    return sorted(r for r in recs if r.startswith("nsr"))[0]


def main() -> int:
    print("=== CALIBRATION DIAGNOSTIC v3.0.0 ===")
    d12 = diag_sign_flip()
    d3 = diag_synthetic()

    d45: dict[str, Any] | None = None
    if d3["diagnosis"] in {
        "PIPELINE_VALID_PHYSICS_SIGN",
        "PIPELINE_VALID_OPPOSITE_SIGN",
        "IAAFT_INSUFFICIENT",
    }:
        rec0 = _select_first_nsr()
        d45 = diag_parameters(first_nsr_record=rec0)

    # Final verdict
    print("\n=== FINAL DIAGNOSTIC VERDICT ===")
    if d12.get("diagnosis") == "D1_SIGN_FLIP" and d3["diagnosis"] == "PIPELINE_VALID_PHYSICS_SIGN":
        verdict = "SIGN_FLIP_CONFIRMED"
        next_action = (
            "Apply Patch D1 (`sep = dh_real - dh_iaaft`) to both "
            "run_hrv_iaaft_calibration.py and the scaffold. Re-run STEP-1."
        )
    elif d12.get("diagnosis") == "D1_SIGN_FLIP":
        verdict = "SIGN_FLIP_LIKELY_SYNTH_AMBIGUOUS"
        next_action = (
            "HRV sign suggests D1 but synthetic benchmark is ambiguous. "
            "Apply Patch D1 as working hypothesis with note in provenance."
        )
    elif d3["diagnosis"] == "PIPELINE_INVALID":
        verdict = "PIPELINE_INVALID"
        next_action = (
            "mfdfa() fails on known multifractal cascade. Do NOT re-run "
            "STEP-1 until Q/scale parameters pass the synthetic gate."
        )
    elif d3["diagnosis"] == "IAAFT_INSUFFICIENT":
        verdict = "IAAFT_INSUFFICIENT"
        next_action = (
            "Pipeline detects Δh but IAAFT sep ≈ 0 on cascade. "
            "Increase N_IAAFT and iteration count before re-running STEP-1."
        )
    else:
        verdict = "REQUIRES_MANUAL_REVIEW"
        next_action = "d12 + d3 are not jointly conclusive — inspect diagnostic.json."

    print(f"  VERDICT     : {verdict}")
    print(f"  NEXT ACTION : {next_action}")

    output = {
        "protocol_version": "v3.0.0",
        "date": "2026-04-15",
        "diag_1_2": d12,
        "diag_3": d3,
        "diag_4_5": d45,
        "VERDICT": verdict,
        "next_action": next_action,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"  Output      : {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
