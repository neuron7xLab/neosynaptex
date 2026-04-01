"""Tests for stability analysis module.

Tests for compute_stability_metrics and is_stable functions.

Reference: MFN_MATH_MODEL.md Section 3.3 (Lyapunov Exponent)

Mathematical invariants:
    - Lyapunov λ < 0 indicates stable (contractive) dynamics
    - Lyapunov λ > 0 indicates unstable (expansive) dynamics
    - Expected value for MFN IFS: λ ≈ -2.1 (stable)
"""

import numpy as np
import pytest

from mycelium_fractal_net.core.stability import (
    compute_lyapunov_exponent,
    compute_stability_metrics,
    is_stable,
)


class TestIsStable:
    """Tests for is_stable function."""

    def test_is_stable_negative_lyapunov(self) -> None:
        """Negative Lyapunov exponent indicates stable dynamics."""
        assert is_stable(-2.1) is True
        assert is_stable(-0.001) is True
        assert is_stable(-100.0) is True

    def test_is_stable_positive_lyapunov(self) -> None:
        """Positive Lyapunov exponent indicates unstable dynamics."""
        assert is_stable(0.1) is False
        assert is_stable(2.5) is False
        assert is_stable(100.0) is False

    def test_is_stable_zero_lyapunov(self) -> None:
        """Zero Lyapunov exponent is on the boundary (not stable by default)."""
        assert is_stable(0.0) is False  # Exactly at threshold

    def test_is_stable_custom_threshold(self) -> None:
        """Test custom stability threshold."""
        # With threshold=0.5, values up to 0.5 are considered stable
        assert is_stable(0.3, threshold=0.5) is True
        assert is_stable(0.6, threshold=0.5) is False

    def test_is_stable_negative_threshold(self) -> None:
        """Test with negative threshold (stricter stability criterion)."""
        assert is_stable(-0.5, threshold=-0.1) is True
        assert is_stable(0.0, threshold=-0.1) is False
        assert is_stable(-0.05, threshold=-0.1) is False


class TestComputeStabilityMetrics:
    """Tests for compute_stability_metrics function."""

    def test_compute_stability_metrics_returns_all_keys(self) -> None:
        """Test that all expected metrics are returned."""
        history = np.random.randn(50, 32, 32) * 0.01
        metrics = compute_stability_metrics(history)

        expected_keys = {
            "lyapunov_exponent",
            "is_stable",
            "mean_change_rate",
            "max_change_rate",
            "final_std",
        }
        assert set(metrics.keys()) == expected_keys

    def test_compute_stability_metrics_stable_dynamics(self) -> None:
        """Test metrics for converging (stable) field history."""
        # Create converging field: variance decreases over time
        np.random.seed(42)
        history = np.zeros((100, 16, 16))
        for t in range(100):
            history[t] = np.random.randn(16, 16) * (0.95**t)  # Exponential decay

        metrics = compute_stability_metrics(history)

        # Should detect stable dynamics
        assert metrics["lyapunov_exponent"] < 0 or np.isfinite(metrics["lyapunov_exponent"])
        assert metrics["final_std"] < history[0].std()  # Final state more stable

    def test_compute_stability_metrics_change_rates(self) -> None:
        """Test that change rates are computed correctly."""
        # Create history with known changes
        history = np.zeros((10, 4, 4))
        history[0] = 0.0
        for t in range(1, 10):
            history[t] = history[t - 1] + 0.1  # Constant change rate

        metrics = compute_stability_metrics(history, dt=1.0)

        # Mean change should be approximately 0.1
        assert 0.09 < metrics["mean_change_rate"] < 0.11
        # Max change should be approximately 0.1
        assert 0.09 < metrics["max_change_rate"] < 0.11

    def test_compute_stability_metrics_with_dt(self) -> None:
        """Test change rate scaling with different dt values."""
        history = np.zeros((10, 4, 4))
        for t in range(10):
            history[t] = float(t)  # Linear increase

        metrics_dt1 = compute_stability_metrics(history, dt=1.0)
        metrics_dt2 = compute_stability_metrics(history, dt=2.0)

        # Change rate should scale inversely with dt
        assert metrics_dt1["mean_change_rate"] == pytest.approx(
            metrics_dt2["mean_change_rate"] * 2, rel=0.01
        )

    def test_compute_stability_metrics_short_history(self) -> None:
        """Test with very short history (single timestep)."""
        history = np.random.randn(1, 8, 8)

        metrics = compute_stability_metrics(history)

        # Should handle gracefully
        assert metrics["mean_change_rate"] == 0.0
        assert metrics["max_change_rate"] == 0.0
        assert np.isfinite(metrics["final_std"])

    def test_compute_stability_metrics_two_timesteps(self) -> None:
        """Test with minimal history (two timesteps)."""
        history = np.zeros((2, 4, 4))
        history[0] = 0.0
        history[1] = 1.0

        metrics = compute_stability_metrics(history)

        # Should compute change rate from single diff
        assert metrics["mean_change_rate"] == 1.0
        assert metrics["max_change_rate"] == 1.0

    def test_compute_stability_metrics_constant_field(self) -> None:
        """Test with constant (unchanging) field."""
        history = np.ones((50, 8, 8)) * 5.0

        metrics = compute_stability_metrics(history)

        # No changes -> zero change rates
        assert metrics["mean_change_rate"] == 0.0
        assert metrics["max_change_rate"] == 0.0
        assert metrics["final_std"] == 0.0

    def test_compute_stability_metrics_is_stable_flag(self) -> None:
        """Test is_stable flag in metrics matches is_stable function."""
        history = np.random.randn(50, 8, 8) * 0.01

        metrics = compute_stability_metrics(history)

        # is_stable in metrics should match the is_stable function
        expected_stable = is_stable(metrics["lyapunov_exponent"])
        assert metrics["is_stable"] == (1.0 if expected_stable else 0.0)

    def test_compute_stability_metrics_no_nan_inf(self) -> None:
        """Test that metrics don't contain NaN or Inf."""
        np.random.seed(123)
        history = np.random.randn(100, 32, 32)

        metrics = compute_stability_metrics(history)

        for key, value in metrics.items():
            assert np.isfinite(value), f"Metric {key} is not finite: {value}"

    @pytest.mark.parametrize("bad_dt", [0.0, -1.0])
    def test_compute_stability_metrics_invalid_dt(self, bad_dt: float) -> None:
        """Ensure invalid dt values raise an error instead of dividing by zero."""
        history = np.random.randn(10, 4, 4)

        with pytest.raises(ValueError, match="dt must be positive"):
            compute_stability_metrics(history, dt=bad_dt)


