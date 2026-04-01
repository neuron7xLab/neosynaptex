from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.tags import Tag
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version


@dataclass(frozen=True)
class TargetConfig:
    python_version: str
    implementation: str
    abi: str
    platform_tag: str
    sys_platform: str
    os_name: str
    platform_system: str
    platform_machine: str


@dataclass(frozen=True)
class LockedRequirement:
    raw: str
    name: str
    version: str
    marker: str | None

    @property
    def key(self) -> tuple[str, Version]:
        return canonicalize_name(self.name), Version(self.version)


@dataclass(frozen=True)
class ParseResult:
    requirements: list[LockedRequirement]
    unsupported: list[str]
    duplicates: list[str]


@dataclass(frozen=True)
class WheelScanResult:
    coverage: dict[tuple[str, Version], set[str]]
    incompatible: list[str]
    malformed: list[str]


def _normalize_python_full_version(python_version: str) -> str:
    parts = python_version.split(".")
    if len(parts) == 2:
        return f"{python_version}.0"
    return python_version


def _derive_target_env_from_platform_tag(platform_tag: str) -> tuple[str, str, str, str]:
    tag = platform_tag.lower()

    if tag.startswith(("manylinux", "linux")):
        machine = tag.split("_")[-1]
        return ("linux", "posix", "Linux", machine)

    if tag.startswith("macosx"):
        machine = tag.split("_")[-1]
        return ("darwin", "posix", "Darwin", machine)

    if tag.startswith("win"):
        machine = tag.split("_", 1)[-1] if "_" in tag else tag.replace("win", "")
        return ("win32", "nt", "Windows", machine)

    return (
        sys.platform,
        "nt" if sys.platform.startswith("win") else "posix",
        platform.system(),
        platform.machine(),
    )


def _marker_environment(target: TargetConfig) -> dict[str, str]:
    env = default_environment()
    env["python_version"] = target.python_version
    env["python_full_version"] = _normalize_python_full_version(target.python_version)
    env["implementation_name"] = (
        "cpython" if target.implementation == "cp" else target.implementation
    )
    env["sys_platform"] = target.sys_platform
    env["os_name"] = target.os_name
    env["platform_system"] = target.platform_system
    env["platform_machine"] = target.platform_machine
    return env


def _iter_requirement_lines(lock_file: Path) -> list[str]:
    lines: list[str] = []
    buffer = ""
    for raw_line in lock_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            if buffer:
                lines.append(buffer.strip())
                buffer = ""
            continue

        if line.startswith("--hash="):
            if buffer:
                lines.append(buffer.strip())
                buffer = ""
            continue

        if line.startswith("--"):
            if buffer:
                lines.append(buffer.strip())
                buffer = ""
            continue

        if line.endswith("\\"):
            buffer += line[:-1].strip() + " "
            continue

        buffer += line
        lines.append(buffer.strip())
        buffer = ""

    if buffer:
        lines.append(buffer.strip())
    return lines


def parse_locked_requirements(lock_file: Path, target: TargetConfig) -> ParseResult:
    applicable_by_key: dict[tuple[str, Version], LockedRequirement] = {}
    unsupported: list[str] = []
    duplicates: list[str] = []
    marker_env = _marker_environment(target)

    for req_line in _iter_requirement_lines(lock_file):
        try:
            req = Requirement(req_line)
        except InvalidRequirement:
            unsupported.append(req_line)
            continue

        if len(req.specifier) != 1:
            unsupported.append(req_line)
            continue

        spec = next(iter(req.specifier))
        if spec.operator != "==" or "*" in spec.version:
            unsupported.append(req_line)
            continue

        if req.marker is not None and not req.marker.evaluate(marker_env):
            continue

        requirement = LockedRequirement(
            raw=req_line,
            name=req.name,
            version=spec.version,
            marker=str(req.marker) if req.marker is not None else None,
        )

        if requirement.key in applicable_by_key:
            duplicates.append(f"{requirement.name}=={requirement.version}")
            continue

        applicable_by_key[requirement.key] = requirement

    return ParseResult(
        requirements=list(applicable_by_key.values()),
        unsupported=unsupported,
        duplicates=sorted(duplicates),
    )


