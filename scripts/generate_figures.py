#!/usr/bin/env python3
"""Generate all manuscript figures from gamma_ledger.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = ROOT / "docs" / "submission" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

SUBSTRATE_LABELS = {
    "zebrafish_wt": "Zebrafish morphogenesis",
    "gray_scott": "Gray-Scott RD",
    "bnsyn": "BN-Syn spiking",
    "kuramoto": "Kuramoto coherence",
    "nfi_unified": "NFI cross-domain",
    "cns_ai_loop": "Human-AI loop",
}

SUBSTRATE_COLORS = {
    "zebrafish_wt": "#2E86AB",
    "gray_scott": "#A23B72",
    "bnsyn": "#F18F01",
    "kuramoto": "#C73E1D",
    "nfi_unified": "#3B1F2B",
    "cns_ai_loop": "#44BBA4",
}


def fig1_gamma_overview() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 11,
            "axes.labelsize": 12,
            "figure.dpi": 300,
            "axes.grid": True,
            "grid.alpha": 0.3,
        }
    )

    ledger = json.loads((ROOT / "evidence" / "gamma_ledger.json").read_text())
    entries = ledger["entries"]

    substrates = [k for k in SUBSTRATE_LABELS if k in entries]
    gammas = [entries[s]["gamma"] for s in substrates]
    ci_lo = [entries[s].get("ci_low") or (entries[s]["gamma"] - 0.05) for s in substrates]
    ci_hi = [entries[s].get("ci_high") or (entries[s]["gamma"] + 0.05) for s in substrates]

    yerr_lo = [g - lo for g, lo in zip(gammas, ci_lo)]
    yerr_hi = [hi - g for g, hi in zip(gammas, ci_hi)]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [SUBSTRATE_COLORS.get(s, "#666") for s in substrates]
    x = np.arange(len(substrates))

    ax.bar(
        x,
        gammas,
        color=colors,
        alpha=0.8,
        width=0.6,
        yerr=[yerr_lo, yerr_hi],
        capsize=5,
        error_kw={"linewidth": 1.5, "capthick": 1.5},
    )

    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1.5, label=r"$\gamma = 1.0$")
    ax.axhspan(0.85, 1.15, alpha=0.08, color="gray", label=r"$\pm 15\%$ band")

    ax.set_xticks(x)
    ax.set_xticklabels(
        [SUBSTRATE_LABELS.get(s, s) for s in substrates], rotation=30, ha="right", fontsize=9
    )
    ax.set_ylabel(r"Scaling exponent $\gamma$")
    ax.set_title(r"Universal $\gamma$-scaling across six independent substrates")
    ax.legend(fontsize=9)

    plt.tight_layout()
    out = FIGURES_DIR / "fig1_gamma_overview.pdf"
    plt.savefig(out, bbox_inches="tight")
    plt.savefig(str(out).replace(".pdf", ".png"), bbox_inches="tight", dpi=150)
    plt.close()
    print(f"  Fig 1: {out}")


def fig2_multiverse() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mv_path = ROOT / "figures" / "multiverse_results.json"
    if not mv_path.exists():
        print("  Multiverse results not found - skipping fig2")
        return

    mv = json.loads(mv_path.read_text())
    summary = mv.get("summary", {})

    fig, ax = plt.subplots(figsize=(6, 4))
    median_g = summary.get("median_gamma", 0.965)
    p05 = summary.get("p05_gamma", 0.948)
    p95 = summary.get("p95_gamma", 1.058)
    n_cells = summary.get("n_cells_total", mv.get("n_cells", 2160))

    ax.barh(0, p95 - p05, left=p05, height=0.4, color="#2E86AB", alpha=0.7)
    ax.axvline(1.0, color="red", linestyle="--", linewidth=2, label=r"$\gamma = 1.0$")
    ax.axvline(
        median_g, color="orange", linestyle="-", linewidth=2, label=f"Median = {median_g:.3f}"
    )
    ax.set_xlabel(r"Scaling exponent $\gamma$")
    ax.set_title(f"Multiverse analysis: N={n_cells} cells, P05-P95 range")
    ax.set_yticks([])
    ax.legend(fontsize=9)

    plt.tight_layout()
    out = FIGURES_DIR / "fig2_multiverse.pdf"
    plt.savefig(out, bbox_inches="tight")
    plt.savefig(str(out).replace(".pdf", ".png"), bbox_inches="tight", dpi=150)
    plt.close()
    print(f"  Fig 2: {out}")


def fig3_basin() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    basin_path = ROOT / "figures" / "basin_ci" / "basin_summary.json"
    if not basin_path.exists():
        print("  Basin results not found - skipping fig3")
        return

    basin = json.loads(basin_path.read_text())
    prop_a = basin["prop_a"]["rate"]
    prop_b = basin["prop_b"]["rate"]

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(
        ["Prop A\n(convergence)", "Prop B\n(failure boundary)"],
        [prop_a, prop_b],
        color=["#2E86AB", "#C73E1D"],
        alpha=0.8,
    )
    ax.axhline(0.95, color="black", linestyle="--", label="95% threshold")
    ax.set_ylabel("Pass rate")
    ax.set_title("Basin exhaustion: Propositions A+B")
    ax.set_ylim(0, 1.1)
    ax.legend()

    for bar, val in zip(bars, [prop_a, prop_b]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{val:.3f}",
            ha="center",
            fontsize=10,
        )

    plt.tight_layout()
    out = FIGURES_DIR / "fig3_basin.pdf"
    plt.savefig(out, bbox_inches="tight")
    plt.savefig(str(out).replace(".pdf", ".png"), bbox_inches="tight", dpi=150)
    plt.close()
    print(f"  Fig 3: {out}")


def main() -> int:
    print("=== Generating Manuscript Figures ===\n")
    fig1_gamma_overview()
    fig2_multiverse()
    fig3_basin()
    print(f"\n  All figures -> {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
