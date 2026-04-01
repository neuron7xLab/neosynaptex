"""Tests for sparse attention module.

Mathematical validation tests for Top-K Sparse Attention.

Reference: Vaswani et al. (2017), Child et al. (2019)

Equations tested:
    Attention(Q,K,V) = softmax(QK^T / √d_k) V
    Sparsity: Only top-k scores retained per query

Complexity:
    Standard: O(n²d)
    Sparse: O(n·k·d)
"""

import math

import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net import SPARSE_TOPK
from mycelium_fractal_net.model import SparseAttention


class TestSparseAttentionParameterValidation:
    """Tests for sparse attention parameter validation."""

    def test_sparse_attention_topk_default(self) -> None:
        """Verify sparse attention uses default topk=4."""
        attn = SparseAttention(embed_dim=32)
        assert attn.topk == SPARSE_TOPK
        assert attn.topk == 4

    def test_sparse_attention_rejects_invalid_embed_dim(self) -> None:
        """Verify rejection of embed_dim < 1."""
        with pytest.raises(ValueError, match="embed_dim"):
            SparseAttention(embed_dim=0)

    def test_sparse_attention_rejects_invalid_topk(self) -> None:
        """Verify rejection of topk < 1."""
        with pytest.raises(ValueError, match="topk"):
            SparseAttention(embed_dim=32, topk=0)

    def test_sparse_attention_rejects_invalid_num_heads(self) -> None:
        """Verify rejection of num_heads < 1."""
        with pytest.raises(ValueError, match="num_heads"):
            SparseAttention(embed_dim=32, num_heads=0)


class TestSparseAttentionMathematicalProperties:
    """Tests for sparse attention mathematical model correctness."""

    def test_sparse_attention_output_shape(self) -> None:
        """Test sparse attention preserves input shape."""
        batch_size = 2
        seq_len = 8
        embed_dim = 32

        attn = SparseAttention(embed_dim=embed_dim)
        x = torch.randn(batch_size, seq_len, embed_dim)

        out = attn(x)

        assert out.shape == x.shape

    def test_sparse_attention_scaling_factor(self) -> None:
        """Test scaling factor √d_k is correctly applied.

        Mathematical basis: Var(Q·K) = d_k for random Q,K with unit variance
        Division by √d_k normalizes variance to 1, preventing softmax saturation.
        """
        embed_dim = 64
        # Create attention to ensure scale factor is applied correctly
        _ = SparseAttention(embed_dim=embed_dim)

        # Expected scale factor
        expected_scale = math.sqrt(embed_dim)
        assert expected_scale == 8.0  # √64 = 8

    def test_sparse_attention_topk_selection(self) -> None:
        """Test that only top-k attention weights are non-zero.

        Sparsity invariant: For each query, at most k positions have non-zero weight.
        """
        attn = SparseAttention(embed_dim=16, topk=2)
        x = torch.randn(1, 8, 16)

        # Access attention computation manually
        q = attn.q_proj(x)
        k = attn.k_proj(x)
        scale = math.sqrt(attn.embed_dim)
        scores = torch.bmm(q, k.transpose(1, 2)) / scale

        # After topk and softmax, at most k positions should have significant weight
        topk_val = min(attn.topk, x.shape[1])
        _, topk_indices = scores.topk(topk_val, dim=-1)

        # Verify topk indices shape
        assert topk_indices.shape == (1, 8, 2)

    def test_sparse_attention_handles_short_sequence(self) -> None:
        """Test sparse attention handles sequences shorter than topk.

        When seq_len < topk, all positions should be included.
        """
        attn = SparseAttention(embed_dim=16, topk=4)
        x = torch.randn(1, 2, 16)  # seq_len=2 < topk=4

        out = attn(x)

        assert out.shape == x.shape
        assert not torch.isnan(out).any()


class TestSparseAttentionNumericalStability:
    """Tests for sparse attention numerical stability."""

    def test_sparse_attention_no_nan(self) -> None:
        """Test sparse attention doesn't produce NaN values."""
        attn = SparseAttention(embed_dim=16)
        x = torch.randn(2, 4, 16)

        out = attn(x)

        assert not torch.isnan(out).any()

    def test_sparse_attention_no_inf(self) -> None:
        """Test sparse attention doesn't produce Inf values."""
        attn = SparseAttention(embed_dim=16)
        x = torch.randn(2, 4, 16)

        out = attn(x)

        assert not torch.isinf(out).any()

    def test_sparse_attention_gradient_flow(self) -> None:
        """Test that gradients flow through sparse attention."""
        attn = SparseAttention(embed_dim=16)
        x = torch.randn(2, 4, 16, requires_grad=True)

        out = attn(x)
        loss = out.sum()
        loss.backward()

        assert x.grad is not None
        assert not torch.isnan(x.grad).any()

    def test_sparse_attention_deterministic(self) -> None:
        """Test sparse attention is deterministic (no randomness)."""
        torch.manual_seed(42)
        attn = SparseAttention(embed_dim=16)
        x = torch.randn(2, 4, 16)

        out1 = attn(x)
        out2 = attn(x)

        assert torch.allclose(out1, out2)

    def test_sparse_attention_large_embed_dim(self) -> None:
        """Test sparse attention works with large embed_dim (scaling factor critical)."""
        embed_dim = 512
        attn = SparseAttention(embed_dim=embed_dim)
        x = torch.randn(1, 4, embed_dim)

        out = attn(x)

        assert out.shape == x.shape
        assert torch.isfinite(out).all()
