"""Contract tests for the architecture manifest."""

from __future__ import annotations

from mlsdm.config.architecture_manifest import (
    ARCHITECTURE_MANIFEST,
    PACKAGE_ROOT,
    validate_manifest,
)


def test_architecture_manifest_is_consistent() -> None:
    """Manifest should have no validation issues."""
    issues = validate_manifest(ARCHITECTURE_MANIFEST)
    assert not issues, f"Architecture manifest violations: {issues}"


def test_manifest_covers_primary_modules() -> None:
    """Ensure the manifest declares the primary system boundaries."""
    names = {module.name for module in ARCHITECTURE_MANIFEST}
    top_modules = {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }
    assert top_modules.issubset(names), (
        "ARCHITECTURE_MANIFEST is missing modules: "
        f"{sorted(top_modules - names)}"
    )
