#!/usr/bin/env python3
"""
Performance Benchmarking Script

Tests performance of key operations and provides a sparse stress test for large inputs.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp

try:
    from core.hierarchical_laminar import CellDataHier, HierarchicalLaminarModel
    from data.biophysical_parameters import get_default_parameters
    from plasticity.unified_weights import (
        UnifiedWeightMatrix,
        create_source_type_matrix,
    )
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    from core.hierarchical_laminar import CellDataHier, HierarchicalLaminarModel
    from data.biophysical_parameters import get_default_parameters
    from plasticity.unified_weights import (
        UnifiedWeightMatrix,
        create_source_type_matrix,
    )


def benchmark_weight_update(N: int = 100, n_iter: int = 1000):
    """Benchmark weight matrix operations."""
    np.random.seed(42)
    params = get_default_parameters()

    connectivity = np.random.rand(N, N) < 0.1
    np.fill_diagonal(connectivity, False)

    layer_assignments = np.random.randint(0, 4, N)
    initial_weights = np.random.lognormal(0, 0.5, (N, N))
    initial_weights = np.clip(initial_weights, 0.01, 10.0)
    source_types = create_source_type_matrix(N, layer_assignments)

    W = UnifiedWeightMatrix(connectivity, initial_weights, source_types, params)

    start = time.time()

    for _ in range(n_iter):
        spikes_pre = np.random.rand(N) < 0.01
        spikes_post = np.random.rand(N) < 0.01
        V_dend = np.random.randn(N) * 10 - 60
        W.update_stp(spikes_pre, spikes_post)
        W.update_calcium(spikes_pre, spikes_post, V_dend)
        if _ % 10 == 0:
            W.update_plasticity_ca_based(M=1.0, G=np.zeros(N))

    elapsed = time.time() - start
    return elapsed, n_iter


def benchmark_laminar_em(N: int = 1000, max_iter: int = 10):
    """Benchmark laminar EM."""
    np.random.seed(42)

    cells = []
    for i in range(N):
        z = np.random.rand()
        layer = min(int(z * 4), 3)
        transcripts = np.zeros(4)
        transcripts[layer] = np.random.poisson(5)
        cells.append(
            CellDataHier(
                cell_id=i,
                animal_id=0,
                x=np.random.rand(),
                y=np.random.rand(),
                z=z,
                s=np.random.rand(),
                transcripts=transcripts,
            )
        )

    model = HierarchicalLaminarModel(lambda_mrf=0.0)

    start = time.time()
    q = model.fit_em_vectorized(cells, max_iter=max_iter, verbose=False)
    elapsed = time.time() - start

    return elapsed, N, q


def stress_test_sparse(
    neurons: int = 100_000, conn_prob: float = 1e-4, steps: int = 5, seed: int = 42
):
    """
    Sparse stress test for large neuron counts.

    Uses a CSR adjacency matrix to avoid dense O(N^2) memory while probing throughput.
    """
    rng = np.random.default_rng(seed)
    conn = sp.random(
        neurons,
        neurons,
        density=conn_prob,
        format="csr",
        data_rvs=rng.random,
    )
    spikes = rng.random((steps, neurons)) < 0.001

    start = time.time()
    for step in range(steps):
        _ = conn @ spikes[step].astype(np.float32)
    elapsed = time.time() - start

    bytes_used = conn.data.nbytes + conn.indptr.nbytes + conn.indices.nbytes + spikes.nbytes
    return elapsed, conn.nnz, bytes_used / (1024 * 1024)


def parse_args():
    parser = argparse.ArgumentParser(description="Performance and stress benchmarks")
    parser.add_argument(
        "--neurons",
        type=int,
        default=100,
        help="Neurons for weight benchmark (default: 100)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Iterations for weight benchmark",
    )
    parser.add_argument(
        "--laminar-cells",
        type=int,
        default=1000,
        help="Cells for laminar EM benchmark",
    )
    parser.add_argument(
        "--laminar-iter",
        type=int,
        default=10,
        help="Iterations for laminar EM benchmark",
    )
    parser.add_argument(
        "--stress-neurons",
        type=int,
        default=0,
        help="Run sparse stress test with this many neurons (0 to skip)",
    )
    parser.add_argument(
        "--stress-steps",
        type=int,
        default=5,
        help="Number of simulation steps for sparse stress test",
    )
    parser.add_argument(
        "--stress-conn-prob",
        type=float,
        default=1e-4,
        help="Connection probability for sparse stress test",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("=" * 70)
    print("PERFORMANCE BENCHMARKS")
    print("=" * 70)

    # Weight updates
    print(
        f"\n1. Weight Matrix Operations ({args.neurons} neurons, {args.iterations} iterations)..."
    )
    elapsed, n_iter = benchmark_weight_update(N=args.neurons, n_iter=args.iterations)
    print(f"   {n_iter} iterations in {elapsed:.2f}s")
    print(f"   {elapsed / n_iter * 1000:.2f} ms/iteration")

    # Laminar EM
    print(f"\n2. Laminar EM ({args.laminar_cells} cells, {args.laminar_iter} iterations)...")
    elapsed, N, _ = benchmark_laminar_em(N=args.laminar_cells, max_iter=args.laminar_iter)
    print(f"   {N} cells in {elapsed:.2f}s")

    # Sparse stress test
    if args.stress_neurons > 0:
        print(
            f"\n3. Sparse stress test ({args.stress_neurons} neurons, "
            f"p={args.stress_conn_prob})..."
        )
        elapsed, nnz, mem_mb = stress_test_sparse(
            neurons=args.stress_neurons,
            conn_prob=args.stress_conn_prob,
            steps=args.stress_steps,
        )
        print(f"   nnz edges: {nnz:,}")
        print(f"   steps: {args.stress_steps}, elapsed: {elapsed:.2f}s")
        print(f"   approx memory (CSR + spikes): {mem_mb:.2f} MB")

    print("\n✅ Benchmarks complete!")
    print("\nReference (Intel i7, 16GB RAM):")
    print("  Weight updates: ~10 ms/iteration")
    print("  Laminar EM: ~2.0s")
