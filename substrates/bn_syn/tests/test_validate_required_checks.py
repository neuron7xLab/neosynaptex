from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_required_checks import (
    RequiredChecksParseError,
    load_required_checks,
    main,
    validate_required_checks,
)


def _write_required_checks(path: Path, workflows: list[str], *, version: str = "1") -> None:
    lines = [f"version: '{version}'", "required_checks:"]
    lines.extend(f"  - workflow_file: {workflow}" for workflow in workflows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_contracts(path: Path, rows: list[str]) -> None:
    path.write_text(
        "\n".join(
            [
                "# Workflow Contracts",
                "",
                "| Workflow file | Workflow name | Gate Class | Trigger set | Reusable? |",
                "| --- | --- | --- | --- | --- |",
                *rows,
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_load_required_checks_rejects_duplicate_workflow_file(tmp_path: Path) -> None:
    path = tmp_path / "REQUIRED_CHECKS.yml"
    _write_required_checks(path, ["ci-pr-atomic.yml", "ci-pr-atomic.yml"])

    with pytest.raises(RequiredChecksParseError, match="Duplicate workflow_file"):
        load_required_checks(path)


def test_load_required_checks_rejects_non_mapping_yaml_root(tmp_path: Path) -> None:
    path = tmp_path / "REQUIRED_CHECKS.yml"
    path.write_text("- foo\n- bar\n", encoding="utf-8")

    with pytest.raises(RequiredChecksParseError, match="must be a mapping"):
        load_required_checks(path)


def test_validate_required_checks_reports_missing_and_extra(tmp_path: Path) -> None:
    required_checks = tmp_path / "REQUIRED_CHECKS.yml"
    contracts = tmp_path / "WORKFLOW_CONTRACTS.md"
    _write_required_checks(required_checks, ["ci-pr-atomic.yml", "extra.yml"])
    _write_contracts(
        contracts,
        [
            "| `ci-pr-atomic.yml` | `ci-pr-atomic` | PR-gate | `pull_request` | NO |",
            "| `required.yml` | `required` | PR-gate | `pull_request` | NO |",
        ],
    )

    violations = validate_required_checks(required_checks, contracts)

    assert any("REQUIRED_CHECKS_MISMATCH" in violation for violation in violations)
    assert "VIOLATION: REQUIRED_CHECKS_MISSING workflows=['required.yml']" in violations
    assert "VIOLATION: REQUIRED_CHECKS_EXTRA workflows=['extra.yml']" in violations


def test_main_supports_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["validate_required_checks", "--help"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Usage: python -m scripts.validate_required_checks" in captured.out


def test_main_rejects_unexpected_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["validate_required_checks", "unexpected"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "Usage: python -m scripts.validate_required_checks" in captured.out


def test_main_returns_parse_error_code_for_invalid_required_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    github = tmp_path / ".github"
    github.mkdir(parents=True)
    (github / "REQUIRED_CHECKS.yml").write_text("- invalid\n", encoding="utf-8")
    _write_contracts(
        github / "WORKFLOW_CONTRACTS.md",
        ["| `ci-pr-atomic.yml` | `ci-pr-atomic` | PR-gate | `pull_request` | NO |"],
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["validate_required_checks"])

    captured = capsys.readouterr()
    assert exit_code == 3
    assert "VIOLATION: PARSE_ERROR" in captured.out


def test_main_returns_mismatch_exit_code_and_messages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    github = tmp_path / ".github"
    github.mkdir(parents=True)
    _write_required_checks(github / "REQUIRED_CHECKS.yml", ["ci-pr-atomic.yml", "extra.yml"])
    _write_contracts(
        github / "WORKFLOW_CONTRACTS.md",
        [
            "| `ci-pr-atomic.yml` | `ci-pr-atomic` | PR-gate | `pull_request` | NO |",
            "| `required.yml` | `required` | PR-gate | `pull_request` | NO |",
        ],
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["validate_required_checks"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "VIOLATION: REQUIRED_CHECKS_MISMATCH" in captured.out
    assert "VIOLATION: REQUIRED_CHECKS_MISSING workflows=['required.yml']" in captured.out
    assert "VIOLATION: REQUIRED_CHECKS_EXTRA workflows=['extra.yml']" in captured.out


def test_main_success_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    github = tmp_path / ".github"
    github.mkdir(parents=True)
    _write_required_checks(github / "REQUIRED_CHECKS.yml", ["ci-pr-atomic.yml"])
    _write_contracts(
        github / "WORKFLOW_CONTRACTS.md",
        ["| `ci-pr-atomic.yml` | `ci-pr-atomic` | PR-gate | `pull_request` | NO |"],
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["validate_required_checks"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "OK: required_checks=1 contract_pr_gates=1 validated" in captured.out
