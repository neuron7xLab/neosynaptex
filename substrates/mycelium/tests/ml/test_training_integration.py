"""End-to-end training integration tests for MyceliumFractalNet.

This module tests complete training loops with convergence guarantees
and validates gradient flow through the entire network.

References:
    - Rumelhart et al. (1986) "Learning representations by back-propagating errors"
    - Glorot & Bengio (2010) "Understanding the difficulty of training deep FFNs"
"""

import pytest

torch = pytest.importorskip("torch")
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from mycelium_fractal_net.model import MyceliumFractalNet


class TestTrainingConvergence:
    """Test MFN training converges on toy problems."""

    def test_xor_problem_convergence(self) -> None:
        """Test MFN learns XOR function.

        XOR is non-linearly separable, requires hidden representations.
        This validates the network can learn non-trivial patterns.
        """
        torch.manual_seed(42)

        # XOR dataset
        x = torch.tensor([[0.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 1.0]])
        y = torch.tensor([[0.0], [1.0], [1.0], [0.0]])

        model = MyceliumFractalNet(
            input_dim=2,
            hidden_dim=32,
            use_sparse_attention=True,
            use_stdp=True,
        )

        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        initial_loss = None
        for epoch in range(500):
            optimizer.zero_grad()
            y_pred = model(x)
            loss = criterion(y_pred, y)
            loss.backward()
            optimizer.step()

            if epoch == 0:
                initial_loss = loss.item()

        final_loss = loss.item()

        assert final_loss < 0.3, f"Did not converge: final_loss={final_loss:.4f}"
        assert final_loss < initial_loss * 0.5, "Loss did not decrease significantly"

    def test_linear_regression_convergence(self) -> None:
        """Test MFN can fit a simple linear relationship."""
        torch.manual_seed(42)

        # Linear: y = 2*x1 + 3*x2 + 1
        x = torch.randn(100, 2)
        y = (2 * x[:, 0] + 3 * x[:, 1] + 1).unsqueeze(1)

        model = MyceliumFractalNet(input_dim=2, hidden_dim=32)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        for _epoch in range(200):
            optimizer.zero_grad()
            y_pred = model(x)
            loss = criterion(y_pred, y)
            loss.backward()
            optimizer.step()

        final_loss = loss.item()
        assert final_loss < 1.0, f"Did not converge on linear: loss={final_loss:.4f}"

    def test_batch_training_consistency(self) -> None:
        """Test training with DataLoader produces consistent results."""
        torch.manual_seed(42)

        x = torch.randn(64, 4)
        y = torch.randn(64, 1)

        dataset = TensorDataset(x, y)
        loader = DataLoader(dataset, batch_size=16, shuffle=True)

        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        losses = []
        for _epoch in range(10):
            epoch_loss = 0.0
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                pred = model(batch_x)
                loss = criterion(pred, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            losses.append(epoch_loss / len(loader))

        # Loss should generally decrease (not monotonically due to stochasticity)
        assert losses[-1] <= losses[0] * 1.5, "Training not making progress"


class TestDeterministicTraining:
    """Verify training is deterministic with fixed seed."""

    def test_deterministic_training_same_seed(self) -> None:
        """Verify training is deterministic with same seed."""
        x = torch.randn(100, 10)
        y = torch.randn(100, 1)

        def train_model(seed: int) -> torch.Tensor:
            torch.manual_seed(seed)

            model = MyceliumFractalNet(input_dim=10, hidden_dim=32)
            optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
            criterion = nn.MSELoss()

            for _ in range(10):
                optimizer.zero_grad()
                loss = criterion(model(x), y)
                loss.backward()
                optimizer.step()

            return torch.cat([p.data.flatten() for p in model.parameters()])

        params1 = train_model(42)
        params2 = train_model(42)

        assert torch.allclose(params1, params2, atol=1e-6), "Training not deterministic"

    def test_different_seeds_produce_different_results(self) -> None:
        """Verify different seeds produce different training outcomes."""
        x = torch.randn(100, 10)
        y = torch.randn(100, 1)

        def train_model(seed: int) -> torch.Tensor:
            torch.manual_seed(seed)

            model = MyceliumFractalNet(input_dim=10, hidden_dim=32)
            optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
            criterion = nn.MSELoss()

            for _ in range(10):
                optimizer.zero_grad()
                loss = criterion(model(x), y)
                loss.backward()
                optimizer.step()

            return torch.cat([p.data.flatten() for p in model.parameters()])

        params1 = train_model(42)
        params2 = train_model(123)

        assert not torch.allclose(params1, params2, atol=1e-4), (
            "Different seeds should produce different results"
        )


class TestGradientFlow:
    """Verify gradients flow through entire network."""

    def test_gradient_flow_all_parameters(self) -> None:
        """Verify gradients flow through all parameters."""
        model = MyceliumFractalNet(
            input_dim=10,
            hidden_dim=32,
            use_sparse_attention=True,
            use_stdp=True,
        )

        x = torch.randn(32, 10, requires_grad=True)
        y = torch.randn(32, 1)

        loss = nn.functional.mse_loss(model(x), y)
        loss.backward()

        # Check all parameters received gradients
        for name, param in model.named_parameters():
            assert param.grad is not None, f"No gradient for {name}"
            assert torch.isfinite(param.grad).all(), f"Non-finite gradient in {name}"

    def test_gradient_magnitudes_reasonable(self) -> None:
        """Test gradients have reasonable magnitudes (no vanishing/exploding)."""
        torch.manual_seed(42)

        model = MyceliumFractalNet(input_dim=10, hidden_dim=64)

        x = torch.randn(32, 10)
        y = torch.randn(32, 1)

        loss = nn.functional.mse_loss(model(x), y)
        loss.backward()

        grad_norms = []
        for _name, param in model.named_parameters():
            if param.grad is not None:
                grad_norm = param.grad.norm().item()
                grad_norms.append(grad_norm)

        # Check gradients are not vanishing (all essentially zero)
        max_grad = max(grad_norms)
        assert max_grad > 1e-8, f"Gradients may be vanishing: max_norm={max_grad}"

        # Check gradients are not exploding
        assert max_grad < 1e4, f"Gradients may be exploding: max_norm={max_grad}"

    def test_input_gradient_exists(self) -> None:
        """Test that gradients flow back to input tensor."""
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)

        x = torch.randn(8, 4, requires_grad=True)
        y = torch.randn(8, 1)

        out = model(x)
        loss = nn.functional.mse_loss(out, y)
        loss.backward()

        assert x.grad is not None, "No gradient on input tensor"
        assert torch.isfinite(x.grad).all(), "Non-finite gradient on input"


