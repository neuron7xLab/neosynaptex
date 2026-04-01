"""Validate public status and anti-overclaim policy for battle usage."""

from __future__ import annotations

from pathlib import Path

REQUIRED_STATUS_LINE = "This project is research-grade / pre-production. No battle usage claimed."
README_STATUS_LINK = "docs/STATUS.md"
FORBIDDEN_README_CLAIMS = (
    "production-ready",
    "battle-tested",
    "battle usage proven",
)


def validate_status_claims(repo_root: Path) -> list[str]:
    errors: list[str] = []
    status_path = repo_root / "docs" / "STATUS.md"
    readme_path = repo_root / "README.md"

    if not status_path.exists():
        errors.append("Missing docs/STATUS.md")
        return errors

    status_text = status_path.read_text(encoding="utf-8")
    if REQUIRED_STATUS_LINE not in status_text:
        errors.append(f"docs/STATUS.md missing required declaration: {REQUIRED_STATUS_LINE!r}")

    if not readme_path.exists():
        errors.append("Missing README.md")
        return errors

    readme_text = readme_path.read_text(encoding="utf-8")
    if README_STATUS_LINK not in readme_text:
        errors.append("README.md must link to docs/STATUS.md")

    readme_text_lower = readme_text.lower()
    for phrase in FORBIDDEN_README_CLAIMS:
        if phrase in readme_text_lower:
            errors.append(f"README.md contains forbidden production claim phrase: {phrase!r}")

    return errors


def main() -> int:
    errors = validate_status_claims(Path.cwd())
    if errors:
        for issue in errors:
            print(f"ERROR: {issue}")
        return 1
    print("Status-claims policy: PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
