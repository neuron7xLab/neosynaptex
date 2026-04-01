"""Contract tests for Pytest Failure Diagnostic Aggregator."""

from __future__ import annotations

import json
from pathlib import Path

from bnsyn.qa.pytest_failure_diagnostics import generate_diagnostics

SCHEMA = Path("schemas/pytest-failure-diagnostics.schema.json")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_multiple_failures_and_kind_differentiation(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    log = tmp_path / "pytest.log"
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    _write(
        junit,
        """
<testsuites>
  <testsuite name="suite-b" tests="1" failures="1" errors="0" skipped="0">
    <testcase classname="tests.test_b" name="test_z" file="tests/test_b.py"><failure message="failed">tb-b</failure></testcase>
  </testsuite>
  <testsuite name="suite-a" tests="1" failures="0" errors="1" skipped="0">
    <testcase classname="tests.test_a" name="test_a" file="tests/test_a.py"><error message="errored">tb-a</error></testcase>
  </testsuite>
</testsuites>
""".strip(),
    )
    _write(log, "FAILED tests/test_b.py::test_z\nERROR tests/test_a.py::test_a")

    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=1,
        schema_path=SCHEMA,
        log_file=log,
    )
    assert payload["status"] == "failures_detected"
    assert payload["summary"] == {"tests_total": 2, "failures": 1, "errors": 1, "skipped": 0}
    failures = payload["failures"]
    assert isinstance(failures, list)
    assert [item["nodeid"] for item in failures] == ["tests/test_a.py::test_a", "tests/test_b.py::test_z"]
    assert [item["kind"] for item in failures] == ["error", "failure"]


def test_malformed_junit_fail_closed(tmp_path: Path) -> None:
    junit = tmp_path / "broken.xml"
    _write(junit, "<testsuites><bad")
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=2,
        schema_path=SCHEMA,
    )
    assert payload["status"] == "input_error"
    assert payload["pytest_exit_code"] == 2
    assert "input_error" in payload


def test_clean_junit_and_markdown_repro(tmp_path: Path) -> None:
    junit = tmp_path / "clean.xml"
    _write(
        junit,
        """
<testsuite name="suite" tests="1" failures="0" errors="0" skipped="0">
  <testcase classname="tests.test_ok" name="test_ok" file="tests/test_ok.py" />
</testsuite>
""".strip(),
    )
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=0,
        schema_path=SCHEMA,
    )
    assert payload["status"] == "clean"
    assert payload["failures"] == []
    assert "No failures detected." in out_md.read_text(encoding="utf-8")


def test_deterministic_clipping_and_markdown_contains_reproduce(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    long_text = "x" * 2000
    _write(
        junit,
        f"""
<testsuite name="suite" tests="1" failures="1" errors="0" skipped="0">
  <testcase classname="tests.test_long" name="test_long" file="tests/test_long.py">
    <failure message="msg">{long_text}</failure>
  </testcase>
</testsuite>
""".strip(),
    )
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=1,
        schema_path=SCHEMA,
    )
    first = payload["failures"][0]
    assert first["traceback_excerpt"].endswith("...")
    assert len(first["traceback_excerpt"]) == 1200
    markdown = out_md.read_text(encoding="utf-8")
    assert "tests/test_long.py::test_long" in markdown
    assert "python -m pytest -q tests/test_long.py::test_long" in markdown


def test_redaction_applies_to_excerpts_and_junit_unchanged(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    secret = "ghp_abcdefghijklmnopqrstuvwxyz123456"
    _write(
        junit,
        f"""
<testsuite name="suite" tests="1" failures="1" errors="0" skipped="0">
  <testcase classname="tests.test_secret" name="test_secret" file="tests/test_secret.py">
    <failure message="Bearer {secret}">{secret}</failure>
  </testcase>
</testsuite>
""".strip(),
    )
    original = junit.read_text(encoding="utf-8")
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=1,
        schema_path=SCHEMA,
    )
    failure = payload["failures"][0]
    assert "ghp_" not in failure["message"]
    assert "ghp_" not in failure["traceback_excerpt"]
    assert junit.read_text(encoding="utf-8") == original


def test_missing_root_counters_are_summed(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    _write(
        junit,
        """
<testsuites>
  <testsuite name="one" tests="2" failures="1" errors="0" skipped="0" />
  <testsuite name="two" tests="3" failures="0" errors="1" skipped="1" />
</testsuites>
""".strip(),
    )
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=1,
        schema_path=SCHEMA,
    )
    assert payload["summary"] == {"tests_total": 5, "failures": 1, "errors": 1, "skipped": 1}


