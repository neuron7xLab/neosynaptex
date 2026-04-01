"""
CartPole Adapter — DNCA in a real Gymnasium environment.

"Code that lives only in tests is dead code."

Maps CartPole's 4D observation → DNCA's 64D input,
DNCA's dominant activity → CartPole binary action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import torch


@dataclass
class CartPoleEpisode:
    length: int
    total_reward: float
    dominant_sequence: List[str]


def run_cartpole(
    dnca_class: type,
    n_episodes: int = 10,
    state_dim: int = 64,
    max_steps: int = 500,
    seed: int = 42,
) -> List[CartPoleEpisode]:
    """
    Run DNCA on CartPole-v1.

    Args:
        dnca_class: DNCA class (to avoid import at module level)
        n_episodes: number of episodes
        state_dim: DNCA state dimension
        max_steps: max steps per episode
        seed: reproducibility seed

    Returns: list of episode results
    """
    try:
        import gymnasium as gym
    except ImportError:
        raise ImportError("pip install gymnasium")

    torch.manual_seed(seed)
    env = gym.make("CartPole-v1")
    results: List[CartPoleEpisode] = []

    for ep in range(n_episodes):
        dnca = dnca_class(state_dim=state_dim, hidden_dim=128, seed=seed + ep)
        obs, _ = env.reset(seed=seed + ep)
        total_reward = 0.0
        dominants: List[str] = []

        for step in range(max_steps):
            # Pad 4D obs → state_dim
            obs_padded = torch.zeros(state_dim)
            obs_tensor = torch.tensor(obs, dtype=torch.float32)
            obs_padded[:4] = obs_tensor

            out = dnca.step(obs_padded, reward=total_reward / max(1, step))

            # Binary action from dominant activity
            action = 1 if out.dominant_activity > 0.5 else 0
            dominants.append(out.dominant_nmo or "none")

            obs, reward, terminated, truncated, _ = env.step(action)
            total_reward += reward

            if terminated or truncated:
                break

        results.append(CartPoleEpisode(
            length=step + 1,
            total_reward=total_reward,
            dominant_sequence=dominants,
        ))

    env.close()
    return results


def cartpole_summary(results: List[CartPoleEpisode]) -> str:
    """Format CartPole results."""
    lengths = [r.length for r in results]
    rewards = [r.total_reward for r in results]
    lines = [
        "=" * 50,
        "DNCA CartPole Results",
        "=" * 50,
        f"  Episodes: {len(results)}",
        f"  Mean length: {np.mean(lengths):.1f} (random ≈ 20)",
        f"  Max length:  {max(lengths)}",
        f"  Mean reward: {np.mean(rewards):.1f}",
        f"  Per episode:",
    ]
    for i, r in enumerate(results):
        lines.append(f"    ep {i+1}: length={r.length}, reward={r.total_reward:.0f}")
    lines.append("=" * 50)
    return "\n".join(lines)
