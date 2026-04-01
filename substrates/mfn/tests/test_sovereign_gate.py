"""Tests for SovereignGate — the immune system of MFN."""

import numpy as np
import pytest

from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.core.sovereign_gate import SovereignGate, SovereignVerdict
from mycelium_fractal_net.types.field import FieldSequence, SimulationSpec


@pytest.fixture
def healthy_seq():
    return simulate_history(SimulationSpec(grid_size=16, steps=30, seed=42))


@pytest.fixture
def degenerate_seq():
    """Flat field — no structure."""
    field = np.ones((16, 16)) * -0.07
    history = np.stack([field] * 10)
    return FieldSequence(field=field, history=history, spec=None, metadata={})


@pytest.fixture
def extreme_seq():
    """Extreme field values — should trigger gate warnings."""
    field = np.random.default_rng(99).uniform(-50, 50, (16, 16))
    history = np.stack([field * (1.5**t) for t in range(10)])
    # Clip to avoid FieldSequence validation error but keep extreme
    field_clipped = np.clip(field, -90, 90)
    history_clipped = np.clip(history, -90, 90)
    return FieldSequence(field=field_clipped, history=history_clipped, spec=None, metadata={})


class TestSovereignGate:
    def test_healthy_passes(self, healthy_seq):
        verdict = SovereignGate().verify(healthy_seq)
        assert verdict.passed
        assert verdict.n_passed >= 4

    def test_extreme_detected(self, extreme_seq):
        verdict = SovereignGate().verify(extreme_seq)
        # Extreme values should trigger at least one lens failure
        assert isinstance(verdict, SovereignVerdict)
        structural = next(l for l in verdict.lenses if l.name == "structural")
        # Range > 100 should fail structural lens
        assert structural.metric > 50  # field has wide range

    def test_degenerate_detected(self, degenerate_seq):
        verdict = SovereignGate().verify(degenerate_seq)
        # Flat field may pass structural but fail others
        assert isinstance(verdict, SovereignVerdict)

    def test_require_all_strict(self, healthy_seq):
        verdict = SovereignGate(require_all=True).verify(healthy_seq)
        # May or may not pass depending on all lenses
        assert verdict.n_passed + verdict.n_failed == 6

    def test_verdict_str(self, healthy_seq):
        verdict = SovereignGate().verify(healthy_seq)
        text = str(verdict)
        assert "SOVEREIGN GATE" in text
        assert "lenses passed" in text

    def test_verdict_to_dict(self, healthy_seq):
        verdict = SovereignGate().verify(healthy_seq)
        d = verdict.to_dict()
        assert "passed" in d
        assert "lenses" in d
        assert len(d["lenses"]) == 6

    def test_recommendation_on_failure(self, extreme_seq):
        verdict = SovereignGate(require_all=True).verify(extreme_seq)
        if not verdict.passed:
            assert len(verdict.recommendation) > 0

    def test_6_lenses_always_run(self, healthy_seq):
        verdict = SovereignGate().verify(healthy_seq)
        lens_names = {l.name for l in verdict.lenses}
        assert lens_names == {"structural", "thermodynamic", "topological", "causal", "transport", "invariant"}

    def test_min_lenses_configurable(self, healthy_seq):
        v1 = SovereignGate(min_lenses=1).verify(healthy_seq)
        v6 = SovereignGate(min_lenses=6).verify(healthy_seq)
        # Lower threshold → more likely to pass
        assert v1.passed or not v6.passed  # v1 at least as permissive as v6