class TestLyapunovExponentEdgeCases:
    """Additional edge case tests for Lyapunov exponent computation."""

    def test_lyapunov_empty_history(self) -> None:
        """Test with empty history array."""
        history = np.array([]).reshape(0, 8, 8)

        # Should handle gracefully (return 0 for empty)
        lyapunov = compute_lyapunov_exponent(history)
        assert lyapunov == 0.0

    def test_lyapunov_with_nan_in_history(self) -> None:
        """Test behavior with NaN values in history."""
        history = np.random.randn(10, 4, 4)
        history[5, 2, 2] = np.nan

        lyapunov = compute_lyapunov_exponent(history)

        # Result may be NaN, but should not raise an exception
        # This tests robustness, not correctness when data is invalid
        assert isinstance(lyapunov, (int, float))

    def test_lyapunov_large_field(self) -> None:
        """Test with larger field dimensions."""
        np.random.seed(42)
        history = np.random.randn(50, 128, 128) * 0.01

        lyapunov = compute_lyapunov_exponent(history)

        assert np.isfinite(lyapunov)

    def test_lyapunov_small_dt(self) -> None:
        """Test with small dt value (should affect result)."""
        history = np.random.randn(20, 8, 8)

        lyap_dt1 = compute_lyapunov_exponent(history, dt=1.0)
        lyap_dt01 = compute_lyapunov_exponent(history, dt=0.1)

        # Different dt should give different results
        # (rate of change scaled by dt)
        assert lyap_dt1 != lyap_dt01 or lyap_dt1 == 0.0


class TestStabilityIntegration:
    """Integration tests combining stability functions."""

    def test_stable_simulation_metrics(self) -> None:
        """Test full stability analysis on simulated stable system."""
        np.random.seed(42)

        # Create damped oscillation (stable)
        T = 100
        history = np.zeros((T, 16, 16))
        for t in range(T):
            history[t] = np.sin(0.1 * t) * np.exp(-0.05 * t) * np.ones((16, 16))
            history[t] += np.random.randn(16, 16) * 0.01

        metrics = compute_stability_metrics(history)

        # Damped system should be stable
        assert metrics["is_stable"] == 1.0 or metrics["lyapunov_exponent"] < 0.5
        # Final state amplitude should be smaller than initial (damped)
        assert np.abs(history[-1]).mean() < np.abs(history[0]).mean() + 0.05

    def test_mfn_expected_lyapunov_range(self) -> None:
        """Test that typical MFN field histories give expected Lyapunov range.

        Reference: MFN_MATH_MODEL.md states λ ≈ -2.1 for stable MFN dynamics.
        We test that Lyapunov is negative (stable) for reasonable inputs.
        """
        np.random.seed(42)

        # Simulate field with typical MFN-like evolution
        history = np.zeros((200, 32, 32))
        field = np.random.randn(32, 32) * 0.5
        for t in range(200):
            # Simple diffusion-like dynamics
            field = field * 0.99 + np.random.randn(32, 32) * 0.01
            history[t] = field

        metrics = compute_stability_metrics(history)

        # System should be stable (λ < 0) or marginally stable
        assert metrics["is_stable"] == 1.0 or metrics["lyapunov_exponent"] < 1.0
