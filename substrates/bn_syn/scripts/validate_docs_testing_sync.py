"""Ensure canonical gate command is synchronized across docs and PR workflow."""

from __future__ import annotations

from pathlib import Path

import yaml

CANONICAL = "make test-gate"
DOC_PATHS = [Path("README.md"), Path("docs/TESTING.md")]
WORKFLOW = Path(".github/workflows/ci-pr-atomic.yml")


class ValidationError(RuntimeError):
    pass


def main() -> int:
    for path in DOC_PATHS:
        if path.exists() and CANONICAL not in path.read_text(encoding="utf-8"):
            raise ValidationError(f"missing canonical command in {path}")

    text = WORKFLOW.read_text(encoding="utf-8")
    if CANONICAL not in text:
        raise ValidationError(f"missing canonical command in {WORKFLOW}")

    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"workflow YAML parse failed: {exc}") from exc

    print("validate_docs_testing_sync: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"validate_docs_testing_sync: FAIL: {exc}")
        raise SystemExit(1)
