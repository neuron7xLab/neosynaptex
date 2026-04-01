"""Pytest failure diagnostics aggregation and CI publication helpers.

Pytest remains the sole pass/fail source of truth. This module is additive-only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TextIO, cast

import jsonschema  # type: ignore[import-untyped]

SCHEMA_VERSION = "1.0.0"
_STATUS_CLEAN = "clean"
_STATUS_FAILURES = "failures_detected"
_STATUS_INPUT_ERROR = "input_error"
_MAX_EXCERPT = 1200
_MAX_LOG_EXCERPT = 500

_REDACTION_PATTERNS = [
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{12,}\b", flags=re.IGNORECASE),
    re.compile(r"\b[a-fA-F0-9]{32,}\b"),
    re.compile(r"\b(?:api[_-]?key|token|secret)\s*[:=]\s*[A-Za-z0-9._\-]{12,}\b", flags=re.IGNORECASE),
]


@dataclass(frozen=True)
class FailureEntry:
    nodeid: str
    file: str
    classname: str
    test_name: str
    kind: str
    message: str
    traceback_excerpt: str
    raw_text_excerpt: str | None
    reproduce: str
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None
    suite_name: str | None = None


@dataclass(frozen=True)
class PublicationOptions:
    annotations_file: Path | None = None
    emit_github_annotations: bool = False
    max_annotations: int = 10
    github_step_summary: Path | None = None


@dataclass(frozen=True)
class RunResult:
    pytest_exit_code: int
    diagnostics_exit_code: int


def _clip(text: str, limit: int = _MAX_EXCERPT) -> str:
    stripped = text.strip()
    return stripped if len(stripped) <= limit else stripped[: limit - 3] + "..."


def _safe_int(value: str | None) -> int:
    try:
        return int(value) if value is not None else 0
    except ValueError:
        return 0


def _redact_text(text: str) -> str:
    redacted = text
    for pattern in _REDACTION_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _ensure_redacted(text: str | None) -> str | None:
    if text is None:
        return None
    try:
        return _redact_text(text)
    except Exception:
        return "[REDACTION_ERROR]"


def _load_schema(schema_path: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    return loaded


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_tail(path: Path, max_bytes: int = 5 * 1024 * 1024) -> str:
    """Read a bounded UTF-8 tail from a file deterministically.

    If seeking starts mid-line, the first partial line is discarded.
    """
    file_size = path.stat().st_size
    if file_size <= max_bytes:
        return path.read_text(encoding="utf-8", errors="replace")

    start = file_size - max_bytes
    with path.open("rb") as handle:
        handle.seek(start)
        chunk = handle.read(max_bytes)

    if start > 0:
        newline_idx = chunk.find(b"\n")
        if newline_idx == -1:
            return ""
        chunk = chunk[newline_idx + 1 :]

    return chunk.decode("utf-8", errors="replace")



def _parse_junit_xml(xml_text: str) -> ET.Element:
    """Parse JUnit XML safely when defusedxml is available."""
    try:
        from defusedxml import ElementTree as defused_et  # type: ignore[import-untyped]

        return cast(ET.Element, defused_et.fromstring(xml_text))
    except ModuleNotFoundError:
        # Local pytest-generated JUnit input; fallback used only when defusedxml is unavailable.
        return ET.fromstring(xml_text)  # nosec B314

def _collect_suites(root: ET.Element) -> list[ET.Element]:
    if root.tag == "testsuite":
        return [root]
    if root.tag == "testsuites":
        return list(root.findall("testsuite"))
    raise ValueError(f"Unsupported JUnit root element: {root.tag}")


def _extract_summary(root: ET.Element) -> dict[str, int]:
    tests_total = _safe_int(root.attrib.get("tests"))
    failures = _safe_int(root.attrib.get("failures"))
    errors = _safe_int(root.attrib.get("errors"))
    skipped = _safe_int(root.attrib.get("skipped"))

    if tests_total == failures == errors == skipped == 0:
        for suite in _collect_suites(root):
            tests_total += _safe_int(suite.attrib.get("tests"))
            failures += _safe_int(suite.attrib.get("failures"))
            errors += _safe_int(suite.attrib.get("errors"))
            skipped += _safe_int(suite.attrib.get("skipped"))

    return {"tests_total": tests_total, "failures": failures, "errors": errors, "skipped": skipped}


def _build_nodeid(file_attr: str, classname: str, test_name: str) -> str:
    if test_name and "::" in test_name:
        return test_name
    if file_attr and test_name:
        return f"{file_attr}::{test_name}"
    if file_attr:
        return file_attr
    if classname and test_name:
        return f"{classname.replace('.', '/')}.py::{test_name}"
    if classname:
        return classname
    return test_name or "<unknown_nodeid>"


def _extract_log_excerpt(log_text: str | None, nodeid: str) -> str | None:
    if not log_text:
        return None
    found = re.search(re.escape(nodeid), log_text)
    if found is None:
        return None
    start = max(0, found.start() - 200)
    end = min(len(log_text), found.end() + 300)
    return _clip(log_text[start:end], _MAX_LOG_EXCERPT)


def _extract_failures(root: ET.Element, log_text: str | None) -> list[FailureEntry]:
    entries: list[FailureEntry] = []
    for suite in _collect_suites(root):
        suite_name = suite.attrib.get("name")
        for testcase in suite.findall("testcase"):
            failure_el = testcase.find("failure")
            error_el = testcase.find("error")
            if failure_el is None and error_el is None:
                continue

            detail = failure_el if failure_el is not None else error_el
            assert detail is not None
            kind = "failure" if failure_el is not None else "error"

            file_attr = testcase.attrib.get("file", "")
            classname = testcase.attrib.get("classname", "")
            test_name = testcase.attrib.get("name", "")
            nodeid = _build_nodeid(file_attr, classname, test_name)

            entries.append(
                FailureEntry(
                    nodeid=nodeid,
                    file=file_attr,
                    classname=classname,
                    test_name=test_name,
                    kind=kind,
                    message=detail.attrib.get("message", ""),
                    traceback_excerpt=_clip(detail.text or ""),
                    raw_text_excerpt=_extract_log_excerpt(log_text, nodeid),
                    reproduce=f"python -m pytest -q {nodeid}",
                    stdout_excerpt=_clip(testcase.findtext("system-out") or "") if testcase.findtext("system-out") else None,
                    stderr_excerpt=_clip(testcase.findtext("system-err") or "") if testcase.findtext("system-err") else None,
                    suite_name=suite_name,
                )
            )

    return sorted(entries, key=lambda x: (x.nodeid, x.kind, x.message))


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Pytest Failure Diagnostic Aggregator",
        "",
        f"- schema_version: `{payload['schema_version']}`",
        f"- status: `{payload['status']}`",
        f"- pytest_exit_code: `{payload['pytest_exit_code']}`",
        f"- tests_total: `{summary['tests_total']}`",
        f"- failures: `{summary['failures']}`",
        f"- errors: `{summary['errors']}`",
        f"- skipped: `{summary['skipped']}`",
        "",
    ]

    failures: list[dict[str, Any]] = payload["failures"]
    if not failures:
        return "\n".join(lines + ["No failures detected.", ""])

    lines.extend(["## Failing tests", ""])
    for idx, failure in enumerate(failures, start=1):
        reason = failure["message"] or failure["traceback_excerpt"] or "No details available"
        lines.extend(
            [
                f"{idx}. `{failure['nodeid']}` ({failure['kind']})",
                f"   - reason: `{_clip(str(reason), 300)}`",
                f"   - reproduce: `{failure['reproduce']}`",
            ]
        )
    return "\n".join(lines + [""])


def _build_payload(
    *, status: str, pytest_exit_code: int, summary: dict[str, int], failures: list[FailureEntry], input_error: dict[str, str] | None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "pytest_exit_code": pytest_exit_code,
        "summary": summary,
        "failures": [asdict(entry) for entry in failures],
    }
    if input_error is not None:
        payload["input_error"] = input_error
    return payload


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = json.loads(json.dumps(payload))
    for failure in sanitized.get("failures", []):
        for key in ("message", "traceback_excerpt", "raw_text_excerpt", "stdout_excerpt", "stderr_excerpt"):
            failure[key] = _ensure_redacted(failure.get(key))
    if "input_error" in sanitized:
        sanitized["input_error"]["message"] = _ensure_redacted(sanitized["input_error"].get("message"))
    return sanitized


def validate_payload(payload: dict[str, Any], schema_path: Path) -> None:
    jsonschema.validate(instance=payload, schema=_load_schema(schema_path))


def _annotation_line(failure: dict[str, Any]) -> str:
    file_path = failure.get("file") or "unknown"
    nodeid = str(failure.get("nodeid", "<unknown_nodeid>"))
    message = failure.get("message") or failure.get("traceback_excerpt") or "pytest failure"
    compact = _clip(str(message), 180).replace("\n", " ")
    return f"::error file={file_path},title=pytest diagnostics::{nodeid} - {compact}"


def publish_ci_outputs(payload: dict[str, Any], options: PublicationOptions, annotation_stream: TextIO | None = None) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    failures: list[dict[str, Any]] = payload.get("failures", [])
    selected = list(failures)[: max(0, options.max_annotations)]
    annotations = [_annotation_line(item) for item in selected]

    if options.annotations_file is not None:
        options.annotations_file.parent.mkdir(parents=True, exist_ok=True)
        options.annotations_file.write_text("\n".join(annotations) + ("\n" if annotations else ""), encoding="utf-8")
        metadata["annotations_file"] = str(options.annotations_file)

    if options.emit_github_annotations:
        stream = annotation_stream if annotation_stream is not None else sys.stderr
        for line in annotations:
            print(line, file=stream)
        metadata["annotations_emitted"] = len(annotations)

    if options.github_step_summary is not None:
        options.github_step_summary.parent.mkdir(parents=True, exist_ok=True)
        summary_lines = [
            "## Pytest Failure Diagnostics",
            "",
            f"- status: `{payload['status']}`",
            f"- pytest_exit_code: `{payload['pytest_exit_code']}`",
            f"- failures: `{payload['summary']['failures']}`",
            f"- errors: `{payload['summary']['errors']}`",
        ]
        if selected:
            summary_lines.extend(["", "### Top failures"])
            for item in selected[:5]:
                summary_lines.append(f"- `{item['nodeid']}` ({item['kind']})")
        with options.github_step_summary.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(summary_lines) + "\n")
        metadata["github_step_summary"] = str(options.github_step_summary)

    return metadata


def generate_diagnostics(
    *,
    junit_xml: Path,
    output_json: Path,
    output_md: Path,
    pytest_exit_code: int,
    schema_path: Path,
    log_file: Path | None = None,
    publication: PublicationOptions | None = None,
) -> dict[str, Any]:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    try:
        xml_text = _read_text(junit_xml)
        if not xml_text.strip():
            raise ValueError(f"JUnit XML input is empty: {junit_xml}")
        root = _parse_junit_xml(xml_text)
        summary = _extract_summary(root)
        log_text = _read_tail(log_file) if log_file is not None and log_file.exists() else None
        failures = _extract_failures(root, log_text)
        payload = _build_payload(
            status=_STATUS_FAILURES if failures else _STATUS_CLEAN,
            pytest_exit_code=pytest_exit_code,
            summary=summary,
            failures=failures,
            input_error=None,
        )
    except Exception as exc:
        payload = _build_payload(
            status=_STATUS_INPUT_ERROR,
            pytest_exit_code=pytest_exit_code,
            summary={"tests_total": 0, "failures": 0, "errors": 0, "skipped": 0},
            failures=[],
            input_error={"type": exc.__class__.__name__, "message": str(exc)},
        )

    sanitized = _redact_payload(payload)
    validate_payload(sanitized, schema_path)

    output_json.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(_render_markdown(sanitized), encoding="utf-8")

    if publication is not None:
        meta = publish_ci_outputs(sanitized, publication)
        if meta:
            enriched: dict[str, Any] = json.loads(output_json.read_text(encoding="utf-8"))
            enriched["publication"] = meta
            validate_payload(enriched, schema_path)
            output_json.write_text(json.dumps(enriched, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return enriched

    return sanitized


def _schema_valid_fallback(pytest_exit_code: int, schema_path: Path, err: Exception) -> dict[str, Any]:
    fallback: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": _STATUS_INPUT_ERROR,
        "pytest_exit_code": pytest_exit_code,
        "summary": {"tests_total": 0, "failures": 0, "errors": 0, "skipped": 0},
        "failures": [],
        "input_error": {"type": err.__class__.__name__, "message": _ensure_redacted(str(err)) or "[REDACTION_ERROR]"},
    }
    validate_payload(fallback, schema_path)
    return fallback


def run_pytest_with_diagnostics(
    *,
    pytest_args: list[str],
    junit_xml: Path,
    log_file: Path,
    output_json: Path,
    output_md: Path,
    schema_path: Path,
    publication: PublicationOptions | None = None,
) -> RunResult:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    junit_xml.parent.mkdir(parents=True, exist_ok=True)

    full_cmd = [sys.executable, "-m", "pytest", *pytest_args, f"--junitxml={junit_xml}"]
    with log_file.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            sys.stdout.write(line)
            handle.write(line)
        process.wait()

    pytest_exit_code = int(process.returncode)

    diagnostics_exit_code = 0
    try:
        generate_diagnostics(
            junit_xml=junit_xml,
            output_json=output_json,
            output_md=output_md,
            pytest_exit_code=pytest_exit_code,
            schema_path=schema_path,
            log_file=log_file,
            publication=publication,
        )
    except Exception as exc:
        diagnostics_exit_code = 1
        fallback = _schema_valid_fallback(pytest_exit_code, schema_path, exc)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(fallback, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output_md.write_text("# Pytest Failure Diagnostic Aggregator\n\n- status: `input_error`\n", encoding="utf-8")
        print(f"[pytest-diagnostics] generation failed: {exc}", file=sys.stderr)

    return RunResult(pytest_exit_code=pytest_exit_code, diagnostics_exit_code=diagnostics_exit_code)
