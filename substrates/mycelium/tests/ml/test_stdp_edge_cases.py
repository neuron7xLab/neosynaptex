"""Additional edge case tests for STDP plasticity module.

These tests target the uncovered code paths in core/stdp.py:
- Parameter validation edge cases
- Weight update computation edge cases
- Numerical stability with extreme values

Reference: MFN_MATH_MODEL.md Appendix C (STDP Mathematical Model)
"""

import math

import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net.core.stdp import (
    STDP_A_MINUS,
    STDP_A_PLUS,
    STDP_TAU_MINUS,
    STDP_TAU_PLUS,
    STDPPlasticity,
)


class TestSTDPValidationEdgeCases:
    """Tests for STDP parameter validation edge cases."""

    def test_stdp_boundary_tau_minimum(self) -> None:
        """Test tau at exactly the minimum boundary (5 ms)."""
        # Should succeed at boundary
        stdp = STDPPlasticity(tau_plus=0.005, tau_minus=0.005)
        assert stdp.tau_plus == 0.005
        assert stdp.tau_minus == 0.005

    def test_stdp_boundary_tau_maximum(self) -> None:
        """Test tau at exactly the maximum boundary (100 ms)."""
        # Should succeed at boundary
        stdp = STDPPlasticity(tau_plus=0.100, tau_minus=0.100)
        assert stdp.tau_plus == 0.100
        assert stdp.tau_minus == 0.100

    def test_stdp_boundary_amplitude_minimum(self) -> None:
        """Test amplitude at exactly the minimum boundary (0.001)."""
        stdp = STDPPlasticity(a_plus=0.001, a_minus=0.001)
        assert stdp.a_plus == 0.001
        assert stdp.a_minus == 0.001

    def test_stdp_boundary_amplitude_maximum(self) -> None:
        """Test amplitude at exactly the maximum boundary (0.1)."""
        stdp = STDPPlasticity(a_plus=0.100, a_minus=0.100)
        assert stdp.a_plus == 0.100
        assert stdp.a_minus == 0.100

    def test_stdp_tau_just_below_minimum(self) -> None:
        """Test tau just below the minimum boundary."""
        with pytest.raises(ValueError, match="biophysical range"):
            STDPPlasticity(tau_plus=0.00499)

    def test_stdp_tau_just_above_maximum(self) -> None:
        """Test tau just above the maximum boundary."""
        with pytest.raises(ValueError, match="biophysical range"):
            STDPPlasticity(tau_minus=0.1001)

    def test_stdp_amplitude_just_below_minimum(self) -> None:
        """Test amplitude just below the minimum boundary."""
        with pytest.raises(ValueError, match="stable range"):
            STDPPlasticity(a_plus=0.00099)

    def test_stdp_amplitude_just_above_maximum(self) -> None:
        """Test amplitude just above the maximum boundary."""
        with pytest.raises(ValueError, match="stable range"):
            STDPPlasticity(a_minus=0.1001)

    def test_stdp_asymmetric_tau_values(self) -> None:
        """Test with different tau_plus and tau_minus values."""
        stdp = STDPPlasticity(tau_plus=0.010, tau_minus=0.030)
        assert stdp.tau_plus == 0.010
        assert stdp.tau_minus == 0.030

    def test_stdp_asymmetric_amplitude_values(self) -> None:
        """Test with custom asymmetric amplitudes."""
        stdp = STDPPlasticity(a_plus=0.005, a_minus=0.015)
        assert stdp.a_plus == 0.005
        assert stdp.a_minus == 0.015


