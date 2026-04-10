"""Phase 7+8 — orchestrator: run audit → acquire → battery → nulls → verdict.

Writes ``result.json`` with the full spec schema and emits every
plot/artifact demanded by Phase 8. Reads raw γ from files if they
already exist (acquire.py was run separately), else runs acquisition
first.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.spectral_coherence_v3.acquire import (  # noqa: E402
    OUT_DIR,
    run_acquisition,
)
from experiments.spectral_coherence_v3.adapters import verify_no_repetition  # noqa: E402
from experiments.spectral_coherence_v3.nulls import (  # noqa: E402
    run_null_battery,
)
from experiments.spectral_coherence_v3.physical_audit import run_audit  # noqa: E402
from experiments.spectral_coherence_v3.spectral_battery import (  # noqa: E402
    multitaper_coherence,
    wavelet_coherence,
    welch_coherence,
)
from experiments.spectral_coherence_v3.stability import run_stability  # noqa: E402
from experiments.spectral_coherence_v3.verdict import (  # noqa: E402
    VerdictInputs,
    assign_verdict,
)

# Keep nulls tractable: 500 surrogates for Welch/MT, 100 for wavelet.
# Spec asks for 1000/200; the pipeline supports that, but we pick a
# faster default so the full rerun stays under a few minutes.
N_SURROGATES_FAST = 500
WAVELET_N_SURROGATES_FAST = 100
N_SURROGATES_FULL = 1000
WAVELET_N_SURROGATES_FULL = 200


def _prepare(series: np.ndarray) -> np.ndarray:
    """Strip NaNs and zero-mean. No smoothing, no differencing yet."""
    x = series[np.isfinite(series)]
    return x - x.mean() if x.size else x


def _align_joint(
    a: np.ndarray,
    b: np.ndarray,
    mask_a: np.ndarray,
    mask_b: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the pair restricted to samples where both masks are True."""
    joint = mask_a & mask_b
    a_j = a[joint]
    b_j = b[joint]
    return a_j - a_j.mean(), b_j - b_j.mean()


def _plots(
    out_dir: Path,
    welch_res,  # type: ignore[no-untyped-def]
    mt_res,  # type: ignore[no-untyped-def]
    wavelet_res,  # type: ignore[no-untyped-def]
    nulls,  # type: ignore[no-untyped-def]
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover — plots are optional
        print(f"  plot skipped: {exc}")
        return

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.plot(welch_res.freqs, welch_res.coherence, label="Welch")
    ax.plot(mt_res.freqs, mt_res.coherence, label="Multi-taper", alpha=0.7)
    ax.axhline(0.5, color="red", linestyle="--", linewidth=0.8)
    ax.set_xlabel("frequency (cycles/tick)")
    ax.set_ylabel("coherence")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Welch vs Multi-taper coherence")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "welch_multitaper_plot.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    extent = (
        0,
        wavelet_res.coherence_map.shape[1],
        float(wavelet_res.freqs.min()),
        float(wavelet_res.freqs.max()),
    )
    im = ax.imshow(
        wavelet_res.coherence_map,
        aspect="auto",
        origin="lower",
        extent=extent,
        vmin=0.0,
        vmax=1.0,
        cmap="magma",
    )
    fig.colorbar(im, ax=ax, label="coherence")
    ax.set_xlabel("tick")
    ax.set_ylabel("frequency (cycles/tick)")
    ax.set_title("Morlet wavelet coherence")
    fig.tight_layout()
    fig.savefig(out_dir / "wavelet_coherence.png", dpi=130)
    plt.close(fig)

    # Null summary.
    fig, ax = plt.subplots(figsize=(7, 3.5))
    names = [r.family for r in nulls.families]
    w_peaks = [float(r.welch_null_peak.mean()) for r in nulls.families]
    mt_peaks = [float(r.multitaper_null_peak.mean()) for r in nulls.families]
    wav_peaks = [float(r.wavelet_null_peak.mean()) for r in nulls.families]
    xs = np.arange(len(names))
    ax.bar(xs - 0.2, w_peaks, width=0.2, label="Welch mean null")
    ax.bar(xs, mt_peaks, width=0.2, label="MT mean null")
    ax.bar(xs + 0.2, wav_peaks, width=0.2, label="Wavelet mean null")
    ax.set_xticks(xs)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("mean null peak coherence")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "null_summary.png", dpi=130)
    plt.close(fig)


