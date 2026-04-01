"""Tests for canary deployment manager.

Tests cover:
- VersionMetrics properties
- CanaryManager initialization and validation
- Version selection logic
- Outcome reporting and metrics tracking
- Automatic rollback conditions
- Latency-based rollback
- Metrics retrieval
- Edge cases and error handling
"""

import pytest

from mlsdm.deploy.canary_manager import CanaryManager, VersionMetrics


class TestVersionMetrics:
    """Tests for VersionMetrics dataclass properties."""

    def test_default_values(self):
        """Test default values for VersionMetrics."""
        metrics = VersionMetrics()
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_latency_ms == 0.0

    def test_error_rate_no_requests(self):
        """Error rate should be 0.0 when no requests made."""
        metrics = VersionMetrics()
        assert metrics.error_rate == 0.0

    def test_error_rate_all_success(self):
        """Error rate should be 0.0 when all requests succeed."""
        metrics = VersionMetrics(total_requests=10, successful_requests=10, failed_requests=0)
        assert metrics.error_rate == 0.0

    def test_error_rate_all_failed(self):
        """Error rate should be 1.0 when all requests fail."""
        metrics = VersionMetrics(total_requests=10, successful_requests=0, failed_requests=10)
        assert metrics.error_rate == 1.0

    def test_error_rate_mixed(self):
        """Error rate should be correctly calculated for mixed results."""
        metrics = VersionMetrics(total_requests=10, successful_requests=7, failed_requests=3)
        assert metrics.error_rate == 0.3

    def test_success_rate_all_success(self):
        """Success rate should be 1.0 when all requests succeed."""
        metrics = VersionMetrics(total_requests=10, successful_requests=10, failed_requests=0)
        assert metrics.success_rate == 1.0

    def test_success_rate_all_failed(self):
        """Success rate should be 0.0 when all requests fail."""
        metrics = VersionMetrics(total_requests=10, successful_requests=0, failed_requests=10)
        assert metrics.success_rate == 0.0

    def test_average_latency_no_successful_requests(self):
        """Average latency should be 0.0 when no successful requests."""
        metrics = VersionMetrics(total_requests=5, successful_requests=0, failed_requests=5)
        assert metrics.average_latency_ms == 0.0

    def test_average_latency_with_successful_requests(self):
        """Average latency should be correctly calculated."""
        metrics = VersionMetrics(
            total_requests=5, successful_requests=5, failed_requests=0, total_latency_ms=500.0
        )
        assert metrics.average_latency_ms == 100.0


class TestCanaryManagerInit:
    """Tests for CanaryManager initialization."""

    def test_valid_initialization(self):
        """Test valid canary manager initialization."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.1,
            error_budget_threshold=0.05,
        )
        assert manager.current_version == "v1.0"
        assert manager.candidate_version == "v2.0"
        assert manager.candidate_ratio == 0.1
        assert manager.error_budget_threshold == 0.05

    def test_default_parameters(self):
        """Test default parameter values."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        assert manager.candidate_ratio == 0.1
        assert manager.error_budget_threshold == 0.05
        assert manager.min_requests_before_decision == 100
        assert manager.auto_rollback_enabled is True
        assert manager.latency_threshold_multiplier is None

    def test_invalid_candidate_ratio_negative(self):
        """Negative candidate ratio should raise ValueError."""
        with pytest.raises(ValueError, match="candidate_ratio must be between"):
            CanaryManager(current_version="v1.0", candidate_version="v2.0", candidate_ratio=-0.1)

    def test_invalid_candidate_ratio_above_one(self):
        """Candidate ratio above 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="candidate_ratio must be between"):
            CanaryManager(current_version="v1.0", candidate_version="v2.0", candidate_ratio=1.5)

    def test_invalid_error_budget_threshold_negative(self):
        """Negative error budget threshold should raise ValueError."""
        with pytest.raises(ValueError, match="error_budget_threshold must be between"):
            CanaryManager(
                current_version="v1.0",
                candidate_version="v2.0",
                error_budget_threshold=-0.1,
            )

    def test_invalid_error_budget_threshold_above_one(self):
        """Error budget threshold above 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="error_budget_threshold must be between"):
            CanaryManager(
                current_version="v1.0",
                candidate_version="v2.0",
                error_budget_threshold=1.5,
            )

    def test_invalid_min_requests_zero(self):
        """Zero min_requests_before_decision should raise ValueError."""
        with pytest.raises(ValueError, match="min_requests_before_decision must be >= 1"):
            CanaryManager(
                current_version="v1.0",
                candidate_version="v2.0",
                min_requests_before_decision=0,
            )

    def test_invalid_min_requests_negative(self):
        """Negative min_requests_before_decision should raise ValueError."""
        with pytest.raises(ValueError, match="min_requests_before_decision must be >= 1"):
            CanaryManager(
                current_version="v1.0",
                candidate_version="v2.0",
                min_requests_before_decision=-5,
            )


