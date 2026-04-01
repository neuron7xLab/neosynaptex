"""Signal preprocessing utilities for 1D inputs."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "Fractal1DPreprocessor",
    "OptimizedFractalDenoise1D",
]


def __getattr__(name: str):
    if name == "OptimizedFractalDenoise1D":
        value = getattr(import_module("mycelium_fractal_net.signal.denoise_1d"), name)
    elif name == "Fractal1DPreprocessor":
        value = getattr(import_module("mycelium_fractal_net.signal.preprocessor"), name)
    else:
        raise AttributeError(name)
    globals()[name] = value
    return value
