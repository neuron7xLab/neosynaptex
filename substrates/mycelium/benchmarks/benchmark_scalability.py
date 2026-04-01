"""Scalability and stress benchmarks for MyceliumFractalNet.

This module provides benchmarks for system behavior under stress:
- Large grid simulations (128x128, 256x256)
- Long-running simulations (1000+ steps)
- Memory efficiency under load
- Concurrent processing throughput

Run with: python benchmarks/benchmark_scalability.py
"""

import csv
import gc
import json
import os
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from mycelium_fractal_net import (
    SimulationConfig,
    SimulationSpec,
    estimate_fractal_dimension,
    run_mycelium_simulation,
)
from mycelium_fractal_net.core import compute_lyapunov_exponent
from mycelium_fractal_net.core.simulate import simulate_history
from mycelium_fractal_net.numerics.grid_ops import BoundaryCondition, compute_laplacian


@dataclass
class ScalabilityResult:
    """Container for scalability benchmark results."""

    name: str
    metric_value: float
    metric_unit: str
    target_value: float
    passed: bool
    memory_mb: float
    timestamp: str


def run_simulation_task(params: dict[str, Any]) -> dict[str, Any]:
    """Worker function for parallel simulation."""
    config = SimulationConfig(
        seed=params["seed"],
        grid_size=params["grid_size"],
        steps=params["steps"],
    )
    start = time.perf_counter()
    result = run_mycelium_simulation(config)
    elapsed = time.perf_counter() - start

    return {
        "seed": params["seed"],
        "elapsed_s": elapsed,
        "growth_events": result.growth_events,
    }


