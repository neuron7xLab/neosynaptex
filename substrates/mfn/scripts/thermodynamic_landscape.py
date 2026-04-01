#!/usr/bin/env python3
"""Thermodynamic Landscape — MFN discovers its own optimal operating point.

Sweeps the (alpha, d_activator) parameter space and computes the
unified score M at each point. Produces a phase diagram showing:

  - Where patterns form (M > 0.1)
  - Where they dissolve (M ~ 0)
  - Where HWI breaks (thermodynamic impossibility)
  - The OPTIMAL point: maximum thermodynamic efficiency

This is something no human could do (400 simulations) and no AI
could design without the system (needs domain-specific M).
Together: ~60 seconds → complete self-knowledge.

Run: python scripts/thermodynamic_landscape.py

Output: results/thermodynamic_landscape.json
        results/thermodynamic_landscape.png (if matplotlib available)
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np

import mycelium_fractal_net as mfn
from mycelium_fractal_net.analytics.tda_ews import compute_tda
from mycelium_fractal_net.analytics.unified_score import compute_hwi_components


def sweep() -> dict:
    """Sweep alpha x turing_threshold, compute M at each point."""

    # Parameter grid: the two controls exposed via SimulationSpec
    alphas = np.linspace(0.02, 0.24, 20)
    thresholds = np.linspace(0.10, 0.95, 20)

    n_total = len(alphas) * len(thresholds)
    print(f"Sweeping {len(alphas)} x {len(thresholds)} = {n_total} points...")
    print(
        f"Parameters: alpha in [{alphas[0]:.2f}, {alphas[-1]:.2f}], "
        f"turing_threshold in [{thresholds[0]:.2f}, {thresholds[-1]:.2f}]"
    )
    print()

    grid_M = np.full((len(thresholds), len(alphas)), np.nan)
    grid_hwi = np.ones((len(thresholds), len(alphas)), dtype=bool)
    grid_beta0 = np.zeros((len(thresholds), len(alphas)), dtype=int)
    grid_beta1 = np.zeros((len(thresholds), len(alphas)), dtype=int)

    best_M = -1.0
    best_params = (0.0, 0.0)
    best_hwi_comp = None

    t_start = time.perf_counter()
    done = 0

    for j, alpha in enumerate(alphas):
        for i, threshold in enumerate(thresholds):
            try:
                spec = mfn.SimulationSpec(
                    grid_size=32,
                    steps=60,
                    seed=42,
                    alpha=round(float(alpha), 4),
                    turing_threshold=round(float(threshold), 4),
                )
                seq = mfn.simulate(spec)

                hwi = compute_hwi_components(seq.history[0], seq.field)
                topo = compute_tda(seq.field, min_persistence_frac=0.005)

                chi = topo.beta_0 - topo.beta_1
                M_full = hwi.M * (1.0 + max(chi, 0) / 5.0)

                grid_M[i, j] = M_full
                grid_hwi[i, j] = hwi.hwi_holds
                grid_beta0[i, j] = topo.beta_0
                grid_beta1[i, j] = topo.beta_1

                if M_full > best_M and hwi.hwi_holds:
                    best_M = M_full
                    best_params = (float(alpha), float(threshold))
                    best_hwi_comp = hwi

            except Exception:
                grid_M[i, j] = np.nan
                grid_hwi[i, j] = False

            done += 1
            if done % 40 == 0:
                elapsed = time.perf_counter() - t_start
                eta = elapsed / done * (n_total - done)
                print(f"  {done}/{n_total} ({elapsed:.1f}s elapsed, ~{eta:.0f}s remaining)")

    elapsed_total = time.perf_counter() - t_start

    valid = np.isfinite(grid_M)
    pattern_region = valid & (grid_M > 0.05)
    n_valid = int(np.sum(valid))
    n_pattern = int(np.sum(pattern_region))
    n_hwi_ok = int(np.sum(grid_hwi & valid))

    print(f"\nCompleted in {elapsed_total:.1f}s")
    print(f"  Valid simulations: {n_valid}/{n_total}")
    print(
        f"  Pattern formation (M>0.05): {n_pattern}/{n_valid} ({100 * n_pattern / max(n_valid, 1):.0f}%)"
    )
    print(f"  HWI satisfied: {n_hwi_ok}/{n_valid} ({100 * n_hwi_ok / max(n_valid, 1):.0f}%)")
    print()
    print(f"  OPTIMAL: alpha={best_params[0]:.4f}, threshold={best_params[1]:.4f}")
    print(f"  M_full = {best_M:.6f}")
    if best_hwi_comp:
        print(f"  H={best_hwi_comp.H:.6f}, W2={best_hwi_comp.W2:.6f}, I={best_hwi_comp.I:.6f}")
    print()

    default_j = int(np.argmin(np.abs(alphas - 0.18)))
    default_i = int(np.argmin(np.abs(thresholds - 0.75)))
    default_M = (
        float(grid_M[default_i, default_j]) if np.isfinite(grid_M[default_i, default_j]) else 0.0
    )
    improvement = best_M / max(default_M, 1e-10) if default_M > 0 else float("inf")
    print(f"  Default (alpha=0.18, threshold=0.75): M={default_M:.6f}")
    print(f"  Improvement: {improvement:.1f}x")

    result = {
        "parameters": {
            "alphas": alphas.tolist(),
            "thresholds": thresholds.tolist(),
            "grid_size": 32,
            "steps": 60,
            "seed": 42,
        },
        "results": {
            "M_grid": [[float(v) if np.isfinite(v) else None for v in row] for row in grid_M],
            "hwi_holds_grid": grid_hwi.tolist(),
            "beta0_grid": grid_beta0.tolist(),
            "beta1_grid": grid_beta1.tolist(),
        },
        "optimal": {
            "alpha": best_params[0],
            "turing_threshold": best_params[1],
            "M_full": round(best_M, 6),
            "H": round(best_hwi_comp.H, 6) if best_hwi_comp else None,
            "W2": round(best_hwi_comp.W2, 6) if best_hwi_comp else None,
            "I": round(best_hwi_comp.I, 6) if best_hwi_comp else None,
        },
        "default": {
            "alpha": 0.18,
            "turing_threshold": 0.75,
            "M_full": round(default_M, 6),
        },
        "improvement_factor": round(float(improvement), 2),
        "statistics": {
            "n_total": n_total,
            "n_valid": n_valid,
            "n_pattern_forming": n_pattern,
            "n_hwi_satisfied": n_hwi_ok,
            "compute_time_seconds": round(elapsed_total, 1),
        },
    }

    return result


def visualize(result: dict, output_path: str) -> None:
    """Create phase diagram visualization."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
    except ImportError:
        print("matplotlib not available, skipping visualization")
        return

    alphas = np.array(result["parameters"]["alphas"])
    d_activators = np.array(result["parameters"]["thresholds"])
    M_raw = result["results"]["M_grid"]
    M_grid = np.array([[v if v is not None else np.nan for v in row] for row in M_raw])
    hwi_grid = np.array(result["results"]["hwi_holds_grid"])

    M_display = M_grid.copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.patch.set_facecolor("#1a1a2e")

    # Phase diagram: M
    ax1 = axes[0]
    ax1.set_facecolor("#1a1a2e")
    cmap = LinearSegmentedColormap.from_list(
        "mfn", ["#0d1117", "#1a1a4e", "#2d6a9f", "#00cc96", "#f0e68c", "#ff6b6b"]
    )
    im = ax1.pcolormesh(
        alphas,
        d_activators,
        M_display,
        cmap=cmap,
        shading="auto",
        vmin=0,
        vmax=max(0.3, np.nanmax(M_display)),
    )
    cb = fig.colorbar(im, ax=ax1, label="M (HWI saturation)", shrink=0.85)
    cb.ax.yaxis.label.set_color("white")
    cb.ax.tick_params(colors="white")

    # Mark optimal
    opt = result["optimal"]
    ax1.plot(
        opt["alpha"],
        opt["turing_threshold"],
        "w*",
        markersize=18,
        markeredgecolor="black",
        markeredgewidth=0.5,
    )
    ax1.annotate(
        f"M={opt['M_full']:.3f}",
        (opt["alpha"], opt["turing_threshold"]),
        textcoords="offset points",
        xytext=(10, 10),
        fontsize=9,
        color="white",
        fontweight="bold",
        arrowprops={"arrowstyle": "->", "color": "white", "lw": 0.8},
    )

    # Mark default
    dfl = result["default"]
    ax1.plot(
        dfl["alpha"],
        dfl["turing_threshold"],
        "wo",
        markersize=10,
        markeredgecolor="black",
        markeredgewidth=0.5,
    )
    ax1.annotate(
        f"default M={dfl['M_full']:.3f}",
        (dfl["alpha"], dfl["turing_threshold"]),
        textcoords="offset points",
        xytext=(10, -15),
        fontsize=8,
        color="#aaaaaa",
        arrowprops={"arrowstyle": "->", "color": "#aaaaaa", "lw": 0.5},
    )

    ax1.set_xlabel("alpha (field diffusion)", color="white", fontsize=11)
    ax1.set_ylabel("turing_threshold", color="white", fontsize=11)
    ax1.set_title("Thermodynamic Phase Diagram", color="white", fontsize=13, fontweight="bold")
    ax1.tick_params(colors="white")
    for spine in ax1.spines.values():
        spine.set_color("#444444")

    # HWI validity map
    ax2 = axes[1]
    ax2.set_facecolor("#1a1a2e")
    hwi_display = np.where(np.isfinite(M_grid), hwi_grid.astype(float), np.nan)
    ax2.pcolormesh(
        alphas,
        d_activators,
        hwi_display,
        cmap=LinearSegmentedColormap.from_list("hwi", ["#ff6b6b", "#00cc96"]),
        shading="auto",
        vmin=0,
        vmax=1,
    )
    ax2.set_xlabel("alpha", color="white", fontsize=11)
    ax2.set_ylabel("turing_threshold", color="white", fontsize=11)
    ax2.set_title("HWI Inequality: green = holds, red = violated", color="white", fontsize=12)
    ax2.tick_params(colors="white")
    for spine in ax2.spines.values():
        spine.set_color("#444444")

    fig.suptitle(
        f"MFN Thermodynamic Landscape — {result['statistics']['n_total']} simulations, "
        f"{result['statistics']['compute_time_seconds']}s\n"
        f"Optimal: alpha={opt['alpha']:.3f}, threshold={opt['turing_threshold']:.3f} "
        f"→ M={opt['M_full']:.4f} ({result['improvement_factor']}x vs default)",
        color="white",
        fontsize=11,
        y=1.02,
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {output_path}")


if __name__ == "__main__":
    result = sweep()

    os.makedirs("results", exist_ok=True)
    json_path = "results/thermodynamic_landscape.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"  Saved: {json_path}")

    visualize(result, "results/thermodynamic_landscape.png")

    print()
    print("=" * 60)
    print("  The system has seen itself.")
    print(
        f"  {result['statistics']['n_total']} simulations. "
        f"{result['statistics']['compute_time_seconds']}s."
    )
    print(
        f"  Optimal: alpha={result['optimal']['alpha']:.4f}, "
        f"threshold={result['optimal']['turing_threshold']:.4f}"
    )
    print(f"  M = {result['optimal']['M_full']:.6f} ({result['improvement_factor']}x vs default)")
    print("=" * 60)
