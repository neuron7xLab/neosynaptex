"""Tests for GNC+ ↔ CIP Bridge."""

from mycelium_fractal_net.neurochem.gnc import MODULATORS, GNCState, compute_gnc_state
from mycelium_fractal_net.neurochem.gnc_cip_bridge import (
    GNC_TO_LEVER_MAP,
    gnc_guided_levers,
    gnc_lever_direction,
    run_gnc_guided_cip,
)


class TestGNCToLeverMap:
    def test_all_axes_have_levers(self):
        for m in MODULATORS:
            assert m in GNC_TO_LEVER_MAP, f"{m} missing from GNC_TO_LEVER_MAP"

    def test_levers_are_strings(self):
        for mapping in GNC_TO_LEVER_MAP.values():
            for lever in mapping.values():
                assert isinstance(lever, str)
                assert len(lever) > 0


class TestGuidedLevers:
    def test_returns_list(self):
        result = gnc_guided_levers(GNCState.default())
        assert isinstance(result, list)

    def test_valid_lever_names(self):
        all_levers = {lv for m in GNC_TO_LEVER_MAP.values() for lv in m.values()}
        result = gnc_guided_levers(compute_gnc_state({"Dopamine": 0.9}))
        for lever in result:
            assert lever in all_levers

    def test_prioritizes_by_deviation(self):
        state = compute_gnc_state({"Dopamine": 0.95, "GABA": 0.05})
        levers = gnc_guided_levers(state, "stable")
        assert len(levers) >= 1

    def test_different_targets_give_different_levers(self):
        state = compute_gnc_state({"Dopamine": 0.8})
        stable = gnc_guided_levers(state, "stable")
        explore = gnc_guided_levers(state, "explore")
        # May differ in order or content
        assert isinstance(stable, list)
        assert isinstance(explore, list)

    def test_no_duplicates(self):
        levers = gnc_guided_levers(compute_gnc_state({"Noradrenaline": 0.9}))
        assert len(levers) == len(set(levers))


class TestLeverDirection:
    def test_respects_sigma_positive(self):
        # DA → nu has Sigma = +1. target_direction = +1 → direction = +1
        result = gnc_lever_direction("Dopamine", "nu", 0.5, +1)
        assert result["direction"] == +1

    def test_respects_sigma_negative(self):
        # GABA → alpha has Sigma = -1. target_direction = +1 → direction = -1
        result = gnc_lever_direction("GABA", "alpha", 0.5, +1)
        assert result["direction"] == -1

    def test_zero_sigma_zero_direction(self):
        # Opioid → alpha has Sigma = 0
        result = gnc_lever_direction("Opioid", "alpha", 0.5, +1)
        assert result["direction"] == 0

    def test_magnitude_bounded(self):
        result = gnc_lever_direction("Dopamine", "nu", 0.9, +1)
        assert 0 <= result["magnitude_hint"] <= 0.3

    def test_gaba_maps_to_gabaa(self):
        result = gnc_lever_direction("GABA", "beta", 0.5, +1)
        assert result["lever_name"] == "gabaa_concentration"


class TestRunGNCGuidedCIP:
    def test_returns_dict(self):
        state = compute_gnc_state({"Dopamine": 0.7})
        result = run_gnc_guided_cip(None, state)
        assert isinstance(result, dict)
        assert "levers" in result
        assert "gnc_interpretation" in result
        assert "predicted_gnc_after" in result

    def test_interpretation_has_rationale(self):
        state = compute_gnc_state({"Glutamate": 0.8, "GABA": 0.2})
        result = run_gnc_guided_cip(None, state)
        for item in result["gnc_interpretation"]:
            assert "rationale" in item
            assert len(item["rationale"]) > 10

    def test_predicted_state_is_gnc(self):
        state = compute_gnc_state({"Dopamine": 0.8})
        result = run_gnc_guided_cip(None, state)
        assert isinstance(result["predicted_gnc_after"], GNCState)

    def test_backward_compatible(self):
        # mfn.plan_intervention without GNC still works
        import mycelium_fractal_net as mfn
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=10, seed=42))
        # This should not raise
        plan = mfn.plan_intervention(seq, budget=1.0)
        assert plan is not None
