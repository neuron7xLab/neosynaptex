"""Deterministic CI failure intelligence summary generator.

This script is intentionally stdlib-only and resilient to missing inputs.
Missing artifacts are recorded as structured errors with explicit codes.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import tempfile
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

try:
    from defusedxml.common import DefusedXmlException
    from defusedxml.ElementTree import ParseError, parse

    HAS_DEFUSEDXML = True
    DEFUSEDXML_ERR = None
except (ImportError, ModuleNotFoundError) as exc:  # pragma: no cover - exercised via unit test monkeypatch
    HAS_DEFUSEDXML = False
    DEFUSEDXML_ERR = repr(exc)
    parse = None  # type: ignore
    ParseError = Exception  # type: ignore
    DefusedXmlException = Exception  # type: ignore


DEFAULT_MAX_LINES = 300
DEFAULT_MAX_BYTES = 200_000
TOP_FAILURE_LIMIT = 10


def _truncate_text(raw: str, max_lines: int, max_bytes: int) -> str:
    lines = (raw or "").splitlines()
    truncated_lines: list[str] = lines[:max_lines]
    joined = "\n".join(truncated_lines)
    if len(joined.encode("utf-8")) > max_bytes:
        encoded = joined.encode("utf-8")[:max_bytes]
        joined = encoded.decode("utf-8", errors="ignore")
    return joined.strip()


def _discover_file(explicit: str | None, patterns: Sequence[str]) -> str | None:
    if explicit and os.path.isfile(explicit):
        return explicit
    for pattern in patterns:
        for path in sorted(glob.glob(pattern, recursive=True)):
            if os.path.isfile(path):
                return path
    return None


def parse_junit(path: str | None, max_lines: int, max_bytes: int) -> list[dict[str, str]]:
    if not HAS_DEFUSEDXML or not path or not os.path.isfile(path):
        return []
    try:
        tree = parse(path)
    except (ParseError, DefusedXmlException):
        return []
    root = tree.getroot()
    candidates: list[dict[str, str]] = []
    for case in root.iter("testcase"):
        node = case.find("failure")
        if node is None:
            node = case.find("error")
        if node is None:
            continue
        name = case.get("name") or ""
        classname = case.get("classname") or ""
        file_path = case.get("file") or ""
        test_id = f"{classname}::{name}" if classname else name
        message = (node.get("message") or "").strip()
        trace = _truncate_text((node.text or "").strip(), max_lines, max_bytes)
        candidates.append(
            {
                "id": test_id,
                "file": file_path,
                "message": message,
                "trace": trace,
            }
        )
    failures = sorted(candidates, key=lambda item: item.get("id") or "")
    return failures[:TOP_FAILURE_LIMIT]


def parse_coverage(path: str | None) -> float | None:
    if not HAS_DEFUSEDXML or not path or not os.path.isfile(path):
        return None
    try:
        tree = parse(path)
    except (ParseError, DefusedXmlException):
        return None
    root = tree.getroot()
    rate = root.attrib.get("line-rate")
    if rate is None:
        return None
    try:
        return round(float(rate) * 100, 2)
    except ValueError:
        return None


def _read_changed_files(path: str | None) -> list[str]:
    if not path or not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8", errors="ignore") as handle:
        return [line.strip() for line in handle.readlines() if line.strip()]


def _collect_logs(glob_pattern: str | None, max_lines: int, max_bytes: int) -> dict[str, str]:
    if not glob_pattern:
        return {}
    logs: dict[str, str] = {}
    for log_path in sorted(glob.glob(glob_pattern, recursive=True)):
        if not os.path.isfile(log_path):
            continue
        with open(log_path, encoding="utf-8", errors="ignore") as handle:
            content = handle.read()
        logs[log_path] = _truncate_text(content, max_lines, max_bytes)
    return logs


def classify_failure(
    failures: Sequence[dict[str, str]],
    logs: dict[str, str],
) -> dict[str, str]:
    if not failures and not logs:
        return {"category": "pass", "reason": "No failures detected"}

    combined_text = " ".join(
        [
            *(f.get("message", "") for f in failures),
            *(f.get("trace", "") for f in failures),
            *logs.values(),
        ]
    ).lower()

    for keyword in ("connection refused", "network unreachable", "timeout connecting", "rate limit"):
        if keyword in combined_text:
            return {"category": "infra", "reason": f"Detected infra keyword '{keyword}'"}

    for keyword in ("ruff", "mypy", "flake8", "static analysis"):
        if keyword in combined_text:
            return {"category": "static analysis", "reason": f"Detected static analysis keyword '{keyword}'"}

    file_counts: dict[str, int] = {}
    for failure in failures:
        file_path = failure.get("file") or ""
        if file_path:
            file_counts[file_path] = file_counts.get(file_path, 0) + 1
    if any(count > 1 for count in file_counts.values()):
        return {"category": "deterministic test", "reason": "Repeated failures within the same test file"}

    for keyword in ("flaky", "intermittent", "timed out", "timeout", "race", "retry"):
        if keyword in combined_text:
            return {"category": "possible flake", "reason": f"Detected flake keyword '{keyword}'"}

    return {"category": "deterministic test", "reason": "Test failures without infra/static indicators"}


def _extract_module(path: str) -> str:
    parts = [p for p in Path(path).parts if p]
    if not parts:
        return path
    # Use up to three segments to capture paths like src/mlsdm/module
    return "/".join(parts[:3])


def impacted_modules(failures: Sequence[dict[str, str]], changed_files: Sequence[str]) -> list[str]:
    fail_paths = {f.get("file") for f in failures if f.get("file")}
    modules: list[str] = []
    for path in fail_paths:
        module = _extract_module(path)
        if module not in modules:
            modules.append(module)
    intersecting: list[str] = []
    for changed in changed_files:
        changed_path = Path(changed)
        for fail_path in fail_paths:
            if not fail_path:
                continue
            fail_dir = Path(fail_path).parent
            if fail_dir == Path("."):
                continue
            if changed_path.is_relative_to(fail_dir):
                module = _extract_module(changed)
                if module not in intersecting:
                    intersecting.append(module)
    return intersecting or modules


def available_repro_commands() -> list[str]:
    makefile_path = "Makefile"
    commands: list[str] = []
    if os.path.isfile(makefile_path):
        with open(makefile_path, encoding="utf-8", errors="ignore") as handle:
            content = handle.read()
        if re.search(r"^test-fast:", content, flags=re.MULTILINE):
            commands.append("make test-fast")
        if re.search(r"^lint:", content, flags=re.MULTILINE):
            commands.append("make lint")
        if re.search(r"^type:", content, flags=re.MULTILINE):
            commands.append("make type")
    if not commands:
        commands.append("python -m pytest -q")
    return commands


def _redact(text: str) -> str:
    patterns = [
        (r"ghp_[A-Za-z0-9]{10,}", "ghp_[REDACTED]"),
        (r"Bearer\s+[A-Za-z0-9._-]+", "Bearer [REDACTED]"),
        (r"AWS_SECRET_ACCESS_KEY[^\s]*", "AWS_SECRET_ACCESS_KEY[REDACTED]"),
        (r"BEGIN PRIVATE KEY[^-]*END PRIVATE KEY", "[REDACTED PRIVATE KEY]"),
    ]
    redacted = text
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    return redacted


def _redact_structure(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _redact_structure(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_structure(v) for v in value]
    if isinstance(value, str):
        return _redact(value)
    return value


def write_outputs(markdown: str, json_obj: dict[str, Any], out_path: str, json_path: str) -> None:
    out_file = Path(out_path)
    json_file = Path(json_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp_md:
        tmp_md.write(markdown)
        tmp_md.flush()
        os.fsync(tmp_md.fileno())
        tmp_md_path = tmp_md.name

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp_json:
        json.dump(json_obj, tmp_json, indent=2)
        tmp_json.flush()
        os.fsync(tmp_json.fileno())
        tmp_json_path = tmp_json.name

    os.replace(tmp_md_path, out_file)
    os.replace(tmp_json_path, json_file)


def build_markdown(summary: dict[str, Any]) -> str:
    lines = []
    status = summary.get("status", "ok")
    lines.append("## Failure Intelligence")
    lines.append("")
    if status == "degraded":
        lines.append(f"**Status:** ⚠️ {status.upper()} - Some artifacts were missing")
    else:
        lines.append(f"**Status:** ✅ {status.upper()}")
    lines.append(f"**Signal:** {summary.get('signal')}")
    lines.append("")

    # Input Integrity section
    input_errors = summary.get("input_errors", [])
    if input_errors:
        lines.append("### Input Integrity")
        lines.append("")
        lines.append("The following expected inputs were missing:")
        for err in input_errors:
            code = err.get("code", "unknown")
            artifact = err.get("artifact", "unknown")
            expected_path = err.get("expected_path", "n/a")
            lines.append(f"- **{code}**: `{artifact}` (expected: `{expected_path}`)")
        lines.append("")

    lines.append("### Top Failures")
    if summary["top_failures"]:
        for failure in summary["top_failures"]:
            lines.append(f"- {failure.get('id') or 'unknown'} ({failure.get('file') or 'n/a'})")
            if failure.get("message"):
                lines.append(f"  - Message: {failure['message']}")
            if failure.get("trace"):
                lines.append("  - Traceback:")
                trace_block = textwrap.indent(failure["trace"], "    ")
                lines.append(f"```\n{trace_block}\n```")
    else:
        lines.append("- No failing tests were detected.")
    lines.append("")
    classification = summary.get("classification", {})
    lines.append(
        f"### Classification\n- Category: {classification.get('category')}\n- Reason: {classification.get('reason')}"
    )
    lines.append("")
    lines.append("### Coverage")
    coverage = summary.get("coverage_percent")
    lines.append(f"- Line coverage: {coverage if coverage is not None else 'Unavailable'}")
    lines.append("")
    lines.append("### Impacted Modules")
    if summary.get("impacted_modules"):
        for module in summary["impacted_modules"]:
            lines.append(f"- {module}")
    else:
        lines.append("- Unable to determine from available data.")
    lines.append("")
    lines.append("### Reproduce Locally")
    for command in summary.get("repro_commands", []):
        lines.append(f"- `{command}`")
    lines.append("")
    lines.append("### Evidence")
    for pointer in summary.get("evidence", []):
        lines.append(f"- {pointer}")
    if summary.get("errors"):
        lines.append("")
        lines.append("### Errors")
        for err in summary["errors"]:
            if isinstance(err, dict):
                lines.append(f"- {err.get('code', 'unknown')}: {err.get('message', str(err))}")
            else:
                lines.append(f"- {err}")
    return "\n".join(lines)


def generate_summary(
    junit_path: str | None,
    coverage_path: str | None,
    changed_files_path: str | None,
    log_glob: str | None,
    max_lines: int,
    max_bytes: int,
    expected_junit_path: str | None = None,
    expected_coverage_path: str | None = None,
) -> dict[str, Any]:
    """Generate failure intelligence summary with structured error tracking.

    Args:
        junit_path: Resolved path to junit XML (may be None if not found)
        coverage_path: Resolved path to coverage XML (may be None if not found)
        changed_files_path: Path to changed files list
        log_glob: Glob pattern for logs
        max_lines: Max lines to include in traces
        max_bytes: Max bytes for traces
        expected_junit_path: Expected junit path (for error reporting)
        expected_coverage_path: Expected coverage path (for error reporting)

    Returns:
        Summary dict with status, input_errors, and analysis results
    """
    input_errors: list[dict[str, str]] = []

    # Track missing inputs as structured errors
    # If user explicitly provided a path but it doesn't exist, report as missing
    if expected_junit_path and not os.path.isfile(expected_junit_path):
        input_errors.append({
            "code": "input_missing",
            "artifact": "junit",
            "expected_path": expected_junit_path,
        })

    if expected_coverage_path and not os.path.isfile(expected_coverage_path):
        input_errors.append({
            "code": "input_missing",
            "artifact": "coverage",
            "expected_path": expected_coverage_path,
        })

    if changed_files_path and not os.path.isfile(changed_files_path):
        input_errors.append({
            "code": "input_missing",
            "artifact": "changed_files",
            "expected_path": changed_files_path,
        })

    # Sort for deterministic output
    input_errors.sort(key=lambda e: (e.get("artifact", ""), e.get("code", "")))

    failures = parse_junit(junit_path, max_lines, max_bytes)
    coverage_percent = parse_coverage(coverage_path)
    changed_files = _read_changed_files(changed_files_path)
    logs = _collect_logs(log_glob, max_lines, max_bytes)
    classification = classify_failure(failures, logs)
    modules = impacted_modules(failures, changed_files)

    # Determine status based on input availability
    status = "degraded" if input_errors else "ok"

    summary: dict[str, Any] = {
        "status": status,
        "signal": "Failures detected" if failures else "No failures detected",
        "top_failures": failures,
        "coverage_percent": coverage_percent,
        "classification": classification,
        "impacted_modules": modules,
        "repro_commands": available_repro_commands(),
        "evidence": [p for p in (junit_path, coverage_path, changed_files_path) if p and os.path.isfile(p)],
        "input_errors": input_errors,
        "errors": [],
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic failure intelligence summary.")
    parser.add_argument("--junit", help="Path to junit XML file", default=None)
    parser.add_argument("--coverage", help="Path to coverage XML file", default=None)
    parser.add_argument("--changed-files", help="Path to file containing changed files list", default=None)
    parser.add_argument("--logs", help="Glob pattern to include log snippets", default=None)
    parser.add_argument("--out", required=True, help="Output markdown summary path")
    parser.add_argument("--json", required=True, dest="json_out", help="Output JSON summary path")
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args()

    # Always create initial stub outputs
    try:
        write_outputs("## Failure Intelligence\n\nStarting...", {"status": "started"}, args.out, args.json_out)
    except Exception:
        pass

    try:
        if not HAS_DEFUSEDXML:
            summary: dict[str, Any] = {
                "status": "degraded",
                "signal": "Failure intelligence unavailable",
                "top_failures": [],
                "coverage_percent": None,
                "classification": {"category": "pass", "reason": "defusedxml missing; parsing skipped"},
                "impacted_modules": [],
                "repro_commands": available_repro_commands(),
                "evidence": [],
                "input_errors": [],
                "errors": [{"code": "defusedxml_missing", "message": DEFUSEDXML_ERR}],
            }
        else:
            # Store expected paths for error reporting
            expected_junit = args.junit
            expected_coverage = args.coverage

            junit_path = _discover_file(
                args.junit,
                patterns=[
                    "junit.xml",
                    "test-results.xml",
                    "artifacts/junit*.xml",
                    "reports/junit*.xml",
                    "**/junit*.xml",
                ],
            )
            coverage_path = _discover_file(
                args.coverage, patterns=["coverage.xml", "reports/coverage.xml", "**/coverage.xml"]
            )

            summary = generate_summary(
                junit_path=junit_path,
                coverage_path=coverage_path,
                changed_files_path=args.changed_files,
                log_glob=args.logs,
                max_lines=args.max_lines,
                max_bytes=args.max_bytes,
                expected_junit_path=expected_junit,
                expected_coverage_path=expected_coverage,
            )
        redacted_summary = _redact_structure(summary)
        markdown = build_markdown(redacted_summary)
        write_outputs(markdown, redacted_summary, args.out, args.json_out)
    except Exception as exc:  # pragma: no cover - exercised via integration path
        error_text = _truncate_text(repr(exc), args.max_lines, args.max_bytes)
        fallback_summary: dict[str, Any] = {
            "status": "degraded",
            "signal": "Failure intelligence error",
            "top_failures": [],
            "coverage_percent": None,
            "classification": {"category": "deterministic test", "reason": "internal error"},
            "impacted_modules": [],
            "repro_commands": available_repro_commands(),
            "evidence": [],
            "input_errors": [],
            "errors": [{"code": "internal_error", "message": error_text}],
        }
        redacted_summary = _redact_structure(fallback_summary)
        markdown = build_markdown(redacted_summary)
        try:
            write_outputs(markdown, redacted_summary, args.out, args.json_out)
        except Exception:
            # Last resort: attempt minimal writes
            Path(args.out).write_text(markdown, encoding="utf-8")
            Path(args.json_out).write_text(json.dumps(redacted_summary), encoding="utf-8")
    # Never propagate exceptions


if __name__ == "__main__":
    main()
