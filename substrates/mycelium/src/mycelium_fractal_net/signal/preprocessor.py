"""Preprocessing pipeline for 1D signals."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict, cast

from mycelium_fractal_net._optional import require_ml_dependency

torch = require_ml_dependency("torch")
nn = torch.nn

from .denoise_1d import OptimizedFractalDenoise1D, _canonicalize_1d

if TYPE_CHECKING:
    from collections.abc import Mapping


class _PresetConfig(TypedDict):
    mode: Literal["multiscale", "fractal"]
    cfde_mode: Literal["single", "multiscale"]
    multiscale_range_sizes: tuple[int, ...] | None
    multiscale_aggregate: Literal["best", "weighted"]
    base_window: int
    trend_scaling: float
    detail_preservation: float
    spike_threshold: float
    spike_damping: float
    iterations: int
    range_size: int
    domain_scale: int
    population_size: int
    iterations_fractal: int
    s_threshold: float
    s_max: float
    overlap: bool
    smooth_kernel: int
    normalize: bool
    center: bool
    post_gain: float


class Fractal1DPreprocessor(nn.Module):
    """Preset-driven 1D preprocessing with fractal denoising."""

    _PRESETS: Mapping[
        Literal["generic", "markets", "ecg"],
        _PresetConfig,
    ] = {
        "generic": {
            "mode": "multiscale",
            "cfde_mode": "single",
            "multiscale_range_sizes": None,
            "multiscale_aggregate": "best",
            "base_window": 5,
            "trend_scaling": 0.55,
            "detail_preservation": 0.88,
            "spike_threshold": 3.5,
            "spike_damping": 0.4,
            "iterations": 2,
            "range_size": 8,
            "domain_scale": 4,
            "population_size": 96,
            "iterations_fractal": 1,
            "s_threshold": 1e-3,
            "s_max": 1.0,
            "overlap": True,
            "smooth_kernel": 5,
            "normalize": True,
            "center": True,
            "post_gain": 1.0,
        },
        "markets": {
            "mode": "fractal",
            "cfde_mode": "single",
            "multiscale_range_sizes": None,
            "multiscale_aggregate": "best",
            "base_window": 7,
            "trend_scaling": 0.6,
            "detail_preservation": 0.85,
            "spike_threshold": 3.2,
            "spike_damping": 0.35,
            "iterations": 2,
            "range_size": 16,
            "domain_scale": 8,
            "population_size": 96,
            "iterations_fractal": 1,
            "s_threshold": 1e-3,
            "s_max": 0.85,
            "overlap": True,
            "smooth_kernel": 7,
            "normalize": True,
            "center": True,
            "post_gain": 1.0,
        },
        "ecg": {
            "mode": "fractal",
            "cfde_mode": "single",
            "multiscale_range_sizes": None,
            "multiscale_aggregate": "best",
            "base_window": 5,
            "trend_scaling": 0.5,
            "detail_preservation": 0.9,
            "spike_threshold": 3.0,
            "spike_damping": 0.3,
            "iterations": 3,
            "range_size": 8,
            "domain_scale": 6,
            "population_size": 64,
            "iterations_fractal": 1,
            "s_threshold": 1e-3,
            "s_max": 0.9,
            "overlap": False,
            "smooth_kernel": 5,
            "normalize": True,
            "center": True,
            "post_gain": 1.0,
        },
    }

    def __init__(
        self,
        preset: Literal["generic", "markets", "ecg"] = "generic",
        *,
        cfde_mode: Literal["single", "multiscale"] | None = None,
        scales: tuple[int, ...] | None = None,
        aggregate: Literal["best", "weighted"] | None = None,
    ) -> None:
        super().__init__()
        if preset not in self._PRESETS:
            available = ", ".join(self._PRESETS.keys())
            raise ValueError(f"Unsupported preset: {preset}. Available presets: {available}")

        cfg = self._PRESETS[preset]
        self.normalize = cfg["normalize"]
        self.center = cfg["center"]
        self.post_gain = cfg["post_gain"]
        self._eps = 1e-6

        self.denoiser = OptimizedFractalDenoise1D(
            base_window=cfg["base_window"],
            trend_scaling=cfg["trend_scaling"],
            detail_preservation=cfg["detail_preservation"],
            spike_threshold=cfg["spike_threshold"],
            spike_damping=cfg["spike_damping"],
            iterations=cfg["iterations"],
            mode=cfg["mode"],
            cfde_mode=cfde_mode or cfg["cfde_mode"],
            multiscale_range_sizes=scales or cfg["multiscale_range_sizes"],
            multiscale_aggregate=aggregate or cfg["multiscale_aggregate"],
            range_size=cfg["range_size"],
            domain_scale=cfg["domain_scale"],
            population_size=cfg["population_size"],
            iterations_fractal=cfg["iterations_fractal"],
            s_threshold=cfg["s_threshold"],
            s_max=cfg["s_max"],
            overlap=cfg["overlap"],
            smooth_kernel=cfg["smooth_kernel"],
        )

    def forward(
        self,
        x: torch.Tensor,
        *,
        return_stats: bool = False,
        debug: bool | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, dict[str, float]]:
        """Run preset preprocessing pipeline."""
        canonical, reshape, original_dtype = _canonicalize_1d(x)
        processed = canonical.to(torch.float32)

        if self.center:
            processed = processed - processed.mean(dim=-1, keepdim=True)

        denoised = self.denoiser(processed, return_stats=return_stats, debug=debug)
        stats: dict[str, float] | None = None
        if return_stats:
            processed, stats = cast("tuple[torch.Tensor, dict[str, float]]", denoised)
        else:
            processed = cast("torch.Tensor", denoised)

        if self.normalize:
            mean = processed.mean(dim=-1, keepdim=True)
            std = processed.std(dim=-1, keepdim=True).clamp_min(self._eps)
            processed = (processed - mean) / std

        if self.post_gain != 1.0:
            processed = processed * self.post_gain

        output = reshape(processed).to(original_dtype)
        if return_stats:
            default_stats = self.denoiser._empty_stats()
            return output, stats or default_stats
        return output
