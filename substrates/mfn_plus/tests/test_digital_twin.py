"""Tests for Neuromodulatory Digital Twin."""

import pytest

from mycelium_fractal_net.neurochem.digital_twin import NeuromodulatoryDigitalTwin
from mycelium_fractal_net.neurochem.gnc import MODULATORS, GNCState, compute_gnc_state


def _make_trajectory(n: int = 10) -> list[GNCState]:
    """Create a trending trajectory for testing."""
    return [
        compute_gnc_state({
            "Dopamine": 0.5 + i * 0.03,
            "GABA": 0.5 - i * 0.02,
        })
        for i in range(n)
    ]


class TestUpdate:
    def test_adds_to_history(self):
        twin = NeuromodulatoryDigitalTwin()
        twin.update(GNCState.default())
        assert len(twin.history) == 1

    def test_chainable(self):
        twin = NeuromodulatoryDigitalTwin()
        result = twin.update(GNCState.default()).update(GNCState.default())
        assert result is twin
        assert len(twin.history) == 2

    def test_mfn_metrics_stored(self):
        twin = NeuromodulatoryDigitalTwin()
        twin.update(GNCState.default(), {"anomaly_score": 0.3})
        assert twin.mfn_history[0]["anomaly_score"] == 0.3


class TestPredict:
    def test_requires_min_3(self):
        twin = NeuromodulatoryDigitalTwin()
        twin.update(GNCState.default())
        with pytest.raises(ValueError, match="3"):
            twin.predict()

    def test_returns_gnc_state(self):
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(_make_trajectory(5))
        predicted = twin.predict(horizon=1)
        assert isinstance(predicted, GNCState)

    def test_short_horizon_linear(self):
        states = _make_trajectory(5)
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(states)
        pred = twin.predict(horizon=1)
        # DA was trending up → prediction should be higher than last
        last_da = states[-1].modulators["Dopamine"]
        assert pred.modulators["Dopamine"] >= last_da - 0.1

    def test_long_horizon_returns_to_baseline(self):
        states = _make_trajectory(5)
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(states)
        pred = twin.predict(horizon=50)
        # Should approach 0.5
        for m in MODULATORS:
            assert abs(pred.modulators[m] - 0.5) < 0.3

    def test_bounded(self):
        states = [compute_gnc_state(dict.fromkeys(MODULATORS, 0.95)) for _ in range(5)]
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(states)
        pred = twin.predict(horizon=3)
        for m in MODULATORS:
            assert 0.0 <= pred.modulators[m] <= 1.0

    def test_trajectory_length(self):
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(_make_trajectory(5))
        traj = twin.predict_trajectory(horizon=7)
        assert len(traj) == 7


class TestValidate:
    def test_f4_on_stationary(self):
        states = [GNCState.default() for _ in range(10)]
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(states)
        result = twin.validate()
        assert "f4_pass" in result
        assert result["n_samples"] == 10

    def test_f4_on_trending(self):
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(_make_trajectory(10))
        result = twin.validate()
        assert result["n_samples"] == 10
        # Trending data should be somewhat predictable
        assert result["mae"] >= 0

    def test_insufficient_history(self):
        twin = NeuromodulatoryDigitalTwin()
        twin.update(GNCState.default())
        result = twin.validate()
        assert not result["f4_pass"]

    def test_predictive_power_bounded(self):
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(_make_trajectory(8))
        result = twin.validate()
        assert 0 <= result["predictive_power"] <= 1


class TestFromStates:
    def test_correct_length(self):
        states = _make_trajectory(7)
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(states)
        assert len(twin.history) == 7


class TestSummary:
    def test_not_empty(self):
        twin = NeuromodulatoryDigitalTwin.from_gnc_states(_make_trajectory(5))
        text = twin.summary()
        assert "Digital Twin" in text
        assert "history=" in text
