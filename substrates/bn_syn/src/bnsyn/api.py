"""Canonical BN-Syn product API surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bnsyn.sim.network import run_simulation

@dataclass(frozen=True)
class RunConfig:
    """Configuration for deterministic simulation runs."""

    steps: int = 2000
    dt_ms: float = 0.1
    seed: int = 42
    N: int = 200


@dataclass(frozen=True)
class SleepStackConfig:
    """Configuration for sleep-stack runs."""

    seed: int = 123
    N: int = 64
    backend: str = "reference"
    steps_wake: int = 800
    steps_sleep: int = 600
    out: str = "results/sleep_stack_v1"


def run(config: RunConfig | dict[str, Any] | None = None) -> dict[str, float]:
    """Run deterministic simulation metrics for the canonical run path."""
    if config is None:
        cfg = RunConfig()
    elif isinstance(config, dict):
        cfg = RunConfig(**config)
    else:
        cfg = config
    return run_simulation(steps=cfg.steps, dt_ms=cfg.dt_ms, seed=cfg.seed, N=cfg.N)


def phase_atlas(seed: int = 20260218) -> dict[str, Any]:
    """Build the deterministic phase atlas payload."""
    from scripts.phase_atlas import build_phase_atlas

    return build_phase_atlas(seed=seed)


def sleep_stack(config: SleepStackConfig | dict[str, Any] | None = None) -> dict[str, Any]:
    """Return deterministic metadata for a sleep-stack execution contract."""
    if config is None:
        cfg = SleepStackConfig()
    elif isinstance(config, dict):
        cfg = SleepStackConfig(**config)
    else:
        cfg = config
    return {
        "seed": cfg.seed,
        "N": cfg.N,
        "backend": cfg.backend,
        "steps_wake": cfg.steps_wake,
        "steps_sleep": cfg.steps_sleep,
        "out": Path(cfg.out).as_posix(),
    }
