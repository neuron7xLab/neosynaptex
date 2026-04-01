"""Contract tests for canonical mutation metrics module."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.mutation_counts import MutationCounts, calculate_score


def test_mutation_baseline_structure() -> None:
    baseline_path = Path("quality/mutation_baseline.json")
    assert baseline_path.exists(), "Mutation baseline file must exist"

    with baseline_path.open(encoding="utf-8") as handle:
        baseline = json.load(handle)

    required_keys = {
        "version",
        "timestamp",
        "baseline_score",
        "tolerance_delta",
        "description",
        "config",
        "scope",
        "metrics",
    }
    assert required_keys.issubset(baseline.keys())


def test_mutation_baseline_factuality() -> None:
    baseline_path = Path("quality/mutation_baseline.json")
    assert baseline_path.exists(), "Mutation baseline must exist"

    with baseline_path.open(encoding="utf-8") as handle:
        baseline = json.load(handle)

    metrics = baseline["metrics"]
    has_data = (
        metrics["total_mutants"] > 0
        or metrics["killed_mutants"] > 0
        or metrics["survived_mutants"] > 0
    )

    if not has_data:
        pytest.skip("Baseline not yet generated - run 'make mutation-baseline' first")

    assert metrics["total_mutants"] == (
        metrics["killed_mutants"]
        + metrics["survived_mutants"]
        + metrics.get("timeout_mutants", 0)
        + metrics.get("suspicious_mutants", 0)
    )
    assert 0.0 <= metrics["score_percent"] <= 100.0


def test_calculate_mutation_score() -> None:
    counts = MutationCounts(45, 5, 2, 1, 0, 0)
    score = calculate_score(counts)
    assert 88.0 < score < 89.0
    assert calculate_score(MutationCounts(0, 0, 0, 0, 0, 0)) == 0.0
    assert calculate_score(MutationCounts(100, 0, 0, 0, 0, 0)) == 100.0


def test_read_mutation_counts_uses_result_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from scripts.mutation_counts import read_mutation_counts

    outputs = {
        "killed": "3\n",
        "survived": "1 2\n",
        "timeout": "\n",
        "suspicious": "\n",
        "skipped": "\n",
        "untested": "4 5 6\n",
    }

    def fake_run(args: list[str], **_kwargs: object) -> SimpleNamespace:
        assert args[0:2] == ["mutmut", "result-ids"]
        return SimpleNamespace(stdout=outputs[args[2]])

    monkeypatch.setattr("subprocess.run", fake_run)

    counts = read_mutation_counts()
    assert counts == MutationCounts(1, 2, 0, 0, 0, 3)
    assert counts.total_scored == 3
    assert counts.killed_equivalent == 1


def test_load_mutation_baseline_and_assessment(tmp_path: Path) -> None:
    from scripts.mutation_counts import assess_mutation_gate, load_mutation_baseline

    baseline_path = tmp_path / "mutation_baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "baseline_score": 80.0,
                "tolerance_delta": 5.0,
                "status": "active",
                "metrics": {"total_mutants": 42},
            }
        ),
        encoding="utf-8",
    )

    baseline = load_mutation_baseline(baseline_path)
    assessment = assess_mutation_gate(MutationCounts(8, 2, 0, 0, 0, 0), baseline)
    assert baseline.min_acceptable == 75.0
    assert assessment.score == 80.0
    assert assessment.gate_passes is True


def test_render_ci_summary_markdown_uses_canonical_metrics() -> None:
    from scripts.mutation_counts import (
        MutationAssessment,
        MutationBaseline,
        render_ci_summary_markdown,
    )

    assessment = MutationAssessment(
        counts=MutationCounts(3, 2, 1, 0, 0, 4),
        baseline=MutationBaseline(70.0, 5.0, "active", 12),
        score=66.67,
    )

    markdown = render_ci_summary_markdown(assessment)
    assert "Gate Status:** ✅ PASS" in markdown
    assert "| Mutation score | 66.67% |" in markdown


def test_render_github_output_lines_contract() -> None:
    from scripts.mutation_counts import (
        MutationAssessment,
        MutationBaseline,
        render_github_output_lines,
    )

    assessment = MutationAssessment(
        counts=MutationCounts(7, 3, 0, 0, 0, 0),
        baseline=MutationBaseline(65.0, 4.0, "active", 10),
        score=70.0,
    )

    rendered = render_github_output_lines(assessment)
    lines = rendered.splitlines()
    assert lines == [
        "baseline_score=65.00",
        "tolerance=4.00",
        "min_acceptable=61.00",
        "score=70.00",
        "total=10",
        "killed=7",
    ]
    assert rendered.endswith("\n")
    assert all(
        line.split("=", 1)[0]
        in {
            "baseline_score",
            "tolerance",
            "min_acceptable",
            "score",
            "total",
            "killed",
        }
        for line in lines
    )


def test_validate_mutation_baseline_script(tmp_path: Path) -> None:
    import scripts.validate_mutation_baseline as validate_mutation_baseline

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "timestamp": "2026-01-01T00:00:00Z",
                "baseline_score": 50.0,
                "tolerance_delta": 5.0,
                "status": "active",
                "description": "test",
                "config": {},
                "scope": {},
                "metrics": {
                    "total_mutants": 10,
                    "killed_mutants": 4,
                    "survived_mutants": 5,
                    "timeout_mutants": 1,
                    "suspicious_mutants": 0,
                    "score_percent": 50.0,
                },
            }
        ),
        encoding="utf-8",
    )

    old_argv = validate_mutation_baseline.sys.argv
    try:
        validate_mutation_baseline.sys.argv = [
            "validate_mutation_baseline.py",
            "--baseline",
            str(baseline_path),
        ]
        assert validate_mutation_baseline.main() == 0
    finally:
        validate_mutation_baseline.sys.argv = old_argv


def test_check_mutation_score_handles_missing_mutmut(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.check_mutation_score as check_mutation_score

    def _raise_file_not_found(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("mutmut")

    monkeypatch.setattr("subprocess.run", _raise_file_not_found)

    with pytest.raises(SystemExit) as exc:
        check_mutation_score.parse_mutmut_results()

    assert exc.value.code == 1


def test_parse_mutmut_results_subprocess_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.check_mutation_score as check_mutation_score

    def fake_run(*_args: object, **_kwargs: object) -> None:
        raise subprocess.CalledProcessError(returncode=2, cmd=["mutmut", "result-ids", "killed"])

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(SystemExit) as exc:
        check_mutation_score.parse_mutmut_results()

    assert exc.value.code == 1


def test_validate_mutation_baseline_invariant_mismatch(tmp_path: Path) -> None:
    import scripts.validate_mutation_baseline as validate_mutation_baseline

    baseline_path = tmp_path / "baseline_bad.json"
    baseline_path.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "timestamp": "2026-01-01T00:00:00Z",
                "baseline_score": 50.0,
                "tolerance_delta": 5.0,
                "status": "active",
                "description": "test",
                "config": {},
                "scope": {},
                "metrics": {
                    "total_mutants": 10,
                    "killed_mutants": 3,
                    "survived_mutants": 5,
                    "timeout_mutants": 1,
                    "suspicious_mutants": 0,
                    "score_percent": 90.0,
                },
            }
        ),
        encoding="utf-8",
    )

    old_argv = validate_mutation_baseline.sys.argv
    try:
        validate_mutation_baseline.sys.argv = [
            "validate_mutation_baseline.py",
            "--baseline",
            str(baseline_path),
        ]
        assert validate_mutation_baseline.main() == 1
    finally:
        validate_mutation_baseline.sys.argv = old_argv


def test_validate_mutation_baseline_rejects_invalid_status(tmp_path: Path) -> None:
    import scripts.validate_mutation_baseline as validate_mutation_baseline

    baseline_path = tmp_path / "baseline_bad_status.json"
    baseline_path.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "timestamp": "2026-01-01T00:00:00Z",
                "baseline_score": 50.0,
                "tolerance_delta": 5.0,
                "status": "ready",
                "description": "test",
                "config": {},
                "scope": {},
                "metrics": {
                    "total_mutants": 10,
                    "killed_mutants": 4,
                    "survived_mutants": 5,
                    "timeout_mutants": 1,
                    "suspicious_mutants": 0,
                    "score_percent": 50.0,
                },
            }
        ),
        encoding="utf-8",
    )

    old_argv = validate_mutation_baseline.sys.argv
    try:
        validate_mutation_baseline.sys.argv = [
            "validate_mutation_baseline.py",
            "--baseline",
            str(baseline_path),
        ]
        assert validate_mutation_baseline.main() == 1
    finally:
        validate_mutation_baseline.sys.argv = old_argv
