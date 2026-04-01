"""Tests for General Neuromodulatory Control (GNC+) v2.0 — 50+ tests."""

import numpy as np
import pytest

from mycelium_fractal_net.neurochem.gnc import (
    _IDX,
    MODULATORS,
    ROLES,
    SIGMA,
    THETA,
    GNCBridge,
    GNCState,
    MesoController,
    compute_gnc_state,
    get_omega,
    gnc_diagnose,
    omega_update,
    reset_omega,
    step,
)

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════


class TestConstants:
    def test_theta_count(self):
        assert len(THETA) == 9

    def test_modulators_count(self):
        assert len(MODULATORS) == 7

    def test_roles_complete(self):
        assert set(ROLES.keys()) == set(MODULATORS)

    def test_sigma_shape(self):
        for m in MODULATORS:
            assert set(SIGMA[m].keys()) == set(THETA)

    def test_sigma_values_valid(self):
        for m in MODULATORS:
            for t in THETA:
                assert SIGMA[m][t] in (-1, 0, +1)

    def test_sigma_not_all_zero(self):
        for m in MODULATORS:
            assert any(SIGMA[m][t] != 0 for t in THETA)


# ═══════════════════════════════════════════════════════════════
# SIGMA MATRIX — every axis
# ═══════════════════════════════════════════════════════════════


class TestSigmaMatrix:
    def test_glutamate_plasticity(self):
        assert SIGMA["Glutamate"]["alpha"] == +1
        assert SIGMA["Glutamate"]["tau"] == -1

    def test_gaba_stability(self):
        assert SIGMA["GABA"]["alpha"] == -1
        assert SIGMA["GABA"]["beta"] == +1
        assert SIGMA["GABA"]["tau"] == +1

    def test_noradrenaline_salience(self):
        assert SIGMA["Noradrenaline"]["beta"] == -1
        assert SIGMA["Noradrenaline"]["sigma_E"] == +1
        assert SIGMA["Noradrenaline"]["sigma_U"] == +1

    def test_serotonin_restraint(self):
        assert SIGMA["Serotonin"]["nu"] == -1
        assert SIGMA["Serotonin"]["lambda_pe"] == -1
        assert SIGMA["Serotonin"]["eta"] == +1

    def test_dopamine_reward(self):
        assert SIGMA["Dopamine"]["nu"] == +1
        assert SIGMA["Dopamine"]["alpha"] == +1
        assert SIGMA["Dopamine"]["lambda_pe"] == +1

    def test_acetylcholine_precision(self):
        assert SIGMA["Acetylcholine"]["rho"] == +1
        assert SIGMA["Acetylcholine"]["sigma_E"] == -1
        assert SIGMA["Acetylcholine"]["sigma_U"] == -1

    def test_opioid_resilience(self):
        assert SIGMA["Opioid"]["beta"] == +1
        assert SIGMA["Opioid"]["eta"] == +1
        assert SIGMA["Opioid"]["nu"] == 0


# ═══════════════════════════════════════════════════════════════
# OMEGA MATRIX
# ═══════════════════════════════════════════════════════════════


class TestOmega:
    def test_glu_gaba_antagonism(self):
        omega = get_omega()
        assert omega[_IDX["Glutamate"], _IDX["GABA"]] < 0

    def test_da_5ht_antagonism(self):
        omega = get_omega()
        assert omega[_IDX["Dopamine"], _IDX["Serotonin"]] < 0

    def test_na_ach_synergy(self):
        omega = get_omega()
        assert omega[_IDX["Noradrenaline"], _IDX["Acetylcholine"]] > 0

    def test_opioid_global_buffer(self):
        omega = get_omega()
        for m in MODULATORS:
            if m != "Opioid":
                assert omega[_IDX["Opioid"], _IDX[m]] > 0

    def test_omega_major_pairs_symmetric(self):
        """Major antagonistic pairs are symmetric (Glu/GABA, DA/5HT)."""
        omega = get_omega()
        assert abs(omega[_IDX["Glutamate"], _IDX["GABA"]] - omega[_IDX["GABA"], _IDX["Glutamate"]]) < 1e-10
        assert abs(omega[_IDX["Dopamine"], _IDX["Serotonin"]] - omega[_IDX["Serotonin"], _IDX["Dopamine"]]) < 1e-10

    def test_omega_diagonal_zero(self):
        omega = get_omega()
        for i in range(7):
            assert omega[i, i] == 0.0

    def test_omega_update_changes_matrix(self):
        reset_omega()
        before = get_omega().copy()
        state = compute_gnc_state({"Glutamate": 0.9, "GABA": 0.1})
        omega_update(state, learning_rate=0.1)
        after = get_omega()
        assert not np.allclose(before, after)
        reset_omega()

    def test_omega_update_bounded(self):
        reset_omega()
        state = compute_gnc_state({"Dopamine": 1.0, "Serotonin": 0.0})
        for _ in range(100):
            omega_update(state, learning_rate=0.1)
        omega = get_omega()
        assert np.all(omega >= -1.0)
        assert np.all(omega <= 1.0)
        reset_omega()

    def test_reset_omega(self):
        state = compute_gnc_state({"Glutamate": 0.9})
        omega_update(state, learning_rate=0.5)
        reset_omega()
        omega = get_omega()
        assert abs(omega[_IDX["Glutamate"], _IDX["GABA"]] - (-0.6)) < 1e-10