class TestCanaryManagerVersionSelection:
    """Tests for version selection logic."""

    def test_select_version_zero_ratio_always_current(self):
        """When candidate_ratio is 0.0, always select current version."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=0.0
        )
        # Run multiple times to verify deterministic behavior
        for _ in range(100):
            assert manager.select_version() == "v1.0"

    def test_select_version_full_ratio_always_candidate(self):
        """When candidate_ratio is 1.0, always select candidate version."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=1.0
        )
        # Run multiple times to verify deterministic behavior
        for _ in range(100):
            assert manager.select_version() == "v2.0"

    def test_select_version_distribution(self):
        """Verify approximate distribution with 50% candidate ratio."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=0.5
        )

        versions = [manager.select_version() for _ in range(1000)]
        current_count = versions.count("v1.0")
        candidate_count = versions.count("v2.0")

        # Allow for statistical variance (should be roughly 50/50)
        assert 300 < current_count < 700
        assert 300 < candidate_count < 700


class TestCanaryManagerSetRatio:
    """Tests for setting candidate ratio."""

    def test_set_valid_ratio(self):
        """Setting valid ratio should update candidate_ratio."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=0.1
        )
        manager.set_candidate_ratio(0.5)
        assert manager.candidate_ratio == 0.5

    def test_set_ratio_to_zero(self):
        """Setting ratio to 0.0 should work."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=0.5
        )
        manager.set_candidate_ratio(0.0)
        assert manager.candidate_ratio == 0.0

    def test_set_ratio_to_one(self):
        """Setting ratio to 1.0 should work."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=0.5
        )
        manager.set_candidate_ratio(1.0)
        assert manager.candidate_ratio == 1.0

    def test_set_invalid_ratio_negative(self):
        """Setting negative ratio should raise ValueError."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        with pytest.raises(ValueError, match="ratio must be between"):
            manager.set_candidate_ratio(-0.1)

    def test_set_invalid_ratio_above_one(self):
        """Setting ratio above 1.0 should raise ValueError."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        with pytest.raises(ValueError, match="ratio must be between"):
            manager.set_candidate_ratio(1.5)


