"""
Golden-path performance benchmarks for MLSDM core components.

This file contains microbenchmarks for:
- PhaseEntangledLatticeMemory (PELM) - entangle/retrieve operations
- MultiLevelSynapticMemory - memory layer operations
- CognitiveController - step operations

All benchmarks output P50/P95/P99 latencies and throughput.

Usage:
    pytest tests/perf/test_golden_path_perf.py -v -s
    python tests/perf/test_golden_path_perf.py  # standalone
"""

import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import psutil
import pytest

# Add src to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Benchmark configuration constants
PELM_N_OPS = 1000
MEMORY_N_OPS = 1000
CONTROLLER_N_OPS = 500
DIMENSION = 384
PELM_CAPACITY = 20000
_IS_CI = os.environ.get("CI", "").lower() == "true" or os.environ.get(
    "GITHUB_ACTIONS", ""
).lower() == "true"

PELM_MIN_OPS_SEC = 40 if _IS_CI else 100
PELM_MAX_P95_MS = 120 if _IS_CI else 50
MEMORY_MIN_OPS_SEC = 200 if _IS_CI else 500
CONTROLLER_MIN_OPS_SEC = 50 if _IS_CI else 100


@dataclass
class PerfResult:
    """Performance measurement result."""

    operation: str
    total_ops: int
    total_time_ms: float
    ops_per_sec: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    memory_mb: float = 0.0

    def __str__(self) -> str:
        return (
            f"{self.operation}:\n"
            f"  Throughput: {self.ops_per_sec:.0f} ops/sec\n"
            f"  Latency:    P50={self.p50_ms:.3f}ms  P95={self.p95_ms:.3f}ms  P99={self.p99_ms:.3f}ms\n"
            f"  Total:      {self.total_ops} ops in {self.total_time_ms:.1f}ms"
        )


def percentile(data: list[float], p: float) -> float:
    """Calculate percentile using nearest-rank method.

    The nearest-rank method: the percentile is the smallest value in the list
    such that at least p% of data values are <= that value.
    """
    if not data:
        return 0.0
    sorted_data = sorted(data)
    n = len(sorted_data)
    # Nearest-rank: index = ceil(p * n) - 1, clamped to valid range
    idx = max(0, min(int(p * n), n - 1))
    return sorted_data[idx]


def get_env_info() -> dict:
    """Get environment information for reproducibility."""
    return {
        "cpu": platform.processor() or platform.machine(),
        "cores": psutil.cpu_count(),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "python": platform.python_version(),
        "platform": platform.system(),
    }


def print_env_info() -> None:
    """Print environment info header."""
    info = get_env_info()
    print("\n" + "=" * 70)
    print("MLSDM GOLDEN-PATH PERFORMANCE BENCHMARKS")
    print("=" * 70)
    print(f"CPU:     {info['cpu']} ({info['cores']} cores)")
    print(f"RAM:     {info['ram_gb']} GB")
    print(f"Python:  {info['python']}")
    print(f"OS:      {info['platform']}")
    print("=" * 70 + "\n")


