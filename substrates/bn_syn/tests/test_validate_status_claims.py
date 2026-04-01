from __future__ import annotations

from pathlib import Path

from scripts.validate_status_claims import REQUIRED_STATUS_LINE, validate_status_claims


def _write_repo(root: Path, *, status_text: str, readme_text: str) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "STATUS.md").write_text(status_text, encoding="utf-8")
    (root / "README.md").write_text(readme_text, encoding="utf-8")


def test_validate_status_claims_pass(tmp_path: Path) -> None:
    _write_repo(
        tmp_path,
        status_text=f"# Status\n\n{REQUIRED_STATUS_LINE}\n",
        readme_text="# README\n\nSee docs/STATUS.md\n",
    )
    assert validate_status_claims(tmp_path) == []


def test_validate_status_claims_missing_required_line(tmp_path: Path) -> None:
    _write_repo(
        tmp_path,
        status_text="# Status\n\nNo declaration\n",
        readme_text="# README\n\nSee docs/STATUS.md\n",
    )
    errors = validate_status_claims(tmp_path)
    assert any("missing required declaration" in e for e in errors)


def test_validate_status_claims_forbidden_phrase(tmp_path: Path) -> None:
    _write_repo(
        tmp_path,
        status_text=f"# Status\n\n{REQUIRED_STATUS_LINE}\n",
        readme_text="# README\n\nThis is battle-tested. See docs/STATUS.md\n",
    )
    errors = validate_status_claims(tmp_path)
    assert any("forbidden production claim phrase" in e for e in errors)
