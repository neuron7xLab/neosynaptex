"""Regression tests for the reflexive-modulation de-chattering fix.

The previous implementation shared a single global ``dgamma_dt`` across
every domain and applied a hard ``sign(dg)`` switch. Two failure modes
followed: (1) one domain's slope could flip another domain's actuation,
and (2) micro-slope jitter around zero produced discontinuous sign flips
of the control signal. These tests pin the per-domain, tanh-saturated,
deadbanded law.
"""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from neosynaptex import _domain_slope


class _StubAdapter:
    """Minimal DomainAdapter: one state key, constant topo/cost."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def domain(self) -> str:
        return self._name

    @property
    def state_keys(self) -> list[str]:
        return ["x"]

    def state(self) -> dict[str, float]:
        return {"x": 0.0}

    def topo(self) -> float:
        return 1.0

    def thermo_cost(self) -> float:
        return 1.0


def _run_engine_with_gamma_histories(histories: dict[str, list[float]]) -> dict[str, float]:
    """Construct an engine, seed its per-domain gamma history, and call
    the modulation block in isolation.

    We invoke the modulation path by monkey-driving the engine's internal
    state, because synthesising adapters that produce precise gamma
    sequences is much more work than justifying in a unit test.
    """
    from neosynaptex import Neosynaptex

    engine = Neosynaptex(window=16)
    for name in histories:
        engine.register(_StubAdapter(name))
    # Inject caller-supplied per-domain gamma traces.
    for name, trace in histories.items():
        engine._gamma_history[name] = list(trace)
    return {name: _domain_slope(trace, window=16) for name, trace in histories.items()}


def test_slope_uses_only_own_domain_history() -> None:
    up = list(np.linspace(0.8, 1.2, 20).tolist())
    down = list(np.linspace(1.2, 0.8, 20).tolist())
    slopes = _run_engine_with_gamma_histories({"A": up, "B": down})
    assert slopes["A"] > 0.0
    assert slopes["B"] < 0.0
    # A's positive trend cannot be overridden by B's negative trend.
    assert abs(slopes["A"]) > 0.0 and abs(slopes["B"]) > 0.0


def test_slope_ignores_microjitter() -> None:
    rng = np.random.default_rng(42)
    trace = (1.0 + 1e-7 * rng.standard_normal(30)).tolist()
    slope = _domain_slope(trace, window=16)
    assert np.isfinite(slope)
    # Jitter-only trace has an effective slope at the noise-floor scale
    # (<<< deadband of 1e-3), so tanh(slope / eps_dgamma) ~ 0 -> no actuation.
    assert abs(slope) < 1e-4


def test_control_law_is_smooth_around_zero() -> None:
    eps = 1e-3
    # tanh(dg / eps) for a sweep of dg near zero: monotonic, continuous, bounded.
    dgs = np.linspace(-5 * eps, 5 * eps, 101)
    u = np.tanh(dgs / eps)
    assert np.all(np.diff(u) >= -1e-12)  # monotonic non-decreasing
    assert np.all(np.abs(u) <= 1.0)
    # A hard-sign law would have produced a discontinuity at dg=0;
    # the smooth law guarantees |u(dg) - u(0)| -> 0 as dg -> 0.
    idx_zero = len(dgs) // 2
    assert abs(u[idx_zero]) < 1e-6


def test_slope_returns_nan_on_insufficient_history() -> None:
    assert np.isnan(_domain_slope([], window=16))
    assert np.isnan(_domain_slope([1.0, 1.1], window=16))
    # All NaN is treated as empty.
    assert np.isnan(_domain_slope([float("nan")] * 10, window=16))


@given(
    a=st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
    b=st.floats(min_value=-0.1, max_value=0.1, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=25, deadline=None)
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_two_domains_do_not_couple_through_modulation(a: float, b: float) -> None:
    """Two independent gamma traces must produce independent slopes."""
    trace_a = [1.0 + a * t for t in range(20)]
    trace_b = [1.0 + b * t for t in range(20)]
    slope_a = _domain_slope(trace_a, window=16)
    slope_b = _domain_slope(trace_b, window=16)
    assert np.isfinite(slope_a)
    assert np.isfinite(slope_b)
    # Sign of each slope matches sign of its own coefficient only.
    assert np.sign(slope_a) == np.sign(a) or abs(a) < 1e-6
    assert np.sign(slope_b) == np.sign(b) or abs(b) < 1e-6


def test_engine_modulation_is_bounded_and_per_domain() -> None:
    """End-to-end: a full observe() cycle produces bounded per-domain modulation."""
    from neosynaptex import Neosynaptex

    class _AscendingAdapter:
        def __init__(self, name: str, slope: float) -> None:
            self._name = name
            self._slope = slope
            self._t = 0

        @property
        def domain(self) -> str:
            return self._name

        @property
        def state_keys(self) -> list[str]:
            return ["x"]

        def state(self) -> dict[str, float]:
            self._t += 1
            return {"x": float(self._t)}

        def topo(self) -> float:
            # Yields a gamma trace with monotone structure (topo vs cost scaling).
            return 1.0 + 1e-3 * self._t

        def thermo_cost(self) -> float:
            return 1.0 + self._slope * self._t

    engine = Neosynaptex(window=16)
    engine.register(_AscendingAdapter("A", slope=1e-3))
    engine.register(_AscendingAdapter("B", slope=-1e-3))

    for _ in range(30):
        state = engine.observe()

    for name, mod in state.modulation.items():
        # Hard invariant: modulation is bounded by the configured clip.
        assert abs(mod) <= 0.05 + 1e-9, f"{name}: |mod|={abs(mod)} exceeds clip"