def _wheel_matches_target_tag(target: TargetConfig, wheel_tags: frozenset[Tag]) -> bool:
    py_tag = f"{target.implementation}{target.python_version.replace('.', '')}"
    supported_interpreters = {
        py_tag,
        f"py{target.python_version.replace('.', '')}",
        "py3",
        "py2.py3",
    }

    for tag in wheel_tags:
        interpreter_ok = tag.interpreter in supported_interpreters
        abi_ok = tag.abi in {target.abi, "abi3", "none"}
        platform_ok = tag.platform in {target.platform_tag, "any"}
        if interpreter_ok and abi_ok and platform_ok:
            return True
    return False


def wheelhouse_coverage(wheelhouse_dir: Path, target: TargetConfig) -> WheelScanResult:
    coverage: dict[tuple[str, Version], set[str]] = {}
    incompatible: list[str] = []
    malformed: list[str] = []

    for wheel_path in sorted(wheelhouse_dir.glob("*.whl")):
        try:
            parsed_name, parsed_version, _, parsed_tags = parse_wheel_filename(wheel_path.name)
        except (InvalidVersion, ValueError):
            malformed.append(wheel_path.name)
            continue

        if not _wheel_matches_target_tag(target, parsed_tags):
            incompatible.append(wheel_path.name)
            continue

        key = (canonicalize_name(parsed_name), parsed_version)
        coverage.setdefault(key, set()).add(wheel_path.name)

    return WheelScanResult(coverage=coverage, incompatible=incompatible, malformed=malformed)


def _build_report(
    lock_file: Path,
    wheelhouse_dir: Path,
    target: TargetConfig,
    parsed: ParseResult,
) -> dict[str, Any]:
    scan = wheelhouse_coverage(wheelhouse_dir, target)
    missing: list[str] = []
    for requirement in parsed.requirements:
        if requirement.key not in scan.coverage:
            missing.append(f"{requirement.name}=={requirement.version}")

    wheels_by_requirement = {
        f"{name}=={str(version)}": sorted(files)
        for (name, version), files in sorted(
            scan.coverage.items(), key=lambda item: (item[0][0], str(item[0][1]))
        )
    }

    return {
        "lock_file": str(lock_file),
        "wheelhouse_dir": str(wheelhouse_dir),
        "target": {
            "python_version": target.python_version,
            "implementation": target.implementation,
            "abi": target.abi,
            "platform_tag": target.platform_tag,
            "sys_platform": target.sys_platform,
            "os_name": target.os_name,
            "platform_system": target.platform_system,
            "platform_machine": target.platform_machine,
        },
        "parsed_requirements_count": len(_iter_requirement_lines(lock_file)),
        "applicable_requirements_count": len(parsed.requirements),
        "unsupported_requirements": sorted(parsed.unsupported),
        "duplicate_requirements": parsed.duplicates,
        "missing": sorted(missing),
        "incompatible_wheels": scan.incompatible,
        "malformed_wheels": scan.malformed,
        "wheel_inventory_count": sum(len(files) for files in scan.coverage.values()),
        "wheel_inventory": wheels_by_requirement,
    }


