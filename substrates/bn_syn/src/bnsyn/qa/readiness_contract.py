"""Execution-backed repository readiness contract for BN-Syn.

This module is the single source of truth for release readiness state.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import hashlib
import inspect
import json
from json import JSONDecodeError
import re
import shutil
import signal
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol, Sequence

from tools.entropy_gate.compute_metrics import compute_metrics, flatten

TRUTH_MODEL_VERSION = "1.2.0"
_MAX_OUTPUT_CHARS = 4000
_COMMAND_FAILURE_EXIT_CODE = 124
_REQUIRED_READINESS_STATES = frozenset({"blocked", "advisory", "ready"})
_REQUIRED_SUBSYSTEMS = (
    "static quality",
    "runtime proof path",
    "bundle validation",
    "governance consistency",
)
# Bound command timeouts tightly enough to expose regressions while still fitting
# comfortably inside the current contracts/build CI budgets.
_RUFF_TIMEOUT_SECONDS = 120.0
_MYPY_TIMEOUT_SECONDS = 180.0
_PYLINT_TIMEOUT_SECONDS = 180.0
_CANONICAL_PROOF_RUN_TIMEOUT_SECONDS = 420.0
_BUNDLE_VALIDATION_TIMEOUT_SECONDS = 120.0
TRUTH_MODEL_FINGERPRINT = "76ba615ec09b44fc"
_SCRUB_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{12,}\b", flags=re.IGNORECASE),
    re.compile(
        r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[A-Za-z0-9._/\-]{6,}\b",
        flags=re.IGNORECASE,
    ),
    re.compile(r"\b[A-Z][A-Z0-9_]{2,}=(?:[^\s]+)"),
    re.compile(r"\b(?:/workspace|/root|/tmp|/home)/[^\s]+"),
)


class ReadinessStatus(StrEnum):
    """Machine-readable readiness states."""

    BLOCKED = "blocked"
    ADVISORY = "advisory"
    READY = "ready"


@dataclass(frozen=True)
class ReadinessCheck:
    """Serializable readiness check result."""

    name: str
    kind: str
    status: str
    blocking: bool
    details: str
    command: str | None = None
    executed_command: list[str] | None = None
    exit_code: int | None = None
    duration_seconds: float | None = None
    stdout_excerpt: str | None = None
    stderr_excerpt: str | None = None
    evidence: str | None = None


@dataclass(frozen=True)
class ReadinessSubsystem:
    """Readiness subsystem containing related checks."""

    key: str
    label: str
    status: ReadinessStatus
    checks: tuple[ReadinessCheck, ...]


@dataclass(frozen=True)
class ReadinessState:
    """Aggregated readiness state for the repository."""

    truth_model_version: str
    timestamp: str
    version: str | None
    status: ReadinessStatus
    release_ready: bool
    execution_backed_pass_count: int
    blocking_failures: tuple[str, ...]
    advisory_findings: tuple[str, ...]
    subsystems: tuple[ReadinessSubsystem, ...]

    def to_report(self) -> dict[str, Any]:
        """Convert state to a JSON-serializable report."""
        return {
            "truth_model_version": self.truth_model_version,
            "timestamp": self.timestamp,
            "version": self.version,
            "state": self.status.value,
            "release_ready": self.release_ready,
            "execution_backed_pass_count": self.execution_backed_pass_count,
            "blocking_failures": list(self.blocking_failures),
            "advisory_findings": list(self.advisory_findings),
            "subsystems": [
                {
                    "key": subsystem.key,
                    "label": subsystem.label,
                    "status": subsystem.status.value,
                    "checks": [asdict(check) for check in subsystem.checks],
                }
                for subsystem in self.subsystems
            ],
        }

    @classmethod
    def evaluate(
        cls,
        repo_root: Path,
        *,
        command_runner: "CommandRunner | None" = None,
        proof_output_dir: Path | None = None,
    ) -> "ReadinessState":
        """Compute the repository readiness state."""
        runner = command_runner or SubprocessCommandRunner()
        output_dir = proof_output_dir or repo_root / "artifacts" / "release_readiness_bundle"

        with ThreadPoolExecutor(max_workers=2) as executor:
            static_quality_future: Future[ReadinessSubsystem] = executor.submit(
                _evaluate_static_quality, repo_root, runner
            )
            governance_future: Future[ReadinessSubsystem] = executor.submit(
                _evaluate_governance_consistency, repo_root
            )
            runtime_proof = _evaluate_runtime_proof_path(repo_root, output_dir, runner)
            bundle_validation = _evaluate_bundle_validation(repo_root, output_dir, runner)
            static_quality = static_quality_future.result()
            governance = governance_future.result()

        subsystems = (static_quality, runtime_proof, bundle_validation, governance)
        blocking_failures = tuple(
            f"{subsystem.label}: {check.name}"
            for subsystem in subsystems
            for check in subsystem.checks
            if check.blocking and check.status != "pass"
        )
        advisory_findings = tuple(
            f"{subsystem.label}: {check.name}"
            for subsystem in subsystems
            for check in subsystem.checks
            if not check.blocking and check.status != "pass"
        )
        execution_backed_pass_count = sum(
            1
            for subsystem in subsystems
            for check in subsystem.checks
            if check.kind == "command" and check.status == "pass"
        )

        if blocking_failures or execution_backed_pass_count == 0:
            status = ReadinessStatus.BLOCKED
        elif advisory_findings:
            status = ReadinessStatus.ADVISORY
        else:
            status = ReadinessStatus.READY

        return cls(
            truth_model_version=TRUTH_MODEL_VERSION,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            version=_read_project_version(repo_root / "pyproject.toml"),
            status=status,
            release_ready=status is ReadinessStatus.READY,
            execution_backed_pass_count=execution_backed_pass_count,
            blocking_failures=blocking_failures,
            advisory_findings=advisory_findings,
            subsystems=subsystems,
        )


@dataclass(frozen=True)
class CommandSpec:
    """Command execution specification."""

    name: str
    command: str
    argv: tuple[str, ...]
    blocking: bool = True
    cwd: Path | None = None
    timeout_seconds: float = 900.0


@dataclass(frozen=True)
class CommandOutcome:
    """Captured command execution outcome."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


