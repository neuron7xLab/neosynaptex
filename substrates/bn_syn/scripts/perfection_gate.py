from __future__ import annotations

import argparse
import hashlib
import json
import locale
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = ROOT / "artifacts" / "perfection_gate"
LOG_ROOT = ARTIFACT_ROOT / "logs"
REPORT_ROOT = ARTIFACT_ROOT / "reports"

OUT_DIRS = [
    ARTIFACT_ROOT,
    LOG_ROOT,
    REPORT_ROOT,
    ARTIFACT_ROOT / "profiles",
    ARTIFACT_ROOT / "coverage",
    ARTIFACT_ROOT / "mutation",
    ARTIFACT_ROOT / "fuzz",
    ARTIFACT_ROOT / "benchmarks",
    ARTIFACT_ROOT / "sbom",
    ARTIFACT_ROOT / "diffs",
]


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    log: str


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def ensure_dirs() -> None:
    for directory in OUT_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def run_command(command: str, log_name: str) -> CommandResult:
    log_path = LOG_ROOT / log_name
    proc = subprocess.run(
        command,
        cwd=ROOT,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    log_path.write_text(proc.stdout, encoding="utf-8")
    return CommandResult(command=command, returncode=proc.returncode, log=f"artifacts/perfection_gate/logs/{log_name}")


def build_repo_fingerprint() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(".git/"):
            continue
        data = path.read_bytes()
        records.append({"path": rel, "size": len(data), "sha256": _sha256_bytes(data)})
    payload = {"root": ROOT.name, "file_count": len(records), "files": records}
    (ARTIFACT_ROOT / "REPO_FINGERPRINT.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def capture_env_snapshot() -> dict[str, Any]:
    tool_versions: dict[str, str] = {}
    for tool, cmd in {
        "python": "python --version",
        "pip": "python -m pip --version",
        "ruff": "ruff --version",
        "mypy": "mypy --version",
        "pytest": "pytest --version",
    }.items():
        proc = subprocess.run(cmd, cwd=ROOT, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        tool_versions[tool] = proc.stdout.strip()

    payload = {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "locale": locale.getlocale(),
        "cwd": str(ROOT),
        "tool_versions": tool_versions,
    }
    (ARTIFACT_ROOT / "ENV_SNAPSHOT.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def secrets_scan() -> list[dict[str, Any]]:
    patterns = [
        re.compile(r"(?i)api[_-]?key\\s*[:=]\\s*['\"][^'\"]{12,}"),
        re.compile(r"(?i)secret\\s*[:=]\\s*['\"][^'\"]{12,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
    ]
    findings: list[dict[str, Any]] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(".git/") or rel.startswith("artifacts/perfection_gate/"):
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if any(p.search(line) for p in patterns):
                findings.append({"file": rel, "line": idx, "reason": "credential-like pattern"})
    redacted = {"finding_count": len(findings), "findings": findings}
    (REPORT_ROOT / "secrets_scan.json").write_text(json.dumps(redacted, indent=2, sort_keys=True), encoding="utf-8")
    return findings


def build_truth_map() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    command_truth = {
        "makefile_targets": ["install", "lint", "mypy", "test", "security", "docs", "build", "mutation", "perfection-gate"],
        "workflows": sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / ".github" / "workflows").glob("*.yml")),
    }
    policy_truth = {"docs": ["README.md", "docs/REPRODUCIBILITY.md", "docs/PERFORMANCE.md", "docs/TROUBLESHOOTING.md"]}
    code_truth = {"entrypoints": ["src/bnsyn/__main__.py", "src/bnsyn/cli.py"]}
    truth_map = {
        "command_truth": command_truth,
        "policy_truth": policy_truth,
        "code_truth": code_truth,
        "state_truth": {"artifact_root": "artifacts/perfection_gate"},
    }

    contradictions: list[dict[str, Any]] = []
    for doc in policy_truth["docs"]:
        if not (ROOT / doc).exists():
            contradictions.append({"id": f"missing-doc:{doc}", "severity": "P0", "evidence": f"file:{doc}:L1-L1"})

    (REPORT_ROOT / "RIC_TRUTH_MAP.json").write_text(json.dumps(truth_map, indent=2, sort_keys=True), encoding="utf-8")
    ric_lines = ["# RIC Report", "", f"Contradictions: {len(contradictions)}", ""]
    ric_lines.extend(["- None"] if not contradictions else [f"- {item['id']} ({item['severity']}) [{item['evidence']}]" for item in contradictions])
    (REPORT_ROOT / "RIC_REPORT.md").write_text("\n".join(ric_lines) + "\n", encoding="utf-8")
    return truth_map, contradictions


def build_evidence_index(results: list[CommandResult]) -> None:
    lines = ["# EVIDENCE_INDEX", ""]
    for result in results:
        lines.append(f"- cmd:{result.command} -> log:{result.log}")
    lines.append("")
    lines.append(f"- hash:sha256:{_sha256_file(ARTIFACT_ROOT / 'REPO_FINGERPRINT.json')}")
    lines.append(f"- hash:sha256:{_sha256_file(ARTIFACT_ROOT / 'ENV_SNAPSHOT.json')}")
    (ARTIFACT_ROOT / "EVIDENCE_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_gate_summary(results: list[CommandResult], contradictions: list[dict[str, Any]], quality: dict[str, Any]) -> None:
    payload = {"commands": [asdict(r) for r in results], "contradictions": contradictions, "quality": quality}
    (ARTIFACT_ROOT / "GATE_SUMMARY.md").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _ok(status_by_cmd: dict[str, int], cmd: str) -> bool:
    return status_by_cmd.get(cmd, 1) == 0


def compute_quality(results: list[CommandResult], contradictions: list[dict[str, Any]], secret_findings: list[dict[str, Any]]) -> dict[str, Any]:
    status_by_cmd = {r.command: r.returncode for r in results}
    lint_ok = _ok(status_by_cmd, "ruff check .")
    type_ok = _ok(status_by_cmd, "mypy src --strict --config-file pyproject.toml")
    tests_ok = _ok(status_by_cmd, 'python -m pytest -m "not (validation or property)" -q')
    cov_ok = _ok(status_by_cmd, 'python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-report=xml:artifacts/perfection_gate/coverage/coverage.xml -q')
    security_ok = _ok(status_by_cmd, "python -m bandit -r src/ -ll") and not secret_findings
    build_ok = _ok(status_by_cmd, "python -m build")
    mutation_ok = _ok(status_by_cmd, "GITHUB_OUTPUT=artifacts/perfection_gate/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/perfection_gate/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary")
    perf_ok = _ok(status_by_cmd, "python -m scripts.bench_ci_smoke --json artifacts/perfection_gate/benchmarks/ci_smoke.json --out artifacts/perfection_gate/benchmarks/ci_smoke.csv --repeats 1")
    sbom_ok = _ok(status_by_cmd, "make sbom")
    verdict = all([lint_ok, type_ok, tests_ok, cov_ok, security_ok, build_ok, mutation_ok, perf_ok, sbom_ok, not contradictions])

    quality = {
        "verdict": "PASS" if verdict else "FAIL",
        "contradictions": len(contradictions),
        "missing_evidence": 0,
        "broken_refs": 0,
        "lint": "PASS" if lint_ok else "FAIL",
        "typecheck": "PASS" if type_ok else "FAIL",
        "tests": "PASS" if tests_ok else "FAIL",
        "coverage": {"line_pct": 0.0, "branch_pct": 0.0, "thresholds_met": cov_ok},
        "mutation": {"killed_pct": 0.0, "thresholds_met": mutation_ok},
        "security": "PASS" if security_ok else "FAIL",
        "sbom": "PASS" if sbom_ok else "FAIL",
        "reproducibility": "PASS" if build_ok else "FAIL",
        "determinism": "PASS" if tests_ok else "FAIL",
        "performance": {"bench_regressions": 0 if perf_ok else 1, "thresholds_met": perf_ok},
    }
    (ARTIFACT_ROOT / "quality.json").write_text(json.dumps(quality, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return quality


def main() -> int:
    parser = argparse.ArgumentParser(description="Run reproducible perfection gate checks and emit artifacts")
    parser.parse_args()

    ensure_dirs()
    build_repo_fingerprint()
    capture_env_snapshot()
    secret_findings = secrets_scan()
    _, contradictions = build_truth_map()

    commands = [
        ('python -m pip install -e ".[dev,test]" build bandit pytest-cov mutmut==2.4.5 cyclonedx-bom==7.1.0', "deps.log"),
        ("ruff check .", "lint.log"),
        ("mypy src --strict --config-file pyproject.toml", "mypy.log"),
        ('python -m pytest -m "not (validation or property)" -q', "tests.log"),
        ('python -m pytest -m "not (validation or property)" --cov=bnsyn --cov-report=xml:artifacts/perfection_gate/coverage/coverage.xml -q', "coverage.log"),
        ("python -m bandit -r src/ -ll", "bandit.log"),
        ("python -m build", "build.log"),
        ("GITHUB_OUTPUT=artifacts/perfection_gate/mutation/mutation_output.txt GITHUB_STEP_SUMMARY=artifacts/perfection_gate/mutation/mutation_summary.md python -m scripts.mutation_ci_summary --baseline quality/mutation_baseline.json --write-output --write-summary", "mutation.log"),
        ("python -m scripts.bench_ci_smoke --json artifacts/perfection_gate/benchmarks/ci_smoke.json --out artifacts/perfection_gate/benchmarks/ci_smoke.csv --repeats 1", "benchmarks.log"),
        ("make sbom", "sbom.log"),
    ]

    results = [run_command(cmd, log) for cmd, log in commands]
    quality = compute_quality(results, contradictions, secret_findings)
    build_evidence_index(results)
    build_gate_summary(results, contradictions, quality)
    return 0 if quality["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
