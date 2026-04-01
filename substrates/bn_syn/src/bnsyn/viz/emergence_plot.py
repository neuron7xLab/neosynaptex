"""Plot emergence NPZ artifacts."""

from __future__ import annotations

from pathlib import Path

import numpy as np

REQUIRED_FIELDS = {
    "format_version",
    "spike_steps",
    "spike_neurons",
    "sigma_trace",
    "rate_trace_hz",
    "dt_ms",
    "steps",
    "N",
    "seed",
    "external_current_pA",
}


def plot_emergence_npz(input_npz: str | Path, output_png: str | Path) -> None:
    """Render spike raster, rate trace, and sigma trace from NPZ artifact."""
    with np.load(input_npz) as data:
        missing = REQUIRED_FIELDS.difference(data.files)
        if missing:
            raise ValueError(f"Missing required NPZ fields: {sorted(missing)}")

        format_version = str(data["format_version"].item())
        if format_version != "1.1.0":
            raise ValueError(f"Unsupported format_version: {format_version}")

        spike_steps = np.asarray(data["spike_steps"], dtype=np.int64)
        spike_neurons = np.asarray(data["spike_neurons"], dtype=np.int64)
        sigma_trace = np.asarray(data["sigma_trace"], dtype=np.float64)
        rate_trace_hz = np.asarray(data["rate_trace_hz"], dtype=np.float64)
        steps = int(np.asarray(data["steps"]).item())
        n_neurons = int(np.asarray(data["N"]).item())

    if spike_steps.shape != spike_neurons.shape:
        raise ValueError("spike_steps and spike_neurons must have identical shapes")
    if sigma_trace.ndim != 1 or rate_trace_hz.ndim != 1:
        raise ValueError("sigma_trace and rate_trace_hz must be 1-D arrays")
    if sigma_trace.shape[0] != steps or rate_trace_hz.shape[0] != steps:
        raise ValueError("Trace lengths must equal steps")
    if spike_steps.size and (spike_steps.min() < 0 or spike_steps.max() >= steps):
        raise ValueError("spike_steps values must be in [0, steps)")
    if spike_neurons.size and (spike_neurons.min() < 0 or spike_neurons.max() >= n_neurons):
        raise ValueError("spike_neurons values must be in [0, N)")

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            'Visualization requires matplotlib. Install with: pip install -e ".[viz]"'
        ) from exc

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    axes[0].scatter(spike_steps, spike_neurons, s=2, c="black", alpha=0.6)
    axes[0].set_ylabel("Neuron")
    axes[0].set_title("Spike raster")

    axes[1].plot(rate_trace_hz, color="tab:orange", linewidth=1.2)
    axes[1].set_ylabel("Rate (Hz)")
    axes[1].set_title("Population rate trace")

    axes[2].plot(sigma_trace, color="tab:blue", linewidth=1.2)
    axes[2].set_ylabel("Sigma")
    axes[2].set_xlabel("Step")
    axes[2].set_title("Sigma trace")

    plt.tight_layout()
    plt.savefig(output_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
