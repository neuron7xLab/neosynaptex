import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from bnsyn.rng import seed_all
from bnsyn.sim.network import run_simulation


pytestmark = pytest.mark.property


@given(
    n=st.integers(min_value=10, max_value=500),
    dt=st.floats(min_value=0.001, max_value=1.0, allow_nan=False, allow_infinity=False),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
@settings(deadline=None)
def test_determinism_property_all_sizes(n: int, dt: float, seed: int) -> None:
    m1 = run_simulation(steps=100, dt_ms=dt, seed=seed, N=n)
    m2 = run_simulation(steps=100, dt_ms=dt, seed=seed, N=n)
    assert m1 == m2, f"Determinism failed for N={n}, dt={dt}, seed={seed}"


@given(seed=st.integers(min_value=0, max_value=2**31 - 2))
@settings(deadline=None)
def test_seed_controls_rng_stream(seed: int) -> None:
    rng_a = seed_all(seed).np_rng
    rng_b = seed_all(seed + 1).np_rng
    sample_a = rng_a.normal(size=5)
    sample_b = rng_b.normal(size=5)
    assert not (sample_a == sample_b).all(), "Different seeds must yield different RNG streams"
