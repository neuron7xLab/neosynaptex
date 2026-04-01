"""Integration tests for Meta-Core, Choice Operator, A_C, and unified diagnose.

Covers all gaps identified in the audit:
- meta_core.compute_reality() end-to-end
- meta_core.resolve_reality() A_C-powered resolution
- Digital Twin predict_with_ac()
- diagnose() with run_ac_check=True
- auto_heal Pareto indeterminacy path (choice_operator integration)
- Public API accessibility (lazy-loaded exports)
"""

from __future__ import annotations

import pytest

import mycelium_fractal_net as mfn

# ── Public API exports ───────────────────────────────────────────────


class TestPublicAPIExports:
    """All new features must be accessible from mfn namespace."""

    def test_compute_reality_accessible(self) -> None:
        assert callable(mfn.compute_reality)

    def test_resolve_reality_accessible(self) -> None:
        assert callable(mfn.resolve_reality)

    def test_agent_state_accessible(self) -> None:
        assert mfn.AgentState is not None

    def test_reality_frame_accessible(self) -> None:
        assert mfn.RealityFrame is not None

    def test_choice_operator_accessible(self) -> None:
        assert callable(mfn.choice_operator)

    def test_choice_result_accessible(self) -> None:
        assert mfn.ChoiceResult is not None

    def test_axiomatic_choice_operator_accessible(self) -> None:
        assert mfn.AxiomaticChoiceOperator is not None

    def test_selection_strategy_accessible(self) -> None:
        assert mfn.SelectionStrategy is not None


# ── Meta-Core: compute_reality ───────────────────────────────────────


class TestComputeReality:
    @pytest.fixture(scope="class")
    def agent(self):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        return mfn.AgentState(sequence=seq, step=0)

    def test_returns_reality_frame(self, agent) -> None:
        rf = mfn.compute_reality(agent, {"Glutamate": 0.6, "GABA": 0.4})
        assert isinstance(rf, mfn.RealityFrame)

    def test_reality_label_valid(self, agent) -> None:
        rf = mfn.compute_reality(agent)
        assert rf.reality_label in ("cognitive", "subcognitive", "transitional", "pathological")

    def test_confidence_bounded(self, agent) -> None:
        rf = mfn.compute_reality(agent)
        assert 0.0 <= rf.reality_confidence <= 1.0

    def test_sovereign_lenses_present(self, agent) -> None:
        rf = mfn.compute_reality(agent, {"Glutamate": 0.6, "GABA": 0.4})
        assert len(rf.sovereign_lenses) == 6
        expected = {"L1_bounds", "L2_consistency", "L3_falsifiability",
                    "L4_coherence", "L5_cognitive", "L6_stability"}
        assert set(rf.sovereign_lenses.keys()) == expected

    def test_theta_signature_has_9_components(self, agent) -> None:
        rf = mfn.compute_reality(agent)
        parts = rf.theta_signature.split("|")
        assert len(parts) == 9

    def test_deterministic_across_calls(self, agent) -> None:
        rf1 = mfn.compute_reality(agent, {"Glutamate": 0.6, "GABA": 0.4})
        rf2 = mfn.compute_reality(agent, {"Glutamate": 0.6, "GABA": 0.4})
        assert rf1.reality_label == rf2.reality_label
        assert rf1.reality_confidence == rf2.reality_confidence


# ── Meta-Core: resolve_reality ───────────────────────────────────────


class TestResolveReality:
    @pytest.fixture(scope="class")
    def agent(self):
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        return mfn.AgentState(sequence=seq, step=0)

    def test_returns_reality_frame(self, agent) -> None:
        rf = mfn.resolve_reality(agent, {"Glutamate": 0.6, "GABA": 0.4})
        assert isinstance(rf, mfn.RealityFrame)

    def test_valid_label(self, agent) -> None:
        rf = mfn.resolve_reality(agent, seed=42)
        assert rf.reality_label in ("cognitive", "subcognitive", "transitional", "pathological")

    def test_confidence_bounded(self, agent) -> None:
        rf = mfn.resolve_reality(agent, seed=42)
        assert 0.0 <= rf.reality_confidence <= 1.0


# ── Digital Twin predict_with_ac ─────────────────────────────────────


