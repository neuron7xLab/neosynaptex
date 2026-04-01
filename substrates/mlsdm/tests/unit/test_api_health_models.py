"""
Comprehensive tests for api/health.py.

Tests cover:
- Health check endpoints
- Memory manager reference management
- Health status models
"""

from unittest.mock import MagicMock

import pytest

from mlsdm.api.health import (
    ComponentStatus,
    DetailedHealthStatus,
    HealthStatus,
    ReadinessStatus,
    SimpleHealthStatus,
    get_memory_manager,
    set_memory_manager,
)


class TestSimpleHealthStatus:
    """Tests for SimpleHealthStatus model."""

    def test_simple_health_status_creation(self):
        """Test SimpleHealthStatus creation."""
        status = SimpleHealthStatus(status="healthy")
        assert status.status == "healthy"

    def test_simple_health_status_unhealthy(self):
        """Test SimpleHealthStatus with unhealthy status."""
        status = SimpleHealthStatus(status="unhealthy")
        assert status.status == "unhealthy"


class TestHealthStatus:
    """Tests for HealthStatus model."""

    def test_health_status_creation(self):
        """Test HealthStatus creation."""
        status = HealthStatus(status="healthy", timestamp=1234567890.0)
        assert status.status == "healthy"
        assert status.timestamp == 1234567890.0


class TestReadinessStatus:
    """Tests for ReadinessStatus model."""

    def test_readiness_status_creation(self):
        """Test ReadinessStatus creation."""
        status = ReadinessStatus(
            ready=True,
            status="ready",
            timestamp=1234567890.0,
            checks={"memory": True, "llm": True},
            components={
                "memory": ComponentStatus(healthy=True),
                "llm": ComponentStatus(healthy=True),
            },
        )
        assert status.ready is True
        assert status.status == "ready"
        assert status.checks["memory"] is True
        assert status.checks["llm"] is True
        assert status.components["memory"].healthy is True

    def test_readiness_status_not_ready(self):
        """Test ReadinessStatus when not ready."""
        status = ReadinessStatus(
            ready=False,
            status="degraded",
            timestamp=1234567890.0,
            checks={"memory": True, "llm": False},
            components={
                "memory": ComponentStatus(healthy=True),
                "llm": ComponentStatus(healthy=False, details="LLM unavailable"),
            },
        )
        assert status.ready is False
        assert status.checks["llm"] is False
        assert status.components["llm"].healthy is False


class TestDetailedHealthStatus:
    """Tests for DetailedHealthStatus model."""

    def test_detailed_health_status_creation(self):
        """Test DetailedHealthStatus creation."""
        status = DetailedHealthStatus(
            status="healthy",
            timestamp=1234567890.0,
            uptime_seconds=3600.0,
            system={"cpu_percent": 25.0, "memory_percent": 50.0},
            memory_state={"l1_norm": 0.5, "l2_norm": 0.3, "l3_norm": 0.1},
            phase="wake",
            statistics={"events_processed": 100},
        )
        assert status.status == "healthy"
        assert status.uptime_seconds == 3600.0
        assert status.system["cpu_percent"] == 25.0
        assert status.memory_state is not None
        assert status.phase == "wake"

    def test_detailed_health_status_without_optional_fields(self):
        """Test DetailedHealthStatus without optional fields."""
        status = DetailedHealthStatus(
            status="healthy",
            timestamp=1234567890.0,
            uptime_seconds=100.0,
            system={},
            memory_state=None,
            phase=None,
            statistics=None,
        )
        assert status.memory_state is None
        assert status.phase is None
        assert status.statistics is None


class TestMemoryManagerReference:
    """Tests for memory manager reference management."""

    def setup_method(self):
        """Reset memory manager before each test."""
        import mlsdm.api.health as health_module

        health_module._memory_manager = None

    def test_set_memory_manager(self):
        """Test setting memory manager."""
        mock_manager = MagicMock()
        set_memory_manager(mock_manager)
        assert get_memory_manager() is mock_manager

    def test_get_memory_manager_when_none(self):
        """Test getting memory manager when not set."""
        assert get_memory_manager() is None

    def test_set_memory_manager_twice(self):
        """Test setting memory manager twice (replaces)."""
        mock_manager1 = MagicMock()
        mock_manager2 = MagicMock()

        set_memory_manager(mock_manager1)
        assert get_memory_manager() is mock_manager1

        set_memory_manager(mock_manager2)
        assert get_memory_manager() is mock_manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
