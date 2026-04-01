from __future__ import annotations

from pathlib import Path

from scripts.validate_calibration_summary import (
    REQUIRED_PROVISIONAL_LINE,
    validate_calibration_summary,
)


def _write_summary(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def test_validate_calibration_summary_rejects_perfect_with_blockers(tmp_path: Path) -> None:
    summary = tmp_path / "CALIBRATION_SUMMARY.md"
    _write_summary(
        summary,
        """# Calibration Summary

Operational readiness is 100/100.

## Top 5 Blockers
1. Synthetic fixtures still proxy real telemetry.
""",
    )
    errors = validate_calibration_summary(summary)
    assert any("Perfect-score claim" in error for error in errors)


def test_validate_calibration_summary_requires_provisional_status(tmp_path: Path) -> None:
    summary = tmp_path / "CALIBRATION_SUMMARY.md"
    _write_summary(
        summary,
        """# Calibration Summary

## Top 5 Blockers
1. Synthetic fixtures still proxy real telemetry.
""",
    )
    errors = validate_calibration_summary(summary)
    assert any("provisional status" in error for error in errors)


def test_validate_calibration_summary_accepts_provisional_claims(tmp_path: Path) -> None:
    summary = tmp_path / "CALIBRATION_SUMMARY.md"
    _write_summary(
        summary,
        f"""# Calibration Summary

{REQUIRED_PROVISIONAL_LINE}

## Top 5 Blockers
1. Synthetic fixtures still proxy real telemetry.
""",
    )
    assert validate_calibration_summary(summary) == []
