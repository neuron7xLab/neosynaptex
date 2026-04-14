"""PhysioNet CHF2DB fetcher — pathological-cardiac contrast.

PhysioNet's BIDMC Congestive Heart Failure RR Interval Database
(``chf2db``) hosts 29 subjects with severe heart failure (NYHA
class III–IV). Identical wfdb annotation format to NSR2DB
(R-peak times via ``ecg`` annotation extension), so the same
preprocessing pipeline applies.

Difference from NSR2DB: the annotation symbol set is broader.
NSR2DB is mostly ``N``; CHF2DB includes meaningful counts of
``V`` (ventricular ectopic), ``A`` (atrial ectopic), and ``~``
(artefact). The standard HRV preprocessing still filters to
``N`` only, but the resulting NN-interval series is shorter
per record than NSR2DB and may be discontinuous at ectopic
beats — a real pathological feature, not a bug.

Records: chf201–chf229.
"""

from __future__ import annotations

from substrates.physionet_hrv.nsr2db_client import (
    NSRRecord,
)
from substrates.physionet_hrv.nsr2db_client import (
    fetch_rr_intervals as _generic_fetch,
)

PN_DIR = "chf2db"
ALL_RECORDS: tuple[str, ...] = tuple(f"chf{i:03d}" for i in range(201, 230))


def fetch_rr_intervals(record_name: str) -> NSRRecord:
    """Fetch one CHF2DB record. Same return shape as NSR2DB."""

    return _generic_fetch(record_name, pn_dir=PN_DIR)


def available_records() -> tuple[str, ...]:
    return ALL_RECORDS
