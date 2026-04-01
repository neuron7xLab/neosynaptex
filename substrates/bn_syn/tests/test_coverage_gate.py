from __future__ import annotations

import json
from pathlib import Path

from scripts import check_coverage_gate
import pytest


def _write_xml(path: Path, line_rate: str | None = None) -> None:
    if line_rate is None:
        path.write_text('<coverage version="7.0"></coverage>', encoding="utf-8")
    else:
        path.write_text(f'<coverage line-rate="{line_rate}"></coverage>', encoding="utf-8")


def test_read_coverage_percent_parses_valid_xml(tmp_path: Path) -> None:
    xml_path = tmp_path / "coverage.xml"
    _write_xml(xml_path, "0.9957")

    assert check_coverage_gate.read_coverage_percent(xml_path) == pytest.approx(99.57)


def test_read_coverage_percent_missing_file_fails(tmp_path: Path) -> None:
    xml_path = tmp_path / "missing.xml"

    with pytest.raises(FileNotFoundError):
        check_coverage_gate.read_coverage_percent(xml_path)


def test_read_coverage_percent_missing_line_rate_fails(tmp_path: Path) -> None:
    xml_path = tmp_path / "coverage.xml"
    _write_xml(xml_path)

    try:
        check_coverage_gate.read_coverage_percent(xml_path)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "line-rate" in str(exc)


def test_read_baseline_missing_required_keys_fails(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"baseline_percent": 99.0}), encoding="utf-8")

    try:
        check_coverage_gate.read_baseline_config(baseline)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "missing required keys" in str(exc)


def test_read_baseline_invalid_json_fails(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{not json", encoding="utf-8")

    try:
        check_coverage_gate.read_baseline_config(baseline)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "invalid" in str(exc)


def test_check_gate_fails_when_baseline_below_minimum() -> None:
    passed, message = check_coverage_gate.check_gate(
        current=99.5,
        baseline=98.0,
        minimum=99.0,
        tolerance=0.05,
    )

    assert not passed
    assert "invalid baseline configuration" in message


def test_check_gate_fails_when_below_baseline_beyond_tolerance() -> None:
    passed, message = check_coverage_gate.check_gate(
        current=99.0,
        baseline=99.2,
        minimum=98.0,
        tolerance=0.05,
    )

    assert not passed
    assert "below baseline" in message


def test_check_gate_fails_when_below_minimum_beyond_tolerance() -> None:
    passed, message = check_coverage_gate.check_gate(
        current=98.8,
        baseline=99.2,
        minimum=99.0,
        tolerance=0.05,
    )

    assert not passed
    assert "below minimum floor" in message


def test_check_gate_passes_within_tolerance() -> None:
    passed, message = check_coverage_gate.check_gate(
        current=99.53,
        baseline=99.57,
        minimum=99.0,
        tolerance=0.05,
    )

    assert passed
    assert message == "PASS: coverage gate satisfied"


def test_main_fails_when_baseline_missing(tmp_path: Path, monkeypatch) -> None:
    xml_path = tmp_path / "coverage.xml"
    _write_xml(xml_path, "0.9957")
    missing_baseline = tmp_path / "missing.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_coverage_gate.py",
            "--coverage-xml",
            str(xml_path),
            "--baseline",
            str(missing_baseline),
        ],
    )

    assert check_coverage_gate.main() == 1


def test_main_fails_when_coverage_xml_missing(tmp_path: Path, monkeypatch) -> None:
    missing_xml = tmp_path / "missing.xml"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "baseline_percent": 99.0,
                "minimum_percent": 99.0,
                "metric": "coverage.xml line-rate",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_coverage_gate.py",
            "--coverage-xml",
            str(missing_xml),
            "--baseline",
            str(baseline),
        ],
    )

    assert check_coverage_gate.main() == 1


def test_main_fails_when_baseline_json_invalid(tmp_path: Path, monkeypatch) -> None:
    xml_path = tmp_path / "coverage.xml"
    _write_xml(xml_path, "0.9957")
    baseline = tmp_path / "baseline.json"
    baseline.write_text("{broken", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "check_coverage_gate.py",
            "--coverage-xml",
            str(xml_path),
            "--baseline",
            str(baseline),
        ],
    )

    assert check_coverage_gate.main() == 1
