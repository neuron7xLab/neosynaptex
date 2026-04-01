from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


METRIC_NAME = "coverage.xml line-rate"
REQUIRED_BASELINE_KEYS = ("baseline_percent", "minimum_percent", "metric")


def read_coverage_percent(xml_path: Path) -> float:
    if not xml_path.exists():
        raise FileNotFoundError(f"coverage file not found: {xml_path}")
    root = ET.parse(xml_path).getroot()
    line_rate = root.attrib.get("line-rate")
    if line_rate is None:
        raise ValueError("coverage.xml missing line-rate attribute")
    return float(line_rate) * 100.0


def read_baseline_config(baseline_path: Path) -> dict[str, Any]:
    if not baseline_path.exists():
        raise FileNotFoundError(f"baseline file not found: {baseline_path}")
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"baseline JSON is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("baseline JSON root must be an object")

    missing_keys = [key for key in REQUIRED_BASELINE_KEYS if key not in data]
    if missing_keys:
        missing = ", ".join(missing_keys)
        raise ValueError(f"baseline JSON missing required keys: {missing}")

    return data


def check_gate(
    current: float,
    baseline: float,
    minimum: float,
    tolerance: float,
) -> tuple[bool, str]:
    if baseline < minimum:
        return (
            False,
            "FAIL: invalid baseline configuration; "
            f"baseline_percent ({baseline:.2f}%) < minimum_percent ({minimum:.2f}%)",
        )

    if current + tolerance < minimum:
        return (
            False,
            f"FAIL: coverage below minimum floor by more than {tolerance:.2f}% "
            f"(current={current:.2f}%, minimum={minimum:.2f}%)",
        )
    if current + tolerance < baseline:
        return (
            False,
            f"FAIL: coverage dropped below baseline by more than {tolerance:.2f}% "
            f"(current={current:.2f}%, baseline={baseline:.2f}%)",
        )
    return (True, "PASS: coverage gate satisfied")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check coverage gate against baseline and floor")
    parser.add_argument("--coverage-xml", type=Path, default=Path("coverage.xml"))
    parser.add_argument("--baseline", type=Path, default=Path("quality/coverage_gate.json"))
    parser.add_argument("--tolerance", type=float, default=0.05)
    args = parser.parse_args()

    try:
        current = read_coverage_percent(args.coverage_xml)
    except (FileNotFoundError, ValueError, ET.ParseError) as exc:
        print(f"FAIL: unable to read coverage metric {METRIC_NAME}: {exc}")
        return 1

    try:
        baseline_data = read_baseline_config(args.baseline)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: unable to read baseline config: {exc}")
        return 1

    try:
        baseline = float(baseline_data["baseline_percent"])
        minimum = float(baseline_data["minimum_percent"])
    except (TypeError, ValueError) as exc:
        print(f"FAIL: baseline numeric values are invalid: {exc}")
        return 1

    metric = str(baseline_data["metric"])

    print(f"Metric: {metric}")
    print(f"Current coverage: {current:.2f}%")
    print(f"Baseline coverage: {baseline:.2f}%")
    print(f"Minimum coverage: {minimum:.2f}%")

    passed, message = check_gate(
        current=current,
        baseline=baseline,
        minimum=minimum,
        tolerance=args.tolerance,
    )
    print(message)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
