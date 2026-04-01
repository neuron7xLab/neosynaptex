#!/usr/bin/env python3
"""Validate evidence snapshot completeness, determinism, and safety."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from defusedxml import ElementTree

SCHEMA_VERSION = "evidence-v1"
REQUIRED_OUTPUTS = {
    "coverage_xml": "coverage/coverage.xml",
    "junit_xml": "pytest/junit.xml",
}
OPTIONAL_OUTPUT_PREFIXES = {
    "benchmark_metrics": "benchmarks/benchmark-metrics.json",
    "raw_latency": "benchmarks/raw_neuro_engine_latency.json",
    "memory_footprint": "memory/memory_footprint.json",
    "uname": "env/uname.txt",
    "iteration_metrics": "iteration/iteration-metrics.jsonl",
}
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB per file
MAX_TOTAL_BYTES = 5 * 1024 * 1024  # 5 MB total snapshot
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"(?i)aws_secret_access_key"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),  # GitHub token
    re.compile(r"-----BEGIN PRIVATE KEY-----"),
    re.compile(r"api[_-]?key\s*[:=]\s*[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{10,}"),
]


def _hash_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class EvidenceError(Exception):
    """Raised when evidence validation fails."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"manifest is not valid JSON: {path}") from exc


def _validate_manifest(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    required_keys = (
        "schema_version",
        "git_sha",
        "short_sha",
        "created_utc",
        "source_ref",
        "commands",
        "outputs",
        "status",
        "file_index",
    )
    for key in required_keys:
        if key not in data:
            raise EvidenceError(f"manifest.json missing required key '{key}'")

    if data["schema_version"] != SCHEMA_VERSION:
        raise EvidenceError(
            f"manifest.json schema_version is '{data['schema_version']}', expected '{SCHEMA_VERSION}'"
        )

    if not isinstance(data["commands"], list) or not all(isinstance(cmd, str) for cmd in data["commands"]):
        raise EvidenceError("manifest.json 'commands' must be a list of strings")

    outputs = data["outputs"]
    if not isinstance(outputs, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in outputs.items()):
        raise EvidenceError("manifest.json 'outputs' must be a mapping of strings")

    status = data["status"]
    if not isinstance(status, dict):
        raise EvidenceError("manifest.json 'status' must be an object")
    for key in ("ok", "partial", "failures"):
        if key not in status:
            raise EvidenceError(f"manifest.json 'status' missing key '{key}'")
    if not isinstance(status["ok"], bool) or not isinstance(status["partial"], bool):
        raise EvidenceError("manifest.json status.ok and status.partial must be booleans")
    if not isinstance(status["failures"], list) or not all(isinstance(err, str) for err in status["failures"]):
        raise EvidenceError("manifest.json status.failures must be a list of strings")
    if status["ok"] == status["partial"]:
        raise EvidenceError("manifest.json status.ok and status.partial must not be equal")
    if status["partial"] and not status["failures"]:
        raise EvidenceError("manifest.json partial snapshots must list failures")

    file_index = data["file_index"]
    if not isinstance(file_index, list):
        raise EvidenceError("manifest.json 'file_index' must be a list")
    for entry in file_index:
        if not isinstance(entry, dict):
            raise EvidenceError("manifest.json file_index entries must be objects")
        for key in ("path", "sha256", "bytes", "mime_guess"):
            if key not in entry:
                raise EvidenceError(f"manifest.json file_index entry missing key '{key}'")
        if not isinstance(entry["path"], str) or not isinstance(entry["sha256"], str):
            raise EvidenceError("manifest.json file_index path/sha256 must be strings")
        if not isinstance(entry["bytes"], int) or entry["bytes"] < 0:
            raise EvidenceError("manifest.json file_index bytes must be a non-negative integer")
        if not isinstance(entry["mime_guess"], str):
            raise EvidenceError("manifest.json file_index mime_guess must be a string")

    return data


def _parse_coverage_percent(path: Path) -> float:
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        raise EvidenceError(f"coverage.xml is not valid XML: {exc}") from exc

    line_rate = root.attrib.get("line-rate")
    if line_rate is None:
        raise EvidenceError("coverage.xml missing 'line-rate' attribute")
    try:
        rate = float(line_rate)
    except ValueError as exc:
        raise EvidenceError(f"coverage.xml line-rate must be numeric (got {line_rate!r})") from exc
    if math.isnan(rate):
        raise EvidenceError("coverage.xml line-rate is NaN")
    if rate < 0 or rate > 1:
        raise EvidenceError(f"coverage.xml line-rate out of bounds: {rate}")
    return rate * 100.0


def _aggregate_tests(element: ElementTree.Element) -> tuple[int, int, int, int]:
    tests = int(element.attrib.get("tests", 0))
    failures = int(element.attrib.get("failures", 0))
    errors = int(element.attrib.get("errors", 0))
    skipped = int(element.attrib.get("skipped", element.attrib.get("skip", 0)))
    for child in element.findall("testsuite"):
        c_tests, c_failures, c_errors, c_skipped = _aggregate_tests(child)
        tests += c_tests
        failures += c_failures
        errors += c_errors
        skipped += c_skipped
    return tests, failures, errors, skipped


def _parse_junit(path: Path) -> tuple[int, int, int, int]:
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        raise EvidenceError(f"junit.xml is not valid XML: {exc}") from exc

    if root.tag not in {"testsuite", "testsuites"}:
        raise EvidenceError(f"junit.xml has unexpected root tag '{root.tag}'")

    totals = _aggregate_tests(root)
    if totals[0] <= 0:
        raise EvidenceError("junit.xml reports zero tests")
    return totals


def _resolve_under(evidence_dir: Path, rel: str) -> Path:
    candidate = (evidence_dir / rel).resolve()
    if not str(candidate).startswith(str(evidence_dir.resolve())):
        raise EvidenceError(f"Path escapes evidence directory: {rel}")
    return candidate


def _ensure_outputs_valid(evidence_dir: Path, outputs: dict[str, str]) -> None:
    allowed_optional = {
        "coverage_log",
        "unit_log",
        "python_version",
        "uv_lock_sha256",
        *OPTIONAL_OUTPUT_PREFIXES.keys(),
    }
    allowed_prefixes = tuple(OPTIONAL_OUTPUT_PREFIXES.values())
    for key, expected_rel in REQUIRED_OUTPUTS.items():
        if key not in outputs:
            raise EvidenceError(f"manifest.outputs missing required key '{key}'")
        if outputs[key] != expected_rel:
            raise EvidenceError(f"manifest.outputs.{key} must be '{expected_rel}' (got '{outputs[key]}')")

    for key, rel in outputs.items():
        if Path(rel).is_absolute():
            raise EvidenceError(f"manifest.outputs contains absolute path: {rel}")
        target = _resolve_under(evidence_dir, rel)
        if not target.exists():
            raise EvidenceError(f"manifest.outputs references missing file: {rel}")
        if key not in REQUIRED_OUTPUTS and key not in allowed_optional and not any(
            rel.startswith(prefix) for prefix in allowed_prefixes
        ):
            raise EvidenceError(f"manifest.outputs contains unexpected key '{key}'")


def _check_file_index(evidence_dir: Path, file_index: list[dict[str, Any]]) -> None:
    indexed_paths = set()
    total_bytes = 0
    actual_files = {str(p.relative_to(evidence_dir)) for p in evidence_dir.rglob("*") if p.is_file()}

    for entry in file_index:
        rel = entry["path"]
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise EvidenceError(f"file_index contains unsafe path: {rel}")
        target = _resolve_under(evidence_dir, rel)
        if not target.exists():
            raise EvidenceError(f"file_index references missing file: {rel}")
        if rel in indexed_paths:
            raise EvidenceError(f"file_index contains duplicate path: {rel}")
        computed_size = target.stat().st_size
        computed_hash = _hash_file(target)
        if computed_size != entry["bytes"]:
            raise EvidenceError(f"file_index bytes mismatch for {rel}: {entry['bytes']} != {computed_size}")
        if computed_hash != entry["sha256"]:
            raise EvidenceError(f"file_index sha256 mismatch for {rel}")
        if computed_size > MAX_FILE_BYTES:
            raise EvidenceError(f"Evidence file too large (> {MAX_FILE_BYTES} bytes): {rel}")
        indexed_paths.add(rel)
        total_bytes += computed_size

    missing_from_index = actual_files - indexed_paths
    missing_from_index.discard("manifest.json")
    if missing_from_index:
        raise EvidenceError(f"file_index missing files: {sorted(missing_from_index)}")
    if total_bytes > MAX_TOTAL_BYTES:
        raise EvidenceError(f"Evidence snapshot too large (> {MAX_TOTAL_BYTES} bytes total)")


def _ensure_outputs_indexed(outputs: dict[str, str], file_index: list[dict[str, Any]]) -> None:
    indexed_paths = {entry["path"] for entry in file_index}
    for rel in outputs.values():
        if rel not in indexed_paths:
            raise EvidenceError(f"manifest.outputs path not found in file_index: {rel}")


def _scan_secrets(evidence_dir: Path) -> None:
    for file_path in evidence_dir.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise EvidenceError(f"Secret-like pattern found in {file_path}")


def verify_snapshot(evidence_dir: Path) -> None:
    if not evidence_dir.is_dir():
        raise EvidenceError(f"Evidence directory not found: {evidence_dir}")

    manifest_path = evidence_dir / "manifest.json"
    if not manifest_path.exists():
        raise EvidenceError("Missing manifest.json")
    manifest = _validate_manifest(manifest_path)
    outputs = manifest["outputs"]
    _ensure_outputs_valid(evidence_dir, outputs)
    _check_file_index(evidence_dir, manifest["file_index"])
    _ensure_outputs_indexed(outputs, manifest["file_index"])
    _scan_secrets(evidence_dir)

    coverage_percent = _parse_coverage_percent(_resolve_under(evidence_dir, outputs["coverage_xml"]))
    tests, failures, errors, skipped = _parse_junit(_resolve_under(evidence_dir, outputs["junit_xml"]))

    print(f"✓ Evidence snapshot valid: {evidence_dir}")
    print(f"  Schema: {manifest['schema_version']} (status.partial={manifest['status']['partial']})")
    print(f"  Coverage: {coverage_percent:.2f}%")
    print(f"  Tests: {tests} (failures={failures}, errors={errors}, skipped={skipped})")
    print(
        f"✓ Summary: coverage={coverage_percent:.2f}%, tests={tests}, "
        f"failures={failures}, errors={errors}, skipped={skipped}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify evidence snapshot integrity")
    parser.add_argument(
        "--evidence-dir",
        required=True,
        type=Path,
        help="Path to evidence snapshot directory (artifacts/evidence/<date>/<sha>)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        verify_snapshot(args.evidence_dir)
    except EvidenceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