class TestPELMPerformance:
    """Performance tests for PhaseEntangledLatticeMemory."""

    @pytest.fixture
    def pelm(self):
        """Create PELM instance for testing."""
        from mlsdm.memory.phase_entangled_lattice_memory import (
            PhaseEntangledLatticeMemory,
        )

        return PhaseEntangledLatticeMemory(dimension=DIMENSION, capacity=PELM_CAPACITY)

    @pytest.mark.benchmark
    def test_pelm_entangle_throughput(self, pelm) -> None:
        """Benchmark PELM entangle operations."""
        # Prepare data
        vectors = [
            np.random.randn(DIMENSION).astype(np.float32).tolist() for _ in range(PELM_N_OPS)
        ]
        phases = [np.random.random() for _ in range(PELM_N_OPS)]
        latencies: list[float] = []

        # Warmup
        for i in range(min(50, PELM_N_OPS)):
            pelm.entangle(vectors[i], phases[i])

        # Benchmark
        start_total = time.perf_counter()
        for v, p in zip(vectors, phases, strict=True):
            start = time.perf_counter()
            pelm.entangle(v, p)
            latencies.append((time.perf_counter() - start) * 1000)
        total_time = (time.perf_counter() - start_total) * 1000

        result = PerfResult(
            operation="PELM.entangle",
            total_ops=PELM_N_OPS,
            total_time_ms=total_time,
            ops_per_sec=PELM_N_OPS / (total_time / 1000),
            p50_ms=percentile(latencies, 0.50),
            p95_ms=percentile(latencies, 0.95),
            p99_ms=percentile(latencies, 0.99),
            memory_mb=pelm.memory_usage_bytes() / 1024 / 1024,
        )

        print(f"\n{result}")
        print(f"  Memory:     {result.memory_mb:.2f} MB")

        # Assertions - ensure minimum performance
        assert (
            result.ops_per_sec >= PELM_MIN_OPS_SEC
        ), f"entangle too slow: {result.ops_per_sec} ops/sec"
        assert (
            result.p95_ms < PELM_MAX_P95_MS
        ), f"P95 latency too high: {result.p95_ms}ms"

    @pytest.mark.benchmark
    def test_pelm_retrieve_throughput(self, pelm) -> None:
        """Benchmark PELM retrieve operations."""
        # Prepare data and populate memory
        vectors = [
            np.random.randn(DIMENSION).astype(np.float32).tolist() for _ in range(PELM_N_OPS)
        ]
        phases = [np.random.random() for _ in range(PELM_N_OPS)]

        for v, p in zip(vectors, phases, strict=True):
            pelm.entangle(v, p)

        latencies: list[float] = []

        # Warmup
        for i in range(min(50, PELM_N_OPS)):
            pelm.retrieve(vectors[i], phases[i], top_k=5)

        # Benchmark
        start_total = time.perf_counter()
        for i in range(PELM_N_OPS):
            start = time.perf_counter()
            pelm.retrieve(vectors[i % len(vectors)], phases[i % len(phases)], top_k=5)
            latencies.append((time.perf_counter() - start) * 1000)
        total_time = (time.perf_counter() - start_total) * 1000

        result = PerfResult(
            operation="PELM.retrieve",
            total_ops=PELM_N_OPS,
            total_time_ms=total_time,
            ops_per_sec=PELM_N_OPS / (total_time / 1000),
            p50_ms=percentile(latencies, 0.50),
            p95_ms=percentile(latencies, 0.95),
            p99_ms=percentile(latencies, 0.99),
        )

        print(f"\n{result}")

        # Assertions
        assert (
            result.ops_per_sec >= PELM_MIN_OPS_SEC
        ), f"retrieve too slow: {result.ops_per_sec} ops/sec"
        assert (
            result.p95_ms < PELM_MAX_P95_MS
        ), f"P95 latency too high: {result.p95_ms}ms"


class TestMultiLevelMemoryPerformance:
    """Performance tests for MultiLevelSynapticMemory."""

    @pytest.fixture
    def memory(self):
        """Create MultiLevelSynapticMemory instance."""
        from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory

        return MultiLevelSynapticMemory(dimension=DIMENSION)

    @pytest.mark.benchmark
    def test_multi_level_update(self, memory) -> None:
        """Benchmark multi-level memory update processing."""
        vectors = [np.random.randn(DIMENSION).astype(np.float32) for _ in range(MEMORY_N_OPS)]
        latencies: list[float] = []

        # Warmup
        for i in range(min(50, MEMORY_N_OPS)):
            memory.update(vectors[i])

        # Benchmark
        start_total = time.perf_counter()
        for v in vectors:
            start = time.perf_counter()
            memory.update(v)
            latencies.append((time.perf_counter() - start) * 1000)
        total_time = (time.perf_counter() - start_total) * 1000

        result = PerfResult(
            operation="MultiLevelMemory.update",
            total_ops=MEMORY_N_OPS,
            total_time_ms=total_time,
            ops_per_sec=MEMORY_N_OPS / (total_time / 1000),
            p50_ms=percentile(latencies, 0.50),
            p95_ms=percentile(latencies, 0.95),
            p99_ms=percentile(latencies, 0.99),
        )

        print(f"\n{result}")

        # Assertions
        assert (
            result.ops_per_sec >= MEMORY_MIN_OPS_SEC
        ), f"update too slow: {result.ops_per_sec} ops/sec"


class TestCognitiveControllerPerformance:
    """Performance tests for CognitiveController."""

    @pytest.fixture
    def controller(self):
        """Create CognitiveController instance."""
        from mlsdm.core.cognitive_controller import CognitiveController

        return CognitiveController(dim=DIMENSION)

    @pytest.mark.benchmark
    def test_controller_process_event(self, controller) -> None:
        """Benchmark cognitive controller process_event operations."""
        vectors = [np.random.randn(DIMENSION).astype(np.float32) for _ in range(CONTROLLER_N_OPS)]
        moral_values = [np.random.uniform(0.3, 0.9) for _ in range(CONTROLLER_N_OPS)]
        latencies: list[float] = []

        # Warmup
        for i in range(min(20, CONTROLLER_N_OPS)):
            controller.process_event(vectors[i], moral_values[i])

        # Benchmark
        start_total = time.perf_counter()
        for v, m in zip(vectors, moral_values, strict=True):
            start = time.perf_counter()
            controller.process_event(v, m)
            latencies.append((time.perf_counter() - start) * 1000)
        total_time = (time.perf_counter() - start_total) * 1000

        result = PerfResult(
            operation="CognitiveController.process_event",
            total_ops=CONTROLLER_N_OPS,
            total_time_ms=total_time,
            ops_per_sec=CONTROLLER_N_OPS / (total_time / 1000),
            p50_ms=percentile(latencies, 0.50),
            p95_ms=percentile(latencies, 0.95),
            p99_ms=percentile(latencies, 0.99),
        )

        print(f"\n{result}")

        # Assertions
        assert (
            result.ops_per_sec >= CONTROLLER_MIN_OPS_SEC
        ), f"process_event too slow: {result.ops_per_sec} ops/sec"


