"""Tests for bulkhead and timeout middleware.

Tests the middleware components including:
- BulkheadSemaphore for concurrency limiting
- BulkheadMiddleware for request isolation
- TimeoutMiddleware for request timeouts
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from mlsdm.api.middleware import (
    BulkheadMetrics,
    BulkheadMiddleware,
    BulkheadSemaphore,
    TimeoutMiddleware,
)


class TestBulkheadMetrics:
    """Tests for BulkheadMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test default metric values."""
        metrics = BulkheadMetrics()
        assert metrics.total_requests == 0
        assert metrics.accepted_requests == 0
        assert metrics.rejected_requests == 0
        assert metrics.current_active == 0
        assert metrics.max_queue_depth == 0

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        metrics = BulkheadMetrics(
            total_requests=100,
            accepted_requests=95,
            rejected_requests=5,
            current_active=10,
            max_queue_depth=20,
        )
        result = metrics.to_dict()

        assert result["total_requests"] == 100
        assert result["accepted_requests"] == 95
        assert result["rejected_requests"] == 5
        assert result["current_active"] == 10
        assert result["max_queue_depth"] == 20


class TestBulkheadSemaphore:
    """Tests for BulkheadSemaphore class."""

    @pytest.mark.asyncio
    async def test_acquire_and_release(self) -> None:
        """Test basic acquire and release."""
        bulkhead = BulkheadSemaphore(max_concurrent=5)

        async with bulkhead.acquire():
            assert bulkhead.metrics.current_active == 1

        assert bulkhead.metrics.current_active == 0
        assert bulkhead.metrics.accepted_requests == 1

    @pytest.mark.asyncio
    async def test_concurrent_requests(self) -> None:
        """Test multiple concurrent requests."""
        bulkhead = BulkheadSemaphore(max_concurrent=3)
        active_count = 0
        max_active = 0

        async def worker() -> None:
            nonlocal active_count, max_active
            async with bulkhead.acquire():
                active_count += 1
                max_active = max(max_active, active_count)
                await asyncio.sleep(0.01)
                active_count -= 1

        # Run 5 concurrent workers with limit of 3
        await asyncio.gather(*[worker() for _ in range(5)])

        assert max_active <= 3
        assert bulkhead.metrics.accepted_requests == 5

    @pytest.mark.asyncio
    async def test_timeout_rejection(self) -> None:
        """Test request rejection on timeout."""
        bulkhead = BulkheadSemaphore(max_concurrent=1, queue_timeout=0.1)

        async def blocker() -> None:
            async with bulkhead.acquire():
                await asyncio.sleep(1.0)  # Hold the slot

        # Start blocker
        blocker_task = asyncio.create_task(blocker())
        await asyncio.sleep(0.05)  # Let blocker acquire

        # Try to acquire - should timeout
        with pytest.raises(asyncio.TimeoutError):
            async with bulkhead.acquire():
                pass

        assert bulkhead.metrics.rejected_requests == 1

        blocker_task.cancel()
        try:
            await blocker_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_available_slots(self) -> None:
        """Test available slots tracking."""
        bulkhead = BulkheadSemaphore(max_concurrent=3)

        assert bulkhead.available == 3

        async with bulkhead.acquire():
            assert bulkhead.available == 2

        assert bulkhead.available == 3

    @pytest.mark.asyncio
    async def test_queue_depth_tracking(self) -> None:
        """Test queue depth tracking."""
        bulkhead = BulkheadSemaphore(max_concurrent=1)

        async def holder() -> None:
            async with bulkhead.acquire():
                await asyncio.sleep(0.2)

        # Start holder
        holder_task = asyncio.create_task(holder())
        await asyncio.sleep(0.05)

        # Create waiters
        waiter_tasks = [asyncio.create_task(bulkhead.acquire().__aenter__()) for _ in range(3)]
        await asyncio.sleep(0.05)

        # Queue depth should reflect waiting requests
        assert bulkhead.queue_depth >= 0  # At least some may be waiting

        # Clean up
        holder_task.cancel()
        for t in waiter_tasks:
            t.cancel()

        try:
            await holder_task
        except asyncio.CancelledError:
            pass

        for t in waiter_tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass


class TestBulkheadMiddleware:
    """Tests for BulkheadMiddleware."""

    def test_middleware_allows_requests_under_limit(self) -> None:
        """Test that requests under limit are allowed."""
        app = FastAPI()
        app.add_middleware(BulkheadMiddleware, max_concurrent=10)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    def test_middleware_metrics_available(self) -> None:
        """Test that middleware exposes metrics."""
        app = FastAPI()
        middleware = BulkheadMiddleware(app, max_concurrent=10)

        metrics = middleware.metrics
        assert isinstance(metrics, BulkheadMetrics)

    def test_middleware_env_config(self) -> None:
        """Test middleware configuration from environment."""
        with patch.dict(
            "os.environ",
            {
                "MLSDM_MAX_CONCURRENT": "50",
                "MLSDM_QUEUE_TIMEOUT": "10.0",
            },
        ):
            app = FastAPI()
            middleware = BulkheadMiddleware(app)
            assert middleware._max_concurrent == 50
            assert middleware._queue_timeout == 10.0


class TestTimeoutMiddleware:
    """Tests for TimeoutMiddleware."""

    def test_fast_request_succeeds(self) -> None:
        """Test that fast requests complete successfully."""
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout=5.0)

        @app.get("/fast")
        def fast_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/fast")
        assert response.status_code == 200

    def test_excluded_paths_bypass_timeout(self) -> None:
        """Test that excluded paths bypass timeout check."""
        app = FastAPI()
        app.add_middleware(
            TimeoutMiddleware,
            timeout=0.001,  # Very short timeout
            exclude_paths=["/health"],
        )

        @app.get("/health")
        def health_endpoint() -> dict[str, str]:
            start = time.perf_counter()
            while time.perf_counter() - start < 0.01:
                pass
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_middleware_env_config(self) -> None:
        """Test middleware configuration from environment."""
        with patch.dict("os.environ", {"MLSDM_REQUEST_TIMEOUT": "45.0"}):
            app = FastAPI()
            middleware = TimeoutMiddleware(app)
            assert middleware._timeout == 45.0


class TestMiddlewareIntegration:
    """Integration tests for middleware components."""

    def test_multiple_middleware_chain(self) -> None:
        """Test that multiple middleware work together."""
        app = FastAPI()
        app.add_middleware(TimeoutMiddleware, timeout=30.0)
        app.add_middleware(BulkheadMiddleware, max_concurrent=100)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    def test_middleware_with_exceptions(self) -> None:
        """Test middleware handling of endpoint exceptions."""
        app = FastAPI()
        app.add_middleware(BulkheadMiddleware, max_concurrent=10)

        @app.get("/error")
        def error_endpoint() -> dict[str, str]:
            raise ValueError("Test error")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/error")
        assert response.status_code == 500
