"""Control-core tests for median/MAD patch in neosynaptex."""

from __future__ import annotations

import numpy as np

import neosynaptex as nxmod


class _Adapter:
    def __init__(self, name: str):
        self._name = name

    @property
    def domain(self) -> str:
        return self._name

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 1.0}

    def topo(self) -> float:
        return 2.0

    def thermo_cost(self) -> float:
        return 1.0


def _warm(nx: nxmod.Neosynaptex, ticks: int = 18):
    out = None
    for _ in range(ticks):
        out = nx.observe()
    return out


def test_robust_aggregation_median_not_mean(monkeypatch):
    # 4 coherent witnesses + 1 large outlier
    vals = [1.0, 1.02, 0.98, 1.01, 4.0]

    def fake_gamma(_t, _c, seed):
        i = seed % 100
        g = vals[i]
        return g, 0.9, g - 0.01, g + 0.01

    monkeypatch.setattr(nxmod, "_per_domain_gamma", fake_gamma)
    nx = nxmod.Neosynaptex(window=16, chi_min=0.0)
    for name in ["a", "b", "c", "d", "e"]:
        nx.register(_Adapter(name))
    s = _warm(nx)
    assert abs(s.gamma_mean - 1.005) < 1e-6


def test_outlier_isolation_detects_outlier(monkeypatch):
    vals = [1.0, 1.0, 1.0, 1.0, 5.0]

    def fake_gamma(_t, _c, seed):
        i = seed % 100
        g = vals[i]
        return g, 0.95, g - 0.01, g + 0.01

    monkeypatch.setattr(nxmod, "_per_domain_gamma", fake_gamma)
    nx = nxmod.Neosynaptex(window=16, chi_min=0.0)
    for name in ["a", "b", "c", "d", "e"]:
        nx.register(_Adapter(name))
    s = _warm(nx)
    assert s.anomaly_score["e"] > 0.8


def test_control_gate_open_closed(monkeypatch):
    vals = [1.0, 1.1, 1.2, 1.3, 1.4]

    def fake_gamma(_t, _c, seed):
        i = seed % 100
        g = vals[i]
        return g, 0.95, g - 0.02, g + 0.02

    monkeypatch.setattr(nxmod, "_per_domain_gamma", fake_gamma)
    nx_closed = nxmod.Neosynaptex(window=16, chi_min=0.95)
    nx_open = nxmod.Neosynaptex(window=16, chi_min=0.0)
    for c in (nx_closed, nx_open):
        for name in ["a", "b", "c", "d", "e"]:
            c.register(_Adapter(name))
    s_closed = _warm(nx_closed)
    s_open = _warm(nx_open)
    assert all(v == 0.0 for v in s_closed.modulation.values())
    assert any(abs(v) > 0 for v in s_open.modulation.values())


def test_modulation_clipping(monkeypatch):
    vals = [2.0, 2.0, 2.0, 2.0, 2.0]

    def fake_gamma(_t, _c, seed):
        i = seed % 100
        g = vals[i]
        return g, 0.95, g - 0.02, g + 0.02

    monkeypatch.setattr(nxmod, "_per_domain_gamma", fake_gamma)
    nx = nxmod.Neosynaptex(window=16, eta=10.0, epsilon=0.05, chi_min=0.0)
    for name in ["a", "b", "c", "d", "e"]:
        nx.register(_Adapter(name))
    s = _warm(nx)
    assert all(abs(v) <= 0.05 for v in s.modulation.values())


def test_fault_tolerance_k5_f2(monkeypatch):
    # 3 honest near 1.1 and 2 faulty outliers, median should stay near honest majority
    vals = [1.1, 1.11, 1.09, 3.5, -1.5]

    def fake_gamma(_t, _c, seed):
        i = seed % 100
        g = vals[i]
        return g, 0.8, g - 0.01, g + 0.01

    monkeypatch.setattr(nxmod, "_per_domain_gamma", fake_gamma)
    nx = nxmod.Neosynaptex(window=16, chi_min=0.0)
    for name in ["a", "b", "c", "d", "e"]:
        nx.register(_Adapter(name))
    s = _warm(nx)
    assert np.isfinite(s.gamma_mean)
    assert abs(s.gamma_mean - 1.1) < 0.02
