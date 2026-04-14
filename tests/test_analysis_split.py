"""Tests for the immutable dev / external analysis split (Task 2)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tools.data.analysis_split import (
    ANALYSIS_SPLIT_PATH,
    ANALYSIS_SPLIT_SHA256,
    AnalysisSplit,
    ImmutabilityError,
    Split,
    SplitLeakError,
    assert_not_external,
    distribution_summary,
    enforce_dev_only,
    load_split,
)
from tools.data.physionet_cohort import COHORTS

_REPO_ROOT = Path(__file__).parent.parent


def test_split_yaml_file_exists() -> None:
    assert ANALYSIS_SPLIT_PATH.exists()


def test_locked_sha256_matches_file() -> None:
    raw = ANALYSIS_SPLIT_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ANALYSIS_SPLIT_SHA256, (
        "config/analysis_split.yaml was edited without updating "
        "ANALYSIS_SPLIT_SHA256 in tools/data/analysis_split.py"
    )


def test_load_split_returns_expected_counts() -> None:
    s = load_split()
    assert isinstance(s, AnalysisSplit)
    assert s.development.n_subjects == 54 + 15
    assert s.external.n_subjects == 29 + 18
    assert s.development.n_subjects + s.external.n_subjects == 116


def test_cohort_roles_match_task1_spec() -> None:
    s = load_split()
    assert set(s.development.cohorts) == {"nsr2db", "chfdb"}
    assert set(s.external.cohorts) == {"chf2db", "nsrdb"}

    # Cross-check against the role declared in the COHORTS spec.
    dev_roles = {COHORTS[c].role for c in s.development.cohorts}
    ext_roles = {COHORTS[c].role for c in s.external.cohorts}
    assert dev_roles == {"development_healthy", "development_pathology"}
    assert ext_roles == {"external_healthy", "external_pathology"}


def test_each_cohort_has_expected_n_in_split() -> None:
    s = load_split()
    counts = {
        ("nsr2db", "development"): 54,
        ("chfdb", "development"): 15,
        ("chf2db", "external"): 29,
        ("nsrdb", "external"): 18,
    }
    for (cohort, split_name), expected in counts.items():
        target: Split = getattr(s, split_name)
        actual = sum(1 for ref in target.subjects if ref.cohort == cohort)
        assert actual == expected, f"{cohort}/{split_name}: {actual} != {expected}"


def test_no_subject_overlap_across_splits() -> None:
    s = load_split()
    dev_keys = {ref.as_tuple() for ref in s.development.subjects}
    ext_keys = {ref.as_tuple() for ref in s.external.subjects}
    assert dev_keys.isdisjoint(ext_keys)


def test_no_duplicate_subject_inside_split() -> None:
    s = load_split()
    for side in (s.development, s.external):
        seen: set[tuple[str, str]] = set()
        for ref in side.subjects:
            assert ref.as_tuple() not in seen, f"dup in {side.name}: {ref}"
            seen.add(ref.as_tuple())


def test_split_covers_every_record_from_manifests() -> None:
    """Every subject in the 4 committed manifests must appear in exactly one
    split. This is the strongest anti-leak check — a subject that exists
    in a manifest but is missing from both splits would be invisible to
    the pipeline."""
    s = load_split()
    all_split_keys = {ref.as_tuple() for ref in s.all_subjects()}
    import json

    for cohort in COHORTS:
        m = json.loads(
            (_REPO_ROOT / "data" / "manifests" / f"{cohort}_manifest.json").read_text("utf-8")
        )
        for entry in m["subjects"]:
            key = (cohort, entry["record"])
            assert key in all_split_keys, f"manifest record {key} missing from split"


def test_immutability_error_on_tamper(tmp_path: Path) -> None:
    tampered = tmp_path / "split.yaml"
    tampered.write_bytes(ANALYSIS_SPLIT_PATH.read_bytes() + b"# tampered\n")
    with pytest.raises(ImmutabilityError):
        load_split(path=tampered)


def test_dev_only_gate_blocks_external_read() -> None:
    s = load_split()
    ext_ref = s.external.subjects[0]
    with enforce_dev_only(), pytest.raises(SplitLeakError):
        assert_not_external((ext_ref,))


def test_dev_only_gate_permits_dev_read() -> None:
    s = load_split()
    dev_ref = s.development.subjects[0]
    with enforce_dev_only():
        # no raise
        assert_not_external((dev_ref,))


def test_distribution_summary_shape() -> None:
    summary = distribution_summary()
    assert summary["split_sha256"] == ANALYSIS_SPLIT_SHA256
    for side in ("development", "external"):
        block = summary["splits"][side]
        for key in (
            "n_subjects",
            "cohorts",
            "cohort_counts",
            "n_rr_intervals",
            "recording_duration_s",
            "mean_rr_s",
            "sampling_fs_hz",
        ):
            assert key in block


def test_distribution_summary_numbers_plausible() -> None:
    summary = distribution_summary()
    dev = summary["splits"]["development"]
    ext = summary["splits"]["external"]
    assert dev["n_subjects"] == 69
    assert ext["n_subjects"] == 47
    # long-term Holter recordings: > 10 hours each
    assert dev["recording_duration_s"]["min"] > 10 * 3600
    assert ext["recording_duration_s"]["min"] > 10 * 3600
    # mean RR in [0.3 s, 2.0 s] per-subject → cohort mean in the same band
    assert 0.3 < dev["mean_rr_s"]["mean"] < 2.0
    assert 0.3 < ext["mean_rr_s"]["mean"] < 2.0


def test_distribution_summary_flags_mixed_sampling() -> None:
    """Dev set mixes 128 Hz (nsr2db) and 250 Hz (chfdb). External is all
    128 Hz. This is a real confound for any spectral comparison and must
    remain visible in the distribution summary for Task 4 to handle."""
    summary = distribution_summary()
    dev_fs = summary["splits"]["development"]["sampling_fs_hz"]
    ext_fs = summary["splits"]["external"]["sampling_fs_hz"]
    assert dev_fs["min"] == 128.0
    assert dev_fs["max"] == 250.0  # chfdb
    assert ext_fs["min"] == 128.0
    assert ext_fs["max"] == 128.0  # both external cohorts at 128 Hz
