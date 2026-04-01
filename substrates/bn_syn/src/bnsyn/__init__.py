"""BN-Syn package entry point and version metadata.

Parameters
----------
None

Returns
-------
None

Notes
-----
This module exposes the package version and provides top-level access to
core configuration and RNG utilities without modifying simulation behavior.

References
----------
docs/SPEC.md
"""

from __future__ import annotations

from importlib import metadata

from bnsyn.api import phase_atlas, run, sleep_stack

try:
    __version__ = metadata.version("bnsyn")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = ["__version__", "rng", "config", "neurons", "synapses", "control", "simulation", "run", "phase_atlas", "sleep_stack"]
