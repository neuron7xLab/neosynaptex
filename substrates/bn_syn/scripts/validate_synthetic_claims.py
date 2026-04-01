"""Validate calibration/credibility claims are evidence-backed and non-deceptive."""

from __future__ import annotations

import re
from pathlib import Path

KEYWORDS = re.compile(r"CALIBRATION|100/100|perfect|calibrated|score|telemetry|synthetic", re.IGNORECASE)
PERFECT = re.compile(r"100/100|\bperfect\b", re.IGNORECASE)
BLOCKER = re.compile(r"blocker|known issue|not validated|provisional", re.IGNORECASE)
SYNTHETIC = re.compile(r"synthetic", re.IGNORECASE)
PROVISIONAL = re.compile(r"PROVISIONAL|NOT INDEPENDENTLY VALIDATED", re.IGNORECASE)
CMD = re.compile(r"`([^`]+)`")
PATH = re.compile(r"(?:^|\s)([\w./-]+\.(?:py|sh|md|json|yaml|yml))")


class ValidationError(RuntimeError):
    pass


def _candidate_files() -> list[Path]:
    files = [Path("README.md")]
    files.extend(Path("docs").rglob("*.md"))
    return [p for p in files if p.exists() and KEYWORDS.search(p.read_text(encoding="utf-8"))]


def _has_proof(text: str) -> bool:
    for cmd in CMD.findall(text):
        parts = cmd.strip().split()
        if not parts:
            continue
        if parts[0] in {"python", "pytest", "make"}:
            return True
    for path in PATH.findall(text):
        if Path(path).exists():
            return True
    return False


def main() -> int:
    failures: list[str] = []
    for path in _candidate_files():
        text = path.read_text(encoding="utf-8")
        if PERFECT.search(text):
            if not _has_proof(text):
                failures.append(f"perfect claim without executable proof in {path}")
            if BLOCKER.search(text) and SYNTHETIC.search(text):
                failures.append(f"perfect claim conflicts with blockers/synthetic in {path}")
        if SYNTHETIC.search(text) and not PROVISIONAL.search(text):
            failures.append(f"synthetic mention missing provisional disclaimer in {path}")
    if failures:
        raise ValidationError("\n".join(failures))
    print("validate_synthetic_claims: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"validate_synthetic_claims: FAIL: {exc}")
        raise SystemExit(1)
