"""Tests for OmegaOrdinal — transfinite neuromodulatory hierarchy."""

from __future__ import annotations

import pytest

from mycelium_fractal_net.neurochem.gnc import MODULATORS, compute_gnc_state
from mycelium_fractal_net.neurochem.omega_ordinal import (
    OmegaInteraction,
    OrdinalRank,
    build_omega_ordinal,
    compute_ordinal_dynamics,
)

# ── OrdinalRank ──────────────────────────────────────────────────


def test_ordinal_rank_labels():
    assert OrdinalRank.OMEGA_0.label() == "ω"
    assert OrdinalRank.OMEGA_1.label() == "ω+1"
    assert OrdinalRank.OMEGA_2.label() == "ω+2"
    assert OrdinalRank.OMEGA_SQ.label() == "ω²"


def test_weight_multipliers_increasing():
    ranks = list(OrdinalRank)
    mults = [r.weight_multiplier() for r in ranks]
    assert all(mults[i] < mults[i + 1] for i in range(len(mults) - 1))


def test_omega_sq_multiplier_is_4():
    assert OrdinalRank.OMEGA_SQ.weight_multiplier() == 4.0


# ── OmegaInteraction ────────────────────────────────────────────


def test_effective_weight_higher_for_higher_rank():
    ix0 = OmegaInteraction("A", "B", OrdinalRank.OMEGA_0, 0.5)
    ix1 = OmegaInteraction("A", "B", OrdinalRank.OMEGA_SQ, 0.5)
    assert ix1.effective_weight > ix0.effective_weight


def test_effective_weight_is_weight_times_multiplier():
    ix = OmegaInteraction("A", "B", OrdinalRank.OMEGA_2, 0.3)
    assert ix.effective_weight == pytest.approx(0.3 * 2.0)


# ── build_omega_ordinal ─────────────────────────────────────────


def test_build_omega_ordinal_has_all_ranks():
    omega = build_omega_ordinal()
    ranks_present = {ix.rank for ix in omega.interactions}
    assert OrdinalRank.OMEGA_0 in ranks_present
    assert OrdinalRank.OMEGA_1 in ranks_present
    assert OrdinalRank.OMEGA_2 in ranks_present
    assert OrdinalRank.OMEGA_SQ in ranks_present


def test_to_matrix_shape():
    omega = build_omega_ordinal()
    M = omega.to_matrix()
    assert M.shape == (7, 7)


def test_to_matrix_not_all_zeros():
    omega = build_omega_ordinal()
    M = omega.to_matrix()
    assert M.any()


def test_all_interactions_have_refs():
    omega = build_omega_ordinal()
    assert all(ix.ref for ix in omega.interactions)


def test_all_interactions_have_labels():
    omega = build_omega_ordinal()
    assert all(ix.label for ix in omega.interactions)


def test_get_by_rank_filters_correctly():
    omega = build_omega_ordinal()
    sq = omega.get_by_rank(OrdinalRank.OMEGA_SQ)
    assert len(sq) >= 1
    assert all(ix.rank == OrdinalRank.OMEGA_SQ for ix in sq)


# ── compute_interaction_level ────────────────────────────────────


def test_healthy_state_low_ordinal_level():
    state = compute_gnc_state()
    omega = build_omega_ordinal()
    level = omega.compute_interaction_level(state)
    assert level in (OrdinalRank.OMEGA_0, OrdinalRank.OMEGA_1)


def test_pathological_state_high_ordinal_level():
    state = compute_gnc_state({
        "Glutamate": 0.95, "GABA": 0.05, "Noradrenaline": 0.95,
        "Serotonin": 0.05, "Dopamine": 0.95, "Acetylcholine": 0.05,
        "Opioid": 0.05,
    })
    omega = build_omega_ordinal()
    level = omega.compute_interaction_level(state)
    assert level.value >= OrdinalRank.OMEGA_1.value


def test_opioid_global_raises_to_omega_2():
    state = compute_gnc_state({
        "Opioid": 0.85,
        "Glutamate": 0.5, "GABA": 0.5, "Noradrenaline": 0.5,
        "Serotonin": 0.5, "Dopamine": 0.5, "Acetylcholine": 0.5,
    })
    omega = build_omega_ordinal()
    level = omega.compute_interaction_level(state)
    assert level.value >= OrdinalRank.OMEGA_2.value


# ── compute_ordinal_dynamics ─────────────────────────────────────


def test_compute_ordinal_dynamics_returns_all_fields():
    omega = build_omega_ordinal()
    result = compute_ordinal_dynamics(compute_gnc_state(), omega)
    assert "ordinal_level" in result
    assert "ordinal_label" in result
    assert "effective_matrix" in result
    assert "ac_required" in result
    assert "phase_transition_risk" in result
    assert "active_interactions" in result
    assert "omega_effect_norm" in result


def test_phase_risk_between_0_and_1():
    omega = build_omega_ordinal()
    result = compute_ordinal_dynamics(compute_gnc_state(), omega)
    assert 0.0 <= result["phase_transition_risk"] <= 1.0


def test_omega_effect_norm_positive():
    omega = build_omega_ordinal()
    result = compute_ordinal_dynamics(compute_gnc_state(), omega)
    assert result["omega_effect_norm"] >= 0


def test_omega_sq_triggers_ac_required():
    # Create a state with extreme imbalance to trigger ω²
    state = compute_gnc_state({
        m: 0.95 if i % 2 == 0 else 0.05
        for i, m in enumerate(MODULATORS)
    })
    omega = build_omega_ordinal()
    result = compute_ordinal_dynamics(state, omega)
    assert isinstance(result["ac_required"], bool)


def test_healthy_state_ac_not_required():
    result = compute_ordinal_dynamics(compute_gnc_state())
    assert result["ac_required"] is False


def test_default_omega_is_used_when_none():
    result = compute_ordinal_dynamics(compute_gnc_state(), None)
    assert result["effective_matrix"].shape == (7, 7)


def test_active_interactions_format():
    result = compute_ordinal_dynamics(compute_gnc_state())
    for item in result["active_interactions"]:
        assert len(item) == 3  # (source, target, rank_label)
        assert isinstance(item[0], str)
        assert isinstance(item[1], str)
        assert isinstance(item[2], str)


# ── summary ──────────────────────────────────────────────────────


def test_summary_contains_all_ranks():
    omega = build_omega_ordinal()
    s = omega.summary()
    assert "ω" in s
    assert "ω+1" in s
    assert "ω+2" in s
    assert "ω²" in s


def test_summary_contains_header():
    omega = build_omega_ordinal()
    s = omega.summary()
    assert "OmegaOrdinal" in s
    assert "Transfinite" in s