class TestSTDPWeightUpdateEdgeCases:
    """Tests for STDP weight update computation edge cases."""

    def test_stdp_multiple_pre_single_post(self) -> None:
        """Test multiple presynaptic spikes with single postsynaptic spike."""
        stdp = STDPPlasticity()

        # 3 presynaptic spikes at different times
        pre_times = torch.tensor([[0.0, 0.01, 0.02]])
        post_times = torch.tensor([[0.015]])  # Post between pre[1] and pre[2]
        weights = torch.ones(3, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        assert delta_w.shape == (3, 1)
        # First two pre spikes are before post -> LTP (positive)
        # Last pre spike is after post -> LTD (negative)
        assert torch.isfinite(delta_w).all()

    def test_stdp_single_pre_multiple_post(self) -> None:
        """Test single presynaptic spike with multiple postsynaptic spikes."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.01]])
        post_times = torch.tensor([[0.005, 0.015, 0.025]])  # Some before, some after
        weights = torch.ones(1, 3)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        assert delta_w.shape == (1, 3)
        assert torch.isfinite(delta_w).all()

    def test_stdp_large_batch(self) -> None:
        """Test with large batch size."""
        stdp = STDPPlasticity()

        batch_size = 64
        n_pre = 10
        n_post = 8

        torch.manual_seed(42)
        pre_times = torch.rand(batch_size, n_pre)
        post_times = torch.rand(batch_size, n_post)
        weights = torch.ones(n_pre, n_post)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        assert delta_w.shape == (n_pre, n_post)
        assert torch.isfinite(delta_w).all()

    def test_stdp_very_small_time_difference(self) -> None:
        """Test with very small time differences (sub-microsecond)."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.0]])
        post_times = torch.tensor([[1e-9]])  # 1 nanosecond
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # Should be very close to A+ (minimal decay)
        assert delta_w.item() == pytest.approx(stdp.a_plus, rel=1e-6)

    def test_stdp_very_large_time_difference(self) -> None:
        """Test with very large time differences (minutes)."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.0]])
        post_times = torch.tensor([[60.0]])  # 1 minute
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # Should be essentially zero (exp(-3000) is tiny, but clamping may apply)
        # Using 1e-10 as a reasonable threshold for "effectively zero"
        assert abs(delta_w.item()) < 1e-10

    def test_stdp_negative_spike_times(self) -> None:
        """Test with negative spike times (relative timing is what matters)."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[-0.010]])
        post_times = torch.tensor([[0.0]])  # 10ms after pre
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # Should produce LTP (positive) since post is after pre
        assert delta_w.item() > 0

    def test_stdp_all_pre_before_post(self) -> None:
        """Test when all presynaptic spikes precede postsynaptic."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.0, 0.002, 0.004]])
        post_times = torch.tensor([[0.010]])
        weights = torch.ones(3, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # All should contribute to LTP (positive)
        assert (delta_w > 0).all()

    def test_stdp_all_pre_after_post(self) -> None:
        """Test when all presynaptic spikes follow postsynaptic."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.020, 0.022, 0.024]])
        post_times = torch.tensor([[0.010]])
        weights = torch.ones(3, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # All should contribute to LTD (negative)
        assert (delta_w < 0).all()

    def test_stdp_mixed_ltp_ltd(self) -> None:
        """Test weight update with mixed LTP and LTD contributions."""
        stdp = STDPPlasticity()

        # Pre spikes at 0, 20ms; post at 10ms
        # First pre -> LTP (10ms delay)
        # Second pre -> LTD (10ms early)
        pre_times = torch.tensor([[0.0, 0.020]])
        post_times = torch.tensor([[0.010]])
        weights = torch.ones(2, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # First synapse: LTP (pre before post)
        # Second synapse: LTD (pre after post)
        assert delta_w[0, 0].item() > 0
        assert delta_w[1, 0].item() < 0


class TestSTDPNumericalStabilityEdgeCases:
    """Tests for STDP numerical stability with extreme values."""

    def test_stdp_exp_clamp_prevents_overflow(self) -> None:
        """Test that exponential clamping prevents numerical overflow."""
        stdp = STDPPlasticity()

        # Time difference that would cause exp(100) without clamping
        pre_times = torch.tensor([[-100.0]])
        post_times = torch.tensor([[0.0]])
        weights = torch.ones(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # Should not overflow
        assert torch.isfinite(delta_w).all()

    def test_stdp_zero_weights_input(self) -> None:
        """Test with zero weight matrix (weights don't affect STDP update)."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.0]])
        post_times = torch.tensor([[0.01]])
        weights = torch.zeros(1, 1)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        # STDP doesn't use weights directly in the computation
        # (weight-dependent STDP would be a different variant)
        assert torch.isfinite(delta_w).all()

    def test_stdp_preserves_dtype(self) -> None:
        """Test that output dtype matches input dtype."""
        stdp = STDPPlasticity()

        # Test float32
        pre_times_32 = torch.tensor([[0.0]], dtype=torch.float32)
        post_times_32 = torch.tensor([[0.01]], dtype=torch.float32)
        weights_32 = torch.ones(1, 1, dtype=torch.float32)

        delta_w_32 = stdp.compute_weight_update(pre_times_32, post_times_32, weights_32)
        assert delta_w_32.dtype == torch.float32

    def test_stdp_double_precision(self) -> None:
        """Test STDP with double precision."""
        stdp = STDPPlasticity()

        pre_times = torch.tensor([[0.0]], dtype=torch.float64)
        post_times = torch.tensor([[0.01]], dtype=torch.float64)
        weights = torch.ones(1, 1, dtype=torch.float64)

        delta_w = stdp.compute_weight_update(pre_times, post_times, weights)

        assert delta_w.dtype == torch.float64
        # Higher precision should give more accurate result
        expected = stdp.a_plus * math.exp(-0.01 / stdp.tau_plus)
        assert abs(delta_w.item() - expected) < 1e-10


class TestSTDPForwardPassthrough:
    """Tests for STDP forward pass identity behavior."""

    def test_stdp_forward_preserves_grad(self) -> None:
        """Test that forward pass preserves gradient computation."""
        stdp = STDPPlasticity()

        x = torch.randn(4, 10, requires_grad=True)
        out = stdp(x)

        # Check gradient flow
        loss = out.sum()
        loss.backward()

        assert x.grad is not None
        assert torch.allclose(x.grad, torch.ones_like(x))

    def test_stdp_forward_different_shapes(self) -> None:
        """Test forward pass with various input shapes."""
        stdp = STDPPlasticity()

        shapes = [(1,), (10,), (4, 10), (2, 3, 4), (1, 1, 1, 1)]

        for shape in shapes:
            x = torch.randn(shape)
            out = stdp(x)
            assert out.shape == x.shape
            assert torch.allclose(out, x)

    def test_stdp_is_nn_module(self) -> None:
        """Test that STDPPlasticity is a proper nn.Module."""
        stdp = STDPPlasticity()

        assert isinstance(stdp, torch.nn.Module)
        assert hasattr(stdp, "forward")
        assert hasattr(stdp, "parameters")


class TestSTDPBiophysicalConstraints:
    """Tests verifying biophysical constraints from literature."""

    def test_stdp_bi_poo_parameters(self) -> None:
        """Test default parameters match Bi & Poo (1998) values.

        Reference: Bi & Poo (1998) J. Neuroscience 18(24):10464-10472
        """
        # Default values should be:
        # tau_+ = tau_- = 20 ms
        # A_+ = 0.01, A_- = 0.012

        assert STDP_TAU_PLUS == 0.020
        assert STDP_TAU_MINUS == 0.020
        assert STDP_A_PLUS == 0.01
        assert STDP_A_MINUS == 0.012

    def test_stdp_asymmetry_prevents_runaway_ltp(self) -> None:
        """Test that A_- > A_+ prevents runaway LTP.

        Biophysical rationale: Network stability requires that average
        depression exceeds average potentiation under random spike timing.
        """
        stdp = STDPPlasticity()

        # A_- should be larger than A_+
        assert stdp.a_minus > stdp.a_plus

        # The ratio (typically 1.05-1.25) ensures stability
        ratio = stdp.a_minus / stdp.a_plus
        assert 1.0 < ratio < 2.0  # Typical biophysical range

    def test_stdp_time_constant_physiological(self) -> None:
        """Test time constants are in physiological range.

        Reference: STDP time constants typically range from 10-50 ms
        for hippocampal and cortical neurons.
        """
        stdp = STDPPlasticity()

        # Time constants in ms
        tau_plus_ms = stdp.tau_plus * 1000
        tau_minus_ms = stdp.tau_minus * 1000

        # Should be in typical range (5-100 ms)
        assert 5 <= tau_plus_ms <= 100
        assert 5 <= tau_minus_ms <= 100
