#!/usr/bin/env python3
"""Memory footprint benchmark for MLSDM PELM.

Measures actual memory usage of Phase-Entangled Lattice Memory (PELM)
to verify the documented 29.37 MB footprint claim.

Usage:
    python benchmarks/measure_memory_footprint.py
    python benchmarks/measure_memory_footprint.py --quick
"""

from __future__ import annotations

import gc
import logging
import sys
import tracemalloc

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def measure_pelm_memory() -> float:
    """Measure PELM memory footprint.

    Returns:
        Memory footprint in MB
    """
    from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

    print("=" * 70)
    print("MLSDM MEMORY FOOTPRINT MEASUREMENT")
    print("=" * 70)

    # Force garbage collection before measurement
    gc.collect()

    # Start tracemalloc for accurate measurement
    tracemalloc.start()

    # Create PELM with production configuration
    dimension = 384
    capacity = 20_000

    print("\nConfiguration:")
    print(f"  Dimension: {dimension}")
    print(f"  Capacity: {capacity}")
    print(f"  Expected footprint: {capacity * dimension * 4 / (1024 * 1024):.2f} MB (data only)")

    # Create PELM
    pelm = PhaseEntangledLatticeMemory(dimension=dimension, capacity=capacity)

    # Get baseline memory
    current, peak = tracemalloc.get_traced_memory()
    print("\nAfter PELM creation (empty):")
    print(f"  Current: {current / (1024 * 1024):.2f} MB")
    print(f"  Peak: {peak / (1024 * 1024):.2f} MB")

    # Fill PELM with batch of vectors (faster than one at a time)
    print(f"\nFilling PELM with {capacity} vectors...")
    batch_size = 1000
    for batch_start in range(0, capacity, batch_size):
        batch_end = min(batch_start + batch_size, capacity)
        for i in range(batch_start, batch_end):
            # Use numpy for speed, convert to list for API
            vector = np.random.randn(dimension).astype(np.float32).tolist()
            pelm.entangle(vector, phase=float(i % 11) / 10.0)

        if batch_end % 5000 == 0 or batch_end == capacity:
            current, peak = tracemalloc.get_traced_memory()
            print(f"  At {batch_end} vectors: {current / (1024 * 1024):.2f} MB current")

    # Final measurement
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\nFinal measurements (at capacity):")
    print(f"  Current memory: {current / (1024 * 1024):.2f} MB")
    print(f"  Peak memory: {peak / (1024 * 1024):.2f} MB")

    # Calculate theoretical size
    theoretical_data = capacity * dimension * 4  # 4 bytes per float32
    theoretical_mb = theoretical_data / (1024 * 1024)

    print("\nTheoretical calculation:")
    print(f"  Vector data: {capacity} × {dimension} × 4 bytes = {theoretical_mb:.2f} MB")
    print(f"  Actual measured: {current / (1024 * 1024):.2f} MB")
    print(f"  Overhead: {(current / (1024 * 1024)) - theoretical_mb:.2f} MB")

    # Verify against documented claim
    documented_footprint_mb = 29.37
    measured_mb = current / (1024 * 1024)

    print(f"\n{'=' * 70}")
    print("VERIFICATION AGAINST DOCUMENTED CLAIM")
    print("=" * 70)
    print(f"  Documented: {documented_footprint_mb:.2f} MB")
    print(f"  Measured: {measured_mb:.2f} MB")

    if measured_mb <= documented_footprint_mb * 1.1:  # Allow 10% margin
        print("  Status: ✅ VERIFIED (within 10% of documented value)")
    else:
        deviation = ((measured_mb / documented_footprint_mb) - 1) * 100
        print(f"  Status: ⚠️ EXCEEDS documented value by {deviation:.1f}%")

    print("=" * 70)

    return measured_mb


