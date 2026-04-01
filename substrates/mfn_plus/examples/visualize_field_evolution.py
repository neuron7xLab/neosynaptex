#!/usr/bin/env python3
"""
Visualize field evolution with matplotlib animation.

This script demonstrates how to create animated visualizations of
MyceliumFractalNet field evolution over time.

Usage:
    python examples/visualize_field_evolution.py [--grid-size 64] [--steps 100] \\
        [--output evolution.gif]
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from mycelium_fractal_net import (
    make_simulation_config_demo,
    run_mycelium_simulation_with_history,
)


def create_evolution_animation(result, output_path=None, fps=10):
    """
    Create an animation of field evolution.

    Args:
        result: Simulation result with field_history
        output_path: Path to save animation (None for display only)
        fps: Frames per second for animation
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Initialize with first frame
    im = ax.imshow(
        result.field_history[0],
        cmap="viridis",
        vmin=-100,
        vmax=50,
        animated=True,
        interpolation="bilinear",
    )

    # Add colorbar
    plt.colorbar(im, ax=ax, label="Membrane Potential (mV)")

    # Setup labels
    ax.set_xlabel("X Position", fontsize=12)
    ax.set_ylabel("Y Position", fontsize=12)
    title = ax.set_title("Field Evolution: t=0", fontsize=14, pad=20)

    # Add text for statistics
    stats_text = ax.text(
        0.02,
        0.98,
        "",
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.7),
        fontsize=10,
    )

    def update(frame):
        """Update function for animation."""
        field = result.field_history[frame]
        im.set_array(field)
        title.set_text(f"Field Evolution: t={frame}/{len(result.field_history) - 1}")

        # Update statistics
        stats_text.set_text(
            f"Mean: {field.mean():.1f} mV\n"
            f"Std: {field.std():.1f} mV\n"
            f"Min: {field.min():.1f} mV\n"
            f"Max: {field.max():.1f} mV"
        )

        return [im, title, stats_text]

    # Create animation
    # Sample frames to target ~100 frames max for reasonable file size
    # For 200 steps: every 2nd frame. For 50 steps: every frame
    max_frames = 100
    frames = range(0, len(result.field_history), max(1, len(result.field_history) // max_frames))
    anim = FuncAnimation(fig, update, frames=frames, interval=1000 // fps, blit=True, repeat=True)

    # Save or show
    if output_path:
        print(f"Saving animation to {output_path}...")
        writer = PillowWriter(fps=fps)
        anim.save(output_path, writer=writer)
        print("✓ Animation saved")
    else:
        print("Displaying animation (close window to exit)...")
        plt.show()

    return anim


def create_multi_view(result, output_path=None):
    """
    Create a multi-panel view of the simulation.

    Args:
        result: Simulation result
        output_path: Path to save figure (None for display only)
    """
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # 1. Initial state
    ax1 = fig.add_subplot(gs[0, 0])
    im1 = ax1.imshow(result.field_history[0], cmap="viridis", vmin=-100, vmax=50)
    ax1.set_title("Initial State (t=0)", fontsize=12)
    ax1.set_xlabel("X")
    ax1.set_ylabel("Y")
    plt.colorbar(im1, ax=ax1, label="Potential (mV)")

    # 2. Mid state
    mid_idx = len(result.field_history) // 2
    ax2 = fig.add_subplot(gs[0, 1])
    im2 = ax2.imshow(result.field_history[mid_idx], cmap="viridis", vmin=-100, vmax=50)
    ax2.set_title(f"Mid State (t={mid_idx})", fontsize=12)
    ax2.set_xlabel("X")
    ax2.set_ylabel("Y")
    plt.colorbar(im2, ax=ax2, label="Potential (mV)")

    # 3. Final state
    ax3 = fig.add_subplot(gs[0, 2])
    im3 = ax3.imshow(result.field_final, cmap="viridis", vmin=-100, vmax=50)
    ax3.set_title(f"Final State (t={len(result.field_history) - 1})", fontsize=12)
    ax3.set_xlabel("X")
    ax3.set_ylabel("Y")
    plt.colorbar(im3, ax=ax3, label="Potential (mV)")

    # 4. Potential distribution
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.hist(result.field_final.flatten(), bins=50, alpha=0.7, edgecolor="black")
    ax4.axvline(
        result.field_final.mean(),
        color="red",
        linestyle="--",
        label=f"Mean: {result.field_final.mean():.1f} mV",
    )
    ax4.set_xlabel("Membrane Potential (mV)", fontsize=11)
    ax4.set_ylabel("Frequency", fontsize=11)
    ax4.set_title("Potential Distribution", fontsize=12)
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. Mean potential over time
    ax5 = fig.add_subplot(gs[1, 1])
    mean_potentials = [frame.mean() for frame in result.field_history]
    ax5.plot(mean_potentials, linewidth=2, color="blue")
    ax5.set_xlabel("Time Step", fontsize=11)
    ax5.set_ylabel("Mean Potential (mV)", fontsize=11)
    ax5.set_title("Temporal Evolution", fontsize=12)
    ax5.grid(True, alpha=0.3)

    # 6. Std over time
    ax6 = fig.add_subplot(gs[1, 2])
    std_potentials = [frame.std() for frame in result.field_history]
    ax6.plot(std_potentials, linewidth=2, color="green")
    ax6.set_xlabel("Time Step", fontsize=11)
    ax6.set_ylabel("Std Deviation (mV)", fontsize=11)
    ax6.set_title("Variability Evolution", fontsize=12)
    ax6.grid(True, alpha=0.3)

    # 7. Binary pattern (for fractal analysis)
    ax7 = fig.add_subplot(gs[2, 0])
    binary = result.field_final > -60
    ax7.imshow(binary, cmap="binary", interpolation="nearest")
    ax7.set_title("Binary Pattern (threshold: -60 mV)", fontsize=12)
    ax7.set_xlabel("X")
    ax7.set_ylabel("Y")

    # 8. Gradient magnitude
    ax8 = fig.add_subplot(gs[2, 1])
    gy, gx = np.gradient(result.field_final)
    gradient_mag = np.sqrt(gx**2 + gy**2)
    im8 = ax8.imshow(gradient_mag, cmap="hot")
    ax8.set_title("Gradient Magnitude", fontsize=12)
    ax8.set_xlabel("X")
    ax8.set_ylabel("Y")
    plt.colorbar(im8, ax=ax8, label="|∇V|")

    # 9. Statistics text
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis("off")
    stats_text = (
        f"Simulation Statistics\n"
        f"{'=' * 30}\n\n"
        f"Grid Size: {result.field_final.shape[0]}×{result.field_final.shape[1]}\n"
        f"Time Steps: {len(result.field_history)}\n\n"
        f"Final Field:\n"
        f"  Mean: {result.field_final.mean():.2f} mV\n"
        f"  Std: {result.field_final.std():.2f} mV\n"
        f"  Min: {result.field_final.min():.2f} mV\n"
        f"  Max: {result.field_final.max():.2f} mV\n\n"
        f"Events:\n"
        f"  Growth: {result.growth_events}\n"
        f"  Turing: {result.turing_activations}\n"
        f"  Clamping: {result.clamping_events}\n"
    )
    ax9.text(
        0.1,
        0.5,
        stats_text,
        fontsize=10,
        verticalalignment="center",
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.5),
    )

    # Overall title
    fig.suptitle("MyceliumFractalNet Field Analysis", fontsize=16, fontweight="bold")

    # Save or show
    if output_path:
        print(f"Saving figure to {output_path}...")
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print("✓ Figure saved")
    else:
        print("Displaying figure (close window to exit)...")
        plt.show()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Visualize MFN field evolution")
    parser.add_argument("--grid-size", type=int, default=64, help="Grid size (default: 64)")
    parser.add_argument("--steps", type=int, default=100, help="Simulation steps (default: 100)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--output", type=str, help="Output path for animation (.gif) or figure (.png)"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Frames per second for animation (default: 10)",
    )
    parser.add_argument(
        "--mode",
        choices=["animation", "multi"],
        default="multi",
        help="Visualization mode (default: multi)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("MyceliumFractalNet Field Visualization")
    print("=" * 60)
    print("Configuration:")
    print(f"  Grid size: {args.grid_size}×{args.grid_size}")
    print(f"  Steps: {args.steps}")
    print(f"  Seed: {args.seed}")
    print(f"  Mode: {args.mode}")
    print()

    # Run simulation
    print("Running simulation...")
    config = make_simulation_config_demo()
    config.grid_size = args.grid_size
    config.steps = args.steps
    config.seed = args.seed

    result = run_mycelium_simulation_with_history(config)

    print("✓ Simulation complete")
    print(f"  Growth events: {result.growth_events}")
    print(f"  Turing activations: {result.turing_activations}")
    print(f"  Potential range: [{result.field_final.min():.1f}, {result.field_final.max():.1f}] mV")
    print()

    # Create visualization
    if args.mode == "animation":
        create_evolution_animation(result, args.output, args.fps)
    else:
        create_multi_view(result, args.output)


if __name__ == "__main__":
    main()