class TestCanaryManagerOutcomeReporting:
    """Tests for outcome reporting and metrics tracking."""

    def test_report_success_without_latency(self):
        """Report successful outcome without latency."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        manager.report_outcome("v1.0", success=True)

        metrics = manager.get_metrics("v1.0")
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 0

    def test_report_success_with_latency(self):
        """Report successful outcome with latency."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        manager.report_outcome("v1.0", success=True, latency_ms=150.0)

        metrics = manager.get_metrics("v1.0")
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["average_latency_ms"] == 150.0

    def test_report_failure(self):
        """Report failed outcome."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        manager.report_outcome("v1.0", success=False)

        metrics = manager.get_metrics("v1.0")
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 1

    def test_report_unknown_version_creates_entry(self):
        """Reporting outcome for unknown version should create metrics entry."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        manager.report_outcome("v3.0", success=True)

        metrics = manager.get_metrics("v3.0")
        assert metrics["total_requests"] == 1

    def test_multiple_outcomes_aggregated(self):
        """Multiple outcomes should be aggregated correctly."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")

        manager.report_outcome("v1.0", success=True, latency_ms=100.0)
        manager.report_outcome("v1.0", success=True, latency_ms=200.0)
        manager.report_outcome("v1.0", success=False)

        metrics = manager.get_metrics("v1.0")
        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 2
        assert metrics["failed_requests"] == 1
        assert metrics["average_latency_ms"] == 150.0  # (100 + 200) / 2


class TestCanaryManagerAutoRollback:
    """Tests for automatic rollback functionality."""

    def test_rollback_triggered_on_high_error_rate(self):
        """Rollback should trigger when error rate exceeds threshold."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
        )

        # Generate failures exceeding error budget
        for _ in range(10):
            manager.report_outcome("v2.0", success=False)

        # Should trigger rollback (100% error rate > 5% threshold)
        assert manager.is_rollback_triggered() is True
        assert manager.candidate_ratio == 0.0

    def test_no_rollback_when_below_threshold(self):
        """No rollback when error rate is below threshold."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=0.2,  # 20% threshold
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
        )

        # Generate 10% error rate
        for _ in range(9):
            manager.report_outcome("v2.0", success=True)
        manager.report_outcome("v2.0", success=False)

        # Should NOT trigger rollback (10% < 20%)
        assert manager.is_rollback_triggered() is False
        assert manager.candidate_ratio == 0.5

    def test_no_rollback_before_min_requests(self):
        """Rollback should not trigger before min_requests_before_decision."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=100,  # High threshold
            auto_rollback_enabled=True,
        )

        # Generate high error rate but below min requests
        for _ in range(10):
            manager.report_outcome("v2.0", success=False)

        # Should NOT trigger rollback yet (only 10 requests)
        assert manager.is_rollback_triggered() is False

    def test_no_rollback_when_disabled(self):
        """Rollback should not trigger when auto_rollback_enabled is False."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=10,
            auto_rollback_enabled=False,
        )

        # Generate 100% error rate
        for _ in range(10):
            manager.report_outcome("v2.0", success=False)

        # Should NOT trigger rollback (disabled)
        assert manager.is_rollback_triggered() is False
        assert manager.candidate_ratio == 0.5


class TestCanaryManagerLatencyRollback:
    """Tests for latency-based rollback functionality."""

    def test_latency_rollback_when_candidate_slower(self):
        """Rollback should trigger when candidate latency exceeds threshold."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=1.0,  # High to avoid error-based rollback
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
            latency_threshold_multiplier=1.5,  # Candidate can be 50% slower max
        )

        # Current version with low latency
        for _ in range(10):
            manager.report_outcome("v1.0", success=True, latency_ms=100.0)

        # Candidate with high latency (200ms > 100ms * 1.5 = 150ms)
        for _ in range(10):
            manager.report_outcome("v2.0", success=True, latency_ms=200.0)

        assert manager.is_rollback_triggered() is True
        assert manager.candidate_ratio == 0.0

    def test_no_latency_rollback_when_candidate_acceptable(self):
        """No rollback when candidate latency is acceptable."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=1.0,
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
            latency_threshold_multiplier=2.0,  # Candidate can be 100% slower max
        )

        # Current version with 100ms latency
        for _ in range(10):
            manager.report_outcome("v1.0", success=True, latency_ms=100.0)

        # Candidate with 150ms latency (150ms < 100ms * 2.0 = 200ms)
        for _ in range(10):
            manager.report_outcome("v2.0", success=True, latency_ms=150.0)

        assert manager.is_rollback_triggered() is False
        assert manager.candidate_ratio == 0.5

    def test_no_latency_check_without_multiplier(self):
        """No latency check when latency_threshold_multiplier is None."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=1.0,
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
            latency_threshold_multiplier=None,  # Disabled
        )

        # Current version with low latency
        for _ in range(10):
            manager.report_outcome("v1.0", success=True, latency_ms=100.0)

        # Candidate with very high latency (10x slower)
        for _ in range(10):
            manager.report_outcome("v2.0", success=True, latency_ms=1000.0)

        # No rollback because latency check is disabled
        assert manager.is_rollback_triggered() is False

    def test_no_latency_check_without_current_metrics(self):
        """No latency check when current version has insufficient requests."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=1.0,
            min_requests_before_decision=10,
            auto_rollback_enabled=True,
            latency_threshold_multiplier=1.5,
        )

        # Only candidate has metrics (current has insufficient for comparison)
        for _ in range(5):  # Less than min_requests_before_decision
            manager.report_outcome("v1.0", success=True, latency_ms=100.0)

        for _ in range(10):
            manager.report_outcome("v2.0", success=True, latency_ms=1000.0)

        # No rollback because current version doesn't have enough data
        assert manager.is_rollback_triggered() is False


class TestCanaryManagerMetricsRetrieval:
    """Tests for metrics retrieval functionality."""

    def test_get_metrics_for_specific_version(self):
        """Get metrics for a specific version."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        manager.report_outcome("v1.0", success=True, latency_ms=100.0)

        metrics = manager.get_metrics("v1.0")
        assert metrics["version"] == "v1.0"
        assert metrics["total_requests"] == 1
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 0
        assert metrics["error_rate"] == 0.0
        assert metrics["success_rate"] == 1.0
        assert metrics["average_latency_ms"] == 100.0

    def test_get_metrics_for_unknown_version(self):
        """Get metrics for unknown version returns empty dict."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        metrics = manager.get_metrics("v3.0")
        assert metrics == {}

    def test_get_all_metrics(self):
        """Get all metrics when version is None."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.3,
        )
        manager.report_outcome("v1.0", success=True)
        manager.report_outcome("v2.0", success=False)

        metrics = manager.get_metrics()
        assert metrics["current_version"] == "v1.0"
        assert metrics["candidate_version"] == "v2.0"
        assert metrics["candidate_ratio"] == 0.3
        assert metrics["rollback_triggered"] is False
        assert "versions" in metrics
        assert "v1.0" in metrics["versions"]
        assert "v2.0" in metrics["versions"]


