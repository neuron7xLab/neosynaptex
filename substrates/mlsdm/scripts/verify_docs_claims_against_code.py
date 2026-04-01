#!/usr/bin/env python3
"""Verify documented claims against code defaults."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "SECURITY_CONTRACTS.md"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mlsdm.security.path_utils import DEFAULT_PUBLIC_PATHS  # noqa: E402

CLAIM_PATTERN = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _load_claims(text: str) -> list[dict[str, object]]:
    claims: list[dict[str, object]] = []
    for match in CLAIM_PATTERN.finditer(text):
        payload = json.loads(match.group(1))
        if "doc_claim" in payload:
            claims.append(payload)
    return claims


def _verify_default_public_paths(claim: dict[str, object]) -> None:
    expected = list(DEFAULT_PUBLIC_PATHS)
    actual = claim.get("value")
    if actual != expected:
        _fail(
            "security.default_public_paths mismatch: "
            f"expected {expected}, got {actual}"
        )


def main() -> int:
    if not DOC_PATH.exists():
        _fail(f"Doc not found: {DOC_PATH}")

    text = DOC_PATH.read_text(encoding="utf-8")
    claims = _load_claims(text)
    if not claims:
        _fail("No doc_claim JSON blocks found.")

    matched = False
    for claim in claims:
        if claim.get("doc_claim") == "security.default_public_paths":
            _verify_default_public_paths(claim)
            matched = True

    if not matched:
        _fail("doc_claim 'security.default_public_paths' not found.")

    print("Documentation claims verified against code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
