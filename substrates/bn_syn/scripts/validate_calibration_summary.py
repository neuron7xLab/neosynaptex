"""Fail-closed validation for calibration summary claim consistency."""

from __future__ import annotations

from pathlib import Path
import re

SUMMARY_PATH = Path("CALIBRATION_SUMMARY.md")
PERFECT_PATTERNS = (
    re.compile(r"\b100\s*/\s*100\b", re.IGNORECASE),
    re.compile(r"\bperfect\b", re.IGNORECASE),
    re.compile(r"\bfully calibrated\b", re.IGNORECASE),
)
REQUIRED_PROVISIONAL_LINE = "Status: PROVISIONAL / NOT INDEPENDENTLY VALIDATED"


def _extract_blockers(summary_text: str) -> list[str]:
    if "## Top 5 Blockers" not in summary_text:
        return []
    section = summary_text.split("## Top 5 Blockers", maxsplit=1)[1]
    lines = section.splitlines()
    blockers: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if re.match(r"^\d+\.\s+", stripped):
            blockers.append(stripped)
    return blockers


def validate_calibration_summary(path: Path = SUMMARY_PATH) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"Missing {path}"]

    text = path.read_text(encoding="utf-8")
    blockers = _extract_blockers(text)
    has_perfect_claim = any(pattern.search(text) for pattern in PERFECT_PATTERNS)

    if has_perfect_claim and blockers:
        errors.append("Perfect-score claim is forbidden when blockers are listed")

    if blockers and REQUIRED_PROVISIONAL_LINE not in text:
        errors.append(
            "Summary must declare provisional status when blockers are non-empty: "
            f"{REQUIRED_PROVISIONAL_LINE!r}"
        )

    if "Synthetic fixtures" in text and "NOT INDEPENDENTLY VALIDATED" not in text:
        errors.append("Synthetic fixture usage must be paired with non-independent validation disclaimer")

    return errors


def main() -> int:
    errors = validate_calibration_summary()
    if errors:
        for issue in errors:
            print(f"ERROR: {issue}")
        return 1
    print("Calibration summary claims: PASS")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
