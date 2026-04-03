"""
EEG PhysioNet Motor Movement/Imagery — Real Substrate Adapter
==============================================================
Real human EEG recordings from PhysioNet EEGBCI dataset (Schalk et al., 2004).
109 subjects, 64 EEG channels, motor imagery tasks.

Method:
  1. Load EDF files via MNE for 20 subjects (S001-S020)
  2. Extract motor imagery epochs (runs 4, 8, 12)
  3. Compute PSD per epoch via Welch (2-35 Hz)
  4. Fit aperiodic component via specparam (FOOOF):
     P(f) = b - chi * log(f), where chi = aperiodic exponent
  5. Per-subject mean aperiodic exponent = gamma measurement
  6. Aggregate across subjects: gamma_mean +/- CI95

Mapping (validated with 20 subjects):
  gamma = aperiodic spectral exponent (chi) per subject
  At criticality (active cognitive states): chi ≈ 1.0
  Flatter spectrum = more 1/f-like = closer to critical dynamics

Citation:
  Donoghue et al. (2020) "Parameterizing neural power spectra"
  Schalk et al. (2004) "BCI2000: A General-Purpose BCI System"

γ is DERIVED from real EEG spectral scaling — never assigned.
Formula: γ_PSD = aperiodic exponent = 2H+1 (fBm interpretation)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np

_TOPO_FLOOR = 1e-6
_FREQ_RANGE = (2.0, 35.0)
_EPOCH_DURATION = 4.0  # seconds for good spectral resolution
_N_SUBJECTS_DEFAULT = 20


class EEGPhysioNetAdapter:
    """Real EEG substrate adapter using PhysioNet EEGBCI data.

    Loads motor imagery EEG for N subjects, computes per-epoch aperiodic
    exponent via specparam (FOOOF), aggregates per subject.
    """

    def __init__(
        self,
        n_subjects: int = _N_SUBJECTS_DEFAULT,
        runs: list[int] | None = None,
        data_path: str | None = None,
        seed: int = 42,
    ) -> None:
        self._subjects = list(range(1, n_subjects + 1))
        self._runs = runs or [4, 8, 12]  # motor imagery
        self._data_path = data_path or str(
            Path(__file__).parent.parent.parent / "data" / "eeg_physionet"
        )
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self._loaded = False

        # Per-subject aggregated results
        self._subj_gammas: list[float] = []
        self._subj_ids: list[str] = []
        # Per-epoch raw exponents (for IAAFT)
        self._all_exponents: np.ndarray = np.array([])
        # Grand average PSD for plotting
        self._grand_freqs: np.ndarray = np.array([])
        self._grand_psd: np.ndarray = np.array([])

    def _load(self) -> None:
        """Load EEG data and compute aperiodic exponents."""
        import mne
        from mne.datasets import eegbci
        from specparam import SpectralModel

        mne.set_log_level("ERROR")

        all_exponents = []
        subj_means = []
        all_psds = []

        for subj in self._subjects:
            try:
                fnames = eegbci.load_data(
                    subj, self._runs,
                    path=self._data_path,
                    update_path=False,
                )
            except Exception:
                continue

            subj_exps = []
            for fname in fnames:
                try:
                    raw = mne.io.read_raw_edf(fname, preload=True, verbose=False)
                    eegbci.standardize(raw)
                    raw.filter(1.0, 40.0, verbose=False)

                    events, event_id = mne.events_from_annotations(
                        raw, verbose=False
                    )
                    # Use task epochs (T1=left fist, T2=right fist)
                    task_ids = {k: v for k, v in event_id.items() if k in ["T1", "T2"]}
                    if not task_ids:
                        # Fallback: use all events
                        events = mne.make_fixed_length_events(
                            raw, duration=_EPOCH_DURATION
                        )
                        task_ids = None

                    epochs = mne.Epochs(
                        raw, events,
                        event_id=task_ids,
                        tmin=0, tmax=_EPOCH_DURATION,
                        baseline=None, preload=True, verbose=False,
                    )
                    if len(epochs) < 3:
                        continue

                    psd_obj = epochs.compute_psd(
                        method="welch",
                        fmin=_FREQ_RANGE[0],
                        fmax=_FREQ_RANGE[1],
                        verbose=False,
                    )
                    psds = psd_obj.get_data()  # (n_epochs, n_channels, n_freqs)
                    freqs = psd_obj.freqs

                    for ep_idx in range(psds.shape[0]):
                        psd_mean = psds[ep_idx].mean(axis=0)
                        all_psds.append(psd_mean)
                        try:
                            sm = SpectralModel(
                                peak_width_limits=[1.0, 8.0],
                                max_n_peaks=4,
                                aperiodic_mode="fixed",
                            )
                            sm.fit(freqs, psd_mean, [2, 35])
                            exp = float(sm.results.params.aperiodic.params[1])
                            if np.isfinite(exp) and 0 < exp < 5:
                                subj_exps.append(exp)
                                all_exponents.append(exp)
                        except Exception:
                            pass

                except Exception:
                    continue

            if subj_exps:
                mean_exp = float(np.mean(subj_exps))
                self._subj_gammas.append(mean_exp)
                self._subj_ids.append(f"S{subj:03d}")
                subj_means.append(mean_exp)

        self._all_exponents = np.array(all_exponents)
        if all_psds:
            self._grand_freqs = freqs
            self._grand_psd = np.mean(all_psds, axis=0)

        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()
            if len(self._subj_gammas) < 3:
                raise RuntimeError(
                    f"Insufficient EEG data: {len(self._subj_gammas)} subjects. "
                    f"Searched: {self._data_path}"
                )

    @property
    def domain(self) -> str:
        return "eeg_physionet"

    @property
    def state_keys(self) -> List[str]:
        return ["aperiodic_exponent", "n_subjects", "n_epochs"]

    def state(self) -> Dict[str, float]:
        self._ensure_loaded()
        return {
            "aperiodic_exponent": float(np.mean(self._subj_gammas)),
            "n_subjects": float(len(self._subj_gammas)),
            "n_epochs": float(len(self._all_exponents)),
        }

    def topo(self) -> float:
        """Not used directly — use get_gamma_result() instead."""
        self._ensure_loaded()
        idx = int(self._rng.integers(0, len(self._all_exponents)))
        return max(_TOPO_FLOOR, float(self._all_exponents[idx]))

    def thermo_cost(self) -> float:
        """Not used directly — use get_gamma_result() instead."""
        return 1.0 / self.topo()

    def get_gamma_result(self) -> dict:
        """Compute gamma statistics across subjects.

        Returns dict with gamma, ci, r2, n, verdict.
        """
        self._ensure_loaded()
        arr = np.array(self._subj_gammas)
        gamma = float(np.mean(arr))

        # Bootstrap CI95
        rng = np.random.default_rng(self._seed)
        boots = np.array([
            float(np.mean(rng.choice(arr, len(arr))))
            for _ in range(2000)
        ])
        ci_low = float(np.percentile(boots, 2.5))
        ci_high = float(np.percentile(boots, 97.5))

        # R2: how well do individual subjects cluster around mean
        ss_tot = float(np.sum((arr - np.mean(arr)) ** 2))
        r2 = 1.0 - ss_tot / (len(arr) * np.var(arr)) if np.var(arr) > 0 else 0.0
        # For per-subject analysis, R2 is not the standard metric; use mean/sd instead

        dist = abs(gamma - 1.0)
        if dist < 0.15:
            verdict = "METASTABLE"
        elif dist < 0.30:
            verdict = "WARNING"
        elif dist < 0.50:
            verdict = "CRITICAL"
        else:
            verdict = "COLLAPSE"

        return {
            "gamma": round(gamma, 4),
            "ci_low": round(ci_low, 4),
            "ci_high": round(ci_high, 4),
            "ci_contains_unity": ci_low <= 1.0 <= ci_high,
            "n_subjects": len(arr),
            "n_epochs": len(self._all_exponents),
            "std": round(float(np.std(arr)), 4),
            "verdict": verdict,
            "per_subject": [
                {"id": sid, "gamma": round(g, 4)}
                for sid, g in zip(self._subj_ids, self._subj_gammas)
            ],
        }

    def get_all_exponents(self) -> np.ndarray:
        """Return all per-epoch aperiodic exponents for IAAFT analysis."""
        self._ensure_loaded()
        return self._all_exponents.copy()

    def get_grand_average_psd(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (freqs, psd) grand average for plotting."""
        self._ensure_loaded()
        return self._grand_freqs.copy(), self._grand_psd.copy()

    def get_all_pairs(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (freqs, grand_avg_psd) for compute_gamma() compatibility."""
        return self.get_grand_average_psd()


def validate_standalone() -> dict:
    """Compute gamma for EEG PhysioNet substrate."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    print("=== EEG PhysioNet — Motor Imagery Validation ===\n")
    print("Loading EEG data for 20 subjects...\n")

    adapter = EEGPhysioNetAdapter(n_subjects=20)
    result = adapter.get_gamma_result()

    print(f"  Subjects: {result['n_subjects']}")
    print(f"  Epochs: {result['n_epochs']}")
    print(f"  gamma (mean aperiodic exp) = {result['gamma']:.4f}")
    print(f"  CI95 = [{result['ci_low']:.4f}, {result['ci_high']:.4f}]")
    print(f"  CI contains 1.0: {result['ci_contains_unity']}")
    print(f"  verdict = {result['verdict']}")

    print("\n  Per-subject:")
    for s in result["per_subject"]:
        print(f"    {s['id']}: gamma={s['gamma']:.4f}")

    return result


if __name__ == "__main__":
    validate_standalone()
