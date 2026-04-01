#!/usr/bin/env python
"""
Reinforcement Learning Use Case: MFN-Guided Exploration.

This example demonstrates how MFN features can modulate exploration
in a simple reinforcement learning setting:

1. GridWorld environment (no external dependencies)
2. ε-greedy agent with MFN-modulated exploration rate
3. Coverage analysis using fractal dimension
4. STDP-inspired temporal credit assignment

Key concepts:
- Higher fractal dimension of visited states → more exploratory behavior
- MFN features provide a natural measure of state-space coverage
- STDP parameters modulate reward attribution to recent actions

Reference: docs/MFN_SYSTEM_ROLE.md, docs/MFN_FEATURE_SCHEMA.md

Usage:
    python examples/rl_exploration.py

Note: This is a lightweight demonstration without external RL libraries.
MFN serves as a feature engine for state-space analysis, not as a policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

import numpy as np
from numpy.typing import NDArray

from mycelium_fractal_net import (
    STDP_A_MINUS,
    STDP_A_PLUS,
    STDP_TAU_MINUS,
    STDP_TAU_PLUS,
    estimate_fractal_dimension,
    generate_fractal_ifs,
    make_simulation_config_demo,
    run_mycelium_simulation,
)


@dataclass
class GridWorldConfig:
    """Configuration for the GridWorld environment."""

    size: int = 10
    goal: Tuple[int, int] = (9, 9)
    start: Tuple[int, int] = (0, 0)
    obstacle_probability: float = 0.1
    seed: int = 42


@dataclass
class GridWorld:
    """
    Simple GridWorld environment for RL demonstration.

    A 2D grid with a start position, goal, and obstacles.
    Agent can move in 4 directions (up, down, left, right).

    Rewards:
        +1.0 for reaching goal
        -0.5 for hitting obstacle
        -0.01 for each step (encourages efficiency)

    Attributes:
        config: Environment configuration.
        state: Current agent position (x, y).
        obstacles: Set of obstacle positions.
        visited: Set of visited positions.
    """

    config: GridWorldConfig
    state: Tuple[int, int] = field(init=False)
    obstacles: set = field(init=False)
    visited: set = field(init=False, default_factory=set)

    def __post_init__(self) -> None:
        """Initialize the environment."""
        self.rng = np.random.default_rng(self.config.seed)
        self.obstacles = self._generate_obstacles()
        self.state = self.config.start
        self.visited = {self.state}

    def _generate_obstacles(self) -> set:
        """Generate random obstacles, avoiding start and goal."""
        obstacles = set()
        for i in range(self.config.size):
            for j in range(self.config.size):
                pos = (i, j)
                if pos in (self.config.start, self.config.goal):
                    continue
                if self.rng.random() < self.config.obstacle_probability:
                    obstacles.add(pos)
        return obstacles

    def reset(self) -> Tuple[int, int]:
        """Reset environment to start state."""
        self.state = self.config.start
        self.visited = {self.state}
        return self.state

    def step(self, action: int) -> Tuple[Tuple[int, int], float, bool]:
        """
        Take an action in the environment.

        Args:
            action: 0=up, 1=right, 2=down, 3=left

        Returns:
            Tuple of (new_state, reward, done).
        """
        # Action deltas: up, right, down, left
        dx, dy = [(0, 1), (1, 0), (0, -1), (-1, 0)][action]

        x, y = self.state
        new_x = max(0, min(self.config.size - 1, x + dx))
        new_y = max(0, min(self.config.size - 1, y + dy))
        new_pos = (new_x, new_y)

        # Check for obstacles - stay in place if blocked
        if new_pos in self.obstacles:
            reward = -0.5  # Penalty for hitting obstacle
            # Don't move
        else:
            self.state = new_pos
            reward = -0.01  # Small step penalty

        self.visited.add(self.state)

        # Check for goal
        done = self.state == self.config.goal
        if done:
            reward = 1.0

        return self.state, reward, done

    def get_coverage(self) -> float:
        """Return fraction of states visited."""
        total_free = self.config.size**2 - len(self.obstacles)
        return len(self.visited) / max(1, total_free)

    def get_visit_map(self) -> NDArray[np.bool_]:
        """Return binary map of visited states."""
        visit_map = np.zeros((self.config.size, self.config.size), dtype=bool)
        for x, y in self.visited:
            visit_map[x, y] = True
        return visit_map


@dataclass
class ExplorationStats:
    """Statistics for exploration analysis."""

    coverage: float
    fractal_dim: float
    unique_states: int
    total_steps: int
    episodes: int
    mean_episode_length: float
    mean_reward: float


class MFNExplorer:
    """
    Exploration module using MFN features to modulate exploration.

    Uses the fractal dimension of visited states as a measure of
    exploration quality. Higher fractal dimension indicates more
    uniform coverage of the state space.

    The exploration rate is modulated by:
    - Base epsilon (decreases over episodes)
    - Exploration bonus (based on inverse visit counts)
    - MFN fractal feedback (higher D → more exploration)
    """

    def __init__(self, grid_size: int, seed: int = 42):
        """Initialize the explorer."""
        self.grid_size = grid_size
        self.rng = np.random.default_rng(seed)
        self.visit_counts = np.zeros((grid_size, grid_size), dtype=np.int32)
        self.action_times: list[float] = []

    def get_exploration_bonus(self, state: Tuple[int, int]) -> float:
        """
        Get exploration bonus for visiting a state.

        Uses inverse square-root of visit count to encourage
        visiting less-explored states.

        Args:
            state: Current (x, y) position.

        Returns:
            Exploration bonus in [0, 0.5] range.
        """
        x, y = state
        self.visit_counts[x, y] += 1
        count = self.visit_counts[x, y]

        # UCB-style bonus: decreases with sqrt of visit count
        bonus = 0.5 / np.sqrt(count)
        return min(0.5, bonus)

    def compute_coverage_fractal_dim(self) -> float:
        """
        Compute fractal dimension of visited state pattern.

        Returns:
            Box-counting fractal dimension of visited states.
        """
        visited = self.visit_counts > 0
        if visited.sum() < 4:
            return 0.0
        return estimate_fractal_dimension(visited)

    def modulate_epsilon(
        self,
        base_epsilon: float,
        episode: int,
        max_episodes: int,
    ) -> float:
        """
        Modulate exploration rate using MFN features.

        The effective epsilon is:
        epsilon = base * decay * (1 + fractal_feedback)

        Where fractal_feedback encourages more exploration when
        coverage is low-dimensional (clustered).

        Args:
            base_epsilon: Initial exploration rate.
            episode: Current episode number.
            max_episodes: Total number of episodes.

        Returns:
            Modulated epsilon value.
        """
        # Linear decay
        decay = 1.0 - (episode / max_episodes) * 0.9

        # Fractal feedback: low dimension → more exploration
        fractal_dim = self.compute_coverage_fractal_dim()
        if fractal_dim > 0:
            # Normalized feedback: 2.0 is ideal (uniform), lower is clustered
            fractal_feedback = max(0, (1.8 - fractal_dim) / 1.8) * 0.2
        else:
            fractal_feedback = 0.3  # High exploration when no coverage

        epsilon = base_epsilon * decay * (1.0 + fractal_feedback)
        return min(1.0, max(0.05, epsilon))  # Clamp to [0.05, 1.0]

    def record_action_time(self, t: float) -> None:
        """Record action timestamp for STDP-style credit assignment."""
        self.action_times.append(t)
        # Keep only recent actions
        if len(self.action_times) > 100:
            self.action_times = self.action_times[-100:]

    def modulate_reward_stdp(self, t: float, reward: float) -> float:
        """
        Apply STDP-inspired reward modulation.

        Positive rewards are enhanced for recent actions using
        exponential temporal weighting based on STDP parameters.

        Args:
            t: Current timestep.
            reward: Original reward value.

        Returns:
            Modulated reward.
        """
        if reward <= 0 or not self.action_times:
            return reward

        # STDP-style modulation: recent actions get more credit
        modulation = 0.0
        for action_t in self.action_times[-20:]:  # Consider last 20 actions
            delta_t = t - action_t
            if delta_t > 0:
                # LTP-like enhancement for recent actions
                modulation += STDP_A_PLUS * np.exp(-delta_t / (STDP_TAU_PLUS * 50))

        return reward * (1.0 + min(modulation, 0.5))


def run_rl_demo(
    *,
    verbose: bool = True,
    num_episodes: int = 50,
    max_steps: int = 100,
    seed: int = 42,
    return_stats: bool = False,
) -> ExplorationStats | None:
    """
    Run the RL exploration demo.

    Args:
        verbose: Print progress and results.
        num_episodes: Number of training episodes.
        max_steps: Maximum steps per episode.
        seed: Random seed for reproducibility.
        return_stats: If True, return exploration statistics.

    Returns:
        ExplorationStats if return_stats is True, else None.
    """
    rng = np.random.default_rng(seed)

    if verbose:
        print("=" * 60)
        print("MyceliumFractalNet Reinforcement Learning Example")
        print("MFN-Guided Exploration in GridWorld")
        print("=" * 60)

    # Initialize environment and explorer
    env_config = GridWorldConfig(size=10, seed=seed)
    env = GridWorld(config=env_config)
    explorer = MFNExplorer(grid_size=env_config.size, seed=seed)

    if verbose:
        print("\n1. Environment Setup")
        print(f"   Grid size: {env_config.size}x{env_config.size}")
        print(f"   Start: {env_config.start}")
        print(f"   Goal: {env_config.goal}")
        print(f"   Obstacles: {len(env.obstacles)}")

    # Training metrics
    episode_rewards: list[float] = []
    episode_lengths: list[int] = []
    total_steps = 0

    if verbose:
        print("\n2. Training with MFN-modulated exploration...")

    for episode in range(num_episodes):
        state = env.reset()
        episode_reward = 0.0
        t = 0

        # Get modulated epsilon for this episode
        epsilon = explorer.modulate_epsilon(0.8, episode, num_episodes)

        for step in range(max_steps):
            # Get exploration bonus for current state
            bonus = explorer.get_exploration_bonus(state)

            # Epsilon-greedy action selection with MFN modulation
            effective_epsilon = min(1.0, epsilon + bonus * 0.5)

            if rng.random() < effective_epsilon:
                # Explore: random action
                action = rng.integers(0, 4)
            else:
                # Exploit: move toward goal (simple heuristic)
                gx, gy = env.config.goal
                x, y = state
                dx, dy = gx - x, gy - y
                if abs(dx) > abs(dy):
                    action = 1 if dx > 0 else 3  # right or left
                else:
                    action = 0 if dy > 0 else 2  # up or down

            # Take action
            new_state, reward, done = env.step(action)

            # STDP-style reward modulation
            explorer.record_action_time(float(t))
            if reward > 0:
                reward = explorer.modulate_reward_stdp(float(t), reward)

            episode_reward += reward
            state = new_state
            t += 1
            total_steps += 1

            if done:
                break

        episode_rewards.append(episode_reward)
        episode_lengths.append(t)

        if verbose and (episode + 1) % 10 == 0:
            print(
                f"   Episode {episode + 1}: reward={episode_reward:.2f}, steps={t}, ε={epsilon:.3f}"
            )

    # Analysis
    if verbose:
        print("\n3. Coverage Analysis")

    coverage = env.get_coverage()
    visit_map = env.get_visit_map()
    fractal_dim = estimate_fractal_dimension(visit_map) if visit_map.sum() >= 4 else 0.0

    if verbose:
        print(f"   State coverage: {coverage * 100:.1f}%")
        print(f"   Unique states visited: {len(env.visited)}")
        print(f"   Coverage fractal dimension: {fractal_dim:.4f}")

    # Lyapunov stability analysis
    if verbose:
        print("\n4. Stability Analysis")
    _, lyapunov = generate_fractal_ifs(rng, num_points=5000)

    if verbose:
        print(f"   Lyapunov exponent: {lyapunov:.4f}")
        print(f"   System stability: {'STABLE' if lyapunov < 0 else 'UNSTABLE'}")

    # Run a reference MFN simulation
    if verbose:
        print("\n5. Reference MFN Simulation")
    sim_config = make_simulation_config_demo()
    result = run_mycelium_simulation(sim_config)

    if verbose:
        print(f"   Growth events: {result.growth_events}")
        print(
            f"   Field range: [{result.field.min() * 1000:.2f}, {result.field.max() * 1000:.2f}] mV"
        )

    # Create stats
    stats = ExplorationStats(
        coverage=coverage,
        fractal_dim=fractal_dim,
        unique_states=len(env.visited),
        total_steps=total_steps,
        episodes=num_episodes,
        mean_episode_length=float(np.mean(episode_lengths[-10:])),
        mean_reward=float(np.mean(episode_rewards[-10:])),
    )

    # Summary
    if verbose:
        print("\n" + "=" * 60)
        print("TRAINING SUMMARY")
        print("=" * 60)
        print(f"Episodes: {num_episodes}")
        print(f"Total steps: {total_steps}")
        print(f"Mean reward (last 10): {stats.mean_reward:.2f}")
        print(f"Mean length (last 10): {stats.mean_episode_length:.1f}")
        print(f"State coverage: {stats.coverage * 100:.1f}%")
        print(f"Coverage fractal dimension: {stats.fractal_dim:.4f}")

        print("\nSTDP Parameters Used:")
        print(f"   τ+ = {STDP_TAU_PLUS * 1000:.0f} ms")
        print(f"   τ- = {STDP_TAU_MINUS * 1000:.0f} ms")
        print(f"   A+ = {STDP_A_PLUS}")
        print(f"   A- = {STDP_A_MINUS}")

        print("\nMFN Integration:")
        print("   - Fractal dimension used to modulate exploration rate")
        print("   - Low coverage D → higher exploration (encourages spread)")
        print("   - STDP timing constants for reward modulation")
        print("   - Visit count bonuses for novel state discovery")

    if return_stats:
        return stats
    return None


def main() -> None:
    """Entry point for the RL exploration example."""
    run_rl_demo(verbose=True, return_stats=False)


if __name__ == "__main__":
    main()
