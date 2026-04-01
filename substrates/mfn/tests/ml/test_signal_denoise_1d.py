"""Tests for 1D fractal denoiser."""

from __future__ import annotations

import pytest

pytest.skip("signal module quarantined", allow_module_level=True)

import math

import numpy as np
import pytest

torch = pytest.importorskip("torch")
from hypothesis import given, settings
from hypothesis import strategies as st

from mycelium_fractal_net.signal import Fractal1DPreprocessor, OptimizedFractalDenoise1D

MODE_CONFIGS = [
    {},
    {
        "mode": "fractal",
        "population_size": 64,
        "range_size": 8,
        "iterations_fractal": 1,
    },
]

SPIKE_IMPROVEMENT_RATIO = 0.98  # require at least modest improvement on spikes
RANDOM_WALK_DRIFT_RATIO = 0.10  # allow at most 10% relative change on random walk
OSCILLATION_TOLERANCE = 1.05
MULTISCALE_SPIKE_TOLERANCE = 1.01


def _mse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean((a - b) ** 2))


@pytest.mark.parametrize(
    ("shape", "mode_kwargs"),
    [
        ((1024,), {}),
        ((1, 1024), {}),
        ((2, 3, 512), {}),
        ((1024,), {"mode": "fractal", "population_size": 32, "range_size": 8}),
        ((2, 3, 512), {"mode": "fractal", "population_size": 32, "range_size": 8}),
    ],
)
def test_shape_invariants(shape: tuple[int, ...], mode_kwargs: dict[str, object]) -> None:
    torch.manual_seed(123)
    np.random.seed(123)
    data = torch.randn(*shape)
    model = OptimizedFractalDenoise1D(**mode_kwargs)
    with torch.no_grad():
        out = model(data)
    assert out.shape == data.shape


@pytest.mark.parametrize("mode_kwargs", MODE_CONFIGS)
def test_outputs_finite(mode_kwargs: dict[str, object]) -> None:
    torch.manual_seed(7)
    np.random.seed(7)
    data = torch.randn(2, 3, 128)
    model = OptimizedFractalDenoise1D(**mode_kwargs)
    with torch.no_grad():
        out = model(data)
    assert torch.isfinite(out).all()


