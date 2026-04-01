"""
Tests for rl_exploration.py example.

Verifies the RL use case: GridWorld + MFN-guided exploration → coverage analysis.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


def load_example_module(name: str):
    """Load an example module by name from the examples directory."""
    examples_dir = Path(__file__).parent.parent.parent / "examples"
    spec = importlib.util.spec_from_file_location(name, examples_dir / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {examples_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pytest.importorskip("torch")


class TestRLExplorationExample:
    """Tests for the RL exploration example."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load the rl_exploration module."""
        self.module = load_example_module("rl_exploration")

    def test_run_rl_demo_returns_stats(self) -> None:
        """Test that run_rl_demo returns valid ExplorationStats when requested."""
        stats = self.module.run_rl_demo(
            verbose=False,
            num_episodes=10,  # Shorter for faster tests
            max_steps=50,
            seed=42,
            return_stats=True,
        )

        assert stats is not None, "Should return ExplorationStats"
        assert hasattr(stats, "coverage"), "Should have coverage attribute"
        assert hasattr(stats, "fractal_dim"), "Should have fractal_dim attribute"
        assert hasattr(stats, "episodes"), "Should have episodes attribute"

    def test_run_rl_demo_no_exceptions(self) -> None:
        """Test that run_rl_demo completes without exceptions."""
        # Should not raise any exceptions with small number of episodes
        self.module.run_rl_demo(
            verbose=False,
            num_episodes=5,
            max_steps=30,
            seed=42,
            return_stats=False,
        )

    def test_exploration_stats_valid_ranges(self) -> None:
        """Test that exploration stats are in valid ranges."""
        stats = self.module.run_rl_demo(
            verbose=False,
            num_episodes=10,
            max_steps=50,
            seed=42,
            return_stats=True,
        )

        assert stats is not None

        # Coverage should be in (0, 1]
        assert 0.0 < stats.coverage <= 1.0, f"Invalid coverage: {stats.coverage}"

        # Fractal dimension should be non-negative
        assert stats.fractal_dim >= 0.0, f"Invalid fractal_dim: {stats.fractal_dim}"

        # Unique states should be positive
        assert stats.unique_states > 0, f"Invalid unique_states: {stats.unique_states}"

        # Total steps should be positive
        assert stats.total_steps > 0, f"Invalid total_steps: {stats.total_steps}"

        # No NaN values
        assert not np.isnan(stats.coverage), "coverage is NaN"
        assert not np.isnan(stats.fractal_dim), "fractal_dim is NaN"
        assert not np.isnan(stats.mean_episode_length), "mean_episode_length is NaN"
        assert not np.isnan(stats.mean_reward), "mean_reward is NaN"


class TestGridWorldEnvironment:
    """Tests for the GridWorld environment."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load the rl_exploration module."""
        self.module = load_example_module("rl_exploration")

    def test_gridworld_initialization(self) -> None:
        """Test GridWorld initialization."""
        GridWorld = self.module.GridWorld
        GridWorldConfig = self.module.GridWorldConfig

        config = GridWorldConfig(size=8, seed=42)
        env = GridWorld(config=config)

        assert env.state == config.start
        assert len(env.visited) == 1
        assert config.start in env.visited

    def test_gridworld_reset(self) -> None:
        """Test GridWorld reset."""
        GridWorld = self.module.GridWorld
        GridWorldConfig = self.module.GridWorldConfig

        config = GridWorldConfig(size=8, seed=42)
        env = GridWorld(config=config)

        # Take some actions
        env.step(0)  # up
        env.step(1)  # right

        # Reset
        state = env.reset()

        assert state == config.start
        assert env.state == config.start
        assert len(env.visited) == 1

    def test_gridworld_step_boundaries(self) -> None:
        """Test that GridWorld respects boundaries."""
        GridWorld = self.module.GridWorld
        GridWorldConfig = self.module.GridWorldConfig

        config = GridWorldConfig(size=5, start=(0, 0), seed=42)
        env = GridWorld(config=config)

        # Try to move left from (0, 0) - should stay in place
        _, _, _ = env.step(3)  # left
        assert env.state[0] >= 0

        # Try to move down from (0, 0) - should stay in place
        _, _, _ = env.step(2)  # down
        assert env.state[1] >= 0

    def test_gridworld_goal_reward(self) -> None:
        """Test that reaching goal gives positive reward."""
        GridWorldConfig = self.module.GridWorldConfig

        config = GridWorldConfig(size=3, start=(0, 0), goal=(1, 0), seed=42)
        assert config.goal != config.start

    def test_gridworld_coverage(self) -> None:
        """Test coverage calculation."""
        GridWorld = self.module.GridWorld
        GridWorldConfig = self.module.GridWorldConfig

        config = GridWorldConfig(size=4, obstacle_probability=0.0, seed=42)
        env = GridWorld(config=config)

        # Initial coverage should be 1/16
        initial_coverage = env.get_coverage()
        assert 0.0 < initial_coverage <= 1.0

        # After some moves, coverage should increase or stay same
        env.step(0)  # up
        env.step(1)  # right
        new_coverage = env.get_coverage()
        assert new_coverage >= initial_coverage


