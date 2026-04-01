#!/usr/bin/env python3
"""Deterministic iteration metrics generator for evidence snapshots.

Contracts (toy environment):
- Discrete action space: [-1.0, 0.0, 1.0] (nearest action to payload is used)
- Outcome: deterministic function of (step, action, risk schedule) + seeded noise
- Risk schedule: low ramp -> spike -> decay -> settle
- Prediction error computed via IterationLoop; safety gate executed each step
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from mlsdm.core.iteration_loop import (
    EnvironmentAdapter,
    IterationContext,
    IterationLoop,
    IterationMetricsEmitter,
    IterationState,
    ObservationBundle,
)

ACTION_SCALE = 0.5
RISK_SCALE = 0.65
DRIFT_SCALE = 0.05


def _risk_schedule(steps: int) -> list[float]:
    schedule: list[float] = []
    for idx in range(steps):
        frac = idx / max(1, steps - 1)
        if frac < 0.4:
            risk = 0.08 + 0.3 * (frac / 0.4)
        elif frac < 0.6:
            risk = 0.38 + 0.55 * ((frac - 0.4) / 0.2)
        elif frac < 0.8:
            risk = 0.93 - 0.45 * ((frac - 0.6) / 0.2)
        else:
            risk = 0.48 - 0.3 * ((frac - 0.8) / 0.2)
        schedule.append(max(0.0, min(1.0, risk)))
    return schedule


class ToyIterationEnvironment(EnvironmentAdapter):
    """Pure, seeded environment for reproducible iteration metrics."""

    def __init__(
        self,
        *,
        risk_schedule: Sequence[float],
        seed: int,
        actions: Sequence[float] = (-1.0, 0.0, 1.0),
        noise_scale: float = 0.02,
    ) -> None:
        self.actions = list(actions)
        if not self.actions:
            raise ValueError("actions must not be empty")
        self.risk_schedule = list(risk_schedule)
        if not self.risk_schedule:
            raise ValueError("risk_schedule must not be empty")
        self.noise_scale = noise_scale
        self.rng = random.Random(seed)
        self.index = 0

    def reset(self, seed: int | None = None) -> ObservationBundle:
        self.index = 0
        if seed is not None:
            self.rng.seed(seed)
        return ObservationBundle(observed_outcome=[0.0], reward=None, terminal=False)

    def step(self, action_payload: float) -> ObservationBundle:
        action = min(self.actions, key=lambda a: abs(a - float(action_payload)))
        risk = self.risk_schedule[min(self.index, len(self.risk_schedule) - 1)]
        base_wave = 0.12 * math.sin(self.index * 0.35)
        drift = 0.18 * math.cos(self.index * 0.15)
        noise = self.rng.uniform(-self.noise_scale, self.noise_scale)
        outcome = action * ACTION_SCALE + risk * RISK_SCALE + base_wave + drift * DRIFT_SCALE + noise
        self.index += 1
        return ObservationBundle(observed_outcome=[outcome], reward=None, terminal=False)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic iteration-metrics.jsonl")
    parser.add_argument("--out", required=True, type=Path, help="Output JSONL path")
    parser.add_argument("--steps", type=int, default=64, help="Number of iterations to run")
    parser.add_argument("--seed", type=int, default=0, help="Seed for RNG and context")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.steps <= 0:
        raise ValueError("--steps must be positive")
    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    schedule = _risk_schedule(args.steps)
    env = ToyIterationEnvironment(risk_schedule=schedule, seed=args.seed)
    emitter = IterationMetricsEmitter(enabled=True, output_path=out_path)
    loop = IterationLoop(enabled=True, metrics_emitter=emitter)
    state = IterationState(parameter=0.0, learning_rate=0.25, tau=1.0, inhibition_gain=1.0)

    env.reset(seed=args.seed)
    abs_errors: list[float] = []
    regime_counts: Counter[str] = Counter()

    for step_idx in range(args.steps):
        risk = schedule[step_idx]
        threat = min(1.0, risk * 0.9 + 0.05 * math.sin(step_idx * 0.25))
        ctx = IterationContext(
            dt=1.0,
            timestamp=float(step_idx),
            seed=args.seed,
            threat=threat,
            risk=risk,
        )
        state, trace, _ = loop.step(state, env, ctx)
        abs_errors.append(float(trace["prediction_error"]["abs_delta"]))
        regime_counts[str(trace["regime"])] += 1

    mean_abs_error = statistics.fmean(abs_errors) if abs_errors else 0.0
    max_risk = max(schedule) if schedule else 0.0
    regimes = ", ".join(f"{k}:{regime_counts[k]}" for k in sorted(regime_counts))

    print(f"iteration-metrics written to: {out_path}")
    print(
        json.dumps(
            {
                "steps": args.steps,
                "seed": args.seed,
                "mean_abs_prediction_error": round(mean_abs_error, 8),
                "max_risk": round(max_risk, 6),
                "regimes": regime_counts,
            },
            sort_keys=True,
        )
    )
    print(f"summary: steps={args.steps}, mean_abs_prediction_error={mean_abs_error:.6f}, max_risk={max_risk:.6f}")
    print(f"regime_histogram: {regimes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
