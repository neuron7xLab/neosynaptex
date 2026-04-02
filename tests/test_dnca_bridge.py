"""8 tests for DncaBridge — DNCA↔Neosynaptex coupling."""

import numpy as np

from core.dnca_bridge import DivergenceReport, DncaBridge
from neosynaptex import MockBnSynAdapter, MockMfnAdapter, Neosynaptex


class MockDnca:
    """Mock DNCA orchestrator for testing."""

    def __init__(self, gamma: float = 1.0, regime: str = "critical") -> None:
        self._gamma = gamma
        self._regime = regime

    def get_gamma(self) -> float:
        return self._gamma

    def get_regime(self) -> str:
        return self._regime

    def get_neuromodulation(self) -> dict[str, float]:
        return {"dopamine": 0.02, "serotonin": -0.01, "norepinephrine": 0.03}


class MockDncaExcessive:
    """DNCA that wants excessive modulation."""

    def get_gamma(self) -> float:
        return 1.0

    def get_regime(self) -> str:
        return "critical"

    def get_neuromodulation(self) -> dict[str, float]:
        return {"dopamine": 0.5, "serotonin": -0.8}


def _make_engine(n_ticks: int = 20) -> Neosynaptex:
    engine = Neosynaptex(window=16)
    engine.register(MockBnSynAdapter())
    engine.register(MockMfnAdapter())
    for _ in range(n_ticks):
        engine.observe()
    return engine


def test_sync_gamma_both_present():
    engine = _make_engine(30)
    bridge = DncaBridge(dnca=MockDnca(gamma=1.0), engine=engine)
    result = bridge.sync_gamma()
    assert np.isfinite(result["dnca_gamma"])
    assert np.isfinite(result["neosynaptex_gamma"])
    assert np.isfinite(result["delta"])


def test_sync_gamma_no_dnca():
    bridge = DncaBridge(dnca=None, engine=_make_engine(20))
    result = bridge.sync_gamma()
    assert np.isnan(result["dnca_gamma"])
    assert np.isnan(result["delta"])


def test_sync_regime_match():
    engine = _make_engine(30)
    bridge = DncaBridge(dnca=MockDnca(regime="critical"), engine=engine)
    result = bridge.sync_regime()
    assert result["mapped_phase"] == "METASTABLE"


def test_sync_regime_mismatch():
    engine = _make_engine(30)
    bridge = DncaBridge(dnca=MockDnca(regime="chaotic"), engine=engine)
    result = bridge.sync_regime()
    assert result["mapped_phase"] == "DEGENERATE"


def test_neuromodulation_bounded():
    bridge = DncaBridge(dnca=MockDncaExcessive())
    mods = bridge.sync_neuromodulation()
    for val in mods.values():
        assert abs(val) <= 0.05, f"Modulation {val} exceeds bound"


def test_neuromodulation_normal():
    bridge = DncaBridge(dnca=MockDnca())
    mods = bridge.sync_neuromodulation()
    assert "dopamine" in mods
    assert mods["dopamine"] == 0.02


def test_divergence_report():
    engine = _make_engine(30)
    bridge = DncaBridge(dnca=MockDnca(gamma=1.0), engine=engine)
    report = bridge.get_divergence_report()
    assert isinstance(report, DivergenceReport)
    assert isinstance(report.warnings, tuple)
    assert np.isfinite(report.gamma_delta)


def test_divergence_history():
    engine = _make_engine(30)
    bridge = DncaBridge(dnca=MockDnca(), engine=engine)
    bridge.get_divergence_report()
    bridge.get_divergence_report()
    assert len(bridge.history) == 2
