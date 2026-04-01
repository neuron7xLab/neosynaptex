"""Generate compact coverage trend artifacts for CI observability."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, TypedDict

FIELD_TIMESTAMP: Final[str] = "timestamp"
FIELD_SHA: Final[str] = "sha"
FIELD_BRANCH: Final[str] = "branch"
FIELD_TOTAL_COVERAGE: Final[str] = "total_coverage"
FIELD_COVERAGE_STATE: Final[str] = "coverage_state"
COVERAGE_SCALE_MIN: Final[float] = 0.0
COVERAGE_SCALE_MAX: Final[float] = 100.0
COVERAGE_PRECISION_DIGITS: Final[int] = 4

STATE_CRITICAL: Final[str] = "critical"
STATE_LOW: Final[str] = "low"
STATE_MODERATE: Final[str] = "moderate"
STATE_HIGH: Final[str] = "high"
STATE_EXCELLENT: Final[str] = "excellent"

STATE_THRESHOLDS: Final[tuple[tuple[float, str], ...]] = (
    (50.0, STATE_CRITICAL),
    (70.0, STATE_LOW),
    (85.0, STATE_MODERATE),
    (95.0, STATE_HIGH),
    (101.0, STATE_EXCELLENT),
)


class CoverageTrendPayload(TypedDict):
    """Serialized coverage trend schema."""

    timestamp: str
    sha: str
    branch: str
    total_coverage: float
    coverage_state: str


@dataclass(frozen=True)
class CoverageTrendRecord:
    """Single point-in-time coverage metric record."""

    timestamp: str
    sha: str
    branch: str
    total_coverage: float
    coverage_state: str

    def to_payload(self) -> CoverageTrendPayload:
        """Return payload representation with unified 0..100 scale."""
        return CoverageTrendPayload(
            timestamp=self.timestamp,
            sha=self.sha,
            branch=self.branch,
            total_coverage=self.total_coverage,
            coverage_state=self.coverage_state,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--sha", type=str, required=True)
    parser.add_argument("--branch", type=str, required=True)
    return parser.parse_args()


def normalize_coverage_percent(value: float) -> float:
    """Normalize coverage to the unified 0..100 percentage scale."""
    if value < COVERAGE_SCALE_MIN or value > COVERAGE_SCALE_MAX:
        raise ValueError("Coverage percent must be within [0, 100]")
    return round(value, COVERAGE_PRECISION_DIGITS)


def validate_state_thresholds(thresholds: tuple[tuple[float, str], ...]) -> None:
    """Validate deterministic state thresholds for quantization."""
    if not thresholds:
        raise ValueError("State thresholds must not be empty")

    previous_boundary = COVERAGE_SCALE_MIN
    for boundary, _state in thresholds:
        if boundary <= previous_boundary:
            raise ValueError("State thresholds must be strictly increasing")
        previous_boundary = boundary

    if thresholds[-1][0] <= COVERAGE_SCALE_MAX:
        raise ValueError("Last state threshold must exceed 100 to cover the full range")


def quantize_coverage_state(total_coverage: float) -> str:
    """Quantize normalized coverage into deterministic discrete states."""
    validate_state_thresholds(STATE_THRESHOLDS)
    for boundary, state in STATE_THRESHOLDS:
        if total_coverage < boundary:
            return state
    raise ValueError("Coverage value could not be quantized")


def load_total_coverage(coverage_json_path: Path) -> float:
    with coverage_json_path.open("r", encoding="utf-8") as coverage_file:
        coverage_payload = json.load(coverage_file)
    totals = coverage_payload.get("totals", {})
    total_coverage = totals.get("percent_covered")
    if not isinstance(total_coverage, int | float):
        raise ValueError("Missing numeric totals.percent_covered in coverage JSON")
    return normalize_coverage_percent(float(total_coverage))


def build_record(total_coverage: float, sha: str, branch: str) -> CoverageTrendRecord:
    return CoverageTrendRecord(
        timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        sha=sha,
        branch=branch,
        total_coverage=total_coverage,
        coverage_state=quantize_coverage_state(total_coverage),
    )


def write_outputs(
    record: CoverageTrendRecord, output_json_path: Path, output_csv_path: Path
) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    payload = record.to_payload()

    with output_json_path.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, separators=(",", ":"))
        json_file.write("\n")

    with output_csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                FIELD_TIMESTAMP,
                FIELD_SHA,
                FIELD_BRANCH,
                FIELD_TOTAL_COVERAGE,
                FIELD_COVERAGE_STATE,
            ],
        )
        writer.writeheader()
        writer.writerow(payload)


def main() -> int:
    args = parse_args()
    total_coverage = load_total_coverage(args.coverage_json)
    record = build_record(total_coverage, args.sha, args.branch)
    write_outputs(record, args.output_json, args.output_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
