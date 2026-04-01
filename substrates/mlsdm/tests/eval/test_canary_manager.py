"""
Tests for Canary Manager progressive delivery functionality.

This module tests the canary deployment manager, including:
- Traffic ramping
- Automatic rollback on high error rates
- Error budget management
- Latency-based rollback
"""

import pytest

from mlsdm.deploy.canary_manager import CanaryManager


class TestCanaryManagerBasics:
    """Basic tests for CanaryManager."""

    def test_canary_manager_initialization(self) -> None:
        """Test that canary manager initializes correctly."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.1,
            error_budget_threshold=0.05,
        )

        assert manager.current_version == "v1"
        assert manager.candidate_version == "v2"
        assert manager.candidate_ratio == 0.1
        assert manager.error_budget_threshold == 0.05
        assert not manager.is_rollback_triggered()

    def test_canary_manager_invalid_ratios(self) -> None:
        """Test that invalid ratios raise errors."""
        with pytest.raises(ValueError, match="candidate_ratio"):
            CanaryManager(
                current_version="v1",
                candidate_version="v2",
                candidate_ratio=1.5,
            )

        with pytest.raises(ValueError, match="error_budget_threshold"):
            CanaryManager(
                current_version="v1",
                candidate_version="v2",
                error_budget_threshold=-0.1,
            )

    def test_select_version_respects_ratio(self) -> None:
        """Test that version selection respects the candidate ratio."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.2,
        )

        # Sample many selections
        selections = {"v1": 0, "v2": 0}
        num_samples = 1000

        for _ in range(num_samples):
            version = manager.select_version()
            selections[version] += 1

        # Check approximate ratio (allow 10% tolerance)
        v2_ratio = selections["v2"] / num_samples
        assert 0.1 <= v2_ratio <= 0.3, f"v2 ratio: {v2_ratio}"

    def test_select_version_extreme_ratios(self) -> None:
        """Test version selection with extreme ratios."""
        # 0% candidate
        manager_0 = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.0,
        )

        for _ in range(100):
            assert manager_0.select_version() == "v1"

        # 100% candidate
        manager_100 = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=1.0,
        )

        for _ in range(100):
            assert manager_100.select_version() == "v2"


