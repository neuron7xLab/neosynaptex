"""Phase 5 — null ensemble (five families × surrogates per estimator).

Each null family defines a transformation of the input pair that
destroys genuine phase coupling while (ideally) preserving marginal
spectral content. A positive verdict must survive every family.

Families
--------
1. phase-randomized   — randomize phases of A, keep its amplitude
                         spectrum; coherence(A_surr, B) must be low.
2. time-shuffled      — random permutation of A in time; destroys
                         both phase AND amplitude structure.
3. circular-shift     — random integer shift of A modulo length;
                         preserves all statistics, destroys alignment.
4. cross-run mismatch — replace A with an independent second run
                         of the same substrate (different seed).
5. time-reversed      — reverse the time axis of A; physical causality
                         breaks.

Wavelet surrogates are expensive, so the wavelet estimator uses
`wavelet_n_surrogates` (default 200) per family while Welch and
multi-taper use the full `n_surrogates` (default 1000).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from experiments.spectral_coherence_v3.spectral_battery import (
    multitaper_coherence,
    wavelet_coherence,
    welch_coherence,
)

__all__ = [
    "NullFamilyResult",
    "NullBatteryResult",
    "run_null_battery",
    "phase_randomize",
    "time_shuffle",
    "circular_shift",
    "time_reverse",
]


# ── Surrogate generators ──────────────────────────────────────────────


def phase_randomize(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    X = np.fft.rfft(x)
    phases = rng.uniform(0.0, 2.0 * np.pi, size=X.shape)
    phases[0] = 0.0
    if len(x) % 2 == 0:
        phases[-1] = 0.0
    X_rand = np.abs(X) * np.exp(1j * phases)
    return np.fft.irfft(X_rand, n=len(x))


def time_shuffle(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    return rng.permutation(x)


def circular_shift(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    k = int(rng.integers(1, len(x)))
    return np.roll(x, k)


def time_reverse(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:  # noqa: ARG001
    return x[::-1].copy()


# ── Batteries ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NullFamilyResult:
    family: str
    welch_null_peak: np.ndarray
    multitaper_null_peak: np.ndarray
    wavelet_null_peak: np.ndarray
    welch_z: float
    welch_p: float
    multitaper_z: float
    multitaper_p: float
    wavelet_z: float
    wavelet_p: float


@dataclass(frozen=True)
class NullBatteryResult:
    families: tuple[NullFamilyResult, ...]
    max_z_score: float
    max_empirical_p: float
    per_family_z: dict[str, float] = field(default_factory=dict)


def _empirical_z_p(obs: float, null: np.ndarray) -> tuple[float, float]:
    """Return (z, empirical_p) of ``obs`` against ``null``.

    Special case: when the null has effectively zero variance (e.g. a
    deterministic transform like time-reversal repeated N times), the
    z-score is not well-defined — we return NaN so the verdict
    aggregator can skip it rather than let a 1/ε blow-up dominate.
    """
    if null.size == 0:
        return float("nan"), 1.0
    mu = float(null.mean())
    sd = float(null.std())
    if sd < 1e-9:
        p = 0.0 if obs > mu + 1e-9 else 1.0
        return float("nan"), float(p)
    z = (obs - mu) / sd
    p = float((null >= obs).mean())
    return float(z), float(p)


def _run_family(
    name: str,
    transform: Callable[[np.ndarray, np.random.Generator], np.ndarray],
    a: np.ndarray,
    b: np.ndarray,
    obs_welch: float,
    obs_mt: float,
    obs_wav: float,
    n_surrogates: int,
    wavelet_n: int,
    rng: np.random.Generator,
    cross_run_a: np.ndarray | None = None,
) -> NullFamilyResult:
    """Run one null family across all three estimators."""
    w_nulls = np.empty(n_surrogates, dtype=np.float64)
    mt_nulls = np.empty(n_surrogates, dtype=np.float64)
    for i in range(n_surrogates):
        if name == "cross_run_mismatch" and cross_run_a is not None:
            a_s = cross_run_a
        else:
            a_s = transform(a, rng)
        w_nulls[i] = welch_coherence(a_s, b).peak_coherence
        mt_nulls[i] = multitaper_coherence(a_s, b).peak_coherence

    wav_nulls = np.empty(wavelet_n, dtype=np.float64)
    for i in range(wavelet_n):
        if name == "cross_run_mismatch" and cross_run_a is not None:
            a_s = cross_run_a
        else:
            a_s = transform(a, rng)
        wav_nulls[i] = float(wavelet_coherence(a_s, b).freq_aggregated.max())

    w_z, w_p = _empirical_z_p(obs_welch, w_nulls)
    mt_z, mt_p = _empirical_z_p(obs_mt, mt_nulls)
    wav_z, wav_p = _empirical_z_p(obs_wav, wav_nulls)
    return NullFamilyResult(
        family=name,
        welch_null_peak=w_nulls,
        multitaper_null_peak=mt_nulls,
        wavelet_null_peak=wav_nulls,
        welch_z=w_z,
        welch_p=w_p,
        multitaper_z=mt_z,
        multitaper_p=mt_p,
        wavelet_z=wav_z,
        wavelet_p=wav_p,
    )


def run_null_battery(
    a: np.ndarray,
    b: np.ndarray,
    obs_welch_peak: float,
    obs_mt_peak: float,
    obs_wav_peak: float,
    n_surrogates: int = 1000,
    wavelet_n_surrogates: int = 200,
    seed: int = 0xC0DECAFE,
    cross_run_a: np.ndarray | None = None,
) -> NullBatteryResult:
    rng = np.random.default_rng(seed)
    families = [
        ("phase_randomized", phase_randomize),
        ("time_shuffled", time_shuffle),
        ("circular_shift", circular_shift),
        ("time_reversed", time_reverse),
    ]
    results: list[NullFamilyResult] = []
    for name, transform in families:
        results.append(
            _run_family(
                name,
                transform,
                a,
                b,
                obs_welch_peak,
                obs_mt_peak,
                obs_wav_peak,
                n_surrogates,
                wavelet_n_surrogates,
                rng,
            )
        )

    # Cross-run mismatch uses the supplied independent γ trace if present.
    if cross_run_a is not None:
        results.append(
            _run_family(
                "cross_run_mismatch",
                lambda x, r: cross_run_a,  # noqa: ARG005 — placeholder
                a,
                b,
                obs_welch_peak,
                obs_mt_peak,
                obs_wav_peak,
                min(n_surrogates, 200),  # single deterministic value; few copies
                min(wavelet_n_surrogates, 50),
                rng,
                cross_run_a=cross_run_a,
            )
        )

    def _family_max(r: NullFamilyResult) -> float:
        finite = [z for z in (r.welch_z, r.multitaper_z, r.wavelet_z) if np.isfinite(z)]
        return max(finite) if finite else float("nan")

    per_family_z = {r.family: _family_max(r) for r in results}
    finite_z = [z for z in per_family_z.values() if np.isfinite(z)]
    # Global worst-case (best null) — the positive must beat every family.
    min_z = min(finite_z) if finite_z else 0.0
    max_p = max(max(r.welch_p, r.multitaper_p, r.wavelet_p) for r in results)
    return NullBatteryResult(
        families=tuple(results),
        max_z_score=float(min_z),  # worst-case z across families
        max_empirical_p=float(max_p),
        per_family_z=per_family_z,
    )
