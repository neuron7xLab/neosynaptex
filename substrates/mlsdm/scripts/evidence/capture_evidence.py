#!/usr/bin/env python3
"""Capture reproducible evidence snapshot (coverage + JUnit logs only).

Modes:
- build: run commands locally if outputs are missing, then pack.
- pack: never re-run tests; only package provided outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, MutableMapping

SCHEMA_VERSION = "evidence-v1"
REQUIRED_OUTPUT_KEYS = ("coverage_xml", "junit_xml")
OPTIONAL_INPUT_KEYS = {
    "benchmark_metrics": "benchmark-metrics.json",
    "raw_latency": "raw_neuro_engine_latency.json",
    "memory_footprint": "memory_footprint.json",
    "iteration_metrics": "iteration-metrics.jsonl",
}
OPTIONAL_DESTS = {
    "benchmark_metrics": Path("benchmarks") / "benchmark-metrics.json",
    "raw_latency": Path("benchmarks") / "raw_neuro_engine_latency.json",
    "memory_footprint": Path("memory") / "memory_footprint.json",
    "iteration_metrics": Path("iteration") / "iteration-metrics.jsonl",
}
DEFAULT_INPUTS = {
    "coverage_xml": "coverage.xml",
    "coverage_log": "coverage-gate.log",
    "junit_xml": "reports/junit.xml",
    "unit_log": "reports/unit-tests.log",
    **OPTIONAL_INPUT_KEYS,
}


class CaptureError(Exception):
    """Raised when evidence capture fails."""


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def source_ref() -> str:
    ref = os.getenv("GITHUB_REF")
    if ref:
        return ref
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


def _prefer_uv(command: list[str]) -> list[str]:
    """Prefix command with `uv run` if available to mirror CI."""
    if os.getenv("DISABLE_UV_RUN"):
        return command
    if shutil.which("uv"):
        return ["uv", "run", *command]
    return command


def run_command(command: list[str], log_path: Path) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        command,
        cwd=repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    log_path.write_text(
        "COMMAND: "
        + " ".join(command)
        + "\n\nSTDOUT:\n"
        + result.stdout
        + "\nSTDERR:\n"
        + result.stderr
        + f"\nEXIT CODE: {result.returncode}\n",
        encoding="utf-8",
    )
    return result


def _uv_lock_sha256() -> str:
    lock = repo_root() / "uv.lock"
    if not lock.exists():
        return "missing"
    try:
        return hashlib.sha256(lock.read_bytes()).hexdigest()
    except Exception:
        return "unreadable"


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def capture_coverage(
    evidence_dir: Path,
    produced: list[Path],
    outputs: MutableMapping[str, str],
    coverage_path: Path,
    coverage_log: Path | None,
) -> None:
    dest_dir = evidence_dir / "coverage"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not coverage_path.exists():
        raise CaptureError("coverage.xml not found at expected path")
    dest_cov = dest_dir / "coverage.xml"
    shutil.copy(coverage_path, dest_cov)
    produced.append(dest_cov)
    outputs["coverage_xml"] = str(dest_cov.relative_to(evidence_dir))
    _copy_log_file(
        evidence_dir,
        produced,
        outputs,
        "coverage_log",
        coverage_log,
        Path("logs") / "coverage_gate.log",
    )


def capture_pytest_junit(
    evidence_dir: Path,
    produced: list[Path],
    outputs: MutableMapping[str, str],
    junit_path: Path,
    unit_log: Path | None,
) -> None:
    dest_dir = evidence_dir / "pytest"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not junit_path.exists():
        raise CaptureError("junit.xml not found at expected path")
    dest_junit = dest_dir / "junit.xml"
    shutil.copy(junit_path, dest_junit)
    produced.append(dest_junit)
    outputs["junit_xml"] = str(dest_junit.relative_to(evidence_dir))
    _copy_log_file(
        evidence_dir,
        produced,
        outputs,
        "unit_log",
        unit_log,
        Path("logs") / "unit_tests.log",
    )


def _record_output(
    evidence_dir: Path, produced: list[Path], outputs: MutableMapping[str, str], key: str, dest_path: Path
) -> None:
    produced.append(dest_path)
    outputs[key] = str(dest_path.relative_to(evidence_dir))


def _copy_optional(
    evidence_dir: Path,
    produced: list[Path],
    outputs: MutableMapping[str, str],
    key: str,
    source_path: Path,
    dest_rel: Path,
) -> None:
    if not source_path.exists():
        return
    dest_path = evidence_dir / dest_rel
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.resolve() != dest_path.resolve():
        shutil.copy(source_path, dest_path)
    _record_output(evidence_dir, produced, outputs, key, dest_path)


def _copy_log_file(
    evidence_dir: Path,
    produced: list[Path],
    outputs: MutableMapping[str, str],
    key: str,
    source_path: Path | None,
    dest_rel: Path,
) -> None:
    if source_path is None or not source_path.exists():
        return
    dest_path = evidence_dir / dest_rel
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.resolve() != dest_path.resolve():
        shutil.copy(source_path, dest_path)
    _record_output(evidence_dir, produced, outputs, key, dest_path)


def capture_env(evidence_dir: Path, produced: list[Path], outputs: MutableMapping[str, str]) -> None:
    env_dir = evidence_dir / "env"
    env_dir.mkdir(parents=True, exist_ok=True)
    py_path = env_dir / "python_version.txt"
    uv_lock_path = env_dir / "uv_lock_sha256.txt"
    uname_path = env_dir / "uname.txt"
    py_path.write_text(sys.version.split()[0] + "\n", encoding="utf-8")
    uv_lock_path.write_text(_uv_lock_sha256() + "\n", encoding="utf-8")
    try:
        uname_output = subprocess.run(["uname", "-a"], capture_output=True, text=True, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        uname_output = "unknown"
    uname_path.write_text(uname_output + "\n", encoding="utf-8")
    produced.extend([py_path, uv_lock_path])
    outputs["python_version"] = str(py_path.relative_to(evidence_dir))
    outputs["uv_lock_sha256"] = str(uv_lock_path.relative_to(evidence_dir))
    outputs["uname"] = str(uname_path.relative_to(evidence_dir))


def _build_file_index(evidence_dir: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(p for p in evidence_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(evidence_dir)
        entries.append(
            {
                "path": str(rel),
                "sha256": _hash_file(path),
                "bytes": path.stat().st_size,
                "mime_guess": _guess_mime(path),
            }
        )
    return entries


def write_manifest(
    evidence_dir: Path,
    sha: str,
    short_sha: str,
    commands: Iterable[str],
    outputs: Mapping[str, str],
    failures: list[str],
) -> None:
    file_index = _build_file_index(evidence_dir)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "git_sha": sha,
        "short_sha": short_sha,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_ref": source_ref(),
        "commands": list(commands),
        "outputs": dict(outputs),
        "status": {
            "ok": len(failures) == 0,
            "partial": len(failures) > 0,
            "failures": failures,
        },
        "file_index": file_index,
    }
    (evidence_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture evidence snapshot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        default="build",
        choices=["build", "pack"],
        help="build: run commands locally if outputs missing; pack: never rerun tests",
    )
    parser.add_argument(
        "--inputs",
        type=Path,
        help="JSON file describing existing outputs (coverage_xml, junit_xml, logs)",
    )
    parser.add_argument(
        "--partial-reason",
        action="append",
        default=[],
        help="Mark snapshot partial with the given reason (may be repeated)",
    )
    return parser.parse_args()


def _load_inputs(inputs_path: Path | None) -> dict[str, Path]:
    data = dict(DEFAULT_INPUTS)
    if inputs_path:
        loaded = json.loads(inputs_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise CaptureError("--inputs JSON must be an object")
        for key, value in loaded.items():
            if not isinstance(value, str):
                raise CaptureError(f"--inputs value for {key} must be a string")
            data[key] = value
    resolved: dict[str, Path] = {}
    for key, value in data.items():
        resolved[key] = (repo_root() / value).resolve() if not os.path.isabs(value) else Path(value).resolve()
    return resolved


def _ensure_outputs_present(inputs: Mapping[str, Path]) -> None:
    missing = []
    for key in REQUIRED_OUTPUT_KEYS:
        path = inputs.get(key)
        if path is None or not Path(path).exists():
            missing.append(key)
    if missing:
        raise CaptureError(f"Required inputs missing: {', '.join(missing)}")


def _maybe_run_commands(
    mode: str,
    commands: list[str],
    produced: list[Path],
    outputs: MutableMapping[str, str],
    inputs: MutableMapping[str, Path],
    evidence_dir: Path,
    failures: list[str],
) -> None:
    if mode == "pack":
        return

    coverage_path = inputs["coverage_xml"]
    junit_path = inputs["junit_xml"]

    # Avoid re-running expensive commands if outputs already exist
    if coverage_path.exists() and junit_path.exists():
        return

    coverage_log = evidence_dir / "logs" / "coverage_gate.log"
    command = _prefer_uv(["bash", "./coverage_gate.sh"])
    commands.append(" ".join(command))
    result_cov = run_command(command, coverage_log)
    produced.append(coverage_log)
    inputs["coverage_xml"] = repo_root() / "coverage.xml"
    inputs["coverage_log"] = coverage_log

    reports_dir = repo_root() / "reports"
    reports_dir.mkdir(exist_ok=True)
    junit_path = reports_dir / "junit.xml"
    unit_log = evidence_dir / "logs" / "unit_tests.log"
    command_unit = _prefer_uv(
        [
            "python",
            "-m",
            "pytest",
            "tests/unit",
            "-q",
            "--junitxml",
            str(junit_path),
            "--maxfail=1",
        ]
    )
    commands.append(" ".join(command_unit))
    result_unit = run_command(command_unit, unit_log)
    produced.append(unit_log)
    inputs["junit_xml"] = junit_path
    inputs["unit_log"] = unit_log

    if result_cov.returncode != 0:
        failures.append(f"coverage gate failed (exit {result_cov.returncode})")
    if result_unit.returncode != 0:
        failures.append(f"unit tests failed (exit {result_unit.returncode})")


def main() -> int:
    args = parse_args()
    root = repo_root()
    os.chdir(root)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sha_full = git_sha()
    short_sha = sha_full[:12] if sha_full != "unknown" else "unknown"
    base_dir = root / "artifacts" / "evidence" / date_str
    temp_dir = Path(tempfile.mkdtemp(prefix="evidence-"))
    evidence_dir = temp_dir

    commands: list[str] = []
    produced: list[Path] = []
    outputs: dict[str, str] = {}
    failures: list[str] = list(args.partial_reason)

    try:
        inputs = _load_inputs(args.inputs)
        _maybe_run_commands(args.mode, commands, produced, outputs, inputs, evidence_dir, failures)
        _ensure_outputs_present(inputs)
        capture_coverage(evidence_dir, produced, outputs, inputs["coverage_xml"], inputs.get("coverage_log"))
        capture_pytest_junit(evidence_dir, produced, outputs, inputs["junit_xml"], inputs.get("unit_log"))
        capture_env(evidence_dir, produced, outputs)
        for key, dest in OPTIONAL_DESTS.items():
            _copy_optional(evidence_dir, produced, outputs, key, inputs[key], dest)
    except (CaptureError, OSError, ValueError) as exc:
        failures.append(str(exc))
        print(f"ERROR: {exc}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"unexpected error: {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
    finally:
        try:
            write_manifest(evidence_dir, sha_full, short_sha, commands, outputs, failures)
        except (OSError, ValueError) as exc:
            print(f"ERROR writing manifest: {exc}", file=sys.stderr)

    final_dir = base_dir / short_sha
    base_dir.mkdir(parents=True, exist_ok=True)
    if final_dir.exists():
        shutil.rmtree(final_dir)
    shutil.move(str(temp_dir), final_dir)

    print(f"Evidence captured at {final_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