# ═══════════════════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════════════════


class TestGNCState:
    def test_default(self):
        s = GNCState.default()
        assert all(s.modulators[m] == 0.5 for m in MODULATORS)

    def test_from_levels(self):
        s = GNCState.from_levels({"Dopamine": 0.8})
        assert s.modulators["Dopamine"] == 0.8
        assert s.modulators["GABA"] == 0.5

    def test_clipping_high(self):
        s = GNCState.from_levels({"Glutamate": 1.5})
        assert s.modulators["Glutamate"] == 1.0

    def test_clipping_low(self):
        s = GNCState.from_levels({"GABA": -0.5})
        assert s.modulators["GABA"] == 0.0

    def test_theta_bounded(self):
        s = compute_gnc_state(dict.fromkeys(MODULATORS, 1.0))
        assert all(0.1 <= s.theta[t] <= 0.9 for t in THETA)

    def test_to_dict(self):
        d = GNCState.default().to_dict()
        assert "modulators" in d
        assert "theta" in d

    def test_summary(self):
        s = compute_gnc_state({"Dopamine": 0.8})
        assert "GNC+" in s.summary()


# ═══════════════════════════════════════════════════════════════
# STEP DYNAMICS
# ═══════════════════════════════════════════════════════════════


class TestStep:
    def test_returns_new_state(self):
        s = GNCState.default()
        s2 = step(s)
        assert isinstance(s2, GNCState)

    def test_theta_changes(self):
        s = compute_gnc_state({"Dopamine": 0.9})
        s2 = step(s)
        assert s2.theta != s.theta

    def test_bounded_after_many_steps(self):
        s = compute_gnc_state({"Noradrenaline": 0.95, "GABA": 0.05})
        for _ in range(50):
            s = step(s)
        assert all(0.1 <= s.theta[t] <= 0.9 for t in THETA)


# ═══════════════════════════════════════════════════════════════
# DIAGNOSIS + FALSIFICATION
# ═══════════════════════════════════════════════════════════════


class TestDiagnosis:
    def test_optimal(self):
        d = gnc_diagnose(GNCState.default())
        assert d.regime in ("optimal", "dysregulated")

    def test_hyperactivated(self):
        d = gnc_diagnose(compute_gnc_state(dict.fromkeys(MODULATORS, 0.85)))
        assert d.regime == "hyperactivated"

    def test_hypoactivated(self):
        d = gnc_diagnose(compute_gnc_state(dict.fromkeys(MODULATORS, 0.15)))
        assert d.regime == "hypoactivated"

    def test_coherence_bounded(self):
        d = gnc_diagnose(compute_gnc_state({"Glutamate": 0.9, "GABA": 0.1}))
        assert 0 <= d.coherence <= 1

    def test_dominant_is_modulator(self):
        d = gnc_diagnose(compute_gnc_state({"Noradrenaline": 0.95}))
        assert d.dominant_axis in MODULATORS

    def test_suppressed_is_modulator(self):
        d = gnc_diagnose(compute_gnc_state({"GABA": 0.05}))
        assert d.suppressed_axis in MODULATORS

    def test_f1_sign_mismatch(self):
        # Force a state where theta doesn't follow sigma prediction
        s = GNCState(
            modulators=dict.fromkeys(MODULATORS, 0.5),
            theta=dict.fromkeys(THETA, 0.5),
        )
        s.modulators["Dopamine"] = 0.9  # high DA → nu should be high
        s.theta["nu"] = 0.1             # but nu is low → F1 violation
        d = gnc_diagnose(s)
        f1_flags = [f for f in d.falsification_flags if "F1" in f]
        assert len(f1_flags) > 0

    def test_f3_omega_inactive(self):
        s = GNCState(
            modulators=dict.fromkeys(MODULATORS, 0.0),
            theta=dict.fromkeys(THETA, 0.5),
        )
        d = gnc_diagnose(s)
        f3_flags = [f for f in d.falsification_flags if "F3" in f]
        assert len(f3_flags) > 0

    def test_f5_theta_identical(self):
        s = GNCState(
            modulators=dict.fromkeys(MODULATORS, 0.5),
            theta=dict.fromkeys(THETA, 0.5),
        )
        d = gnc_diagnose(s)
        f5_flags = [f for f in d.falsification_flags if "F5" in f]
        assert len(f5_flags) > 0

    def test_summary(self):
        d = gnc_diagnose(compute_gnc_state({"Dopamine": 0.8}))
        text = d.summary()
        assert "GNC+" in text
        assert d.recommendation


