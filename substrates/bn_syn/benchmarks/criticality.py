"""Criticality benchmark computing avalanche statistics and power-law fit."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams  # noqa: E402
from bnsyn.rng import seed_all  # noqa: E402
from bnsyn.sim.network import Network, NetworkParams  # noqa: E402

from benchmarks.common import build_context, metric_payload  # noqa: E402


@dataclass(frozen=True)
class CriticalitySummary:
    sigma_mean: float
    sigma_std: float
    avalanche_count: int
    power_law_slope: float
    power_law_r2: float


EXT_RATE_HZ = 1000.0
EXT_W_NS = 50.0


def _simulate_activity(
    seed: int, n_neurons: int, dt_ms: float, steps: int
) -> tuple[np.ndarray, np.ndarray]:
    pack = seed_all(seed)
    rng = pack.np_rng
    net = Network(
        NetworkParams(N=n_neurons, ext_rate_hz=EXT_RATE_HZ, ext_w_nS=EXT_W_NS),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=dt_ms,
        rng=rng,
    )
    activity = np.zeros(steps, dtype=np.float64)
    sigmas = np.zeros(steps, dtype=np.float64)
    for idx in range(steps):
        metrics = net.step()
        activity[idx] = metrics["A_t1"]
        sigmas[idx] = metrics["sigma"]
    return activity, sigmas


def _avalanche_sizes(activity: np.ndarray, silence_threshold: float) -> np.ndarray:
    sizes: list[float] = []
    current = 0.0
    for value in activity:
        if value > silence_threshold:
            current += value
        elif current > 0.0:
            sizes.append(current)
            current = 0.0
    if current > 0.0:
        sizes.append(current)
    return np.asarray(sizes, dtype=np.float64)


def _power_law_fit(sizes: np.ndarray, min_size: float = 2.0) -> tuple[float, float]:
    filtered = sizes[sizes >= min_size]
    if filtered.size < 5:
        raise AssertionError("Insufficient avalanche samples for power-law fit")
    unique_sizes, counts = np.unique(filtered, return_counts=True)
    log_sizes = np.log(unique_sizes)
    log_counts = np.log(counts)
    slope, intercept = np.polyfit(log_sizes, log_counts, deg=1)
    predicted = slope * log_sizes + intercept
    ss_res = float(np.sum((log_counts - predicted) ** 2))
    ss_tot = float(np.sum((log_counts - np.mean(log_counts)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(slope), float(r2)


def _emit_metrics(metrics: Iterable[dict[str, object]]) -> None:
    for metric in metrics:
        print(json.dumps(metric, sort_keys=True))


def _summarize(seed: int, n_neurons: int, dt_ms: float, steps: int) -> CriticalitySummary:
    activity, sigmas = _simulate_activity(seed, n_neurons, dt_ms, steps)
    silence_threshold = float(np.percentile(activity, 20.0))
    sizes = _avalanche_sizes(activity, silence_threshold)
    slope, r2 = _power_law_fit(sizes)
    return CriticalitySummary(
        sigma_mean=float(np.mean(sigmas)),
        sigma_std=float(np.std(sigmas)),
        avalanche_count=int(sizes.size),
        power_law_slope=slope,
        power_law_r2=r2,
    )


def main() -> None:
    seed = 21
    n_neurons = 200
    dt_ms = 0.1
    steps = 600
    ctx = build_context(seed, n_neurons, dt_ms)

    summary = _summarize(seed, n_neurons, dt_ms, steps)
    sigma_drift = abs(summary.sigma_mean - 1.0)

    if sigma_drift > 0.2:
        raise AssertionError(f"Sigma drift too high: {sigma_drift:.3f}")
    if summary.power_law_slope >= 0.0:
        raise AssertionError("Power-law slope is not negative")

    metrics = [
        metric_payload(ctx, "criticality_sigma_mean", summary.sigma_mean, "sigma", "criticality"),
        metric_payload(ctx, "criticality_sigma_std", summary.sigma_std, "sigma", "criticality"),
        metric_payload(
            ctx, "criticality_avalanche_count", summary.avalanche_count, "count", "criticality"
        ),
        metric_payload(
            ctx, "criticality_powerlaw_slope", summary.power_law_slope, "slope", "criticality"
        ),
        metric_payload(ctx, "criticality_powerlaw_r2", summary.power_law_r2, "r2", "criticality"),
    ]
    _emit_metrics(metrics)


if __name__ == "__main__":
    main()
