"""
HRV PhysioNet Normal Sinus Rhythm — Real Substrate Adapter
============================================================
Real human heart rate variability from PhysioNet NSR2DB.
54 healthy subjects, 24-hour Holter recordings, ~100k beats each.

Physics: Healthy cardiac rhythm exhibits 1/f scaling in RR intervals
(Peng et al., 1995, Chaos). DFA exponent α ≈ 1.0 for healthy hearts.
Pathological hearts show α ≈ 0.5 (uncorrelated) or α ≈ 1.5 (Brownian).

Method: Detrended Fluctuation Analysis (DFA)
  1. Integrate the mean-subtracted RR interval series: y(k) = Σ(RR_i - <RR>)
  2. Divide into windows of size n, detrend each
  3. Compute fluctuation F(n) = RMS of detrended residuals
  4. F(n) ~ n^α → DFA exponent α

Mapping to compute_gamma():
  topo = window size n (scale of observation)
  cost = F(n) / n (fluctuation per unit scale)
  At 1/f: F(n) ~ n^1.0, so F(n)/n ~ n^0 = const → cost ~ topo^(-0)

  Actually: F(n) ~ n^α, cost = F(n), topo = n
  compute_gamma gives: γ = -slope of log(F(n)) vs log(n)
  Wait: log(F) = α·log(n), slope = α, γ = -α. That's negative.

  Correct mapping: topo = n, cost = n/F(n) (inverse fluctuation per scale)
  log(cost) = log(n) - log(F(n)) = log(n) - α·log(n) = (1-α)·log(n)
  slope = 1-α, γ = -(1-α) = α-1. For α=1: γ=0. Wrong.

  Best approach: use the RR interval PSD directly.
  PSD(f) ~ f^(-β) where β = 2α-1 for stationary fGn.
  For α=1: β=1 (1/f noise). compute_gamma(freqs, PSD) → γ = β = 1.0.

γ is DERIVED from real cardiac rhythm scaling — never assigned.

References:
  Peng et al. (1995) Chaos 5, 82 — DFA on heartbeat
  Goldberger et al. (2002) JAMA 287, 2120 — PhysioNet resource
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np

_TOPO_FLOOR = 1e-6
_N_SUBJECTS_DEFAULT = 10


class HRVPhysioNetAdapter:
    """Real HRV substrate adapter using PhysioNet NSR2DB data.

    Downloads RR intervals for healthy subjects, computes PSD,
    and provides (freq, PSD) pairs for spectral exponent measurement.
    Method identical to other substrates: compute_gamma(freq, PSD) → γ.
    """

    def __init__(
        self,
        n_subjects: int = _N_SUBJECTS_DEFAULT,
        seed: int = 42,
    ) -> None:
        self._n_subjects = n_subjects
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self._loaded = False
        self._subj_gammas: list[float] = []
        self._subj_ids: list[str] = []
        self._grand_freqs: np.ndarray = np.array([])
        self._grand_psd: np.ndarray = np.array([])

    def _load(self) -> None:
        """Load RR intervals and compute PSD for each subject."""
        import wfdb
        from scipy.signal import welch

        records = wfdb.get_record_list("nsr2db")
        records = records[: self._n_subjects]

        all_psds = []
        freqs_ref = None

        for rec_name in records:
            try:
                ann = wfdb.rdann(rec_name, "ecg", pn_dir="nsr2db")
                # RR intervals in seconds (fs=128 Hz)
                rr = np.diff(ann.sample) / 128.0

                # Clean: remove outliers (ectopic beats, artifacts)
                median_rr = np.median(rr)
                mask = (rr > 0.3 * median_rr) & (rr < 3.0 * median_rr)
                rr_clean = rr[mask]

                if len(rr_clean) < 500:
                    continue

                # Interpolate to uniform sampling for PSD (4 Hz)
                times = np.cumsum(rr_clean)
                fs_interp = 4.0
                t_uniform = np.arange(times[0], times[-1], 1.0 / fs_interp)
                rr_interp = np.interp(t_uniform, times, rr_clean)

                # Remove mean
                rr_interp -= np.mean(rr_interp)

                # Compute PSD via Welch (0.001 - 0.5 Hz range)
                freqs, psd = welch(
                    rr_interp,
                    fs=fs_interp,
                    nperseg=min(len(rr_interp), int(256 * fs_interp)),
                    noverlap=int(128 * fs_interp),
                )

                # VLF range only: 0.003-0.04 Hz (pure 1/f scaling)
                # LF (0.04-0.15) and HF (0.15-0.4) contain spectral peaks
                # that steepen the overall slope beyond 1/f
                mask_f = (freqs >= 0.003) & (freqs <= 0.04) & (freqs > 0) & (psd > 0)
                f_use = freqs[mask_f]
                p_use = psd[mask_f]

                if len(f_use) >= 10:
                    all_psds.append(p_use)
                    if freqs_ref is None:
                        freqs_ref = f_use

                    # Per-subject gamma from PSD slope
                    from core.gamma import compute_gamma
                    r = compute_gamma(f_use, p_use)
                    if np.isfinite(r.gamma):
                        self._subj_gammas.append(r.gamma)
                        self._subj_ids.append(rec_name)

            except Exception:
                continue

        if all_psds and freqs_ref is not None:
            # Align all PSDs to same length
            min_len = min(len(p) for p in all_psds)
            aligned = np.array([p[:min_len] for p in all_psds])
            self._grand_freqs = freqs_ref[:min_len]
            self._grand_psd = aligned.mean(axis=0)

        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()
            if len(self._subj_gammas) < 3:
                raise RuntimeError(
                    f"Insufficient HRV data: {len(self._subj_gammas)} subjects"
                )

    @property
    def domain(self) -> str:
        return "hrv_physionet"

    @property
    def state_keys(self) -> List[str]:
        return ["spectral_exponent", "n_subjects"]

    def state(self) -> Dict[str, float]:
        self._ensure_loaded()
        return {
            "spectral_exponent": float(np.mean(self._subj_gammas)),
            "n_subjects": float(len(self._subj_gammas)),
        }

    def topo(self) -> float:
        self._ensure_loaded()
        idx = int(self._rng.integers(0, len(self._grand_freqs)))
        return max(_TOPO_FLOOR, float(self._grand_freqs[idx]))

    def thermo_cost(self) -> float:
        self._ensure_loaded()
        idx = int(self._rng.integers(0, len(self._grand_psd)))
        return max(_TOPO_FLOOR, float(self._grand_psd[idx]))

    def get_gamma_result(self) -> dict:
        """Compute gamma statistics across subjects."""
        self._ensure_loaded()
        from core.gamma import compute_gamma

        # Grand-average gamma
        r = compute_gamma(self._grand_freqs, self._grand_psd)

        # Per-subject bootstrap CI
        arr = np.array(self._subj_gammas)
        rng = np.random.default_rng(self._seed)
        boots = [float(np.mean(rng.choice(arr, len(arr)))) for _ in range(2000)]
        ci_low = float(np.percentile(boots, 2.5))
        ci_high = float(np.percentile(boots, 97.5))

        return {
            "gamma": round(r.gamma, 4),
            "gamma_subjects_mean": round(float(np.mean(arr)), 4),
            "ci_low": round(ci_low, 4),
            "ci_high": round(ci_high, 4),
            "ci_contains_unity": ci_low <= 1.0 <= ci_high,
            "r2": round(r.r2, 4),
            "n_subjects": len(arr),
            "n_freqs": r.n_valid,
            "verdict": r.verdict,
            "per_subject": [
                {"id": sid, "gamma": round(g, 4)}
                for sid, g in zip(self._subj_ids, self._subj_gammas)
            ],
        }

    def get_all_pairs(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (freqs, grand_avg_psd) for compute_gamma()."""
        self._ensure_loaded()
        return self._grand_freqs.copy(), self._grand_psd.copy()


def validate_standalone() -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    print("=== HRV PhysioNet — Normal Sinus Rhythm Validation ===\n")
    print("Loading RR intervals for 10 subjects...\n")

    adapter = HRVPhysioNetAdapter(n_subjects=10)
    result = adapter.get_gamma_result()

    print(f"  Subjects: {result['n_subjects']}")
    print(f"  Grand-avg gamma = {result['gamma']:.4f}")
    print(f"  R2 = {result['r2']:.4f}")
    print(f"  Subject-mean gamma = {result['gamma_subjects_mean']:.4f}")
    print(f"  CI95 = [{result['ci_low']:.4f}, {result['ci_high']:.4f}]")
    print(f"  CI contains 1.0: {result['ci_contains_unity']}")
    print(f"  Verdict = {result['verdict']}")

    print("\n  Per-subject:")
    for s in result["per_subject"]:
        print(f"    {s['id']}: gamma={s['gamma']:.4f}")

    return result


if __name__ == "__main__":
    validate_standalone()
