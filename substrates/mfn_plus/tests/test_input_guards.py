"""Security tests for input guards — adversarial inputs must be caught at the gate."""

from __future__ import annotations

import numpy as np
import pytest

from mycelium_fractal_net.core.input_guards import (
    ValidationError,
    safe_json_value,
    validate_field,
    validate_field_sequence,
)

# ── validate_field ───────────────────────────────────────────────────────────


def test_valid_field() -> None:
    validate_field(np.ones((16, 16)))


def test_nan_field_rejected() -> None:
    f = np.ones((8, 8))
    f[3, 3] = float("nan")
    with pytest.raises(ValidationError, match="NaN"):
        validate_field(f)


def test_inf_field_rejected() -> None:
    f = np.ones((8, 8))
    f[0, 0] = float("inf")
    with pytest.raises(ValidationError, match="Inf"):
        validate_field(f)


def test_non_square_rejected() -> None:
    with pytest.raises(ValidationError, match="square"):
        validate_field(np.ones((8, 16)))


def test_1d_rejected() -> None:
    with pytest.raises(ValidationError, match="2D"):
        validate_field(np.ones(64))


def test_too_small_rejected() -> None:
    with pytest.raises(ValidationError, match="too small"):
        validate_field(np.ones((1, 1)))


def test_too_large_rejected() -> None:
    with pytest.raises(ValidationError, match="too large"):
        validate_field(np.ones((2048, 2048)))


def test_not_ndarray_rejected() -> None:
    with pytest.raises(ValidationError, match="ndarray"):
        validate_field([[1, 2], [3, 4]])  # type: ignore[arg-type]


# ── validate_field_sequence ──────────────────────────────────────────────────


def test_valid_sequence() -> None:
    import mycelium_fractal_net as mfn

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=0))
    validate_field_sequence(seq)


def test_sequence_nan_history() -> None:
    import mycelium_fractal_net as mfn

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=0))
    # Inject NaN into history
    seq.history[5, 3, 3] = float("nan")
    with pytest.raises(ValidationError, match="NaN"):
        validate_field_sequence(seq)


def test_sequence_missing_field() -> None:
    class NoField:
        pass

    with pytest.raises(ValidationError, match="missing"):
        validate_field_sequence(NoField())


# ── UnifiedEngine rejects bad input ──────────────────────────────────────────


def test_unified_engine_rejects_nan() -> None:
    import mycelium_fractal_net as mfn
    from mycelium_fractal_net.core.unified_engine import UnifiedEngine

    seq = mfn.simulate(mfn.SimulationSpec(grid_size=8, steps=10, seed=0))
    seq.field[0, 0] = float("nan")
    with pytest.raises(ValidationError, match="NaN"):
        UnifiedEngine().analyze(seq)


# ── safe_json_value ──────────────────────────────────────────────────────────


def test_safe_json_nan() -> None:
    assert safe_json_value(float("nan")) is None


def test_safe_json_inf() -> None:
    assert safe_json_value(float("inf")) is None


def test_safe_json_normal() -> None:
    assert safe_json_value(3.14) == 3.14


def test_safe_json_string() -> None:
    assert safe_json_value("hello") == "hello"
