"""Tests for MyceliumFractalNet neural network model."""

import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net.model import MyceliumFractalNet


def test_model_forward_2d_input() -> None:
    """Test model handles 2D input (batch, features)."""
    model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
    x = torch.randn(8, 4)  # batch=8, features=4

    out = model(x)

    assert out.shape == (8, 1)
    assert not torch.isnan(out).any()


def test_model_forward_3d_input() -> None:
    """Test model handles 3D input (batch, seq_len, features)."""
    model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
    x = torch.randn(8, 5, 4)  # batch=8, seq_len=5, features=4

    out = model(x)

    assert out.shape == (8, 1)
    assert not torch.isnan(out).any()


def test_model_without_sparse_attention() -> None:
    """Test model works without sparse attention."""
    model = MyceliumFractalNet(use_sparse_attention=False)
    x = torch.randn(4, 4)

    out = model(x)

    assert out.shape == (4, 1)


def test_model_without_stdp() -> None:
    """Test model works without STDP module."""
    model = MyceliumFractalNet(use_stdp=False)
    x = torch.randn(4, 4)

    out = model(x)

    assert out.shape == (4, 1)


def test_model_train_step() -> None:
    """Test model training step."""
    model = MyceliumFractalNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = torch.nn.MSELoss()

    x = torch.randn(8, 4)
    y = torch.randn(8, 1)

    loss = model.train_step(x, y, optimizer, loss_fn)

    assert isinstance(loss, float)
    assert loss >= 0.0


def test_model_gradient_flow() -> None:
    """Test gradients flow through model."""
    model = MyceliumFractalNet()
    x = torch.randn(4, 4, requires_grad=True)

    out = model(x)
    loss = out.sum()
    loss.backward()

    # Check gradients exist in model parameters
    for param in model.parameters():
        if param.requires_grad:
            assert param.grad is not None


def test_model_parameter_count() -> None:
    """Test model has reasonable number of parameters."""
    model = MyceliumFractalNet(input_dim=4, hidden_dim=32)

    total_params = sum(p.numel() for p in model.parameters())

    # Should be reasonable size
    assert total_params > 0
    assert total_params < 100000  # Not too large


def test_model_deterministic_with_seed() -> None:
    """Test model is deterministic with same seed."""
    torch.manual_seed(42)
    model1 = MyceliumFractalNet()
    x1 = torch.randn(4, 4)
    out1 = model1(x1)

    torch.manual_seed(42)
    model2 = MyceliumFractalNet()
    x2 = torch.randn(4, 4)
    out2 = model2(x2)

    assert torch.allclose(out1, out2)