class TestLossBehavior:
    """Test loss function behavior during training."""

    def test_loss_decreases_on_simple_data(self) -> None:
        """Test that loss decreases on simple fitting task."""
        torch.manual_seed(42)

        # Simple data that should be easy to fit
        x = torch.randn(50, 4)
        y = x.sum(dim=1, keepdim=True)  # y = sum of inputs

        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        initial_loss = criterion(model(x), y).item()

        for _ in range(100):
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        final_loss = criterion(model(x), y).item()

        assert final_loss < initial_loss, "Loss should decrease during training"

    def test_loss_is_non_negative(self) -> None:
        """Test that MSE loss is always non-negative."""
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        criterion = nn.MSELoss()

        for _ in range(10):
            x = torch.randn(16, 4)
            y = torch.randn(16, 1)

            loss = criterion(model(x), y)
            assert loss.item() >= 0, f"Loss should be non-negative: {loss.item()}"


class TestModelConfigurations:
    """Test different model configurations during training."""

    def test_training_without_sparse_attention(self) -> None:
        """Test training works without sparse attention."""
        torch.manual_seed(42)

        model = MyceliumFractalNet(input_dim=4, hidden_dim=32, use_sparse_attention=False)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        x = torch.randn(32, 4)
        y = torch.randn(32, 1)

        initial_loss = criterion(model(x), y).item()

        for _ in range(50):
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        final_loss = criterion(model(x), y).item()
        assert final_loss < initial_loss, "Training should reduce loss"

    def test_training_without_stdp(self) -> None:
        """Test training works without STDP module."""
        torch.manual_seed(42)

        model = MyceliumFractalNet(input_dim=4, hidden_dim=32, use_stdp=False)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        x = torch.randn(32, 4)
        y = torch.randn(32, 1)

        initial_loss = criterion(model(x), y).item()

        for _ in range(50):
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        final_loss = criterion(model(x), y).item()
        assert final_loss < initial_loss, "Training should reduce loss"

    def test_training_minimal_configuration(self) -> None:
        """Test training with minimal model configuration."""
        torch.manual_seed(42)

        model = MyceliumFractalNet(
            input_dim=4,
            hidden_dim=16,  # Small
            use_sparse_attention=False,
            use_stdp=False,
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        x = torch.randn(32, 4)
        y = torch.randn(32, 1)

        for _ in range(50):
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        # Should complete without errors
        assert torch.isfinite(loss), "Loss should be finite"


class TestOptimizers:
    """Test training with different optimizers."""

    @pytest.mark.parametrize(
        "optimizer_class",
        [torch.optim.SGD, torch.optim.Adam, torch.optim.AdamW, torch.optim.RMSprop],
    )
    def test_various_optimizers(self, optimizer_class: type[torch.optim.Optimizer]) -> None:
        """Test training works with various optimizers."""
        torch.manual_seed(42)

        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        optimizer = optimizer_class(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        x = torch.randn(32, 4)
        y = torch.randn(32, 1)

        for _ in range(20):
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        final_loss = criterion(model(x), y).item()

        assert torch.isfinite(torch.tensor(final_loss)), (
            f"Non-finite loss with {optimizer_class.__name__}"
        )


class TestLearningRates:
    """Test training with different learning rates."""

    @pytest.mark.parametrize("lr", [0.001, 0.01, 0.1])
    def test_various_learning_rates(self, lr: float) -> None:
        """Test training works with various learning rates."""
        torch.manual_seed(42)

        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        x = torch.randn(32, 4)
        y = torch.randn(32, 1)

        for _ in range(20):
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        assert torch.isfinite(loss), f"Non-finite loss with lr={lr}"


class TestTrainStepMethod:
    """Test the model's built-in train_step method."""

    def test_train_step_returns_float(self) -> None:
        """Test train_step returns a float loss value."""
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        x = torch.randn(16, 4)
        y = torch.randn(16, 1)

        loss = model.train_step(x, y, optimizer, criterion)

        assert isinstance(loss, float), f"Expected float, got {type(loss)}"
        assert loss >= 0.0, f"Loss should be non-negative: {loss}"

    def test_train_step_updates_parameters(self) -> None:
        """Test train_step actually updates model parameters."""
        torch.manual_seed(42)

        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.1)
        criterion = nn.MSELoss()

        # Get initial parameters
        initial_params = [p.clone() for p in model.parameters()]

        x = torch.randn(16, 4)
        y = torch.randn(16, 1)

        model.train_step(x, y, optimizer, criterion)

        # Check parameters changed
        params_changed = False
        for p_init, p_curr in zip(initial_params, model.parameters(), strict=False):
            if not torch.allclose(p_init, p_curr, atol=1e-8):
                params_changed = True
                break

        assert params_changed, "train_step should update parameters"

    def test_multiple_train_steps(self) -> None:
        """Test multiple train_step calls work correctly."""
        model = MyceliumFractalNet(input_dim=4, hidden_dim=32)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = nn.MSELoss()

        x = torch.randn(16, 4)
        y = torch.randn(16, 1)

        losses = []
        for _ in range(10):
            loss = model.train_step(x, y, optimizer, criterion)
            losses.append(loss)

        # All losses should be finite
        assert all(loss >= 0 and loss < float("inf") for loss in losses)