def run_all_benchmarks() -> dict:
    """Run all benchmarks and return results as dict."""
    from mlsdm.core.cognitive_controller import CognitiveController
    from mlsdm.memory.multi_level_memory import MultiLevelSynapticMemory
    from mlsdm.memory.phase_entangled_lattice_memory import PhaseEntangledLatticeMemory

    results = {}

    # PELM entangle
    pelm = PhaseEntangledLatticeMemory(dimension=DIMENSION, capacity=PELM_CAPACITY)
    vectors = [np.random.randn(DIMENSION).astype(np.float32).tolist() for _ in range(PELM_N_OPS)]
    phases = [np.random.random() for _ in range(PELM_N_OPS)]
    pelm_entangle_latencies: list[float] = []
    start_total = time.perf_counter()
    for v, p in zip(vectors, phases, strict=True):
        start = time.perf_counter()
        pelm.entangle(v, p)
        pelm_entangle_latencies.append((time.perf_counter() - start) * 1000)
    total_time = (time.perf_counter() - start_total) * 1000
    results["pelm_entangle"] = {
        "ops_per_sec": PELM_N_OPS / (total_time / 1000),
        "p50_ms": percentile(pelm_entangle_latencies, 0.50),
        "p95_ms": percentile(pelm_entangle_latencies, 0.95),
        "p99_ms": percentile(pelm_entangle_latencies, 0.99),
        "memory_mb": pelm.memory_usage_bytes() / 1024 / 1024,
    }

    # PELM retrieve
    pelm_retrieve_latencies: list[float] = []
    start_total = time.perf_counter()
    for i in range(PELM_N_OPS):
        start = time.perf_counter()
        pelm.retrieve(vectors[i], phases[i], top_k=5)
        pelm_retrieve_latencies.append((time.perf_counter() - start) * 1000)
    total_time = (time.perf_counter() - start_total) * 1000
    results["pelm_retrieve"] = {
        "ops_per_sec": PELM_N_OPS / (total_time / 1000),
        "p50_ms": percentile(pelm_retrieve_latencies, 0.50),
        "p95_ms": percentile(pelm_retrieve_latencies, 0.95),
        "p99_ms": percentile(pelm_retrieve_latencies, 0.99),
    }

    # MultiLevelMemory
    memory = MultiLevelSynapticMemory(dimension=DIMENSION)
    vectors_np = [np.random.randn(DIMENSION).astype(np.float32) for _ in range(MEMORY_N_OPS)]
    memory_latencies: list[float] = []
    start_total = time.perf_counter()
    for v in vectors_np:
        start = time.perf_counter()
        memory.update(v)
        memory_latencies.append((time.perf_counter() - start) * 1000)
    total_time = (time.perf_counter() - start_total) * 1000
    results["multi_level_update"] = {
        "ops_per_sec": MEMORY_N_OPS / (total_time / 1000),
        "p50_ms": percentile(memory_latencies, 0.50),
        "p95_ms": percentile(memory_latencies, 0.95),
        "p99_ms": percentile(memory_latencies, 0.99),
    }

    # CognitiveController
    controller = CognitiveController(dim=DIMENSION)
    moral_values = [np.random.uniform(0.3, 0.9) for _ in range(CONTROLLER_N_OPS)]
    controller_latencies: list[float] = []
    start_total = time.perf_counter()
    for i in range(CONTROLLER_N_OPS):
        start = time.perf_counter()
        controller.process_event(vectors_np[i], moral_values[i])
        controller_latencies.append((time.perf_counter() - start) * 1000)
    total_time = (time.perf_counter() - start_total) * 1000
    results["controller_process_event"] = {
        "ops_per_sec": CONTROLLER_N_OPS / (total_time / 1000),
        "p50_ms": percentile(controller_latencies, 0.50),
        "p95_ms": percentile(controller_latencies, 0.95),
        "p99_ms": percentile(controller_latencies, 0.99),
    }

    return results


if __name__ == "__main__":
    print_env_info()
    results = run_all_benchmarks()

    print("-" * 70)
    print("RESULTS SUMMARY")
    print("-" * 70)

    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Throughput: {data['ops_per_sec']:.0f} ops/sec")
        print(
            f"  P50: {data['p50_ms']:.3f}ms  P95: {data['p95_ms']:.3f}ms  P99: {data['p99_ms']:.3f}ms"
        )
        if "memory_mb" in data:
            print(f"  Memory: {data['memory_mb']:.2f} MB")

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)
