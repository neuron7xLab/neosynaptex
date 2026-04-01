"""Tests for mfn.inverse_synthesis() — reverse parameter synthesis."""

from __future__ import annotations

import mycelium_fractal_net as mfn
from mycelium_fractal_net.types.field import SimulationSpec
from mycelium_fractal_net.types.inverse import InverseSynthesisResult


def test_inverse_result_type() -> None:
    result = mfn.inverse_synthesis(
        "approaching_transition",
        0.5,
        grid_size=16,
        steps=30,
        max_iterations=5,
    )
    assert isinstance(result, InverseSynthesisResult)
    assert isinstance(result.found, bool)
    assert isinstance(result.synthesized_spec, SimulationSpec)


def test_inverse_synthesized_spec_is_valid() -> None:
    result = mfn.inverse_synthesis(
        "stable",
        0.1,
        grid_size=16,
        steps=30,
        max_iterations=5,
    )
    spec = result.synthesized_spec
    assert 4 <= spec.grid_size <= 512
    assert spec.steps >= 1
    assert 0.0 < spec.alpha <= 0.25


def test_inverse_to_dict() -> None:
    result = mfn.inverse_synthesis(
        "approaching_transition",
        0.5,
        grid_size=16,
        steps=30,
        max_iterations=3,
    )
    d = result.to_dict()
    assert d["schema_version"] == "mfn-inverse-synthesis-v1"
    assert "found" in d
    assert "achieved_transition_type" in d
    assert "synthesized_spec" in d


def test_inverse_summary() -> None:
    result = mfn.inverse_synthesis(
        "approaching_transition",
        0.5,
        grid_size=16,
        steps=30,
        max_iterations=3,
    )
    s = result.summary()
    assert "[INVERSE:" in s


def test_inverse_search_trajectory() -> None:
    result = mfn.inverse_synthesis(
        "approaching_transition",
        0.5,
        grid_size=16,
        steps=30,
        max_iterations=5,
    )
    assert len(result.search_trajectory) >= 1
    for entry in result.search_trajectory:
        assert "params" in entry
        assert "objective" in entry


def test_inverse_deterministic() -> None:
    r1 = mfn.inverse_synthesis(
        "stable",
        0.1,
        grid_size=16,
        steps=30,
        max_iterations=3,
        seed=42,
    )
    r2 = mfn.inverse_synthesis(
        "stable",
        0.1,
        grid_size=16,
        steps=30,
        max_iterations=3,
        seed=42,
    )
    assert r1.achieved_ews_score == r2.achieved_ews_score
    assert r1.objective_value == r2.objective_value
