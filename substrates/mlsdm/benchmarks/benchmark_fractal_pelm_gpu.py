#!/usr/bin/env python3
"""Benchmark script for FractalPELMGPU experimental memory module.

This script demonstrates basic usage and performance characteristics
of the GPU/CPU backend for phase-aware retrieval.

NOT integrated into CI - for manual runs only.

Usage:
    python benchmarks/benchmark_fractal_pelm_gpu.py
    python benchmarks/benchmark_fractal_pelm_gpu.py --mode quick
    python benchmarks/benchmark_fractal_pelm_gpu.py --mode full --num-vectors 10000

Modes:
    quick: Reduced workload for fast validation (default)
    full: Complete stress test with larger datasets
"""

from __future__ import annotations

import argparse
import gc
import logging
import sys
import time
import tracemalloc

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def check_torch_available() -> tuple[bool, str | None, bool]:
    """Check if torch is available.

    Returns:
        Tuple of (torch_available, version, cuda_available)
    """
    try:
        import torch

        return True, torch.__version__, torch.cuda.is_available()
    except ImportError:
        return False, None, False


def benchmark_fractal_pelm_gpu(
    num_vectors: int = 5_000,
    num_queries: int = 100,
    dimension: int = 384,
    capacity: int = 10_000,
    top_k: int = 10,
) -> int:
    """Run FractalPELMGPU benchmark.

    Args:
        num_vectors: Number of vectors to store
        num_queries: Number of queries to run
        dimension: Vector dimension
        capacity: Memory capacity
        top_k: Number of results to retrieve

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    torch_available, torch_version, cuda_available = check_torch_available()

    print("=" * 70)
    print("FractalPELMGPU BENCHMARK (Experimental)")
    print("=" * 70)
    print()
    print(f"PyTorch available: {torch_available}")
    if torch_available:
        print(f"PyTorch version: {torch_version}")
        print(f"CUDA available: {cuda_available}")
    print()

    if not torch_available:
        print("ERROR: PyTorch is required for this benchmark.")
        print("Install with: pip install mlsdm[neurolang]")
        return 1

    # Import after checking
    from mlsdm.memory.experimental import FractalPELMGPU

    print("Configuration:")
    print(f"  Dimension: {dimension}")
    print(f"  Capacity: {capacity}")
    print(f"  Vectors to store: {num_vectors}")
    print(f"  Queries: {num_queries}")
    print(f"  Top-k: {top_k}")
    print()

    # Prepare data
    np.random.seed(42)
    vectors = np.random.randn(num_vectors, dimension).astype(np.float32)
    phases = np.random.rand(num_vectors).astype(np.float32)
    query_vectors = np.random.randn(num_queries, dimension).astype(np.float32)
    query_phases = np.random.rand(num_queries).astype(np.float32)

    # CPU benchmark
    print("-" * 70)
    print("CPU BENCHMARK")
    print("-" * 70)

    gc.collect()
    tracemalloc.start()

    memory_cpu = FractalPELMGPU(
        dimension=dimension,
        capacity=capacity,
        device="cpu",
        use_amp=False,
        fractal_weight=0.3,
    )

    # Measure entangle time
    t0 = time.perf_counter()
    memory_cpu.batch_entangle(vectors, phases)
    entangle_time_cpu = time.perf_counter() - t0

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  Entangle time: {entangle_time_cpu * 1000:.2f} ms")
    print(f"  Vectors stored: {memory_cpu.size}")
    print(f"  Memory (current): {current_mem / (1024 * 1024):.2f} MB")
    print(f"  Memory (peak): {peak_mem / (1024 * 1024):.2f} MB")

    # Measure single retrieve
    t0 = time.perf_counter()
    for i in range(num_queries):
        results = memory_cpu.retrieve(query_vectors[i], query_phases[i], top_k=top_k)
    single_retrieve_time_cpu = (time.perf_counter() - t0) / num_queries

    print(f"  Single retrieve (avg): {single_retrieve_time_cpu * 1000:.3f} ms")

    # Measure batch retrieve
    t0 = time.perf_counter()
    results = memory_cpu.batch_retrieve(query_vectors, query_phases, top_k=top_k)
    batch_retrieve_time_cpu = time.perf_counter() - t0

    print(f"  Batch retrieve ({num_queries} queries): {batch_retrieve_time_cpu * 1000:.2f} ms")
    print(f"  Throughput: {num_queries / batch_retrieve_time_cpu:.1f} queries/sec")

    # Sample result
    print("  Sample result (first query, top-3):")
    for i, (score, vec, _meta) in enumerate(results[0][:3]):
        print(f"    #{i+1}: score={score:.4f}, vec_norm={np.linalg.norm(vec):.2f}")

    # GPU benchmark if available
    if cuda_available:
        print()
        print("-" * 70)
        print("GPU (CUDA) BENCHMARK")
        print("-" * 70)

        import torch

        # Warm up GPU
        _ = torch.zeros(1, device="cuda")
        torch.cuda.synchronize()

        gc.collect()
        torch.cuda.empty_cache()

        memory_gpu = FractalPELMGPU(
            dimension=dimension,
            capacity=capacity,
            device="cuda",
            use_amp=True,
            fractal_weight=0.3,
        )

        # Measure entangle time
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        memory_gpu.batch_entangle(vectors, phases)
        torch.cuda.synchronize()
        entangle_time_gpu = time.perf_counter() - t0

        print(f"  Entangle time: {entangle_time_gpu * 1000:.2f} ms")
        print(f"  Vectors stored: {memory_gpu.size}")
        print(f"  GPU memory allocated: {torch.cuda.memory_allocated() / (1024 * 1024):.2f} MB")

        # Measure single retrieve
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        for i in range(num_queries):
            results = memory_gpu.retrieve(query_vectors[i], query_phases[i], top_k=top_k)
        torch.cuda.synchronize()
        single_retrieve_time_gpu = (time.perf_counter() - t0) / num_queries

        print(f"  Single retrieve (avg): {single_retrieve_time_gpu * 1000:.3f} ms")

        # Measure batch retrieve
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        results = memory_gpu.batch_retrieve(query_vectors, query_phases, top_k=top_k)
        torch.cuda.synchronize()
        batch_retrieve_time_gpu = time.perf_counter() - t0

        print(f"  Batch retrieve ({num_queries} queries): {batch_retrieve_time_gpu * 1000:.2f} ms")
        print(f"  Throughput: {num_queries / batch_retrieve_time_gpu:.1f} queries/sec")

        # Speedup
        print()
        print("SPEEDUP (GPU vs CPU):")
        print(f"  Entangle: {entangle_time_cpu / entangle_time_gpu:.2f}x")
        print(f"  Single retrieve: {single_retrieve_time_cpu / single_retrieve_time_gpu:.2f}x")
        print(f"  Batch retrieve: {batch_retrieve_time_cpu / batch_retrieve_time_gpu:.2f}x")

    print()
    print("=" * 70)
    print("Benchmark complete.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="FractalPELMGPU benchmark for experimental memory module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  quick - Reduced workload for fast validation (1000 vectors, 50 queries)
  full  - Complete stress test (10000 vectors, 500 queries)
        """,
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["quick", "full"],
        default="quick",
        help="Benchmark mode (default: quick)",
    )
    parser.add_argument(
        "--num-vectors",
        type=int,
        default=None,
        help="Override number of vectors to store",
    )
    parser.add_argument(
        "--num-queries",
        type=int,
        default=None,
        help="Override number of queries to run",
    )
    args = parser.parse_args(argv)

    # Set defaults based on mode
    if args.mode == "quick":
        num_vectors = args.num_vectors or 1_000
        num_queries = args.num_queries or 50
    else:  # full
        num_vectors = args.num_vectors or 10_000
        num_queries = args.num_queries or 500

    return benchmark_fractal_pelm_gpu(
        num_vectors=num_vectors,
        num_queries=num_queries,
    )


if __name__ == "__main__":
    sys.exit(main())