def test_json_output_deterministic_order(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    _write(
        junit,
        """
<testsuite name="suite" tests="2" failures="2" errors="0" skipped="0">
  <testcase classname="tests.test_o" name="test_b" file="tests/test_o.py"><failure message="m">tb</failure></testcase>
  <testcase classname="tests.test_o" name="test_a" file="tests/test_o.py"><failure message="m">tb</failure></testcase>
</testsuite>
""".strip(),
    )
    out1 = tmp_path / "1.json"
    md1 = tmp_path / "1.md"
    out2 = tmp_path / "2.json"
    md2 = tmp_path / "2.md"

    generate_diagnostics(junit_xml=junit, output_json=out1, output_md=md1, pytest_exit_code=1, schema_path=SCHEMA)
    generate_diagnostics(junit_xml=junit, output_json=out2, output_md=md2, pytest_exit_code=1, schema_path=SCHEMA)
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")
    assert md1.read_text(encoding="utf-8") == md2.read_text(encoding="utf-8")


def test_publication_metadata_written_and_schema_valid(tmp_path: Path) -> None:
    from bnsyn.qa.pytest_failure_diagnostics import PublicationOptions

    junit = tmp_path / "junit.xml"
    _write(
        junit,
        """
<testsuite name="suite" tests="1" failures="1" errors="0" skipped="0">
  <testcase classname="tests.test_meta" name="test_meta" file="tests/test_meta.py"><failure message="boom">tb</failure></testcase>
</testsuite>
""".strip(),
    )
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    annotations = tmp_path / "ann.txt"
    summary = tmp_path / "summary.md"

    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=1,
        schema_path=SCHEMA,
        publication=PublicationOptions(
            annotations_file=annotations,
            emit_github_annotations=False,
            max_annotations=1,
            github_step_summary=summary,
        ),
    )
    assert "publication" in payload
    assert payload["publication"]["annotations_file"] == str(annotations)
    assert payload["publication"]["github_step_summary"] == str(summary)


def test_bounded_tail_log_enrichment_match_in_tail(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    nodeid = "tests/test_tail.py::test_tail"
    _write(
        junit,
        """
<testsuite name="suite" tests="1" failures="1" errors="0" skipped="0">
  <testcase classname="tests.test_tail" name="test_tail" file="tests/test_tail.py">
    <failure message="failed">tb</failure>
  </testcase>
</testsuite>
""".strip(),
    )
    log = tmp_path / "pytest.log"
    # Force nodeid to exist only near the end of a file larger than 5MiB.
    prefix = ("x" * (5 * 1024 * 1024 + 1024)) + "\n"
    suffix = f"FAILED {nodeid} - assertion\n"
    log.write_text(prefix + suffix, encoding="utf-8")

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=1,
        schema_path=SCHEMA,
        log_file=log,
    )
    assert payload["failures"][0]["raw_text_excerpt"] is not None
    assert nodeid in payload["failures"][0]["raw_text_excerpt"]


def test_bounded_tail_log_enrichment_match_outside_tail_is_safe(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    nodeid = "tests/test_old.py::test_old"
    _write(
        junit,
        """
<testsuite name="suite" tests="1" failures="1" errors="0" skipped="0">
  <testcase classname="tests.test_old" name="test_old" file="tests/test_old.py">
    <failure message="failed">tb</failure>
  </testcase>
</testsuite>
""".strip(),
    )
    log = tmp_path / "pytest.log"
    log.write_text(f"FAILED {nodeid}\n" + ("y" * (5 * 1024 * 1024 + 2048)), encoding="utf-8")

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=1,
        schema_path=SCHEMA,
        log_file=log,
    )
    assert payload["failures"][0]["raw_text_excerpt"] is None


def test_parse_junit_xml_fallback_without_defusedxml(monkeypatch: object) -> None:
    import builtins
    from bnsyn.qa import pytest_failure_diagnostics as diag

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):
        if name.startswith('defusedxml'):
            raise ModuleNotFoundError('simulated missing defusedxml')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', fake_import)
    root = diag._parse_junit_xml('<testsuite tests="0" failures="0" errors="0" skipped="0"/>')
    assert root.tag == 'testsuite'


def test_missing_junit_input_is_fail_closed_with_explicit_context(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xml"
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    payload = generate_diagnostics(
        junit_xml=missing,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=2,
        schema_path=SCHEMA,
    )

    assert payload["status"] == "input_error"
    assert payload["input_error"]["type"] == "FileNotFoundError"
    assert str(missing) in payload["input_error"]["message"]


def test_empty_junit_input_is_fail_closed_with_explicit_context(tmp_path: Path) -> None:
    junit = tmp_path / "empty.xml"
    _write(junit, "   \n")
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    payload = generate_diagnostics(
        junit_xml=junit,
        output_json=out_json,
        output_md=out_md,
        pytest_exit_code=2,
        schema_path=SCHEMA,
    )

    assert payload["status"] == "input_error"
    assert payload["input_error"]["type"] == "ValueError"
    assert "JUnit XML input is empty" in payload["input_error"]["message"]
