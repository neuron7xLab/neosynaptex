"""Tests for Wolfram Bridge — computational irreducibility detection."""

from __future__ import annotations

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.wolfram_bridge import (
    compute_incompressibility,
    compute_prediction_residual,
    detect_computational_irreducibility,
)

# ── Incompressibility ────────────────────────────────────────────────


class TestIncompressibility:
    def test_constant_field_low(self) -> None:
        field = np.full((32, 32), 0.5)
        assert compute_incompressibility(field) < 0.15

    def test_random_field_high(self) -> None:
        rng = np.random.RandomState(42)
        field = rng.uniform(0, 1, (32, 32))
        assert compute_incompressibility(field) > 0.5

    def test_bounded_0_1(self) -> None:
        rng = np.random.RandomState(42)
        field = rng.uniform(-1, 1, (32, 32))
        K = compute_incompressibility(field)
        assert 0.0 <= K <= 1.0

    def test_structured_pattern_medium(self) -> None:
        x = np.linspace(0, 4 * np.pi, 32)
        X, Y = np.meshgrid(x, x)
        field = np.sin(X) * np.cos(Y)
        K = compute_incompressibility(field)
        assert 0.05 <= K <= 0.8


# ── Prediction residual ─────────────────────────────────────────────


class TestPredictionResidual:
    def test_constant_field_zero(self) -> None:
        field = np.full((16, 16), 0.5)
        assert compute_prediction_residual(field) < 0.01

    def test_random_field_nonzero(self) -> None:
        rng = np.random.RandomState(42)
        field = rng.uniform(-1, 1, (16, 16))
        assert compute_prediction_residual(field) > 0.0

    def test_with_history_converged_low(self) -> None:
        """Converged field with variance: last two frames nearly identical."""
        rng = np.random.RandomState(42)
        f1 = rng.uniform(0.4, 0.6, (16, 16))
        f2 = f1 + rng.normal(0, 0.01, (16, 16))
        f3 = f2 + rng.normal(0, 0.001, (16, 16))  # converging
        history = np.stack([f1, f2, f3])
        assert compute_prediction_residual(f3, history) < 0.5

    def test_with_history_divergent_high(self) -> None:
        """Divergent: last two frames very different → high residual."""
        rng = np.random.RandomState(42)
        f1 = rng.uniform(-1, 1, (16, 16))
        f2 = rng.uniform(-1, 1, (16, 16))
        f3 = rng.uniform(-1, 1, (16, 16))
        history = np.stack([f1, f2, f3])
        P = compute_prediction_residual(f3, history)
        assert P > 0.1


# ── CI detection ─────────────────────────────────────────────────────


class TestCIDetection:
    def test_healthy_mfn_not_irreducible(self) -> None:
        """Converged Turing pattern is computationally reducible."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
        ci = detect_computational_irreducibility(seq)
        assert isinstance(ci, dict)
        assert not ci["is_irreducible"]

    def test_noise_is_irreducible(self) -> None:
        """Pure noise is maximally irreducible."""
        from mycelium_fractal_net.types.field import FieldSequence

        rng = np.random.RandomState(42)
        noise = FieldSequence(field=rng.uniform(-0.1, 0.1, (32, 32)))
        ci = detect_computational_irreducibility(noise)
        assert ci["is_irreducible"]
        assert ci["pce_complexity_class"] == "3_chaotic"

    def test_flat_is_reducible(self) -> None:
        """Flat field is maximally reducible (Class 1)."""
        from mycelium_fractal_net.types.field import FieldSequence

        flat = FieldSequence(field=np.full((32, 32), -0.05))
        ci = detect_computational_irreducibility(flat)
        assert not ci["is_irreducible"]
        assert ci["pce_complexity_class"] == "1_fixed"

    def test_ci_score_bounded(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        ci = detect_computational_irreducibility(seq)
        assert 0.0 <= ci["ci_score"] <= 1.0

    def test_intrinsic_randomness_bounded(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        ci = detect_computational_irreducibility(seq)
        assert 0.0 <= ci["intrinsic_randomness"] <= 1.0

    def test_dict_has_all_keys(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        ci = detect_computational_irreducibility(seq)
        expected = {"ci_score", "is_irreducible", "incompressibility",
                    "lyapunov_indicator", "prediction_residual",
                    "pce_complexity_class", "intrinsic_randomness"}
        assert set(ci.keys()) == expected


# ── A_C integration ──────────────────────────────────────────────────


class TestCIActivation:
    def test_ci_triggers_activation(self) -> None:
        """High CI score should trigger A_C activation."""
        from mycelium_fractal_net.neurochem.axiomatic_choice import (
            ActivationCondition,
            check_activation_conditions,
        )
        from mycelium_fractal_net.neurochem.gnc import compute_gnc_state

        state = compute_gnc_state()
        result = check_activation_conditions(state, ci_score=0.8)
        assert result.should_activate
        assert ActivationCondition.COMPUTATIONAL_IRREDUCIBILITY in result.active_conditions

    def test_low_ci_no_trigger(self) -> None:
        from mycelium_fractal_net.neurochem.axiomatic_choice import check_activation_conditions
        from mycelium_fractal_net.neurochem.gnc import compute_gnc_state

        state = compute_gnc_state()
        result = check_activation_conditions(state, ci_score=0.3)
        # CI alone should not trigger (below threshold)
        assert not result.should_activate or "computational_irreducibility" not in [
            c.value for c in result.active_conditions
        ]

    def test_ci_combined_with_ccp(self) -> None:
        """CI + CCP violation should give higher severity."""
        from mycelium_fractal_net.neurochem.axiomatic_choice import check_activation_conditions
        from mycelium_fractal_net.neurochem.gnc import compute_gnc_state

        state = compute_gnc_state()
        r1 = check_activation_conditions(state, ci_score=0.8)
        r2 = check_activation_conditions(state, ci_score=0.8, ccp_D_f=1.2)
        assert r2.severity >= r1.severity


# ── Wolfram classification ───────────────────────────────────────────


class TestWolframClassification:
    def test_healthy_mfn_class_4_or_2(self) -> None:
        """Healthy MFN should be Class 4 (complex) or Class 2 (periodic)."""
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=60, seed=42))
        ci = detect_computational_irreducibility(seq)
        assert ci["pce_complexity_class"] in ("4_complex", "2_periodic")

    def test_classification_deterministic(self) -> None:
        seq = mfn.simulate(mfn.SimulationSpec(grid_size=16, steps=20, seed=42))
        ci1 = detect_computational_irreducibility(seq)
        ci2 = detect_computational_irreducibility(seq)
        assert ci1["pce_complexity_class"] == ci2["pce_complexity_class"]
        assert ci1["ci_score"] == ci2["ci_score"]
