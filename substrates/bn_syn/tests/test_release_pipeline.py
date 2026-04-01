from __future__ import annotations

from pathlib import Path

from scripts.release_pipeline import bump_semver, changelog_has_version


def test_bump_semver_modes() -> None:
    assert bump_semver("0.2.0", "patch") == "0.2.1"
    assert bump_semver("0.2.0", "minor") == "0.3.0"
    assert bump_semver("0.2.0", "major") == "1.0.0"


def test_changelog_has_current_version() -> None:
    assert changelog_has_version(Path("CHANGELOG.md"), "0.5.0")