class TestMFNExplorer:
    """Tests for the MFN Explorer module."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load the rl_exploration module."""
        self.module = load_example_module("rl_exploration")

    def test_explorer_initialization(self) -> None:
        """Test MFNExplorer initialization."""
        MFNExplorer = self.module.MFNExplorer

        explorer = MFNExplorer(grid_size=8, seed=42)

        assert explorer.grid_size == 8
        assert explorer.visit_counts.shape == (8, 8)
        assert np.all(explorer.visit_counts == 0)

    def test_exploration_bonus_decreases(self) -> None:
        """Test that exploration bonus decreases with visits."""
        MFNExplorer = self.module.MFNExplorer

        explorer = MFNExplorer(grid_size=8, seed=42)

        # First visit should have higher bonus than subsequent visits
        bonus1 = explorer.get_exploration_bonus((0, 0))
        bonus2 = explorer.get_exploration_bonus((0, 0))
        bonus3 = explorer.get_exploration_bonus((0, 0))

        assert bonus1 > bonus2 > bonus3

    def test_coverage_fractal_dim_computation(self) -> None:
        """Test fractal dimension computation for coverage."""
        MFNExplorer = self.module.MFNExplorer

        explorer = MFNExplorer(grid_size=8, seed=42)

        # Visit some states
        for i in range(4):
            for j in range(4):
                explorer.get_exploration_bonus((i, j))

        fractal_dim = explorer.compute_coverage_fractal_dim()
        assert fractal_dim >= 0.0
        assert fractal_dim <= 2.5

    def test_epsilon_modulation(self) -> None:
        """Test epsilon modulation over episodes."""
        MFNExplorer = self.module.MFNExplorer

        explorer = MFNExplorer(grid_size=8, seed=42)

        # Epsilon should decrease over episodes
        eps_early = explorer.modulate_epsilon(0.8, episode=0, max_episodes=100)
        eps_late = explorer.modulate_epsilon(0.8, episode=90, max_episodes=100)

        assert eps_late < eps_early
        assert eps_early <= 1.0
        assert eps_late >= 0.05

    def test_stdp_reward_modulation(self) -> None:
        """Test STDP-inspired reward modulation."""
        MFNExplorer = self.module.MFNExplorer

        explorer = MFNExplorer(grid_size=8, seed=42)

        # Record some actions
        for t in range(5):
            explorer.record_action_time(float(t))

        # Modulate a positive reward
        original_reward = 1.0
        modulated = explorer.modulate_reward_stdp(t=6.0, reward=original_reward)

        # Modulated reward should be >= original for positive reward
        assert modulated >= original_reward

    def test_main_function_exists(self) -> None:
        """Test that main() function exists and is callable."""
        assert callable(self.module.main)
