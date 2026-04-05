"""
HRV Fantasia — PhysioNet T1 Substrate Adapter
==============================================

Second, **independent** T1 wild-empirical cardiac witness alongside the
existing ``substrates/hrv_physionet`` (NSR2DB, VLF spectral exponent).
This adapter uses the **Fantasia Database** (Iyengar et al. 1996) and
a completely orthogonal pipeline:

  * **Data:** 10 healthy young subjects (f1y01–f1y10), 120 minutes of
    continuous ECG at 250 Hz, public license ODC-By.
  * **Pipeline:** Detrended Fluctuation Analysis (Peng et al. 1995) of
    the normal-beat RR-interval series on long-time scales (16–64 beats),
    giving the DFA α exponent. Healthy cardiac rhythm gives α ≈ 1 by
    construction of the critical-brain / entropic-body hypothesis.

Rationale for the redundancy with ``hrv_physionet``
---------------------------------------------------
Two databases (Fantasia vs NSR2DB), two methods (DFA α vs VLF PSD slope),
two population ages (young vs all-adult), all giving γ ≈ 1 would be
a strong cross-validation of the cardiac 1/f claim. One passing and
one failing would be a **finding** worth recording.

No parameter in the DFA pipeline is tuned:

  * Scale range [16, 64] beats is the canonical long-scale region
    (Peng 1995, Goldberger 2002) — α₂ in the HRV literature.
  * Segment detrending is linear (degree-1 polynomial) — standard.
  * Bootstrap n = 2000, seed = 42.

The short-scale α₁ ([4, 16] beats) is also computed for cross-check
but the primary γ value is α₂.

Dependencies
------------
Requires ``wfdb`` for PhysioNet annotation loading. ``wfdb`` is an
optional dev dependency, not a core requirement. The adapter imports
it lazily, and the tests in ``tests/test_hrv_fantasia_substrate.py``
skip gracefully when ``wfdb`` is absent from CI.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Pipeline constants — published HRV DFA convention, not tuned
# ---------------------------------------------------------------------------
_N_SUBJECTS_DEFAULT = 10
_RR_MIN_S = 0.3  # physiological floor for RR (200 bpm)
_RR_MAX_S = 2.0  # physiological ceiling (30 bpm)
_DFA_SHORT_RANGE = (4, 16)  # α₁ — parasympathetic (HF)
_DFA_LONG_RANGE = (16, 64)  # α₂ — 1/f regime, primary γ
_MIN_BEATS = 1000
_BOOTSTRAP_N = 2000

_DATA_BASE = Path(__file__).parent.parent.parent / "data" / "fantasia"


def _dfa_alpha(rr: np.ndarray, scales: np.ndarray) -> float:
    """Detrended Fluctuation Analysis scaling exponent (Peng 1995).

    ``rr`` is the RR-interval series (seconds). Returns the log-log
    slope of the fluctuation function F(n) vs segment size n over the
    provided ``scales``. NaN if fewer than 3 valid scales.
    """
    y = np.cumsum(rr - np.mean(rr))
    n_total = len(y)
    F: list[float] = []
    used: list[int] = []
    for s in scales:
        s = int(s)
        if s < 4 or s > n_total // 4:
            continue
        n_seg = n_total // s
        f_sum = 0.0
        for seg in range(n_seg):
            segment = y[seg * s : (seg + 1) * s]
            x_fit = np.arange(s, dtype=np.float64)
            coeffs = np.polyfit(x_fit, segment, 1)
            trend = np.polyval(coeffs, x_fit)
            f_sum += float(np.mean((segment - trend) ** 2))
        F.append(math.sqrt(f_sum / n_seg))
        used.append(s)
    if len(F) < 3:
        return float("nan")
    log_s = np.log(np.asarray(used, dtype=np.float64))
    log_f = np.log(np.asarray(F, dtype=np.float64) + 1e-10)
    return float(np.polyfit(log_s, log_f, 1)[0])


class HRVFantasiaAdapter:
    """Fantasia HRV adapter — DFA α exponent on the young cohort.

    Parameters
    ----------
    n_subjects : int, default 10
        How many young subjects (f1y01 … f1yNN) to load.
    data_path : str | Path | None
        Override the local Fantasia directory. Defaults to the
        repository-standard ``data/fantasia/``.
    seed : int, default 42
        Seed for the bootstrap CI.
    """

    def __init__(
        self,
        n_subjects: int = _N_SUBJECTS_DEFAULT,
        data_path: str | Path | None = None,
        seed: int = 42,
    ) -> None:
        self._n_subjects = int(n_subjects)
        self._data_path = Path(data_path) if data_path is not None else _DATA_BASE
        self._seed = int(seed)
        self._rng = np.random.default_rng(seed)
        self._loaded = False

        self._subj_ids: list[str] = []
        self._alpha1_per_subj: list[float] = []  # short-scale
        self._alpha2_per_subj: list[float] = []  # long-scale (primary)
        self._rr_counts: list[int] = []

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _load(self) -> None:
        try:
            import wfdb  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise ModuleNotFoundError(
                "substrates.hrv_fantasia requires `wfdb` to load PhysioNet "
                "annotations. Install via `pip install wfdb` (dev dependency)."
            ) from exc

        scales_short = np.unique(
            np.round(
                np.logspace(
                    math.log10(_DFA_SHORT_RANGE[0]),
                    math.log10(_DFA_SHORT_RANGE[1]),
                    6,
                )
            ).astype(int)
        )
        scales_long = np.unique(
            np.round(
                np.logspace(
                    math.log10(_DFA_LONG_RANGE[0]),
                    math.log10(_DFA_LONG_RANGE[1]),
                    6,
                )
            ).astype(int)
        )

        for i in range(1, self._n_subjects + 1):
            subj = f"f1y{i:02d}"
            hea = self._data_path / f"{subj}.hea"
            ecg = self._data_path / f"{subj}.ecg"
            if not hea.exists() or not ecg.exists():
                continue
            try:
                hdr = wfdb.rdheader(str(self._data_path / subj))
                ann = wfdb.rdann(str(self._data_path / subj), "ecg")
                normal = ann.sample[np.asarray(ann.symbol) == "N"]
                if len(normal) < _MIN_BEATS:
                    continue
                rr = np.diff(normal) / float(hdr.fs)
                rr = rr[(rr > _RR_MIN_S) & (rr < _RR_MAX_S)]
                if len(rr) < _MIN_BEATS:
                    continue
                a1 = _dfa_alpha(rr, scales_short)
                a2 = _dfa_alpha(rr, scales_long)
                if math.isfinite(a1) and math.isfinite(a2):
                    self._subj_ids.append(subj)
                    self._alpha1_per_subj.append(a1)
                    self._alpha2_per_subj.append(a2)
                    self._rr_counts.append(int(len(rr)))
            except Exception:
                continue

        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()
            if len(self._alpha2_per_subj) < 3:
                raise RuntimeError(
                    f"Insufficient Fantasia data: "
                    f"{len(self._alpha2_per_subj)} subjects loaded from "
                    f"{self._data_path}. Need ≥ 3 for a bootstrap CI."
                )

    # ------------------------------------------------------------------
    # DomainAdapter protocol
    # ------------------------------------------------------------------
    @property
    def domain(self) -> str:
        return "hrv_fantasia"

    @property
    def state_keys(self) -> list[str]:
        return ["dfa_alpha2", "dfa_alpha1", "n_subjects"]

    def state(self) -> dict[str, float]:
        self._ensure_loaded()
        return {
            "dfa_alpha2": float(np.mean(self._alpha2_per_subj)),
            "dfa_alpha1": float(np.mean(self._alpha1_per_subj)),
            "n_subjects": float(len(self._alpha2_per_subj)),
        }

    def topo(self) -> float:
        """Random per-subject α₂ (engine compatibility)."""
        self._ensure_loaded()
        if not self._alpha2_per_subj:
            return 1e-6
        idx = int(self._rng.integers(0, len(self._alpha2_per_subj)))
        return max(1e-6, float(self._alpha2_per_subj[idx]))

    def thermo_cost(self) -> float:
        """Dual scaling: 1/α₂."""
        t = self.topo()
        return max(1e-6, 1.0 / t) if t > 1e-6 else 1e6

    # ------------------------------------------------------------------
    # γ aggregation
    # ------------------------------------------------------------------
    def compute_gamma(self) -> dict:
        """Return γ = α₂ (long-scale DFA) with bootstrap CI95."""
        self._ensure_loaded()
        arr = np.asarray(self._alpha2_per_subj, dtype=np.float64)
        arr1 = np.asarray(self._alpha1_per_subj, dtype=np.float64)
        gamma = float(np.mean(arr))
        sd = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
        rng = np.random.default_rng(self._seed)
        boot = np.array(
            [
                float(np.mean(rng.choice(arr, size=arr.size, replace=True)))
                for _ in range(_BOOTSTRAP_N)
            ]
        )
        ci_low = float(np.percentile(boot, 2.5))
        ci_high = float(np.percentile(boot, 97.5))

        dist = abs(gamma - 1.0)
        verdict = (
            "METASTABLE"
            if dist < 0.15
            else "WARNING"
            if dist < 0.30
            else "CRITICAL"
            if dist < 0.50
            else "COLLAPSE"
        )
        return {
            "gamma": round(gamma, 4),
            "ci_low": round(ci_low, 4),
            "ci_high": round(ci_high, 4),
            "ci_contains_unity": bool(ci_low <= 1.0 <= ci_high),
            "std": round(sd, 4),
            "n_subjects": int(arr.size),
            "alpha1_mean": round(float(np.mean(arr1)), 4),
            "alpha1_std": round(float(np.std(arr1, ddof=1)), 4) if arr1.size > 1 else 0.0,
            "method": ("Detrended Fluctuation Analysis, long-scale α₂ (16–64 beats, Peng 1995)"),
            "verdict": verdict,
            "per_subject": [
                {
                    "id": sid,
                    "alpha2": round(float(a2), 4),
                    "alpha1": round(float(a1), 4),
                    "n_rr": int(n),
                }
                for sid, a1, a2, n in zip(
                    self._subj_ids,
                    self._alpha1_per_subj,
                    self._alpha2_per_subj,
                    self._rr_counts,
                    strict=False,
                )
            ],
        }


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------
def run_gamma_analysis(n_subjects: int = _N_SUBJECTS_DEFAULT, seed: int = 42) -> dict:
    print("=== HRV Fantasia (PhysioNet) — DFA α on young cohort ===\n")
    print(f"  subjects: f1y01..f1y{n_subjects:02d}")
    print("  method:   DFA α₂ on RR intervals, scales 16–64 beats\n")
    adapter = HRVFantasiaAdapter(n_subjects=n_subjects, seed=seed)
    result = adapter.compute_gamma()
    print(f"  γ (α₂)      = {result['gamma']:.4f}")
    print(f"  α₁ (short)  = {result['alpha1_mean']:.4f} ± {result['alpha1_std']:.4f}")
    print(f"  CI95        = [{result['ci_low']:.4f}, {result['ci_high']:.4f}]")
    print(f"  CI contains 1.0: {result['ci_contains_unity']}")
    print(f"  n_subjects  = {result['n_subjects']}")
    print(f"  verdict     = {result['verdict']}")
    print("\n  Per-subject:")
    for s in result["per_subject"]:
        print(f"    {s['id']}: α₂={s['alpha2']:.4f} α₁={s['alpha1']:.4f} n_rr={s['n_rr']}")
    return result


if __name__ == "__main__":
    run_gamma_analysis()
