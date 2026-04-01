"""Core smoke test — verifies simulate/extract/detect/forecast work without optional deps.

This test imports only core modules and verifies the minimal pipeline works.
It should pass in a clean environment with only core dependencies:
numpy, sympy, pydantic, cryptography.
"""

from __future__ import annotations

import numpy as np


def test_core_import() -> None:
    """Core module imports without optional deps."""
    import mycelium_fractal_net as mfn

    assert hasattr(mfn, "simulate")
    assert hasattr(mfn, "extract")
    assert hasattr(mfn, "detect")
    assert hasattr(mfn, "forecast")
    assert hasattr(mfn, "compare")


def test_core_simulate() -> None:
    """Simulate produces a valid FieldSequence."""
    from mycelium_fractal_net import SimulationSpec, simulate

    spec = SimulationSpec(grid_size=16, steps=8, seed=42)
    seq = simulate(spec)
    assert seq.field.shape == (16, 16)
    assert np.isfinite(seq.field).all()


def test_core_extract() -> None:
    """Extract produces a MorphologyDescriptor."""
    from mycelium_fractal_net import SimulationSpec, extract, simulate

    seq = simulate(SimulationSpec(grid_size=16, steps=8, seed=42))
    desc = extract(seq)
    assert desc is not None
    assert hasattr(desc, "version")


def test_core_detect() -> None:
    """Detect produces an AnomalyEvent."""
    from mycelium_fractal_net import SimulationSpec, detect, simulate

    seq = simulate(SimulationSpec(grid_size=16, steps=8, seed=42))
    event = detect(seq)
    assert event is not None
    assert hasattr(event, "score")
    assert 0.0 <= event.score <= 1.0


def test_core_forecast() -> None:
    """Forecast produces a ForecastResult."""
    from mycelium_fractal_net import SimulationSpec, forecast, simulate

    seq = simulate(SimulationSpec(grid_size=16, steps=8, seed=42))
    result = forecast(seq)
    assert result is not None
    assert hasattr(result, "horizon")
