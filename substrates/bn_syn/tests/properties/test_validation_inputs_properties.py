"""Property tests for input validation utilities."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bnsyn.validation.inputs import validate_state_vector


@pytest.mark.property
@settings(derandomize=True, max_examples=60, deadline=None)
@given(
    n_neurons=st.integers(min_value=1, max_value=64),
    bad_index=st.integers(min_value=0, max_value=63),
    bad_value=st.sampled_from([np.nan, np.inf, -np.inf]),
)
def test_state_validator_property_rejects_non_finite(
    n_neurons: int,
    bad_index: int,
    bad_value: float,
) -> None:
    vec = np.zeros(n_neurons, dtype=np.float64)
    vec[bad_index % n_neurons] = bad_value
    with pytest.raises(ValueError, match="contains"):
        validate_state_vector(vec, n_neurons=n_neurons)
