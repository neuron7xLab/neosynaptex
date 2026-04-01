#!/usr/bin/env python3
"""Assert gate-id canonicality and benchmark honesty/document alignment."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

CANONICAL_GATES = ["G0_INTEGRITY", "G1_MINIMUM_READINESS", "G2_EVIDENCE_SUFFICIENCY"]


def assert_gate_ids(eval_fixture: Path) -> None:
    doc = json.loads(eval_fixture.read_text(encoding="utf-8"))
    ids = [g["gate_id"] for g in doc["gate_results"]]
    assert ids == CANONICAL_GATES, ids


def assert_benchmark_honesty(metrics: dict) -> None:
    assert metrics.get("status") == "DEMO_VALIDATION_ONLY", metrics.get("status")
    assert int(metrics.get("case_count", 0)) >= 10, metrics.get("case_count")
    assert int(metrics.get("adversarial_case_count", 0)) >= 4, metrics.get("adversarial_case_count")
    assert float(metrics.get("gate_agreement", 0)) >= 0.9, metrics.get("gate_agreement")
    assert float(metrics.get("anti_gaming_recall", 0)) >= 0.9, metrics.get("anti_gaming_recall")


def assert_benchmark_doc_alignment(root: Path, metrics: dict) -> None:
    readme = (root / "benchmark/README.md").read_text(encoding="utf-8")
    dashboard = (root / "benchmark-dashboard.html").read_text(encoding="utf-8")
    report = (root / "docs/BENCHMARK_REPORT_2026.md").read_text(encoding="utf-8")

    assert "synthetic demo benchmark" in readme, "benchmark README drift"
    assert "Included demo benchmark" in dashboard and "Metrics JSON" in dashboard, "benchmark dashboard drift"
    assert "synthetic harness-validation benchmark" in report, "benchmark report drift"

    case_csv = root / "benchmark/results/case_level_results.csv"
    rows = list(csv.DictReader(case_csv.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == int(metrics["case_count"]), (len(rows), metrics["case_count"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--gate-fixture", default="tests/fixtures/evaluation-result.valid.json")
    parser.add_argument("--metrics", default="benchmark/metrics.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    assert_gate_ids((root / args.gate_fixture).resolve())
    metrics = json.loads((root / args.metrics).read_text(encoding="utf-8"))
    assert_benchmark_honesty(metrics)
    assert_benchmark_doc_alignment(root, metrics)

    print("GATE_AND_BENCHMARK_INVARIANTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
