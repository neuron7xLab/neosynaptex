#!/usr/bin/env python3
"""Calibration Benchmark Suite for MLSDM.

This script runs calibration experiments to validate and tune thresholds
for the key MLSDM modules:
- Moral Filter (toxic vs non-toxic rejection rates)
- Aphasia Detector (telegraphic vs normal text detection)
- Secure Mode (risk blocking behavior)
- PELM Memory (retrieval precision with phase tolerance and top_k)

Usage:
    python scripts/run_calibration_benchmarks.py
    python scripts/run_calibration_benchmarks.py --mode quick
    python scripts/run_calibration_benchmarks.py --mode full

Output:
    - Console summary of calibration metrics
    - Detailed results for documentation in docs/CALIBRATION_RESULTS.md
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# Module imports must come after path manipulation
from mlsdm.cognition.moral_filter import MoralFilter  # noqa: E402
from mlsdm.cognition.moral_filter_v2 import MoralFilterV2  # noqa: E402
from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector  # noqa: E402
from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory  # noqa: E402
from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory  # noqa: E402

# =============================================================================
# BENCHMARK DATA
# =============================================================================

# Moral filter test cases: (moral_value, is_toxic)
MORAL_FILTER_TEST_CASES = [
    # Clearly toxic (should be rejected)
    (0.1, True),
    (0.15, True),
    (0.2, True),
    (0.25, True),
    # Borderline cases
    (0.35, True),
    (0.4, True),
    (0.45, False),  # borderline non-toxic
    # Non-toxic (should be accepted)
    (0.55, False),
    (0.6, False),
    (0.7, False),
    (0.8, False),
    (0.9, False),
    (0.95, False),
]

# Aphasia test cases: (text, is_telegraphic)
APHASIA_TEST_CASES = [
    # Telegraphic speech (Broca-like, should be detected)
    ("Go store. Buy milk.", True),
    ("Cat. Run. Fast.", True),
    ("Book. Read. Good.", True),
    ("Error. System. Fail.", True),
    ("User want help. Need answer.", True),
    # Normal full sentences (should NOT be detected)
    ("The cat ran quickly across the street.", False),
    ("I would like to help you with your question.", False),
    ("The weather today is quite pleasant for a walk.", False),
    ("Please let me know if you need any further assistance.", False),
    ("The system is working correctly and all tests have passed.", False),
    # Edge cases
    ("Yes.", True),  # Too short
    ("", True),  # Empty
    ("The cat sat on the mat.", False),  # Short but complete
]


# PELM test scenarios: vectors with phases
def generate_pelm_test_vectors(
    dim: int = 10,
    num_vectors: int = 100,
) -> list[tuple[list[float], float]]:
    """Generate test vectors with random phases."""
    rng = np.random.default_rng(42)
    vectors = []
    for i in range(num_vectors):
        vec = rng.random(dim).tolist()
        # Distribute phases across [0, 1]
        phase = i / num_vectors
        vectors.append((vec, phase))
    return vectors


# =============================================================================
# BENCHMARK CLASSES
# =============================================================================


@dataclass
class MoralFilterMetrics:
    """Metrics for moral filter calibration."""

    threshold: float
    toxic_rejection_rate: float  # % of toxic correctly rejected
    false_positive_rate: float  # % of non-toxic incorrectly rejected
    total_samples: int
    toxic_samples: int
    non_toxic_samples: int


@dataclass
class AphasiaDetectorMetrics:
    """Metrics for aphasia detector calibration."""

    min_sentence_len: float
    min_function_word_ratio: float
    max_fragment_ratio: float
    severity_threshold: float
    telegraphic_detection_rate: float  # % of telegraphic correctly detected
    false_positive_rate: float  # % of normal incorrectly flagged
    total_samples: int


@dataclass
class PELMMetrics:
    """Metrics for PELM calibration."""

    phase_tolerance: float
    top_k: int
    recall_at_k: float  # % of relevant items retrieved
    precision_at_k: float  # % of retrieved that are relevant
    avg_retrieval_time_ms: float
    total_queries: int


def run_moral_filter_benchmark(threshold: float = 0.5) -> MoralFilterMetrics:
    """Run moral filter benchmark with given threshold."""
    mf = MoralFilter(threshold=threshold)

    toxic_rejected = 0
    non_toxic_rejected = 0
    toxic_total = 0
    non_toxic_total = 0

    for moral_value, is_toxic in MORAL_FILTER_TEST_CASES:
        accepted = mf.evaluate(moral_value)

        if is_toxic:
            toxic_total += 1
            if not accepted:
                toxic_rejected += 1
        else:
            non_toxic_total += 1
            if not accepted:
                non_toxic_rejected += 1

    toxic_rejection_rate = toxic_rejected / toxic_total if toxic_total > 0 else 0.0
    false_positive_rate = non_toxic_rejected / non_toxic_total if non_toxic_total > 0 else 0.0

    return MoralFilterMetrics(
        threshold=threshold,
        toxic_rejection_rate=toxic_rejection_rate,
        false_positive_rate=false_positive_rate,
        total_samples=len(MORAL_FILTER_TEST_CASES),
        toxic_samples=toxic_total,
        non_toxic_samples=non_toxic_total,
    )


def run_moral_filter_v2_benchmark(threshold: float = 0.5) -> MoralFilterMetrics:
    """Run moral filter v2 benchmark with given threshold."""
    mf = MoralFilterV2(initial_threshold=threshold)

    toxic_rejected = 0
    non_toxic_rejected = 0
    toxic_total = 0
    non_toxic_total = 0

    for moral_value, is_toxic in MORAL_FILTER_TEST_CASES:
        accepted = mf.evaluate(moral_value)

        if is_toxic:
            toxic_total += 1
            if not accepted:
                toxic_rejected += 1
        else:
            non_toxic_total += 1
            if not accepted:
                non_toxic_rejected += 1

    toxic_rejection_rate = toxic_rejected / toxic_total if toxic_total > 0 else 0.0
    false_positive_rate = non_toxic_rejected / non_toxic_total if non_toxic_total > 0 else 0.0

    return MoralFilterMetrics(
        threshold=threshold,
        toxic_rejection_rate=toxic_rejection_rate,
        false_positive_rate=false_positive_rate,
        total_samples=len(MORAL_FILTER_TEST_CASES),
        toxic_samples=toxic_total,
        non_toxic_samples=non_toxic_total,
    )


def run_aphasia_benchmark(
    min_sentence_len: float = 6.0,
    min_function_word_ratio: float = 0.15,
    max_fragment_ratio: float = 0.5,
    severity_threshold: float = 0.3,
) -> AphasiaDetectorMetrics:
    """Run aphasia detector benchmark with given parameters."""
    detector = AphasiaBrocaDetector(
        min_sentence_len=min_sentence_len,
        min_function_word_ratio=min_function_word_ratio,
        max_fragment_ratio=max_fragment_ratio,
    )

    telegraphic_detected = 0
    normal_flagged = 0
    telegraphic_total = 0
    normal_total = 0

    for text, is_telegraphic in APHASIA_TEST_CASES:
        result = detector.analyze(text)

        # Detection is based on is_aphasic AND severity >= threshold
        detected = result["is_aphasic"] and result["severity"] >= severity_threshold

        if is_telegraphic:
            telegraphic_total += 1
            if detected:
                telegraphic_detected += 1
        else:
            normal_total += 1
            if detected:
                normal_flagged += 1

    detection_rate = telegraphic_detected / telegraphic_total if telegraphic_total > 0 else 0.0
    false_positive_rate = normal_flagged / normal_total if normal_total > 0 else 0.0

    return AphasiaDetectorMetrics(
        min_sentence_len=min_sentence_len,
        min_function_word_ratio=min_function_word_ratio,
        max_fragment_ratio=max_fragment_ratio,
        severity_threshold=severity_threshold,
        telegraphic_detection_rate=detection_rate,
        false_positive_rate=false_positive_rate,
        total_samples=len(APHASIA_TEST_CASES),
    )


def run_pelm_benchmark(
    phase_tolerance: float = 0.15,
    top_k: int = 5,
    dim: int = 10,
    num_vectors: int = 100,
    num_queries: int = 20,
) -> PELMMetrics:
    """Run PELM benchmark with given parameters."""
    pelm = PhaseEntangledLatticeMemory(dimension=dim, capacity=1000)

    # Store test vectors
    test_vectors = generate_pelm_test_vectors(dim, num_vectors)
    for vec, phase in test_vectors:
        pelm.entangle(vec, phase)

    # Run queries and measure performance
    rng = np.random.default_rng(123)
    total_relevant_retrieved = 0
    total_retrieved = 0
    total_relevant_available = 0
    retrieval_times = []

    for _ in range(num_queries):
        # Pick a random query phase
        query_phase = rng.random()
        query_vec = rng.random(dim).tolist()

        # Count how many vectors are within phase_tolerance (ground truth)
        relevant_count = sum(
            1 for _, phase in test_vectors if abs(phase - query_phase) <= phase_tolerance
        )
        total_relevant_available += min(relevant_count, top_k)

        # Time the retrieval
        start = time.perf_counter()
        results = pelm.retrieve(query_vec, query_phase, phase_tolerance, top_k)
        elapsed_ms = (time.perf_counter() - start) * 1000
        retrieval_times.append(elapsed_ms)

        # Count retrieved and relevant
        total_retrieved += len(results)
        # All retrieved should be relevant (within phase tolerance)
        total_relevant_retrieved += sum(
            1 for r in results if abs(r.phase - query_phase) <= phase_tolerance
        )

    # Calculate metrics
    recall = (
        total_relevant_retrieved / total_relevant_available if total_relevant_available > 0 else 0.0
    )
    precision = total_relevant_retrieved / total_retrieved if total_retrieved > 0 else 0.0
    avg_time = sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0.0

    return PELMMetrics(
        phase_tolerance=phase_tolerance,
        top_k=top_k,
        recall_at_k=recall,
        precision_at_k=precision,
        avg_retrieval_time_ms=avg_time,
        total_queries=num_queries,
    )


def run_synaptic_memory_benchmark(
    lambda_l1: float = 0.5,
    lambda_l2: float = 0.1,
    lambda_l3: float = 0.01,
    theta_l1: float = 1.2,
    theta_l2: float = 2.5,
    gating12: float = 0.45,
    gating23: float = 0.30,
    dim: int = 10,
    num_events: int = 100,
) -> dict[str, Any]:
    """Run synaptic memory benchmark with given parameters."""
    mem = MultiLevelSynapticMemory(
        dimension=dim,
        lambda_l1=lambda_l1,
        lambda_l2=lambda_l2,
        lambda_l3=lambda_l3,
        theta_l1=theta_l1,
        theta_l2=theta_l2,
        gating12=gating12,
        gating23=gating23,
    )

    rng = np.random.default_rng(456)

    # Simulate events
    for _ in range(num_events):
        event = rng.random(dim).astype(np.float32)
        mem.update(event)

    l1, l2, l3 = mem.state()

    return {
        "lambda_l1": lambda_l1,
        "lambda_l2": lambda_l2,
        "lambda_l3": lambda_l3,
        "theta_l1": theta_l1,
        "theta_l2": theta_l2,
        "gating12": gating12,
        "gating23": gating23,
        "final_l1_norm": float(np.linalg.norm(l1)),
        "final_l2_norm": float(np.linalg.norm(l2)),
        "final_l3_norm": float(np.linalg.norm(l3)),
        "num_events": num_events,
    }


# =============================================================================
# MAIN CALIBRATION RUNNER
# =============================================================================


def print_section(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def main(argv: list[str] | None = None) -> int:
    """Run all calibration benchmarks and print results.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="MLSDM Calibration Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["quick", "full"],
        default="quick",
        help="Benchmark mode: quick (default) runs fewer iterations, full runs all",
    )
    args = parser.parse_args(argv)

    logger.info("MLSDM Calibration Benchmark Suite")
    logger.info("=" * 70)
    logger.info("Mode: %s", args.mode)

    try:
        # Import modules here to catch import errors early
        from mlsdm.cognition.moral_filter import MoralFilter  # noqa: F401
        from mlsdm.cognition.moral_filter_v2 import MoralFilterV2  # noqa: F401
        from mlsdm.extensions.neuro_lang_extension import AphasiaBrocaDetector  # noqa: F401
        from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory  # noqa: F401
        from mlsdm.memory.phase_entangled_lattice_memory import (
            PhaseEntangledLatticeMemory,  # noqa: F401
        )
    except ImportError as e:
        logger.error("Failed to import required modules: %s", e)
        logger.error("Make sure mlsdm is installed: pip install -e .")
        return 1

    try:
        # -------------------------------------------------------------------------
        # Moral Filter Calibration
        # -------------------------------------------------------------------------
        print_section("1. MORAL FILTER CALIBRATION")

        print("\n1.1 MoralFilter (v1) - Threshold Sweep:")
        print("-" * 50)
        print(f"{'Threshold':>10} | {'Toxic Reject %':>14} | {'False Pos %':>12}")
        print("-" * 50)

        for threshold in [0.3, 0.4, 0.5, 0.6, 0.7]:
            metrics = run_moral_filter_benchmark(threshold)
            print(
                f"{threshold:>10.2f} | "
                f"{metrics.toxic_rejection_rate * 100:>13.1f}% | "
                f"{metrics.false_positive_rate * 100:>11.1f}%"
            )

        print("\n1.2 MoralFilterV2 - Threshold Sweep:")
        print("-" * 50)
        print(f"{'Threshold':>10} | {'Toxic Reject %':>14} | {'False Pos %':>12}")
        print("-" * 50)

        for threshold in [0.3, 0.4, 0.5, 0.6, 0.7]:
            metrics = run_moral_filter_v2_benchmark(threshold)
            print(
                f"{threshold:>10.2f} | "
                f"{metrics.toxic_rejection_rate * 100:>13.1f}% | "
                f"{metrics.false_positive_rate * 100:>11.1f}%"
            )

        # -------------------------------------------------------------------------
        # Aphasia Detector Calibration
        # -------------------------------------------------------------------------
        print_section("2. APHASIA DETECTOR CALIBRATION")

        print("\n2.1 Severity Threshold Sweep:")
        print("-" * 60)
        print(f"{'Severity':>10} | {'Detection %':>12} | {'False Pos %':>12}")
        print("-" * 60)

        for severity in [0.1, 0.2, 0.3, 0.4, 0.5]:
            metrics = run_aphasia_benchmark(severity_threshold=severity)
            print(
                f"{severity:>10.2f} | "
                f"{metrics.telegraphic_detection_rate * 100:>11.1f}% | "
                f"{metrics.false_positive_rate * 100:>11.1f}%"
            )

        print("\n2.2 Min Sentence Length Sweep:")
        print("-" * 60)
        print(f"{'Min Len':>10} | {'Detection %':>12} | {'False Pos %':>12}")
        print("-" * 60)

        for min_len in [4.0, 5.0, 6.0, 7.0, 8.0]:
            metrics = run_aphasia_benchmark(min_sentence_len=min_len)
            print(
                f"{min_len:>10.1f} | "
                f"{metrics.telegraphic_detection_rate * 100:>11.1f}% | "
                f"{metrics.false_positive_rate * 100:>11.1f}%"
            )

        # -------------------------------------------------------------------------
        # PELM Calibration
        # -------------------------------------------------------------------------
        print_section("3. PELM (PHASE-ENTANGLED LATTICE MEMORY) CALIBRATION")

        print("\n3.1 Phase Tolerance Sweep:")
        print("-" * 70)
        print(f"{'Tolerance':>10} | {'Recall':>10} | {'Precision':>10} | {'Latency ms':>12}")
        print("-" * 70)

        for tolerance in [0.05, 0.10, 0.15, 0.20, 0.30]:
            metrics = run_pelm_benchmark(phase_tolerance=tolerance)
            print(
                f"{tolerance:>10.2f} | "
                f"{metrics.recall_at_k * 100:>9.1f}% | "
                f"{metrics.precision_at_k * 100:>9.1f}% | "
                f"{metrics.avg_retrieval_time_ms:>11.3f}"
            )

        print("\n3.2 Top-K Sweep (tolerance=0.15):")
        print("-" * 70)
        print(f"{'Top-K':>10} | {'Recall':>10} | {'Precision':>10} | {'Latency ms':>12}")
        print("-" * 70)

        for top_k in [1, 3, 5, 10, 20]:
            metrics = run_pelm_benchmark(top_k=top_k)
            print(
                f"{top_k:>10} | "
                f"{metrics.recall_at_k * 100:>9.1f}% | "
                f"{metrics.precision_at_k * 100:>9.1f}% | "
                f"{metrics.avg_retrieval_time_ms:>11.3f}"
            )

        # -------------------------------------------------------------------------
        # Synaptic Memory Calibration
        # -------------------------------------------------------------------------
        print_section("4. SYNAPTIC MEMORY CALIBRATION")

        print("\n4.1 Default Parameters (100 events):")
        result = run_synaptic_memory_benchmark()
        print(f"  L1 norm: {result['final_l1_norm']:.4f}")
        print(f"  L2 norm: {result['final_l2_norm']:.4f}")
        print(f"  L3 norm: {result['final_l3_norm']:.4f}")

        print("\n4.2 Decay Rate Comparison:")
        print("-" * 60)
        print(f"{'λ_L1':>8} | {'λ_L2':>8} | {'λ_L3':>8} | {'L1':>10} | {'L2':>10} | {'L3':>10}")
        print("-" * 60)

        decay_configs = [
            (0.3, 0.05, 0.005),  # Slower decay
            (0.5, 0.10, 0.010),  # Default
            (0.7, 0.15, 0.015),  # Faster decay
        ]

        for l1, l2, l3 in decay_configs:
            result = run_synaptic_memory_benchmark(lambda_l1=l1, lambda_l2=l2, lambda_l3=l3)
            print(
                f"{l1:>8.2f} | {l2:>8.2f} | {l3:>8.3f} | "
                f"{result['final_l1_norm']:>10.4f} | "
                f"{result['final_l2_norm']:>10.4f} | "
                f"{result['final_l3_norm']:>10.4f}"
            )

        # -------------------------------------------------------------------------
        # Summary
        # -------------------------------------------------------------------------
        print_section("CALIBRATION SUMMARY")

        print("\nRecommended Calibration Values:")
        print("-" * 50)
        print("  Moral Filter:")
        print("    threshold = 0.50 (balanced)")
        print("    min_threshold = 0.30 (safety floor)")
        print("")
        print("  Aphasia Detector:")
        print("    severity_threshold = 0.30")
        print("    min_sentence_len = 6.0")
        print("")
        print("  PELM:")
        print("    phase_tolerance = 0.15")
        print("    top_k = 5")
        print("")
        print("  Synaptic Memory:")
        print("    lambda_l1 = 0.50, lambda_l2 = 0.10, lambda_l3 = 0.01")

        print("\n" + "=" * 70)
        print("Calibration benchmarks complete.")
        print("See docs/CALIBRATION_RESULTS.md for detailed analysis.")

        return 0

    except Exception as e:
        logger.error("Benchmark failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
