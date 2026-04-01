"""Scalability benchmark measuring runtime, memory, and step cost."""

from __future__ import annotations

import json
import time
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

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams  # noqa: E402
from bnsyn.rng import seed_all  # noqa: E402
from bnsyn.sim.network import Network, NetworkParams  # noqa: E402

from benchmarks.common import build_context, peak_rss_mb  # noqa: E402


@dataclass(frozen=True)
class ScalabilityResult:
    n_neurons: int
    runtime_s: float
    step_cost_ms: float
    peak_rss_mb: float


EXT_RATE_HZ = 1000.0
EXT_W_NS = 50.0


def _run_scalability(seed: int, n_neurons: int, dt_ms: float, steps: int) -> ScalabilityResult:
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
    start = time.perf_counter()
    for _ in range(steps):
        net.step()
    runtime = time.perf_counter() - start
    return ScalabilityResult(
        n_neurons=n_neurons,
        runtime_s=runtime,
        step_cost_ms=(runtime / steps) * 1000.0,
        peak_rss_mb=peak_rss_mb(),
    )


def _emit_results(results: Iterable[ScalabilityResult], ctx_seed: int, dt_ms: float) -> None:
    ctx = build_context(ctx_seed, n_neurons=0, dt_ms=dt_ms)
    for result in results:
        payload = {
            "benchmark": "scalability",
            "N": result.n_neurons,
            "dt": dt_ms,
            "seed": ctx.seed,
            "runtime_s": result.runtime_s,
            "step_cost_ms": result.step_cost_ms,
            "peak_rss_mb": result.peak_rss_mb,
            "timestamp": ctx.timestamp,
            "git_sha": ctx.git_sha,
        }
        print(json.dumps(payload, sort_keys=True))


def main() -> None:
    seed = 13
    dt_ms = 0.1
    steps = 200
    sizes = [50, 100, 500, 1000]
    results = [_run_scalability(seed, size, dt_ms, steps) for size in sizes]
    _emit_results(results, seed, dt_ms)


if __name__ == "__main__":
    main()