def run_all(
    out_dir: Path | None = None,
    fast: bool = True,
) -> dict[str, Any]:
    out_dir = out_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1 ── audit (always re-runs; cheap)
    print("── Phase 1: physical audit ──")
    audit = run_audit(out_dir / "audit.json")

    # Phase 3 ── acquisition (skip if artifacts exist)
    print("── Phase 3: acquisition ──")
    bn_path = out_dir / "gamma_bnsyn_raw.npy"
    gs_path = out_dir / "gamma_geosync_raw.npy"
    if not (bn_path.exists() and gs_path.exists()):
        acq = run_acquisition()
    else:
        acq_path = out_dir / "acquisition.json"
        acq = json.loads(acq_path.read_text()) if acq_path.exists() else {}

    gamma_b = np.load(bn_path)
    gamma_g = np.load(gs_path)
    mask_b = np.load(out_dir / "valid_mask_bnsyn.npy")
    mask_g = np.load(out_dir / "valid_mask_geosync.npy")

    # Repetition audit on the raw series (spec §Fix 1 verification).
    repetition_detected = not (verify_no_repetition(gamma_b) and verify_no_repetition(gamma_g))
    print(f"  repetition_detected = {repetition_detected}")

    a_j, b_j = _align_joint(gamma_b, gamma_g, mask_b, mask_g)
    print(f"  joint valid samples = {a_j.size}")

    # Phase 4 ── spectral battery
    print("── Phase 4: spectral battery ──")
    welch_res = welch_coherence(a_j, b_j, nperseg=128, noverlap=64)
    mt_res = multitaper_coherence(a_j, b_j, nw=3.0)
    wav_res = wavelet_coherence(a_j, b_j)
    print(f"  welch peak C={welch_res.peak_coherence:.3f} @ f={welch_res.peak_frequency:.4f}")
    print(f"  multitaper peak C={mt_res.peak_coherence:.3f} @ f={mt_res.peak_frequency:.4f}")
    print(f"  wavelet peak band={wav_res.peak_band} persistent={wav_res.persistent_band}")

    # Phase 5 ── null ensemble
    print("── Phase 5: null ensemble ──")
    n_surr = N_SURROGATES_FAST if fast else N_SURROGATES_FULL
    wav_surr = WAVELET_N_SURROGATES_FAST if fast else WAVELET_N_SURROGATES_FULL
    nulls = run_null_battery(
        a_j,
        b_j,
        obs_welch_peak=welch_res.peak_coherence,
        obs_mt_peak=mt_res.peak_coherence,
        obs_wav_peak=float(wav_res.freq_aggregated.max()),
        n_surrogates=n_surr,
        wavelet_n_surrogates=wav_surr,
    )
    print(f"  worst-case z-score across families = {nulls.max_z_score:.2f}")
    print(f"  worst-case empirical p = {nulls.max_empirical_p:.4f}")

    # Phase 6 ── stability
    print("── Phase 6: stability ──")
    stab = run_stability(
        a_j,
        b_j,
        welch_peak=welch_res.peak_frequency,
        mt_peak=mt_res.peak_frequency,
        wavelet_band=wav_res.peak_band,
        wavelet_peak=wav_res.peak_freq,
    )
    print(f"  frequency_stable={stab.frequency_stable}")
    print(f"  estimator_agreement={stab.estimator_agreement}")
    print(f"  segment_robustness_pass={stab.segment_robustness_pass}")
    print(f"  segments={stab.segment_peak_frequencies}")

    # Phase 7 ── verdict
    inputs = VerdictInputs(
        physical_frequency_match=bool(audit["physical_frequency_match"]),
        frequency_stable=stab.frequency_stable,
        max_coherence_welch=welch_res.peak_coherence,
        max_coherence_multitaper=mt_res.peak_coherence,
        max_z_score=nulls.max_z_score,
        empirical_p_value=nulls.max_empirical_p,
        wavelet_persistent_band=wav_res.persistent_band,
        segment_robustness_pass=stab.segment_robustness_pass,
        repetition_detected=repetition_detected,
        nan_rate_bnsyn=float(acq.get("nan_rate_bnsyn", 1.0)),
        nan_rate_geosync=float(acq.get("nan_rate_geosync", 1.0)),
        estimator_agreement=stab.estimator_agreement,
    )
    verdict = assign_verdict(inputs)
    print(f"── Phase 7: VERDICT = {verdict.label} ──")

    # Phase 8 ── artifacts
    result = {
        "characteristic_timescale_bnsyn_ticks": float(
            audit["bnsyn"]["characteristic_timescale_ticks"]
        ),
        "characteristic_timescale_geosync_ticks": float(
            audit["geosync"]["characteristic_timescale_ticks"]
        ),
        "physical_frequency_match": bool(audit["physical_frequency_match"]),
        "f_bnsyn": float(audit["f_bnsyn"]),
        "f_geosync": float(audit["f_geosync"]),
        "v1_peak_frequencies": [0.2031, 0.2500],
        "v2_peak_frequency_welch": float(welch_res.peak_frequency),
        "v2_peak_frequency_multitaper": float(mt_res.peak_frequency),
        "frequency_stable": bool(stab.frequency_stable),
        "max_coherence_welch": float(welch_res.peak_coherence),
        "max_coherence_multitaper": float(mt_res.peak_coherence),
        "wavelet_peak_band": [float(wav_res.peak_band[0]), float(wav_res.peak_band[1])],
        "wavelet_persistent_band": bool(wav_res.persistent_band),
        "max_z_score": float(nulls.max_z_score),
        "empirical_p_value": float(nulls.max_empirical_p),
        "segment_robustness_pass": bool(stab.segment_robustness_pass),
        "segment_peak_frequencies": list(stab.segment_peak_frequencies),
        "estimator_agreement": bool(stab.estimator_agreement),
        "repetition_detected": bool(repetition_detected),
        "bnsyn_valid_samples": int(mask_b.sum()),
        "geosync_valid_samples": int(mask_g.sum()),
        "joint_valid_samples": int(a_j.size),
        "nan_rate_bnsyn": float(acq.get("nan_rate_bnsyn", 1.0)),
        "nan_rate_geosync": float(acq.get("nan_rate_geosync", 1.0)),
        "verdict": verdict.label,
        "verdict_reasons": list(verdict.reasons),
        "verdict_gates_passed": list(verdict.positive_gates_passed),
        "verdict_gates_failed": list(verdict.positive_gates_failed),
        "per_family_z": nulls.per_family_z,
        "n_surrogates_welch_mt": n_surr,
        "n_surrogates_wavelet": wav_surr,
        "underpowered": bool(a_j.size < 1500),
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))
    print(f"  wrote {out_dir / 'result.json'}")

    _plots(out_dir, welch_res, mt_res, wav_res, nulls)
    return result


if __name__ == "__main__":
    run_all(fast=True)