@dataclass(frozen=True)
class MarkdownSection:
    """Normalized markdown heading section."""

    title: str
    level: int
    content: tuple[str, ...]


@dataclass
class MarkdownNode:
    """Minimal markdown AST node used for structural contract checks."""

    kind: str
    text: str = ""
    level: int = 0
    children: list["MarkdownNode"] = field(default_factory=list)


class CommandRunner(Protocol):
    """Protocol for executing readiness commands."""

    def run(self, spec: CommandSpec, repo_root: Path) -> CommandOutcome:
        """Execute the given command spec."""


class SubprocessCommandRunner:
    """Default subprocess-backed command runner."""

    def run(self, spec: CommandSpec, repo_root: Path) -> CommandOutcome:
        cwd = spec.cwd or repo_root
        start = perf_counter()
        try:
            completed = subprocess.run(  # nosec B603
                list(spec.argv),
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                timeout=spec.timeout_seconds,
            )
            return CommandOutcome(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_seconds=perf_counter() - start,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            detail = f"Timeout after {spec.timeout_seconds:.1f}s"
            return CommandOutcome(
                exit_code=_COMMAND_FAILURE_EXIT_CODE,
                stdout=stdout,
                stderr=_append_detail(stderr, detail),
                duration_seconds=perf_counter() - start,
            )
        except OSError as exc:
            return CommandOutcome(
                exit_code=_COMMAND_FAILURE_EXIT_CODE,
                stdout="",
                stderr=f"OS error while executing command: {exc}",
                duration_seconds=perf_counter() - start,
            )


def _append_detail(text: str, detail: str) -> str:
    stripped = text.strip()
    if not stripped:
        return detail
    return f"{stripped}\n{detail}"


def _signal_name(returncode: int) -> str:
    try:
        return signal.Signals(-returncode).name
    except ValueError:
        return f"SIG{-returncode}"


def _scrub_output(text: str, repo_root: Path) -> str:
    scrubbed = text.replace(repo_root.as_posix(), "[REPO_ROOT]")
    for pattern in _SCRUB_PATTERNS:
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    return scrubbed


def _truncate(text: str, repo_root: Path) -> str | None:
    scrubbed = _scrub_output(text, repo_root)
    stripped = scrubbed.strip()
    if not stripped:
        return None
    if len(stripped) <= _MAX_OUTPUT_CHARS:
        return stripped
    return stripped[-_MAX_OUTPUT_CHARS:]


def _command_check(
    repo_root: Path,
    runner: CommandRunner,
    spec: CommandSpec,
    *,
    evidence: str,
) -> ReadinessCheck:
    outcome = runner.run(spec, repo_root)
    status = "pass" if outcome.exit_code == 0 else "fail"
    if outcome.exit_code == 0:
        details = f"Command passed in {outcome.duration_seconds:.2f}s"
    elif outcome.exit_code < 0:
        details = (
            f"Command terminated by signal {_signal_name(outcome.exit_code)} "
            f"after {outcome.duration_seconds:.2f}s"
        )
    else:
        details = (
            f"Command failed with exit code {outcome.exit_code} "
            f"after {outcome.duration_seconds:.2f}s"
        )
    return ReadinessCheck(
        name=spec.name,
        kind="command",
        status=status,
        blocking=spec.blocking,
        details=details,
        command=spec.command,
        executed_command=list(spec.argv),
        exit_code=outcome.exit_code,
        duration_seconds=round(outcome.duration_seconds, 6),
        stdout_excerpt=_truncate(outcome.stdout, repo_root),
        stderr_excerpt=_truncate(outcome.stderr, repo_root),
        evidence=evidence,
    )


def _policy_check(
    name: str,
    *,
    status: str,
    details: str,
    blocking: bool,
    evidence: str,
) -> ReadinessCheck:
    return ReadinessCheck(
        name=name,
        kind="policy",
        status=status,
        blocking=blocking,
        details=details,
        evidence=evidence,
    )


def _subsystem_status(checks: Sequence[ReadinessCheck]) -> ReadinessStatus:
    if any(check.blocking and check.status != "pass" for check in checks):
        return ReadinessStatus.BLOCKED
    if any((not check.blocking) and check.status != "pass" for check in checks):
        return ReadinessStatus.ADVISORY
    return ReadinessStatus.READY


def _evaluate_static_quality(repo_root: Path, runner: CommandRunner) -> ReadinessSubsystem:
    checks = (
        _command_check(
            repo_root,
            runner,
            CommandSpec(
                name="ruff check",
                command="ruff check .",
                argv=(sys.executable, "-m", "ruff", "check", "."),
                timeout_seconds=_RUFF_TIMEOUT_SECONDS,
            ),
            evidence="command:ruff check .",
        ),
        _command_check(
            repo_root,
            runner,
            CommandSpec(
                name="mypy strict",
                command="mypy src --strict --config-file pyproject.toml",
                argv=(
                    sys.executable,
                    "-m",
                    "mypy",
                    "src",
                    "--strict",
                    "--config-file",
                    "pyproject.toml",
                ),
                timeout_seconds=_MYPY_TIMEOUT_SECONDS,
            ),
            evidence="command:mypy src --strict --config-file pyproject.toml",
        ),
        _command_check(
            repo_root,
            runner,
            CommandSpec(
                name="pylint src/bnsyn",
                command="pylint src/bnsyn",
                argv=(sys.executable, "-m", "pylint", "src/bnsyn"),
                timeout_seconds=_PYLINT_TIMEOUT_SECONDS,
            ),
            evidence="command:pylint src/bnsyn",
        ),
    )
    return ReadinessSubsystem(
        key="static_quality",
        label="Static quality",
        status=_subsystem_status(checks),
        checks=checks,
    )


def _evaluate_runtime_proof_path(
    repo_root: Path,
    output_dir: Path,
    runner: CommandRunner,
) -> ReadinessSubsystem:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    checks = (
        _command_check(
            repo_root,
            runner,
            CommandSpec(
                name="canonical proof run",
                command="bnsyn run --profile canonical --plot --export-proof",
                argv=(
                    sys.executable,
                    "-m",
                    "bnsyn.cli",
                    "run",
                    "--profile",
                    "canonical",
                    "--plot",
                    "--export-proof",
                    "--output",
                    output_dir.as_posix(),
                ),
                timeout_seconds=_CANONICAL_PROOF_RUN_TIMEOUT_SECONDS,
            ),
            evidence=f"command:bnsyn run --profile canonical --plot --export-proof --output {output_dir.as_posix()}",
        ),
    )
    return ReadinessSubsystem(
        key="runtime_proof_path",
        label="Runtime proof path",
        status=_subsystem_status(checks),
        checks=checks,
    )


def _evaluate_bundle_validation(
    repo_root: Path,
    output_dir: Path,
    runner: CommandRunner,
) -> ReadinessSubsystem:
    checks = (
        _command_check(
            repo_root,
            runner,
            CommandSpec(
                name="canonical bundle validation",
                command="bnsyn validate-bundle <artifact_dir>",
                argv=(
                    sys.executable,
                    "-m",
                    "bnsyn.cli",
                    "validate-bundle",
                    output_dir.as_posix(),
                ),
                timeout_seconds=_BUNDLE_VALIDATION_TIMEOUT_SECONDS,
            ),
            evidence=f"command:bnsyn validate-bundle {output_dir.as_posix()}",
        ),
    )
    return ReadinessSubsystem(
        key="bundle_validation",
        label="Bundle validation",
        status=_subsystem_status(checks),
        checks=checks,
    )


def _evaluate_governance_consistency(repo_root: Path) -> ReadinessSubsystem:
    checks = (
        check_status_document_contract(repo_root / "docs" / "STATUS.md"),
        check_release_readiness_document_contract(repo_root / "docs" / "RELEASE_READINESS.md"),
        check_mutation_baseline(repo_root / "quality" / "mutation_baseline.json"),
        check_entropy_gate(repo_root),
    )
    return ReadinessSubsystem(
        key="governance_consistency",
        label="Governance consistency",
        status=_subsystem_status(checks),
        checks=checks,
    )


def _read_project_version(path: Path) -> str | None:
    if not path.exists():
        return None
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    return str(version) if version else None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _parse_markdown_sections(text: str) -> dict[str, MarkdownSection]:
    root = MarkdownNode(kind="document")
    current_section: MarkdownNode | None = None
    in_code_fence = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            if current_section is not None:
                current_section.children.append(MarkdownNode(kind="code", text=raw_line))
            continue
        if in_code_fence:
            if current_section is not None:
                current_section.children.append(MarkdownNode(kind="code", text=raw_line))
            continue

        heading_match = re.match(r"^(#{1,6})\s+(?P<title>.+?)\s*$", stripped)
        if heading_match:
            current_section = MarkdownNode(
                kind="section",
                text=heading_match.group("title"),
                level=len(heading_match.group(1)),
            )
            root.children.append(current_section)
            continue

        if current_section is None:
            continue

        list_match = re.match(r"^(?:[-*]|\d+\.)\s+(?P<item>.+?)\s*$", stripped)
        if list_match:
            current_section.children.append(MarkdownNode(kind="list_item", text=list_match.group("item")))
            continue

        if stripped:
            current_section.children.append(MarkdownNode(kind="paragraph", text=stripped))

    sections: dict[str, MarkdownSection] = {}
    for node in root.children:
        sections[_normalize_markdown(node.text)] = MarkdownSection(
            title=node.text,
            level=node.level,
            content=tuple(child.text for child in node.children),
        )
    return sections


def _normalize_markdown(value: str) -> str:
    collapsed = " ".join(value.strip().lower().split())
    return collapsed.replace("**", "").replace("`", "")


def _extract_list_items(lines: Sequence[str]) -> list[str]:
    return [_normalize_markdown(line) for line in lines if line.strip()]


def _require_section(sections: dict[str, MarkdownSection], title: str) -> MarkdownSection | None:
    return sections.get(_normalize_markdown(title))

def _contains_phrase(lines: Sequence[str], expected: str) -> bool:
    normalized_expected = _normalize_markdown(expected)
    return any(normalized_expected in _normalize_markdown(line) for line in lines)


def check_mutation_baseline(path: Path) -> ReadinessCheck:
    if not path.exists():
        return _policy_check(
            "mutation baseline",
            status="fail",
            details=f"Missing {path}",
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )

    try:
        data = _load_json(path)
    except (OSError, ValueError, JSONDecodeError) as exc:
        return _policy_check(
            "mutation baseline",
            status="fail",
            details=f"Unreadable mutation baseline: {exc}",
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )
    status = data.get("status")
    metrics = data.get("metrics", {})
    total_mutants = metrics.get("total_mutants")
    killed_mutants = metrics.get("killed_mutants")
    if status != "active" or not isinstance(total_mutants, int) or total_mutants <= 0:
        return _policy_check(
            "mutation baseline",
            status="fail",
            details=(
                "Mutation baseline must be active with total_mutants > 0 "
                f"(status={status!r}, total_mutants={total_mutants!r})"
            ),
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )
    if not isinstance(killed_mutants, int) or killed_mutants <= 0:
        return _policy_check(
            "mutation baseline",
            status="fail",
            details=f"metrics.killed_mutants must be > 0 (killed_mutants={killed_mutants!r})",
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )
    return _policy_check(
        "mutation baseline",
        status="pass",
        details=(
            f"Baseline active with total_mutants={total_mutants} and killed_mutants={killed_mutants}"
        ),
        blocking=True,
        evidence=f"file:{path.as_posix()}",
    )


def check_entropy_gate(repo_root: Path) -> ReadinessCheck:
    policy_path = repo_root / "entropy" / "policy.json"
    baseline_path = repo_root / "entropy" / "baseline.json"
    if not policy_path.exists() or not baseline_path.exists():
        missing = [
            candidate.as_posix()
            for candidate in (policy_path, baseline_path)
            if not candidate.exists()
        ]
        return _policy_check(
            "entropy gate",
            status="fail",
            details=f"Missing entropy inputs: {', '.join(missing)}",
            blocking=True,
            evidence="files:entropy/policy.json,entropy/baseline.json",
        )

    try:
        policy = _load_json(policy_path)
        baseline = _load_json(baseline_path)
    except (OSError, ValueError, JSONDecodeError) as exc:
        return _policy_check(
            "entropy gate",
            status="fail",
            details=f"Unreadable entropy inputs: {exc}",
            blocking=True,
            evidence="files:entropy/policy.json,entropy/baseline.json",
        )
    comparators = policy.get("comparators", {})
    if not isinstance(comparators, dict) or not comparators:
        return _policy_check(
            "entropy gate",
            status="fail",
            details="policy.json comparators missing or empty",
            blocking=True,
            evidence="file:entropy/policy.json",
        )

    current = compute_metrics(repo_root)
    baseline_flat = flatten(baseline)
    current_flat = flatten(current)
    failures: list[str] = []
    for key, comparator in sorted(comparators.items()):
        if key not in baseline_flat:
            failures.append(f"{key}: baseline missing key")
            continue
        if key not in current_flat:
            failures.append(f"{key}: current missing key")
            continue

        baseline_value = baseline_flat[key]
        current_value = current_flat[key]
        if comparator == "lte":
            if current_value > baseline_value:
                failures.append(
                    f"{key}: regression (current={current_value} > baseline={baseline_value})"
                )
        elif comparator == "gte":
            if current_value < baseline_value:
                failures.append(
                    f"{key}: regression (current={current_value} < baseline={baseline_value})"
                )
        elif comparator == "eq":
            if current_value != baseline_value:
                failures.append(
                    f"{key}: changed (current={current_value} != baseline={baseline_value})"
                )
        else:
            failures.append(f"{key}: unknown comparator {comparator!r}")

    if failures:
        return _policy_check(
            "entropy gate",
            status="fail",
            details="; ".join(failures[:3]),
            blocking=True,
            evidence="files:entropy/policy.json,entropy/baseline.json",
        )

    return _policy_check(
        "entropy gate",
        status="pass",
        details="Current entropy metrics satisfy policy comparators against baseline",
        blocking=True,
        evidence="files:entropy/policy.json,entropy/baseline.json",
    )


def check_status_document_contract(path: Path) -> ReadinessCheck:
    if not path.exists():
        return _policy_check(
            "STATUS readiness contract",
            status="fail",
            details=f"Missing {path}",
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )

    sections = _parse_markdown_sections(path.read_text(encoding="utf-8"))
    readiness_section = _require_section(sections, "Machine-readable release readiness")
    if readiness_section is None:
        return _policy_check(
            "STATUS readiness contract",
            status="fail",
            details="Missing 'Machine-readable release readiness' section",
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )

    list_items = set(_extract_list_items(readiness_section.content))
    missing_states = sorted(_REQUIRED_READINESS_STATES - list_items)
    missing_contract_lines = [
        line
        for line in (
            "python -m scripts.release_readiness",
            "artifacts/release_readiness.json",
            "execution-backed",
        )
        if not _contains_phrase(readiness_section.content, line)
    ]
    if missing_states or missing_contract_lines:
        detail_parts: list[str] = []
        if missing_states:
            detail_parts.append("missing readiness states: " + ", ".join(missing_states))
        if missing_contract_lines:
            detail_parts.append("missing semantic lines: " + ", ".join(missing_contract_lines))
        return _policy_check(
            "STATUS readiness contract",
            status="fail",
            details="; ".join(detail_parts),
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )

    return _policy_check(
        "STATUS readiness contract",
        status="pass",
        details="STATUS.md delegates live readiness to the execution-backed report and defines all states",
        blocking=True,
        evidence=f"file:{path.as_posix()}",
    )


def check_release_readiness_document_contract(path: Path) -> ReadinessCheck:
    if not path.exists():
        return _policy_check(
            "RELEASE_READINESS readiness contract",
            status="fail",
            details=f"Missing {path}",
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )

    sections = _parse_markdown_sections(path.read_text(encoding="utf-8"))
    source_section = _require_section(sections, "Single-command truth source")
    states_section = _require_section(sections, "Readiness states")
    subsystem_section = _require_section(sections, "Subsystems")
    missing_sections = [
        title
        for title, section in (
            ("Single-command truth source", source_section),
            ("Readiness states", states_section),
            ("Subsystems", subsystem_section),
        )
        if section is None
    ]
    if missing_sections:
        return _policy_check(
            "RELEASE_READINESS readiness contract",
            status="fail",
            details="Missing sections: " + ", ".join(missing_sections),
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )

    assert source_section is not None
    assert states_section is not None
    assert subsystem_section is not None

    state_items = set(_extract_list_items(states_section.content))
    missing_states = sorted(_REQUIRED_READINESS_STATES - state_items)
    subsystem_items = _extract_list_items(subsystem_section.content)
    missing_subsystems = [
        item for item in _REQUIRED_SUBSYSTEMS if item not in subsystem_items
    ]
    missing_source_lines = [
        line
        for line in (
            "python -m scripts.release_readiness",
            "truth_model_version",
        )
        if not _contains_phrase(source_section.content + states_section.content, line)
    ]
    if not _contains_phrase(
        states_section.content,
        "ready requires at least one execution-backed check",
    ):
        missing_source_lines.append("ready requires at least one execution-backed check")

    if missing_states or missing_subsystems or missing_source_lines:
        detail_parts: list[str] = []
        if missing_states:
            detail_parts.append("missing readiness states: " + ", ".join(missing_states))
        if missing_subsystems:
            detail_parts.append("missing subsystems: " + ", ".join(missing_subsystems))
        if missing_source_lines:
            detail_parts.append("missing semantic lines: " + ", ".join(missing_source_lines))
        return _policy_check(
            "RELEASE_READINESS readiness contract",
            status="fail",
            details="; ".join(detail_parts),
            blocking=True,
            evidence=f"file:{path.as_posix()}",
        )

    return _policy_check(
        "RELEASE_READINESS readiness contract",
        status="pass",
        details="RELEASE_READINESS.md documents the same readiness states and execution-backed criteria",
        blocking=True,
        evidence=f"file:{path.as_posix()}",
    )


def compute_truth_model_fingerprint() -> str:
    """Return a stable fingerprint for readiness-contract logic."""
    relevant_objects = (
        ReadinessState.evaluate,
        SubprocessCommandRunner.run,
        check_mutation_baseline,
        check_entropy_gate,
        check_status_document_contract,
        check_release_readiness_document_contract,
    )
    digest = hashlib.sha256()
    for obj in relevant_objects:
        digest.update(inspect.getsource(obj).encode("utf-8"))
    return digest.hexdigest()[:16]