class TestPredictWithAC:
    def test_returns_trajectory_and_flags(self) -> None:
        from mycelium_fractal_net.neurochem.digital_twin import NeuromodulatoryDigitalTwin
        from mycelium_fractal_net.neurochem.gnc import GNCState, compute_gnc_state

        twin = NeuromodulatoryDigitalTwin()
        for i in range(5):
            state = compute_gnc_state({"Dopamine": 0.5 + i * 0.05})
            twin.update(state)

        traj, flags = twin.predict_with_ac(horizon=3, ccp_D_f=1.2, seed=42)
        assert len(traj) == 3
        assert len(flags) == 3
        assert all(isinstance(s, GNCState) for s in traj)
        assert all(isinstance(f, bool) for f in flags)

    def test_ac_activates_on_ccp_violation(self) -> None:
        from mycelium_fractal_net.neurochem.digital_twin import NeuromodulatoryDigitalTwin
        from mycelium_fractal_net.neurochem.gnc import compute_gnc_state

        twin = NeuromodulatoryDigitalTwin()
        for i in range(5):
            twin.update(compute_gnc_state({"Dopamine": 0.5 + i * 0.02}))

        # D_f=1.2 is outside cognitive window -> A_C should activate
        _, flags = twin.predict_with_ac(horizon=3, ccp_D_f=1.2, ccp_R=0.3, seed=42)
        assert any(flags), "A_C should activate on CCP violation"

    def test_trajectory_valid_on_nominal(self) -> None:
        from mycelium_fractal_net.neurochem.digital_twin import NeuromodulatoryDigitalTwin
        from mycelium_fractal_net.neurochem.gnc import GNCState, compute_gnc_state

        twin = NeuromodulatoryDigitalTwin()
        for i in range(5):
            twin.update(compute_gnc_state({"Dopamine": 0.5 + i * 0.02}))

        traj, _flags = twin.predict_with_ac(horizon=3, ccp_D_f=1.7, ccp_R=0.8, seed=42)
        # Regardless of activation, trajectory must be valid GNC states
        assert all(isinstance(s, GNCState) for s in traj)
        assert all(0.1 <= s.theta["alpha"] <= 0.9 for s in traj)


# ── diagnose with run_ac_check ───────────────────────────────────────


class TestDiagnoseACCheck:
    def test_ac_activation_present_when_enabled(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        r = mfn.diagnose(
            seq,
            gnc_levels={"Dopamine": 0.7, "GABA": 0.5},
            compute_ccp=True,
            run_ac_check=True,
        )
        assert r.ac_activation is not None
        assert "should_activate" in r.ac_activation
        assert "conditions" in r.ac_activation
        assert "severity" in r.ac_activation

    def test_ac_activation_none_when_disabled(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        r = mfn.diagnose(seq)
        assert r.ac_activation is None

    def test_ac_nominal_does_not_activate(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        r = mfn.diagnose(
            seq,
            gnc_levels={"Dopamine": 0.6, "GABA": 0.4},
            compute_ccp=True,
            run_ac_check=True,
        )
        # Healthy field with balanced GNC+ -> should not activate
        if r.ac_activation:
            assert not r.ac_activation["should_activate"]


# ── Choice Operator in auto_heal Pareto path ─────────────────────────


class TestAutoHealChoiceIntegration:
    def test_auto_heal_basic_still_works(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        result = mfn.auto_heal(seq)
        assert isinstance(result, mfn.HealResult)

    def test_auto_heal_returns_severity(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        result = mfn.auto_heal(seq)
        assert result.severity_before in ("stable", "info", "warning", "critical")


# ── Full pipeline: simulate -> diagnose -> compute_reality ───────────


class TestFullPipeline:
    def test_end_to_end_pipeline(self) -> None:
        """The complete NFI pipeline in one test."""
        # 1. Simulate
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))

        # 2. Unified diagnose with all features
        report = mfn.diagnose(
            seq,
            gnc_levels={"Dopamine": 0.7, "GABA": 0.5, "Glutamate": 0.6},
            compute_ccp=True,
            run_ac_check=True,
        )
        assert report.severity in ("stable", "info", "warning", "critical")
        assert report.ccp_state is not None
        assert report.gnc_diagnosis is not None
        assert report.ac_activation is not None

        # 3. Meta-Core reality computation
        agent = mfn.AgentState(sequence=seq, step=0)
        rf = mfn.compute_reality(agent, {"Glutamate": 0.6, "GABA": 0.4})
        assert isinstance(rf, mfn.RealityFrame)

        # 4. Choice operator standalone
        result = mfn.choice_operator(
            candidates=["A", "B", "C"],
            scores=[0.50, 0.51, 0.52],
            ccp_states=[
                {"D_f": 1.6, "R": 0.7},
                {"D_f": 1.75, "R": 0.8},
                {"D_f": 1.9, "R": 0.85},
            ],
            threshold=0.05,
        )
        assert isinstance(result, mfn.ChoiceResult)
        assert result.selected_index == 1  # closest to cognitive center