class ScalabilityBenchmarkSuite:
    """Scalability benchmarks for stress testing."""

    def __init__(self, results_dir: Path | None = None) -> None:
        """Initialize benchmark suite."""
        self.results: list[ScalabilityResult] = []
        self.results_dir = results_dir or Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)

    def benchmark_large_grid_128(self) -> ScalabilityResult:
        """Benchmark 128x128 grid simulation.

        Target: <15s for 200 steps
        """
        gc.collect()
        tracemalloc.start()

        profile = os.getenv("MFN_BENCHMARK_PROFILE", "smoke").lower()
        grid_size = 64 if profile != "full" else 128
        steps = 64 if profile != "full" else 200
        config = SimulationConfig(
            grid_size=grid_size,
            steps=steps,
            seed=42,
            turing_enabled=True,
        )

        start = time.perf_counter()
        result = run_mycelium_simulation(config)
        elapsed = time.perf_counter() - start

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        target_s = 15.0

        bench_result = ScalabilityResult(
            name="large_grid_128x128",
            metric_value=elapsed,
            metric_unit="s",
            target_value=target_s,
            passed=elapsed < target_s and result.field.shape == (grid_size, grid_size),
            memory_mb=peak_mb,
            timestamp=datetime.now().isoformat(),
        )

        print(
            f"Large grid ({grid_size}x{grid_size}, {steps} steps): {elapsed:.2f}s, {peak_mb:.2f}MB "
            f"(target: <{target_s}s)"
        )

        self.results.append(bench_result)
        return bench_result

    def benchmark_large_grid_256(self) -> ScalabilityResult:
        """Benchmark 256x256 grid simulation.

        Target: <60s for 100 steps
        """
        gc.collect()
        tracemalloc.start()

        config = SimulationConfig(
            grid_size=256,
            steps=100,
            seed=42,
            turing_enabled=True,
        )

        start = time.perf_counter()
        result = run_mycelium_simulation(config)
        elapsed = time.perf_counter() - start

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        target_s = 60.0

        bench_result = ScalabilityResult(
            name="large_grid_256x256",
            metric_value=elapsed,
            metric_unit="s",
            target_value=target_s,
            passed=elapsed < target_s and result.field.shape == (256, 256),
            memory_mb=peak_mb,
            timestamp=datetime.now().isoformat(),
        )

        print(
            f"Large grid (256x256, 100 steps): {elapsed:.2f}s, {peak_mb:.2f}MB "
            f"(target: <{target_s}s)"
        )

        self.results.append(bench_result)
        return bench_result

    def benchmark_long_simulation(self) -> ScalabilityResult:
        """Benchmark 1000-step simulation.

        Target: <30s for 64x64 grid, 1000 steps
        """
        gc.collect()
        tracemalloc.start()

        config = SimulationConfig(
            grid_size=64,
            steps=1000,
            seed=42,
            turing_enabled=True,
        )

        start = time.perf_counter()
        _ = run_mycelium_simulation(config)
        elapsed = time.perf_counter() - start

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        target_s = 30.0

        bench_result = ScalabilityResult(
            name="long_simulation_1000_steps",
            metric_value=elapsed,
            metric_unit="s",
            target_value=target_s,
            passed=elapsed < target_s,
            memory_mb=peak_mb,
            timestamp=datetime.now().isoformat(),
        )

        print(
            f"Long simulation (64x64, 1000 steps): {elapsed:.2f}s, {peak_mb:.2f}MB "
            f"(target: <{target_s}s)"
        )

        self.results.append(bench_result)
        return bench_result

    def benchmark_concurrent_simulations(self) -> ScalabilityResult:
        """Benchmark concurrent simulation throughput.

        Target: >3 simulations/second with 4 workers
        """
        profile = os.getenv("MFN_BENCHMARK_PROFILE", "smoke").lower()
        num_workers = 2 if profile != "full" else 4
        num_tasks = 4 if profile != "full" else 16
        steps = 20 if profile != "full" else 50
        params_list = [{"seed": i * 100, "grid_size": 32, "steps": steps} for i in range(num_tasks)]

        gc.collect()
        tracemalloc.start()

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(run_simulation_task, params_list))
        total_time = time.perf_counter() - start

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        throughput = num_tasks / total_time
        peak_mb = peak / (1024 * 1024)
        target_throughput = 3.0

        bench_result = ScalabilityResult(
            name="concurrent_throughput",
            metric_value=throughput,
            metric_unit="sim/s",
            target_value=target_throughput,
            passed=throughput >= target_throughput and len(results) == num_tasks,
            memory_mb=peak_mb,
            timestamp=datetime.now().isoformat(),
        )

        print(
            f"Concurrent throughput ({num_workers} workers): {throughput:.2f} sim/s, "
            f"{peak_mb:.2f}MB (target: >{target_throughput} sim/s)"
        )

        self.results.append(bench_result)
        return bench_result

    def benchmark_laplacian_numpy_vs_jit(self) -> ScalabilityResult:
        """Benchmark reference vs optional accelerated Laplacian with parity check."""
        rng = np.random.default_rng(42)
        field = rng.normal(size=(128, 128)).astype(np.float64)

        start = time.perf_counter()
        reference = compute_laplacian(field, boundary=BoundaryCondition.PERIODIC, use_accel=False)
        reference_elapsed = time.perf_counter() - start

        start = time.perf_counter()
        accelerated = compute_laplacian(field, boundary=BoundaryCondition.PERIODIC, use_accel=True)
        accelerated_elapsed = time.perf_counter() - start

        passed = bool(np.allclose(reference, accelerated, rtol=0.0, atol=1e-12))
        result = ScalabilityResult(
            name="laplacian_numpy_vs_jit",
            metric_value=accelerated_elapsed,
            metric_unit="s",
            target_value=reference_elapsed * 2.0 if reference_elapsed > 0 else 1.0,
            passed=passed,
            memory_mb=0.0,
            timestamp=datetime.now().isoformat(),
        )
        print(
            f"Laplacian parity: ref={reference_elapsed:.4f}s accel={accelerated_elapsed:.4f}s parity={'ok' if passed else 'fail'}"
        )
        self.results.append(result)
        return result

    def benchmark_memmap_history_scale(self) -> ScalabilityResult:
        """Benchmark disk-backed history path for larger scale contours."""
        profile = os.getenv("MFN_BENCHMARK_PROFILE", "smoke").lower()
        experimental = os.getenv("MFN_EXPERIMENTAL_SCALE", "0").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if experimental:
            grid_size = 1024
            steps = 16
            name = "memmap_history_1024x1024_experimental"
        elif profile == "full":
            grid_size = 512
            steps = 128
            name = "memmap_history_512x512"
        else:
            grid_size = 128
            steps = 24
            name = "memmap_history_128x128_smoke"

        gc.collect()
        tracemalloc.start()
        start = time.perf_counter()
        seq = simulate_history(
            SimulationSpec(grid_size=grid_size, steps=steps, seed=42),
            history_backend="memmap",
        )
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak / (1024 * 1024)
        memmap_path = Path(str(seq.metadata.get("history_memmap_path", "")))
        passed = (
            seq.history is not None
            and memmap_path.exists()
            and seq.field.shape == (grid_size, grid_size)
        )
        result = ScalabilityResult(
            name=name,
            metric_value=elapsed,
            metric_unit="s",
            target_value=600.0 if experimental else 180.0,
            passed=passed,
            memory_mb=peak_mb,
            timestamp=datetime.now().isoformat(),
        )
        print(
            f"Memmap history ({grid_size}x{grid_size}, {steps} steps): {elapsed:.2f}s, {peak_mb:.2f}MB"
        )
        self.results.append(result)
        return result

    def benchmark_memory_efficiency(self) -> ScalabilityResult:
        """Benchmark memory efficiency with repeated simulations.

        Target: <100MB peak across 20 simulation runs
        """
        gc.collect()
        tracemalloc.start()

        config = SimulationConfig(grid_size=32, steps=50, seed=42)

        for _ in range(20):
            result = run_mycelium_simulation(config)
            del result
            gc.collect()

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        target_mb = 100.0

        bench_result = ScalabilityResult(
            name="memory_efficiency_20_runs",
            metric_value=peak_mb,
            metric_unit="MB",
            target_value=target_mb,
            passed=peak_mb < target_mb,
            memory_mb=peak_mb,
            timestamp=datetime.now().isoformat(),
        )

        print(f"Memory efficiency (20 runs): {peak_mb:.2f}MB (target: <{target_mb}MB)")

        self.results.append(bench_result)
        return bench_result

    def benchmark_fractal_dimension_scaling(self) -> ScalabilityResult:
        """Benchmark fractal dimension on large fields.

        Target: <0.5s for 256x256 field
        """
        rng = np.random.default_rng(42)
        large_field = rng.random((256, 256)) > 0.5

        gc.collect()
        tracemalloc.start()

        start = time.perf_counter()
        dim = estimate_fractal_dimension(large_field)
        elapsed = time.perf_counter() - start

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        target_s = 0.5

        bench_result = ScalabilityResult(
            name="fractal_dimension_256x256",
            metric_value=elapsed,
            metric_unit="s",
            target_value=target_s,
            passed=elapsed < target_s and 1.0 <= dim <= 2.0,
            memory_mb=peak_mb,
            timestamp=datetime.now().isoformat(),
        )

        print(f"Fractal dimension (256x256): {elapsed:.3f}s, dim={dim:.3f} (target: <{target_s}s)")

        self.results.append(bench_result)
        return bench_result

    def benchmark_lyapunov_large_history(self) -> ScalabilityResult:
        """Benchmark Lyapunov exponent on large history.

        Target: <2s for 500x64x64 history
        """
        rng = np.random.default_rng(42)
        large_history = rng.normal(loc=-0.07, scale=0.01, size=(500, 64, 64))

        gc.collect()
        tracemalloc.start()

        start = time.perf_counter()
        lyap = compute_lyapunov_exponent(large_history)
        elapsed = time.perf_counter() - start

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        target_s = 2.0

        bench_result = ScalabilityResult(
            name="lyapunov_500x64x64",
            metric_value=elapsed,
            metric_unit="s",
            target_value=target_s,
            passed=elapsed < target_s and not np.isnan(lyap),
            memory_mb=peak_mb,
            timestamp=datetime.now().isoformat(),
        )

        print(f"Lyapunov (500x64x64): {elapsed:.3f}s, λ={lyap:.3f} (target: <{target_s}s)")

        self.results.append(bench_result)
        return bench_result

    def run_all(self) -> list[ScalabilityResult]:
        """Run all scalability benchmarks."""
        print("\n" + "=" * 60)
        print("MyceliumFractalNet Scalability Benchmarks")
        print("=" * 60 + "\n")

        profile = os.getenv("MFN_BENCHMARK_PROFILE", "smoke").lower()
        if profile == "full":
            self.benchmark_large_grid_128()
            self.benchmark_large_grid_256()
            self.benchmark_long_simulation()
            self.benchmark_concurrent_simulations()
            self.benchmark_memory_efficiency()
            self.benchmark_fractal_dimension_scaling()
            self.benchmark_lyapunov_large_history()
            self.benchmark_laplacian_numpy_vs_jit()
            self.benchmark_memmap_history_scale()
        else:
            self.benchmark_large_grid_128()
            self.benchmark_concurrent_simulations()
            self.benchmark_fractal_dimension_scaling()
            self.benchmark_laplacian_numpy_vs_jit()
            self.benchmark_memmap_history_scale()

        # Summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        print(f"\nPassed: {passed}/{total}")

        if passed < total:
            print("\nFailed benchmarks:")
            for r in self.results:
                if not r.passed:
                    print(
                        f"  - {r.name}: {r.metric_value:.2f} {r.metric_unit} "
                        f"(target: {r.target_value} {r.metric_unit})"
                    )

        return self.results

    def save_results(self, filename: str | None = None) -> Path:
        """Save benchmark results to canonical JSON + CSV files."""
        json_name = filename or "benchmark_scalability.json"
        csv_name = json_name.replace(".json", ".csv")
        output_path = self.results_dir / json_name
        csv_path = self.results_dir / csv_name

        results_dict = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": [asdict(r) for r in self.results],
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
        }

        with open(output_path, "w") as f:
            json.dump(results_dict, f, indent=2)
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "name",
                    "metric_value",
                    "metric_unit",
                    "target_value",
                    "passed",
                    "memory_mb",
                    "timestamp",
                ],
            )
            writer.writeheader()
            for row in self.results:
                writer.writerow(asdict(row))

        print(f"\nResults saved to: {output_path}")
        print(csv_path)
        return output_path


def run_scalability_benchmarks() -> int:
    """Run all scalability benchmarks and return exit code."""
    suite = ScalabilityBenchmarkSuite()
    results = suite.run_all()
    suite.save_results()

    # Return non-zero if any benchmark failed
    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = run_scalability_benchmarks()
    sys.exit(exit_code)
