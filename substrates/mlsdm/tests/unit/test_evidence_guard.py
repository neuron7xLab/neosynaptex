from __future__ import annotations

import fnmatch
from pathlib import Path

MAX_EVIDENCE_FILE_BYTES = 5 * 1024 * 1024  # 5 MB cap per requirement: keep evidence small and non-sensitive
FORBIDDEN_PATTERNS = [
    "*.env",
    "*.pem",
    "id_rsa",
    "id_rsa.*",
    "token*",
    "*.key",
    "*.p12",
]


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return current.parents[3] if len(current.parents) > 3 else current.parent


def _evidence_files() -> list[Path]:
    evidence_root = _repo_root() / "artifacts" / "evidence"
    if not evidence_root.exists():
        msg = f"Evidence directory missing: {evidence_root}"
        raise AssertionError(msg)
    return [p for p in evidence_root.rglob("*") if p.is_file()]


def test_evidence_files_do_not_match_forbidden_patterns() -> None:
    violations: list[str] = []
    for path in _evidence_files():
        rel = path.relative_to(_repo_root() / "artifacts" / "evidence")
        rel_str = str(rel).lower()
        name_lower = rel.name.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(name_lower, pattern):
                violations.append(str(rel))
                break
    assert not violations, f"Forbidden files present in evidence: {violations}"


def test_evidence_files_are_under_size_cap() -> None:
    oversized = []
    for path in _evidence_files():
        if path.stat().st_size > MAX_EVIDENCE_FILE_BYTES:
            oversized.append(str(path))
    assert not oversized, (
        f"Evidence files exceed {MAX_EVIDENCE_FILE_BYTES} bytes cap: {oversized}"
    )
