"""Sanity check test for metrics evidence paths.

This test ensures that:
1. docs/METRICS_SOURCE.md does not contain CI workflow links (must use in-repo evidence)
2. At least one evidence snapshot exists in the repository
"""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    """Get repository root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[3] if len(current.parents) > 3 else current.parent


class TestMetricsEvidencePaths:
    """Tests to prevent drift between docs and committed evidence."""

    def test_no_ci_workflow_links_in_metrics_source(self) -> None:
        """METRICS_SOURCE.md should not reference CI workflow URLs."""
        repo_root = _repo_root()
        metrics_source = repo_root / "docs" / "METRICS_SOURCE.md"

        assert metrics_source.exists(), f"Missing {metrics_source}"

        content = metrics_source.read_text()

        # Check for GitHub Actions workflow URLs
        workflow_patterns = [
            r"actions/workflows",
            r"github\.com/[^/]+/[^/]+/actions",
            r"Latest CI run",
        ]

        violations = []
        for pattern in workflow_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(pattern)

        assert not violations, (
            f"docs/METRICS_SOURCE.md contains CI workflow references: {violations}. "
            "Use in-repo evidence paths under artifacts/evidence/ instead."
        )

    def test_evidence_directory_exists(self) -> None:
        """artifacts/evidence/ directory must exist."""
        repo_root = _repo_root()
        evidence_dir = repo_root / "artifacts" / "evidence"

        assert evidence_dir.exists(), (
            f"Evidence directory not found: {evidence_dir}. "
            "Run 'make evidence' to generate evidence snapshots."
        )

    def test_at_least_one_evidence_snapshot_exists(self) -> None:
        """At least one evidence snapshot must be committed."""
        repo_root = _repo_root()
        evidence_dir = repo_root / "artifacts" / "evidence"

        if not evidence_dir.exists():
            # Skip if evidence dir doesn't exist (will be caught by other test)
            return

        # Find dated subdirectories (YYYY-MM-DD pattern)
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        snapshots = [
            d for d in evidence_dir.iterdir()
            if d.is_dir() and date_pattern.match(d.name)
        ]

        assert len(snapshots) >= 1, (
            f"No evidence snapshots found in {evidence_dir}. "
            "Run 'make evidence' to generate a snapshot."
        )

    def test_evidence_snapshot_has_required_files(self) -> None:
        """Evidence snapshots should contain required files."""
        repo_root = _repo_root()
        evidence_dir = repo_root / "artifacts" / "evidence"

        if not evidence_dir.exists():
            return

        # Find dated subdirectories
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        dated_dirs = [
            d for d in evidence_dir.iterdir()
            if d.is_dir() and date_pattern.match(d.name)
        ]

        if not dated_dirs:
            return

        # Check the most recent snapshot
        latest_date_dir = sorted(dated_dirs)[-1]
        sha_dirs = [d for d in latest_date_dir.iterdir() if d.is_dir()]

        if not sha_dirs:
            return

        latest_snapshot = sorted(sha_dirs)[-1]

        # Required files
        required_files = [
            "manifest.json",
            "coverage/coverage.xml",
            "pytest/junit.xml",
            "env/python_version.txt",
            "env/uv_lock_sha256.txt",
        ]

        missing = []
        for rel_path in required_files:
            full_path = latest_snapshot / rel_path
            if not full_path.exists():
                missing.append(rel_path)

        assert not missing, (
            f"Evidence snapshot {latest_snapshot.name} is missing required files: {missing}. "
            "Run 'make evidence' to regenerate."
        )
