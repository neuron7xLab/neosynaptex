from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import generate_coverage_trend


def test_normalize_coverage_percent_rounds() -> None:
    assert generate_coverage_trend.normalize_coverage_percent(87.654321) == 87.6543


@pytest.mark.parametrize("value", [-0.01, 100.01])
def test_normalize_coverage_percent_rejects_out_of_scale(value: float) -> None:
    with pytest.raises(ValueError, match=r"\[0, 100\]"):
        generate_coverage_trend.normalize_coverage_percent(value)


def test_validate_state_thresholds_accepts_default() -> None:
    generate_coverage_trend.validate_state_thresholds(generate_coverage_trend.STATE_THRESHOLDS)


@pytest.mark.parametrize(
    "thresholds",
    [
        tuple(),
        ((50.0, "critical"), (50.0, "low")),
        ((50.0, "critical"), (70.0, "low"), (95.0, "high")),
    ],
)
def test_validate_state_thresholds_rejects_invalid(
    thresholds: tuple[tuple[float, str], ...],
) -> None:
    with pytest.raises(ValueError):
        generate_coverage_trend.validate_state_thresholds(thresholds)


@pytest.mark.parametrize(
    ("coverage", "state"),
    [
        (0.0, generate_coverage_trend.STATE_CRITICAL),
        (49.9999, generate_coverage_trend.STATE_CRITICAL),
        (50.0, generate_coverage_trend.STATE_LOW),
        (69.9999, generate_coverage_trend.STATE_LOW),
        (70.0, generate_coverage_trend.STATE_MODERATE),
        (84.9999, generate_coverage_trend.STATE_MODERATE),
        (85.0, generate_coverage_trend.STATE_HIGH),
        (94.9999, generate_coverage_trend.STATE_HIGH),
        (95.0, generate_coverage_trend.STATE_EXCELLENT),
        (100.0, generate_coverage_trend.STATE_EXCELLENT),
    ],
)
def test_quantize_coverage_state_boundaries(coverage: float, state: str) -> None:
    assert generate_coverage_trend.quantize_coverage_state(coverage) == state


def test_load_total_coverage_rejects_missing_numeric(tmp_path: Path) -> None:
    coverage_json = tmp_path / "coverage.json"
    coverage_json.write_text(json.dumps({"totals": {"percent_covered": "bad"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing numeric"):
        generate_coverage_trend.load_total_coverage(coverage_json)


def test_main_writes_json_and_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    coverage_json = tmp_path / "coverage.json"
    coverage_json.write_text(
        json.dumps({"totals": {"percent_covered": 91.234567}}), encoding="utf-8"
    )
    output_json = tmp_path / "out" / "coverage-trend.json"
    output_csv = tmp_path / "out" / "coverage-trend.csv"

    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_coverage_trend.py",
            "--coverage-json",
            str(coverage_json),
            "--output-json",
            str(output_json),
            "--output-csv",
            str(output_csv),
            "--sha",
            "deadbeef",
            "--branch",
            "main",
        ],
    )

    assert generate_coverage_trend.main() == 0

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["sha"] == "deadbeef"
    assert payload["branch"] == "main"
    assert payload["total_coverage"] == 91.2346
    assert payload["coverage_state"] == generate_coverage_trend.STATE_HIGH

    csv_lines = output_csv.read_text(encoding="utf-8").strip().splitlines()
    assert csv_lines[0] == "timestamp,sha,branch,total_coverage,coverage_state"
    assert csv_lines[1].endswith(",deadbeef,main,91.2346,high")
