"""
Locust load testing for MLSDM system.

Tests:
- 100 concurrent users over 10 minutes
- P50/P95/P99 latency measurements
- Saturation point determination
- Memory stability monitoring
- Report generation
"""

import json
import os
import time
from datetime import datetime
from typing import Any

import numpy as np
import psutil
import pytest

pytest.importorskip("locust", reason="locust (and zope.event dependency) required for load tests")
from locust import HttpUser, TaskSet, between, events, task
from locust.runners import MasterRunner

# ============================================================================
# Global State for Metrics Collection
# ============================================================================


class MetricsCollector:
    """Collects metrics during load test."""

    def __init__(self) -> None:
        self.latencies: list[float] = []
        self.response_times: list[float] = []
        self.memory_samples: list[float] = []
        self.timestamps: list[float] = []
        self.errors: list[dict[str, Any]] = []
        self.rps_samples: list[tuple[float, int]] = []

        self.start_time = time.time()
        self.request_count = 0
        self.last_rps_time = time.time()
        self.last_rps_count = 0

    def record_request(self, response_time: float, success: bool) -> None:
        """Record a request completion."""
        self.request_count += 1
        self.timestamps.append(time.time() - self.start_time)

        if success:
            self.latencies.append(response_time)
            self.response_times.append(response_time)

        # Sample RPS every second
        current_time = time.time()
        if current_time - self.last_rps_time >= 1.0:
            rps = (self.request_count - self.last_rps_count) / (current_time - self.last_rps_time)
            self.rps_samples.append((current_time - self.start_time, int(rps)))
            self.last_rps_time = current_time
            self.last_rps_count = self.request_count

    def record_memory(self) -> None:
        """Record current memory usage."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        self.memory_samples.append(memory_mb)

    def record_error(self, error: str, context: dict[str, Any]) -> None:
        """Record an error."""
        self.errors.append(
            {"timestamp": time.time() - self.start_time, "error": error, "context": context}
        )

    def calculate_percentiles(self) -> dict[str, float]:
        """Calculate latency percentiles."""
        if not self.latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

        latencies_arr = np.array(self.latencies)
        return {
            "p50": float(np.percentile(latencies_arr, 50)),
            "p95": float(np.percentile(latencies_arr, 95)),
            "p99": float(np.percentile(latencies_arr, 99)),
            "mean": float(np.mean(latencies_arr)),
            "min": float(np.min(latencies_arr)),
            "max": float(np.max(latencies_arr)),
        }

    def determine_saturation_point(self) -> dict[str, Any]:
        """Determine saturation point based on RPS and latency correlation."""
        if len(self.rps_samples) < 10 or len(self.latencies) < 10:
            return {
                "saturation_rps": 0,
                "saturation_detected": False,
                "reason": "Insufficient data",
            }

        # Group latencies by time windows and correlate with RPS
        window_size = 5  # seconds
        max_time = max(ts for ts, _ in self.rps_samples)

        rps_by_window = []
        latency_by_window = []

        for i in range(0, int(max_time), window_size):
            window_start = i
            window_end = i + window_size

            # Get RPS in this window
            window_rps = [rps for ts, rps in self.rps_samples if window_start <= ts < window_end]
            if window_rps:
                avg_rps = np.mean(window_rps)
                rps_by_window.append(avg_rps)

                # Get latencies in this window
                # Zip up to minimum length to ensure alignment
                min_len = min(len(self.latencies), len(self.timestamps))
                window_latencies = [
                    lat
                    for lat, ts in zip(
                        self.latencies[:min_len], self.timestamps[:min_len], strict=False
                    )
                    if window_start <= ts < window_end
                ]
                if window_latencies:
                    avg_latency = np.mean(window_latencies)
                    latency_by_window.append(avg_latency)
                else:
                    latency_by_window.append(0)

        if len(rps_by_window) < 3:
            return {
                "saturation_rps": 0,
                "saturation_detected": False,
                "reason": "Insufficient windows",
            }

        # Look for inflection point where latency starts increasing significantly
        # with RPS increase
        saturation_detected = False
        saturation_rps = 0

        for i in range(1, len(rps_by_window)):
            if i >= len(latency_by_window):
                break

            rps_increase = rps_by_window[i] - rps_by_window[i - 1]
            latency_increase = latency_by_window[i] - latency_by_window[i - 1]

            # Saturation: RPS increases but latency increases disproportionately
            if rps_increase > 0 and latency_increase / (rps_increase + 1e-6) > 10:
                saturation_detected = True
                saturation_rps = int(rps_by_window[i - 1])
                break

        if not saturation_detected:
            # No clear saturation detected, return max observed RPS
            saturation_rps = int(max(rps_by_window)) if rps_by_window else 0

        return {
            "saturation_rps": saturation_rps,
            "saturation_detected": saturation_detected,
            "reason": "Latency spike detected" if saturation_detected else "No saturation in test",
        }

    def check_memory_stability(self) -> dict[str, Any]:
        """Check for memory leaks."""
        if len(self.memory_samples) < 10:
            return {"stable": True, "leak_detected": False, "reason": "Insufficient samples"}

        # Check if memory is continuously increasing
        samples = np.array(self.memory_samples)

        # Split into first half and second half
        mid = len(samples) // 2
        first_half_mean = np.mean(samples[:mid])
        second_half_mean = np.mean(samples[mid:])

        # Calculate growth rate
        growth_rate = (second_half_mean - first_half_mean) / first_half_mean

        # Check for linear trend
        x = np.arange(len(samples))
        coeffs = np.polyfit(x, samples, 1)
        slope = coeffs[0]

        leak_detected = False
        reason = "Memory stable"

        # Leak indicators:
        # 1. More than 20% growth from first to second half
        # 2. Positive slope indicating continuous growth
        if growth_rate > 0.20 and slope > 0.5:
            leak_detected = True
            reason = f"Memory increased {growth_rate*100:.1f}% with positive trend"

        return {
            "stable": not leak_detected,
            "leak_detected": leak_detected,
            "growth_rate": float(growth_rate),
            "initial_memory_mb": float(samples[0]),
            "final_memory_mb": float(samples[-1]),
            "mean_memory_mb": float(np.mean(samples)),
            "reason": reason,
        }

    def generate_report(self, output_path: str = "load_test_report.json") -> None:
        """Generate comprehensive load test report."""
        percentiles = self.calculate_percentiles()
        saturation = self.determine_saturation_point()
        memory_check = self.check_memory_stability()

        report = {
            "test_info": {
                "duration_seconds": time.time() - self.start_time,
                "total_requests": self.request_count,
                "successful_requests": len(self.latencies),
                "failed_requests": len(self.errors),
                "timestamp": datetime.now().isoformat(),
            },
            "latency_metrics": percentiles,
            "saturation_analysis": saturation,
            "memory_stability": memory_check,
            "errors": self.errors[:100],  # Limit error list
            "rps_samples": self.rps_samples[-100:],  # Last 100 samples
        }

        # Write report
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print("\n" + "=" * 80)
        print("LOAD TEST REPORT")
        print("=" * 80)
        print(f"\nTest Duration: {report['test_info']['duration_seconds']:.1f}s")
        print(f"Total Requests: {report['test_info']['total_requests']}")
        print(f"Success Rate: {len(self.latencies)/self.request_count*100:.1f}%")
        print("\nLatency Metrics:")
        print(f"  P50: {percentiles['p50']:.2f}ms")
        print(f"  P95: {percentiles['p95']:.2f}ms")
        print(f"  P99: {percentiles['p99']:.2f}ms")
        print(f"  Mean: {percentiles['mean']:.2f}ms")
        print("\nSaturation Analysis:")
        print(f"  Saturation RPS: {saturation['saturation_rps']}")
        print(f"  Saturation Detected: {saturation['saturation_detected']}")
        print(f"  Reason: {saturation['reason']}")
        print("\nMemory Stability:")
        print(f"  Stable: {memory_check['stable']}")
        print(f"  Leak Detected: {memory_check['leak_detected']}")
        print(f"  Initial Memory: {memory_check.get('initial_memory_mb', 0):.1f} MB")
        print(f"  Final Memory: {memory_check.get('final_memory_mb', 0):.1f} MB")
        print(f"  Reason: {memory_check['reason']}")
        print("\n" + "=" * 80)
        print(f"Report saved to: {output_path}")
        print("=" * 80 + "\n")


# Global metrics collector
metrics = MetricsCollector()


# ============================================================================
# Locust Task Sets
# ============================================================================


class MLSDMTaskSet(TaskSet):
    """Task set for MLSDM load testing."""

    @task(3)
    def generate_text(self) -> None:
        """Generate text with high moral value."""
        prompt = f"Tell me about artificial intelligence {np.random.randint(1000)}"

        start_time = time.time()
        try:
            response = self.client.post(
                "/generate",
                json={"prompt": prompt, "moral_value": 0.9, "max_tokens": 100},
                timeout=10,
            )

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            if response.status_code == 200:
                metrics.record_request(response_time, True)
            else:
                metrics.record_request(response_time, False)
                metrics.record_error(f"HTTP {response.status_code}", {"prompt": prompt})

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            metrics.record_request(response_time, False)
            metrics.record_error(str(e), {"prompt": prompt})

    @task(1)
    def get_status(self) -> None:
        """Check system status."""
        start_time = time.time()
        try:
            response = self.client.get("/health", timeout=5)
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                metrics.record_request(response_time, True)
            else:
                metrics.record_request(response_time, False)

        except Exception:
            response_time = (time.time() - start_time) * 1000
            metrics.record_request(response_time, False)

    @task(1)
    def moral_filter_test(self) -> None:
        """Test with lower moral values."""
        prompt = f"Potentially toxic content {np.random.randint(1000)}"
        moral_value = np.random.uniform(0.3, 0.7)

        start_time = time.time()
        try:
            response = self.client.post(
                "/generate",
                json={"prompt": prompt, "moral_value": moral_value, "max_tokens": 50},
                timeout=10,
            )

            response_time = (time.time() - start_time) * 1000

            if response.status_code in [200, 400]:  # 400 expected for rejected
                metrics.record_request(response_time, True)
            else:
                metrics.record_request(response_time, False)

        except Exception:
            response_time = (time.time() - start_time) * 1000
            metrics.record_request(response_time, False)


class MLSDMUser(HttpUser):
    """Simulated user for MLSDM system."""

    tasks = [MLSDMTaskSet]
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        # Set base URL if not provided
        if not self.host:
            self.host = os.environ.get("MLSDM_HOST", "http://localhost:8000")


# ============================================================================
# Event Handlers
# ============================================================================


@events.init.add_listener
def on_locust_init(environment: Any, **kwargs: Any) -> None:
    """Initialize load test."""
    print("\n" + "=" * 80)
    print("MLSDM LOAD TEST - INITIALIZATION")
    print("=" * 80)
    print(f"Target: {os.environ.get('MLSDM_HOST', 'http://localhost:8000')}")
    print("Users: 100 concurrent")
    print("Duration: 10 minutes")
    print("=" * 80 + "\n")


@events.test_start.add_listener
def on_test_start(environment: Any, **kwargs: Any) -> None:
    """Called when test starts."""
    global metrics
    metrics = MetricsCollector()
    print("Load test started. Collecting metrics...")


@events.test_stop.add_listener
def on_test_stop(environment: Any, **kwargs: Any) -> None:
    """Called when test stops."""
    print("\nLoad test completed. Generating report...")

    # Generate final report
    output_dir = os.environ.get("LOAD_TEST_OUTPUT_DIR", ".")
    report_path = os.path.join(output_dir, "load_test_report.json")
    metrics.generate_report(report_path)


# Periodic memory sampling
@events.test_start.add_listener
def start_memory_monitor(environment: Any, **kwargs: Any) -> None:
    """Start periodic memory monitoring."""

    def sample_memory() -> None:
        """Sample memory periodically."""
        while True:
            metrics.record_memory()
            time.sleep(5)  # Sample every 5 seconds

    # Only run on master or standalone (not on workers)
    if environment.runner is None or isinstance(environment.runner, MasterRunner):
        import threading

        monitor_thread = threading.Thread(target=sample_memory, daemon=True)
        monitor_thread.start()


# ============================================================================
# Standalone Test Mode
# ============================================================================


def run_standalone_test() -> None:
    """Run a standalone load test without Locust web UI."""
    import subprocess
    import sys

    print("\n" + "=" * 80)
    print("RUNNING STANDALONE LOAD TEST")
    print("=" * 80)
    print("Configuration:")
    print("  Users: 100")
    print("  Spawn Rate: 10 users/second")
    print("  Duration: 600 seconds (10 minutes)")
    print("=" * 80 + "\n")

    # Run locust in headless mode
    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        __file__,
        "--headless",
        "--users",
        "100",
        "--spawn-rate",
        "10",
        "--run-time",
        "600s",
        "--host",
        os.environ.get("MLSDM_HOST", "http://localhost:8000"),
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Load test failed: {e}")
        return

    print("\nStandalone load test completed successfully!")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MLSDM Load Test")
    parser.add_argument(
        "--standalone", action="store_true", help="Run standalone test without web UI"
    )
    parser.add_argument("--host", default="http://localhost:8000", help="Target host URL")

    args = parser.parse_args()

    # Set environment variable
    os.environ["MLSDM_HOST"] = args.host

    if args.standalone:
        run_standalone_test()
    else:
        print("\nTo run the load test, use one of these commands:")
        print("\n1. With Locust web UI:")
        print("   locust -f tests/load/locust_load_test.py --host http://localhost:8000")
        print("\n2. Headless mode (10 min, 100 users):")
        print(
            "   locust -f tests/load/locust_load_test.py --headless --users 100 "
            "--spawn-rate 10 --run-time 600s --host http://localhost:8000"
        )
        print("\n3. Standalone mode:")
        print("   python tests/load/locust_load_test.py --standalone --host http://localhost:8000")
        print()
