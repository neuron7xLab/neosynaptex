"""Tests for STDP plasticity module.

Mathematical validation tests for Spike-Timing Dependent Plasticity.

Reference: MFN_MATH_MODEL.md (STDP section), Bi & Poo (1998)

Equations tested:
    Δw = A+ * exp(-Δt/τ+) if Δt > 0 (LTP)
    Δw = -A- * exp(Δt/τ-) if Δt < 0 (LTD)

Parameter constraints (biophysical):
    τ ∈ [5, 100] ms
    A ∈ [0.001, 0.1]
    A-/A+ > 1 for stability
"""

import math

import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net import (
    STDP_A_MINUS,
    STDP_A_PLUS,
    STDP_TAU_MINUS,
    STDP_TAU_PLUS,
)
from mycelium_fractal_net.model import STDPPlasticity


class TestSTDPParameterValidation:
    """Tests for STDP parameter validation against biophysical constraints."""

    def test_stdp_parameters_match_spec(self) -> None:
        """Verify STDP parameters match specification: tau±20ms, a±0.01/0.012."""
        stdp = STDPPlasticity()

        assert stdp.tau_plus == STDP_TAU_PLUS
        assert stdp.tau_minus == STDP_TAU_MINUS
        assert stdp.a_plus == STDP_A_PLUS
        assert stdp.a_minus == STDP_A_MINUS

        # Check actual values
        assert abs(stdp.tau_plus - 0.020) < 1e-6  # 20 ms
        assert abs(stdp.tau_minus - 0.020) < 1e-6  # 20 ms
        assert abs(stdp.a_plus - 0.01) < 1e-6
        assert abs(stdp.a_minus - 0.012) < 1e-6

    def test_stdp_parameters_in_biophysical_range(self) -> None:
        """Verify default parameters are within biophysical range [5, 100] ms."""
        stdp = STDPPlasticity()

        # Time constants in biophysical range
        assert 0.005 <= stdp.tau_plus <= 0.100
        assert 0.005 <= stdp.tau_minus <= 0.100

        # Amplitudes in stable range
        assert 0.001 <= stdp.a_plus <= 0.100
        assert 0.001 <= stdp.a_minus <= 0.100

    def test_stdp_asymmetry_ratio(self) -> None:
        """Verify A-/A+ > 1 for network stability (prevents runaway LTP)."""
        stdp = STDPPlasticity()
        ratio = stdp.a_minus / stdp.a_plus
        assert ratio > 1.0, f"A-/A+ = {ratio} should be > 1 for stability"

    def test_stdp_rejects_tau_below_min(self) -> None:
        """Verify rejection of time constants below biophysical minimum."""
        with pytest.raises(ValueError, match=r"\d+.*ms.*biophysical range"):
            STDPPlasticity(tau_plus=0.001)  # 1 ms < 5 ms minimum

    def test_stdp_rejects_tau_above_max(self) -> None:
        """Verify rejection of time constants above biophysical maximum."""
        with pytest.raises(ValueError, match=r"\d+.*ms.*biophysical range"):
            STDPPlasticity(tau_minus=0.200)  # 200 ms > 100 ms maximum

    def test_stdp_rejects_amplitude_below_min(self) -> None:
        """Verify rejection of amplitudes below stable minimum."""
        with pytest.raises(ValueError, match="stable range"):
            STDPPlasticity(a_plus=0.0001)  # 0.0001 < 0.001 minimum

    def test_stdp_rejects_amplitude_above_max(self) -> None:
        """Verify rejection of amplitudes above stable maximum."""
        with pytest.raises(ValueError, match="stable range"):
            STDPPlasticity(a_minus=0.5)  # 0.5 > 0.1 maximum


