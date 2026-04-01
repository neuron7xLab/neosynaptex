"""Compatibility shim for legacy experiments.generate_dataset."""

from warnings import warn

from mycelium_fractal_net.experiments.generate_dataset import *  # noqa: F401,F403

warn(
    "Importing root-level 'experiments.generate_dataset' is deprecated; use 'mycelium_fractal_net.experiments.generate_dataset' instead.",
    DeprecationWarning,
    stacklevel=2,
)
