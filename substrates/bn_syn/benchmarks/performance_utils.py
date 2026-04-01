"""Utilities for deterministic performance benchmarking."""

from __future__ import annotations

import importlib
import importlib.util
import json
import math
import os
import platform
import time
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from benchmarks.common import git_sha, utc_timestamp
from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams

_PSUTIL_CACHE: ModuleType | None | bool = False


def _psutil_module() -> ModuleType | None:
    global _PSUTIL_CACHE
    if _PSUTIL_CACHE is False:
        spec = importlib.util.find_spec("psutil")
        _PSUTIL_CACHE = importlib.import_module("psutil") if spec else None
    return _PSUTIL_CACHE if isinstance(_PSUTIL_CACHE, ModuleType) else None


@dataclass(frozen=True)
class BenchmarkRun:
    runtime_sec: float
    neurons: int
    synapses: int
    steps: int
    dt: float
    memory_mb: float
    events_per_sec: float
    spikes_per_sec: float
    synaptic_updates_per_sec: float
    spike_count: float


def _safe_float(value: float) -> float:
    if math.isfinite(value):
        return float(value)
    return 0.0


def _cpu_name() -> str:
    cpu = platform.processor()
    if cpu:
        return cpu
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        return platform.machine() or "unknown"
    return platform.machine() or "unknown"


def hardware_info() -> dict[str, Any]:
    total_ram = 0.0
    psutil_module = _psutil_module()
    if psutil_module is not None:
        total_ram = float(psutil_module.virtual_memory().total) / (1024**3)
    return {
        "cpu": _cpu_name(),
        "ram_gb": _safe_float(total_ram),
    }


def process_memory_rss() -> int:
    psutil_module = _psutil_module()
    if psutil_module is None:
        return 0
    return int(psutil_module.Process(os.getpid()).memory_info().rss)


def run_network_benchmark(
    *,
    seed: int,
    n_neurons: int,
    dt_ms: float,
    steps: int,
    p_conn: float,
    frac_inhib: float,
    sample_interval: int = 10,
) -> BenchmarkRun:
    pack = seed_all(seed)
    rng = pack.np_rng
    nparams = NetworkParams(N=n_neurons, p_conn=p_conn, frac_inhib=frac_inhib)
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=dt_ms,
        rng=rng,
    )
    synapses = int(net.W_exc.metrics.nnz + net.W_inh.metrics.nnz)

    max_rss = process_memory_rss()
    spike_count = 0.0

    start_time = time.perf_counter()
    for idx in range(steps):
        metrics = net.step()
        spike_count += float(metrics["A_t1"])
        if idx % sample_interval == 0:
            max_rss = max(max_rss, process_memory_rss())
    runtime = time.perf_counter() - start_time
    max_rss = max(max_rss, process_memory_rss())

    synaptic_updates = float(synapses * steps)
    spikes_per_sec = spike_count / runtime if runtime > 0 else 0.0
    synaptic_updates_per_sec = synaptic_updates / runtime if runtime > 0 else 0.0
    events_per_sec = (spike_count + synaptic_updates) / runtime if runtime > 0 else 0.0

    return BenchmarkRun(
        runtime_sec=_safe_float(runtime),
        neurons=n_neurons,
        synapses=synapses,
        steps=steps,
        dt=_safe_float(dt_ms),
        memory_mb=_safe_float(max_rss / (1024**2)),
        events_per_sec=_safe_float(events_per_sec),
        spikes_per_sec=_safe_float(spikes_per_sec),
        synaptic_updates_per_sec=_safe_float(synaptic_updates_per_sec),
        spike_count=_safe_float(spike_count),
    )


def build_payload(
    *,
    seed: int,
    parameters: dict[str, Any],
    results: dict[str, Any],
) -> dict[str, Any]:
    return {
        "timestamp": utc_timestamp(),
        "git_commit": git_sha(),
        "seed": seed,
        "hardware": hardware_info(),
        "parameters": parameters,
        "results": results,
    }


def emit_json(payload: dict[str, Any], *, output_path: str | None = None) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    else:
        print(text)
