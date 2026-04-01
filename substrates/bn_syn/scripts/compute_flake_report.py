from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


@dataclass
class TestFailureRate:
    test: str
    runs: int
    failures: int
    fail_rate: float
    quarantined: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute a flake-rate report from a JUnit XML file.")
    parser.add_argument("--junit", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protocol = yaml.safe_load(args.protocol.read_text(encoding="utf-8"))
    threshold = float(protocol["protocol"]["flake_quarantine"]["fail_rate_threshold"])

    tree = ET.parse(args.junit)
    root = tree.getroot()

    reports: list[TestFailureRate] = []
    for testcase in root.findall(".//testcase"):
        name = f"{testcase.attrib.get('classname', '<unknown>')}::{testcase.attrib.get('name', '<unknown>')}"
        failed = int(any(child.tag in {"failure", "error"} for child in testcase))
        fail_rate = float(failed)
        reports.append(
            TestFailureRate(
                test=name,
                runs=1,
                failures=failed,
                fail_rate=fail_rate,
                quarantined=fail_rate > threshold,
            )
        )

    quarantined = [r for r in reports if r.quarantined]
    payload = {
        "threshold": threshold,
        "source": str(args.junit),
        "tests": [asdict(item) for item in reports],
        "quarantined_count": len(quarantined),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Flake Report",
        "",
        f"- Threshold: `{threshold:.2%}`",
        f"- Total tests scanned: `{len(reports)}`",
        f"- Quarantined tests: `{len(quarantined)}`",
    ]
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
