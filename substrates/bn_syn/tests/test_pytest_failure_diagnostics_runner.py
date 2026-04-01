"""Runner integration tests for pytest diagnostics behavior."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

from bnsyn.qa.pytest_failure_diagnostics import PublicationOptions, generate_diagnostics, publish_ci_outputs

SCHEMA = Path("schemas/pytest-failure-diagnostics.schema.json")


def _run_runner(
    tmp_path: Path,
    test_code: str,
    *,
    markers: str = "",
    passthrough: list[str] | None = None,
    use_separator: bool = False,
) -> subprocess.CompletedProcess[str]:
    test_file = tmp_path / "synthetic_test.py"
    test_file.write_text(test_code, encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "scripts.run_pytest_with_diagnostics",
        "--markers",
        markers,
        "--junit",
        str(tmp_path / "junit.xml"),
        "--log",
        str(tmp_path / "pytest.log"),
        "--output-json",
        str(tmp_path / "diag.json"),
        "--output-md",
        str(tmp_path / "diag.md"),
        "--schema",
        str(SCHEMA),
    ]

    args = passthrough[:] if passthrough else [str(test_file)]
    if use_separator:
        cmd.append("--")
    cmd.extend(args)

    env = dict(os.environ)
    env["PYTHONPATH"] = f"{Path.cwd() / 'src'}:{env.get('PYTHONPATH', '')}"
    return subprocess.run(cmd, text=True, capture_output=True, check=False, env=env)


def test_runner_preserves_zero_exit_code_and_emits_artifacts(tmp_path: Path) -> None:
    result = _run_runner(tmp_path, "def test_ok():\n    assert True\n")
    assert result.returncode == 0
    assert (tmp_path / "diag.json").exists()
    assert (tmp_path / "diag.md").exists()


def test_runner_preserves_nonzero_exit_code_and_emits_artifacts(tmp_path: Path) -> None:
    result = _run_runner(tmp_path, "def test_fail():\n    assert False\n")
    assert result.returncode == 1
    payload = json.loads((tmp_path / "diag.json").read_text(encoding="utf-8"))
    assert payload["pytest_exit_code"] == 1
    assert payload["status"] == "failures_detected"


def test_runner_invalid_marker_preserves_error_semantics(tmp_path: Path) -> None:
    result = _run_runner(tmp_path, "def test_ok():\n    assert True\n", markers="(")
    assert result.returncode != 0
    payload = json.loads((tmp_path / "diag.json").read_text(encoding="utf-8"))
    assert payload["pytest_exit_code"] == result.returncode


def test_runner_passthrough_supports_flags_and_separator(tmp_path: Path) -> None:
    test_file = tmp_path / "synthetic_test.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    result = _run_runner(
        tmp_path,
        "def test_ok():\n    assert True\n",
        passthrough=[str(test_file), "-k", "test_ok"],
        use_separator=True,
    )
    assert result.returncode == 0


def test_publication_helpers_emit_bounded_deterministic_annotations_and_summary(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
<testsuite name="suite" tests="3" failures="3" errors="0" skipped="0">
  <testcase classname="t" name="test_a" file="a.py"><failure message="m">tb</failure></testcase>
  <testcase classname="t" name="test_b" file="b.py"><failure message="m">tb</failure></testcase>
  <testcase classname="t" name="test_c" file="c.py"><failure message="m">tb</failure></testcase>
</testsuite>
""".strip(),
        encoding="utf-8",
    )
    out_json = tmp_path / "diag.json"
    out_md = tmp_path / "diag.md"
    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=1,
        schema_path=SCHEMA,
    )

    annotation_stream = io.StringIO()
    annotations = tmp_path / "ann.txt"
    summary = tmp_path / "summary.md"
    meta = publish_ci_outputs(
        payload,
        PublicationOptions(
            annotations_file=annotations,
            emit_github_annotations=True,
            max_annotations=2,
            github_step_summary=summary,
        ),
        annotation_stream=annotation_stream,
    )
    assert meta["annotations_emitted"] == 2
    annotation_lines = annotations.read_text(encoding="utf-8").strip().splitlines()
    assert len(annotation_lines) == 2
    assert annotation_lines == sorted(annotation_lines)
    assert annotation_stream.getvalue().strip().splitlines() == annotation_lines
    assert "status:" in summary.read_text(encoding="utf-8")


