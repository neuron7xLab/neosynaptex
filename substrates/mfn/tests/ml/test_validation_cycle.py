import pytest

pytest.importorskip("torch")

from mycelium_fractal_net import run_validation
from mycelium_fractal_net.model import ValidationConfig


def test_validation_cycle_produces_metrics() -> None:
    cfg = ValidationConfig(epochs=1, batch_size=4, grid_size=32, steps=16)
    metrics = run_validation(cfg)

    required_keys = {
        "loss_start",
        "loss_final",
        "loss_drop",
        "pot_min_mV",
        "pot_max_mV",
        "example_fractal_dim",
        "growth_events",
        "nernst_symbolic_mV",
        "nernst_numeric_mV",
    }
    assert required_keys.issubset(metrics.keys())

    assert metrics["loss_start"] >= 0.0
    assert metrics["loss_final"] >= 0.0
    assert metrics["pot_min_mV"] < metrics["pot_max_mV"]
    assert 0.0 <= metrics["example_fractal_dim"] <= 3.0
