"""Determinism benchmark for BN-Syn traces."""

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
class Trace:
    sigma: np.ndarray
    rate_hz: np.ndarray


EXT_RATE_HZ = 1000.0
EXT_W_NS = 50.0


def _simulate_trace(seed: int, n_neurons: int, dt_ms: float, steps: int) -> Trace:
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
    sigmas = np.zeros(steps, dtype=np.float64)
    rates = np.zeros(steps, dtype=np.float64)
    for idx in range(steps):
        metrics = net.step()
        sigmas[idx] = metrics["sigma"]
        rates[idx] = metrics["spike_rate_hz"]
    return Trace(sigma=sigmas, rate_hz=rates)


def _max_abs_error(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs(a - b)))


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return float("nan")
    corr = np.corrcoef(a, b)[0, 1]
    return float(corr)


def _emit_metrics(metrics: Iterable[dict[str, object]]) -> None:
    for metric in metrics:
        print(json.dumps(metric, sort_keys=True))


def main() -> None:
    seed = 42
    n_neurons = 200
    dt_ms = 0.1
    steps = 300
    ctx = build_context(seed, n_neurons, dt_ms)

    trace_a = _simulate_trace(seed, n_neurons, dt_ms, steps)
    trace_b = _simulate_trace(seed, n_neurons, dt_ms, steps)

    sigma_error = _max_abs_error(trace_a.sigma, trace_b.sigma)
    rate_error = _max_abs_error(trace_a.rate_hz, trace_b.rate_hz)
    max_error = max(sigma_error, rate_error)

    if max_error >= 1e-12:
        raise AssertionError(f"Determinism drift too high: {max_error:.3e}")

    trace_c = _simulate_trace(seed + 1, n_neurons, dt_ms, steps)
    sigma_corr = _correlation(trace_a.sigma, trace_c.sigma)
    rate_corr = _correlation(trace_a.rate_hz, trace_c.rate_hz)
    if not np.isfinite(sigma_corr) or not np.isfinite(rate_corr):
        raise AssertionError("Non-finite correlations for different seeds")

    if max(sigma_corr, rate_corr) >= 0.95:
        raise AssertionError(
            f"Different seeds too correlated: sigma_corr={sigma_corr:.2f}, rate_corr={rate_corr:.2f}"
        )

    metrics = [
        metric_payload(ctx, "determinism_max_abs_error", max_error, "abs", "determinism"),
        metric_payload(ctx, "seed_diff_sigma_corr", sigma_corr, "corr", "determinism"),
        metric_payload(ctx, "seed_diff_rate_corr", rate_corr, "corr", "determinism"),
    ]
    _emit_metrics(metrics)


if __name__ == "__main__":
    main()
