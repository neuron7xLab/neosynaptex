"""Emergence experiment artifact generation."""

from __future__ import annotations

from numbers import Real
from pathlib import Path

import numpy as np

from bnsyn.config import AdExParams, CriticalityParams, SynapseParams
from bnsyn.numerics import compute_steps_exact
from bnsyn.rng import seed_all
from bnsyn.sim.network import Network, NetworkParams
from bnsyn.experiments.phase_space import coherence_from_voltages

FORMAT_VERSION = "1.1.0"


def run_emergence_to_disk(
    *,
    N: int,
    dt_ms: float,
    duration_ms: float,
    seed: int,
    external_current_pA: float,
    output_dir: str | Path,
) -> tuple[dict[str, float], str]:
    """Run deterministic emergence stepping and persist NPZ artifact."""
    if seed <= 0:
        raise ValueError("seed must be a positive integer")
    if not isinstance(external_current_pA, Real):
        raise TypeError("external_current_pA must be a finite real number")
    current = float(external_current_pA)
    if not np.isfinite(current):
        raise ValueError("external_current_pA must be a finite real number")

    steps = compute_steps_exact(duration_ms, dt_ms)

    pack = seed_all(seed)
    net = Network(
        NetworkParams(N=N),
        AdExParams(),
        SynapseParams(),
        CriticalityParams(),
        dt_ms=dt_ms,
        rng=pack.np_rng,
    )
    injected_current = np.full(N, current, dtype=np.float64)

    sigma_trace: list[float] = []
    rate_trace_hz: list[float] = []
    coherence_trace: list[float] = []
    spike_steps: list[int] = []
    spike_neurons: list[int] = []

    for step in range(steps):
        metrics = net.step(external_current_pA=injected_current)
        sigma_trace.append(float(metrics["sigma"]))
        rate_trace_hz.append(float(metrics["spike_rate_hz"]))
        coherence_trace.append(
            coherence_from_voltages(
                net.state.V_mV,
                vreset_mV=float(net.adex.Vreset_mV),
                vthreshold_mV=float(net.adex.VT_mV),
            )
        )
        for neuron_idx in net.state.spiked.nonzero()[0]:
            spike_steps.append(step)
            spike_neurons.append(int(neuron_idx))

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = f"run_{seed}_Iext_{int(round(current))}pA.npz"
    artifact_path = out_dir / artifact_name

    sigma_arr = np.asarray(sigma_trace, dtype=np.float64)
    rate_arr = np.asarray(rate_trace_hz, dtype=np.float64)
    coherence_arr = np.asarray(coherence_trace, dtype=np.float64)
    np.savez(
        artifact_path,
        format_version=np.asarray(FORMAT_VERSION),
        spike_steps=np.asarray(spike_steps, dtype=np.int64),
        spike_neurons=np.asarray(spike_neurons, dtype=np.int64),
        sigma_trace=sigma_arr,
        rate_trace_hz=rate_arr,
        coherence_trace=coherence_arr,
        dt_ms=np.asarray(float(dt_ms), dtype=np.float64),
        steps=np.asarray(steps, dtype=np.int64),
        N=np.asarray(int(N), dtype=np.int64),
        seed=np.asarray(int(seed), dtype=np.int64),
        external_current_pA=np.asarray(current, dtype=np.float64),
    )

    metrics_out = {
        "sigma_mean": float(np.mean(sigma_arr)),
        "rate_mean_hz": float(np.mean(rate_arr)),
        "sigma_std": float(np.std(sigma_arr)),
        "rate_std": float(np.std(rate_arr)),
    }
    return metrics_out, artifact_path.as_posix()