def measure_cognitive_controller_memory() -> float:
    """Measure full CognitiveController memory footprint.

    Returns:
        Memory footprint in MB
    """
    from mlsdm.core.cognitive_controller import CognitiveController

    print("\n" + "=" * 70)
    print("COGNITIVE CONTROLLER MEMORY FOOTPRINT")
    print("=" * 70)

    gc.collect()
    tracemalloc.start()

    # Create controller with default settings (other params use production defaults)
    dimension = 384  # Standard embedding dimension
    controller = CognitiveController(
        dim=dimension,
    )

    current, peak = tracemalloc.get_traced_memory()
    print("\nAfter CognitiveController creation:")
    print(f"  Current: {current / (1024 * 1024):.2f} MB")
    print(f"  Peak: {peak / (1024 * 1024):.2f} MB")

    # Process some events
    print("\nProcessing 100 events...")
    for _ in range(100):
        vector = np.random.randn(dimension).astype(np.float32)
        vector = vector / np.linalg.norm(vector)
        controller.process_event(vector, moral_value=0.8)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\nAfter processing 100 events:")
    print(f"  Current: {current / (1024 * 1024):.2f} MB")
    print(f"  Peak: {peak / (1024 * 1024):.2f} MB")

    print("=" * 70)

    return current / (1024 * 1024)


def quick_memory_check() -> int:
    """Quick memory check for CI - verifies empty PELM footprint.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

    gc.collect()
    tracemalloc.start()

    _pelm = PhaseEntangledLatticeMemory(dimension=384, capacity=20_000)

    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    measured_mb = current / (1024 * 1024)
    documented_footprint_mb = 29.37

    print(f"Quick check: PELM initial footprint = {measured_mb:.2f} MB")
    print(f"Documented: {documented_footprint_mb:.2f} MB")

    # Verify pre-allocated memory is within expected range
    if measured_mb < 29.0:
        print(f"⚠️ PELM footprint {measured_mb:.2f} MB is too small (expected ~29 MB)")
        return 1
    if measured_mb > 35.0:
        print(f"⚠️ PELM footprint {measured_mb:.2f} MB exceeds limit")
        return 1

    print("✅ Memory footprint within expected range")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run memory benchmarks.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    import argparse
    import json
    import platform
    import subprocess
    from datetime import datetime, timezone

    parser = argparse.ArgumentParser(
        description="MLSDM Memory Footprint Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick check for CI (verify empty PELM footprint only)",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=None,
        help="Path to write JSON output with memory metrics",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for numpy (for determinism)",
    )
    args = parser.parse_args(argv)

    # Set seed if provided for determinism
    if args.seed is not None:
        np.random.seed(args.seed)

    if args.quick:
        return quick_memory_check()

    print("\n" + "=" * 70)
    print("MLSDM MEMORY FOOTPRINT BENCHMARK")
    print("=" * 70)
    print("\nThis benchmark verifies documented memory claims.")
    print("Reference: SLO_SPEC.md, ARCHITECTURE_SPEC.md, CLAIMS_TRACEABILITY.md")

    try:
        pelm_mb = measure_pelm_memory()
        controller_mb = measure_cognitive_controller_memory()

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  PELM (20k vectors, 384 dim): {pelm_mb:.2f} MB")
        print(f"  CognitiveController (full): {controller_mb:.2f} MB")
        print("\n  Documented footprint: 29.37 MB")
        print("=" * 70)

        # Write JSON output if requested
        if args.json_out:
            try:
                git_sha = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip() or "unknown"
            except Exception:
                git_sha = "unknown"

            output = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "commit": git_sha,
                "pelm_mb": round(pelm_mb, 2),
                "controller_mb": round(controller_mb, 2),
                "config": {"dim": 384, "cap": 20000},
                "python": platform.python_version(),
                "platform": platform.platform(),
            }
            with open(args.json_out, "w") as f:
                json.dump(output, f, indent=2)
            print(f"\nJSON output written to: {args.json_out}")

        return 0 if pelm_mb <= 35.0 else 1  # Allow some margin

    except Exception as e:
        logger.error("Benchmark failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
