"""Compatibility shim for legacy experiments imports."""

from warnings import warn

from mycelium_fractal_net.experiments import (
    ConfigSampler,
    SweepConfig,
    generate_dataset,
    to_record,
)

warn(
    "Importing root-level 'experiments' is deprecated; use 'mycelium_fractal_net.experiments' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ConfigSampler", "SweepConfig", "generate_dataset", "to_record"]
