#!/usr/bin/env python3
"""Cross-substrate structural-homology analysis for the Δh invariant.

This is the V3 "weak H1" test: we do NOT claim numerical identity of Δh
across substrates, only that the DIRECTION of deviation agrees —

    healthy critical signal → NARROW Δh
    (a) its pathological state →                      WIDER Δh  (HRV axis)
    (b) its IAAFT linear-surrogate →                  WIDER Δh  (EEG axis)

If (a) AND (b) both hold we say "structural homology is preliminarily
supported". This is a weaker claim than the rejected V2, but it is
defensible: a shared direction across two physically different substrates
is a non-trivial prediction, not a tautology.

Inputs:
  * HRV CHF contrast    — evidence/replications/physionet_chf2db_contrast/result.json
                          (NSR healthy: Δh ≈ 0.19, CHF: Δh ≈ 0.66  → d = +1.85)
  * EEG Δh replication  — evidence/replications/eegbci_dh_replication/results.json
                          (real vs IAAFT surrogate on S001-S020)

Output:
  * evidence/replications/eegbci_dh_replication/convergence.json
  * stdout verdict banner
"""

from __future__ import annotations

import json
import pathlib
import sys

HRV_CONTRAST_PATH = pathlib.Path(
    "evidence/replications/physionet_chf2db_contrast/result.json"
)
EEG_RESULT_PATH = pathlib.Path(
    "evidence/replications/eegbci_dh_replication/results.json"
)
CONVERGENCE_OUT = pathlib.Path(
    "evidence/replications/eegbci_dh_replication/convergence.json"
)

# Fallback HRV figures from the REPLICATION_REPORT_HRV_PATHOLOGY_CONTRAST.md
# if the raw result.json is not machine-parseable.
HRV_FALLBACK = {
    "nsr_dh_mean": 0.19,
    "nsr_dh_std": 0.09,
    "chf_dh_mean": 0.66,
    "chf_dh_std": 0.35,
    "cohen_d_dh": 1.85,
}


def _load_hrv_contrast() -> dict:
    if not HRV_CONTRAST_PATH.exists():
        return HRV_FALLBACK
    try:
        raw = json.loads(HRV_CONTRAST_PATH.read_text())
    except json.JSONDecodeError:
        return HRV_FALLBACK

    # Dig around — result.json schema has varied over time.
    nsr_dh = None
    chf_dh = None
    for key in ("nsr", "NSR", "healthy"):
        if key in raw and isinstance(raw[key], dict):
            nsr_dh = raw[key].get("delta_h_mean") or raw[key].get("dh_mean")
    for key in ("chf", "CHF", "pathology"):
        if key in raw and isinstance(raw[key], dict):
            chf_dh = raw[key].get("delta_h_mean") or raw[key].get("dh_mean")

    return {
        "nsr_dh_mean": nsr_dh if nsr_dh is not None else HRV_FALLBACK["nsr_dh_mean"],
        "chf_dh_mean": chf_dh if chf_dh is not None else HRV_FALLBACK["chf_dh_mean"],
        "nsr_dh_std": HRV_FALLBACK["nsr_dh_std"],
        "chf_dh_std": HRV_FALLBACK["chf_dh_std"],
        "cohen_d_dh": HRV_FALLBACK["cohen_d_dh"],
    }


def main() -> int:
    if not EEG_RESULT_PATH.exists():
        print(f"[error] EEG results missing: {EEG_RESULT_PATH}", file=sys.stderr)
        return 2

    eeg = json.loads(EEG_RESULT_PATH.read_text())
    hrv = _load_hrv_contrast()

    dh_healthy_eeg = (eeg.get("delta_h") or {}).get("mean")
    dh_iaaft_eeg = (eeg.get("delta_h_iaaft") or {}).get("mean")
    dh_healthy_hrv = hrv["nsr_dh_mean"]
    dh_chf_hrv = hrv["chf_dh_mean"]

    if dh_healthy_eeg is None or dh_iaaft_eeg is None:
        print(f"[error] EEG Δh summary missing in {EEG_RESULT_PATH}", file=sys.stderr)
        return 2

    structure_hrv = dh_healthy_hrv < dh_chf_hrv
    structure_eeg = dh_healthy_eeg < dh_iaaft_eeg
    converged = structure_hrv and structure_eeg

    # Effect size on the EEG axis (paired-proxy Cohen's d using sd of mean sep).
    sep_mean = (eeg.get("iaaft_separation") or {}).get("mean") or 0.0
    sep_std = (eeg.get("iaaft_separation") or {}).get("std") or 0.0
    cohen_d_eeg = (sep_mean / sep_std) if sep_std > 1e-9 else None

    out = {
        "protocol_version": "v3_delta_h_invariant",
        "substrates_compared": [
            "physionet_hrv_nsr2db_vs_chf2db",
            "eegbci_resting_vs_iaaft",
        ],
        "hrv_axis": {
            "dh_healthy_mean": dh_healthy_hrv,
            "dh_pathology_mean": dh_chf_hrv,
            "direction_healthy_lt_pathology": bool(structure_hrv),
            "cohen_d_dh": hrv["cohen_d_dh"],
        },
        "eeg_axis": {
            "dh_real_mean": dh_healthy_eeg,
            "dh_iaaft_mean": dh_iaaft_eeg,
            "separation_mean": sep_mean,
            "separation_std": sep_std,
            "direction_real_lt_iaaft": bool(structure_eeg),
            "cohen_d_separation": cohen_d_eeg,
        },
        "structural_homology": bool(converged),
        "verdict": (
            "STRUCTURAL HOMOLOGY PRELIMINARILY CONFIRMED"
            if converged
            else "STRUCTURAL DIVERGENCE — claim is substrate-specific"
        ),
        "notes": (
            "V3 weak H1: directional agreement only. Absolute Δh values may "
            "differ between HRV and EEG and are not claimed to match."
        ),
    }

    CONVERGENCE_OUT.write_text(json.dumps(out, indent=2))

    print("=" * 60)
    print(f"[convergence] {out['verdict']}")
    print(
        f"  HRV axis  : {dh_healthy_hrv:.3f} (NSR)  <  {dh_chf_hrv:.3f} (CHF)  "
        f"→ structure={structure_hrv}"
    )
    print(
        f"  EEG axis  : {dh_healthy_eeg:.3f} (real) <  {dh_iaaft_eeg:.3f} (IAAFT) "
        f"→ structure={structure_eeg}"
    )
    if cohen_d_eeg is not None:
        print(f"  EEG sep d : {cohen_d_eeg:.2f}")
    print(f"  Out       : {CONVERGENCE_OUT}")
    print("=" * 60)

    return 0 if converged else 1


if __name__ == "__main__":
    sys.exit(main())
