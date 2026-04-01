import pytest

from bnsyn.rng import seed_all, split


@pytest.mark.validation
def test_rng_split_is_repeatable() -> None:
    pack = seed_all(123)
    gens = split(pack.np_rng, 3)
    pack2 = seed_all(123)
    gens2 = split(pack2.np_rng, 3)
    assert gens[0].integers(0, 1000) == gens2[0].integers(0, 1000)
