"""Tests for input validation utilities."""

from __future__ import annotations

import numpy as np
import pytest

from bnsyn.validation.inputs import (
    validate_connectivity_matrix,
    validate_spike_array,
    validate_state_vector,
)


def test_validate_state_vector_type_and_dtype() -> None:
    with pytest.raises(TypeError, match="expected ndarray"):
        validate_state_vector([1, 2, 3], n_neurons=3, name="state")

    with pytest.raises(ValueError, match="expected dtype float64"):
        validate_state_vector(np.array([1, 2, 3], dtype=np.float32), n_neurons=3, name="state")


def test_validate_state_vector_shape_and_nan() -> None:
    with pytest.raises(ValueError, match="expected shape"):
        validate_state_vector(np.zeros((2, 2), dtype=np.float64), n_neurons=3, name="state")

    with pytest.raises(ValueError, match="contains NaN"):
        validate_state_vector(np.array([0.0, np.nan], dtype=np.float64), n_neurons=2, name="state")


def test_validate_state_vector_rejects_infinite_values() -> None:
    with pytest.raises(ValueError, match="contains non-finite values"):
        validate_state_vector(np.array([0.0, np.inf], dtype=np.float64), n_neurons=2, name="state")


def test_validate_spike_array_dtype_and_shape() -> None:
    with pytest.raises(ValueError, match="expected dtype bool"):
        validate_spike_array(np.array([0, 1], dtype=np.int32), n_neurons=2, name="spikes")

    with pytest.raises(ValueError, match="expected shape"):
        validate_spike_array(np.array([[True, False]]), n_neurons=2, name="spikes")


def test_validate_connectivity_matrix_dtype_shape_nan() -> None:
    with pytest.raises(ValueError, match="expected dtype float64"):
        validate_connectivity_matrix(
            np.array([[1, 2]], dtype=np.float32), shape=(1, 2), name="conn"
        )

    with pytest.raises(ValueError, match="expected shape"):
        validate_connectivity_matrix(
            np.array([[1.0, 2.0]], dtype=np.float64), shape=(2, 1), name="conn"
        )

    with pytest.raises(ValueError, match="contains NaN"):
        validate_connectivity_matrix(
            np.array([[np.nan]], dtype=np.float64), shape=(1, 1), name="conn"
        )


def test_validate_connectivity_matrix_rejects_infinite_values() -> None:
    with pytest.raises(ValueError, match="contains non-finite values"):
        validate_connectivity_matrix(
            np.array([[1.0, -np.inf]], dtype=np.float64), shape=(1, 2), name="conn"
        )


def test_state_validator_fuzz_entrypoint_fast() -> None:
    """Bounded fuzz-style regression entrypoint for API boundary validation."""
    rng = np.random.default_rng(20260205)
    for _ in range(100):
        size = int(rng.integers(1, 48))
        vec = rng.standard_normal(size).astype(np.float64)
        coin = int(rng.integers(0, 5))
        if coin == 0:
            vec[int(rng.integers(0, size))] = np.nan
            with pytest.raises(ValueError, match="contains NaN"):
                validate_state_vector(vec, n_neurons=size)
        elif coin == 1:
            vec[int(rng.integers(0, size))] = np.inf
            with pytest.raises(ValueError, match="contains non-finite values"):
                validate_state_vector(vec, n_neurons=size)
        else:
            validate_state_vector(vec, n_neurons=size)
