"""PhysioNet NSR2DB fetcher via ``wfdb`` — no auth required.

PhysioNet hosts the Normal Sinus Rhythm RR Interval Database as
WFDB-format records. The ``wfdb`` Python package streams them
directly via HTTPS without manual download.

Records nsr001 through nsr054 are available. Each is an ECG
recording (~24 hours) with R-peak annotations. The annotation
file (``ecg`` extension) gives R-peak positions in samples; the
header file gives the sampling frequency. RR intervals are derived
as the differences between consecutive normal R-peak positions,
divided by the sampling rate, yielding inter-beat intervals in
seconds.

This module returns RR-interval series in seconds suitable for
HRV spectral analysis.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib

import numpy as np
import wfdb

__all__ = [
    "NSRRecord",
    "available_records",
    "fetch_rr_intervals",
]

PN_DIR = "nsr2db"
ANNOTATION_EXTENSION = "ecg"

# Records nsr001-nsr054. Some of these may be missing in any given
# PhysioNet snapshot; the fetcher tolerates per-record failure and
# returns whatever is available.
ALL_RECORDS: tuple[str, ...] = tuple(f"nsr{i:03d}" for i in range(1, 55))


@dataclasses.dataclass(frozen=True)
class NSRRecord:
    """One NSR2DB record's RR-interval series + provenance."""

    record_name: str
    n_normal_beats: int
    n_rr_intervals: int
    fs_hz: float
    mean_rr_s: float
    std_rr_s: float
    rr_seconds: np.ndarray
    fetched_utc: str

    def as_provenance_dict(self) -> dict:
        return {
            "record_name": self.record_name,
            "n_normal_beats": self.n_normal_beats,
            "n_rr_intervals": self.n_rr_intervals,
            "fs_hz": self.fs_hz,
            "mean_rr_s": round(self.mean_rr_s, 4),
            "std_rr_s": round(self.std_rr_s, 4),
            "rr_sha256": hashlib.sha256(self.rr_seconds.astype(np.float64).tobytes()).hexdigest(),
            "fetched_utc": self.fetched_utc,
        }


def available_records() -> tuple[str, ...]:
    """Return the canonical record-name list."""

    return ALL_RECORDS


def fetch_rr_intervals(
    record_name: str,
    *,
    pn_dir: str = PN_DIR,
    annotation_ext: str = ANNOTATION_EXTENSION,
) -> NSRRecord:
    """Fetch one NSR2DB record and return its RR-interval series.

    Filters annotations to symbol == "N" (normal beats) per the
    standard HRV preprocessing convention.

    Raises on network or wfdb errors.
    """

    ann = wfdb.rdann(record_name, annotation_ext, pn_dir=pn_dir)
    samples = np.asarray(ann.sample, dtype=np.int64)
    symbols = ann.symbol
    fs = float(ann.fs)
    normal_mask = np.array([s == "N" for s in symbols])
    normal_samples = samples[normal_mask]
    rr_samples = np.diff(normal_samples)
    rr_seconds = rr_samples / fs
    fetched = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return NSRRecord(
        record_name=record_name,
        n_normal_beats=int(normal_mask.sum()),
        n_rr_intervals=int(len(rr_seconds)),
        fs_hz=fs,
        mean_rr_s=float(rr_seconds.mean()),
        std_rr_s=float(rr_seconds.std()),
        rr_seconds=rr_seconds.astype(np.float64),
        fetched_utc=fetched,
    )
