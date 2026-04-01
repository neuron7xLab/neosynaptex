#!/usr/bin/env python3
"""Export requirements.txt from pyproject.toml dependencies.

This script ensures requirements.txt stays in sync with pyproject.toml.
Run this to regenerate requirements.txt when dependencies change.

Usage:
    python scripts/ci/export_requirements.py
    python scripts/ci/export_requirements.py --check  # CI mode: fail if drift detected
"""
from __future__ import annotations

import argparse
import re
import sys

# Python 3.11+ has tomllib in stdlib, earlier versions need tomli backport
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError as e:
        raise ImportError(
            "tomli package is required for Python <3.11. "
            "Install it with: pip install tomli"
        ) from e

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

# Project root is two levels up from this script
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
REQUIREMENTS_PATH = PROJECT_ROOT / "requirements.txt"
def _normalize_package_name(name: str) -> str:
    normalized = name.strip().lower()
    normalized = normalized.replace("_", "-").replace(".", "-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized


def _normalize_excluded_packages(
    excluded_packages: dict[str, dict[str, str]]
) -> dict[str, dict[str, str]]:
    return {
        _normalize_package_name(name): metadata
        for name, metadata in excluded_packages.items()
    }


EXCLUDED_PACKAGES: dict[str, dict[str, str]] = _normalize_excluded_packages(
    {
        "jupyter": {
            "reason": "excluded from requirements.txt to avoid pip-audit failures via nbconvert",
            "cve": "CVE-2025-53000",
            "remove_when": "remove once nbconvert>=7.16.0",
        },
        "jupyter_core": {
            "reason": "excluded from requirements.txt to avoid pip-audit failures via nbconvert",
            "cve": "CVE-2025-53000",
            "remove_when": "remove once nbconvert>=7.16.0",
        },
    }
)


def load_pyproject(path: Path) -> dict[str, Any]:
    """Load pyproject.toml data using tomllib."""
    return tomllib.loads(path.read_text(encoding="utf-8"))


def parse_pyproject_deps(pyproject_data: dict[str, Any]) -> dict[str, Any]:
    """Parse dependencies from pyproject.toml data."""
    project = pyproject_data.get("project", {})
    core_deps = list(project.get("dependencies", []) or [])
    optional_deps = {
        group: list(deps or [])
        for group, deps in (project.get("optional-dependencies", {}) or {}).items()
    }
    return {"core": core_deps, "optional": optional_deps}


def _format_group_list(groups: Iterable[str]) -> str:
    group_list = ", ".join(groups)
    return group_list if group_list else "none"


def _title_case_group(group: str) -> str:
    return group.replace("-", " ").title()


def _normalize_dependency_name(dep: str) -> str:
    name = re.split(r"[<>=!~;\\[]", dep, maxsplit=1)[0].strip()
    return _normalize_package_name(name)


def filter_excluded_dependencies(deps: Iterable[str]) -> list[str]:
    return [dep for dep in deps if _normalize_dependency_name(dep) not in EXCLUDED_PACKAGES]


def _format_excluded_packages(excluded_packages: dict[str, dict[str, str]]) -> list[str]:
    if not excluded_packages:
        return ["# Optional dependency packages excluded: none"]
    excluded_lines = [
        "# Optional dependency packages excluded:",
    ]
    for name in sorted(excluded_packages):
        metadata = excluded_packages[name]
        reason = metadata["reason"]
        cve = metadata["cve"]
        remove_when = metadata["remove_when"]
        excluded_lines.append(f"# - {name}: {reason} ({cve}; {remove_when})")
    return excluded_lines


def generate_requirements(deps: dict[str, Any]) -> str:
    """Generate requirements.txt content from parsed dependencies."""
    optional_groups = sorted(deps["optional"].keys())
    group_list = _format_group_list(optional_groups)
    header = f"""\
# GENERATED FILE - DO NOT EDIT MANUALLY
# This file is auto-generated from pyproject.toml dependencies.
# Regenerate with: python scripts/ci/export_requirements.py
#
# MLSDM Full Installation Requirements
#
# This file includes all dependencies including optional ones,
# except excluded packages listed below.
# Optional dependency groups discovered in pyproject.toml: {group_list}
# Optional dependency groups included in this file: all ({group_list})
# Optional dependency groups excluded: none
#
# For minimal installation: pip install -e .
# For embeddings support: pip install -e ".[embeddings]"
# For full dev install: pip install -r requirements.txt
#
"""
    lines = [header]
    lines.extend(_format_excluded_packages(EXCLUDED_PACKAGES))
    lines.append("")

    lines.append("# Core Dependencies (from pyproject.toml [project.dependencies])")
    for dep in sorted(deps["core"], key=str.lower):
        lines.append(dep)
    lines.append("")

    for group in optional_groups:
        title = _title_case_group(group)
        lines.append(
            f"# Optional {title} (from pyproject.toml [project.optional-dependencies].{group})"
        )
        lines.append(f"# Install with: pip install \".[{group}]\"")
        for dep in sorted(filter_excluded_dependencies(deps["optional"][group]), key=str.lower):
            lines.append(dep)
        lines.append("")

    lines.append("# Security: Pin minimum versions for indirect dependencies with known vulnerabilities")
    lines.append("certifi>=2025.11.12")
    lines.append("cryptography>=46.0.3")
    lines.append("jinja2>=3.1.6")
    lines.append("urllib3>=2.6.2")
    lines.append("setuptools>=80.9.0")
    lines.append("idna>=3.11")
    lines.append("")

    return "\n".join(lines)


def normalize_requirements(content: str) -> list[str]:
    """Normalize requirements content for comparison.

    Ignores comments, empty lines, and normalizes whitespace.
    Returns sorted list of non-empty, non-comment lines.
    """
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return sorted(lines, key=str.lower)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export requirements.txt from pyproject.toml")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: fail if requirements.txt differs from generated",
    )
    args = parser.parse_args()

    if not PYPROJECT_PATH.exists():
        print(f"ERROR: pyproject.toml not found at {PYPROJECT_PATH}", file=sys.stderr)
        return 1

    pyproject_data = load_pyproject(PYPROJECT_PATH)
    deps = parse_pyproject_deps(pyproject_data)
    generated = generate_requirements(deps)

    if args.check:
        if not REQUIREMENTS_PATH.exists():
            print("ERROR: requirements.txt does not exist", file=sys.stderr)
            return 1

        current = REQUIREMENTS_PATH.read_text(encoding="utf-8")
        current_deps = normalize_requirements(current)
        generated_deps = normalize_requirements(generated)

        if current_deps != generated_deps:
            print("ERROR: Dependency drift detected!", file=sys.stderr)
            print("", file=sys.stderr)
            print("requirements.txt is out of sync with pyproject.toml", file=sys.stderr)
            print("Run: python scripts/ci/export_requirements.py", file=sys.stderr)
            print("", file=sys.stderr)

            current_set = set(current_deps)
            generated_set = set(generated_deps)

            missing = generated_set - current_set
            extra = current_set - generated_set

            if missing:
                print("Missing in requirements.txt:", file=sys.stderr)
                for dep in sorted(missing):
                    print(f"  + {dep}", file=sys.stderr)

            if extra:
                print("Extra in requirements.txt:", file=sys.stderr)
                for dep in sorted(extra):
                    print(f"  - {dep}", file=sys.stderr)

            return 1

        print("✓ requirements.txt is in sync with pyproject.toml")
        return 0

    # Write mode
    REQUIREMENTS_PATH.write_text(generated, encoding="utf-8")
    print(f"✓ Generated {REQUIREMENTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
