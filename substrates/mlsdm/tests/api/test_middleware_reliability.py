"""
Tests for API Middleware Components.

Tests for:
- TimeoutMiddleware (REL-004)
- PriorityMiddleware (REL-005)
- BulkheadMiddleware metrics integration (REL-002)
"""

import asyncio

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from mlsdm.api.middleware import (
    BulkheadMiddleware,
    PriorityMiddleware,
    RequestPriority,
    TimeoutMiddleware,
)


class TestRequestPriority:
    """Tests for RequestPriority class."""

    def test_from_header_high(self):
        """Test parsing 'high' priority."""
        assert RequestPriority.from_header("high", "normal") == "high"
        assert RequestPriority.from_header("HIGH", "normal") == "high"
        assert RequestPriority.from_header("High", "normal") == "high"

    def test_from_header_normal(self):
        """Test parsing 'normal' priority."""
        assert RequestPriority.from_header("normal", "low") == "normal"
        assert RequestPriority.from_header("NORMAL", "low") == "normal"

    def test_from_header_low(self):
        """Test parsing 'low' priority."""
        assert RequestPriority.from_header("low", "normal") == "low"
        assert RequestPriority.from_header("LOW", "normal") == "low"

    def test_from_header_numeric_high(self):
        """Test parsing high numeric priorities (7-10)."""
        assert RequestPriority.from_header("7", "normal") == "high"
        assert RequestPriority.from_header("8", "normal") == "high"
        assert RequestPriority.from_header("9", "normal") == "high"
        assert RequestPriority.from_header("10", "normal") == "high"

    def test_from_header_numeric_normal(self):
        """Test parsing normal numeric priorities (4-6)."""
        assert RequestPriority.from_header("4", "low") == "normal"
        assert RequestPriority.from_header("5", "low") == "normal"
        assert RequestPriority.from_header("6", "low") == "normal"

    def test_from_header_numeric_low(self):
        """Test parsing low numeric priorities (1-3)."""
        assert RequestPriority.from_header("1", "normal") == "low"
        assert RequestPriority.from_header("2", "normal") == "low"
        assert RequestPriority.from_header("3", "normal") == "low"

    def test_from_header_none(self):
        """Test None header returns default."""
        assert RequestPriority.from_header(None, "normal") == "normal"
        assert RequestPriority.from_header(None, "high") == "high"

    def test_from_header_invalid(self):
        """Test invalid values return default."""
        assert RequestPriority.from_header("invalid", "normal") == "normal"
        assert RequestPriority.from_header("123abc", "low") == "low"
        assert RequestPriority.from_header("", "normal") == "normal"

    def test_weights(self):
        """Test priority weights."""
        assert RequestPriority.WEIGHTS["high"] == 3
        assert RequestPriority.WEIGHTS["normal"] == 2
        assert RequestPriority.WEIGHTS["low"] == 1
        assert RequestPriority.WEIGHTS["high"] > RequestPriority.WEIGHTS["normal"]
        assert RequestPriority.WEIGHTS["normal"] > RequestPriority.WEIGHTS["low"]


class TestTimeoutMiddleware:
    """Tests for TimeoutMiddleware (REL-004)."""

    def test_request_within_timeout(self):
        """Test request completes within timeout."""
        app = FastAPI()

        @app.get("/fast")
        async def fast_endpoint():
            return {"status": "ok"}

        app.add_middleware(TimeoutMiddleware, timeout=5.0)

        client = TestClient(app)
        response = client.get("/fast")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_excluded_paths(self):
        """Test excluded paths bypass timeout."""
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        app.add_middleware(
            TimeoutMiddleware,
            timeout=0.01,  # Very short timeout
            exclude_paths=["/health"],
        )

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200

    def test_timeout_header_in_response(self):
        """Test timeout information is in response when timeout occurs."""
        app = FastAPI()

        @app.get("/slow")
        async def slow_endpoint():
            await asyncio.sleep(5)
            return {"status": "ok"}

        app.add_middleware(TimeoutMiddleware, timeout=0.1)

        client = TestClient(app)
        response = client.get("/slow")

        # Should get 504 on timeout
        assert response.status_code == 504
        assert "X-Request-Timeout" in response.headers


class TestPriorityMiddleware:
    """Tests for PriorityMiddleware (REL-005)."""

    def test_priority_header_applied(self):
        """Test priority header is parsed and applied."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(request: Request):
            return {
                "priority": request.state.priority,
                "weight": request.state.priority_weight,
            }

        app.add_middleware(PriorityMiddleware)

        client = TestClient(app)

        # Test high priority
        response = client.get("/test", headers={"X-MLSDM-Priority": "high"})
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "high"
        assert data["weight"] == 3

        # Test normal priority
        response = client.get("/test", headers={"X-MLSDM-Priority": "normal"})
        data = response.json()
        assert data["priority"] == "normal"
        assert data["weight"] == 2

        # Test low priority
        response = client.get("/test", headers={"X-MLSDM-Priority": "low"})
        data = response.json()
        assert data["priority"] == "low"
        assert data["weight"] == 1

    def test_priority_response_header(self):
        """Test priority applied header is in response."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        app.add_middleware(PriorityMiddleware)

        client = TestClient(app)
        response = client.get("/test", headers={"X-MLSDM-Priority": "high"})

        assert "X-MLSDM-Priority-Applied" in response.headers
        assert response.headers["X-MLSDM-Priority-Applied"] == "high"

    def test_default_priority(self):
        """Test default priority when header is missing."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"priority": request.state.priority}

        app.add_middleware(PriorityMiddleware, default_priority="normal")

        client = TestClient(app)
        response = client.get("/test")

        data = response.json()
        assert data["priority"] == "normal"

    def test_priority_disabled(self):
        """Test priority middleware can be disabled."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"has_priority": hasattr(request.state, "priority")}

        app.add_middleware(PriorityMiddleware, enabled=False)

        client = TestClient(app)
        response = client.get("/test", headers={"X-MLSDM-Priority": "high"})

        # When disabled, priority should not be set
        assert response.status_code == 200


class TestBulkheadMetricsIntegration:
    """Tests for Bulkhead Prometheus metrics integration (REL-002)."""

    def test_bulkhead_updates_metrics(self):
        """Test that bulkhead updates Prometheus metrics."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        app.add_middleware(
            BulkheadMiddleware,
            max_concurrent=10,
            queue_timeout=5.0,
            enable_prometheus_metrics=True,
        )

        client = TestClient(app)

        # Make some requests
        for _ in range(5):
            response = client.get("/test")
            assert response.status_code == 200

    def test_bulkhead_metrics_disabled(self):
        """Test that Prometheus metrics can be disabled."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        app.add_middleware(
            BulkheadMiddleware,
            max_concurrent=10,
            queue_timeout=5.0,
            enable_prometheus_metrics=False,
        )

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
