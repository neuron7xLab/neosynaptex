"""Immutable development / external validation split — cardiac γ-program.

Contract
--------
Task 2 of the γ-program remediation protocol. Freezes the subject-level
development / external-validation split BEFORE any feature computation so
that calibration (Task 8) cannot silently bleed into validation.

The split is encoded once, in ``config/analysis_split.yaml``, and its
SHA-256 is locked by the constant :data:`ANALYSIS_SPLIT_SHA256`. Any
edit to the YAML without a corresponding constant update breaks
:func:`load_split` and every downstream pipeline. The constant is
review-gated; the YAML is not.

Primary unit
------------
The primary unit of analysis is the **subject**. Windows are nested
observations within a subject. A subject lives in exactly one split —
this is verified both at load time (no overlap across splits) and at
cohort intake time (no cross-cohort record collision, see
:mod:`tools.data.physionet_cohort` tests).

Calibration discipline
----------------------
Any code that calls :func:`load_split` gets back *frozen* membership;
no threshold, feature fit, or null-separability verdict may look at
the ``external`` split during calibration (see CLAIM_BOUNDARY §E-02 /
§E-03).  The ``enforce_dev_only`` context manager is provided for
calibration entry points so that accidental external reads raise
immediately.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "ANALYSIS_SPLIT_PATH",
    "ANALYSIS_SPLIT_SHA256",
    "ImmutabilityError",
    "SplitLeakError",
    "Split",
    "SubjectRef",
    "load_split",
    "enforce_dev_only",
]


# --- Immutability anchor ---------------------------------------------------
#
# This constant is the review gate. Changing ``config/analysis_split.yaml``
# without also updating this constant breaks the load and every test that
# calls :func:`load_split`. Rotating this value signals to reviewers that
# the calibration / validation split changed — which is a protocol event,
# not a routine edit.
#
# Value is computed over the raw UTF-8 bytes of ``config/analysis_split.yaml``
# as-committed. Do not add a trailing newline between edit and hash unless
# the edit itself deliberately changes the file.

ANALYSIS_SPLIT_PATH = Path(__file__).resolve().parents[2] / "config" / "analysis_split.yaml"
ANALYSIS_SPLIT_SHA256 = "119c29c80a99553e36d2b6a8144a27831902ec08a7a706968d9ae553f508b103"

_SPLIT_NAMES: tuple[str, ...] = ("development", "external")
_SplitName = Literal["development", "external"]


class ImmutabilityError(RuntimeError):
    """Raised when the on-disk split YAML does not match the locked hash."""


class SplitLeakError(RuntimeError):
    """Raised when code tries to read the external split under dev-only gate."""


@dataclasses.dataclass(frozen=True)
class SubjectRef:
    cohort: str
    record: str

    def as_tuple(self) -> tuple[str, str]:
        return (self.cohort, self.record)


@dataclasses.dataclass(frozen=True)
class Split:
    """One side of the dev / external partition."""

    name: _SplitName
    cohorts: tuple[str, ...]
    subjects: tuple[SubjectRef, ...]

    @property
    def n_subjects(self) -> int:
        return len(self.subjects)

    def records_in(self, cohort: str) -> tuple[str, ...]:
        return tuple(s.record for s in self.subjects if s.cohort == cohort)


@dataclasses.dataclass(frozen=True)
class AnalysisSplit:
    """The full, verified split contract."""

    schema_version: int
    sha256: str
    development: Split
    external: Split

    def all_subjects(self) -> tuple[SubjectRef, ...]:
        return self.development.subjects + self.external.subjects


# --- YAML parsing (no external dependency) ---------------------------------
#
# The split YAML is intentionally regular — flat keys, simple lists, and
# inline-mapping entries like ``{cohort: nsr2db, record: nsr001}``. A
# micro-parser here avoids pulling in ``pyyaml`` just for this one file
# and keeps the loader dependency-free for CI jobs that don't install
# the dev extras.


def _parse_subject_line(line: str) -> SubjectRef:
    # Expected: "      - {cohort: <c>, record: <r>}"
    payload = line.strip().lstrip("-").strip()
    if not (payload.startswith("{") and payload.endswith("}")):
        raise ValueError(f"malformed subject line: {line!r}")
    body = payload[1:-1]
    parts = [p.strip() for p in body.split(",")]
    kv: dict[str, str] = {}
    for p in parts:
        k, _, v = p.partition(":")
        kv[k.strip()] = v.strip()
    if kv.keys() != {"cohort", "record"}:
        raise ValueError(f"subject line missing keys: {line!r}")
    return SubjectRef(cohort=kv["cohort"], record=kv["record"])


def _parse(text: str) -> dict[str, Any]:
    schema_version: int | None = None
    splits: dict[str, dict[str, Any]] = {}
    cohort_assignment: dict[str, str] = {}

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if stripped.startswith("schema_version:"):
            schema_version = int(stripped.split(":", 1)[1].strip())
            i += 1
            continue

        if stripped == "cohort_assignment:":
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and ":" in lines[i]:
                k, _, v = lines[i].strip().partition(":")
                cohort_assignment[k.strip()] = v.strip()
                i += 1
            continue

        if stripped == "splits:":
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                if not lines[i].strip():
                    i += 1
                    continue
                split_header = lines[i].strip().rstrip(":")
                if split_header not in _SPLIT_NAMES:
                    i += 1
                    continue
                block: dict[str, Any] = {"name": split_header, "subjects": []}
                i += 1
                while i < len(lines) and lines[i].startswith("    "):
                    sub = lines[i].strip()
                    if sub.startswith("cohorts:"):
                        # simple list form: [a, b]
                        raw = sub.split(":", 1)[1].strip()
                        raw = raw.strip("[]")
                        block["cohorts"] = tuple(
                            c.strip().strip("'\"") for c in raw.split(",") if c.strip()
                        )
                        i += 1
                    elif sub.startswith("n_subjects:"):
                        block["n_subjects"] = int(sub.split(":", 1)[1].strip())
                        i += 1
                    elif sub == "subjects:":
                        i += 1
                        while i < len(lines) and lines[i].startswith("      -"):
                            block["subjects"].append(_parse_subject_line(lines[i]))
                            i += 1
                    else:
                        i += 1
                splits[split_header] = block
            continue

        i += 1

    if schema_version is None:
        raise ValueError("schema_version missing from analysis_split.yaml")
    if set(splits) != set(_SPLIT_NAMES):
        raise ValueError(f"splits must be exactly {_SPLIT_NAMES}, got {set(splits)}")
    return {
        "schema_version": schema_version,
        "cohort_assignment": cohort_assignment,
        "splits": splits,
    }


# --- Public API ------------------------------------------------------------
def load_split(
    *,
    path: Path | None = None,
    expected_sha256: str | None = None,
) -> AnalysisSplit:
    """Read + hash-verify + structurally validate the split config.

    Raises :class:`ImmutabilityError` if the YAML has been edited without
    updating :data:`ANALYSIS_SPLIT_SHA256`. Raises :class:`ValueError` on
    structural problems (duplicate subject, wrong split member count,
    unknown cohort).
    """

    p = path or ANALYSIS_SPLIT_PATH
    expected = expected_sha256 or ANALYSIS_SPLIT_SHA256

    raw = p.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ImmutabilityError(
            f"config/analysis_split.yaml has been modified:\n"
            f"  expected sha256 = {expected}\n"
            f"  actual sha256   = {actual}\n"
            "If the edit was intentional, update "
            "ANALYSIS_SPLIT_SHA256 in tools/data/analysis_split.py "
            "in the same PR. See docs/protocols/ANALYSIS_SPLIT.md."
        )

    data = _parse(raw.decode("utf-8"))

    # structural checks
    dev = data["splits"]["development"]
    ext = data["splits"]["external"]

    dev_keys = {s.as_tuple() for s in dev["subjects"]}
    ext_keys = {s.as_tuple() for s in ext["subjects"]}
    overlap = dev_keys & ext_keys
    if overlap:
        raise ValueError(f"subject overlap across splits: {sorted(overlap)}")
    if len(dev_keys) != len(dev["subjects"]):
        raise ValueError("duplicate subject inside development split")
    if len(ext_keys) != len(ext["subjects"]):
        raise ValueError("duplicate subject inside external split")

    # cross-check: cohort_assignment must cover every subject cohort
    declared_cohorts = set(data["cohort_assignment"].keys())
    subject_cohorts = {s.cohort for s in dev["subjects"]} | {s.cohort for s in ext["subjects"]}
    missing = subject_cohorts - declared_cohorts
    if missing:
        raise ValueError(f"cohort_assignment missing cohorts: {sorted(missing)}")

    return AnalysisSplit(
        schema_version=int(data["schema_version"]),
        sha256=actual,
        development=Split(
            name="development",
            cohorts=tuple(dev.get("cohorts", ())),
            subjects=tuple(dev["subjects"]),
        ),
        external=Split(
            name="external",
            cohorts=tuple(ext.get("cohorts", ())),
            subjects=tuple(ext["subjects"]),
        ),
    )


# --- Dev-only enforcement --------------------------------------------------
_DEV_ONLY: list[bool] = []


@contextlib.contextmanager
def enforce_dev_only() -> Iterator[None]:
    """Gate: forbid reading the external split inside the block.

    Calibration code paths must wrap threshold fitting in this context
    manager. Any downstream call to :func:`assert_not_external` made
    from within the block raises :class:`SplitLeakError`.
    """

    _DEV_ONLY.append(True)
    try:
        yield
    finally:
        _DEV_ONLY.pop()


def assert_not_external(subjects: tuple[SubjectRef, ...]) -> None:
    """No-op unless called inside :func:`enforce_dev_only`."""

    if not _DEV_ONLY:
        return
    split = load_split()
    ext_keys = {s.as_tuple() for s in split.external.subjects}
    leaks = [s for s in subjects if s.as_tuple() in ext_keys]
    if leaks:
        raise SplitLeakError(
            "external-split subjects read under enforce_dev_only(): "
            + ", ".join(f"{s.cohort}:{s.record}" for s in leaks)
        )


# --- Convenience: distribution summary ------------------------------------
def distribution_summary() -> dict[str, Any]:
    """Per-split aggregate metrics for the comparison report.

    Reads per-subject numbers from ``data/manifests/{cohort}_manifest.json``
    so the summary stays in sync with Task 1.
    """

    split = load_split()
    manifests_dir = ANALYSIS_SPLIT_PATH.parent.parent / "data" / "manifests"

    out: dict[str, Any] = {
        "schema_version": 1,
        "split_sha256": split.sha256,
        "splits": {},
    }

    for s in (split.development, split.external):
        rr_counts: list[int] = []
        durations_s: list[float] = []
        mean_rrs: list[float] = []
        sampling_fs: list[float] = []
        cohort_counts: dict[str, int] = {}
        for cohort in s.cohorts:
            m = json.loads((manifests_dir / f"{cohort}_manifest.json").read_text("utf-8"))
            by_record = {e["record"]: e for e in m["subjects"]}
            for rec in s.records_in(cohort):
                e = by_record[rec]
                rr_counts.append(e["n_rr_intervals"])
                durations_s.append(e["recording_duration_s"])
                mean_rrs.append(e["mean_rr_s"])
                sampling_fs.append(e["fs_hz"])
            cohort_counts[cohort] = len(s.records_in(cohort))

        def stats(xs: list[float]) -> dict[str, float]:
            if not xs:
                return {"n": 0, "mean": 0.0, "min": 0.0, "max": 0.0}
            return {
                "n": len(xs),
                "mean": round(sum(xs) / len(xs), 6),
                "min": round(min(xs), 6),
                "max": round(max(xs), 6),
            }

        out["splits"][s.name] = {
            "n_subjects": s.n_subjects,
            "cohorts": list(s.cohorts),
            "cohort_counts": cohort_counts,
            "n_rr_intervals": stats([float(x) for x in rr_counts]),
            "recording_duration_s": stats(durations_s),
            "mean_rr_s": stats(mean_rrs),
            "sampling_fs_hz": stats(sampling_fs),
        }
    return out
