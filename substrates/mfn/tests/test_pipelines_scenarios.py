"""Tests for the scenarios data pipeline helpers."""

from __future__ import annotations

import numpy as np

from mycelium_fractal_net.pipelines.scenarios import (
    ScenarioConfig,
    _generate_param_configs,
)


def test_generate_param_configs_uses_rng_for_shuffling() -> None:
    """Providing an RNG should change the ordering without changing seeds."""

    config = ScenarioConfig(
        name="test",
        num_samples=4,
        seeds_per_config=1,
        alpha_values=[0.1, 0.2],
    )

    rng = np.random.default_rng(123)
    configs = _generate_param_configs(config, rng=rng)

    sim_ids = [cfg["sim_id"] for cfg in configs]
    seeds = [cfg["random_seed"] for cfg in configs]

    # All simulations should still be present but in a shuffled order
    assert set(sim_ids) == {0, 1, 2, 3}
    assert sim_ids != sorted(sim_ids)

    # The seeds remain tied to sim_id even after shuffling
    assert seeds == [config.base_seed + sim_id for sim_id in sim_ids]
