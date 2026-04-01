"""Performance benchmarks for MyceliumFractalNet.

CPU-first benchmarks that run without optional dependencies (torch, numba).
ML benchmarks are gated behind ``MFN_BENCHMARK_PROFILE=full`` and require ``[ml]``.

Run with: python benchmarks/benchmark_core.py
"""

import csv
import json
import os
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from mycelium_fractal_net import estimate_fractal_dimension, simulate_mycelium_field


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""

    name: str
    metric_value: float
    metric_unit: str
    target_value: float
    passed: bool
    timestamp: str


class BenchmarkSuite:
    """Performance benchmarks to prevent regressions."""

    def __init__(self, results_dir: Path | None = None) -> None:
        self.results: list[BenchmarkResult] = []
        self.results_dir = results_dir or Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)

    # ═══════════════════════════════════════════════════════
    #  CPU-only benchmarks (always available)
    # ═══════════════════════════════════════════════════════

    def benchmark_field_simulation(self) -> BenchmarkResult:
        """Measure field simulation latency (CPU-only)."""
        rng = np.random.default_rng(42)
        for _ in range(3):
            _, _ = simulate_mycelium_field(rng, grid_size=32, steps=20)

        profile = os.getenv("MFN_BENCHMARK_PROFILE", "smoke").lower()
        rng = np.random.default_rng(42)
        start = time.perf_counter()
        num_iterations = 2 if profile != "full" else 10
        grid_size = 32 if profile != "full" else 64
        steps = 40 if profile != "full" else 100
        for _ in range(num_iterations):
            rng = np.random.default_rng(42)
            _, _ = simulate_mycelium_field(
                rng, grid_size=grid_size, steps=steps, turing_enabled=True
            )
        end = time.perf_counter()

        avg_latency_ms = (end - start) / num_iterations * 1000
        target_ms = 250.0 if profile != "full" else 100.0
        result = BenchmarkResult(
            name="field_simulation",
            metric_value=avg_latency_ms,
            metric_unit="ms",
            target_value=target_ms,
            passed=avg_latency_ms < target_ms,
            timestamp=datetime.now().isoformat(),
        )
        print(
            f"Field simulation ({grid_size}x{grid_size}, {steps} steps): {avg_latency_ms:.2f} ms (target: <{target_ms} ms)"
        )
        self.results.append(result)
        return result

    def benchmark_fractal_dimension(self) -> BenchmarkResult:
        """Measure fractal dimension estimation latency."""
        rng = np.random.default_rng(42)
        binary_field = rng.random((64, 64)) > 0.5
        for _ in range(5):
            _ = estimate_fractal_dimension(binary_field)

        start = time.perf_counter()
        num_iterations = 50
        for _ in range(num_iterations):
            _ = estimate_fractal_dimension(binary_field)
        end = time.perf_counter()

        avg_latency_ms = (end - start) / num_iterations * 1000
        target_ms = 50.0
        result = BenchmarkResult(
            name="fractal_dimension",
            metric_value=avg_latency_ms,
            metric_unit="ms",
            target_value=target_ms,
            passed=avg_latency_ms < target_ms,
            timestamp=datetime.now().isoformat(),
        )
        print(f"Fractal dimension estimation: {avg_latency_ms:.2f} ms (target: <{target_ms} ms)")
        self.results.append(result)
        return result

    def benchmark_pipeline_e2e(self) -> BenchmarkResult:
        """Measure full pipeline: simulate → extract → detect → forecast."""
        import mycelium_fractal_net as mfn

        spec = mfn.SimulationSpec(grid_size=32, steps=16, seed=42)
        # Warmup
        for _ in range(3):
            s = mfn.simulate(spec)
            s.extract()
            s.detect()
            s.forecast(4)

        start = time.perf_counter()
        num_iterations = 10
        for _ in range(num_iterations):
            s = mfn.simulate(spec)
            s.extract()
            s.detect()
            s.forecast(4)
        end = time.perf_counter()

        avg_latency_ms = (end - start) / num_iterations * 1000
        target_ms = 200.0
        result = BenchmarkResult(
            name="pipeline_e2e",
            metric_value=avg_latency_ms,
            metric_unit="ms",
            target_value=target_ms,
            passed=avg_latency_ms < target_ms,
            timestamp=datetime.now().isoformat(),
        )
        print(f"Pipeline E2E (32x32): {avg_latency_ms:.2f} ms (target: <{target_ms} ms)")
        self.results.append(result)
        return result

    def benchmark_causal_gate(self) -> BenchmarkResult:
        """Measure causal validation gate latency."""
        import mycelium_fractal_net as mfn
        from mycelium_fractal_net.core.causal_validation import validate_causal_consistency

        seq = mfn.simulate(mfn.SimulationSpec(grid_size=32, steps=16, seed=42))
        desc = seq.extract()
        det = seq.detect()
        # Warmup
        for _ in range(5):
            validate_causal_consistency(seq, desc, det, mode="strict")

        start = time.perf_counter()
        num_iterations = 50
        for _ in range(num_iterations):
            validate_causal_consistency(seq, desc, det, mode="strict")
        end = time.perf_counter()

        avg_latency_ms = (end - start) / num_iterations * 1000
        target_ms = 10.0
        result = BenchmarkResult(
            name="causal_gate",
            metric_value=avg_latency_ms,
            metric_unit="ms",
            target_value=target_ms,
            passed=avg_latency_ms < target_ms,
            timestamp=datetime.now().isoformat(),
        )
        print(f"Causal gate latency: {avg_latency_ms:.2f} ms (target: <{target_ms} ms)")
        self.results.append(result)
        return result

    def benchmark_memory_simulation(self) -> BenchmarkResult:
        """Measure peak memory during simulation."""
        tracemalloc.start()
        rng = np.random.default_rng(42)
        for _ in range(10):
            _, _ = simulate_mycelium_field(rng, grid_size=64, steps=50)
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        target_mb = 100.0
        result = BenchmarkResult(
            name="memory_simulation",
            metric_value=peak_mb,
            metric_unit="MB",
            target_value=target_mb,
            passed=peak_mb < target_mb,
            timestamp=datetime.now().isoformat(),
        )
        print(f"Peak memory (simulation): {peak_mb:.2f} MB (target: <{target_mb} MB)")
        self.results.append(result)
        return result

    # ═══════════════════════════════════════════════════════
    #  ML benchmarks (require torch)
    # ═══════════════════════════════════════════════════════

    def _has_torch(self) -> bool:
        try:
            import torch  # noqa: F401

            return True
        except ImportError:
            return False

    def benchmark_forward_pass(self) -> BenchmarkResult | None:
        """Measure forward pass latency. Requires torch."""
        if not self._has_torch():
            print("Forward pass: SKIPPED (torch not installed)")
            return None
        import torch

        from mycelium_fractal_net.model import MyceliumFractalNet

        torch.manual_seed(42)
        model = MyceliumFractalNet(input_dim=128, hidden_dim=64)
        model.eval()
        x = torch.randn(32, 128)

        for _ in range(10):
            with torch.no_grad():
                _ = model(x)

        profile = os.getenv("MFN_BENCHMARK_PROFILE", "smoke").lower()
        start = time.perf_counter()
        num_iterations = 10 if profile != "full" else 100
        for _ in range(num_iterations):
            with torch.no_grad():
                _ = model(x)
        end = time.perf_counter()

        avg_latency_ms = (end - start) / num_iterations * 1000
        target_ms = 1000.0 if profile != "full" else 10.0
        result = BenchmarkResult(
            name="forward_pass_latency",
            metric_value=avg_latency_ms,
            metric_unit="ms",
            target_value=target_ms,
            passed=avg_latency_ms < target_ms,
            timestamp=datetime.now().isoformat(),
        )
        print(f"Forward pass latency: {avg_latency_ms:.2f} ms (target: <{target_ms} ms)")
        self.results.append(result)
        return result

    def benchmark_training_step(self) -> BenchmarkResult | None:
        """Measure single training step latency. Requires torch."""
        if not self._has_torch():
            print("Training step: SKIPPED (torch not installed)")
            return None
        import torch

        from mycelium_fractal_net.model import MyceliumFractalNet

        torch.manual_seed(42)
        model = MyceliumFractalNet(input_dim=64, hidden_dim=64)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        criterion = torch.nn.MSELoss()
        x = torch.randn(32, 64)
        y = torch.randn(32, 1)

        for _ in range(5):
            _ = model.train_step(x, y, optimizer, criterion)

        start = time.perf_counter()
        num_iterations = 50
        for _ in range(num_iterations):
            _ = model.train_step(x, y, optimizer, criterion)
        end = time.perf_counter()

        avg_latency_ms = (end - start) / num_iterations * 1000
        target_ms = 20.0
        result = BenchmarkResult(
            name="training_step",
            metric_value=avg_latency_ms,
            metric_unit="ms",
            target_value=target_ms,
            passed=avg_latency_ms < target_ms,
            timestamp=datetime.now().isoformat(),
        )
        print(f"Training step: {avg_latency_ms:.2f} ms (target: <{target_ms} ms)")
        self.results.append(result)
        return result

    # ═══════════════════════════════════════════════════════
    #  Orchestration
    # ═══════════════════════════════════════════════════════

    def run_all(self) -> list[BenchmarkResult]:
        """Run all benchmarks and return results."""
        print("\n" + "=" * 60)
        print("MyceliumFractalNet Performance Benchmarks")
        print("=" * 60 + "\n")

        # CPU-only benchmarks (always run)
        self.benchmark_field_simulation()
        self.benchmark_fractal_dimension()
        self.benchmark_pipeline_e2e()
        self.benchmark_causal_gate()
        self.benchmark_memory_simulation()

        # ML benchmarks (optional)
        profile = os.getenv("MFN_BENCHMARK_PROFILE", "smoke").lower()
        if profile == "full":
            self.benchmark_forward_pass()
            self.benchmark_training_step()
        elif self._has_torch():
            self.benchmark_forward_pass()

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
                        f"  - {r.name}: {r.metric_value:.2f} {r.metric_unit} (target: {r.target_value} {r.metric_unit})"
                    )

        return self.results

    def save_results(self, filename: str | None = None) -> Path:
        """Save benchmark results to canonical JSON + CSV files."""
        json_name = filename or "benchmark_core.json"
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
                    "timestamp",
                ],
            )
            writer.writeheader()
            for row in self.results:
                writer.writerow(asdict(row))

        print(f"\nResults saved to: {output_path}")
        print(csv_path)
        return output_path


def run_benchmarks() -> int:
    suite = BenchmarkSuite()
    results = suite.run_all()
    suite.save_results()
    all_passed = all(r.passed for r in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = run_benchmarks()
    sys.exit(exit_code)
