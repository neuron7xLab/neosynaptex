"""Contract tests for architecture dependencies."""

from __future__ import annotations

from mlsdm.config.architecture_manifest import PACKAGE_ROOT
from tests.contracts.architecture_imports import find_architecture_import_violations


def test_architecture_dependencies_respected() -> None:
    """Ensure code imports match manifest allowed dependencies."""
    violations = find_architecture_import_violations()
    if violations:
        formatted = "\n".join(
            f"{violation.source_module} -> {violation.target_module}: "
            f"{violation.source_file.relative_to(PACKAGE_ROOT)} "
            f"({violation.import_statement}) "
            f"[{violation.reason}]"
            for violation in violations
        )
        raise AssertionError(
            "Disallowed architecture dependencies detected:\n" + formatted
        )
