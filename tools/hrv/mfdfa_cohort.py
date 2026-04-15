"""Cohort-scale MFDFA runner — batch ``(h(q=2), Δh)`` extraction.

Walks a cohort of cached RR-interval ``.rr.npy`` arrays and applies the
``substrates.physionet_hrv.mfdfa.mfdfa`` estimator per subject. Returns
a list of :class:`MFDFASubject` records suitable for classifier input
and for §4.3 of the preprint skeleton.

Design constraints
------------------
- Offline only. Does not talk to PhysioNet. If a subject's cache is
  missing, the subject is skipped with an explanatory status rather
  than silently dropped — that distinction matters for claim discipline.
- No surrogate nulls here. The Branch A promotion gate (per
  ``manuscript/hrv_bounded_preprint_skeleton.md`` §3.5) is the
  blind-validation step, not a null separation on MFDFA itself. Null
  separation lives in :mod:`tools.hrv.null_suite`.
- Deterministic. Given identical cached arrays and identical MFDFA
  parameters, the output is bitwise reproducible.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from substrates.physionet_hrv.mfdfa import mfdfa

__all__ = ["MFDFASubject", "load_rr_cache", "run_cohort_mfdfa"]

_DEFAULT_Q_VALUES = np.arange(-3.0, 3.5, 0.5)


@dataclasses.dataclass(frozen=True)
class MFDFASubject:
    cohort: str
    record: str
    status: str  # "ok" | "missing_cache" | "mfdfa_error" | "too_short"
    n_rr: int
    h_at_q2: float | None
    delta_h: float | None
    delta_alpha: float | None
    error: str | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "cohort": self.cohort,
            "record": self.record,
            "status": self.status,
            "n_rr": self.n_rr,
            "h_at_q2": None if self.h_at_q2 is None else round(self.h_at_q2, 4),
            "delta_h": None if self.delta_h is None else round(self.delta_h, 4),
            "delta_alpha": None if self.delta_alpha is None else round(self.delta_alpha, 4),
            "error": self.error,
        }


def load_rr_cache(cohort: str, record: str, cache_dir: Path) -> np.ndarray | None:
    """Return the RR array in seconds, or ``None`` if absent."""

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
    q_values: np.ndarray,
    s_min: int,
    fit_order: int,
) -> MFDFASubject:
    if rr is None:
        return MFDFASubject(
            cohort=cohort,
            record=record,
            status="missing_cache",
            n_rr=0,
            h_at_q2=None,
            delta_h=None,
            delta_alpha=None,
        )
    rr = rr[:rr_truncate]
    if rr.size < 4 * s_min:
        return MFDFASubject(
            cohort=cohort,
            record=record,
            status="too_short",
            n_rr=int(rr.size),
            h_at_q2=None,
            delta_h=None,
            delta_alpha=None,
        )
    try:
        result = mfdfa(
            rr,
            q_values=q_values,
            s_min=s_min,
            s_max=rr.size // 4,
            fit_order=fit_order,
        )
    except Exception as exc:  # noqa: BLE001 — record + continue
        return MFDFASubject(
            cohort=cohort,
            record=record,
            status="mfdfa_error",
            n_rr=int(rr.size),
            h_at_q2=None,
            delta_h=None,
            delta_alpha=None,
            error=f"{type(exc).__name__}: {exc}",
        )
    return MFDFASubject(
        cohort=cohort,
        record=record,
        status="ok",
        n_rr=int(rr.size),
        h_at_q2=float(result.h_at_q2),
        delta_h=float(result.delta_h),
        delta_alpha=float(result.delta_alpha),
    )


def run_cohort_mfdfa(
    cohort_records: Iterable[tuple[str, str]],
    *,
    cache_dir: Path,
    rr_truncate: int = 20000,
    q_values: np.ndarray = _DEFAULT_Q_VALUES,
    s_min: int = 16,
    fit_order: int = 1,
) -> list[MFDFASubject]:
    """Batch MFDFA across ``(cohort, record)`` pairs from disk cache.

    Parameters follow the Kantelhardt 2002 conventions used in the
    n=5 pilot (``run_nsr2db_hrv_multifractal.per_subject_run``):
    q ∈ [-3, 3] step 0.5, scales ∈ [s_min, n_rr/4], linear detrending.
    """

    return [
        _run_one(
            cohort,
            record,
            load_rr_cache(cohort, record, cache_dir),
            rr_truncate=rr_truncate,
            q_values=q_values,
            s_min=s_min,
            fit_order=fit_order,
        )
        for cohort, record in cohort_records
    ]
