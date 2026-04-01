"""Load testing utilities for performance validation.

Provides helpers for running controlled load tests with deterministic results.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class LoadTestResults:
    """Aggregated results from a load test run.

    Attributes:
        total_requests: Total number of requests attempted
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        latencies_ms: List of latency measurements in milliseconds
        errors: List of error types encountered
        mean_latency_ms: Mean latency
        p50_latency_ms: 50th percentile (median) latency
        p95_latency_ms: 95th percentile latency
        p99_latency_ms: 99th percentile latency
        min_latency_ms: Minimum latency observed
        max_latency_ms: Maximum latency observed
        error_rate_percent: Percentage of requests that failed
        requests_per_second: Average throughput
    """

    total_requests: int
    successful_requests: int
    failed_requests: int
    latencies_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # Computed metrics (calculated post-init)
    mean_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    error_rate_percent: float = 0.0
    requests_per_second: float = 0.0
    total_duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        """Calculate derived metrics after initialization."""
        if self.latencies_ms:
            self.mean_latency_ms = statistics.mean(self.latencies_ms)
            self.min_latency_ms = min(self.latencies_ms)
            self.max_latency_ms = max(self.latencies_ms)

            # Use numpy for percentile calculations
            latency_array = np.array(self.latencies_ms)
            self.p50_latency_ms = float(np.percentile(latency_array, 50))
            self.p95_latency_ms = float(np.percentile(latency_array, 95))
            self.p99_latency_ms = float(np.percentile(latency_array, 99))

        if self.total_requests > 0:
            self.error_rate_percent = (self.failed_requests / self.total_requests) * 100.0

        if self.total_duration_seconds > 0:
            self.requests_per_second = self.total_requests / self.total_duration_seconds


def run_load_test(
    operation: Callable[[], Any],
    n_requests: int,
    concurrency: int = 1,
    timeout_per_request: float = 30.0,
) -> LoadTestResults:
    """Run a synchronous load test against an operation.

    Args:
        operation: Callable that performs a single request (should be sync)
        n_requests: Total number of requests to make
        concurrency: Number of concurrent workers
        timeout_per_request: Maximum time to wait for each request

    Returns:
        LoadTestResults with aggregated metrics
    """
    latencies: list[float] = []
    errors: list[str] = []
    successful = 0
    failed = 0

    def execute_single_request() -> tuple[bool, float, str | None]:
        """Execute a single request and return (success, latency_ms, error)."""
        start = time.perf_counter()
        try:
            operation()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return (True, elapsed_ms, None)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return (False, elapsed_ms, type(e).__name__)

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(execute_single_request) for _ in range(n_requests)]

        for future in as_completed(futures, timeout=n_requests * timeout_per_request):
            success, latency_ms, error = future.result()
            latencies.append(latency_ms)

            if success:
                successful += 1
            else:
                failed += 1
                if error:
                    errors.append(error)

    total_duration = time.perf_counter() - start_time

    results = LoadTestResults(
        total_requests=n_requests,
        successful_requests=successful,
        failed_requests=failed,
        latencies_ms=latencies,
        errors=errors,
    )
    results.total_duration_seconds = total_duration
    results.requests_per_second = n_requests / total_duration if total_duration > 0 else 0.0

    return results


async def run_async_load_test(
    operation: Callable[[], Any],
    n_requests: int,
    concurrency: int = 1,
    timeout_per_request: float = 30.0,
) -> LoadTestResults:
    """Run an asynchronous load test against an async operation.

    Args:
        operation: Async callable that performs a single request
        n_requests: Total number of requests to make
        concurrency: Number of concurrent tasks
        timeout_per_request: Maximum time to wait for each request

    Returns:
        LoadTestResults with aggregated metrics
    """
    latencies: list[float] = []
    errors: list[str] = []
    successful = 0
    failed = 0

    async def execute_single_request() -> tuple[bool, float, str | None]:
        """Execute a single async request and return (success, latency_ms, error)."""
        start = time.perf_counter()
        try:
            await operation()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return (True, elapsed_ms, None)
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return (False, elapsed_ms, type(e).__name__)

    start_time = time.perf_counter()

    # Run requests in batches to control concurrency
    tasks: list[asyncio.Task[tuple[bool, float, str | None]]] = []
    for _ in range(n_requests):
        task = asyncio.create_task(execute_single_request())
        tasks.append(task)

        # Limit concurrent tasks
        if len(tasks) >= concurrency:
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED, timeout=timeout_per_request
            )
            tasks = list(pending)

            for task_done in done:
                success, latency_ms, error = task_done.result()
                latencies.append(latency_ms)

                if success:
                    successful += 1
                else:
                    failed += 1
                    if error:
                        errors.append(error)

    # Wait for remaining tasks
    if tasks:
        done, _ = await asyncio.wait(tasks, timeout=timeout_per_request)
        for task in done:
            success, latency_ms, error = task.result()
            latencies.append(latency_ms)

            if success:
                successful += 1
            else:
                failed += 1
                if error:
                    errors.append(error)

    total_duration = time.perf_counter() - start_time

    results = LoadTestResults(
        total_requests=n_requests,
        successful_requests=successful,
        failed_requests=failed,
        latencies_ms=latencies,
        errors=errors,
    )
    results.total_duration_seconds = total_duration
    results.requests_per_second = n_requests / total_duration if total_duration > 0 else 0.0

    return results


def create_stub_llm_provider() -> Callable[[str], str]:
    """Create a deterministic stub LLM provider for testing.

    Returns a callable that simulates LLM generation with predictable latency.
    """

    def stub_generate(prompt: str) -> str:
        """Stub LLM generation with minimal, predictable latency."""
        # Simulate minimal processing time (< 1ms)
        time.sleep(0.0001)
        return f"Response to: {prompt[:50]}"

    return stub_generate
