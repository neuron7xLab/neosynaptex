"""Tests for Axiomatic Choice Operator A_C — axioms A1-A5, all strategies."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.neurochem.axiomatic_choice import (
    ActivationCondition,
    AxiomaticChoiceOperator,
    SelectionStrategy,
    check_activation_conditions,
)
from mycelium_fractal_net.neurochem.gnc import (
    MODULATORS,
    THETA,
    GNCState,
    compute_gnc_state,
    gnc_diagnose,
)

# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def healthy_state():
    return compute_gnc_state({
        "Glutamate": 0.65, "GABA": 0.40, "Noradrenaline": 0.55,
        "Serotonin": 0.50, "Dopamine": 0.60, "Acetylcholine": 0.55, "Opioid": 0.55,
    })


@pytest.fixture
def candidates():
    return [
        compute_gnc_state({
            "Glutamate": 0.65, "GABA": 0.40, "Noradrenaline": 0.55,
            "Serotonin": 0.50, "Dopamine": 0.60, "Acetylcholine": 0.55, "Opioid": 0.55,
        }),
        compute_gnc_state(dict.fromkeys(MODULATORS, 0.5)),
        compute_gnc_state(dict.fromkeys(MODULATORS, 0.4)),
    ]


# ── Activation tests ─────────────────────────────────────────────────


class TestActivation:
    def test_ccp_d_f_violation(self, healthy_state) -> None:
        r = check_activation_conditions(healthy_state, ccp_D_f=1.2)
        assert r.should_activate
        assert ActivationCondition.CCP_VIOLATION_D_F in r.active_conditions

    def test_ccp_r_violation(self, healthy_state) -> None:
        r = check_activation_conditions(healthy_state, ccp_R=0.2)
        assert r.should_activate
        assert ActivationCondition.CCP_VIOLATION_R in r.active_conditions

    def test_gradient_vanished(self, healthy_state) -> None:
        r = check_activation_conditions(healthy_state, gradient_norm=0.001)
        assert r.should_activate
        assert ActivationCondition.GRADIENT_VANISHED in r.active_conditions

    def test_j_equivalence(self, healthy_state) -> None:
        r = check_activation_conditions(healthy_state, j_values=[0.51, 0.50, 0.52])
        assert r.should_activate
        assert ActivationCondition.J_EQUIVALENCE in r.active_conditions

    def test_theta_stagnation(self, healthy_state) -> None:
        almost_same = compute_gnc_state({
            m: healthy_state.modulators[m] + 0.0001 for m in MODULATORS
        })
        r = check_activation_conditions(healthy_state, prev_gnc_state=almost_same)
        assert r.should_activate
        assert ActivationCondition.THETA_STAGNATION in r.active_conditions

    def test_no_activation_nominal(self, healthy_state) -> None:
        r = check_activation_conditions(healthy_state, ccp_D_f=1.71, ccp_R=0.80)
        assert not r.should_activate

    def test_severity_increases(self, healthy_state) -> None:
        r1 = check_activation_conditions(healthy_state, ccp_D_f=1.2)
        r2 = check_activation_conditions(healthy_state, ccp_D_f=1.2, ccp_R=0.2)
        assert r2.severity >= r1.severity

    def test_summary_inactive(self, healthy_state) -> None:
        r = check_activation_conditions(healthy_state, ccp_D_f=1.7, ccp_R=0.8)
        assert "inactive" in r.summary()

    def test_summary_active(self, healthy_state) -> None:
        r = check_activation_conditions(healthy_state, ccp_D_f=1.2)
        assert "ACTIVATE" in r.summary()


# ── A1: Admissibility ────────────────────────────────────────────────


class TestA1:
    def test_selected_is_gnc_state(self, candidates) -> None:
        op = AxiomaticChoiceOperator()
        selected = op.select(candidates, force=True)
        assert isinstance(selected, GNCState)

    def test_empty_candidates_raises(self) -> None:
        op = AxiomaticChoiceOperator()
        with pytest.raises(ValueError, match="empty"):
            op.select([])


# ── A2: CCP-Closure ──────────────────────────────────────────────────


class TestA2:
    def test_selected_has_valid_regime(self, candidates) -> None:
        op = AxiomaticChoiceOperator()
        selected = op.select(candidates, force=True)
        diag = gnc_diagnose(selected)
        assert diag.regime in ("optimal", "hyperactivated", "hypoactivated", "dysregulated")


# ── A3: Non-Derivability ─────────────────────────────────────────────


class TestA3:
    def test_ensemble_produces_selection(self, candidates) -> None:
        op = AxiomaticChoiceOperator(strategy=SelectionStrategy.ENSEMBLE)
        s = op.select(candidates, force=True)
        assert s is not None


# ── A4: Phase Induction ──────────────────────────────────────────────


class TestA4:
    def test_delta_theta_nonzero(self, candidates) -> None:
        prev = compute_gnc_state(dict.fromkeys(MODULATORS, 0.5))
        op = AxiomaticChoiceOperator()
        selected = op.select(candidates, prev_state=prev, force=True)
        delta = np.mean([abs(selected.theta[t] - prev.theta[t]) for t in THETA])
        assert delta > 1e-6

    def test_perturbation_when_identical(self) -> None:
        """When selected == prev, A4 perturbation kicks in."""
        state = compute_gnc_state(dict.fromkeys(MODULATORS, 0.5))
        op = AxiomaticChoiceOperator(seed=42)
        selected = op.select([state], prev_state=state, force=True)
        delta = np.mean([abs(selected.theta[t] - state.theta[t]) for t in THETA])
        assert delta > 1e-6  # perturbation applied


# ── A5: Stabilization ────────────────────────────────────────────────


class TestA5:
    def test_selected_coherence_positive(self, candidates) -> None:
        op = AxiomaticChoiceOperator()
        selected = op.select(candidates, force=True)
        assert gnc_diagnose(selected).coherence > 0.0


# ── Strategy tests ───────────────────────────────────────────────────


class TestStrategies:
    def test_max_coherence_selects_highest(self, candidates) -> None:
        op = AxiomaticChoiceOperator(strategy=SelectionStrategy.MAX_COHERENCE)
        selected = op.select(candidates, force=True)
        selected_coh = gnc_diagnose(selected).coherence
        all_cohs = [gnc_diagnose(c).coherence for c in candidates]
        assert selected_coh == max(all_cohs)

    def test_random_returns_valid(self, candidates) -> None:
        op = AxiomaticChoiceOperator(strategy=SelectionStrategy.RANDOM_ADMISSIBLE, seed=42)
        assert op.select(candidates, force=True) is not None

    def test_ensemble_returns_valid(self, candidates) -> None:
        op = AxiomaticChoiceOperator(strategy=SelectionStrategy.ENSEMBLE)
        assert op.select(candidates, force=True) is not None

    def test_all_strategies_return_valid(self, candidates) -> None:
        for strat in SelectionStrategy:
            op = AxiomaticChoiceOperator(strategy=strat, seed=42)
            selected = op.select(candidates, force=True)
            assert selected is not None, f"Strategy {strat} returned None"


# ── Axiom validation ─────────────────────────────────────────────────


class TestAxiomValidation:
    def test_all_satisfied(self, candidates) -> None:
        op = AxiomaticChoiceOperator()
        selected = op.select(candidates, force=True)
        result = op.validate_axioms(selected, candidates)
        assert result["A1_admissibility"]
        assert result["A2_ccp_closure"]
        assert result["A3_non_derivability"]
        assert result["A5_stabilization"]

    def test_a4_with_prev_state(self, candidates) -> None:
        prev = compute_gnc_state(dict.fromkeys(MODULATORS, 0.5))
        op = AxiomaticChoiceOperator()
        selected = op.select(candidates, prev_state=prev, force=True)
        result = op.validate_axioms(selected, candidates, prev_state=prev)
        assert result["A4_phase_induction"]


# ── History ──────────────────────────────────────────────────────────


class TestHistory:
    def test_records_activations(self, candidates) -> None:
        op = AxiomaticChoiceOperator()
        op.select(candidates, force=True)
        op.select(candidates, force=True)
        assert len(op.history) == 2

    def test_critical_severity_uses_ensemble(self, candidates) -> None:
        op = AxiomaticChoiceOperator(strategy=SelectionStrategy.RANDOM_ADMISSIBLE)
        # 6 conditions -> severity=6/7=0.86 -> ensemble forced
        op.select(
            candidates,
            prev_state=candidates[0],
            gradient_norm=0.001,
            j_values=[0.50, 0.51],
            ccp_D_f=1.2,
            ccp_R=0.2,
            ci_score=0.9,
        )
        if op.history:
            assert op.history[-1].strategy == "ensemble"

    def test_summary_after_activation(self, candidates) -> None:
        op = AxiomaticChoiceOperator()
        op.select(candidates, force=True)
        s = op.summary()
        assert "A_C history" in s
        assert "activations" in s
