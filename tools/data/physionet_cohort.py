"""PhysioNet cardiac cohort intake — wfdb-only, manifest-driven.

Purpose
-------
Raw intake of four PhysioNet cardiac databases required by the
γ-program cohort expansion gate (Task 1). This module *only* reaches
PhysioNet via the ``wfdb`` Python API, derives RR-interval series from
annotation files, and emits one manifest per dataset.

No feature extraction, no spectral fits, no nulls. Those belong to
downstream PRs (Tasks 3, 4, 5, 6). Separation of concerns is a
protocol requirement, not a style choice.

Cohort
------
NSR2DB — Normal Sinus Rhythm RR Interval DB       (54 subjects, 128 Hz, ``ecg``)
CHF2DB — BIDMC Congestive Heart Failure RR DB     (29 subjects, 128 Hz, ``ecg``)
CHFDB  — BIDMC Congestive Heart Failure DB        (15 subjects, 250 Hz, ``ecg``)
NSRDB  — MIT-BIH Normal Sinus Rhythm DB           (18 subjects, 128 Hz, ``atr``)

NSRDB record names are not contiguous; they are the canonical
PhysioNet identifiers and are hard-coded below against the published
record list (https://physionet.org/content/nsrdb/1.0.0/RECORDS).

RR derivation
-------------
For each record:
  1. ``wfdb.rdann(record, ann_ext, pn_dir=dataset)`` → sample indices + symbols.
  2. Filter to symbol == "N" (normal beats) per HRV convention
     (Task Force of ESC/NASPE 1996, §3.1 "editing").
  3. RR_i = (sample[i+1] − sample[i]) / fs  for consecutive normal beats.
     ⚠  diff across non-adjacent normals is still a valid NN-interval —
     but at ectopic beats the interval is a *concatenation gap*. We keep
     that behaviour here (raw intake) and defer ectopy-gap handling to
     the outlier-protocol PR (Task 7).

Manifest shape
--------------
One JSON file per dataset under ``data/manifests/{dataset}_manifest.json``
with:

  ``dataset_name, source_url, license, citation, wfdb_version,
  annotation_extension, expected_n_subjects, actual_n_subjects,
  generated_utc, subjects[]``

Each ``subjects[]`` entry carries record id, ``fs_hz``, beat counts,
RR summary stats and a SHA-256 of the raw RR array so integrity can
be verified across machines.

The RR arrays themselves are *optionally* cached as
``data/raw/{dataset}/{record}.rr.npy`` (gitignored) so downstream
consumers can avoid re-fetching.

This module's callers are:
  - ``scripts/build_physionet_cohort_manifests.py`` (CLI)
  - ``tests/test_physionet_cohort_manifests.py`` (static shape tests)

Failure discipline
------------------
Per-record fetch failures are recorded as ``status: "failed"`` entries
with the exception class/message, and the manifest still lists the
expected record so the gap is visible. ``actual_n_subjects`` counts
only successful fetches. A dataset where ``actual < expected`` must be
investigated before the cohort-expansion gate closes.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "CohortSpec",
    "CohortRecord",
    "COHORTS",
    "build_manifest",
    "derive_rr_intervals",
    "fetch_record",
    "write_manifest",
]


# ---------------------------------------------------------------------------
# Static cohort specification
# ---------------------------------------------------------------------------
#
# Record lists are committed in full rather than derived at runtime so
# that CI can assert the expected count offline. The NSRDB list is the
# canonical RECORDS file published with v1.0.0 on PhysioNet.

_NSR2DB_RECORDS: tuple[str, ...] = tuple(f"nsr{i:03d}" for i in range(1, 55))
_CHF2DB_RECORDS: tuple[str, ...] = tuple(f"chf{i:03d}" for i in range(201, 230))
_CHFDB_RECORDS: tuple[str, ...] = tuple(f"chf{i:02d}" for i in range(1, 16))
_NSRDB_RECORDS: tuple[str, ...] = (
    "16265",
    "16272",
    "16273",
    "16420",
    "16483",
    "16539",
    "16773",
    "16786",
    "16795",
    "17052",
    "17453",
    "18177",
    "18184",
    "19088",
    "19090",
    "19093",
    "19140",
    "19830",
)


@dataclasses.dataclass(frozen=True)
class CohortSpec:
    """Pinned identity of one PhysioNet cardiac cohort."""

    name: str
    pn_dir: str
    annotation_extension: str
    expected_records: tuple[str, ...]
    source_url: str
    license: str
    citation: str
    nominal_fs_hz: float
    role: str  # "development_healthy" | "development_pathology" |
    #           "external_healthy"    | "external_pathology"

    @property
    def expected_n_subjects(self) -> int:
        return len(self.expected_records)


COHORTS: dict[str, CohortSpec] = {
    "nsr2db": CohortSpec(
        name="nsr2db",
        pn_dir="nsr2db",
        annotation_extension="ecg",
        expected_records=_NSR2DB_RECORDS,
        source_url="https://physionet.org/content/nsr2db/1.0.0/",
        license="ODC-By 1.0",
        citation=(
            "Goldberger et al. (2000). PhysioBank, PhysioToolkit, and "
            "PhysioNet. Circulation 101(23):e215-e220."
        ),
        nominal_fs_hz=128.0,
        role="development_healthy",
    ),
    "chfdb": CohortSpec(
        name="chfdb",
        pn_dir="chfdb",
        annotation_extension="ecg",
        expected_records=_CHFDB_RECORDS,
        source_url="https://physionet.org/content/chfdb/1.0.0/",
        license="ODC-By 1.0",
        citation=(
            "Baim et al. (1986). Survival of patients with severe "
            "congestive heart failure. JACC 7(3):661-670. "
            "PhysioNet BIDMC CHF DB."
        ),
        nominal_fs_hz=250.0,
        role="development_pathology",
    ),
    "chf2db": CohortSpec(
        name="chf2db",
        pn_dir="chf2db",
        annotation_extension="ecg",
        expected_records=_CHF2DB_RECORDS,
        source_url="https://physionet.org/content/chf2db/1.0.0/",
        license="ODC-By 1.0",
        citation=(
            "BIDMC Congestive Heart Failure RR Interval Database. "
            "PhysioNet. NYHA class III-IV subjects."
        ),
        nominal_fs_hz=128.0,
        role="external_pathology",
    ),
    "nsrdb": CohortSpec(
        name="nsrdb",
        pn_dir="nsrdb",
        annotation_extension="atr",
        expected_records=_NSRDB_RECORDS,
        source_url="https://physionet.org/content/nsrdb/1.0.0/",
        license="ODC-By 1.0",
        citation=(
            "The MIT-BIH Normal Sinus Rhythm Database. PhysioNet. Recorded at Beth Israel Hospital."
        ),
        nominal_fs_hz=128.0,
        role="external_healthy",
    ),
}


# ---------------------------------------------------------------------------
# Per-record fetch
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class CohortRecord:
    """Per-record intake result, serialisable to manifest entry."""

    record: str
    status: str  # "ok" | "failed"
    fs_hz: float | None
    n_annotations: int | None
    n_normal_beats: int | None
    n_rr_intervals: int | None
    recording_duration_s: float | None
    mean_rr_s: float | None
    std_rr_s: float | None
    min_rr_s: float | None
    max_rr_s: float | None
    rr_sha256: str | None
    symbols_observed: tuple[str, ...] | None
    error_class: str | None
    error_message: str | None

    def as_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        # keep tuples as lists in JSON
        if self.symbols_observed is not None:
            d["symbols_observed"] = list(self.symbols_observed)
        # drop all-None error fields on success for clarity
        if self.status == "ok":
            d.pop("error_class", None)
            d.pop("error_message", None)
        return d


def derive_rr_intervals(
    samples: np.ndarray,
    symbols: Iterable[str],
    fs_hz: float,
) -> tuple[np.ndarray, int]:
    """Return (rr_seconds, n_normal_beats) for one annotated record.

    RR_i = (sample[i+1] − sample[i]) / fs, restricted to consecutive
    beats whose symbols are both ``"N"``. At ectopic beats the beat
    series breaks; rather than concatenating across gaps we skip those
    transitions and emit only consecutive-normal pairs. This is the
    Task Force 1996 §3.1 preprocessing convention and matches the
    prior ``substrates/physionet_hrv/nsr2db_client.py`` behaviour.
    """

    samples = np.asarray(samples, dtype=np.int64)
    sym = np.asarray(list(symbols))
    if samples.shape[0] != sym.shape[0]:
        raise ValueError(
            f"samples and symbols length mismatch: {samples.shape[0]} vs {sym.shape[0]}"
        )
    normal = sym == "N"
    # indices where current AND next beat are normal → valid RR slot
    both_normal = normal[:-1] & normal[1:]
    rr_samples = np.diff(samples)[both_normal]
    rr_seconds = rr_samples.astype(np.float64) / float(fs_hz)
    return rr_seconds, int(normal.sum())


def fetch_record(
    spec: CohortSpec,
    record: str,
    *,
    cache_dir: Path | None = None,
) -> CohortRecord:
    """Fetch one record's annotations via wfdb and return an intake row.

    If ``cache_dir`` is given, the RR array is saved as
    ``cache_dir/{record}.rr.npy`` (atomic write). Errors are captured
    as ``status="failed"`` rather than raised so one bad record does
    not block the whole manifest.
    """

    import wfdb  # local import — wfdb is optional until intake runs

    try:
        ann = wfdb.rdann(record, spec.annotation_extension, pn_dir=spec.pn_dir)
    except Exception as exc:  # noqa: BLE001 — intake must not raise
        return CohortRecord(
            record=record,
            status="failed",
            fs_hz=None,
            n_annotations=None,
            n_normal_beats=None,
            n_rr_intervals=None,
            recording_duration_s=None,
            mean_rr_s=None,
            std_rr_s=None,
            min_rr_s=None,
            max_rr_s=None,
            rr_sha256=None,
            symbols_observed=None,
            error_class=type(exc).__name__,
            error_message=str(exc),
        )

    samples = np.asarray(ann.sample, dtype=np.int64)
    symbols = list(ann.symbol)
    fs = float(ann.fs)
    rr, n_normal = derive_rr_intervals(samples, symbols, fs)
    duration_s = float(samples[-1] - samples[0]) / fs if samples.size >= 2 else 0.0
    rr_sha = hashlib.sha256(rr.astype(np.float64).tobytes()).hexdigest()
    symbols_observed = tuple(sorted(set(symbols)))

    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        # np.save appends ``.npy`` unless the path already ends in it; write
        # to a sibling ``.partial`` file then rename so a crash mid-write
        # does not leave a corrupt ``.npy`` that later readers would trust.
        out = cache_dir / f"{record}.rr.npy"
        partial = cache_dir / f"{record}.rr.partial"
        with partial.open("wb") as fh:
            np.save(fh, rr.astype(np.float64), allow_pickle=False)
        partial.replace(out)

    return CohortRecord(
        record=record,
        status="ok",
        fs_hz=fs,
        n_annotations=int(samples.size),
        n_normal_beats=n_normal,
        n_rr_intervals=int(rr.size),
        recording_duration_s=round(duration_s, 3),
        mean_rr_s=round(float(rr.mean()), 6) if rr.size else None,
        std_rr_s=round(float(rr.std()), 6) if rr.size else None,
        min_rr_s=round(float(rr.min()), 6) if rr.size else None,
        max_rr_s=round(float(rr.max()), 6) if rr.size else None,
        rr_sha256=rr_sha,
        symbols_observed=symbols_observed,
        error_class=None,
        error_message=None,
    )


# ---------------------------------------------------------------------------
# Cohort-level manifest
# ---------------------------------------------------------------------------
def build_manifest(
    spec: CohortSpec,
    *,
    cache_dir: Path | None = None,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    """Iterate all expected records and return a manifest dict."""

    import wfdb  # for version stamp

    subjects: list[dict[str, Any]] = []
    ok_count = 0
    for i, rec in enumerate(spec.expected_records):
        row = fetch_record(spec, rec, cache_dir=cache_dir)
        if row.status == "ok":
            ok_count += 1
        subjects.append(row.as_dict())
        if on_progress is not None:
            on_progress(i + 1, len(spec.expected_records), rec, row.status)

    return {
        "dataset_name": spec.name,
        "source_url": spec.source_url,
        "license": spec.license,
        "citation": spec.citation,
        "pn_dir": spec.pn_dir,
        "annotation_extension": spec.annotation_extension,
        "nominal_fs_hz": spec.nominal_fs_hz,
        "role": spec.role,
        "expected_n_subjects": spec.expected_n_subjects,
        "actual_n_subjects": ok_count,
        "wfdb_version": getattr(wfdb, "__version__", "unknown"),
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subjects": subjects,
    }


def write_manifest(manifest: dict[str, Any], out_path: Path) -> None:
    """Atomically write a manifest JSON with sorted keys + 2-space indent."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(out_path)