class TestCanaryManagerResetMetrics:
    """Tests for metrics reset functionality."""

    def test_reset_metrics_clears_all_data(self):
        """Reset metrics should clear all tracked data."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            error_budget_threshold=0.05,
            min_requests_before_decision=5,
        )

        # Generate some metrics and trigger rollback
        for _ in range(10):
            manager.report_outcome("v2.0", success=False)

        assert manager.is_rollback_triggered() is True

        # Reset metrics
        manager.reset_metrics()

        # Verify reset
        assert manager.is_rollback_triggered() is False
        metrics = manager.get_metrics("v2.0")
        assert metrics["total_requests"] == 0

    def test_reset_does_not_affect_configuration(self):
        """Reset should not affect manager configuration."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.7,
        )

        manager.reset_metrics()

        assert manager.current_version == "v1.0"
        assert manager.candidate_version == "v2.0"
        # Note: candidate_ratio may be 0 if rollback was triggered before reset


class TestCanaryManagerPromoteCandidate:
    """Tests for candidate promotion functionality."""

    def test_promote_candidate_sets_ratio_to_one(self):
        """Promoting candidate should set ratio to 1.0."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=0.1
        )

        manager.promote_candidate()

        assert manager.candidate_ratio == 1.0

    def test_promote_candidate_all_traffic_to_candidate(self):
        """After promotion, all traffic goes to candidate."""
        manager = CanaryManager(current_version="v1.0", candidate_version="v2.0")
        manager.promote_candidate()

        # All selections should return candidate
        for _ in range(100):
            assert manager.select_version() == "v2.0"


class TestCanaryManagerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_boundary_candidate_ratio_zero(self):
        """Test boundary: candidate_ratio = 0.0."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=0.0
        )
        assert manager.candidate_ratio == 0.0

    def test_boundary_candidate_ratio_one(self):
        """Test boundary: candidate_ratio = 1.0."""
        manager = CanaryManager(
            current_version="v1.0", candidate_version="v2.0", candidate_ratio=1.0
        )
        assert manager.candidate_ratio == 1.0

    def test_boundary_error_threshold_zero(self):
        """Test boundary: error_budget_threshold = 0.0."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            error_budget_threshold=0.0,
            min_requests_before_decision=1,
        )
        # Any error should trigger rollback with 0% threshold
        manager.report_outcome("v2.0", success=False)
        assert manager.is_rollback_triggered() is True

    def test_boundary_error_threshold_one(self):
        """Test boundary: error_budget_threshold = 1.0."""
        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            error_budget_threshold=1.0,
            min_requests_before_decision=1,
        )
        # Even 100% errors should not trigger rollback at 100% threshold
        manager.report_outcome("v2.0", success=False)
        assert manager.is_rollback_triggered() is False

    def test_concurrent_access_thread_safety(self):
        """Test thread safety with concurrent access."""
        import threading

        manager = CanaryManager(
            current_version="v1.0",
            candidate_version="v2.0",
            candidate_ratio=0.5,
            auto_rollback_enabled=False,  # Disable to focus on thread safety
        )

        errors = []

        def worker():
            try:
                for _ in range(100):
                    manager.select_version()
                    manager.report_outcome("v1.0", success=True, latency_ms=10.0)
                    manager.get_metrics()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        metrics = manager.get_metrics("v1.0")
        assert metrics["total_requests"] == 1000  # 10 threads * 100 requests
