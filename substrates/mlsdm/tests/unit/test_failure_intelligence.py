import json
from pathlib import Path

from scripts.ci.failure_intelligence import (
    _redact,
    build_markdown,
    generate_summary,
)


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_parses_junit_and_coverage(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    write_file(
        junit,
        """
        <testsuite>
          <testcase classname="pkg.test_sample" name="test_one" file="tests/unit/test_sample.py">
            <failure message="assert 1 == 0">Traceback line 1
Traceback line 2</failure>
          </testcase>
          <testcase classname="pkg.test_sample" name="test_two" file="tests/unit/test_sample.py">
            <error message="boom">Error line 1</error>
          </testcase>
        </testsuite>
        """,
    )
    coverage = tmp_path / "coverage.xml"
    write_file(
        coverage,
        '<coverage line-rate="0.85" branch-rate="0.1" version="1.0"></coverage>',
    )
    changed_files = tmp_path / "changed.txt"
    write_file(changed_files, "tests/unit/test_sample.py\nsrc/mlsdm/core/module.py\n")

    summary = generate_summary(
        junit_path=str(junit),
        coverage_path=str(coverage),
        changed_files_path=str(changed_files),
        log_glob=None,
        max_lines=50,
        max_bytes=5_000,
    )

    assert summary["signal"] == "Failures detected"
    assert summary["classification"]["category"] == "deterministic test"
    assert summary["coverage_percent"] == 85.0
    assert summary["top_failures"][0]["id"] == "pkg.test_sample::test_one"
    assert "Traceback line 1" in summary["top_failures"][0]["trace"]
    assert summary["impacted_modules"]


def test_redaction_and_markdown(tmp_path: Path):
    sensitive_text = "token ghp_1234567890 and Bearer secretvalue"
    redacted = _redact(sensitive_text)
    assert "REDACTED" in redacted
    data = {
        "signal": "No failures detected",
        "top_failures": [],
        "classification": {"category": "pass", "reason": "ok"},
        "coverage_percent": None,
        "impacted_modules": [],
        "repro_commands": ["make test-fast"],
        "evidence": [],
    }
    md = build_markdown(data)
    assert "Failure Intelligence" in md
    out_md = tmp_path / "summary.md"
    out_json = tmp_path / "summary.json"
    out_md.write_text(md, encoding="utf-8")
    out_json.write_text(json.dumps(data), encoding="utf-8")
    assert out_md.exists()
    assert out_json.exists()


def test_handles_missing_inputs(tmp_path: Path):
    md_path = tmp_path / "summary.md"
    json_path = tmp_path / "summary.json"
    summary = generate_summary(
        junit_path="nonexistent.xml",
        coverage_path="missing.xml",
        changed_files_path=None,
        log_glob=None,
        max_lines=10,
        max_bytes=1000,
    )
    md = build_markdown(summary)
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(summary), encoding="utf-8")
    assert summary["signal"] == "No failures detected"
    assert md_path.read_text(encoding="utf-8")
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["signal"] == "No failures detected"


def test_rejects_malicious_xml(tmp_path: Path):
    # Billion laughs style payload should be ignored safely
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version="1.0"?>
<!DOCTYPE lolz [
 <!ENTITY lol "lol">
 <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
]>
<testsuite>
  <testcase classname="pkg.test_sample" name="test_one" file="tests/unit/test_sample.py">
    <failure message="boom">&lol1;</failure>
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )
    summary = generate_summary(
        junit_path=str(junit),
        coverage_path=None,
        changed_files_path=None,
        log_glob=None,
        max_lines=50,
        max_bytes=5_000,
    )
    # defusedxml should block entity expansion and return no failures
    assert summary["top_failures"] == []