def test_fractal_do_no_harm_random_walk() -> None:
    torch.manual_seed(1)
    np.random.seed(1)
    rng = np.random.default_rng(1)

    steps = rng.normal(0.0, 0.1, size=256)
    base = np.cumsum(steps)
    noise = rng.normal(0.0, 0.05, size=256)
    noisy = base + noise

    model = OptimizedFractalDenoise1D(
        mode="fractal",
        population_size=32,
        range_size=8,
        iterations_fractal=1,
        overlap=False,
        do_no_harm=True,
        harm_ratio=0.90,
        s_max=0.5,
        s_threshold=0.01,
    )
    tensor = torch.tensor(noisy, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        denoised = model(tensor).squeeze(0).squeeze(0).cpu().numpy()

    mse_noisy = _mse(noisy, base)
    mse_denoised = _mse(denoised, base)
    assert mse_denoised <= mse_noisy * 1.10


def test_fractal_improves_spikes_mse() -> None:
    torch.manual_seed(0)
    np.random.seed(0)
    rng = np.random.default_rng(0)

    length = 256
    x = np.linspace(0, 2 * np.pi, length)
    base = 0.2 * np.sin(x)
    base[length // 3 : 2 * length // 3] += 0.5

    noisy = base + rng.normal(0.0, 0.05, size=length)
    spike_indices = rng.choice(length, size=10, replace=False)
    noisy[spike_indices] += rng.choice([-1.0, 1.0], size=10)

    model = OptimizedFractalDenoise1D(
        mode="fractal",
        population_size=64,
        range_size=8,
        iterations_fractal=1,
    )
    tensor = torch.tensor(noisy, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    with torch.no_grad():
        denoised = model(tensor).squeeze(0).squeeze(0).cpu().numpy()

    mse_noisy = _mse(noisy, base)
    mse_denoised = _mse(denoised, base)
    assert mse_denoised <= mse_noisy * SPIKE_IMPROVEMENT_RATIO
    assert np.isfinite(denoised).all()


def test_determinism_with_fixed_seed() -> None:
    params = {
        "mode": "fractal",
        "population_size": 64,
        "range_size": 8,
        "iterations_fractal": 2,
        "overlap": False,
    }
    torch.manual_seed(99)
    np.random.seed(99)
    data = torch.randn(1, 1, 128)
    model = OptimizedFractalDenoise1D(**params)
    with torch.no_grad():
        out1 = model(data).clone()

    torch.manual_seed(99)
    np.random.seed(99)
    data_repeat = torch.randn(1, 1, 128)
    model_repeat = OptimizedFractalDenoise1D(**params)
    with torch.no_grad():
        out2 = model_repeat(data_repeat).clone()

    assert torch.equal(out1, out2)


@pytest.mark.parametrize("mode_kwargs", MODE_CONFIGS)
@settings(max_examples=15, deadline=None)
@given(
    batch=st.integers(min_value=1, max_value=2),
    channels=st.integers(min_value=1, max_value=3),
    length=st.integers(min_value=32, max_value=96),
)
def test_denoiser_property_same_shape_and_finite(
    mode_kwargs: dict[str, object],
    batch: int,
    channels: int,
    length: int,
) -> None:
    torch.manual_seed(42)
    np.random.seed(42)
    data = torch.randn(batch, channels, length)
    model = OptimizedFractalDenoise1D(**mode_kwargs)
    with torch.no_grad():
        out = model(data)
    assert out.shape == data.shape
    assert torch.isfinite(out).all()


def test_basal_ganglia_inhibits_high_complexity() -> None:
    torch.manual_seed(1234)
    data = torch.randn(1, 1, 128)
    model = OptimizedFractalDenoise1D(
        mode="fractal",
        population_size=16,
        range_size=8,
        iterations_fractal=1,
        fractal_dim_threshold=-0.5,  # force inhibition for typical signals
    )
    with torch.no_grad():
        out = model(data)
    assert torch.allclose(out, data, atol=0.0, rtol=0.0)


def test_mutual_information_is_tracked() -> None:
    torch.manual_seed(5)
    data = torch.randn(1, 1, 96)
    model = OptimizedFractalDenoise1D(
        mode="fractal",
        population_size=16,
        range_size=8,
        iterations_fractal=1,
    )
    with torch.no_grad():
        _ = model(data)
    assert model.last_mutual_information is not None
    assert math.isfinite(model.last_mutual_information)
    assert model.last_mutual_information >= 0.0


def test_recursive_energy_stability() -> None:
    torch.manual_seed(11)
    np.random.seed(11)
    length = 256
    base = torch.linspace(-1.0, 1.0, steps=length, dtype=torch.float64).unsqueeze(0).unsqueeze(0)
    noise = 0.05 * torch.randn_like(base)
    sinusoid = torch.sin(torch.linspace(0, 4 * np.pi, length, dtype=torch.float64)).view(1, 1, -1)
    signal = base + noise + 0.2 * sinusoid

    kernel = torch.tensor([[[0.25, 0.5, 0.25]]], dtype=torch.float64)
    baseline = torch.nn.functional.conv1d(signal, kernel, padding=1)

    model = OptimizedFractalDenoise1D(
        mode="fractal",
        population_size=16,
        range_size=8,
        iterations_fractal=1,
        acceptor_iterations=7,
        do_no_harm=True,
    )

    with torch.no_grad():
        first_pass = model._denoise_fractal(signal, canonical=False)
        recursive = signal
        for _ in range(4):
            recursive = model._denoise_fractal(recursive, canonical=False)

    def energy(t: torch.Tensor) -> torch.Tensor:
        return torch.mean((t - baseline) ** 2)

    tolerance = 5e-5
    assert energy(recursive) <= energy(first_pass) + tolerance
    assert torch.max(torch.abs(recursive)) <= torch.max(torch.abs(signal)) * 2.0


def test_cfde_recursive_monotonic_energy() -> None:
    torch.manual_seed(21)
    np.random.seed(21)

    length = 256
    ramp = torch.linspace(-0.4, 0.2, steps=length // 2, dtype=torch.float64)
    slope = torch.linspace(0.2, 0.5, steps=length - length // 2, dtype=torch.float64)
    base = torch.cat([ramp, slope]).unsqueeze(0).unsqueeze(0)
    noise = 0.02 * torch.randn_like(base)
    signal = base + noise

    kernel = torch.ones((1, 1, 5), dtype=torch.float64) / 5.0
    baseline = torch.nn.functional.conv1d(signal, kernel, padding=2)

    model = OptimizedFractalDenoise1D(
        mode="fractal",
        population_size=16,
        range_size=8,
        iterations_fractal=1,
        s_max=0.8,
        s_threshold=0.01,
        overlap=True,
        log_mutual_information=False,
    )

    with torch.no_grad():
        first_pass = model._denoise_fractal(signal, canonical=False)
        recursive = signal
        for _ in range(3):
            recursive = model._denoise_fractal(recursive, canonical=False)

    def energy(t: torch.Tensor) -> torch.Tensor:
        return torch.mean((t - baseline) ** 2)

    tolerance = 1e-4
    assert energy(recursive) <= energy(first_pass) + tolerance
    assert torch.max(torch.abs(recursive)) <= torch.max(torch.abs(signal)) * 2.0


def test_cfde_return_stats_multiscale_mode() -> None:
    torch.manual_seed(2)
    np.random.seed(2)
    data = torch.randn(1, 1, 80)
    model = OptimizedFractalDenoise1D(
        mode="fractal",
        cfde_mode="multiscale",
        population_size=32,
        range_size=8,
        iterations_fractal=1,
        log_mutual_information=False,
    )
    with torch.no_grad():
        out, stats = model(data, return_stats=True)  # type: ignore[misc]
    assert out.shape == data.shape
    assert {
        "inhibition_rate",
        "reconstruction_mse",
        "baseline_mse",
        "effective_iterations",
    }.issubset(stats.keys())
    assert 0.0 <= stats["inhibition_rate"] <= 1.0
    assert stats["effective_iterations"] >= 1.0
    assert math.isfinite(stats["reconstruction_mse"])
    assert math.isfinite(stats["baseline_mse"])


def test_fractal_bounded_oscillation_across_iterations() -> None:
    torch.manual_seed(33)
    np.random.seed(33)
    data = torch.randn(1, 1, 96, dtype=torch.float64)
    model = OptimizedFractalDenoise1D(
        mode="fractal",
        population_size=24,
        range_size=8,
        iterations_fractal=1,
        log_mutual_information=False,
    )
    with torch.no_grad():
        iter1 = model._denoise_fractal(data, canonical=False)
        iter2 = model._denoise_fractal(iter1, canonical=False)
        iter3 = model._denoise_fractal(iter2, canonical=False)

    def diff_energy(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return torch.mean((a - b) ** 2)

    assert diff_energy(iter2, iter1) <= diff_energy(iter1, data) * OSCILLATION_TOLERANCE
    assert diff_energy(iter3, iter2) <= diff_energy(iter2, iter1) * OSCILLATION_TOLERANCE


def test_preprocessor_can_return_stats() -> None:
    torch.manual_seed(14)
    np.random.seed(14)
    series = torch.randn(128, dtype=torch.float32)
    preprocessor = Fractal1DPreprocessor(preset="generic")
    with torch.no_grad():
        out, stats = preprocessor(series, return_stats=True)  # type: ignore[misc]
    assert out.shape == series.shape
    assert "effective_iterations" in stats


def _proxy_mse(output: np.ndarray, reference: np.ndarray, window: int = 5) -> float:
    """Compute proxy MSE against a local-mean baseline."""
    kernel = np.ones(window) / float(window)
    baseline = np.convolve(reference, kernel, mode="same")
    return _mse(output, baseline)


def test_multiscale_shape_and_determinism() -> None:
    torch.manual_seed(2024)
    np.random.seed(2024)
    shapes = [(128,), (2, 128), (2, 3, 96)]
    params = {
        "mode": "fractal",
        "cfde_mode": "multiscale",
        "range_size": 8,
        "population_size": 120,
        "iterations_fractal": 2,
        "multiscale_range_sizes": (8, 16, 32),
        "multiscale_aggregate": "best",
        "log_mutual_information": False,
    }

    for shape in shapes:
        torch.manual_seed(7)
        np.random.seed(7)
        data = torch.randn(*shape)
        model = OptimizedFractalDenoise1D(**params)
        with torch.no_grad():
            first = model(data)

        torch.manual_seed(7)
        np.random.seed(7)
        data_repeat = torch.randn(*shape)
        model_repeat = OptimizedFractalDenoise1D(**params)
        with torch.no_grad():
            second = model_repeat(data_repeat)

        assert torch.equal(first, second)
        assert first.shape == data.shape


def test_multiscale_not_worse_than_single_on_spikes() -> None:
    torch.manual_seed(515)
    np.random.seed(515)
    rng = np.random.default_rng(515)
    length = 512
    base = np.linspace(-0.2, 0.4, length)
    base[length // 4 : length // 2] += 0.3
    base[length // 2 :] -= 0.15
    noisy = base + rng.normal(0.0, 0.05, size=length)
    spike_indices = rng.choice(length, size=20, replace=False)
    noisy[spike_indices] += rng.normal(0.8, 0.1, size=20) * rng.choice([-1.0, 1.0], size=20)

    tensor = torch.tensor(noisy, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    single = OptimizedFractalDenoise1D(
        mode="fractal",
        cfde_mode="single",
        population_size=120,
        range_size=8,
        iterations_fractal=2,
        log_mutual_information=False,
    )
    multiscale = OptimizedFractalDenoise1D(
        mode="fractal",
        cfde_mode="multiscale",
        population_size=120,
        range_size=8,
        iterations_fractal=2,
        multiscale_range_sizes=(8, 16, 32),
        multiscale_aggregate="best",
        log_mutual_information=False,
    )

    with torch.no_grad():
        out_single = single(tensor).squeeze(0).squeeze(0).cpu().numpy()
        out_multi = multiscale(tensor).squeeze(0).squeeze(0).cpu().numpy()

    proxy_single = _proxy_mse(out_single, noisy)
    proxy_multi = _proxy_mse(out_multi, noisy)
    assert proxy_multi <= proxy_single * MULTISCALE_SPIKE_TOLERANCE