class TestSTDPMathematicalProperties:
    """Tests for STDP mathematical model correctness."""

    def test_stdp_ltp_when_pre_before_post(self) -> None:
        """Test Long-Term Potentiation when presynaptic spike precedes postsynaptic."""
        stdp = STDPPlasticity()

        # Pre spike at t=0, post spike at t=0.01 (10ms later)
        pre_times = torch.tensor([[0.0]])
        post_times = torch.tensor([[0.01]])
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # LTP should produce positive weight change
        assert delta_w.sum().item() > 0

    def test_stdp_ltd_when_post_before_pre(self) -> None:
        """Test Long-Term Depression when postsynaptic spike precedes presynaptic."""
        stdp = STDPPlasticity()

        # Post spike at t=0, pre spike at t=0.01 (10ms later)
        pre_times = torch.tensor([[0.01]])
        post_times = torch.tensor([[0.0]])
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # LTD should produce negative weight change
        assert delta_w.sum().item() < 0

    def test_stdp_exponential_decay(self) -> None:
        """Test that STDP weight update decays exponentially with time difference.

        Mathematical invariant: Δw(Δt) = A+ * exp(-Δt/τ+) for Δt > 0
        Should decrease monotonically with increasing Δt.
        """
        stdp = STDPPlasticity()

        # Test at different time delays
        delays = [0.005, 0.010, 0.020, 0.040]
        ltp_values = []

        for delay in delays:
            pre_times = torch.tensor([[0.0]])
            post_times = torch.tensor([[delay]])
            weights = torch.ones(1, 1)
            delta_w = stdp.compute_weight_update(pre_times, post_times, weights)
            ltp_values.append(delta_w.item())

        # Weight changes should decrease with larger time delays
        for i in range(len(ltp_values) - 1):
            assert ltp_values[i] > ltp_values[i + 1]

    def test_stdp_exact_ltp_formula(self) -> None:
        """Test LTP matches exact formula: Δw = A+ * exp(-Δt/τ+).

        Reference: Bi & Poo (1998), Song et al. (2000)
        """
        stdp = STDPPlasticity()
        delta_t = 0.010  # 10 ms

        pre_times = torch.tensor([[0.0]])
        post_times = torch.tensor([[delta_t]])
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # Expected value from formula
        expected = stdp.a_plus * math.exp(-delta_t / stdp.tau_plus)

        assert abs(delta_w.item() - expected) < 1e-6

    def test_stdp_exact_ltd_formula(self) -> None:
        """Test LTD matches exact formula: Δw = -A- * exp(Δt/τ-) for Δt < 0.

        Reference: Bi & Poo (1998)
        """
        stdp = STDPPlasticity()
        delta_t = -0.010  # -10 ms (post before pre)

        pre_times = torch.tensor([[0.010]])
        post_times = torch.tensor([[0.0]])
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # Expected value from formula (note: delta_t is negative, so exp(delta_t/tau))
        expected = -stdp.a_minus * math.exp(delta_t / stdp.tau_minus)

        assert abs(delta_w.item() - expected) < 1e-6

    def test_stdp_zero_at_simultaneous_spikes(self) -> None:
        """Test no weight change when Δt = 0 (simultaneous spikes)."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.0]])
        post_times = torch.tensor([[0.0]])
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # Neither LTP nor LTD should apply when Δt = 0
        assert abs(delta_w.item()) < 1e-6


class TestSTDPNumericalStability:
    """Tests for STDP numerical stability."""

    def test_stdp_forward_pass_through(self) -> None:
        """Test that STDP forward pass is identity."""
        stdp = STDPPlasticity()
        x = torch.randn(4, 10)

        out = stdp(x)

        assert torch.allclose(out, x)

    def test_stdp_no_nan_for_large_time_diff(self) -> None:
        """Test no NaN/Inf for large time differences (>1s)."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.0]])
        post_times = torch.tensor([[2.0]])  # 2 seconds later
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        assert torch.isfinite(delta_w).all()
        # Should be very small (exp(-100) ≈ 0)
        assert abs(delta_w.item()) < 1e-10

    def test_stdp_batch_processing(self) -> None:
        """Test STDP correctly handles batch of spike times."""
        stdp = STDPPlasticity()

        batch_size = 4
        n_pre = 3
        n_post = 2

        pre_times = torch.rand(batch_size, n_pre)
        post_times = torch.rand(batch_size, n_post)
        weights = torch.ones(n_pre, n_post)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        assert delta_w.shape == (n_pre, n_post)
        assert torch.isfinite(delta_w).all()
