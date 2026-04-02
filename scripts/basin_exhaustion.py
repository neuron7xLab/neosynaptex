#!/usr/bin/env python3
"""Basin exhaustion for closed-loop control under robust witness aggregation.

Primary model:
  - honest-majority median aggregation over k witnesses
  - bounded update |u_t| <= epsilon <= 0.05
  - quality degradation outside critical window

Outputs:
  - basin_summary.json
  - sensitivity_table.csv
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


@dataclass
class BasinResult:
    seed: int
    fault_rate: float
    sigma: float
    rho: float
    epsilon: float
    eta: float
    chi_min: float
    critical_fraction: float
    collapse_fraction: float
    unresolved_fraction: float


def _parse_grid(spec: str) -> tuple[int, int, int]:
    parts = spec.lower().split("x")
    if len(parts) != 3:
        raise ValueError(f"Invalid grid spec '{spec}', expected AxBxC")
    g, s, q = (int(v) for v in parts)
    if min(g, s, q) <= 1:
        raise ValueError("Grid dimensions must be > 1")
    return g, s, q


def _simulate_one(
    grid: tuple[int, int, int],
    steps: int,
    seed: int,
    k: int,
    fault_rate: float,
    sigma: float,
    rho: float,
    epsilon: float,
    eta: float,
    chi_min: float,
    q_min: float = 0.45,
    q_critical: float = 0.5,
    delta: float = 0.08,
) -> BasinResult:
    rng = np.random.default_rng(seed)
    g_bins, sr_bins, q_bins = grid
    g0 = np.linspace(0.0, 2.0, g_bins)
    sr0 = np.linspace(0.0, 1.0, sr_bins)  # kept for explicit state-space coverage
    q0 = np.linspace(0.0, 1.0, q_bins)
    gamma, _, quality = np.meshgrid(g0, sr0, q0, indexing="ij")

    for _ in range(steps):
        e = gamma - 1.0

        noise = rng.uniform(-sigma, sigma, size=(k,) + e.shape)
        faulty = rng.random(size=(k,) + e.shape) < fault_rate
        corruption = rng.uniform(-0.5, 0.5, size=(k,) + e.shape)
        witnesses = e + np.where(faulty, corruption, noise)

        e_median = np.median(witnesses, axis=0)
        mad = np.median(np.abs(witnesses - e_median), axis=0)
        chi = 1.0 - mad / (np.abs(e_median + 1.0) + 1e-6)
        gate = chi >= chi_min

        u = np.where(gate, -np.clip(eta * e_median, -epsilon, epsilon), 0.0)
        drift = rng.uniform(-rho, rho, size=e.shape)
        e = e + u + drift
        gamma = e + 1.0

        outside = np.maximum(np.abs(e) - delta, 0.0)
        quality = np.clip(quality - 0.08 * outside, 0.0, 1.0)

    delta_star = sigma + (rho / max(eta, 1e-9))
    critical_mask = (np.abs(gamma - 1.0) <= delta_star) & (quality >= q_critical)
    collapse_mask = quality < q_min
    unresolved_mask = ~(critical_mask | collapse_mask)

    total = gamma.size
    return BasinResult(
        seed=seed,
        fault_rate=fault_rate,
        sigma=sigma,
        rho=rho,
        epsilon=epsilon,
        eta=eta,
        chi_min=chi_min,
        critical_fraction=float(np.count_nonzero(critical_mask) / total),
        collapse_fraction=float(np.count_nonzero(collapse_mask) / total),
        unresolved_fraction=float(np.count_nonzero(unresolved_mask) / total),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", default="201x101x101")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--witness-count", type=int, default=5)
    parser.add_argument("--fault-rates", default="0,0.05,0.10")
    parser.add_argument("--sigmas", default="0.01,0.02,0.05")
    parser.add_argument("--rhos", default="0.0,0.005,0.01")
    parser.add_argument("--epsilons", default="0.01,0.03,0.05")
    parser.add_argument("--etas", default="0.01,0.03,0.05,0.1")
    parser.add_argument("--chi-mins", default="0.2,0.3,0.5,0.7")
    parser.add_argument("--output", default="figures/basin")
    args = parser.parse_args()

    grid = _parse_grid(args.grid)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    def parse_floats(text: str) -> list[float]:
        return [float(x.strip()) for x in text.split(",") if x.strip()]

    fault_rates = parse_floats(args.fault_rates)
    sigmas = parse_floats(args.sigmas)
    rhos = parse_floats(args.rhos)
    epsilons = parse_floats(args.epsilons)
    etas = parse_floats(args.etas)
    chi_mins = parse_floats(args.chi_mins)

    runs: list[BasinResult] = []
    for seed in range(args.seeds):
        for fault_rate, sigma, rho, epsilon, eta, chi_min in itertools.product(
            fault_rates, sigmas, rhos, epsilons, etas, chi_mins
        ):
            result = _simulate_one(
                grid=grid,
                steps=args.steps,
                seed=seed,
                k=args.witness_count,
                fault_rate=fault_rate,
                sigma=sigma,
                rho=rho,
                epsilon=epsilon,
                eta=eta,
                chi_min=chi_min,
            )
            runs.append(result)

    summary = {
        "grid": args.grid,
        "steps": args.steps,
        "witness_count": args.witness_count,
        "n_runs": len(runs),
        "mean_critical_fraction": float(np.mean([r.critical_fraction for r in runs])),
        "mean_collapse_fraction": float(np.mean([r.collapse_fraction for r in runs])),
        "mean_unresolved_fraction": float(np.mean([r.unresolved_fraction for r in runs])),
        "no_third_attractor_flag": bool(
            np.mean([r.unresolved_fraction for r in runs]) < 0.05
        ),
    }

    (output_dir / "basin_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "basin_runs.json").write_text(
        json.dumps([asdict(r) for r in runs], indent=2), encoding="utf-8"
    )

    with (output_dir / "sensitivity_table.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(runs[0]).keys()))
        writer.writeheader()
        for row in runs:
            writer.writerow(asdict(row))

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
