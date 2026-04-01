"""Backward-compatible re-export from decomposed model_pkg.

Original model.py (1329 LOC) has been split into:
- model_pkg/biophysics.py    (433 LOC) — Nernst, IFS, Lyapunov, simulation, fractal
- model_pkg/components.py    (284 LOC) — STDPPlasticity, SparseAttention
- model_pkg/aggregation.py   (280 LOC) — HierarchicalKrumAggregator
- model_pkg/network.py       (362 LOC) — MyceliumFractalNet, validation

All imports from mycelium_fractal_net.model continue to work.
"""

from mycelium_fractal_net.model_pkg import *  # noqa: F403
from mycelium_fractal_net.model_pkg import __all__  # noqa: F401
