#!/usr/bin/env python3
"""Visualize temperature ablation experiment results.

This script generates publication-quality figures from experiment results.

Usage
-----
python -m scripts.visualize_experiment --run-id temp_ablation_v1
python -m scripts.visualize_experiment --run-id temp_ablation_v1 --results results/temp_ablation_v1 --out figures
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Use non-interactive backend for CI/server environments
matplotlib.use("Agg")


def load_condition_results(results_dir: Path, condition: str) -> dict[str, Any]:
    """Load results for a specific condition.

    Parameters
    ----------
    results_dir : Path
        Results directory.
    condition : str
        Condition name.

    Returns
    -------
    dict[str, Any]
        Condition results.
    """
    condition_file = results_dir / f"{condition}.json"
    if not condition_file.exists():
        raise FileNotFoundError(f"Condition results not found: {condition_file}")

    with open(condition_file, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def plot_stability_comparison(results_dir: Path, output_path: Path, conditions: list[str]) -> None:
    """Generate stability variance comparison bar plot.

    Parameters
    ----------
    results_dir : Path
        Results directory.
    output_path : Path
        Output path for figure.
    conditions : list[str]
        List of condition names.
    """
    condition_data = {}
    for condition in conditions:
        data = load_condition_results(results_dir, condition)
        condition_data[condition] = data["aggregates"]

    # Extract metrics
    w_cons_vars = [condition_data[c]["stability_w_cons_var_end"] for c in conditions]
    w_total_vars = [condition_data[c]["stability_w_total_var_end"] for c in conditions]

    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # w_cons variance
    ax1.bar(range(len(conditions)), w_cons_vars, color=["#2E86AB", "#A23B72", "#F18F01", "#C73E1D"])
    ax1.set_xticks(range(len(conditions)))
    ax1.set_xticklabels([c.replace("_", "\n") for c in conditions], rotation=0, ha="center")
    ax1.set_ylabel("Variance", fontsize=12)
    ax1.set_title("w_cons Stability Variance (Lower = Better)", fontsize=13, fontweight="bold")
    ax1.grid(axis="y", alpha=0.3)

    # w_total variance
    ax2.bar(
        range(len(conditions)), w_total_vars, color=["#2E86AB", "#A23B72", "#F18F01", "#C73E1D"]
    )
    ax2.set_xticks(range(len(conditions)))
    ax2.set_xticklabels([c.replace("_", "\n") for c in conditions], rotation=0, ha="center")
    ax2.set_ylabel("Variance", fontsize=12)
    ax2.set_title("w_total Stability Variance (Lower = Better)", fontsize=13, fontweight="bold")
    ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def plot_temperature_vs_stability(
    results_dir: Path, output_path: Path, conditions: list[str]
) -> None:
    """Generate temperature profile vs stability scatter plot.

    Parameters
    ----------
    results_dir : Path
        Results directory.
    output_path : Path
        Output path for figure.
    conditions : list[str]
        List of condition names.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = {
        "cooling_geometric": "#2E86AB",
        "fixed_high": "#A23B72",
        "fixed_low": "#F18F01",
        "random_T": "#C73E1D",
    }

    for condition in conditions:
        data = load_condition_results(results_dir, condition)
        agg = data["aggregates"]

        # Get mean temperature from first trial trajectory
        if data["trials"]:
            temp_traj = data["trials"][0]["trajectories"]["temperature"]
            mean_temp = np.mean(temp_traj)
        else:
            mean_temp = 0.5

        w_total_var = agg["stability_w_total_var_end"]

        ax.scatter(
            mean_temp,
            w_total_var,
            s=200,
            alpha=0.7,
            color=colors.get(condition, "#888888"),
            edgecolor="black",
            linewidth=1.5,
            label=condition.replace("_", " "),
        )

    ax.set_xlabel("Mean Temperature", fontsize=12)
    ax.set_ylabel("w_total Stability Variance", fontsize=12)
    ax.set_title("Temperature vs Stability", fontsize=14, fontweight="bold")
    ax.legend(loc="best", fontsize=10)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def plot_tag_activity(results_dir: Path, output_path: Path, conditions: list[str]) -> None:
    """Generate tag activity over time plot.

    Parameters
    ----------
    results_dir : Path
        Results directory.
    output_path : Path
        Output path for figure.
    conditions : list[str]
        List of condition names.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = {
        "cooling_geometric": "#2E86AB",
        "fixed_high": "#A23B72",
        "fixed_low": "#F18F01",
        "random_T": "#C73E1D",
    }

    for condition in conditions:
        data = load_condition_results(results_dir, condition)

        # Average tag trajectories across trials
        all_tag_trajs = [trial["trajectories"]["tag_frac"] for trial in data["trials"]]
        mean_tag_traj = np.mean(all_tag_trajs, axis=0)

        time_points = np.arange(len(mean_tag_traj)) * 50  # Every 50 steps

        ax.plot(
            time_points,
            mean_tag_traj,
            label=condition.replace("_", " "),
            color=colors.get(condition, "#888888"),
            linewidth=2,
            alpha=0.8,
        )

    ax.set_xlabel("Consolidation Step", fontsize=12)
    ax.set_ylabel("Tag Fraction", fontsize=12)
    ax.set_title("Synaptic Tag Activity Over Time", fontsize=14, fontweight="bold")
    ax.legend(loc="best", fontsize=10)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def plot_comparison_grid(results_dir: Path, output_path: Path, conditions: list[str]) -> None:
    """Generate multi-panel comparison grid.

    Parameters
    ----------
    results_dir : Path
        Results directory.
    output_path : Path
        Output path for figure.
    conditions : list[str]
        List of condition names.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = {
        "cooling_geometric": "#2E86AB",
        "fixed_high": "#A23B72",
        "fixed_low": "#F18F01",
        "random_T": "#C73E1D",
    }

    # Panel 1: Temperature trajectories
    ax = axes[0, 0]
    for condition in conditions:
        data = load_condition_results(results_dir, condition)
        if data["trials"]:
            temp_traj = data["trials"][0]["trajectories"]["temperature"]
            time_points = np.arange(len(temp_traj)) * 50
            ax.plot(
                time_points,
                temp_traj,
                label=condition.replace("_", " "),
                color=colors.get(condition, "#888888"),
                linewidth=2,
            )
    ax.set_xlabel("Step")
    ax.set_ylabel("Temperature")
    ax.set_title("Temperature Profiles", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # Panel 2: w_total trajectories
    ax = axes[0, 1]
    for condition in conditions:
        data = load_condition_results(results_dir, condition)
        all_w_total_trajs = [trial["trajectories"]["w_total_mean"] for trial in data["trials"]]
        mean_w_total_traj = np.mean(all_w_total_trajs, axis=0)
        time_points = np.arange(len(mean_w_total_traj)) * 50
        ax.plot(
            time_points,
            mean_w_total_traj,
            label=condition.replace("_", " "),
            color=colors.get(condition, "#888888"),
            linewidth=2,
        )
    ax.set_xlabel("Step")
    ax.set_ylabel("w_total (mean)")
    ax.set_title("Total Weight Dynamics", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # Panel 3: Protein trajectories
    ax = axes[1, 0]
    for condition in conditions:
        data = load_condition_results(results_dir, condition)
        all_protein_trajs = [trial["trajectories"]["protein"] for trial in data["trials"]]
        mean_protein_traj = np.mean(all_protein_trajs, axis=0)
        time_points = np.arange(len(mean_protein_traj)) * 50
        ax.plot(
            time_points,
            mean_protein_traj,
            label=condition.replace("_", " "),
            color=colors.get(condition, "#888888"),
            linewidth=2,
        )
    ax.set_xlabel("Step")
    ax.set_ylabel("Protein")
    ax.set_title("Protein Synthesis", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # Panel 4: Stability metrics summary
    ax = axes[1, 1]
    condition_data = {}
    for condition in conditions:
        data = load_condition_results(results_dir, condition)
        condition_data[condition] = data["aggregates"]

    w_total_vars = [condition_data[c]["stability_w_total_var_end"] for c in conditions]
    ax.bar(
        range(len(conditions)),
        w_total_vars,
        color=[colors.get(c, "#888888") for c in conditions],
        alpha=0.7,
        edgecolor="black",
        linewidth=1.5,
    )
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels(
        [c.replace("_", "\n") for c in conditions], rotation=0, ha="center", fontsize=9
    )
    ax.set_ylabel("Variance")
    ax.set_title("w_total Stability Variance", fontweight="bold")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def main() -> int:
    """Main CLI entry point.

    Returns
    -------
    int
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Visualize temperature ablation experiment results",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Experiment run ID (e.g., temp_ablation_v1)",
    )
    parser.add_argument(
        "--results",
        type=str,
        default=None,
        help="Results directory (default: results/<run-id>)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="figures",
        help="Output directory for figures (default: figures)",
    )

    args = parser.parse_args()

    # Determine paths
    if args.results is None:
        results_dir = Path("results") / args.run_id
    else:
        results_dir = Path(args.results)

    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not results_dir.exists():
        print(f"Error: Results directory not found: {results_dir}", file=sys.stderr)
        return 1

    print(f"Visualizing results from: {results_dir}")
    print(f"Output directory: {output_dir}")

    # Detect available conditions from results directory
    available_files = list(results_dir.glob("*.json"))
    available_conditions = []
    for f in available_files:
        if f.name != "manifest.json":
            condition_name = f.stem
            available_conditions.append(condition_name)

    # Determine which cooling condition is present
    if "cooling_piecewise" in available_conditions:
        conditions = ["cooling_piecewise", "fixed_high", "fixed_low", "random_T"]
    elif "cooling_geometric" in available_conditions:
        conditions = ["cooling_geometric", "fixed_high", "fixed_low", "random_T"]
    else:
        print(f"Error: No cooling condition found in {results_dir}", file=sys.stderr)
        return 1

    # Filter to only conditions that exist
    conditions = [c for c in conditions if c in available_conditions]
    print(f"Found conditions: {conditions}")

    # Generate all figures
    plot_stability_comparison(results_dir, output_dir / "hero.png", conditions)
    plot_temperature_vs_stability(
        results_dir, output_dir / "temperature_vs_stability.png", conditions
    )
    plot_tag_activity(results_dir, output_dir / "tag_activity.png", conditions)
    plot_comparison_grid(results_dir, output_dir / "comparison_grid.png", conditions)

    print(f"\nVisualization complete! Figures saved to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