def _write_report(report_path: Path | None, report: dict[str, Any]) -> None:
    if report_path is None:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_wheelhouse(
    lock_file: Path,
    wheelhouse_dir: Path,
    target: TargetConfig,
    report_path: Path | None = None,
) -> int:
    if not lock_file.is_file():
        raise SystemExit(f"lock file not found: {lock_file}")
    if not wheelhouse_dir.is_dir():
        raise SystemExit(f"wheelhouse directory not found: {wheelhouse_dir}")

    parsed = parse_locked_requirements(lock_file, target)
    report = _build_report(
        lock_file=lock_file, wheelhouse_dir=wheelhouse_dir, target=target, parsed=parsed
    )
    _write_report(report_path, report)

    if report["unsupported_requirements"]:
        print(
            "Unsupported lock entries detected (only pinned '==' entries are allowed):",
            file=sys.stderr,
        )
        for entry in report["unsupported_requirements"]:
            print(f"  - {entry}", file=sys.stderr)
        return 2

    if report["duplicate_requirements"]:
        print("Duplicate applicable lock entries detected:", file=sys.stderr)
        for entry in report["duplicate_requirements"]:
            print(f"  - {entry}", file=sys.stderr)
        return 2

    if report["missing"]:
        print("Missing wheel artifacts for locked dependencies:", file=sys.stderr)
        for requirement in report["missing"]:
            print(f"  - {requirement}", file=sys.stderr)
        return 1

    print("wheelhouse validation passed: all applicable locked dependencies are covered.")
    return 0


def build_wheelhouse(lock_file: Path, wheelhouse_dir: Path, target: TargetConfig) -> None:
    if not lock_file.is_file():
        raise SystemExit(f"lock file not found: {lock_file}")

    wheelhouse_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--no-deps",
        "--dest",
        str(wheelhouse_dir),
        "--requirement",
        str(lock_file),
        "--python-version",
        target.python_version,
        "--implementation",
        target.implementation,
        "--abi",
        target.abi,
        "--platform",
        target.platform_tag,
        "--progress-bar",
        "off",
        "--disable-pip-version-check",
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            "wheelhouse build failed: one or more locked dependencies are unavailable as wheels "
            f"for target python={target.python_version}, implementation={target.implementation}, "
            f"abi={target.abi}, platform={target.platform_tag}."
        ) from error


def sysconfig_platform_tag() -> str:
    machine = platform.machine().replace("-", "_").replace(".", "_")
    system = platform.system().lower()
    if system == "linux":
        return f"manylinux_2_17_{machine}"
    if system == "darwin":
        return f"macosx_11_0_{machine}"
    if system == "windows":
        if machine in {"x86_64", "amd64"}:
            return "win_amd64"
        return f"win_{machine}"
    return "any"


def _default_target(
    python_version: str,
    implementation: str,
    abi: str,
    platform_tag: str,
) -> TargetConfig:
    sys_plat, os_name, plat_sys, plat_machine = _derive_target_env_from_platform_tag(platform_tag)
    return TargetConfig(
        python_version=python_version,
        implementation=implementation,
        abi=abi,
        platform_tag=platform_tag,
        sys_platform=sys_plat,
        os_name=os_name,
        platform_system=plat_sys,
        platform_machine=plat_machine,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and validate offline wheelhouse artifacts.")
    parser.add_argument("--lock-file", default="requirements-lock.txt", type=Path)
    parser.add_argument("--wheelhouse", default="wheelhouse", type=Path)
    parser.add_argument("--python-version", default="3.11")
    parser.add_argument("--implementation", default="cp")
    parser.add_argument("--abi", default=None)
    parser.add_argument("--platform-tag", default=None)
    parser.add_argument("--report", type=Path, default=None)

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="Download pinned wheels for the configured target.")
    subparsers.add_parser(
        "validate", help="Validate wheelhouse covers applicable pinned dependencies."
    )

    args = parser.parse_args()

    normalized = args.python_version.replace(".", "")
    abi = args.abi or f"{args.implementation}{normalized}"
    platform_tag = args.platform_tag or sysconfig_platform_tag()
    target = _default_target(args.python_version, args.implementation, abi, platform_tag)

    if args.command == "build":
        build_wheelhouse(args.lock_file, args.wheelhouse, target)
        return 0

    return validate_wheelhouse(
        lock_file=args.lock_file,
        wheelhouse_dir=args.wheelhouse,
        target=target,
        report_path=args.report,
    )


if __name__ == "__main__":
    raise SystemExit(main())
