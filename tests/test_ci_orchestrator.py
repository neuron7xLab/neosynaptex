"""6 tests for CIOrchestrator — cross-substrate integration + gamma invariant."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from ci_orchestrator import CIOrchestrator  # noqa: E402


def test_cross_substrate_runs():
    orch = CIOrchestrator()
    result = orch.run_cross_substrate()
    assert "gamma_mean" in result
    assert np.isfinite(result["gamma_mean"])
    assert result["phase"] != "DEGENERATE"


def test_cross_substrate_gamma_in_range():
    orch = CIOrchestrator()
    result = orch.run_cross_substrate()
    assert 0.5 <= result["gamma_mean"] <= 1.5


def test_gamma_invariant_passes():
    orch = CIOrchestrator()
    cross = orch.run_cross_substrate()
    check = orch.run_gamma_invariant_check(cross["gamma_per_domain"])
    assert check["passed"]
    assert check["excludes_zero"]


def test_gamma_invariant_rejects_zeros():
    orch = CIOrchestrator()
    check = orch.run_gamma_invariant_check({"a": 0.0, "b": 0.0, "c": 0.0})
    assert not check["passed"]


def test_generate_report():
    orch = CIOrchestrator()
    report = orch.generate_report()
    assert report.cross_substrate_passed
    assert report.gamma_invariant_passed
    assert len(report.errors) == 0


def test_substrate_smoke_missing():
    orch = CIOrchestrator()
    # Non-existent substrate should return True (skip)
    assert orch.run_substrate_smoke("nonexistent_substrate")


def test_gamma_invariant_requires_two_finite_domains():
    orch = CIOrchestrator()
    check = orch.run_gamma_invariant_check({"a": np.nan, "b": 1.0, "c": np.inf})
    assert not check["passed"]
    assert check["reason"] == "insufficient valid gammas"


def test_gamma_invariant_ignores_non_finite_values():
    orch = CIOrchestrator()
    check = orch.run_gamma_invariant_check({"a": 1.0, "b": np.nan, "c": 1.2, "d": np.inf})
    assert check["passed"]
    assert check["n_domains"] == 2
    assert check["in_range"]


def test_generate_report_captures_cross_substrate_exceptions(monkeypatch):
    orch = CIOrchestrator()

    def _raise() -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr(orch, "run_cross_substrate", _raise)
    report = orch.generate_report()

    assert not report.cross_substrate_passed
    assert not report.gamma_invariant_passed
    assert report.phase == "ERROR"
    assert any("cross_substrate: boom" in err for err in report.errors)
