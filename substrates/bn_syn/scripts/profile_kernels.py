#!/usr/bin/env python3
"""Kernel profiler for BN-Syn throughput analysis.

This script instruments and profiles major computational kernels to identify
bottlenecks and scaling surfaces for optimization.

Parameters
----------
--output : str
    Path to output JSON file (default: benchmarks/kernel_profile.json)
--seed : int
    Random seed for deterministic reproduction (default: 42)
--neurons : int
    Number of neurons in the network (default: 200)
--dt : float
    Timestep in milliseconds (default: 0.1)
--steps : int
    Number of simulation steps (default: 1000)

Returns
-------
None
    Writes JSON with kernel metrics to file or stdout

Notes
-----
This creates the "Performance Jacobian" - the gradient of computational cost
with respect to each kernel operation.

References
----------
Problem statement STEP 2
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from bnsyn.benchmarks.regime import BENCHMARK_REGIME_ID
from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.neuron.adex import adex_step
from bnsyn.numerics.integrators import exp_decay_step
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.synapse.conductance import nmda_mg_block


class KernelProfiler:
    """Profiler for tracking kernel-level performance.

    Attributes
    ----------
    timings : dict[str, list[float]]
        Timing measurements for each kernel
    call_counts : dict[str, int]
        Call count for each kernel
    memory_snapshots : dict[str, list[float]]
        Memory usage snapshots per kernel
    """

    def __init__(self) -> None:
        """Initialize kernel profiler."""
        self.timings: dict[str, list[float]] = defaultdict(list)
        self.call_counts: dict[str, int] = defaultdict(int)
        self.memory_snapshots: dict[str, list[float]] = defaultdict(list)

    def record(self, kernel: str, duration: float, memory_mb: float = 0.0) -> None:
        """Record kernel execution metrics.

        Parameters
        ----------
        kernel : str
            Kernel identifier
        duration : float
            Execution time in seconds
        memory_mb : float, optional
            Memory usage in MB
        """
        self.timings[kernel].append(duration)
        self.call_counts[kernel] += 1
        if memory_mb > 0:
            self.memory_snapshots[kernel].append(memory_mb)

    def report(self) -> dict[str, Any]:
        """Generate profiling report.

        Returns
        -------
        dict[str, Any]
            Profiling summary with timing, call counts, and memory
        """
        kernels: dict[str, Any] = {}

        for kernel_name in self.timings:
            times = self.timings[kernel_name]
            total_time = sum(times)
            avg_time = total_time / len(times) if times else 0.0
            min_time = min(times) if times else 0.0
            max_time = float(np.percentile(np.array(times, dtype=np.float64), 95)) if times else 0.0

            mem_snapshots = self.memory_snapshots.get(kernel_name, [])
            avg_mem = sum(mem_snapshots) / len(mem_snapshots) if mem_snapshots else 0.0

            kernels[kernel_name] = {
                "call_count": self.call_counts[kernel_name],
                "total_time_sec": total_time,
                "avg_time_sec": avg_time,
                "min_time_sec": min_time,
                "max_time_sec": max_time,
                "avg_memory_mb": avg_mem,
            }

        return kernels


def profile_network_kernels(
    *,
    seed: int,
    n_neurons: int,
    dt_ms: float,
    steps: int,
) -> dict[str, Any]:
    """Profile network simulation kernels.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility
    n_neurons : int
        Number of neurons
    dt_ms : float
        Timestep in milliseconds
    steps : int
        Number of simulation steps

    Returns
    -------
    dict[str, Any]
        Complete profiling manifest with kernel metrics
    """
    # Initialize profiler
    profiler = KernelProfiler()

    # Seed RNG for determinism
    pack = seed_all(seed)
    rng = pack.np_rng

    # Network configuration
    nparams = NetworkParams(
        N=n_neurons,
        frac_inhib=0.2,
        p_conn=0.05,
        w_exc_nS=0.5,
        w_inh_nS=1.0,
        ext_rate_hz=2.0,
        ext_w_nS=0.3,
    )

    # Create network
    t0 = time.perf_counter()
    net = Network(
        nparams,
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=dt_ms,
        rng=rng,
    )
    setup_time = time.perf_counter() - t0
    profiler.record("network_setup", setup_time)

    # Count synapses
    synapses = int(net.W_exc.metrics.nnz + net.W_inh.metrics.nnz)

    # Profile simulation loop
    I_syn = np.zeros(n_neurons, dtype=np.float64)
    I_ext = np.zeros(n_neurons, dtype=np.float64)
    for step_idx in range(steps):
        # External Poisson input
        t0 = time.perf_counter()
        lam = nparams.ext_rate_hz * (dt_ms / 1000.0)
        _ = rng.random(n_neurons) < lam
        profiler.record("poisson_input", time.perf_counter() - t0)

        # Spike propagation (synaptic matrix multiplication)
        t0 = time.perf_counter()
        spikes = net.state.spiked
        spikes_E = spikes[: net.nE].astype(float)
        spikes_I = spikes[net.nE :].astype(float)
        _ = net.W_exc.apply(np.asarray(spikes_E, dtype=np.float64))
        _ = net.W_inh.apply(np.asarray(spikes_I, dtype=np.float64))
        profiler.record("synapse_propagation", time.perf_counter() - t0)

        # Conductance decay
        t0 = time.perf_counter()
        _ = exp_decay_step(net.g_ampa, dt_ms, net.syn.tau_AMPA_ms)
        _ = exp_decay_step(net.g_nmda, dt_ms, net.syn.tau_NMDA_ms)
        _ = exp_decay_step(net.g_gabaa, dt_ms, net.syn.tau_GABAA_ms)
        profiler.record("conductance_decay", time.perf_counter() - t0)

        # NMDA Mg block
        t0 = time.perf_counter()
        _ = nmda_mg_block(net.state.V_mV, net.syn.mg_mM)
        profiler.record("nmda_mg_block", time.perf_counter() - t0)

        # AdEx neuron update
        t0 = time.perf_counter()
        I_syn.fill(0.0)
        I_ext.fill(0.0)
        _ = adex_step(net.state, net.adex, dt_ms, I_syn_pA=I_syn, I_ext_pA=I_ext)
        profiler.record("adex_update", time.perf_counter() - t0)

        # Criticality estimation
        t0 = time.perf_counter()
        A_t = float(np.sum(spikes))
        A_t1 = float(np.sum(net.state.spiked))
        _ = net.branch.update(A_t=max(A_t, 1.0), A_t1=max(A_t1, 1.0))
        profiler.record("criticality_estimation", time.perf_counter() - t0)

        # Full step (integrated)
        t0 = time.perf_counter()
        _ = net.step()
        profiler.record("full_step", time.perf_counter() - t0)

    # Generate report
    kernel_metrics = profiler.report()

    # Calculate complexity estimates
    complexity_estimates = {
        "adex_update": f"O({n_neurons})",
        "conductance_decay": f"O({n_neurons})",
        "synapse_propagation": f"O({synapses})",
        "nmda_mg_block": f"O({n_neurons})",
        "criticality_estimation": f"O({n_neurons})",
        "poisson_input": f"O({n_neurons})",
        "full_step": f"O({synapses} + {n_neurons})",
    }

    manifest = {
        "regime_id": BENCHMARK_REGIME_ID,
        "configuration": {
            "neurons": n_neurons,
            "synapses": synapses,
            "dt_ms": dt_ms,
            "steps": steps,
            "seed": seed,
        },
        "kernels": kernel_metrics,
        "complexity": complexity_estimates,
        "metadata": {
            "description": "Performance Jacobian - gradient of cost w.r.t. kernels",
            "note": "Use this to identify O(N²) operations and optimization surfaces",
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
    }

    return manifest


def aggregate_kernel_profiles(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        raise ValueError("runs must contain at least one profile")
    kernel_names = runs[0]["kernels"].keys()
    kernels: dict[str, Any] = {}
    for name in kernel_names:
        totals = [run["kernels"][name]["total_time_sec"] for run in runs]
        avgs = [run["kernels"][name]["avg_time_sec"] for run in runs]
        mins = [run["kernels"][name]["min_time_sec"] for run in runs]
        maxs = [run["kernels"][name]["max_time_sec"] for run in runs]
        mems = [run["kernels"][name]["avg_memory_mb"] for run in runs]
        kernels[name] = {
            "call_count": runs[0]["kernels"][name]["call_count"],
            "total_time_sec": float(np.median(np.array(totals, dtype=np.float64))),
            "avg_time_sec": float(np.median(np.array(avgs, dtype=np.float64))),
            "min_time_sec": float(np.median(np.array(mins, dtype=np.float64))),
            "max_time_sec": float(np.median(np.array(maxs, dtype=np.float64))),
            "avg_memory_mb": float(np.median(np.array(mems, dtype=np.float64))),
        }

    return {
        "regime_id": runs[0]["regime_id"],
        "configuration": runs[0]["configuration"],
        "kernels": kernels,
        "complexity": runs[0]["complexity"],
        "metadata": runs[0]["metadata"],
        "summary": {
            "runs": len(runs),
            "statistic": "median",
        },
    }


def main() -> None:
    """CLI entry point for kernel profiler."""
    parser = argparse.ArgumentParser(
        description="BN-Syn kernel profiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarks/kernel_profile.json",
        help="Output JSON path (default: benchmarks/kernel_profile.json)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--neurons",
        type=int,
        default=200,
        help="Number of neurons (default: 200)",
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=0.1,
        help="Timestep in ms (default: 0.1)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="Number of steps (default: 1000)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=2,
        help="Warmup runs before profiling (default: 2)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Number of profiling repeats (default: 5)",
    )

    args = parser.parse_args()

    # Validate input parameters
    if args.steps <= 0:
        raise ValueError("steps must be positive")
    if args.neurons <= 0:
        raise ValueError("neurons must be positive")
    if args.dt <= 0:
        raise ValueError("dt must be positive")
    if args.warmup < 0 or args.repeats <= 0:
        raise ValueError("warmup must be >=0 and repeats must be positive")

    for _ in range(args.warmup):
        profile_network_kernels(
            seed=args.seed,
            n_neurons=args.neurons,
            dt_ms=args.dt,
            steps=args.steps,
        )

    runs = [
        profile_network_kernels(
            seed=args.seed,
            n_neurons=args.neurons,
            dt_ms=args.dt,
            steps=args.steps,
        )
        for _ in range(args.repeats)
    ]
    manifest = aggregate_kernel_profiles(runs)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    print(f"✅ Kernel profile written to {output_path}")
    print("\nTop kernels by total time:")
    kernels = manifest["kernels"]
    sorted_kernels = sorted(kernels.items(), key=lambda x: x[1]["total_time_sec"], reverse=True)
    for kernel_name, metrics in sorted_kernels[:5]:
        print(f"  {kernel_name}: {metrics['total_time_sec']:.4f}s ({metrics['call_count']} calls)")


if __name__ == "__main__":
    main()
