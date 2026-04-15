"""Cohort-scale γ-fit runner — batch per-subject VLF γ-fit from cache.

Walks ``(cohort, record)`` pairs, loads each cached RR array from
``data/raw/{cohort}/{record}.rr.npy``, and applies
``substrates.physionet_hrv.hrv_gamma_fit.fit_hrv_gamma`` per subject
with the pilot's canonical parameters (Welch nperseg=1024, VLF band
[0.003, 0.04] Hz, Theil-Sen slope, bootstrap CI on top of the
non-parametric CI).

Returns a list of :class:`GammaSubject` records suitable for the
§5.3 full-cohort γ analysis in the preprint skeleton.

Design rules
------------
- Offline only. No PhysioNet traffic.
- Missing cache, too-short records, and fit failures are reported
  as distinct statuses — never silently dropped.
- Deterministic: same cached arrays + same parameters ⇒ bitwise
  reproducible per-subject γ values.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from substrates.physionet_hrv.hrv_gamma_fit import fit_hrv_gamma

__all__ = ["GammaSubject", "load_rr_cache", "run_cohort_gamma"]


@dataclasses.dataclass(frozen=True)
class GammaSubject:
    cohort: str
    record: str
    status: str  # "ok" | "missing_cache" | "too_short" | "gamma_fit_error"
    n_rr: int
    gamma: float | None
    gamma_ci_low: float | None
    gamma_ci_high: float | None
    r2: float | None
    n_frequencies_fit: int | None
    error: str | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "cohort": self.cohort,
            "record": self.record,
            "status": self.status,
            "n_rr": self.n_rr,
            "gamma": None if self.gamma is None else round(self.gamma, 4),
            "gamma_ci95": (
                None
                if self.gamma_ci_low is None or self.gamma_ci_high is None
                else [round(self.gamma_ci_low, 4), round(self.gamma_ci_high, 4)]
            ),
            "r2": None if self.r2 is None else round(self.r2, 4),
            "n_frequencies_fit": self.n_frequencies_fit,
            "error": self.error,
        }


def load_rr_cache(cohort: str, record: str, cache_dir: Path) -> np.ndarray | None:
    path = cache_dir / cohort / f"{record}.rr.npy"
    if not path.exists():
        return None
    return np.load(path, allow_pickle=False)


def _run_one(
    cohort: str,
    record: str,
    rr: np.ndarray | None,
    *,
    rr_truncate: int,
    fit_lo_hz: float,
    fit_hi_hz: float,
    nperseg: int,
    bootstrap_n: int,
    seed: int,
) -> GammaSubject:
    if rr is None:
        return GammaSubject(
            cohort=cohort,
            record=record,
            status="missing_cache",
            n_rr=0,
            gamma=None,
            gamma_ci_low=None,
            gamma_ci_high=None,
            r2=None,
            n_frequencies_fit=None,
        )
    rr = rr[:rr_truncate]
    if rr.size < nperseg // 2:
        return GammaSubject(
            cohort=cohort,
            record=record,
            status="too_short",
            n_rr=int(rr.size),
            gamma=None,
            gamma_ci_low=None,
            gamma_ci_high=None,
            r2=None,
            n_frequencies_fit=None,
        )
    try:
        fit = fit_hrv_gamma(
            rr,
            fit_lo_hz=fit_lo_hz,
            fit_hi_hz=fit_hi_hz,
            nperseg=nperseg,
            bootstrap_n=bootstrap_n,
            seed=seed,
        )
    except Exception as exc:  # noqa: BLE001 — record + continue
        return GammaSubject(
            cohort=cohort,
            record=record,
            status="gamma_fit_error",
            n_rr=int(rr.size),
            gamma=None,
            gamma_ci_low=None,
            gamma_ci_high=None,
            r2=None,
            n_frequencies_fit=None,
            error=f"{type(exc).__name__}: {exc}",
        )
    return GammaSubject(
        cohort=cohort,
        record=record,
        status="ok",
        n_rr=int(rr.size),
        gamma=float(fit.gamma),
        gamma_ci_low=float(fit.ci_low),
        gamma_ci_high=float(fit.ci_high),
        r2=float(fit.r2),
        n_frequencies_fit=int(fit.n_frequencies_fit),
    )


def run_cohort_gamma(
    cohort_records: Iterable[tuple[str, str]],
    *,
    cache_dir: Path,
    rr_truncate: int = 20000,
    fit_lo_hz: float = 0.003,
    fit_hi_hz: float = 0.04,
    nperseg: int = 1024,
    bootstrap_n: int = 500,
    seed: int = 42,
) -> list[GammaSubject]:
    """Batch per-subject γ-fit over ``(cohort, record)`` pairs."""

    return [
        _run_one(
            cohort,
            record,
            load_rr_cache(cohort, record, cache_dir),
            rr_truncate=rr_truncate,
            fit_lo_hz=fit_lo_hz,
            fit_hi_hz=fit_hi_hz,
            nperseg=nperseg,
            bootstrap_n=bootstrap_n,
            seed=seed,
        )
        for cohort, record in cohort_records
    ]
