"""Tests for GNC+ ↔ EWS Bridge."""

from mycelium_fractal_net.neurochem.gnc import GNCState, compute_gnc_state
from mycelium_fractal_net.neurochem.gnc_ews_bridge import (
    TRANSITION_PATTERNS,
    detect_transition_pattern,
    gnc_ews_trajectory,
    gnc_predictive_ews,
)


class TestTransitionPatterns:
    def test_all_patterns_have_refs(self):
        for name, p in TRANSITION_PATTERNS.items():
            assert "ref" in p and len(p["ref"]) > 10, f"{name} missing ref"

    def test_all_patterns_have_risk(self):
        for p in TRANSITION_PATTERNS.values():
            assert p["risk"] in ("low", "medium", "high")

    def test_pattern_risk_scores_bounded(self):
        for p in TRANSITION_PATTERNS.values():
            assert 0 <= p["risk_score"] <= 1


class TestDetectPattern:
    def test_hyperexcitability(self):
        state = compute_gnc_state({"Glutamate": 0.85, "GABA": 0.20})
        patterns = detect_transition_pattern(state)
        names = [p["pattern_name"] for p in patterns]
        assert "hyperexcitability" in names

    def test_dopamine_crash(self):
        state = compute_gnc_state({"Dopamine": 0.90, "Serotonin": 0.15})
        patterns = detect_transition_pattern(state)
        names = [p["pattern_name"] for p in patterns]
        assert "dopamine_crash" in names

    def test_resilience_collapse(self):
        state = compute_gnc_state({"Opioid": 0.15, "Noradrenaline": 0.80})
        patterns = detect_transition_pattern(state)
        names = [p["pattern_name"] for p in patterns]
        assert "resilience_collapse" in names

    def test_no_pattern_on_healthy(self):
        patterns = detect_transition_pattern(GNCState.default())
        assert len(patterns) == 0

    def test_sorted_by_horizon(self):
        state = compute_gnc_state({
            "Glutamate": 0.85, "GABA": 0.20,
            "Opioid": 0.15, "Noradrenaline": 0.80,
        })
        patterns = detect_transition_pattern(state)
        if len(patterns) >= 2:
            horizons = [p["horizon_steps"] for p in patterns]
            assert horizons == sorted(horizons)


class TestPredictiveEWS:
    def test_nominal_on_default(self):
        result = gnc_predictive_ews(GNCState.default(), 0.1)
        assert result["level"] == "nominal"

    def test_combined_score_bounded(self):
        result = gnc_predictive_ews(GNCState.default(), 0.5)
        assert 0 <= result["combined_score"] <= 1

    def test_critical_when_both_high(self):
        state = compute_gnc_state({"Glutamate": 0.9, "GABA": 0.1})
        result = gnc_predictive_ews(state, 0.7)
        assert result["level"] in ("critical", "warning")

    def test_combined_is_max(self):
        state = compute_gnc_state({"Dopamine": 0.9, "Serotonin": 0.1})
        result = gnc_predictive_ews(state, 0.3)
        assert result["combined_score"] >= max(result["gnc_risk_score"], result["mfn_ews_score"])

    def test_recommendation_not_empty(self):
        result = gnc_predictive_ews(GNCState.default(), 0.5)
        assert len(result["recommendation"]) > 5

    def test_level_valid(self):
        for ews in [0.0, 0.3, 0.5, 0.8]:
            result = gnc_predictive_ews(GNCState.default(), ews)
            assert result["level"] in ("nominal", "watch", "warning", "critical")


class TestTrajectory:
    def test_stable_trajectory(self):
        states = [GNCState.default() for _ in range(5)]
        scores = [0.1] * 5
        result = gnc_ews_trajectory(states, scores)
        assert result["trend"] in ("stable", "insufficient")

    def test_increasing_trend(self):
        states = [
            compute_gnc_state({"Glutamate": 0.5 + i * 0.1, "GABA": 0.5 - i * 0.1})
            for i in range(5)
        ]
        scores = [0.1 + i * 0.15 for i in range(5)]
        result = gnc_ews_trajectory(states, scores)
        assert result["trend"] in ("increasing", "stable")

    def test_empty_trajectory(self):
        result = gnc_ews_trajectory([], [])
        assert result["trajectory_risk"] == 0.0

    def test_recommendation_present(self):
        states = [GNCState.default() for _ in range(3)]
        result = gnc_ews_trajectory(states, [0.1, 0.2, 0.3])
        assert len(result["recommendation"]) > 5
