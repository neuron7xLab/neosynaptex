from __future__ import annotations

from scripts.ca_drift_detector import assert_zero_drift


def test_drift_zero_contract() -> None:
    report = assert_zero_drift()
    assert report["status"] == "PASS"
    assert report["drifts"] == []
