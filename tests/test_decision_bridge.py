"""Tests for core.decision_bridge — unified analytical convergence."""

from __future__ import annotations

import numpy as np
import pytest

from core.constants import SENSOR_GAMMA_MAX_ABS, SENSOR_PHI_MAX_ABS
from core.decision_bridge import (
    DecisionBridge,
    DecisionSnapshot,
    OnlinePredictor,
    PIController,
    SanitizationReport,
    SensorGate,
)


def _make_healthy_data(n: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Generate phi_history and gamma_history for a healthy system."""
    rng = np.random.default_rng(42)
    phi = rng.normal(0, 0.1, size=(n, 4))
    gamma = 1.0 + rng.normal(0, 0.02, size=n)
    return phi, gamma


def _make_dead_data(n: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Constant state → dead equilibrium."""
    phi = np.ones((n, 4)) * 0.5
    gamma = np.ones(n) * 1.0
    return phi, gamma


# ═══════════════════════════════════════════════════════════════════════
# Existing behavioural tests — kept to guard backward compatibility.
# ═══════════════════════════════════════════════════════════════════════


class TestConstruction:
    def test_default_bridge(self) -> None:
        bridge = DecisionBridge()
        assert bridge._oeb_gain == pytest.approx(0.05)

    def test_reset(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data()
        bridge.evaluate(
            tick=1,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        bridge.reset()
        assert bridge._oeb_gain == pytest.approx(0.05)
        assert bridge._oeb_energy == pytest.approx(1.0)


class TestEvaluateHealthy:
    def test_returns_snapshot(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data()
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.02,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert isinstance(snap, DecisionSnapshot)
        assert snap.tick == 20

    def test_healthy_system_optimal(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(30)
        snap = bridge.evaluate(
            tick=30,
            gamma_mean=1.01,
            gamma_std=0.02,
            spectral_radius=0.85,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.system_health == "OPTIMAL"
        assert snap.hallucination_risk == "low"
        assert snap.confidence > 0.5

    def test_operating_regime_detected(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.operating_regime in ("frozen", "critical", "chaotic")


class TestEvaluateDead:
    def test_dead_system(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_dead_data()
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.0,
            spectral_radius=0.5,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.gradient_diagnosis == "dead_equilibrium"
        assert snap.system_health == "DEAD"

    def test_dead_has_zero_alive_frac(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_dead_data()
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.0,
            spectral_radius=0.5,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.alive_frac < 0.1


class TestDegradation:
    def test_high_halluc_risk_degrades(self) -> None:
        bridge = DecisionBridge()
        gamma = np.linspace(1.0, 0.5, 20)
        phi = np.random.default_rng(0).normal(size=(20, 4))
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=0.6,
            gamma_std=0.2,
            spectral_radius=1.3,
            phase="DIVERGING",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.hallucination_risk in ("moderate", "high")
        assert snap.system_health in ("DEGRADED", "CRITICAL")


class TestOEBDynamics:
    def test_oeb_gain_increases_under_risk(self) -> None:
        bridge = DecisionBridge()
        initial_gain = bridge._oeb_gain
        gamma = np.linspace(1.0, 0.3, 20)
        phi = np.random.default_rng(0).normal(size=(20, 4))
        bridge.evaluate(
            tick=20,
            gamma_mean=0.4,
            gamma_std=0.3,
            spectral_radius=1.5,
            phase="DIVERGING",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert bridge._oeb_gain > initial_gain

    def test_oeb_energy_depletes(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        for t in range(50):
            bridge.evaluate(
                tick=t,
                gamma_mean=1.0,
                gamma_std=0.02,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )
        assert bridge._oeb_energy < 1.0


class TestConfidence:
    def test_low_confidence_on_short_history(self) -> None:
        bridge = DecisionBridge()
        phi = np.random.default_rng(0).normal(size=(2, 4))
        gamma = np.array([1.0, 1.01])
        snap = bridge.evaluate(
            tick=2,
            gamma_mean=1.0,
            gamma_std=0.01,
            spectral_radius=0.9,
            phase="INITIALIZING",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.confidence < 0.5

    def test_full_confidence_on_long_history(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(30)
        snap = bridge.evaluate(
            tick=30,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.confidence >= 1.0


class TestFDT:
    def test_fdt_not_available_on_short_history(self) -> None:
        bridge = DecisionBridge()
        phi = np.random.default_rng(0).normal(size=(5, 4))
        gamma = np.array([1.0, 1.01, 1.02, 1.01, 1.0])
        snap = bridge.evaluate(
            tick=5,
            gamma_mean=1.0,
            gamma_std=0.01,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.gamma_fdt_available is False


class TestSnapshotImmutability:
    def test_frozen(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data()
        snap = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        with pytest.raises(AttributeError):
            snap.tick = 999  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════
# New tests — ingress gate, predictor, PI controller, idempotence.
# ═══════════════════════════════════════════════════════════════════════


class TestSensorGateValidate:
    def test_rejects_non_finite_phi(self) -> None:
        gate = SensorGate()
        phi = np.array([[0.0, 1.0], [np.nan, 0.0]])
        gamma = np.array([1.0, 1.1])
        with pytest.raises(ValueError, match="non-finite"):
            gate.validate(phi, gamma)

    def test_rejects_non_finite_gamma(self) -> None:
        gate = SensorGate()
        phi = np.zeros((2, 2))
        gamma = np.array([1.0, np.inf])
        with pytest.raises(ValueError, match="non-finite"):
            gate.validate(phi, gamma)

    def test_rejects_shape_mismatch(self) -> None:
        gate = SensorGate()
        phi = np.zeros((3, 2))
        gamma = np.array([1.0, 1.1])
        with pytest.raises(ValueError, match="length mismatch"):
            gate.validate(phi, gamma)

    def test_rejects_wrong_ndim(self) -> None:
        gate = SensorGate()
        phi = np.zeros(6)  # 1-D, should be 2-D
        gamma = np.array([1.0, 1.1])
        with pytest.raises(ValueError, match="phi_history must be 2-D"):
            gate.validate(phi, gamma)

    def test_rejects_empty(self) -> None:
        gate = SensorGate()
        phi = np.zeros((0, 2))
        gamma = np.zeros(0)
        with pytest.raises(ValueError, match="non-empty"):
            gate.validate(phi, gamma)

    def test_validate_does_not_mutate_input(self) -> None:
        gate = SensorGate()
        phi = np.array([[0.0, 100.0], [0.0, 0.0]])  # 100 is absurd but finite
        gamma = np.array([1.0, 500.0])  # 500 is absurd but finite
        phi_copy = phi.copy()
        gamma_copy = gamma.copy()
        gate.validate(phi, gamma)  # must not raise — values are finite
        np.testing.assert_array_equal(phi, phi_copy)
        np.testing.assert_array_equal(gamma, gamma_copy)


class TestSensorGateSanitize:
    def test_in_range_passes_through(self) -> None:
        gate = SensorGate()
        phi, gamma = _make_healthy_data(10)
        phi_out, gamma_out, report = gate.sanitize(phi, gamma)
        np.testing.assert_array_equal(phi_out, phi)
        np.testing.assert_array_equal(gamma_out, gamma)
        assert report.phi_n_clipped == 0
        assert report.gamma_n_clipped == 0
        assert report.any_clipped is False

    def test_clips_and_reports(self) -> None:
        gate = SensorGate()
        phi = np.array([[0.0, 0.0], [2 * SENSOR_PHI_MAX_ABS, 0.0], [0.0, 0.0], [0.0, 0.0]])
        gamma = np.array([1.0, 2 * SENSOR_GAMMA_MAX_ABS, 1.0, 1.0])
        phi_out, gamma_out, report = gate.sanitize(phi, gamma)
        assert np.all(np.abs(phi_out) <= SENSOR_PHI_MAX_ABS + 1e-12)
        assert np.all(np.abs(gamma_out) <= SENSOR_GAMMA_MAX_ABS + 1e-12)
        assert report.phi_n_clipped == 1
        assert report.gamma_n_clipped == 1
        assert report.phi_max_abs_deviation > 0
        assert report.gamma_max_abs_deviation > 0
        assert report.any_clipped is True

    def test_sanitize_is_idempotent(self) -> None:
        gate = SensorGate()
        phi = np.array([[0.0, 0.0], [10 * SENSOR_PHI_MAX_ABS, 0.0], [0.0, 0.0], [0.0, 0.0]])
        gamma = np.array([1.0, 10 * SENSOR_GAMMA_MAX_ABS, 1.0, 1.0])
        phi1, gamma1, report1 = gate.sanitize(phi, gamma)
        phi2, gamma2, report2 = gate.sanitize(phi1, gamma1)
        np.testing.assert_array_equal(phi1, phi2)
        np.testing.assert_array_equal(gamma1, gamma2)
        assert report1.any_clipped is True
        assert report2.any_clipped is False  # already clean

    def test_sanitize_still_rejects_non_finite(self) -> None:
        gate = SensorGate()
        phi = np.array([[0.0, np.nan]])
        gamma = np.array([1.0])
        with pytest.raises(ValueError, match="non-finite"):
            gate.sanitize(phi, gamma)

    def test_sanitization_report_is_frozen(self) -> None:
        report = SanitizationReport(
            phi_n_clipped=0,
            gamma_n_clipped=0,
            phi_max_abs_deviation=0.0,
            gamma_max_abs_deviation=0.0,
        )
        with pytest.raises(AttributeError):
            report.phi_n_clipped = 5  # type: ignore[misc]


class TestOnlinePredictor:
    def test_first_observation_is_nan(self) -> None:
        pred = OnlinePredictor()
        residual = pred.observe(0.5)
        assert np.isnan(residual)

    def test_constant_signal_zero_residual_after_warmup(self) -> None:
        pred = OnlinePredictor()
        # Warm up on a constant series.
        for _ in range(8):
            pred.observe(0.7)
        residual = pred.observe(0.7)
        assert abs(residual) < 1e-10

    def test_residual_bounded_and_finite_on_stochastic_ar1(self) -> None:
        """Predictor stays numerically stable under a long AR(1) stream.

        This is the smoke-test for production use: a well-behaved input
        must never produce NaN / Inf / unbounded residuals.
        """
        rng = np.random.default_rng(0)
        phi_true = 0.5
        n = 500
        x = np.zeros(n, dtype=np.float64)
        for t in range(1, n):
            x[t] = 0.5 + phi_true * (x[t - 1] - 0.5) + rng.normal(0, 0.05)
        x = np.clip(x, 0.0, 1.0)

        pred = OnlinePredictor()
        residuals: list[float] = []
        for v in x:
            r = pred.observe(float(v))
            if np.isfinite(r):
                residuals.append(r)

        assert len(residuals) > 450  # vast majority of samples produced a residual
        arr = np.asarray(residuals)
        assert np.all(np.isfinite(arr))
        # Residuals cannot exceed the support of the clipped signal [0, 1].
        assert float(np.max(np.abs(arr))) <= 1.0

    def test_first_difference_is_not_prediction_error(self) -> None:
        """Witness that residual ≠ first-difference on a non-trivial signal.

        The two quantities coincide only for a degenerate (constant) input;
        on any real signal they differ. This rejects the patch's earlier
        ``prediction_error := |S_t − S_{t−1}|`` semantics.
        """
        rng = np.random.default_rng(1)
        x = np.clip(0.5 + 0.1 * rng.standard_normal(60), 0.0, 1.0)

        pred = OnlinePredictor()
        residuals: list[float] = []
        for v in x:
            r = pred.observe(float(v))
            if np.isfinite(r):
                residuals.append(r)
        first_diff_tail = np.diff(x)[-len(residuals) :]

        # The two sequences are genuinely different arrays of numbers.
        assert not np.allclose(np.asarray(residuals), first_diff_tail, atol=1e-6)

    def test_rejects_non_finite_observation(self) -> None:
        pred = OnlinePredictor()
        with pytest.raises(ValueError, match="non-finite"):
            pred.observe(float("nan"))

    def test_reset_clears_state(self) -> None:
        pred = OnlinePredictor()
        for _ in range(5):
            pred.observe(0.5)
        assert pred.pending_forecast is not None
        pred.reset()
        assert pred.pending_forecast is None
        assert np.isnan(pred.observe(0.5))


class TestPIController:
    def test_gain_bounded_under_large_positive_error(self) -> None:
        pi = PIController()
        for _ in range(1000):
            pi.step(1e6)
        assert pi.gain <= 1.0 + 1e-12

    def test_gain_bounded_under_large_negative_error(self) -> None:
        pi = PIController()
        for _ in range(1000):
            pi.step(-1e6)
        assert pi.gain >= 0.01 - 1e-12

    def test_integral_anti_windup(self) -> None:
        pi = PIController(integral_sat=5.0)
        for _ in range(1000):
            pi.step(1.0)
        assert abs(pi.integral) <= 5.0 + 1e-12

    def test_deterministic(self) -> None:
        a = PIController()
        b = PIController()
        errors = [0.1, -0.05, 0.2, 0.0, -0.3, 0.4]
        for e in errors:
            a.step(e)
            b.step(e)
        assert a.gain == b.gain
        assert a.integral == b.integral

    def test_zero_error_sequence_is_stationary(self) -> None:
        pi = PIController()
        g0 = pi.gain
        for _ in range(100):
            pi.step(0.0)
        assert pi.gain == pytest.approx(g0)
        assert pi.integral == pytest.approx(0.0)

    def test_rejects_non_finite_error(self) -> None:
        pi = PIController()
        with pytest.raises(ValueError, match="finite"):
            pi.step(float("inf"))

    def test_construction_rejects_bad_bounds(self) -> None:
        with pytest.raises(ValueError):
            PIController(gain_min=0.5, gain_max=0.2)  # init inside but bounds inverted

    def test_reset(self) -> None:
        pi = PIController()
        for _ in range(10):
            pi.step(0.5)
        pi.reset()
        assert pi.gain == pytest.approx(0.05)
        assert pi.integral == pytest.approx(0.0)


class TestBridgeIngress:
    def test_evaluate_raises_on_non_finite_by_default(self) -> None:
        bridge = DecisionBridge()
        phi = np.array([[0.0, 1.0], [np.nan, 0.0]])
        gamma = np.array([1.0, 1.1])
        with pytest.raises(ValueError, match="non-finite"):
            bridge.evaluate(
                tick=2,
                gamma_mean=1.05,
                gamma_std=0.02,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )

    def test_evaluate_default_path_leaves_report_none(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(12)
        snap = bridge.evaluate(
            tick=12,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap.sanitization_report is None

    def test_evaluate_sanitize_populates_report(self) -> None:
        bridge = DecisionBridge()
        phi = np.zeros((8, 4))
        phi[3, 2] = 10 * SENSOR_PHI_MAX_ABS
        gamma = np.ones(8)
        gamma[5] = 10 * SENSOR_GAMMA_MAX_ABS
        snap = bridge.evaluate(
            tick=8,
            gamma_mean=1.0,
            gamma_std=0.02,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
            sanitize_inputs=True,
        )
        assert snap.sanitization_report is not None
        assert snap.sanitization_report.phi_n_clipped == 1
        assert snap.sanitization_report.gamma_n_clipped == 1


class TestBridgeIdempotence:
    def test_same_tick_returns_identical_snapshot(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        a = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        b = bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert a is b  # memoized object, not a copy

    def test_same_tick_does_not_advance_controller(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        gain_after_first = bridge._oeb_gain
        energy_after_first = bridge._oeb_energy
        for _ in range(5):
            bridge.evaluate(
                tick=20,
                gamma_mean=1.0,
                gamma_std=0.03,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )
        assert bridge._oeb_gain == gain_after_first
        assert bridge._oeb_energy == energy_after_first

    def test_memoised_tick_still_validates_fresh_input(self) -> None:
        """Fail-closed ingress must run even when the snapshot is cached.

        Regression: the memoisation check originally short-circuited
        before ``SensorGate.validate``, so a second caller could pass
        non-finite input for an already-evaluated tick and silently
        receive the cached good snapshot — masking real corruption.
        """
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        bridge.evaluate(
            tick=42,
            gamma_mean=1.0,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        corrupt = phi.copy()
        corrupt[0, 0] = float("nan")
        with pytest.raises(ValueError, match="non-finite"):
            bridge.evaluate(
                tick=42,
                gamma_mean=1.0,
                gamma_std=0.03,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=corrupt,
                gamma_history=gamma,
            )

    def test_new_tick_advances_state(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        bridge.evaluate(
            tick=20,
            gamma_mean=1.0,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        energy_after_first = bridge._oeb_energy
        bridge.evaluate(
            tick=21,
            gamma_mean=1.0,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert bridge._oeb_energy < energy_after_first


class TestBridgePredictorIntegration:
    def test_prediction_warms_up(self) -> None:
        bridge = DecisionBridge()
        phi, gamma = _make_healthy_data(20)
        # First call → predictor still below the min-samples floor → NaN.
        snap1 = bridge.evaluate(
            tick=1,
            gamma_mean=1.0,
            gamma_std=0.03,
            spectral_radius=0.9,
            phase="METASTABLE",
            phi_history=phi,
            gamma_history=gamma,
        )
        assert snap1.prediction_available is False
        assert np.isnan(snap1.prediction_residual)
        # Advance past the predictor warm-up floor; residual becomes finite.
        last = snap1
        for t in range(2, 8):
            last = bridge.evaluate(
                tick=t,
                gamma_mean=1.0,
                gamma_std=0.03,
                spectral_radius=0.9,
                phase="METASTABLE",
                phi_history=phi,
                gamma_history=gamma,
            )
        assert last.prediction_available is True
        assert np.isfinite(last.prediction_residual)
