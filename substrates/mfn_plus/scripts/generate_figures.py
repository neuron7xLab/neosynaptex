#!/usr/bin/env python3
"""Generate publication figures from G0-G6 results.

Outputs PDF figures to manuscript/figures/ for LaTeX inclusion.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = Path("results")
FIGURES = Path("manuscript/figures")
FIGURES.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 10,
    "font.family": "serif",
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


def fig1_ccp_reproducibility():
    """G0: D_f and R across 20 seeds."""
    data = json.loads((RESULTS / "g0_reproducibility.json").read_text())
    seeds = [r["seed"] for r in data["per_seed"]]
    D_f = [r["D_f"] for r in data["per_seed"]]
    R = [r["R"] for r in data["per_seed"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.5))

    ax1.bar(seeds, D_f, color="#2196F3", alpha=0.8, width=0.7)
    ax1.axhline(1.5, color="#E53935", ls="--", lw=1, label="CCP window")
    ax1.axhline(2.0, color="#E53935", ls="--", lw=1)
    ax1.axhline(data["D_f_mean"], color="#1B5E20", ls="-", lw=1.5,
                label=f'mean={data["D_f_mean"]:.3f}')
    ax1.set_xlabel("Seed")
    ax1.set_ylabel("$D_f$")
    ax1.set_title("Fractal Dimension (G0)")
    ax1.set_ylim(1.4, 2.1)
    ax1.legend(fontsize=8)

    ax2.bar(seeds, R, color="#FF9800", alpha=0.8, width=0.7)
    ax2.axhline(0.4, color="#E53935", ls="--", lw=1, label="$R_c = 0.4$")
    ax2.axhline(data["R_mean"], color="#1B5E20", ls="-", lw=1.5,
                label=f'mean={data["R_mean"]:.3f}')
    ax2.set_xlabel("Seed")
    ax2.set_ylabel("$R$")
    ax2.set_title("Phase Coherence (G0)")
    ax2.set_ylim(0.0, 1.0)
    ax2.legend(fontsize=8)

    fig.suptitle(f'CCP Reproducibility: {data["cognitive_fraction"]:.0%} cognitive, '
                 f'CV={data["D_f_cv"]:.2%}', fontsize=11, y=1.02)
    plt.tight_layout()
    fig.savefig(FIGURES / "fig1_ccp_reproducibility.pdf")
    plt.close(fig)
    print("  Fig 1: CCP reproducibility")


def fig2_cross_substrate():
    """G3: CCP across substrates."""
    data = json.loads((RESULTS / "g3_cross_validation.json").read_text())

    substrates = data["substrates"]
    names = ["MFN Turing", "FHN Excitable", "Kuramoto"]
    keys = ["mfn_turing", "fhn_excitable", "kuramoto"]
    colors = ["#4CAF50", "#2196F3", "#FF9800"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.5))

    for i, (name, key, color) in enumerate(zip(names, keys, colors, strict=False)):
        results = substrates[key]["results"]
        D_f_vals = [r["D_f"] for r in results]
        R_vals = [r["R"] for r in results]
        x_pos = [i - 0.15, i, i + 0.15]

        ax1.bar(x_pos, D_f_vals, color=color, alpha=0.8, width=0.12, label=name)
        ax2.bar(x_pos, R_vals, color=color, alpha=0.8, width=0.12, label=name)

    ax1.axhline(1.5, color="#E53935", ls="--", lw=1)
    ax1.axhline(2.0, color="#E53935", ls="--", lw=1)
    ax1.set_xticks(range(3))
    ax1.set_xticklabels(names, fontsize=8)
    ax1.set_ylabel("$D_f$")
    ax1.set_title("Fractal Dimension")
    ax1.set_ylim(1.4, 2.2)

    ax2.axhline(0.4, color="#E53935", ls="--", lw=1, label="$R_c$")
    ax2.set_xticks(range(3))
    ax2.set_xticklabels(names, fontsize=8)
    ax2.set_ylabel("$R$")
    ax2.set_title("Phase Coherence")
    ax2.set_ylim(0.0, 1.0)

    fig.suptitle("Cross-Substrate CCP Validation (G3)", fontsize=11, y=1.02)
    plt.tight_layout()
    fig.savefig(FIGURES / "fig2_cross_substrate.pdf")
    plt.close(fig)
    print("  Fig 2: Cross-substrate")


def fig3_falsification():
    """G2: Adversarial states."""
    data = json.loads((RESULTS / "g2_falsification.json").read_text())
    cases = data["cases"]

    names = [c["case"].replace("_", "\n") for c in cases]
    D_f_vals = [c["D_f"] for c in cases]
    R_vals = [c["R"] for c in cases]
    cognitive = [c["cognitive"] for c in cases]
    colors = ["#4CAF50" if c else "#E53935" for c in cognitive]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.5))

    ax1.barh(range(len(names)), D_f_vals, color=colors, alpha=0.8)
    ax1.axvline(1.5, color="gray", ls="--", lw=1)
    ax1.axvline(2.0, color="gray", ls="--", lw=1)
    ax1.set_yticks(range(len(names)))
    ax1.set_yticklabels(names, fontsize=8)
    ax1.set_xlabel("$D_f$")
    ax1.set_title("Fractal Dimension")

    ax2.barh(range(len(names)), R_vals, color=colors, alpha=0.8)
    ax2.axvline(0.4, color="gray", ls="--", lw=1)
    ax2.set_yticks(range(len(names)))
    ax2.set_yticklabels(names, fontsize=8)
    ax2.set_xlabel("$R$")
    ax2.set_title("Phase Coherence")

    fig.suptitle("Falsification: CCP Discriminative Power (G2)", fontsize=11, y=1.02)
    plt.tight_layout()
    fig.savefig(FIGURES / "fig3_falsification.pdf")
    plt.close(fig)
    print("  Fig 3: Falsification")


def fig4_gnc_agent():
    """G6: GNC+ agent adaptation."""
    data = json.loads((RESULTS / "g6_ai_transfer.json").read_text())

    fig, ax = plt.subplots(figsize=(5, 3))

    early = data["training_early_coherence"]
    late = data["training_late_coherence"]
    ood = data["ood_coherence"]

    bars = ax.bar(
        ["Early\n(steps 1-10)", "Late\n(steps 40-50)", "OOD\n(novel)"],
        [early, late, ood],
        color=["#2196F3", "#4CAF50", "#FF9800"],
        alpha=0.8,
    )
    ax.axhline(0.3, color="#E53935", ls="--", lw=1, label="Functional threshold")
    ax.set_ylabel("Coherence")
    ax.set_ylim(0, 1.1)
    ax.set_title("GNC+ Agent: Resilience Under Perturbation (G6)")
    ax.legend(fontsize=8)

    for bar, val in zip(bars, [early, late, ood], strict=False):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{val:.3f}", ha="center", fontsize=9)

    plt.tight_layout()
    fig.savefig(FIGURES / "fig4_gnc_agent.pdf")
    plt.close(fig)
    print("  Fig 4: GNC+ agent")


if __name__ == "__main__":
    print("Generating publication figures...")
    fig1_ccp_reproducibility()
    fig2_cross_substrate()
    fig3_falsification()
    fig4_gnc_agent()
    print(f"\nAll figures saved to {FIGURES}/")
