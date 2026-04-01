"""Tests for NFI public API — importability, quick-start, validation.

Ref: Vasylenko (2026)
"""

from __future__ import annotations

import pytest


def test_root_import_nfi_symbols():
    """All NFI symbols importable from root package."""
    from mycelium_fractal_net import (
        AdaptiveRunResult,
        EmergentValidationSuite,
        GammaEmergenceProbe,
        NFIAdaptiveLoop,
        NFIClosureLoop,
        NFIStateContract,
        ThetaMapping,
    )

    assert NFIAdaptiveLoop is not None
    assert NFIClosureLoop is not None
    assert NFIStateContract is not None
    assert GammaEmergenceProbe is not None
    assert EmergentValidationSuite is not None
    assert AdaptiveRunResult is not None
    assert ThetaMapping is not None


def test_nfi_subpackage_import():
    """Direct nfi subpackage import works."""
    from mycelium_fractal_net.nfi import (
        CA1TemporalBuffer,
        GammaEmergenceProbe,
        GammaEmergenceReport,
        NFIAdaptiveLoop,
        NFIClosureLoop,
        NFIStateContract,
        TemporalSummary,
        ThetaMapping,
        ValidationReport,
    )

    assert GammaEmergenceReport is not None
    assert CA1TemporalBuffer is not None
    assert TemporalSummary is not None
    assert ValidationReport is not None


def test_adaptive_loop_five_steps():
    """NFIAdaptiveLoop runs 5 steps without error."""
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.nfi import NFIAdaptiveLoop

    base = mfn.SimulationSpec(grid_size=32, steps=30, seed=42)
    loop = NFIAdaptiveLoop(base_spec=base)
    result = loop.run(n_steps=5)

    assert len(result.contracts) == 5
    assert len(result.specs_history) == 5
    assert len(result.coherence_trace) == 5
    assert len(result.alpha_trace) == 5
    assert all(0.0 < a <= 0.25 for a in result.alpha_trace)
    assert result.gamma_report is not None


def test_validation_suite_does_not_throw():
    """EmergentValidationSuite runs without exceptions (results may vary)."""
    from mycelium_fractal_net.nfi import EmergentValidationSuite

    suite = EmergentValidationSuite(
        n_healthy=12,
        n_pathological=10,
        n_transition=10,
        n_bootstrap=100,
    )
    report = suite.run()

    assert report.healthy_result is not None
    assert report.pathological_result is not None
    assert report.transition_result is not None
    assert isinstance(report.failures, list)


def test_docstring_quickstart_executes():
    """The quick-start example from nfi/__init__.py docstring works."""
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.nfi import GammaEmergenceProbe, NFIAdaptiveLoop

    loop = NFIAdaptiveLoop(base_spec=mfn.SimulationSpec(grid_size=32, steps=40))
    result = loop.run(n_steps=10)

    probe = GammaEmergenceProbe()
    report = probe.analyze(result.contracts)

    assert report.label in ("EMERGENT", "NOT_EMERGED", "INSUFFICIENT_DATA")
