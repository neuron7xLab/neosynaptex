"""Contract tests for mutation_ci_summary tool."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.mutation_counts import MutationCounts


def test_mutation_ci_summary_requires_target_flags() -> None:
    import scripts.mutation_ci_summary as mutation_ci_summary

    old_argv = mutation_ci_summary.sys.argv
    try:
        mutation_ci_summary.sys.argv = ["mutation_ci_summary.py"]
        assert mutation_ci_summary.main() == 1
    finally:
        mutation_ci_summary.sys.argv = old_argv


def test_mutation_ci_summary_writes_output_file(tmp_path: Path) -> None:
    from scripts.mutation_ci_summary import write_github_output
    from scripts.mutation_counts import MutationAssessment, MutationBaseline

    output_file = tmp_path / "github_output.txt"
    assessment = MutationAssessment(
        counts=MutationCounts(5, 5, 0, 0, 0, 0),
        baseline=MutationBaseline(50.0, 2.0, "active", 10),
        score=50.0,
    )

    write_github_output(output_file, assessment)
    content = output_file.read_text(encoding="utf-8")
    assert "baseline_score=50.00" in content
    assert "killed=5" in content


def test_mutation_ci_summary_missing_github_output_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.mutation_ci_summary as mutation_ci_summary

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {"baseline_score": 70.0, "tolerance_delta": 5.0, "metrics": {"total_mutants": 1}}
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        mutation_ci_summary,
        "read_mutation_counts",
        lambda: (_ for _ in ()).throw(AssertionError("read_mutation_counts should not be called")),
    )

    old_argv = mutation_ci_summary.sys.argv
    old_env = dict(mutation_ci_summary.os.environ)
    try:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.sys.argv = [
            "mutation_ci_summary.py",
            "--baseline",
            str(baseline_path),
            "--write-output",
        ]
        assert mutation_ci_summary.main() == 1
    finally:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ.update(old_env)
        mutation_ci_summary.sys.argv = old_argv


def test_mutation_ci_summary_missing_github_summary_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.mutation_ci_summary as mutation_ci_summary

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {"baseline_score": 70.0, "tolerance_delta": 5.0, "metrics": {"total_mutants": 1}}
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        mutation_ci_summary,
        "read_mutation_counts",
        lambda: (_ for _ in ()).throw(AssertionError("read_mutation_counts should not be called")),
    )

    old_argv = mutation_ci_summary.sys.argv
    old_env = dict(mutation_ci_summary.os.environ)
    try:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.sys.argv = [
            "mutation_ci_summary.py",
            "--baseline",
            str(baseline_path),
            "--write-summary",
        ]
        assert mutation_ci_summary.main() == 1
    finally:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ.update(old_env)
        mutation_ci_summary.sys.argv = old_argv


def test_mutation_ci_summary_missing_env_does_not_load_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.mutation_ci_summary as mutation_ci_summary

    monkeypatch.setattr(
        mutation_ci_summary,
        "load_mutation_baseline",
        lambda _path: (_ for _ in ()).throw(
            AssertionError("load_mutation_baseline should not be called")
        ),
    )

    old_argv = mutation_ci_summary.sys.argv
    old_env = dict(mutation_ci_summary.os.environ)
    try:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.sys.argv = ["mutation_ci_summary.py", "--write-output"]
        assert mutation_ci_summary.main() == 1
    finally:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ.update(old_env)
        mutation_ci_summary.sys.argv = old_argv


def test_mutation_ci_summary_invalid_baseline_payload_is_best_effort(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import scripts.mutation_ci_summary as mutation_ci_summary

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps({"metrics": {"total_mutants": 1}}), encoding="utf-8")
    summary_path = tmp_path / "summary.md"

    monkeypatch.setattr(
        mutation_ci_summary,
        "read_mutation_counts",
        lambda: (_ for _ in ()).throw(AssertionError("read_mutation_counts should not be called")),
    )

    old_argv = mutation_ci_summary.sys.argv
    old_env = dict(mutation_ci_summary.os.environ)
    try:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ["GITHUB_STEP_SUMMARY"] = str(summary_path)
        mutation_ci_summary.sys.argv = [
            "mutation_ci_summary.py",
            "--baseline",
            str(baseline_path),
            "--write-summary",
        ]
        assert mutation_ci_summary.main() == 0
        assert "NOT EVALUATED" in summary_path.read_text(encoding="utf-8")
    finally:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ.update(old_env)
        mutation_ci_summary.sys.argv = old_argv


def test_mutation_ci_summary_mutmut_failure_is_best_effort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.mutation_ci_summary as mutation_ci_summary

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "baseline_score": 70.0,
                "tolerance_delta": 5.0,
                "status": "active",
                "metrics": {
                    "total_mutants": 1,
                    "killed_mutants": 1,
                    "survived_mutants": 0,
                    "timeout_mutants": 0,
                    "suspicious_mutants": 0,
                    "score_percent": 100.0,
                },
            }
        ),
        encoding="utf-8",
    )
    summary_path = tmp_path / "summary.md"

    def _raise_called_process_error() -> MutationCounts:
        raise subprocess.CalledProcessError(returncode=2, cmd=["mutmut", "result-ids", "killed"])

    monkeypatch.setattr(mutation_ci_summary, "read_mutation_counts", _raise_called_process_error)

    old_argv = mutation_ci_summary.sys.argv
    old_env = dict(mutation_ci_summary.os.environ)
    try:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ["GITHUB_STEP_SUMMARY"] = str(summary_path)
        mutation_ci_summary.sys.argv = [
            "mutation_ci_summary.py",
            "--baseline",
            str(baseline_path),
            "--write-summary",
        ]
        assert mutation_ci_summary.main() == 0
        assert "NOT EVALUATED" in summary_path.read_text(encoding="utf-8")
    finally:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ.update(old_env)
        mutation_ci_summary.sys.argv = old_argv


def test_mutation_ci_summary_missing_baseline_file_is_best_effort(tmp_path: Path) -> None:
    import scripts.mutation_ci_summary as mutation_ci_summary

    missing_baseline = tmp_path / "missing-baseline.json"
    summary_path = tmp_path / "summary.md"

    old_argv = mutation_ci_summary.sys.argv
    old_env = dict(mutation_ci_summary.os.environ)
    try:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ["GITHUB_STEP_SUMMARY"] = str(summary_path)
        mutation_ci_summary.sys.argv = [
            "mutation_ci_summary.py",
            "--baseline",
            str(missing_baseline),
            "--write-summary",
        ]
        assert mutation_ci_summary.main() == 0
        assert "NOT EVALUATED" in summary_path.read_text(encoding="utf-8")
    finally:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ.update(old_env)
        mutation_ci_summary.sys.argv = old_argv


def test_mutation_ci_summary_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.mutation_ci_summary as mutation_ci_summary

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "baseline_score": 70.0,
                "tolerance_delta": 5.0,
                "status": "active",
                "metrics": {
                    "total_mutants": 1,
                    "killed_mutants": 1,
                    "survived_mutants": 0,
                    "timeout_mutants": 0,
                    "suspicious_mutants": 0,
                    "score_percent": 100.0,
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        mutation_ci_summary, "read_mutation_counts", lambda: MutationCounts(1, 0, 0, 0, 0, 0)
    )

    old_argv = mutation_ci_summary.sys.argv
    old_env = dict(mutation_ci_summary.os.environ)
    try:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ["GITHUB_OUTPUT"] = str(tmp_path / "nonexistent" / "out.txt")
        mutation_ci_summary.sys.argv = [
            "mutation_ci_summary.py",
            "--baseline",
            str(baseline_path),
            "--write-output",
        ]
        assert mutation_ci_summary.main() == 1
    finally:
        mutation_ci_summary.os.environ.clear()
        mutation_ci_summary.os.environ.update(old_env)
        mutation_ci_summary.sys.argv = old_argv
