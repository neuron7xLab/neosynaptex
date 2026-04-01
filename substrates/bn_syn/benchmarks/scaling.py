"""dt-invariance benchmark comparing firing, weights, and sigma."""

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
class RunSummary:
    sigma_mean: float
    rate_mean_hz: float
    weights_mean: float
    weights_std: float
    weights_p50: float


EXT_RATE_HZ = 1000.0
EXT_W_NS = 50.0
MAX_SIGMA_DRIFT = 0.05
MAX_RATE_DRIFT = 0.15


def _run_network(seed: int, n_neurons: int, dt_ms: float, steps: int) -> RunSummary:
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

    w_exc = net.W_exc.to_dense().ravel()
    w_inh = net.W_inh.to_dense().ravel()
    weights = np.concatenate([w_exc, w_inh]).astype(np.float64, copy=False)

    return RunSummary(
        sigma_mean=float(np.mean(sigmas)),
        rate_mean_hz=float(np.mean(rates)),
        weights_mean=float(np.mean(weights)),
        weights_std=float(np.std(weights)),
        weights_p50=float(np.median(weights)),
    )


def _relative_drift(a: float, b: float) -> float:
    denom = max(1e-12, abs(a))
    return abs(a - b) / denom


def _emit_metrics(metrics: Iterable[dict[str, object]]) -> None:
    for metric in metrics:
        print(json.dumps(metric, sort_keys=True))


def main() -> None:
    seed = 77
    n_neurons = 200
    steps = 300
    dt_a = 0.1
    dt_b = 0.05
    ctx = build_context(seed, n_neurons, dt_a)

    run_a = _run_network(seed, n_neurons, dt_a, steps)
    run_b = _run_network(seed, n_neurons, dt_b, steps * 2)

    sigma_drift = _relative_drift(run_a.sigma_mean, run_b.sigma_mean)
    rate_drift = _relative_drift(run_a.rate_mean_hz, run_b.rate_mean_hz)
    weights_mean_drift = _relative_drift(run_a.weights_mean, run_b.weights_mean)
    weights_std_drift = _relative_drift(run_a.weights_std, run_b.weights_std)
    weights_p50_drift = _relative_drift(run_a.weights_p50, run_b.weights_p50)

    if max(weights_mean_drift, weights_std_drift, weights_p50_drift) > 1e-12:
        raise AssertionError("Weight distribution drift exceeded tolerance")

    if sigma_drift > MAX_SIGMA_DRIFT or rate_drift > MAX_RATE_DRIFT:
        raise AssertionError(
            f"dt-invariance drift too high: sigma={sigma_drift:.3e}, rate={rate_drift:.3e}"
        )

    metrics = [
        metric_payload(ctx, "dt_sigma_drift", sigma_drift, "relative", "scaling"),
        metric_payload(ctx, "dt_rate_drift", rate_drift, "relative", "scaling"),
        metric_payload(ctx, "dt_weight_mean_drift", weights_mean_drift, "relative", "scaling"),
        metric_payload(ctx, "dt_weight_std_drift", weights_std_drift, "relative", "scaling"),
        metric_payload(ctx, "dt_weight_p50_drift", weights_p50_drift, "relative", "scaling"),
    ]
    _emit_metrics(metrics)


if __name__ == "__main__":
    main()
