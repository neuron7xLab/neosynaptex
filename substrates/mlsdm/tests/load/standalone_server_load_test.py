"""
Standalone Server Load Test for MLSDM.

This is a self-contained load test that doesn't require Locust.
It starts the MLSDM server, runs load testing, and generates a report.

Features:
    - Auto-detects CI environment (GitHub Actions, GitLab CI, Jenkins, etc.)
    - Applies 1.5x timeout multiplier in CI for reliability
    - Graceful async task cancellation with proper cleanup
    - Comprehensive error logging

Usage:
    # Local testing
    python tests/load/standalone_server_load_test.py
    python tests/load/standalone_server_load_test.py --users 50 --duration 60

    # CI mode (explicit or auto-detected)
    python tests/load/standalone_server_load_test.py --ci-mode
    python tests/load/standalone_server_load_test.py --users 20 --duration 20 --ci-mode

Requirements:
    - httpx (pip install httpx)
    - uvicorn (already installed with MLSDM)
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, stdev
from typing import Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Import async utilities
from async_utils import calculate_timeout, graceful_cancel_tasks, is_ci_environment

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestResult:
    """Result from a single request."""

    success: bool
    latency_ms: float
    status_code: int
    error: str | None = None


@dataclass
class LoadTestReport:
    """Comprehensive load test report."""

    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    latencies: list[float] = field(default_factory=list)

    # Calculated metrics
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    avg_latency: float = 0.0
    min_latency: float = 0.0
    max_latency: float = 0.0
    std_latency: float = 0.0

    # Memory tracking
    initial_memory_mb: float = 0.0
    final_memory_mb: float = 0.0
    memory_growth_mb: float = 0.0

    # Status
    passed: bool = False
    errors: list[str] = field(default_factory=list)

    def calculate_percentiles(self) -> None:
        """Calculate latency percentiles from collected data.

        Uses nearest-rank method for percentile calculation.
        """
        if not self.latencies:
            return

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        self.min_latency = sorted_latencies[0]
        self.max_latency = sorted_latencies[-1]
        self.avg_latency = mean(sorted_latencies)

        if n >= 2:
            self.std_latency = stdev(sorted_latencies)

        # Nearest-rank percentile calculation
        def percentile(data: list[float], p: float) -> float:
            """Calculate p-th percentile using nearest-rank method."""
            k = max(0, int(len(data) * p) - 1)
            return data[min(k, len(data) - 1)]

        self.p50_latency = percentile(sorted_latencies, 0.50)
        self.p95_latency = percentile(sorted_latencies, 0.95)
        self.p99_latency = percentile(sorted_latencies, 0.99)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "test_info": {
                "duration_seconds": self.duration_seconds,
                "timestamp": datetime.now().isoformat(),
            },
            "request_metrics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate_percent": round(
                    self.successful_requests / max(1, self.total_requests) * 100, 2
                ),
                "requests_per_second": round(self.requests_per_second, 2),
            },
            "latency_metrics_ms": {
                "p50": round(self.p50_latency, 2),
                "p95": round(self.p95_latency, 2),
                "p99": round(self.p99_latency, 2),
                "avg": round(self.avg_latency, 2),
                "min": round(self.min_latency, 2),
                "max": round(self.max_latency, 2),
                "std": round(self.std_latency, 2),
            },
            "memory_metrics_mb": {
                "initial": round(self.initial_memory_mb, 2),
                "final": round(self.final_memory_mb, 2),
                "growth": round(self.memory_growth_mb, 2),
            },
            "status": {
                "passed": self.passed,
                "errors": self.errors[:10],  # Limit to first 10 errors
            },
        }

    def print_report(self) -> None:
        """Print formatted report to console."""
        print("\n" + "=" * 70)
        print("MLSDM STANDALONE LOAD TEST REPORT")
        print("=" * 70)
        print(f"\nTest Duration: {self.duration_seconds:.1f} seconds")
        print(f"Timestamp: {datetime.now().isoformat()}")

        print("\n--- Request Metrics ---")
        print(f"Total Requests:      {self.total_requests}")
        print(f"Successful Requests: {self.successful_requests}")
        print(f"Failed Requests:     {self.failed_requests}")
        success_rate = self.successful_requests / max(1, self.total_requests) * 100
        print(f"Success Rate:        {success_rate:.1f}%")
        print(f"Requests/Second:     {self.requests_per_second:.1f}")

        print("\n--- Latency Metrics (ms) ---")
        print(f"P50:  {self.p50_latency:.2f}")
        print(f"P95:  {self.p95_latency:.2f}")
        print(f"P99:  {self.p99_latency:.2f}")
        print(f"Avg:  {self.avg_latency:.2f}")
        print(f"Min:  {self.min_latency:.2f}")
        print(f"Max:  {self.max_latency:.2f}")
        print(f"Std:  {self.std_latency:.2f}")

        print("\n--- Memory Metrics (MB) ---")
        print(f"Initial: {self.initial_memory_mb:.1f}")
        print(f"Final:   {self.final_memory_mb:.1f}")
        print(f"Growth:  {self.memory_growth_mb:.1f}")

        print("\n--- Status ---")
        if self.passed:
            print("✅ LOAD TEST PASSED")
        else:
            print("❌ LOAD TEST FAILED")
            if self.errors:
                print("\nErrors:")
                for err in self.errors[:5]:
                    print(f"  - {err}")

        print("=" * 70 + "\n")


class StandaloneLoadTest:
    """Standalone load test runner."""

    def __init__(
        self,
        host: str = "http://localhost:8000",
        concurrent_users: int = 10,
        duration_seconds: int = 30,
        warmup_seconds: int = 5,
        ci_mode: bool = False,
    ):
        self.host = host
        self.concurrent_users = concurrent_users
        self.duration_seconds = duration_seconds
        self.warmup_seconds = warmup_seconds
        self.ci_mode = ci_mode or is_ci_environment()
        self.stop_event = asyncio.Event()
        # Thread-safe queue for collecting results from concurrent workers
        self._results_queue: asyncio.Queue[LoadTestResult] = asyncio.Queue()

        logger.info(
            f"Load test configuration: users={concurrent_users}, "
            f"duration={duration_seconds}s, CI mode={'enabled' if self.ci_mode else 'disabled'}"
        )

    async def make_request(self, client: Any, request_type: str) -> LoadTestResult:
        """Make a single request to the server."""
        start_time = time.perf_counter()

        try:
            if request_type == "generate":
                response = await client.post(
                    f"{self.host}/generate",
                    json={
                        "prompt": f"Test prompt {time.time()}",
                        "moral_value": 0.8,
                        "max_tokens": 50,
                    },
                    timeout=10.0,
                )
            elif request_type == "health":
                response = await client.get(
                    f"{self.host}/health",
                    timeout=5.0,
                )
            else:
                response = await client.get(
                    f"{self.host}/status",
                    timeout=5.0,
                )

            latency_ms = (time.perf_counter() - start_time) * 1000

            return LoadTestResult(
                success=response.status_code in (200, 400),  # 400 is expected for moral filter
                latency_ms=latency_ms,
                status_code=response.status_code,
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return LoadTestResult(
                success=False,
                latency_ms=latency_ms,
                status_code=0,
                error=str(e),
            )

    async def worker(self, worker_id: int, client: Any) -> None:
        """Worker that makes requests in a loop."""
        import random

        while not self.stop_event.is_set():
            # Weighted random selection: 60% generate, 20% health, 20% status
            rand = random.random()
            if rand < 0.6:
                request_type = "generate"
            elif rand < 0.8:
                request_type = "health"
            else:
                request_type = "status"

            result = await self.make_request(client, request_type)
            await self._results_queue.put(result)

            # Small delay to avoid overwhelming
            await asyncio.sleep(random.uniform(0.05, 0.2))

    async def get_server_memory(self) -> float:
        """Get server memory usage via status endpoint."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.host}/status", timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("system", {}).get("memory_mb", 0)
        except Exception:
            pass
        return 0.0

    async def run_test(self) -> LoadTestReport:
        """Run the load test."""
        import httpx

        print(f"\n🚀 Starting load test: {self.concurrent_users} users, {self.duration_seconds}s")
        print(f"   Target: {self.host}")

        # Get initial memory
        initial_memory = await self.get_server_memory()

        # Warmup phase
        if self.warmup_seconds > 0:
            print(f"   Warmup: {self.warmup_seconds}s...")
            async with httpx.AsyncClient() as client:
                for _ in range(3):
                    try:
                        await client.get(f"{self.host}/health", timeout=5.0)
                    except Exception:
                        pass
            await asyncio.sleep(self.warmup_seconds)

        # Main test phase
        print(f"   Running load test for {self.duration_seconds}s...")
        start_time = time.time()

        async with httpx.AsyncClient() as client:
            # Create worker tasks
            workers = [
                asyncio.create_task(self.worker(i, client)) for i in range(self.concurrent_users)
            ]

            # Wait for duration
            await asyncio.sleep(self.duration_seconds)

            # Signal workers to stop
            self.stop_event.set()

            # Wait for workers to finish (with CI-aware timeout)
            # Base timeout is 10s, adjusted to 15s in CI environments
            shutdown_timeout = calculate_timeout(10.0, self.ci_mode)
            logger.debug(f"Waiting for {len(workers)} workers to stop (timeout={shutdown_timeout:.1f}s)")

            try:
                await graceful_cancel_tasks(workers, timeout=shutdown_timeout, ci_mode=self.ci_mode)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Worker shutdown timeout after {shutdown_timeout:.1f}s, "
                    f"some workers may still be running"
                )

        elapsed = time.time() - start_time

        # Get final memory
        final_memory = await self.get_server_memory()

        # Collect all results from queue (thread-safe)
        results: list[LoadTestResult] = []
        while not self._results_queue.empty():
            try:
                results.append(self._results_queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        # Calculate report
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        report = LoadTestReport(
            duration_seconds=elapsed,
            total_requests=len(results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            requests_per_second=len(results) / elapsed if elapsed > 0 else 0,
            latencies=[r.latency_ms for r in successful],
            initial_memory_mb=initial_memory,
            final_memory_mb=final_memory,
            memory_growth_mb=final_memory - initial_memory,
            errors=[r.error for r in failed if r.error][:10],
        )

        report.calculate_percentiles()

        # Determine pass/fail criteria
        # Pass if: success rate > 95%, P95 < 500ms, memory growth < 100MB
        success_rate = len(successful) / max(1, len(results)) * 100
        report.passed = (
            success_rate >= 95.0 and report.p95_latency < 500.0 and report.memory_growth_mb < 100.0
        )

        return report


async def wait_for_server(host: str, timeout: int = 30, ci_mode: bool = False) -> bool:
    """Wait for server to be ready."""
    import httpx

    # Adjust timeout for CI environments
    adjusted_timeout = calculate_timeout(float(timeout), ci_mode)

    print(f"   Waiting for server at {host}...")
    logger.debug(f"Server readiness check timeout: {adjusted_timeout:.1f}s (base={timeout}s)")
    start = time.time()

    while time.time() - start < adjusted_timeout:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{host}/health", timeout=2.0)
                if response.status_code == 200:
                    print("   ✅ Server is ready!")
                    logger.info(f"Server became ready after {time.time() - start:.1f}s")
                    return True
        except Exception as e:
            logger.debug(f"Server not ready yet: {e}")
        await asyncio.sleep(1)

    print("   ❌ Server failed to start within timeout")
    logger.error(f"Server failed to become ready within {adjusted_timeout:.1f}s")
    return False


def start_server(port: int = 8765) -> subprocess.Popen[bytes] | None:
    """Start the MLSDM server."""
    print(f"   Starting MLSDM server on port {port}...")

    env = os.environ.copy()
    env["DISABLE_RATE_LIMIT"] = "1"  # Disable rate limiting for load test
    env["LLM_BACKEND"] = "local_stub"  # Use stub backend
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..", "..", "src")

    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "mlsdm.api.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--workers",
                "1",
                "--log-level",
                "warning",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return process
    except Exception as e:
        print(f"   Failed to start server: {e}")
        return None


async def run_standalone_test(
    users: int = 10,
    duration: int = 30,
    host: str | None = None,
    start_server_flag: bool = True,
    ci_mode: bool = False,
) -> LoadTestReport:
    """Run a complete standalone load test."""
    print("\n" + "=" * 70)
    print("MLSDM STANDALONE SERVER LOAD TEST")
    print("=" * 70)

    # Auto-detect CI mode
    ci_mode = ci_mode or is_ci_environment()
    if ci_mode:
        logger.info("CI mode enabled (detected from environment or explicit flag)")

    server_process = None
    test_host = host or "http://127.0.0.1:8765"

    try:
        # Start server if requested
        if start_server_flag and host is None:
            server_process = start_server()
            if server_process is None:
                report = LoadTestReport(
                    duration_seconds=0,
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    requests_per_second=0,
                    passed=False,
                    errors=["Failed to start server"],
                )
                return report

            # Wait for server to be ready (with CI-aware timeout)
            server_timeout = 60 if ci_mode else 30
            if not await wait_for_server(test_host, timeout=server_timeout, ci_mode=ci_mode):
                report = LoadTestReport(
                    duration_seconds=0,
                    total_requests=0,
                    successful_requests=0,
                    failed_requests=0,
                    requests_per_second=0,
                    passed=False,
                    errors=["Server failed to become ready"],
                )
                return report

        # Run load test
        load_test = StandaloneLoadTest(
            host=test_host,
            concurrent_users=users,
            duration_seconds=duration,
            warmup_seconds=3,
            ci_mode=ci_mode,
        )

        report = await load_test.run_test()
        return report

    finally:
        # Stop server with appropriate timeout
        if server_process is not None:
            print("\n   Stopping server...")
            server_process.send_signal(signal.SIGTERM)
            shutdown_timeout = 10 if ci_mode else 5
            try:
                server_process.wait(timeout=shutdown_timeout)
                logger.info("Server stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("Server shutdown timeout, forcing kill")
                server_process.kill()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="MLSDM Standalone Server Load Test")
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Number of concurrent users (default: 10)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Test duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Target host URL (default: start local server)",
    )
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Don't start a server (use existing)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for JSON report",
    )
    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Enable CI mode with conservative timeouts (auto-detected from environment)",
    )

    args = parser.parse_args()

    # Run the test
    report = asyncio.run(
        run_standalone_test(
            users=args.users,
            duration=args.duration,
            host=args.host,
            start_server_flag=not args.no_server,
            ci_mode=args.ci_mode,
        )
    )

    # Print report
    report.print_report()

    # Save JSON report if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"Report saved to: {args.output}")

    # Exit with appropriate code
    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
