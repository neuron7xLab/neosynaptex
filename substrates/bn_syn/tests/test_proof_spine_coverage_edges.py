from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from bnsyn.experiments import declarative as decl
from bnsyn.proof import evaluate as proof_eval


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_fit_power_law_handles_no_positive_avalanches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = {
        "avalanche_admission": {
            "min_tail_count": 5,
            "p_value_threshold": 0.05,
            "ks_max": 0.3,
            "monte_carlo_simulations": 2,
        }
    }
    policy_path = tmp_path / "policy.json"
    _write_json(policy_path, policy)
    monkeypatch.setattr(decl, "STAT_POWER_CONFIG_PATH", policy_path)

    result = decl._fit_power_law([0, -1, 0], seed=11)
    assert result["validity"]["verdict"] == "FAIL"
    assert "no positive avalanches" in result["validity"]["reasons"]


def test_fit_power_law_nonfinite_alpha_and_ks_threshold_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = {
        "avalanche_admission": {
            "min_tail_count": 1,
            "p_value_threshold": 0.0,
            "ks_max": -1.0,
            "monte_carlo_simulations": 2,
        }
    }
    policy_path = tmp_path / "policy.json"
    _write_json(policy_path, policy)
    monkeypatch.setattr(decl, "STAT_POWER_CONFIG_PATH", policy_path)

    mle_calls = {"n": 0}

    def _fake_mle(_: np.ndarray, __: int) -> float:
        mle_calls["n"] += 1
        if mle_calls["n"] == 1:
            return 1.0  # exercises alpha<=1 branch
        return 2.5

    monkeypatch.setattr(decl, "_powerlaw_mle_alpha", _fake_mle)
    monkeypatch.setattr(decl, "_powerlaw_ks_distance", lambda *_args: 0.25)

    result = decl._fit_power_law([1, 2, 3, 4, 5, 6], seed=23)
    assert result["validity"]["verdict"] == "FAIL"
    assert "ks_distance above threshold" in result["validity"]["reasons"]


def test_build_emergence_image_rejects_non_2d_inputs() -> None:
    with pytest.raises(ValueError, match="must be 2D arrays"):
        decl._build_emergence_image(np.array([1, 2], dtype=np.uint8), np.array([3, 4], dtype=np.uint8))


def test_proof_gate_parsers_fail_closed_on_missing_sections_and_bad_json(tmp_path: Path) -> None:
    artifact_dir = tmp_path

    _write_json(artifact_dir / "robustness_report.json", {"replay_check": "bad"})
    _write_json(artifact_dir / "avalanche_fit_report.json", {"alpha": 2.1})
    _write_json(artifact_dir / "envelope_report.json", {"verdict": "FAIL", "failure_reasons": ["x"]})

    g6 = proof_eval.evaluate_gate_g6_determinism(artifact_dir)
    g7 = proof_eval.evaluate_gate_g7_avalanche(artifact_dir)
    g8 = proof_eval.evaluate_gate_g8_repro_envelope(artifact_dir)

    assert g6["status"] == "FAIL" and g6["details"] == "missing replay_check"
    assert g7["status"] == "FAIL" and g7["details"] == "missing validity section"
    assert g8["status"] == "FAIL" and g8.get("errors") == ["x"]

    (artifact_dir / "robustness_report.json").write_text("{", encoding="utf-8")
    (artifact_dir / "avalanche_fit_report.json").write_text("{", encoding="utf-8")
    (artifact_dir / "envelope_report.json").write_text("{", encoding="utf-8")

    assert "determinism gate unreadable" in proof_eval.evaluate_gate_g6_determinism(artifact_dir)["details"]
    assert "avalanche gate unreadable" in proof_eval.evaluate_gate_g7_avalanche(artifact_dir)["details"]
    assert "envelope gate unreadable" in proof_eval.evaluate_gate_g8_repro_envelope(artifact_dir)["details"]


def test_compute_verdict_inconclusive_path() -> None:
    gates = {
        "G1_active_spiking": {"status": "INCONCLUSIVE"},
        "G2_rate_in_bounds": {"status": "PASS"},
    }
    registry = {
        "G1_active_spiking": {"status": "wired"},
        "G2_rate_in_bounds": {"status": "wired"},
    }
    verdict, code, reasons = proof_eval._compute_verdict(gates, registry)
    assert verdict == "INCONCLUSIVE"
    assert code == 1
    assert reasons == ["G1_active_spiking unresolved"]