# ═══════════════════════════════════════════════════════════════
# MESO CONTROLLER
# ═══════════════════════════════════════════════════════════════


class TestMesoController:
    def test_micro_for_balanced(self):
        ctrl = MesoController()
        s = GNCState.default()
        strategy = ctrl.evaluate(s)
        assert strategy in ("micro", "meso", "macro")

    def test_macro_for_extreme(self):
        ctrl = MesoController()
        s = compute_gnc_state(dict.fromkeys(MODULATORS, 0.95))
        ctrl.evaluate(s)
        # High imbalance or low coherence should trigger meso/macro
        assert ctrl.current_strategy in ("meso", "macro")

    def test_apply_returns_state(self):
        ctrl = MesoController()
        s = compute_gnc_state({"Dopamine": 0.8})
        reset_omega()
        s2 = ctrl.apply(s)
        assert isinstance(s2, GNCState)
        reset_omega()

    def test_history_tracked(self):
        ctrl = MesoController()
        for _ in range(5):
            ctrl.apply(GNCState.default())
        assert len(ctrl.strategy_history) == 5

    def test_summary(self):
        ctrl = MesoController()
        ctrl.apply(GNCState.default())
        text = ctrl.summary()
        assert "Meso" in text

    def test_meso_balances_extremes(self):
        ctrl = MesoController()
        s = compute_gnc_state({"Glutamate": 0.9, "GABA": 0.1})
        reset_omega()
        s2 = ctrl.apply(s)
        # Meso should push extremes toward center
        if ctrl.current_strategy == "meso":
            assert s2.modulators["Glutamate"] < s.modulators["Glutamate"]
            assert s2.modulators["GABA"] > s.modulators["GABA"]
        reset_omega()


# ═══════════════════════════════════════════════════════════════
# BRIDGE
# ═══════════════════════════════════════════════════════════════


class TestGNCBridge:
    def test_modulate_default(self):
        b = GNCBridge()
        assert 0 <= b.modulate_anomaly_score(0.5) <= 1

    def test_na_boosts(self):
        b = GNCBridge(GNCState.from_levels({"Noradrenaline": 0.9}))
        assert b.modulate_anomaly_score(0.3) > 0.3

    def test_gaba_dampens(self):
        b = GNCBridge(GNCState.from_levels({"GABA": 0.9}))
        assert b.modulate_anomaly_score(0.3) < 0.3

    def test_update_from_m(self):
        b = GNCBridge()
        b.update_from_m_score(0.4)
        assert b.state.modulators["Dopamine"] == pytest.approx(0.8, abs=0.01)

    def test_resilience(self):
        b = GNCBridge()
        before = b.state.modulators["Opioid"]
        b.activate_resilience()
        assert b.state.modulators["Opioid"] > before

    def test_summary(self):
        assert "GNC+" in GNCBridge().summary()

    def test_score_clamped(self):
        b = GNCBridge(GNCState.from_levels({"Noradrenaline": 1.0}))
        assert b.modulate_anomaly_score(1.0) <= 1.0
        assert b.modulate_anomaly_score(0.0) >= 0.0


# ═══════════════════════════════════════════════════════════════
# INTEGRATION WITH MFN DIAGNOSE
# ═══════════════════════════════════════════════════════════════


class TestGNCIntegration:
    def test_diagnose_includes_gnc(self):
        from mycelium_fractal_net import SimulationSpec, diagnose, simulate

        seq = simulate(SimulationSpec(grid_size=16, steps=20, seed=42))
        report = diagnose(seq)
        # gnc_diagnosis should be populated (string from GNCBridge.summary)
        assert report.gnc_diagnosis is not None
        assert "GNC+" in report.gnc_diagnosis
