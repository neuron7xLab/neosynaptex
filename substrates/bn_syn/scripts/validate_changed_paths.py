"""Fail if changed paths escape allowed integrity-hardening scope."""

from __future__ import annotations

import subprocess

ALLOWED_PREFIXES = (
    "tests/",
    "scripts/",
    "docs/",
    ".github/workflows/",
)
ALLOWED_FILES = {
    "pyproject.toml",
    "setup.cfg",
    "Makefile",
    "README.md",
    ".github/REPO_MANIFEST.md",
    "manifest/repo_manifest.computed.json",
}


class ValidationError(RuntimeError):
    pass


def _allowed(path: str) -> bool:
    if path.startswith("requirements"):
        return True
    if path in ALLOWED_FILES:
        return True
    return path.startswith(ALLOWED_PREFIXES)


def main() -> int:
    res = subprocess.run(
        ["git", "diff", "--name-only", "--", "."],
        text=True,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        raise ValidationError(res.stderr.strip())
    changed = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    bad = [path for path in changed if not _allowed(path)]
    if bad:
        raise ValidationError(f"changed paths outside allowlist: {bad}")
    print("validate_changed_paths: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"validate_changed_paths: FAIL: {exc}")
        raise SystemExit(1)