class TestCanaryManagerRollback:
    """Tests for automatic rollback functionality."""

    def test_canary_reduces_traffic_on_errors(self) -> None:
        """Test that high error rate triggers rollback."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
        )

        # Report successful requests for current version
        for _ in range(100):
            manager.report_outcome("v1", success=True, latency_ms=50.0)

        # Report mostly failed requests for candidate
        for _ in range(8):
            manager.report_outcome("v2", success=False)
        for _ in range(2):
            manager.report_outcome("v2", success=True, latency_ms=50.0)

        # Should trigger rollback (80% error rate > 5% threshold)
        assert manager.is_rollback_triggered()
        assert manager.candidate_ratio == 0.0

    def test_canary_no_rollback_on_good_metrics(self) -> None:
        """Test that good metrics don't trigger rollback."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
        )

        # Report successful requests for both versions
        for _ in range(100):
            manager.report_outcome("v1", success=True, latency_ms=50.0)
            manager.report_outcome("v2", success=True, latency_ms=50.0)

        # Should NOT trigger rollback
        assert not manager.is_rollback_triggered()
        assert manager.candidate_ratio == 0.5

    def test_canary_waits_for_min_requests(self) -> None:
        """Test that rollback waits for minimum requests."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=100,
            auto_rollback_enabled=True,
        )

        # Report some failed requests but not enough for decision
        for _ in range(50):
            manager.report_outcome("v2", success=False)

        # Should NOT trigger rollback yet (need 100 requests)
        assert not manager.is_rollback_triggered()
        assert manager.candidate_ratio == 0.5

        # Report more failures to reach minimum
        for _ in range(50):
            manager.report_outcome("v2", success=False)

        # Now should trigger rollback
        assert manager.is_rollback_triggered()
        assert manager.candidate_ratio == 0.0

    def test_canary_rollback_on_latency(self) -> None:
        """Test rollback based on latency degradation."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
            latency_threshold_multiplier=1.5,  # Candidate can be 1.5x slower
        )

        # Report fast requests for current version (avg 50ms)
        for _ in range(100):
            manager.report_outcome("v1", success=True, latency_ms=50.0)

        # Report slow requests for candidate (avg 60ms, within 1.5x threshold)
        # 60ms < 50ms * 1.5 = 75ms, so should NOT trigger rollback
        for _ in range(10):
            manager.report_outcome("v2", success=True, latency_ms=60.0)

        # Should NOT trigger rollback (60ms < 75ms threshold)
        assert not manager.is_rollback_triggered()

        # Create second manager to test rollback case
        # Report slow requests for candidate (avg 150ms, exceeds 1.5x threshold)
        manager2 = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
            latency_threshold_multiplier=1.5,
        )

        for _ in range(100):
            manager2.report_outcome("v1", success=True, latency_ms=50.0)

        for _ in range(10):
            manager2.report_outcome("v2", success=True, latency_ms=200.0)

        # Should trigger rollback (200ms > 50ms * 1.5 = 75ms)
        assert manager2.is_rollback_triggered()
        assert manager2.candidate_ratio == 0.0

    def test_canary_auto_rollback_disabled(self) -> None:
        """Test that rollback can be disabled."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=10,
            auto_rollback_enabled=False,  # Disabled
        )

        # Report failed requests
        for _ in range(10):
            manager.report_outcome("v2", success=False)

        # Should NOT trigger rollback (disabled)
        assert not manager.is_rollback_triggered()
        assert manager.candidate_ratio == 0.5


class TestCanaryManagerMetrics:
    """Tests for metrics collection and reporting."""

    def test_get_metrics_for_version(self) -> None:
        """Test getting metrics for a specific version."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
        )

        # Report some requests
        for _ in range(10):
            manager.report_outcome("v1", success=True, latency_ms=50.0)

        for _ in range(5):
            manager.report_outcome("v2", success=True, latency_ms=60.0)
        for _ in range(2):
            manager.report_outcome("v2", success=False)

        # Get metrics for v1
        v1_metrics = manager.get_metrics("v1")
        assert v1_metrics["total_requests"] == 10
        assert v1_metrics["successful_requests"] == 10
        assert v1_metrics["error_rate"] == 0.0
        assert v1_metrics["average_latency_ms"] == 50.0

        # Get metrics for v2
        v2_metrics = manager.get_metrics("v2")
        assert v2_metrics["total_requests"] == 7
        assert v2_metrics["successful_requests"] == 5
        assert v2_metrics["failed_requests"] == 2
        assert abs(v2_metrics["error_rate"] - 2 / 7) < 0.01

    def test_get_all_metrics(self) -> None:
        """Test getting all metrics."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.3,
        )

        manager.report_outcome("v1", success=True, latency_ms=50.0)
        manager.report_outcome("v2", success=True, latency_ms=60.0)

        all_metrics = manager.get_metrics()

        assert "current_version" in all_metrics
        assert "candidate_version" in all_metrics
        assert "candidate_ratio" in all_metrics
        assert "rollback_triggered" in all_metrics
        assert "versions" in all_metrics

        assert all_metrics["current_version"] == "v1"
        assert all_metrics["candidate_version"] == "v2"
        assert all_metrics["candidate_ratio"] == 0.3
        assert "v1" in all_metrics["versions"]
        assert "v2" in all_metrics["versions"]

    def test_reset_metrics(self) -> None:
        """Test that metrics can be reset."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
        )

        # Report some requests
        for _ in range(10):
            manager.report_outcome("v1", success=True, latency_ms=50.0)
            manager.report_outcome("v2", success=False)

        # Trigger rollback
        manager2 = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=5,
        )
        for _ in range(10):
            manager2.report_outcome("v2", success=False)

        assert manager2.is_rollback_triggered()

        # Reset
        manager2.reset_metrics()

        # Check that metrics are cleared
        all_metrics = manager2.get_metrics()
        assert not all_metrics["rollback_triggered"]
        for version_metrics in all_metrics["versions"].values():
            assert version_metrics["total_requests"] == 0


class TestCanaryManagerPromotion:
    """Tests for candidate promotion."""

    def test_promote_candidate(self) -> None:
        """Test promoting candidate to full traffic."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.1,
        )

        assert manager.candidate_ratio == 0.1

        # Promote candidate
        manager.promote_candidate()

        assert manager.candidate_ratio == 1.0

        # All traffic should go to candidate now
        for _ in range(100):
            assert manager.select_version() == "v2"

    def test_set_candidate_ratio(self) -> None:
        """Test manually setting candidate ratio."""
        manager = CanaryManager(
            current_version="v1",
            candidate_version="v2",
            candidate_ratio=0.1,
        )

        manager.set_candidate_ratio(0.5)
        assert manager.candidate_ratio == 0.5

        with pytest.raises(ValueError):
            manager.set_candidate_ratio(1.5)
