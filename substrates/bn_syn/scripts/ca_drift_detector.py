from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DRIFT_REPORT_PATH = REPO_ROOT / "artifacts" / "ca_dccg" / "05_enforcement" / "DRIFT_REPORT.json"


def assert_zero_drift() -> dict[str, object]:
    report = json.loads(DRIFT_REPORT_PATH.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        msg = "DRIFT_REPORT.json must be a JSON object"
        raise ValueError(msg)
    drifts = report.get("drifts", [])
    if not isinstance(drifts, list):
        msg = "drifts field must be a JSON array"
        raise ValueError(msg)
    if drifts:
        msg = "Drift detected; merge must fail closed"
        raise ValueError(msg)
    return report


if __name__ == "__main__":
    assert_zero_drift()
