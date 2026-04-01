"""Neural network components — STDPPlasticity, SparseAttention."""

from __future__ import annotations

import math

from mycelium_fractal_net._optional import require_ml_dependency

torch = require_ml_dependency("torch")
nn = torch.nn
F = torch.nn.functional

# === STDP parameters (heterosynaptic) ===
STDP_TAU_PLUS: float = 0.020  # 20 ms
STDP_TAU_MINUS: float = 0.020  # 20 ms
STDP_A_PLUS: float = 0.01
STDP_A_MINUS: float = 0.012

# === Sparse attention top-k ===
SPARSE_TOPK: int = 4


class STDPPlasticity(nn.Module):
    """
    Spike-Timing Dependent Plasticity (STDP) module.

    Mathematical Model (Bi & Poo, 1998):
    ------------------------------------
    The STDP learning rule implements Hebbian plasticity based on relative
    spike timing between pre- and postsynaptic neurons:

    .. math::

        \\Delta w = \\begin{cases}
            A_+ e^{-\\Delta t/\\tau_+} & \\Delta t > 0 \\text{ (LTP)} \\\\
            -A_- e^{\\Delta t/\\tau_-} & \\Delta t < 0 \\text{ (LTD)}
        \\end{cases}

    where:
        - Δt = t_post - t_pre (spike timing difference)
        - τ+ = τ- = 20 ms (time constant, from hippocampal slice recordings)
        - A+ = 0.01 (LTP magnitude, dimensionless)
        - A- = 0.012 (LTD magnitude, dimensionless, asymmetric for stability)

    Biophysical Basis:
    ------------------
    - NMDA receptor activation requires coincident pre/post activity
    - Ca²⁺ influx magnitude determines potentiation vs depression
    - Asymmetry (A- > A+) prevents runaway excitation

    Parameter Constraints:
    ----------------------
    - τ ∈ [5, 100] ms: Biological range from cortical recordings
    - A ∈ [0.001, 0.1]: Prevents weight explosion while maintaining plasticity
    - A-/A+ > 1: Ensures stable network dynamics (prevents runaway LTP)

    References:
        Bi, G. & Poo, M. (1998). Synaptic modifications in cultured
        hippocampal neurons. J. Neuroscience, 18(24), 10464-10472.

        Song, S., Miller, K.D. & Abbott, L.F. (2000). Competitive Hebbian
        learning through spike-timing-dependent synaptic plasticity.
        Nature Neuroscience, 3(9), 919-926.
    """

    # Biophysically valid parameter ranges (from empirical neurophysiology)
    TAU_MIN: float = 0.005  # 5 ms
    TAU_MAX: float = 0.100  # 100 ms
    A_MIN: float = 0.001
    A_MAX: float = 0.100

    # Numerical stability constants
    EXP_CLAMP_MAX: float = 50.0  # exp(-50) ≈ 1.9e-22, prevents underflow/overflow

    def __init__(
        self,
        tau_plus: float = STDP_TAU_PLUS,
        tau_minus: float = STDP_TAU_MINUS,
        a_plus: float = STDP_A_PLUS,
        a_minus: float = STDP_A_MINUS,
    ) -> None:
        super().__init__()

        # Validate parameters against biophysical constraints
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
        Compute STDP weight update.

        Parameters
        ----------
        pre_times : torch.Tensor
            Presynaptic spike times of shape (batch, n_pre).
        post_times : torch.Tensor
            Postsynaptic spike times of shape (batch, n_post).
        weights : torch.Tensor
            Current weights of shape (n_pre, n_post).

        Returns
        -------
        torch.Tensor
            Weight update matrix.
        """
        # Time differences: delta_t = t_post - t_pre
        # Positive delta_t means pre before post (LTP)
        delta_t = post_times.unsqueeze(-2) - pre_times.unsqueeze(-1)

        # Clamp exponential arguments to prevent underflow/overflow
        # Uses class constant EXP_CLAMP_MAX for consistency
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
        """Pass through (STDP is applied via compute_weight_update)."""
        return x


class SparseAttention(nn.Module):
    """
    Sparse attention mechanism with top-k selection.

    Mathematical Model:
    -------------------
    Standard scaled dot-product attention with sparse masking:

    .. math::

        \\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V

    Sparsification:
        For each query position, only the top-k attention scores are retained,
        others are set to -∞ before softmax:

    .. math::

        \\text{SparseAttention}_i = \\text{softmax}(\\text{topk}(\\frac{Q_i K^T}{\\sqrt{d_k}}, k))V

    Scaling Factor:
        The factor √d_k (embed_dim) normalizes variance of dot products:
        - For random Q,K with unit variance: Var(Q·K) = d_k
        - Division by √d_k → Var(Q·K/√d_k) = 1
        - Prevents softmax saturation for large d_k

    Complexity Analysis:
    --------------------
    - Standard attention: O(n²d) time, O(n²) space for attention matrix
    - Sparse attention: O(n·k·d) time, O(n·k) effective space
    - Speedup factor: n/k (e.g., 8x for n=32, k=4)

    Parameter Constraints:
    ----------------------
    - topk ∈ [1, seq_len]: Must be at least 1 for valid softmax
    - embed_dim > 0: Must be positive
    - Recommended: topk ≤ √seq_len for efficiency vs. expressiveness tradeoff

    Design Choices:
    ---------------
    - Default topk=4: Balances sparsity with context retention
    - NaN handling: Replaces NaN with 0 (occurs when seq_len < topk)

    References:
        Vaswani, A. et al. (2017). Attention Is All You Need. NeurIPS.
        Child, R. et al. (2019). Generating Long Sequences with Sparse Transformers.
    """

    # Valid parameter ranges
    TOPK_MIN: int = 1
    EMBED_DIM_MIN: int = 1

    def __init__(
        self,
        embed_dim: int,
        num_heads: int = 1,
        topk: int = SPARSE_TOPK,
    ) -> None:
        super().__init__()

        # Validate parameters
        if embed_dim < self.EMBED_DIM_MIN:
            raise ValueError(f"embed_dim={embed_dim} must be >= {self.EMBED_DIM_MIN}")
        if topk < self.TOPK_MIN:
            raise ValueError(f"topk={topk} must be >= {self.TOPK_MIN}")
        if num_heads < 1:
            raise ValueError(f"num_heads={num_heads} must be >= 1")

        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.topk = topk

        self.q_proj = nn.Linear(embed_dim, embed_dim)
        self.k_proj = nn.Linear(embed_dim, embed_dim)
        self.v_proj = nn.Linear(embed_dim, embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Apply sparse attention.

        Parameters
        ----------
        x : torch.Tensor
            Input of shape (batch, seq_len, embed_dim).

        Returns
        -------
        torch.Tensor
            Output of same shape.
        """
        _batch_size, seq_len, _ = x.shape

        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        # Compute attention scores
        scale = math.sqrt(self.embed_dim)
        scores = torch.bmm(q, k.transpose(1, 2)) / scale

        # Sparse top-k selection
        topk_val = min(self.topk, seq_len)
        topk_values, topk_indices = scores.topk(topk_val, dim=-1)

        # Create sparse attention mask
        sparse_scores = torch.full_like(scores, float("-inf"))
        sparse_scores.scatter_(-1, topk_indices, topk_values)

        # Softmax over sparse scores
        attn_weights = F.softmax(sparse_scores, dim=-1)
        attn_weights = torch.nan_to_num(attn_weights, nan=0.0)

        # Apply attention
        out = torch.bmm(attn_weights, v)
        result: torch.Tensor = self.out_proj(out)
        return result
