"""Static tests for PhysioNet cardiac cohort manifests (Task 1).

Verifies that the committed manifests under ``data/manifests/`` match
the pinned ``COHORTS`` spec:

  1. Each of 4 cohorts has a manifest file.
  2. ``expected_n_subjects`` matches the hard-coded record-list length.
  3. ``actual_n_subjects == expected_n_subjects`` (no silent failures).
  4. Every subject carries a valid 64-hex SHA-256 of its RR series.
  5. Annotation extension + pn_dir in the manifest match the COHORTS spec.
  6. Sampling frequency per record matches the nominal fs for the cohort
     within tolerance (wfdb returns float, so allow ±0.01 Hz).

A separate *slow* empirical test regenerates one small cohort (chfdb)
from the live PhysioNet endpoint and checks the RR-interval SHA-256 is
byte-identical to the committed manifest. This is skipped when wfdb
is unavailable or the PhysioNet endpoint is unreachable.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from tools.data.physionet_cohort import COHORTS

_REPO_ROOT = Path(__file__).parent.parent
_MANIFESTS = _REPO_ROOT / "data" / "manifests"
_WFDB_AVAILABLE = importlib.util.find_spec("wfdb") is not None

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _load(cohort: str) -> dict:
    path = _MANIFESTS / f"{cohort}_manifest.json"
    assert path.exists(), f"missing manifest: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("cohort", sorted(COHORTS))
def test_manifest_file_present(cohort: str) -> None:
    assert (_MANIFESTS / f"{cohort}_manifest.json").exists()


@pytest.mark.parametrize("cohort", sorted(COHORTS))
def test_expected_n_matches_spec(cohort: str) -> None:
    m = _load(cohort)
    spec = COHORTS[cohort]
    assert m["expected_n_subjects"] == spec.expected_n_subjects
    assert m["pn_dir"] == spec.pn_dir
    assert m["annotation_extension"] == spec.annotation_extension
    assert m["role"] == spec.role


@pytest.mark.parametrize("cohort", sorted(COHORTS))
def test_actual_matches_expected(cohort: str) -> None:
    m = _load(cohort)
    assert m["actual_n_subjects"] == m["expected_n_subjects"], (
        f"{cohort}: {m['actual_n_subjects']}/{m['expected_n_subjects']} "
        "intake failures must be resolved before gate closes"
    )
    assert len(m["subjects"]) == m["expected_n_subjects"]


@pytest.mark.parametrize("cohort", sorted(COHORTS))
def test_each_subject_has_valid_sha256(cohort: str) -> None:
    m = _load(cohort)
    for entry in m["subjects"]:
        assert entry["status"] == "ok", entry
        sha = entry.get("rr_sha256")
        assert sha is not None, entry["record"]
        assert _SHA256_RE.match(sha), sha


@pytest.mark.parametrize("cohort", sorted(COHORTS))
def test_fs_matches_nominal(cohort: str) -> None:
    m = _load(cohort)
    nominal = COHORTS[cohort].nominal_fs_hz
    for entry in m["subjects"]:
        fs = entry["fs_hz"]
        assert fs is not None, entry["record"]
        assert abs(fs - nominal) < 0.01, f"{entry['record']} fs={fs} != {nominal}"


@pytest.mark.parametrize("cohort", sorted(COHORTS))
def test_rr_summary_stats_plausible(cohort: str) -> None:
    """Mean RR between 0.3 s (200 bpm) and 2.0 s (30 bpm) for every subject."""
    m = _load(cohort)
    for entry in m["subjects"]:
        mean_rr = entry["mean_rr_s"]
        n_rr = entry["n_rr_intervals"]
        assert mean_rr is not None, entry["record"]
        assert 0.3 <= mean_rr <= 2.0, f"{entry['record']} mean_rr={mean_rr}"
        assert n_rr >= 1000, f"{entry['record']} too few RR: {n_rr}"


@pytest.mark.parametrize("cohort", sorted(COHORTS))
def test_records_match_spec(cohort: str) -> None:
    m = _load(cohort)
    expected = list(COHORTS[cohort].expected_records)
    actual = [e["record"] for e in m["subjects"]]
    assert actual == expected


def test_no_subject_overlap_across_cohorts() -> None:
    """Task 2 depends on this: a subject must live in exactly one cohort."""
    seen: dict[str, str] = {}
    for cohort in sorted(COHORTS):
        m = _load(cohort)
        for entry in m["subjects"]:
            rec = entry["record"]
            prior = seen.get(rec)
            assert prior is None, f"record {rec!r} appears in {prior} and {cohort}"
            seen[rec] = cohort


@pytest.mark.slow
@pytest.mark.skipif(not _WFDB_AVAILABLE, reason="wfdb not installed")
def test_live_fetch_chfdb_first_record_matches_manifest_sha() -> None:
    """Empirical: re-fetch chfdb:chf01 and confirm RR SHA-256 matches manifest.

    Guards against manifest drift if a researcher regenerates the cohort.
    """
    from tools.data.physionet_cohort import fetch_record

    spec = COHORTS["chfdb"]
    first = spec.expected_records[0]
    fresh = fetch_record(spec, first, cache_dir=None)
    m = _load("chfdb")
    manifest_entry = next(e for e in m["subjects"] if e["record"] == first)
    if fresh.status != "ok":
        pytest.skip(f"PhysioNet unreachable: {fresh.error_class}: {fresh.error_message}")
    assert fresh.rr_sha256 == manifest_entry["rr_sha256"], (
        f"RR SHA-256 drift on {first}: live={fresh.rr_sha256} "
        f"vs committed={manifest_entry['rr_sha256']}"
    )
