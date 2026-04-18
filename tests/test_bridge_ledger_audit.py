"""Tests for ``tools/audit/bridge_ledger_audit.py``.

Covers:
    * Missing ledger → exit 3.
    * Tampered chain → exit 2.
    * Chain OK + DEAD verdict / chaotic regime / high risk → exit 1.
    * Chain OK + healthy stream → exit 0.
    * JSON report is written when requested.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from core.decision_bridge import DecisionBridge
from core.decision_bridge_telemetry import TelemetryLedger
from tools.audit.bridge_ledger_audit import audit, main


def _healthy_history(n: int = 12) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    phi = rng.normal(0, 0.1, size=(n, 4))
    gamma = 1.0 + rng.normal(0, 0.02, size=n)
    return phi, gamma


def _run_healthy_bridge(tmp_path: Path, n_ticks: int = 8) -> Path:
    ledger = TelemetryLedger(tmp_path / "healthy.jsonl")
    bridge = DecisionBridge(telemetry=ledger)
    phi, gamma = _healthy_history()
    for t in range(n_ticks):
        bridge.evaluate(
            tick=t,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
    return ledger.path


def _run_dead_bridge(tmp_path: Path) -> Path:
    ledger = TelemetryLedger(tmp_path / "dead.jsonl")
    bridge = DecisionBridge(telemetry=ledger)
    phi = np.ones((20, 4)) * 0.5
    gamma = np.ones(20)
    for t in range(5):
        bridge.evaluate(
            tick=t,
            gamma_mean=1.0,
            gamma_std=0.0,
            spectral_radius=0.5,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
    return ledger.path


class TestAuditExitCodes:
    def test_missing_ledger_returns_io_error(self, tmp_path: Path) -> None:
        exit_code, report = audit(tmp_path / "does_not_exist.jsonl")
        assert exit_code == 3
        assert report is None

    def test_healthy_stream_returns_zero(self, tmp_path: Path) -> None:
        path = _run_healthy_bridge(tmp_path)
        exit_code, report = audit(path)
        assert report is not None
        assert exit_code == 0
        assert report.anomalies == []
        assert report.verification["ok"] is True

    def test_dead_verdict_raises_anomaly_exit(self, tmp_path: Path) -> None:
        path = _run_dead_bridge(tmp_path)
        exit_code, report = audit(path)
        assert report is not None
        assert exit_code == 1
        assert any("DEAD" in a for a in report.anomalies)
        assert report.verification["ok"] is True  # chain still intact

    def test_tampered_ledger_returns_tamper_exit(self, tmp_path: Path) -> None:
        path = _run_healthy_bridge(tmp_path)
        # Corrupt one byte of one event's self_hash field.
        lines = path.read_text(encoding="utf-8").splitlines()
        obj = json.loads(lines[2])
        obj["payload"]["critic_gain"] = 0.9999  # silent edit; hash will mismatch
        lines[2] = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        exit_code, report = audit(path)
        assert report is not None
        assert exit_code == 2
        assert report.verification["ok"] is False


class TestAuditJSONReport:
    def test_json_report_is_written(self, tmp_path: Path) -> None:
        path = _run_healthy_bridge(tmp_path)
        report_path = tmp_path / "report.json"
        exit_code = main([str(path), "--json-report", str(report_path)])
        assert exit_code == 0
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["n_events"] > 0
        assert "health_histogram" in data
        assert "verification" in data
        assert data["verification"]["ok"] is True
