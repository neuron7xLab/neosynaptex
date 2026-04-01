import json
import sys
from pathlib import Path

import scripts.ci.failure_intelligence as fi


def run_main(tmp_path: Path, args: list[str]) -> dict:
    out_md = tmp_path / "out.md"
    out_json = tmp_path / "out.json"
    argv = ["prog", "--out", str(out_md), "--json", str(out_json), *args]
    original = list(sys.argv)
    sys.argv = argv
    try:
        fi.main()
    finally:
        sys.argv = original
    assert out_md.exists()
    assert out_json.exists()
    return json.loads(out_json.read_text(encoding="utf-8"))


def test_missing_defusedxml_writes_outputs(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(fi, "HAS_DEFUSEDXML", False)
    monkeypatch.setattr(fi, "DEFUSEDXML_ERR", "ImportError('defusedxml')")
    monkeypatch.setattr(fi, "parse", None, raising=False)
    summary = run_main(tmp_path, [])
    # Check that errors contains structured error with defusedxml_missing code
    errors = summary.get("errors", [])
    assert any(
        isinstance(e, dict) and e.get("code") == "defusedxml_missing" for e in errors
    ), f"Expected defusedxml_missing error in {errors}"
    assert summary["signal"].startswith("Failure intelligence")
    assert summary.get("status") == "degraded"


def test_corrupt_xml_is_handled(tmp_path: Path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<testsuite><testcase></testsuite", encoding="utf-8")
    summary = run_main(tmp_path, ["--junit", str(bad)])
    assert summary["top_failures"] == []


def test_happy_path_outputs(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
        <testsuite>
          <testcase classname="pkg.test_sample" name="test_one" file="tests/unit/test_sample.py">
            <failure message="assert 1 == 0">Traceback line 1</failure>
          </testcase>
        </testsuite>
        """,
        encoding="utf-8",
    )
    coverage = tmp_path / "coverage.xml"
    coverage.write_text('<coverage line-rate="0.5" branch-rate="0.1" version="1.0"></coverage>', encoding="utf-8")
    summary = run_main(tmp_path, ["--junit", str(junit), "--coverage", str(coverage)])
    assert summary["coverage_percent"] == 50.0
    assert summary["top_failures"][0]["id"] == "pkg.test_sample::test_one"
    assert summary.get("status") == "ok"
    assert summary.get("input_errors", []) == []


def test_missing_junit_produces_structured_error(tmp_path: Path):
    """When junit path is explicitly provided but missing, produces structured error."""
    missing_path = str(tmp_path / "nonexistent-junit.xml")
    summary = run_main(tmp_path, ["--junit", missing_path])

    # Status should be degraded
    assert summary.get("status") == "degraded"

    # input_errors should contain structured error
    input_errors = summary.get("input_errors", [])
    assert len(input_errors) == 1
    assert input_errors[0]["code"] == "input_missing"
    assert input_errors[0]["artifact"] == "junit"
    assert input_errors[0]["expected_path"] == missing_path

    # Script should still exit successfully (outputs exist)
    # This is already checked by run_main


def test_missing_coverage_produces_structured_error(tmp_path: Path):
    """When coverage path is explicitly provided but missing, produces structured error."""
    missing_path = str(tmp_path / "nonexistent-coverage.xml")
    summary = run_main(tmp_path, ["--coverage", missing_path])

    # Status should be degraded
    assert summary.get("status") == "degraded"

    # input_errors should contain structured error
    input_errors = summary.get("input_errors", [])
    assert len(input_errors) == 1
    assert input_errors[0]["code"] == "input_missing"
    assert input_errors[0]["artifact"] == "coverage"
    assert input_errors[0]["expected_path"] == missing_path


def test_multiple_missing_artifacts_produces_sorted_errors(tmp_path: Path):
    """When multiple artifacts are missing, errors are sorted deterministically."""
    missing_junit = str(tmp_path / "missing-junit.xml")
    missing_cov = str(tmp_path / "missing-coverage.xml")
    summary = run_main(tmp_path, ["--junit", missing_junit, "--coverage", missing_cov])

    # Status should be degraded
    assert summary.get("status") == "degraded"

    # input_errors should contain both errors, sorted alphabetically by artifact name
    input_errors = summary.get("input_errors", [])
    assert len(input_errors) == 2
    # Sorted by artifact: coverage < junit (alphabetical)
    assert input_errors[0]["artifact"] == "coverage"
    assert input_errors[1]["artifact"] == "junit"


def test_missing_changed_files_produces_structured_error(tmp_path: Path):
    """When changed-files path is explicitly provided but missing, produces structured error."""
    missing_path = str(tmp_path / "nonexistent-changed.txt")
    summary = run_main(tmp_path, ["--changed-files", missing_path])

    # Status should be degraded
    assert summary.get("status") == "degraded"

    # input_errors should contain structured error
    input_errors = summary.get("input_errors", [])
    assert len(input_errors) == 1
    assert input_errors[0]["code"] == "input_missing"
    assert input_errors[0]["artifact"] == "changed_files"


def test_markdown_includes_input_integrity_section(tmp_path: Path):
    """Markdown output includes Input Integrity section when artifacts are missing."""
    out_md = tmp_path / "out.md"
    missing_path = str(tmp_path / "missing.xml")
    run_main(tmp_path, ["--junit", missing_path])

    md_content = out_md.read_text(encoding="utf-8")
    assert "### Input Integrity" in md_content
    assert "input_missing" in md_content
    assert "junit" in md_content
