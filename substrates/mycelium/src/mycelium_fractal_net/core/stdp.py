"""
STDP Plasticity Module (PyTorch ML layer).

This module provides STDP for the PyTorch model pipeline (model_pkg/).
For the core numpy simulation, STDP-like plasticity is implemented as
adaptive diffusivity in reaction_diffusion_engine._adapt_alpha().

Conceptual domain: Synaptic plasticity, learning rules

Reference:
    - docs/MFN_MATH_MODEL.md Appendix C (STDP Mathematical Model)
    - docs/ARCHITECTURE.md Section 4 (STDP Plasticity)

Mathematical Model:
    Δw = A_+ exp(-Δt/τ_+)  if Δt > 0 (LTP - Long-Term Potentiation)
    Δw = -A_- exp(Δt/τ_-)  if Δt < 0 (LTD - Long-Term Depression)

    where Δt = t_post - t_pre

Parameters (from Bi & Poo, 1998):
    τ_+ = τ_- = 20 ms    - Time constants
    A_+ = 0.01           - LTP magnitude
    A_- = 0.012          - LTD magnitude (asymmetric for stability)

Biophysical basis:
    - NMDA receptor activation requires coincident pre/post activity
    - Ca²⁺ influx magnitude determines potentiation vs depression
    - Asymmetry (A_- > A_+) prevents runaway excitation

Example:
    >>> import torch
    >>> from mycelium_fractal_net.core.stdp import STDPPlasticity
    >>> stdp = STDPPlasticity(tau_plus=0.020, tau_minus=0.020)
    >>> pre_times = torch.tensor([[0.01, 0.02]])  # Pre-synaptic spike times
    >>> post_times = torch.tensor([[0.015]])      # Post-synaptic spike times
    >>> weights = torch.ones(2, 1)
    >>> delta_w = stdp.compute_weight_update(pre_times, post_times, weights)
"""

from __future__ import annotations

from mycelium_fractal_net._optional import require_ml_dependency

torch = require_ml_dependency("torch")
nn = torch.nn

# Default STDP parameters (from neurophysiology)
STDP_TAU_PLUS: float = 0.020  # 20 ms
STDP_TAU_MINUS: float = 0.020  # 20 ms
STDP_A_PLUS: float = 0.01
STDP_A_MINUS: float = 0.012

__all__ = [
    "STDP_A_MINUS",
    "STDP_A_PLUS",
    "STDP_TAU_MINUS",
    # Constants
    "STDP_TAU_PLUS",
    # Classes
    "STDPPlasticity",
]


class STDPPlasticity(nn.Module):
    """
    Spike-Timing Dependent Plasticity (STDP) module.

    Implements heterosynaptic Hebbian plasticity based on relative
    spike timing between pre- and postsynaptic neurons.

    Parameters
    ----------
    tau_plus : float, optional
        LTP time constant in seconds, default 20 ms.
    tau_minus : float, optional
        LTD time constant in seconds, default 20 ms.
    a_plus : float, optional
        LTP magnitude, default 0.01.
    a_minus : float, optional
        LTD magnitude, default 0.012 (asymmetric for stability).

    Raises
    ------
    ValueError
        If parameters are outside biophysical ranges.

    Reference
    ---------
    Bi, G. & Poo, M. (1998). Synaptic modifications in cultured
    hippocampal neurons. J. Neuroscience, 18(24), 10464-10472.
    """

    # Biophysically valid parameter ranges
    TAU_MIN: float = 0.005  # 5 ms
    TAU_MAX: float = 0.100  # 100 ms
    A_MIN: float = 0.001
    A_MAX: float = 0.100

    # Numerical stability
    EXP_CLAMP_MAX: float = 50.0

    def __init__(
        self,
        tau_plus: float = STDP_TAU_PLUS,
        tau_minus: float = STDP_TAU_MINUS,
        a_plus: float = STDP_A_PLUS,
        a_minus: float = STDP_A_MINUS,
    ) -> None:
        super().__init__()

        # Validate parameters
        self._validate_time_constant(tau_plus, "tau_plus")
        self._validate_time_constant(tau_minus, "tau_minus")
        self._validate_amplitude(a_plus, "a_plus")
        self._validate_amplitude(a_minus, "a_minus")

        self.tau_plus = tau_plus
        self.tau_minus = tau_minus
        self.a_plus = a_plus
        self.a_minus = a_minus

    def _validate_time_constant(self, tau: float, name: str) -> None:
        """Validate time constant is within biophysical range."""
        if not (self.TAU_MIN <= tau <= self.TAU_MAX):
            tau_min_ms = self.TAU_MIN * 1000
            tau_max_ms = self.TAU_MAX * 1000
            tau_ms = tau * 1000
            raise ValueError(
                f"{name}={tau_ms:.1f}ms outside biophysical range "
                f"[{tau_min_ms:.0f}, {tau_max_ms:.0f}]ms"
            )

    def _validate_amplitude(self, a: float, name: str) -> None:
        """Validate amplitude is within stable range."""
        if not (self.A_MIN <= a <= self.A_MAX):
            raise ValueError(f"{name}={a} outside stable range [{self.A_MIN}, {self.A_MAX}]")

    def compute_weight_update(
        self,
        pre_times: torch.Tensor,
        post_times: torch.Tensor,
        weights: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute STDP weight update matrix.

        Parameters
        ----------
        pre_times : torch.Tensor
            Presynaptic spike times, shape (batch, n_pre).
        post_times : torch.Tensor
            Postsynaptic spike times, shape (batch, n_post).
        weights : torch.Tensor
            Current weights, shape (n_pre, n_post).

        Returns
        -------
        torch.Tensor
            Weight update matrix, shape (n_pre, n_post).
        """
        # Time differences: delta_t = t_post - t_pre
        delta_t = post_times.unsqueeze(-2) - pre_times.unsqueeze(-1)

        clamp = self.EXP_CLAMP_MAX

        # LTP: pre before post (delta_t > 0)
        ltp_mask = delta_t > 0
        ltp_exp_arg = torch.clamp(-delta_t / self.tau_plus, min=-clamp, max=clamp)
        ltp = self.a_plus * torch.exp(ltp_exp_arg)
        ltp = ltp * ltp_mask.float()

        # LTD: post before pre (delta_t < 0)
        ltd_mask = delta_t < 0
        ltd_exp_arg = torch.clamp(delta_t / self.tau_minus, min=-clamp, max=clamp)
        ltd = -self.a_minus * torch.exp(ltd_exp_arg)
        ltd = ltd * ltd_mask.float()

        # Sum updates across batch
        delta_w = (ltp + ltd).mean(dim=0)

        return delta_w

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Pass-through (STDP is applied via compute_weight_update)."""
        return x
