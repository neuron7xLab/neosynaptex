"""Deterministic release pipeline helper (changelog + version + build + dry-run publish)."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def read_pyproject_version(pyproject_path: Path) -> str:
    text = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', text, flags=re.MULTILINE)
    if not match:
        raise ValueError("Could not find [project].version in pyproject.toml")
    return match.group(1)


def bump_semver(version: str, bump: str) -> str:
    match = SEMVER_RE.match(version)
    if not match:
        raise ValueError(f"Invalid semver version: {version}")
    major, minor, patch = map(int, match.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unsupported bump kind: {bump}")


def changelog_has_version(changelog_path: Path, version: str) -> bool:
    header = f"## [{version}]"
    return header in changelog_path.read_text(encoding="utf-8")


def replace_pyproject_version(pyproject_path: Path, new_version: str) -> None:
    text = pyproject_path.read_text(encoding="utf-8")
    updated = re.sub(
        r'(^version\s*=\s*")([0-9]+\.[0-9]+\.[0-9]+)("\s*$)',
        rf"\g<1>{new_version}\g<3>",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if updated == text:
        raise ValueError("Failed to update pyproject version")
    pyproject_path.write_text(updated, encoding="utf-8")


def run_build() -> None:
    subprocess.run([sys.executable, "-m", "build"], check=True)


def run_publish_dry_run() -> None:
    dist_dir = Path("dist")
    artifacts = sorted(dist_dir.glob("*"))
    if not artifacts:
        raise RuntimeError("No artifacts found in dist/ for dry-run publish")
    for artifact in artifacts:
        print(f"DRY-RUN publish artifact: {artifact}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Release pipeline helper")
    parser.add_argument("--bump", choices=["major", "minor", "patch"], default=None)
    parser.add_argument("--apply-version-bump", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    pyproject = Path("pyproject.toml")
    changelog = Path("CHANGELOG.md")

    current_version = read_pyproject_version(pyproject)
    target_version = current_version

    if args.bump:
        target_version = bump_semver(current_version, args.bump)

    if args.apply_version_bump and target_version != current_version:
        replace_pyproject_version(pyproject, target_version)
        print(f"Updated pyproject version: {current_version} -> {target_version}")

    if not changelog_has_version(changelog, target_version):
        print(f"ERROR: CHANGELOG.md is missing entry for version {target_version}")
        return 1

    if args.verify_only:
        print(f"Release verification passed for version {target_version}")
        return 0

    run_build()
    run_publish_dry_run()
    print(f"Release pipeline dry-run passed for version {target_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