def test_runner_internal_diagnostics_failure_writes_schema_valid_fallback(tmp_path: Path, monkeypatch) -> None:
    from bnsyn.qa import pytest_failure_diagnostics as diag

    test_file = tmp_path / "t.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    def boom(**_kwargs):
        raise RuntimeError("forced generation error")

    monkeypatch.setattr(diag, "generate_diagnostics", boom)

    result = diag.run_pytest_with_diagnostics(
        pytest_args=["-q", str(test_file)],
        junit_xml=tmp_path / "junit.xml",
        log_file=tmp_path / "pytest.log",
        output_json=tmp_path / "diag.json",
        output_md=tmp_path / "diag.md",
        schema_path=SCHEMA,
    )

    assert result.pytest_exit_code == 0
    assert result.diagnostics_exit_code == 1
    payload = json.loads((tmp_path / "diag.json").read_text(encoding="utf-8"))
    assert payload["status"] == "input_error"
    assert payload["pytest_exit_code"] == 0


def test_cli_exit_semantics_pytest_pass_diag_fail(monkeypatch, capsys) -> None:
    import scripts.run_pytest_with_diagnostics as runner
    from bnsyn.qa.pytest_failure_diagnostics import RunResult
    import bnsyn.qa.pytest_failure_diagnostics as diag

    monkeypatch.setattr(diag, "run_pytest_with_diagnostics", lambda **_kwargs: RunResult(pytest_exit_code=0, diagnostics_exit_code=3))
    monkeypatch.setattr(sys, "argv", ["run_pytest_with_diagnostics.py"])
    rc = runner.main()
    captured = capsys.readouterr()
    assert rc == 3
    assert "pytest passed but diagnostics generation failed" in captured.err


def test_cli_exit_semantics_pytest_fail_still_wins(monkeypatch) -> None:
    import scripts.run_pytest_with_diagnostics as runner
    from bnsyn.qa.pytest_failure_diagnostics import RunResult
    import bnsyn.qa.pytest_failure_diagnostics as diag

    monkeypatch.setattr(diag, "run_pytest_with_diagnostics", lambda **_kwargs: RunResult(pytest_exit_code=5, diagnostics_exit_code=2))
    monkeypatch.setattr(sys, "argv", ["run_pytest_with_diagnostics.py"])
    rc = runner.main()
    assert rc == 5



def test_reusable_workflow_invokes_authoritative_runner_with_required_paths() -> None:
    workflow = Path('.github/workflows/_reusable_pytest.yml').read_text(encoding='utf-8')
    assert 'python -m scripts.run_pytest_with_diagnostics' in workflow
    assert '--junit junit.xml' in workflow
    assert '--log pytest.log' in workflow
    assert '--output-json artifacts/tests/failure-diagnostics.json' in workflow
    assert '--output-md artifacts/tests/failure-diagnostics.md' in workflow


def test_reusable_workflow_uploads_diagnostics_artifacts() -> None:
    workflow = Path('.github/workflows/_reusable_pytest.yml').read_text(encoding='utf-8')
    assert 'name: Upload pytest diagnostics artifacts' in workflow
    assert 'artifacts/tests/failure-diagnostics.json' in workflow
    assert 'artifacts/tests/failure-diagnostics.md' in workflow


def test_reusable_workflow_uses_authoritative_result_variable_for_gating() -> None:
    workflow = Path('.github/workflows/_reusable_pytest.yml').read_text(encoding='utf-8')
    assert 'AUTHORITATIVE_RUN_RESULT=' in workflow
    assert "if: env.AUTHORITATIVE_RUN_RESULT == '0'" in workflow
    assert "if: env.AUTHORITATIVE_RUN_RESULT != '0'" in workflow
    assert 'name: Fail if authoritative run failed' in workflow
    assert 'PYTEST_RESULT' not in workflow


def test_reusable_workflow_coverage_artifact_upload_is_guarded() -> None:
    workflow = Path('.github/workflows/_reusable_pytest.yml').read_text(encoding='utf-8')
    assert "if: always() && hashFiles('coverage.xml') != ''" in workflow
    assert "if: env.AUTHORITATIVE_RUN_RESULT == '0'" in workflow


def test_reusable_workflow_failure_artifact_condition_includes_authoritative_result() -> None:
    workflow = Path('.github/workflows/_reusable_pytest.yml').read_text(encoding='utf-8')
    assert 'name: Upload artifacts on failure' in workflow
    assert "if: always() && (failure() || env.AUTHORITATIVE_RUN_RESULT != '0')" in workflow
    assert 'if: failure()' not in workflow
