import pytest

pytest.importorskip("torch")

from mycelium_fractal_net import run_validation
from mycelium_fractal_net.model import ValidationConfig


def test_determinism_with_same_seed() -> None:
    cfg = ValidationConfig(seed=123, epochs=1, batch_size=4, grid_size=32, steps=16)

    m1 = run_validation(cfg)
    m2 = run_validation(cfg)

    # Дозволяємо мінімальні відмінності через floating-point, порівнюємо ключові метрики
    for key in ("loss_start", "loss_final", "example_fractal_dim"):
        assert abs(m1[key] - m2[key]) < 1e-6
