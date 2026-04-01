"""ML-dependent biophysics tests (require torch).

Split from test_biophysics_core.py — these tests require torch for
MyceliumFractalNet model testing.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from mycelium_fractal_net.model import MyceliumFractalNet


class TestNetworkNumericalStability:
    """Test neural network numerical stability under various conditions."""

    def test_model_stability_1000_steps(self) -> None:
        torch.manual_seed(42)
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        model.eval()
        x = torch.randn(32, 4)
        for step in range(1000):
            x_in = x + torch.randn_like(x) * 0.01
            out = model(x_in)
            assert torch.isfinite(out).all(), f"NaN/Inf at step {step}"

    def test_model_gradient_stability(self) -> None:
        torch.manual_seed(42)
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = torch.nn.MSELoss()
        x = torch.randn(32, 4)
        y = torch.randn(32, 1)
        for step in range(100):
            optimizer.zero_grad()
            out = model(x)
            loss = criterion(out, y)
            loss.backward()
            for name, param in model.named_parameters():
                if param.grad is not None:
                    assert torch.isfinite(param.grad).all(), (
                        f"Non-finite gradient in {name} at step {step}"
                    )
            optimizer.step()

    def test_model_with_extreme_inputs(self) -> None:
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        model.eval()
        for val, name in [(100.0, "large"), (1e-6, "small"), (-100.0, "negative")]:
            x = torch.ones(8, 4) * val
            out = model(x)
            assert torch.isfinite(out).all(), f"Model fails with {name} inputs"

    def test_model_with_zero_input(self) -> None:
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        model.eval()
        x = torch.zeros(8, 4)
        out = model(x)
        assert torch.isfinite(out).all()
        assert out.shape == (8, 1)


class TestBatchProcessing:
    @pytest.mark.parametrize("batch_size", [1, 4, 16, 64, 128])
    def test_various_batch_sizes(self, batch_size: int) -> None:
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        model.eval()
        x = torch.randn(batch_size, 4)
        out = model(x)
        assert out.shape == (batch_size, 1)
        assert torch.isfinite(out).all()

    @pytest.mark.parametrize("input_dim", [2, 4, 8, 16, 32])
    def test_various_input_dims(self, input_dim: int) -> None:
        model = MyceliumFractalNet(input_dim=input_dim, hidden_dim=32)
        model.eval()
        x = torch.randn(8, input_dim)
        out = model(x)
        assert out.shape == (8, 1)
        assert torch.isfinite(out).all()
